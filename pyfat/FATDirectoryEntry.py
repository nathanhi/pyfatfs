# -*- coding: utf-8 -*-

"""Directory entry operations with PyFAT."""
import os
import struct

from pyfat._exceptions import PyFATException, NotAnLFNEntryException,\
    BrokenLFNEntryException

import errno


class FATDirectoryEntry(object):
    """Represents directory entries in FAT (files & directories)."""

    #: Bit set in DIR_Attr if entry is read-only
    ATTR_READ_ONLY = 0x01
    #: Bit set in DIR_Attr if entry is hidden
    ATTR_HIDDEN = 0x02
    #: Bit set in DIR_Attr if entry is a system file
    ATTR_SYSTEM = 0x04
    #: Bit set in DIR_Attr if entry is a volume id descriptor
    ATTR_VOLUME_ID = 0x8
    #: Bit set in DIR_Attr if entry is a directory
    ATTR_DIRECTORY = 0x10
    #: Bit set in DIR_Attr if entry is an archive
    ATTR_ARCHIVE = 0x20
    #: Bits set in DIR_Attr if entry is an LFN entry
    ATTR_LONG_NAME = ATTR_READ_ONLY | ATTR_HIDDEN | \
        ATTR_SYSTEM | ATTR_VOLUME_ID
    #: Bitmask to check if entry is an LFN entry
    ATTR_LONG_NAME_MASK = ATTR_READ_ONLY | ATTR_HIDDEN | ATTR_SYSTEM | \
        ATTR_VOLUME_ID | ATTR_DIRECTORY | ATTR_ARCHIVE

    #: Directory entry header layout in struct formatted string
    FAT_DIRECTORY_LAYOUT = "<11sBHHHHHHHHL"
    #: Size of a directory entry header in bytes
    FAT_DIRECTORY_HEADER_SIZE = struct.calcsize(FAT_DIRECTORY_LAYOUT)
    #: Directory entry headers
    FAT_DIRECTORY_VARS = ["DIR_Name", "DIR_Attr", "DIR_NTRes",
                          "DIR_CrtTimeTenth", "DIR_CrtDateTenth",
                          "DIR_LstAccessDate", "DIR_FstClusHI",
                          "DIR_WrtTime", "DIR_WrtDate",
                          "DIR_FstClusLO", "DIR_FileSize"]

    def __init__(self, DIR_Name, DIR_Attr, DIR_NTRes, DIR_CrtTimeTenth,
                 DIR_CrtDateTenth, DIR_LstAccessDate, DIR_FstClusHI,
                 DIR_WrtTime, DIR_WrtDate, DIR_FstClusLO, DIR_FileSize,
                 encoding, lfn_entry=None):
        """FAT directory entry constructor.

        :param DIR_Name: Directory name can either be string or byte string
        :param DIR_Attr: Attributes of directory
        :param DIR_NTRes: Reserved attributes of directory entry
        :param DIR_CrtTimeTenth: Creation timestamp of entry
        :param DIR_CrtDateTenth: Creation date of entry
        :param DIR_LstAccessDate: Last access date of entry
        :param DIR_FstClusHI: High cluster value of entry data
        :param DIR_WrtTime: Modification timestamp of entry
        :param DIR_WrtDate: Modification date of entry
        :param DIR_FstClusLO: Low cluster value of entry data
        :param DIR_FileSize: File size in bytes
        :param encoding: Encoding of filename
        :param lfn_entry: FATLongDirectoryEntry instance or None
        """
        if len(DIR_Name) > 0:
            if DIR_Name[0] == 0x0 or DIR_Name[0] == 0xE5:
                # Empty directory entry
                raise NotADirectoryError("Given dir entry is invalid and has "
                                         "no valid name.")

            if DIR_Name[0] == 0x05:
                # Translate 0x05 to 0xE5
                DIR_Name = DIR_Name.replace(bytes(0x05), bytes(0xE5), 1)

        if isinstance(DIR_Name, str):
            # Encode it to given encoding
            DIR_Name = DIR_Name.encode(encoding)

        self.name = DIR_Name
        self.attr = int(DIR_Attr)
        self.ntres = int(DIR_NTRes)
        self.crttimetenth = int(DIR_CrtTimeTenth)
        self.crtdatetenth = int(DIR_CrtDateTenth)
        self.lstaccessdate = int(DIR_LstAccessDate)
        self.fstclushi = int(DIR_FstClusHI)
        self.wrttime = int(DIR_WrtTime)
        self.wrtdate = int(DIR_WrtDate)
        self.fstcluslo = int(DIR_FstClusLO)
        self.filesize = int(DIR_FileSize)

        self._parent = None

        # Handle LFN entries
        self.lfn_entry = None
        self.set_lfn_entry(lfn_entry)

        self.__dirs = set()
        self.__encoding = encoding

        if not is_8dot3_conform(self.get_short_name()):
            raise PyFATException(f"Given directory name "
                                 f"{self.get_short_name()} is not conform "
                                 f"to 8.3 file naming convention.",
                                 errno=errno.EINVAL)

    def calculate_checksum(self) -> int:
        """Calculate checksum of short directory entry.

        :returns: Checksum as int
        """
        chksum = 0
        for c in self.name:
            chksum = ((chksum >> 1) | (chksum & 1) << 7) + c
            chksum &= 0xFF
        return chksum

    def set_lfn_entry(self, lfn_entry):
        """Set LFN entry for current directory entry.

        :param: lfn_entry: Can be either of type `FATLongDirectoryEntry`
                or `None`.
        """
        if not isinstance(lfn_entry, FATLongDirectoryEntry):
            return

        # Verify LFN entries checksums
        chksum = self.calculate_checksum()
        for entry in lfn_entry.lfn_entries:
            entry_chksum = lfn_entry.lfn_entries[entry]["LDIR_Chksum"]
            if entry_chksum != chksum:
                raise BrokenLFNEntryException()
        self.lfn_entry = lfn_entry

    def get_entry_size(self):
        """Get size of directory entry.

        :returns: Entry size in bytes as int
        """
        sz = self.FAT_DIRECTORY_HEADER_SIZE
        if isinstance(self.lfn_entry, FATLongDirectoryEntry):
            sz *= len(self.lfn_entry.lfn_entries)
        return sz

    def get_size(self):
        """Get filesize or directory entry size.

        :returns: Filesize or directory entry size in bytes as int
        """
        if self.is_directory():
            sz = self.FAT_DIRECTORY_HEADER_SIZE
            sz *= len(self.__dirs)+1
            return sz

        return self.filesize

    def get_cluster(self):
        """Get cluster address of directory entry.

        :returns: Cluster address of entry
        """
        return self.fstcluslo + (self.fstclushi << 16)

    def set_cluster(self, first_cluster):
        """Set low and high cluster address in directory headers."""
        self.fstcluslo = (first_cluster >> (16 * 0) & 0xFFFF)
        self.fstclushi = (first_cluster >> (16 * 1) & 0xFFFF)

    def byte_repr(self):
        """Represent directory entry as bytes.

        Note: Also represents accompanying LFN entries

        :returns: Entry & LFN entry as bytes-object
        """
        name = self.name
        if name[0] == 0xE5:
            name[0] = 0x05

        entry = struct.pack(self.FAT_DIRECTORY_LAYOUT, name, self.attr,
                            self.ntres, self.crttimetenth, self.crtdatetenth,
                            self.lstaccessdate, self.fstclushi, self.wrttime,
                            self.wrtdate, self.fstcluslo, self.filesize)

        if isinstance(self.lfn_entry, FATLongDirectoryEntry):
            entry += self.lfn_entry.byte_repr()

        return entry

    def _add_parent(self, cls):
        """Add parent directory link to current directory entry.

        raises: PyFATException
        """
        if self._parent is not None:
            raise PyFATException("Trying to add multiple parents to current "
                                 "directory!", errno=errno.ETOOMANYREFS)

        if not isinstance(cls, FATDirectoryEntry):
            raise PyFATException("Trying to add a non-FAT directory entry "
                                 "as parent directory!", errno=errno.EBADE)

        self._parent = cls

    def _get_parent_dir(self, sd):
        """Build path name for recursive directory entries."""
        name = self.__repr__()
        if self.__repr__() == "/":
            name = ""
        sd += [name]

        if self._parent is None:
            return sd

        return self._parent._get_parent_dir(sd)

    def get_parent_dir(self):
        """Iterate all parents up and join them by "/"."""
        parent_dirs = [self.__repr__()]

        if self._parent is None:
            return "/".join(list(reversed(parent_dirs)))

        return "/".join(list(reversed(
            self._parent._get_parent_dir(parent_dirs))))

    def is_special(self):
        """Determine if dir entry is a dot or dotdot entry.

        :returns: Boolean value whether or not entry is
                  a dot or dotdot entry
        """
        return self.get_short_name() in [".", ".."]

    def is_read_only(self):
        """Determine if dir entry has read-only attribute set.

        :returns: Boolean value indicating read-only attribute is set
        """
        return (self.ATTR_READ_ONLY & self.attr) > 0

    def is_hidden(self):
        """Determine if dir entry has the hidden attribute set.

        :returns: Boolean value indicating hidden attribute is set
        """
        return (self.ATTR_HIDDEN & self.attr) > 0

    def is_system(self):
        """Determine if dir entry has the system file attribute set.

        :returns: Boolean value indicating system attribute is set
        """
        return (self.ATTR_SYSTEM & self.attr) > 0

    def is_volume_id(self):
        """Determine if dir entry has the volume ID attribute set.

        :returns: Boolean value indicating volume ID attribute is set
        """
        return (self.ATTR_VOLUME_ID & self.attr) > 0

    def _verify_is_directory(self):
        """Verify that current entry is a directory.

        raises: PyFATException: If current entry is not a directory.
        """
        if not self.is_directory():
            raise PyFATException("Cannot get entries of this entry, as "
                                 "it is not a directory.",
                                 errno=errno.ENOTDIR)

    def is_directory(self):
        """Determine if dir entry has directory attribute set.

        :returns: Boolean value indicating directory attribute is set
        """
        return (self.ATTR_DIRECTORY & self.attr) > 0

    def is_archive(self):
        """Determine if dir entry has archive attribute set.

        :returns: Boolean value indicating archive attribute is set
        """
        return (self.ATTR_ARCHIVE & self.attr) > 0

    def get_entries(self):
        """Get entries of directory.

        :raises: PyFatException: If entry is not a directory
        :returns: tuple: root (current path, full),
                 dirs (all dirs), files (all files)
        """
        dirs = []
        files = []
        specials = []

        self._verify_is_directory()

        for d in self.__dirs:
            if d.is_special() or d.is_volume_id():
                # Volume IDs and dot/dotdot entries
                specials += [d]
            elif d.is_directory():
                # Directories
                dirs += [d]
            else:
                # Everything else must be a file
                files += [d]

        return dirs, files, specials

    def _search_entry(self, name: str):
        """Find given dir entry by walking current dir.

        :param name: Name of entry to search for
        :raises: PyFATException: If entry cannot be found
        :returns: FATDirectoryEntry: Found entry
        """
        dirs, files, _ = self.get_entries()
        for entry in dirs+files:
            try:
                if entry.get_long_name() == name:
                    return entry
            except NotAnLFNEntryException:
                pass
            if entry.get_short_name() == name:
                return entry

        raise PyFATException(f'Cannot find entry {name}',
                             errno=errno.ENOENT)

    def get_entry(self, path: str):
        """Get sub-entry if current entry is a directory.

        :param path: Relative path of entry to get
        :raises: PyFATException: If entry cannot be found
        :returns: FATDirectoryEntry: Found entry
        """
        entry = self
        for segment in filter(None, path.split("/")):
            entry._verify_is_directory()
            entry = entry._search_entry(segment)
        return entry

    def walk(self):
        """Walk all directory entries recursively.

        :returns: tuple: root (current path, full),
                         dirs (all dirs), files (all files)
        """
        root = self.get_parent_dir()
        dirs, files, _ = self.get_entries()

        yield root, dirs, files
        for d in self.__dirs:
            if d.is_special():
                # Ignore dot and dotdot
                continue

            if not d.is_directory():
                continue

            yield from d.walk()

    def add_subdirectory(self, dir_entry):
        """Register a subdirectory in current directory entry.

        :param dir_entry: FATDirectoryEntry
        :raises: PyFATException: If current entry is not a directory or
                                 given directory entry already has a parent
                                 directory set
        """
        # Check if current dir entry is even a directory!
        self._verify_is_directory()

        dir_entry._add_parent(self)
        self.__dirs.add(dir_entry)

    def __repr__(self):
        """String-represent directory entry by (preferrably) LFN.

        :returns: str: Long file name if existing, 8DOT3 otherwise
        """
        try:
            return self.get_long_name()
        except NotAnLFNEntryException:
            return self.get_short_name()

    def get_short_name(self):
        """Get short name of directory entry.

        :returns: str: Name of directory entry
        """
        n = self.name.decode(self.__encoding)

        sep = "."
        if self.attr == self.ATTR_DIRECTORY:
            sep = ""

        name = n[0:8].strip()
        ext = n[8:11].strip()

        if ext == "":
            return name
        else:
            return sep.join([name, ext])

    def get_long_name(self):
        """Get long name of directory entry.

        :raises: NotAnLFNEntryException: If entry has no long file name
        :returns: str: Long file name of directory entry
        """
        if self.lfn_entry is None:
            raise NotAnLFNEntryException("No LFN entry found for this "
                                         "dir entry.")

        name = ""
        for i in sorted(self.lfn_entry.lfn_entries.keys()):
            for h in ["LDIR_Name1", "LDIR_Name2", "LDIR_Name3"]:
                name += FATLongDirectoryEntry._remove_padding(
                    self.lfn_entry.lfn_entries[i][h]).decode(self.__encoding)

        return name.strip()


