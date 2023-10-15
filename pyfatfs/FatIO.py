# -*- coding: utf-8 -*-

"""Implementation of `FatIO` for basic I/O."""
import errno
import io
import threading
from typing import Union, Optional

from fs.mode import Mode

from pyfatfs.PyFat import PyFat


class FatIO(io.RawIOBase):
    """Wrap basic I/O operations for PyFat."""

    def __init__(self, fs: PyFat,
                 path: str,
                 mode: Mode = Mode('r')) -> None:
        """Wrap basic I/O operations for PyFat. **Currently read-only**.

        :param fs: `PyFat`: Instance of opened filesystem
        :param path: `str`: Path to file. If `mode` is *r*,
                            the file must exist.
        :param mode: `Mode`: Mode to open file in.
        """
        super(FatIO, self).__init__()
        self.mode = mode
        self.fs = fs
        self.name = str(path)
        # TODO: File locking
        self._lock = threading.Lock()

        self.dir_entry = self.fs.root_dir.get_entry(path)
        if self.dir_entry.is_directory() or self.dir_entry.is_special():
            raise IsADirectoryError(errno.EISDIR, path)
        elif self.dir_entry.is_volume_id():
            raise FileNotFoundError(errno.ENOENT, path)

        #: Position in bytes from beginning of file
        self.__bpos = 0
        #: Current cluster chain number
        self.__cpos = self.dir_entry.get_cluster()
        #: Current cluster chain index
        self.__cindex = 0
        #: Current cluster chain offset (in bytes)
        self.__coffpos = 0

        if self.mode.truncate:
            self.seek(0)
            self.truncate()
        if self.mode.appending:
            self.seek(0, 2)

    def __repr__(self) -> str:
        """Readable representation of class instance.

        ex: <FatFile fs=<PyFat object> path="/README.txt" mode="r">
        """
        return str(f'<{self.__class__.__name__} '
                   f'fs={self.fs} '
                   f'path="{self.name}" '
                   f'mode="{self.mode}"')

    def seek(self, offset: int, whence: int = 0) -> int:
        """Seek to a given offset in the file.

        :param offset: ``int``: offset in bytes in the file
        :param whence: ``int``: offset position:
                       - ``0``: absolute
                       - ``1``: relative to current position
                       - ``2``: relative to file end
        :returns: New position in bytes in the file
        """
        if whence == 1:
            offset += self.__bpos
        elif whence == 2:
            offset += self.dir_entry.get_size()
        elif whence != 0:
            raise ValueError(f"Invalid whence {whence}, should be 0, 1 or 2")

        offset = min(offset, self.dir_entry.filesize)
        prev_index = self.__cindex

        self.__cindex = offset // self.fs.bytes_per_cluster
        self.__coffpos = offset % self.fs.bytes_per_cluster
        self.__bpos = offset

        if self.__bpos == self.dir_entry.filesize and \
                self.__bpos > 0 and self.__coffpos == 0:
            # We are currently at the end of the last cluster, there is no
            # next cluster so go back to the end of the previous cluster
            self.__coffpos = self.fs.bytes_per_cluster
            self.__cindex -= 1

        # If we go back, we have to start from the beginning of the file
        if self.__cindex < prev_index:
            self.__cpos = self.dir_entry.get_cluster()
            prev_index = 0

        if self.__cindex > prev_index:
            fp = self.fs.get_cluster_chain(self.__cpos)
            for _ in range(0, self.__cindex - prev_index + 1):
                self.__cpos = next(fp)

        return self.__bpos

    def seekable(self) -> bool:
        """FAT I/O driver is able to seek in files.

        :returns: `True`
        """
        return True

    def close(self) -> None:
        """Close open file handles assuming lock handle."""
        self.seek(0)
        if self.mode.writing:
            self.fs.flush_fat()
        super().close()

    def readable(self) -> bool:
        """Determine whether or not the file is readable."""
        return self.mode.reading

    def read(self, size: int = -1) -> Union[bytes, None]:
        """Read given bytes from file."""
        if not self.mode.reading:
            raise IOError("File not open for reading")

        # Set size boundary
        if size + self.__bpos > self.dir_entry.filesize or size < 0:
            size = self.dir_entry.filesize - self.__bpos

        if size == 0:
            return b""

        chunks = []
        read_bytes = 0
        cluster_offset = self.__coffpos
        for c in self.fs.get_cluster_chain(self.__cpos):
            chunk_size = self.fs.bytes_per_cluster - cluster_offset
            # Do not read past EOF
            if read_bytes + chunk_size > size:
                chunk_size = size - read_bytes

            chunk = self.fs.read_cluster_contents(c)
            chunk = chunk[cluster_offset:][:chunk_size]
            cluster_offset = 0
            chunks.append(chunk)
            read_bytes += chunk_size
            if read_bytes == size:
                break

        self.seek(read_bytes, 1)

        chunks = b"".join(chunks)
        if len(chunks) != size:
            raise RuntimeError("Read a different amount of data "
                               "than was requested.")
        return chunks

    def readinto(self, __buffer: bytearray) -> Optional[int]:
        """Read data "directly" into bytearray."""
        data = self.read(len(__buffer))
        bytes_read = len(data)
        __buffer[:bytes_read] = data
        return bytes_read

    def writable(self) -> bool:
        """Determine whether or not the file is writable."""
        if not self.dir_entry.is_read_only() and not self.fs.is_read_only:
            return self.mode.writing
        return False

    def write(self, __b: Union[bytes, bytearray]) -> Optional[int]:
        """Write given bytes to file."""
        if not self.writable():
            raise IOError('Cannot write to read-only file!')

        sz = len(__b)
        cluster = self.dir_entry.get_cluster()
        if sz == 0:
            # Nothing to do
            return sz
        elif cluster == 0:
            # Allocate new cluster chain if needed
            self.__cpos = self.fs.allocate_bytes(sz)[0]
            self.dir_entry.set_cluster(self.__cpos)
        else:
            # Rewrite from current cluster
            if self.__coffpos != 0:
                cluster_data = self.fs.read_cluster_contents(self.__cpos)
                __b = cluster_data[0:self.__coffpos] + __b

        self.fs.write_data_to_cluster(__b, self.__cpos)
        if self.__bpos + sz > self.dir_entry.filesize:
            self.dir_entry.filesize = self.__bpos + sz
        self.seek(sz, 1)
        self.fs.update_directory_entry(self.dir_entry.get_parent_dir())
        return sz

    def truncate(self, size: Optional[int] = 0) -> int:
        """Truncate file to given size.

        :param size: `int`: Size to truncate to, defaults to 0.
        :returns: `int`: Truncated size
        """
        cur_pos = self.tell()
        size = size if size is not None else cur_pos

        if size > self.dir_entry.get_size():
            self.seek(0, 2)
            self.write(b'\0' * (size - self.dir_entry.get_size()))
            self.seek(cur_pos)
        elif size < self.dir_entry.get_size():
            # Always keep at least one cluster allocated
            num_clusters = max(1, self.fs.calc_num_clusters(size))
            i = 0
            for c in self.fs.get_cluster_chain(self.dir_entry.get_cluster()):
                i += 1
                if i <= num_clusters:
                    continue
                self.fs.free_cluster_chain(c)
                self.fs.flush_fat()
                break

        # Update file size
        self.dir_entry.set_size(size)
        self.fs.update_directory_entry(self.dir_entry.get_parent_dir())
        return size
