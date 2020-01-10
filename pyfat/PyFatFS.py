# -*- coding: utf-8 -*-

"""PyFilesystem2 implementation of PyFAT."""

import errno

from fs.base import FS
from fs.permissions import Permissions
from fs.info import Info
from fs.errors import DirectoryExpected, DirectoryExists, \
    ResourceNotFound, FileExpected, DirectoryNotEmpty
from fs import ResourceType

from pyfat import FAT_OEM_ENCODING
from pyfat.PyFat import PyFat
from pyfat.FATDirectoryEntry import FATDirectoryEntry, make_lfn_entry
from pyfat._exceptions import PyFATException
from pyfat.FatIO import FatIO
from pyfat.EightDotThree import EightDotThree


class PyFatFS(FS):
    """PyFilesystem2 extension."""

    def __init__(self, filename: str, encoding: str = FAT_OEM_ENCODING,
                 offset: int = 0, preserve_case: bool = True,
                 read_only: bool = False):
        """PyFilesystem2 FAT constructor, initializes self.fs.

        :param filename: `str`: Name of file/device to open as FAT partition.
        :param encoding: `str`: Valid Python standard encoding.
        :param offset: `int`: Offset from file start to filesystem
                       start in bytes.
        :param preserve_case: `bool`: By default 8DOT3 filenames do not
                              support casing. If preserve_case is set to
                              `True`, it will create an LFN entry if the
                              casing does not conform to 8DOT3.
        :param read_only: `bool`: If set to true, the filesystem is mounted
                          in read-only mode, not allowing any modifications.
        """
        super(PyFatFS, self).__init__()
        self.preserve_case = preserve_case
        self.fs = PyFat(encoding=encoding, offset=offset)
        self.fs.open(filename, read_only=read_only)

    def close(self):
        """Clean up open handles."""
        try:
            self.fs.close()
        except PyFATException:
            # Ignore if filesystem is already closed
            pass

        super(PyFatFS, self).close()

    def exists(self, path: str):
        """Verify if given path exists on filesystem.

        :param path: Path to file or directory on filesystem
        :returns Boolean value indicating entries existence
        """
        try:
            self.fs.root_dir.get_entry(path)
        except PyFATException as e:
            if e.errno == errno.ENOENT:
                return False
            raise e

        return True

    def getinfo(self, path: str, namespaces=None):
        """Generate PyFilesystem2's `Info` struct.

        :param path: Path to file or directory on filesystem
        :param namespaces: Info namespaces to query, `NotImplemented`
        :returns `Info`
        """
        entry = self.fs.root_dir.get_entry(path)
        info = {"basic": {"name": repr(entry),
                          "is_dir": entry.is_directory()},
                "details": {"accessed": NotImplemented,
                            "created": NotImplemented,
                            "metadata_changed": None,
                            "modified": NotImplemented,
                            "size": entry.filesize,
                            "type": self.gettype(path)}}
        return Info(info)

    def getmeta(self, namespace=u'standard'):
        """Get generic filesystem metadata.

        :param namespace: Namespace to query, only `standard` supported
        :returns `dict` with file system meta data
        """
        if namespace != u'standard':
            return None

        return {"case_insensitive": not self.preserve_case,
                "invalid_path_chars": "\0",
                "max_path_length": 255,
                "max_sys_path": None,
                "network": False,
                "read_only": self.fs.is_read_only,
                "supports_rename": True}

    def getsize(self, path: str):
        """Get size of file in bytes.

        :param path: Path to file or directory on filesystem
        :returns Size in bytes as `int`
        """
        entry = self.fs.root_dir.get_entry(path)
        return entry.filesize

    def gettype(self, path: str):
        """Get type of file as `ResourceType`.

        :param path: Path to file or directory on filesystem
        :returns `ResourceType.directory` or `ResourceType.file`
        """
        entry = self.fs.root_dir.get_entry(path)
        if entry.is_directory():
            return ResourceType.directory

        return ResourceType.file

    def listdir(self, path: str):
        """List contents of given directory entry.

        :param path: Path to directory on filesystem
        """
        dir_entry = self.opendir(path)
        dirs, files, _ = dir_entry.get_entries()
        return [str(e) for e in dirs+files]

    def makedir(self, path: str, permissions: Permissions = None,
                recreate: bool = False):
        """Create directory on filesystem.

        :param path: Path of new directory on filesystem
        :param permissions: Currently not implemented
        :param recreate: Ignore if directory already exists
        """
        base = "/".join(path.split("/")[:-1])
        dirname = path.split("/")[-1]

        # Plausability checks
        try:
            base = self.opendir(base)
        except DirectoryExpected:
            raise ResourceNotFound(path)

        try:
            self._get_dir_entry(path)
        except ResourceNotFound:
            pass
        else:
            # TODO: Implement recreate param
            raise DirectoryExists(path)

        parent_is_root = base == self.fs.root_dir

        # Determine 8DOT3 file name + LFN
        short_name = EightDotThree()
        n = short_name.make_8dot3_name(dirname, base)
        short_name.set_str_name(n)

        newdir = FATDirectoryEntry(DIR_Name=short_name,
                                   DIR_Attr=FATDirectoryEntry.ATTR_DIRECTORY,
                                   DIR_NTRes=0,
                                   DIR_CrtTimeTenth=0,
                                   DIR_CrtDateTenth=0,
                                   DIR_LstAccessDate=0,
                                   DIR_FstClusHI=0x00,
                                   DIR_WrtTime=0,
                                   DIR_WrtDate=0,
                                   DIR_FstClusLO=0x00,
                                   DIR_FileSize=0,
                                   encoding=self.fs.encoding)

        # Create LFN entry if required
        if short_name.get_unpadded_filename() != dirname:
            lfn_entry = make_lfn_entry(dirname, short_name)
            newdir.set_lfn_entry(lfn_entry)

        # Create . and .. directory entries
        first_cluster = self.fs.allocate_bytes(
            FATDirectoryEntry.FAT_DIRECTORY_HEADER_SIZE * 2,
            erase=True)[0]
        newdir.set_cluster(first_cluster)
        dot_sn = EightDotThree()
        dot_sn.set_str_name(".")
        dot = FATDirectoryEntry(DIR_Name=dot_sn,
                                DIR_Attr=FATDirectoryEntry.ATTR_DIRECTORY,
                                DIR_NTRes=newdir.ntres,
                                DIR_CrtTimeTenth=newdir.crttimetenth,
                                DIR_CrtDateTenth=newdir.crtdatetenth,
                                DIR_LstAccessDate=newdir.lstaccessdate,
                                DIR_FstClusHI=newdir.fstclushi,
                                DIR_WrtTime=newdir.wrttime,
                                DIR_WrtDate=newdir.wrtdate,
                                DIR_FstClusLO=newdir.fstcluslo,
                                DIR_FileSize=newdir.filesize,
                                encoding=self.fs.encoding)
        dotdot_sn = EightDotThree()
        dotdot_sn.set_str_name("..")
        base_fstclushi = base.fstclushi if not parent_is_root else 0x0
        base_fstcluslo = base.fstcluslo if not parent_is_root else 0x0
        dotdot = FATDirectoryEntry(DIR_Name=dotdot_sn,
                                   DIR_Attr=FATDirectoryEntry.ATTR_DIRECTORY,
                                   DIR_NTRes=base.ntres,
                                   DIR_CrtTimeTenth=base.crttimetenth,
                                   DIR_CrtDateTenth=base.crtdatetenth,
                                   DIR_LstAccessDate=base.lstaccessdate,
                                   DIR_FstClusHI=base_fstclushi,
                                   DIR_WrtTime=base.wrttime,
                                   DIR_WrtDate=base.wrtdate,
                                   DIR_FstClusLO=base_fstcluslo,
                                   DIR_FileSize=base.filesize,
                                   encoding=self.fs.encoding)
        newdir.add_subdirectory(dot)
        newdir.add_subdirectory(dotdot)

        # Write new directory contents
        self.fs.update_directory_entry(newdir)

        # Write parent directory
        base.add_subdirectory(newdir)
        self.fs.update_directory_entry(base)

        # Flush FAT(s) to disk
        self.fs.flush_fat()

    def removedir(self, path: str):
        """Remove empty directories from the filesystem.

        :param path: `str`: Directory to remove
        """
        base = "/".join(path.split("/")[:-1])
        dirname = path.split("/")[-1]

        # Plausability checks
        try:
            base = self.opendir(base)
        except DirectoryExpected:
            raise ResourceNotFound(path)

        dir_entry = self._get_dir_entry(path)
        # Verify if the directory is empty
        if not dir_entry.is_empty():
            raise DirectoryNotEmpty(path)

        # Remove entry from parent directory
        base.remove_subdirectory(dirname)
        self.fs.update_directory_entry(base)

        # Free cluster in FAT
        self.fs.free_cluster_chain(dir_entry.get_cluster())
        del dir_entry

    def openbin(self, path: str, mode: str = "r",
                buffering: int = -1, **options):
        """Open file from filesystem.

        :param path: Path to file on filesystem
        :param mode: Mode to open file in
        :param buffering: TBD
        returns: `BinaryIO` stream
        """
        path = self.validatepath(path)

        try:
            info = self.getinfo(path)
        except ResourceNotFound:
            raise ResourceNotFound(path)
        else:
            if info.is_dir:
                raise FileExpected(path)

        return FatIO(self.fs, path, mode)

    def _get_dir_entry(self, path: str) -> FATDirectoryEntry:
        """Get a filesystem object for a path.

        :param path: `str`: Path on the filesystem
        :returns: `FATDirectoryEntry`
        """
        path = self.validatepath(path)
        try:
            dir_entry = self.fs.root_dir.get_entry(path)
        except PyFATException as e:
            if e.errno == errno.ENOENT:
                raise ResourceNotFound(path)
            raise e

        return dir_entry

    def opendir(self, path: str) -> FATDirectoryEntry:
        """Get a filesystem object for a sub-directory.

        :param path: str: Path to a directory on the filesystem.
        """
        dir_entry = self._get_dir_entry(path)

        if not dir_entry.is_directory():
            raise DirectoryExpected(path)

        return dir_entry

    def remove(self, path: str):
        """Not yet implemented."""
        print("remove")

    def setinfo(self, path: str, info):
        """Not yet implemented."""
        print("setinfo")
