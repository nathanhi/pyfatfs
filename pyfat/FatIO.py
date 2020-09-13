# -*- coding: utf-8 -*-

"""Implementation of `FatIO` for basic I/O."""
import errno
import io
import threading
from typing import Union, Optional

from fs.mode import Mode

from pyfat.PyFat import PyFat


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
        self.mode = Mode(mode)
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
        #: Current cluster chain offset (in bytes)
        self.__coffpos = 0
        #: Handle to cluster chain iterator
        self.__fp = self.fs.get_cluster_chain(self.__cpos)

    def __repr__(self) -> str:
        """Readable representation of class instance.

        ex: <FatFile fs=<PyFat object> path="/README.txt" mode="r">
        """
        return f'<{self.__class__.__name__} ' \
               f'fs={self.fs} ' \
               f'path="{self.name}" ' \
               f'mode="{self.mode}"'

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

        old_bpos = self.__bpos
        old_cluster_count = old_bpos // self.fs.bytes_per_cluster
        cluster_count = offset // self.fs.bytes_per_cluster
        self.__coffpos = offset % self.fs.bytes_per_cluster
        self.__bpos = offset

        if old_bpos > self.__bpos:
            # Reset iterator if we have to seek back
            self.__fp = self.fs.get_cluster_chain(self.dir_entry.get_cluster())
            old_cluster_count = 0

        for _ in range(old_cluster_count, cluster_count):
            self.__cpos = next(self.__fp)

        return self.__bpos

    def seekable(self) -> bool:
        """Defines that the FAT I/O driver is able to seek in files.

        :returns `True`
        """
        return True

    def close(self) -> None:
        """Close open file handles assuming lock handle."""
        self.seek(0)
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
            return None

        chunks = []
        read_bytes = 0
        cluster_offset = self.__coffpos
        last_cluster = self.__cpos
        for c in self.__fp:
            chunk_size = self.fs.bytes_per_cluster - cluster_offset
            # Do not read past EOF
            if read_bytes + chunk_size > size:
                chunk_size = size - read_bytes - cluster_offset

            chunk = self.fs.read_cluster_contents(c)
            chunk = chunk[cluster_offset:][:chunk_size]
            cluster_offset = 0
            chunks.append(chunk)
            read_bytes += chunk_size
            last_cluster = c
            if read_bytes == size:
                break

        # Manually seek, we already touched the __fp generator
        self.__bpos += read_bytes
        self.__cpos = last_cluster
        self.__coffpos = read_bytes % self.fs.bytes_per_cluster

        chunks = b"".join(chunks)
        if len(chunks) != size:
            raise RuntimeError(f"Read a different amount of data than was requested.")
        return chunks

    def writable(self) -> bool:
        """Determine whether or not the file is writable."""
        if not self.dir_entry.is_read_only():
            return self.mode.writing
        return False

    def write(self, __b: Union[bytes, bytearray]) -> Optional[int]:
        """Write given bytes to file."""
        sz = len(__b)
        cluster = self.dir_entry.get_cluster()
        if sz == 0:
            # Nothing to do
            return sz
        elif cluster == 0:
            # Allocate new cluster chain if needed
            cluster = self.fs.allocate_bytes(sz)[0]
            self.dir_entry.set_cluster(cluster)
        elif self.__bpos == self.dir_entry.filesize:
            # Concatenate and rewrite last cluster
            __coffpos = self.__coffpos
            if self.__coffpos == 0:
                __coffpos = self.fs.bytes_per_cluster
            cluster = self.__cpos
            cluster_data = self.fs.read_cluster_contents(cluster)
            cluster_data = cluster_data[0:__coffpos]
            __b = cluster_data + __b
        else:
            raise NotImplementedError('Unable to modify file contents at the '
                                      'moment.\n'
                                      f'filesize: {self.dir_entry.filesize}'
                                      f'bpos: {self.__bpos}')

        self.fs.write_data_to_cluster(__b, cluster)

        # Seek after write
        self.__fp = self.fs.get_cluster_chain(cluster)
        self.dir_entry.filesize += sz
        self.seek(self.dir_entry.filesize)

        self.fs.update_directory_entry(self.dir_entry.get_parent_dir())
        return sz
