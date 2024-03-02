# -*- coding: utf-8 -*-

"""PyFilesystem2 implementation of PyFAT."""
import datetime
import posixpath
import errno
from copy import copy
from io import BytesIO, IOBase
from typing import Union

from fs.base import FS
from fs.mode import Mode
from fs.path import split, normpath
from fs.permissions import Permissions
from fs.info import Info
from fs.errors import DirectoryExpected, DirectoryExists, \
    ResourceNotFound, FileExpected, DirectoryNotEmpty, RemoveRootError, \
    FileExists
from fs import ResourceType
from fs.subfs import SubFS

from pyfatfs import FAT_OEM_ENCODING
from pyfatfs.DosDateTime import DosDateTime
from pyfatfs.PyFat import PyFat
from pyfatfs.FATDirectoryEntry import FATDirectoryEntry, make_lfn_entry
from pyfatfs._exceptions import PyFATException
from pyfatfs.FatIO import FatIO
from pyfatfs.EightDotThree import EightDotThree


class PyFatFS(FS):
    """PyFilesystem2 extension."""

    def __init__(self, filename: str, encoding: str = FAT_OEM_ENCODING,
                 offset: int = 0, preserve_case: bool = True,
                 read_only: bool = False, utc: bool = False,
                 lazy_load: bool = True):
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
        :param utc: `bool`: Store timestamps in UTC rather than the local time.
                    This applies to dentry creation, modification and last
                    access time.
        :param lazy_load: `bool`: Load directory entries on-demand instead of
                          parsing the entire directory listing on mount.
        """
        super(PyFatFS, self).__init__()
        self.preserve_case = preserve_case
        self.fs = PyFat(encoding=encoding, offset=int(offset),
                        lazy_load=lazy_load)
        self.fs.open(filename, read_only=read_only)

        if utc:
            self.tz = datetime.timezone.utc
        else:
            self.tz = datetime.datetime.now(datetime.timezone.utc)
            self.tz = self.tz.astimezone().tzinfo

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
        :returns: Boolean value indicating entries existence
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
        :returns: `Info`
        """
        try:
            entry = self.fs.root_dir.get_entry(path)
        except PyFATException as e:
            if e.errno in [errno.ENOTDIR, errno.ENOENT]:
                raise ResourceNotFound(path)
            raise e

        info = {"basic": {"name": repr(entry),
                          "is_dir": entry.is_directory()},
                "details": {"accessed": entry.get_atime().timestamp(),
                            "created": entry.get_ctime().timestamp(),
                            "metadata_changed": None,
                            "modified": entry.get_mtime().timestamp(),
                            "size": entry.filesize,
                            "type": self.gettype(path)}}
        return Info(info)

    def getmeta(self, namespace=u'standard'):
        """Get generic filesystem metadata.

        :param namespace: Namespace to query, only `standard` supported
        :returns: `dict` with file system meta data
        """
        if namespace != u'standard':
            return {}

        return {"case_insensitive": not self.preserve_case,
                "invalid_path_chars": "\0",
                "max_path_length": 255,
                "max_sys_path": None,
                "network": False,
                "read_only": self.fs.is_read_only,
                "unicode_paths": self.fs.encoding.lower().startswith('utf'),
                "supports_rename": True}

    def getsize(self, path: str):
        """Get size of file in bytes.

        :param path: Path to file or directory on filesystem
        :returns: Size in bytes as `int`
        """
        try:
            entry = self.fs.root_dir.get_entry(path)
        except PyFATException as e:
            if e.errno == errno.ENOENT:
                raise ResourceNotFound(path)
            raise e
        return entry.filesize

    def gettype(self, path: str):
        """Get type of file as `ResourceType`.

        :param path: Path to file or directory on filesystem
        :returns: `ResourceType.directory` or `ResourceType.file`
        """
        entry = self.fs.root_dir.get_entry(path)
        if entry.is_directory():
            return ResourceType.directory

        return ResourceType.file

    def listdir(self, path: str):
        """List contents of given directory entry.

        :param path: Path to directory on filesystem
        """
        dir_entry = self._get_dir_entry(path)
        try:
            dirs, files, _ = dir_entry.get_entries()
        except PyFATException as e:
            if e.errno == errno.ENOTDIR:
                raise DirectoryExpected(path)
            raise e
        return [str(e) for e in dirs+files]

    def create(self, path: str, wipe: bool = False) -> bool:
        """Create a new file.

        :param path: Path of new file on filesystem
        :param wipe: Overwrite existing file contents
        """
        basename = "/".join(path.split("/")[:-1])
        dirname = path.split("/")[-1]

        # Plausibility checks
        try:
            self.opendir(basename)
        except DirectoryExpected:
            raise ResourceNotFound(path)
        base = self._get_dir_entry(basename)

        try:
            dentry = self._get_dir_entry(path)
        except ResourceNotFound:
            pass
        else:
            if dentry.is_directory():
                raise FileExpected(path)
            if not wipe:
                return False
            else:
                # Clean up existing file contents
                dt = DosDateTime.now(tz=self.tz)
                dentry.wrttime = dt.serialize_time()
                dentry.wrtdate = dt.serialize_date()
                dentry.lstaccessdate = dt.serialize_date()
                dentry.filesize = 0
                old_cluster = dentry.get_cluster()
                dentry.set_cluster(0)
                self.fs.free_cluster_chain(old_cluster)
                return True

        # Determine 8DOT3 file name + LFN
        short_name = EightDotThree(encoding=self.fs.encoding)
        n = short_name.make_8dot3_name(dirname, base)
        short_name.set_str_name(n)

        newdir = FATDirectoryEntry.new(name=short_name, tz=self.tz,
                                       encoding=self.fs.encoding)

        # Create LFN entry if required
        _sfn = short_name.get_unpadded_filename()
        if _sfn != dirname.upper() or (_sfn != dirname and self.preserve_case):
            lfn_entry = make_lfn_entry(dirname, short_name)
            newdir.set_lfn_entry(lfn_entry)

        # Write reference to parent directory
        base.add_subdirectory(newdir)
        self.fs.update_directory_entry(base)

        # Flush FAT(s) to disk
        self.fs.flush_fat()
        return True

    def makedir(self, path: str, permissions: Permissions = None,
                recreate: bool = False):
        """Create directory on filesystem.

        :param path: Path of new directory on filesystem
        :param permissions: Currently not implemented
        :param recreate: Ignore if directory already exists
        """
        path = normpath(path)
        base = split(path)[0]
        dirname = split(path)[1]

        # Plausibility checks
        try:
            self.opendir(base)
        except DirectoryExpected:
            raise ResourceNotFound(path)
        base = self._get_dir_entry(base)

        try:
            dentry = self._get_dir_entry(path)
        except ResourceNotFound:
            pass
        else:
            if not recreate or not dentry.is_directory():
                raise DirectoryExists(path)
            else:
                return SubFS(self, path)

        parent_is_root = base == self.fs.root_dir

        # Determine 8DOT3 file name + LFN
        short_name = EightDotThree(encoding=self.fs.encoding)
        n = short_name.make_8dot3_name(dirname, base)
        short_name.set_str_name(n)

        newdir = FATDirectoryEntry.new(name=short_name, tz=self.tz,
                                       attr=FATDirectoryEntry.ATTR_DIRECTORY,
                                       encoding=self.fs.encoding)

        # Create LFN entry if required
        _sfn = short_name.get_unpadded_filename()
        if _sfn != dirname.upper() or (_sfn != dirname and self.preserve_case):
            lfn_entry = make_lfn_entry(dirname, short_name)
            newdir.set_lfn_entry(lfn_entry)

        # Create . and .. directory entries
        first_cluster = self.fs.allocate_bytes(
            FATDirectoryEntry.FAT_DIRECTORY_HEADER_SIZE * 2,
            erase=True)[0]
        newdir.set_cluster(first_cluster)
        dot_sn = EightDotThree()
        dot_sn.set_byte_name(b".          ")
        dot = copy(newdir)
        dot.name = dot_sn
        dot.lfn_entry = None
        dot._parent = None

        dotdot_sn = EightDotThree()
        dotdot_sn.set_byte_name(b"..         ")
        dotdot = copy(base)
        dotdot.name = dotdot_sn
        dotdot.lfn_entry = None
        dotdot._parent = None
        if parent_is_root:
            dotdot.set_cluster(0)
        newdir.add_subdirectory(dot)
        newdir.add_subdirectory(dotdot)

        # Write new directory contents
        self.fs.update_directory_entry(newdir)

        # Write parent directory
        base.add_subdirectory(newdir)
        self.fs.update_directory_entry(base)

        # Flush FAT(s) to disk
        self.fs.flush_fat()

        return SubFS(self, path)

    def removedir(self, path: str):
        """Remove empty directories from the filesystem.

        :param path: `str`: Directory to remove
        """
        dir_entry = self._get_dir_entry(path)
        try:
            base = dir_entry.get_parent_dir()
        except PyFATException as e:
            if e.errno == errno.ENOENT:
                # Don't remove root directory
                raise RemoveRootError(path)
            raise e

        # Verify if the directory is empty
        try:
            if not dir_entry.is_empty():
                raise DirectoryNotEmpty(path)
        except PyFATException as e:
            if e.errno == errno.ENOTDIR:
                raise DirectoryExpected(path)

        self._remove(base, dir_entry)

    def removetree(self, dir_path: str):
        """Recursively remove the contents of a directory.

        :param dir_path: ``str``: Path to a directory on the filesystem.
        """
        dir_entry = self._get_dir_entry(dir_path)

        if not dir_entry.is_directory():
            raise DirectoryExpected(dir_path)

        dirs, files, _ = dir_entry.get_entries()

        for f in files:
            self._remove(dir_entry, f)

        for d in dirs:
            self.removetree(posixpath.join(dir_path, str(d)))

        try:
            self.removedir(dir_path)
        except RemoveRootError:
            pass

    def remove(self, path: str):
        """Remove a file from the filesystem.

        :param path: `str`: Path of file to remove
        """
        dir_entry = self._get_dir_entry(path)

        # Check for file
        if dir_entry.is_directory() or dir_entry.is_special():
            raise FileExpected(path)

        base = dir_entry.get_parent_dir()
        self._remove(base, dir_entry)

    def _remove(self, parent_dir: FATDirectoryEntry,
                dir_entry: FATDirectoryEntry):
        """Remove directory entry regardless of type (dir or file).

        **NOTE:** This will not recursively remove directories, thus
        leave allocated clusters behind unless the directory has been
        purged before. Also, there is no check for special files such as
        volume labels, ».« and »..« entries. So it might leave the filesystem
        in a broken state if used incorrectly.

        :param parent_dir: ``FATDirectoryEntry``: Parent directory
        :param dir_entry: ``FATDirectoryEntry``: Directory entry to remove
        :raises PyFATException: ``ENOENT`` if given dir entry does not exist
                                in ``parent_dir``
        """
        # Remove entry from parent directory
        parent_dir.remove_dir_entry(str(dir_entry))
        self.fs.update_directory_entry(parent_dir)

        # Mark dentry as free
        dir_entry.mark_empty()
        if dir_entry.is_directory():
            self.fs.update_directory_entry(dir_entry)

        # Free cluster in FAT
        if dir_entry.get_entry_size() > 0 and dir_entry.get_cluster() != 0:
            # Empty files have a cluster ID of 0
            self.fs.free_cluster_chain(dir_entry.get_cluster())
        del dir_entry

    def openbin(self, path: str, mode: str = "r",
                buffering: int = -1, **options):
        """Open file from filesystem.

        :param path: Path to file on filesystem
        :param mode: Mode to open file in
        :param buffering: TBD
        :returns: `BinaryIO` stream
        """
        path = self.validatepath(path)
        mode = Mode(mode + 'b')
        if mode.create:
            if mode.exclusive:
                try:
                    self.getinfo(path)
                except ResourceNotFound:
                    pass
                else:
                    raise FileExists(path)
            self.create(path)
        if "t" in mode:
            raise ValueError('Text-mode not allowed in openbin')

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
        _path = normpath(self.validatepath(path))
        try:
            dir_entry = self.fs.root_dir.get_entry(_path)
        except PyFATException as e:
            if e.errno == errno.ENOENT:
                raise ResourceNotFound(path)
            raise e

        return dir_entry

    def opendir(self, path: str, factory=None) -> SubFS:
        """Get a filesystem object for a sub-directory.

        :param path: str: Path to a directory on the filesystem.
        """
        factory = factory or self.subfs_class or SubFS

        dir_entry = self._get_dir_entry(path)

        if not dir_entry.is_directory():
            raise DirectoryExpected(path)

        return factory(self, path)

    def setinfo(self, path: str, info):
        """Set file meta information such as timestamps."""
        details = info.get('details', {})
        dentry = self._get_dir_entry(path)

        ctime = details.get("created")
        mtime = details.get("modified")
        atime = details.get("accessed")
        if ctime:
            ctime = DosDateTime.fromtimestamp(ctime, tz=self.tz)
            dentry.crttime = ctime.serialize_time()
            dentry.crtdate = ctime.serialize_date()
        if mtime:
            mtime = DosDateTime.fromtimestamp(mtime, tz=self.tz)
            dentry.wrttime = mtime.serialize_time()
            dentry.wrtdate = mtime.serialize_date()
        if atime:
            atime = DosDateTime.fromtimestamp(atime, tz=self.tz)
            dentry.lstaccessdate = atime.serialize_date()

        self.fs.update_directory_entry(dentry.get_parent_dir())


