#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import errno

from fs.base import FS
from fs.permissions import Permissions
from fs.info import Info
from fs.errors import DirectoryExpected, DirectoryExists, ResourceNotFound
from fs import ResourceType

from pyfat.FATDirectoryEntry import FATDirectoryEntry, make_8dot3_name, make_lfn_entry
from pyfat.PyFat import PyFat
from pyfat._exceptions import PyFATException


class PyFatFS(FS):
    def __init__(self, filename: str, encoding: str = 'ibm437',
                 offset: int = 0):
        super(PyFatFS, self).__init__()
        self.fs = PyFat(encoding=encoding, offset=offset)
        self.fs.open(filename)

    def close(self):
        self.fs.close()
        super(PyFatFS, self).close()

    def exists(self, path: str):
        try:
            self.fs.root_dir.get_entry(path)
        except PyFATException as e:
            if e.errno == errno.ENOENT:
                return False
            raise e

        return True

    def getinfo(self, path: str, namespaces=None):
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
        if namespace != u'standard':
            return None

        return {"case_insensitive": True,
                "invalid_path_chars": "/",
                "max_path_length": 255,
                "max_sys_path": None,
                "network": False,
                "read_only": False,
                "supports_rename": True}

    def getsize(self, path: str):
        entry = self.fs.root_dir.get_entry(path)
        return entry.filesize

    def gettype(self, path: str):
        entry = self.fs.root_dir.get_entry(path)
        if entry.is_directory():
            return ResourceType.directory

        return ResourceType.file

    def listdir(self, path: str):
        dir_entry = self.opendir(path)
        dirs, files, specials = dir_entry.get_entries()
        return [str(e) for e in dirs+files]

    def makedir(self, path: str, permissions: Permissions = None,
                recreate: bool = False):
        base = "/".join(path.split("/")[:-1])
        dirname = path.split("/")[-1]

        # Plausability checks
        try:
            base = self.opendir(base)
        except DirectoryExpected:
            raise ResourceNotFound(path)

        dirs, files, _ = base.get_entries()
        if dirname.upper() in [str(e).upper() for e in dirs+files]:
            raise DirectoryExists(path)

        # Determine file name + LFN
        short_name = make_8dot3_name(dirname, base)
        if short_name != dirname:
            lfn_entry = make_lfn_entry(dirname, encoding=self.fs.encoding)
        else:
            lfn_entry = None

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
                                   encoding=self.fs.encoding,
                                   lfn_entry=lfn_entry)

        # Determine position in FAT
        base_cluster_size = 0
        base_cluster_chain = []
        for c in self.fs.get_cluster_chain(base.get_cluster()):
            base_cluster_chain += [c]
            base_cluster_size += self.fs.bytes_per_cluster

        dirs, files, _ = base.get_entries()
        base_entries_bytes = 0

        for e in dirs + files:
            base_entries_bytes += e.get_entry_size()

        base_cluster_free = base_cluster_size - base_entries_bytes
        if newdir.get_entry_size() > base_cluster_free:
            # Enhance chain if entries exhausted; FAT32 only
            if self.fs.fat_type in [self.FAT_TYPE_FAT12, self.FAT_TYPE_FAT16]:
                raise PyFATException("Cannot create directory, maximum root "
                                     "directory entries exhausted!",
                                     errno=errno.ENOSPC)

            required_bytes = newdir.get_entry_size() - base_cluster_free
            new_chain = self.fs.allocate_bytes(required_bytes)[0]
            self.fs.fat[base_cluster_chain[-1:]] = new_chain

        # Create . and .. directory entries
        first_cluster = self.fs.allocate_bytes(FATDirectoryEntry.FAT_DIRECTORY_HEADER_SIZE * 2)[0]
        newdir.set_cluster(first_cluster)
        dot = FATDirectoryEntry(DIR_Name=".",
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
        dotdot = FATDirectoryEntry(DIR_Name="..",
                                   DIR_Attr=FATDirectoryEntry.ATTR_DIRECTORY,
                                   DIR_NTRes=base.ntres,
                                   DIR_CrtTimeTenth=base.crttimetenth,
                                   DIR_CrtDateTenth=base.crtdatetenth,
                                   DIR_LstAccessDate=base.lstaccessdate,
                                   DIR_FstClusHI=base.fstclushi,
                                   DIR_WrtTime=base.wrttime,
                                   DIR_WrtDate=base.wrtdate,
                                   DIR_FstClusLO=base.fstcluslo,
                                   DIR_FileSize=base.filesize,
                                   encoding=self.fs.encoding)

        # TODO: Flush dot and dotdot entries to disk

        # TODO: Flush directory entry to disk
        start_cluster = base_entries_bytes // self.fs.bytes_per_cluster

        print(f"makedir '{base}' + '{dirname}'")

    def openbin(self, path: str, mode: str = "r",
                buffering: int = -1, **options):
        print("openbin")

    """@_init_check
    def get_file(self, dir_entry: FATDirectoryEntry):
        ""'"Open given entry if it is a file.""'"
        if dir_entry.is_special() or dir_entry.is_directory():
            raise IsADirectoryError(f'Cannot open "{dir_entry.__repr__()}", since it is a directory')

        fullsize = dir_entry.filesize
        fsz = 0
        for i in self.get_cluster_chain(dir_entry.fstcluslo):
            self.__seek(i)
            sz = self.bpb_header["BPB_SecPerClus"] * self.bpb_header["BPB_BytsPerSec"]
            if fsz + sz > fullsize:
                sz = fullsize - fsz
            fsz += sz
            import sys
            sys.stdout.write(self.__fp.read(sz).decode('UTF-8'))"""

    def opendir(self, path: str) -> FATDirectoryEntry:
        """Get a filesystem object for a sub-directory.
        :param path: str: Path to a directory on the filesystem.
        """
        try:
            dir_entry = self.fs.root_dir.get_entry(path)
        except PyFATException as e:
            if e.errno == errno.ENOENT:
                raise DirectoryExpected(path)
            raise e

        if not dir_entry.is_directory():
            raise DirectoryExpected(path)

        return dir_entry

    def remove(self, path: str):
        print("remove")

    def removedir(self, path: str):
        print("removedir")

    def setinfo(self, path: str, info):
        print("setinfo")