class FATLongDirectoryEntry(object):
    """Represents long file name (LFN) entries."""

    #: LFN entry header layout in struct formatted string
    FAT_LONG_DIRECTORY_LAYOUT = "<B10sBBB12sH4s"
    #: LFN header fields when extracted with `FAT_LONG_DIRECTORY_LAYOUT`
    FAT_LONG_DIRECTORY_VARS = ["LDIR_Ord", "LDIR_Name1", "LDIR_Attr",
                               "LDIR_Type", "LDIR_Chksum", "LDIR_Name2",
                               "LDIR_FstClusLO", "LDIR_Name3"]
    #: Ordinance of last LFN entry in a chain
    LAST_LONG_ENTRY = 0x40

    def __init__(self):
        """Initialize empty LFN directory entry object."""
        self.lfn_entries = {}

    def byte_repr(self):
        """Represent LFN entries as bytes."""
        entries_bytes = b""
        for e in self.lfn_entries.keys():
            e = self.lfn_entries[e]
            entries_bytes += struct.pack(self.FAT_LONG_DIRECTORY_LAYOUT,
                                         e["LDIR_Ord"], e["LDIR_Name1"],
                                         e["LDIR_Attr"], e["LDIR_Type"],
                                         e["LDIR_Chksum"], e["LDIR_Name2"],
                                         e["LDIR_FstClusLO"], e["LDIR_Name3"])
        return entries_bytes

    @staticmethod
    def _remove_padding(entry: bytes):
        """Remove padding from given LFN entry.

        :param entry: LDIR_Name* entry
        """
        while entry.endswith(b'\xFF\xFF'):
            entry = entry[:-2]
        entry = entry.replace(b'\x00', b'')
        return entry

    @staticmethod
    def is_lfn_entry(LDIR_Ord, LDIR_Attr):
        """Verify that entry is an LFN entry.

        :param LDIR_Ord: First byte of the directory header, ordinance
        :param LDIR_Attr: Attributes segment of directory header
        :returns: `True` if entry is a valid LFN entry
        """
        lfn_attr = FATDirectoryEntry.ATTR_LONG_NAME
        lfn_attr_mask = FATDirectoryEntry.ATTR_LONG_NAME_MASK
        is_attr_set = (LDIR_Attr & lfn_attr_mask) == lfn_attr

        return is_attr_set and LDIR_Ord != 0xE5

    def add_lfn_entry(self, LDIR_Ord, LDIR_Name1, LDIR_Attr, LDIR_Type,
                      LDIR_Chksum, LDIR_Name2, LDIR_FstClusLO, LDIR_Name3):
        """Add LFN entry to this instances chain.

        :param LDIR_Ord: Ordinance of LFN entry
        :param LDIR_Name1: First name field of LFN entry
        :param LDIR_Attr: Attributes of LFN entry
        :param LDIR_Type: Type of LFN entry
        :param LDIR_Chksum: Checksum value of following 8dot3 entry
        :param LDIR_Name2: Second name field of LFN entry
        :param LDIR_FstClusLO: Cluster address of LFN entry. Always zero.
        :param LDIR_Name3: Third name field of LFN entry
        """
        # Check if attribute matches
        if not self.is_lfn_entry(LDIR_Ord, LDIR_Attr):
            raise NotAnLFNEntryException("Given LFN entry is not a long "
                                         "file name entry or attribute "
                                         "not set correctly!")

        # Check if FstClusLO is 0, as required by the spec
        if LDIR_FstClusLO != 0:
            raise PyFATException("Given LFN entry has an invalid first "
                                 "cluster ID, don't know what to do.",
                                 errno=errno.EFAULT)

        # Check if item with same index has already been added
        if LDIR_Ord in self.lfn_entries.keys():
            raise PyFATException("Given LFN entry part with index \'{}\'"
                                 "has already been added to LFN "
                                 "entry list.".format(LDIR_Ord))

        mapped_entries = dict(zip(self.FAT_LONG_DIRECTORY_VARS,
                                  (LDIR_Ord, LDIR_Name1, LDIR_Attr, LDIR_Type,
                                   LDIR_Chksum, LDIR_Name2, LDIR_FstClusLO,
                                   LDIR_Name3)))

        self.lfn_entries[LDIR_Ord] = mapped_entries

    def is_lfn_entry_complete(self):
        """Verify that LFN object forms a complete chain.

        :returns: `True` if `LAST_LONG_ENTRY` is found
        """
        for k in self.lfn_entries.keys():
            if (int(k) & self.LAST_LONG_ENTRY) == self.LAST_LONG_ENTRY:
                return True

        return False