class PyFatBytesIOFS(PyFatFS):
    """Provide PyFatFS functionality for BytesIO or IOBase streams."""

    def __init__(self, fp: Union[IOBase, BytesIO],
                 encoding: str = FAT_OEM_ENCODING,
                 offset: int = 0, preserve_case: bool = True,
                 utc: bool = False, lazy_load: bool = True):
        """PyFilesystem2 FAT constructor, initializes self.fs with BytesIO.

        :param fp: `BytesIO` / `IOBase`: Open file, either in-memory
                   or already open handle.
        :param encoding: `str`: Valid Python standard encoding.
        :param offset: `int`: Offset from file start to filesystem
                       start in bytes.
        :param preserve_case: `bool`: By default 8DOT3 filenames do not
                              support casing. If preserve_case is set to
                              `True`, it will create an LFN entry if the
                              casing does not conform to 8DOT3.
        :param utc: `bool`: Store timestamps in UTC rather than the local time.
                    This applies to dentry creation, modification and last
                    access time.
        :param lazy_load: `bool`: Load directory entries on-demand instead of
                          parsing the entire directory listing on mount.
        """
        super(PyFatFS, self).__init__()
        self.preserve_case = preserve_case
        self.fs = PyFat(encoding=encoding, offset=int(offset),
                        lazy_load=lazy_load)
        self.fs.set_fp(fp)

        if utc:
            self.tz = datetime.timezone.utc
        else:
            self.tz = datetime.datetime.now(datetime.timezone.utc)
            self.tz = self.tz.astimezone().tzinfo
