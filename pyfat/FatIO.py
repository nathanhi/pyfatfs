# -*- coding: utf-8 -*-

"""Implementation of `FatIO` for basic I/O."""
import errno
import io
import threading

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
        self.__fp = None
        self.name = str(path)
        # TODO: Seek support
        self.pos = 0
        # TODO: File locking
        self._lock = threading.Lock()

        self.dir_entry = self.fs.root_dir.get_entry(path)
        if self.dir_entry.is_directory() or self.dir_entry.is_special():
            raise IsADirectoryError(errno.EISDIR, path)
        elif self.dir_entry.is_volume_id():
            raise FileNotFoundError(errno.ENOENT, path)

    def __repr__(self) -> str:
        """Readable representation of class instance.

        ex: <FatFile fs=<PyFat object> path="/README.txt" mode="r">
        """
        return f'<{self.__class__.__name__} ' \
               f'fs={self.fs} ' \
               f'path="{self.name}" ' \
               f'mode="{self.mode}"'

    def close(self) -> None:
        """Close open file handles assuming lock handle."""
        raise NotImplementedError()

    def readable(self) -> bool:
        """Determine whether or not the file is readable."""
        return self.mode.reading

    def read(self, size: int = -1) -> bytes:
        """Read given bytes from file."""
        if not self.mode.reading:
            raise IOError("File not open for reading")

        chunks = []
        if size > self.dir_entry.filesize or size < 0:
            size = self.dir_entry.filesize
        read_bytes = 0

        for c in self.fs.get_cluster_chain(self.dir_entry.get_cluster()):
            chunk_size = self.fs.bytes_per_cluster
            if read_bytes + chunk_size > size:
                chunk_size = size - read_bytes
            read_bytes += chunk_size

            chunk = self.fs.read_cluster_contents(c)[:chunk_size]
            chunks.append(chunk)

        return b"".join(chunks)