def make_8dot3_name(dir_name: str, parent_dir_entry: FATDirectoryEntry):
    """Generate filename based on 8.3 rules out of a long file name.

    In 8.3 notation we try to use the first 6 characters and
    fill the rest with a tilde, followed by a number (starting
    at 1). If that entry is already given, we increment this
    number and try again until all possibilities are exhausted
    (i.e. A~999999.TXT).

    :param dir_name: Long name of directory entry
    :param parent_dir_entry: Directory entry of parent dir.
    :raises: PyFATException: If parent dir is not a directory
                             or all name generation possibilities
                             are exhausted
    """
    dirs, files, _ = parent_dir_entry.get_entries()
    dir_entries = [e.get_short_name() for e in dirs+files]

    extsep = "."

    try:
        basename = dir_name.upper().rsplit(".", 1)[0][0:8]
    except IndexError:
        basename = ""

    try:
        extname = dir_name.upper().rsplit(".", 1)[1][0:3]
    except IndexError:
        extname = ""

    if len(extname) == 0:
        extsep = ""

    i = 0
    while len(str(i)) + 1 <= 7:
        if i > 0:
            maxlen = 8-(1+len(str(i)))
            basename = f"{basename[0:maxlen]}~{i}"

        short_name = f"{basename}{extsep}{extname}"

        if short_name not in dir_entries:
            return short_name
        i += 1

    raise PyFATException("Cannot generate 8dot3 filename, "
                         "unable to find suiting short file name.",
                         errno=errno.EEXIST)


def is_8dot3_conform(entry_name: str):
    """Indicate conformance of given entries name to 8.3 standard.

    :param entry_name: Name of entry to check
    :returns: bool indicating conformance of name to 8.3 standard
    """
    if entry_name != entry_name.upper():
        # Case sensitivity check
        return False

    root, ext = os.path.splitext(entry_name)
    ext = ext[1:]
    if len(root) > 8 and len(ext) > 0:
        return False
    elif len(ext) == 0 and len(root) > 11:
        return False
    elif len(ext) > 3:
        return False

    return True


def make_lfn_entry(dir_name: str, encoding: str = 'ibm437'):
    """Generate a `FATLongDirectoryEntry` instance from directory name.

    :param dir_name: Long name of directory
    :param encoding: Encoding of file name
    :raises PyFATException if entry name does not require an LFN
            entry or the name exceeds the FAT limitation of 255 characters
    """
    lfn_entry = FATLongDirectoryEntry()
    lfn_entry_length = 13
    dir_name = bytearray(dir_name.encode(encoding))
    dir_name_modulus = len(dir_name) % lfn_entry_length
    lfn_dir_name = bytearray()

    if is_8dot3_conform(dir_name.decode(encoding)):
        raise PyFATException("Directory entry is already 8.3 conform, "
                             "no need to create an LFN entry.",
                             errno=errno.EINVAL)

    if len(dir_name) > 255:
        raise PyFATException("Long file name exceeds 255 "
                             "characters, not supported.",
                             errno=errno.ENAMETOOLONG)

    i = 0
    while i < len(dir_name):
        lfn_dir_name.extend([dir_name[i], 0x00])
        i += 1

    if dir_name_modulus == 0:
        # Remove last NULL byte if string evenly fits to LFN entries
        lfn_dir_name = lfn_dir_name[:-1]
    else:
        # Fill the rest with 0xFF if it doesn't fit evenly
        padding = lfn_entry_length - (len(lfn_dir_name) % lfn_entry_length)
        lfn_dir_name.extend([0xFF]*padding)

    # Generate linked LFN entries
    lfn_entries = len(lfn_dir_name) // lfn_entry_length*2
    for i in range(lfn_entries):
        if i == lfn_entries:
            lfn_entry_ord = 0x40
        else:
            lfn_entry_ord = i

        n = i*lfn_entry_length*2
        dirname1 = lfn_dir_name[n:n+10]
        n += 10
        dirname2 = lfn_dir_name[n:n+12]
        n += 12
        dirname3 = lfn_dir_name[n:n+4]
        # TODO: Generate checksum
        lfn_entry.add_lfn_entry(LDIR_Ord=lfn_entry_ord,
                                LDIR_Name1=dirname1,
                                LDIR_Attr=FATDirectoryEntry.ATTR_LONG_NAME,
                                LDIR_Type=0x00,
                                LDIR_Chksum=0x00,
                                LDIR_Name2=dirname2,
                                LDIR_FstClusLO=0,
                                LDIR_Name3=dirname3)
    return lfn_entry
