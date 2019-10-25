#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import math
import struct
import warnings

from contextlib import contextmanager
from os import PathLike
from io import BufferedReader, open

from pyfat.FATDirectoryEntry import FATDirectoryEntry, FATLongDirectoryEntry
from pyfat._exceptions import PyFATException


def _init_check(func):
    def _wrapper(*args, **kwargs):
        initialised = args[0].initialised

        if initialised is True:
            return func(*args, **kwargs)
        else:
            raise PyFATException(
                "Class has not yet been fully initialised, "
                "please instantiate first.")

    return _wrapper


class PyFat(object):
    """ PyFAT base class, parses generic filesystem information.
    """
    #: Used as fat_type if unable to detect FAT type
    FAT_TYPE_UNKNOWN = 0
    #: Used as fat_type if FAT12 fs has been detected
    FAT_TYPE_FAT12 = 12
    #: Used as fat_type if FAT16 fs has been detected
    FAT_TYPE_FAT16 = 16
    #: Used as fat_type if FAT32 fs has been detected
    FAT_TYPE_FAT32 = 32

    #: Maps fat_type to BS_FilSysType from FS header information
    FS_TYPES = {FAT_TYPE_UNKNOWN: b"FAT     ",
                FAT_TYPE_FAT12: b"FAT12   ",
                FAT_TYPE_FAT16: b"FAT16   ",
                FAT_TYPE_FAT32: b"FAT32   "}

    #: Possible cluster values for FAT12 partitions
    FAT12_CLUSTER_VALUES = {'FREE_CLUSTER': 0x000,
                            'MIN_DATA_CLUSTER': 0x002,
                            'MAX_DATA_CLUSTER': 0xFF5,
                            'BAD_CLUSTER': 0xFF7,
                            'END_OF_CLUSTER_MIN': 0xFF8,
                            'END_OF_CLUSTER_MAX': 0xFFF}
    FAT12_SPECIAL_EOC = 0xFF0
    #: Possible cluster values for FAT16 partitions
    FAT16_CLUSTER_VALUES = {'FREE_CLUSTER': 0x0000,
                            'MIN_DATA_CLUSTER': 0x0002,
                            'MAX_DATA_CLUSTER': 0xFFF5,
                            'BAD_CLUSTER': 0xFFF7,
                            'END_OF_CLUSTER_MIN': 0xFFF8,
                            'END_OF_CLUSTER_MAX': 0xFFFF}
    #: Possible cluster values for FAT32 partitions
    FAT32_CLUSTER_VALUES = {'FREE_CLUSTER': 0x0000000,
                            'MIN_DATA_CLUSTER': 0x0000002,
                            'MAX_DATA_CLUSTER': 0xFFFFFF5,
                            'BAD_CLUSTER': 0xFFFFFF7,
                            'END_OF_CLUSTER_MIN': 0xFFFFFF8,
                            'END_OF_CLUSTER_MAX': 0xFFFFFFF}
    #: Maps fat_type to possible cluster values
    FAT_CLUSTER_VALUES = {FAT_TYPE_FAT12: FAT12_CLUSTER_VALUES,
                          FAT_TYPE_FAT16: FAT16_CLUSTER_VALUES,
                          FAT_TYPE_FAT32: FAT32_CLUSTER_VALUES}

    #: BPB header layout in struct formatted string
    bpb_header_layout = "<3s8sHBHBHHBHHHLL"
    #: BPB header fields when extracted with bpb_header_layout
    bpb_header_vars = ["BS_jmpBoot", "BS_OEMName", "BPB_BytsPerSec",
                       "BPB_SecPerClus", "BPB_RsvdSecCnt", "BPB_NumFATS",
                       "BPB_RootEntCnt", "BPB_TotSec16", "BPB_Media",
                       "BPB_FATSz16", "BPB_SecPerTrk", "BPB_NumHeads",
                       "BPB_HiddSec", "BPB_TotSec32"]

    #: FAT12/16 header layout in struct formatted string
    fat12_header_layout = "<BBBL11s8s"
    #: FAT12/16 header fields when extracted with fat12_header_layout
    fat12_header_vars = ["BPB_DrvNum", "BS_Reserved1", "BS_BootSig",
                         "BS_VolID", "BS_VolLab", "BS_FilSysType"]

    #: FAT32 header layout in struct formatted string
    fat32_header_layout = "<LHHLHH12sBBBL11s8s"
    #: FAT32 header fields when extracted with fat32_header_layout
    fat32_header_vars = ["BPB_FATSz32", "BPB_ExtFlags", "BPB_FSVer",
                         "BPB_RootClus", "BPB_FSInfo", "BPB_BkBootSec",
                         "BPB_Reserved", "BS_DrvNum", "BS_Reserved1",
                         "BS_BootSig", "BS_VolID", "BS_VolLab",
                         "BS_FilSysType"]

    #: FAT12/16 bit mask for clean shutdown bit
    FAT12_CLEAN_SHUTDOWN_BIT_MASK = 0x8000
    #: FAT12/16 bit mask for volume error bit
    FAT12_DRIVE_ERROR_BIT_MASK = 0x4000
    #: FAT32 bit mask for clean shutdown bit
    FAT32_CLEAN_SHUTDOWN_BIT_MASK = 0x0800000
    #: FAT32 bit mask for volume error bit
    FAT32_DRIVE_ERROR_BIT_MASK = 0x0400000

    def __init__(self,
                 encoding: str = 'ibm437',
                 offset: int = 0):
        """PyFAT main class.
        :param encoding: Define encoding to use for filenames
        :param offset: Offset of the FAT partition in the given file
        :type encoding: str
        :type offset: int
        """
        self.__fp = None
        self.__fp_offset = offset
        self.bpb_header = None
        self.fat_header = None
        self.root_dir = None
        self.root_dir_sector = 0
        self.root_dir_sectors = 0
        self.bytes_per_cluster = 0
        self.first_data_sector = 0
        self.fat_type = self.FAT_TYPE_UNKNOWN
        self.fat = {}
        self.initialised = False
        self.fat_clusterchains = {}
        self.encoding = encoding

    def __set_fp(self, fp):
        if isinstance(self.__fp, BufferedReader):
            raise PyFATException("Cannot overwrite existing file handle, "
                                 "create new class instance of PyFAT.")
        self.__fp = fp

    def __seek(self, address: int):
        """Seek to given address with offset."""
        if self.__fp is None:
            raise PyFATException("Cannot seek without a file handle!")
        self.__fp.seek(address + self.__fp_offset)

    def open(self, filename):
        try:
            self.__set_fp(open(filename, 'rb'))
        except OSError as e:
            raise PyFATException("Cannot open given "
                                 "file \'{}\' ({})".format(filename, e.errno))

        # Parse BPB & FAT headers of given file
        self.parse_header()

        # Parse FAT
        self._parse_fat()

        # Parse root directory
        self.parse_root_dir()

    @_init_check
    def _get_total_sectors(self):
        """Get total number of sectors for all FAT sizes."""
        if self.bpb_header["BPB_TotSec16"] != 0:
            return self.bpb_header["BPB_TotSec16"]

        return self.bpb_header["BPB_TotSec32"]

    def _get_fat_size_count(self):
        if self.bpb_header["BPB_FATSz16"] != 0:
            return self.bpb_header["BPB_FATSz16"]

        # Only possible with FAT32
        self.__parse_fat32_header()
        try:
            return self.fat_header["BPB_FATSz32"]
        except KeyError:
            raise PyFATException("Invalid FAT size of 0 detected in header, "
                                 "cannot continue")

    @_init_check
    def _parse_fat(self):
        """Parse information in FAT."""
        # Read all FATs
        fat_size = self.bpb_header["BPB_BytsPerSec"] * self._get_fat_size_count()

        # Seek FAT entries
        first_fat_bytes = self.bpb_header["BPB_RsvdSecCnt"] * self.bpb_header["BPB_BytsPerSec"]
        fats = []
        for i in range(self.bpb_header["BPB_NumFATS"]):
            self.__seek(first_fat_bytes + (i * fat_size))
            fats += [self.__fp.read(fat_size)]

        if len(fats) < 1:
            raise PyFATException("Invalid number of FATs configured, "
                                 "cannot continue")
        elif len(set(fats)) > 1:
            raise PyFATException("One or more FATs differ, filesystem most "
                                 "likely corrupted")

        # Parse first FAT
        self.bytes_per_cluster = self.bpb_header["BPB_BytsPerSec"] * \
            self.bpb_header["BPB_SecPerClus"]

        if len(fats[0]) != self.bpb_header["BPB_BytsPerSec"] * \
                self._get_fat_size_count():
            raise PyFATException("Invalid length of FAT")

        # FAT12: 12 bits (1.5 bytes) per FAT entry
        # FAT16: 16 bits (2 bytes) per FAT entry
        # FAT32: 32 bits (4 bytes) per FAT entry
        fat_entry_size = self.fat_type / 8
        total_entries = fat_size // int(fat_entry_size)
        self.fat = [None] * total_entries

        curr = 0
        cluster = 0
        incr = -(-self.fat_type // 8)
        while curr < fat_size:
            offset = int(curr + incr)

            if self.fat_type == self.FAT_TYPE_FAT12:
                if curr == (fat_size-1):
                    # Sector boundary case for FAT12
                    del self.fat[-1]
                    break

                self.fat[cluster] = struct.unpack("<H", fats[0][curr:offset])[0]
                if curr % 2 == 0:
                    # Even: Only fetch low 12 bits
                    self.fat[cluster] &= 0x0FFF
                else:
                    # Odd: Only fetch high 12 bits
                    self.fat[cluster] >>= 4
            elif self.fat_type == self.FAT_TYPE_FAT16:
                self.fat[cluster] = struct.unpack("<H", fats[0][curr:offset])[0]
            elif self.fat_type == self.FAT_TYPE_FAT32:
                self.fat[cluster] = struct.unpack("<L", fats[0][curr:offset])[0]
                # Ignore first four bits, FAT32 clusters are
                # actually just 28bits long
                self.fat[cluster] &= 0x0FFFFFFF
            else:
                raise PyFATException("Unknown FAT type, cannot continue")

            curr += int(fat_entry_size)
            cluster += 1

        assert None not in self.fat

    @_init_check
    def allocate_bytes(self, size: int):
        """Allocate cluster in FAT."""
        # Calculate number of clusters required for file
        num_clusters = size / self.bytes_per_cluster
        num_clusters = math.ceil(num_clusters)

        # Fill list of found free clusters
        free_clusters = []
        for i in range(0, len(self.fat)):
            if self.FAT_CLUSTER_VALUES[self.fat_type]["MIN_DATA_CLUSTER"] > i > self.FAT_CLUSTER_VALUES[self.fat_type]["MAX_DATA_CLUSTER"]:
                # Ignore out of bound entries
                continue

            if num_clusters == len(free_clusters):
                # Allocated enough clusters!
                break

            if self.fat[i] == self.FAT_CLUSTER_VALUES[self.fat_type]["FREE_CLUSTER"]:
                if i == self.FAT_CLUSTER_VALUES[self.fat_type]["BAD_CLUSTER"]:
                    # Do not allocate a BAD_CLUSTER
                    continue

                if self.fat_type == self.FAT_TYPE_FAT12 and i == self.FAT12_SPECIAL_EOC:
                    # Do not allocate special EOC marker on FAT12
                    continue

                free_clusters += [i]
        else:
            free_space = len(free_clusters) * self.bytes_per_cluster
            raise PyFATException(f"Not enough free space to allocate {size} bytes ({free_space} bytes free)")

        # Allocate cluster chain in FAT
        for i in range(0, len(free_clusters)):
            try:
                self.fat[free_clusters[i]] = free_clusters[i+1]
            except IndexError:
                self.fat[free_clusters[i]] = self.FAT_CLUSTER_VALUES[self.fat_type]["END_OF_CLUSTER_MAX"]

        # TODO: Write FAT to disk
        pass

        return free_clusters

    def _fat12_parse_root_dir(self):
        """Parses the FAT12/16 root dir entries.
        FAT12/16 has a fixed location of root directory entries
        and is therefore size limited (BPB_RootEntCnt).
        """
        root_dir_byte = self.root_dir_sector * self.bpb_header["BPB_BytsPerSec"]
        root_dir_entry = FATDirectoryEntry(DIR_Name="/",
                                           DIR_Attr=FATDirectoryEntry.ATTR_DIRECTORY,
                                           DIR_NTRes=0,
                                           DIR_CrtTimeTenth=0,
                                           DIR_CrtDateTenth=0,
                                           DIR_LstAccessDate=0,
                                           DIR_FstClusHI=0,
                                           DIR_WrtTime=0,
                                           DIR_WrtDate=0,
                                           DIR_FstClusLO=0,
                                           DIR_FileSize=0,
                                           encoding=self.encoding)
        root_dir_entry.set_cluster(self.root_dir_sector // self.bpb_header["BPB_SecPerClus"])
        max_bytes = self.bpb_header["BPB_RootEntCnt"] * FATDirectoryEntry.FAT_DIRECTORY_HEADER_SIZE

        # Parse all directory entries in root directory
        subdirs, _ = self.parse_dir_entries_in_address(root_dir_byte, root_dir_byte + max_bytes)
        for dir_entry in subdirs:
            root_dir_entry.add_subdirectory(dir_entry)

        return root_dir_entry

    def _fat32_parse_root_dir(self):
        """Parses the FAT32 root dir entries.
        FAT32 actually has its root directory entries distributed
        across a cluster chain that we need to follow
        """
        root_dir_entry_cluster = self.fat_header["BPB_RootClus"]
        root_dir_entry = FATDirectoryEntry("/",
                                           FATDirectoryEntry.ATTR_DIRECTORY,
                                           "0", "0", "0", "0", "0", "0", "0",
                                           self.fat_header["BPB_RootClus"],
                                           "0", encoding=self.encoding)

        # Follow root directory cluster chain
        for dir_entry in self.parse_dir_entries_in_cluster_chain(root_dir_entry_cluster):
            root_dir_entry.add_subdirectory(dir_entry)

        return root_dir_entry

    def parse_root_dir(self):
        """Parses root directory entry."""
        if self.fat_type in [self.FAT_TYPE_FAT12, self.FAT_TYPE_FAT16]:
            self.root_dir = self._fat12_parse_root_dir()
        else:
            self.root_dir = self._fat32_parse_root_dir()

    def parse_lfn_entry(self,
                        lfn_entry: FATLongDirectoryEntry = None,
                        address: int = 0):
        """Parse LFN entry at given address."""
        dir_hdr_sz = FATDirectoryEntry.FAT_DIRECTORY_HEADER_SIZE

        self.__seek(address)
        lfn_dir_data = self.__fp.read(dir_hdr_sz)

        lfn_dir_hdr = struct.unpack(FATLongDirectoryEntry.FAT_LONG_DIRECTORY_LAYOUT, lfn_dir_data)
        lfn_dir_hdr = dict(zip(FATLongDirectoryEntry.FAT_LONG_DIRECTORY_VARS, lfn_dir_hdr))

        lfn_entry.add_lfn_entry(**lfn_dir_hdr)

    def __parse_dir_entry(self, address):
        """Parse directory entry at given address."""
        self.__seek(address)
        dir_data = self.__fp.read(FATDirectoryEntry.FAT_DIRECTORY_HEADER_SIZE)
        dir_hdr = struct.unpack(FATDirectoryEntry.FAT_DIRECTORY_LAYOUT,
                                dir_data)
        dir_hdr = dict(zip(FATDirectoryEntry.FAT_DIRECTORY_VARS, dir_hdr))
        return dir_hdr

    def parse_dir_entries_in_address(self,
                                     address: int = 0,
                                     max_address: int = 0,
                                     tmp_lfn_entry: FATLongDirectoryEntry = FATLongDirectoryEntry()):
        """Parses directory entries in address range."""
        dir_hdr_size = FATDirectoryEntry.FAT_DIRECTORY_HEADER_SIZE

        if max_address == 0:
            max_address = FATDirectoryEntry.FAT_DIRECTORY_HEADER_SIZE

        dir_entries = []

        for hdr_addr in range(address, max_address, dir_hdr_size):
            # Parse each entry
            dir_hdr = self.__parse_dir_entry(hdr_addr)

            if dir_hdr["DIR_Name"][0] == 0x0 or dir_hdr["DIR_Name"][0] == 0xE5:
                # Empty directory entry, ignore and reset LFN entries
                tmp_lfn_entry = FATLongDirectoryEntry()
                continue

            # Long File Names
            if FATLongDirectoryEntry.is_lfn_entry(dir_hdr["DIR_Name"],
                                                  dir_hdr["DIR_Attr"]):
                self.parse_lfn_entry(tmp_lfn_entry, hdr_addr)
                continue

            # Normal directory entries
            if not tmp_lfn_entry.is_lfn_entry_complete():
                # Ignore incomplete LFN entries altogether
                tmp_lfn_entry = None

            dir_entry = FATDirectoryEntry(encoding=self.encoding,
                                          lfn_entry=tmp_lfn_entry,
                                          **dir_hdr)
            dir_entries += [dir_entry]

            if dir_entry.is_directory() and not dir_entry.is_special():
                # Iterate all subdirectories except for dot and dotdot
                subdirs = self.parse_dir_entries_in_cluster_chain(dir_entry.get_cluster())
                for d in subdirs:
                    dir_entry.add_subdirectory(d)

            # Reset temporary LFN entry
            tmp_lfn_entry = FATLongDirectoryEntry()

        return dir_entries, tmp_lfn_entry

    def parse_dir_entries_in_cluster_chain(self, cluster):
        """Parses directory entries while following given cluster chain."""
        dir_entries = []
        tmp_lfn_entry = FATLongDirectoryEntry()
        max_bytes = (self.bpb_header["BPB_SecPerClus"] * self.bpb_header["BPB_BytsPerSec"])
        for b in self.get_cluster_chain(cluster):
            # Parse all directory entries in chain
            tmp_dir_entries, tmp_lfn_entry = self.parse_dir_entries_in_address(b, b+max_bytes, tmp_lfn_entry)
            dir_entries += tmp_dir_entries

        return dir_entries

    @_init_check
    def get_cluster_chain(self, first_cluster):
        """Follow a cluster chain beginning with the first cluster address."""
        i = first_cluster
        while i <= len(self.fat):
            # First two cluster entries are reserved
            first_sector_of_cluster = int((i-2) * self.bpb_header["BPB_SecPerClus"] + self.first_data_sector)
            address = first_sector_of_cluster * self.bpb_header["BPB_BytsPerSec"]
            if self.FAT_CLUSTER_VALUES[self.fat_type]["MIN_DATA_CLUSTER"] <= self.fat[i] <= self.FAT_CLUSTER_VALUES[self.fat_type]["MAX_DATA_CLUSTER"]:
                # Normal data cluster, follow chain
                yield address
            elif self.fat_type == self.FAT_TYPE_FAT12 and self.fat[i] == self.FAT12_SPECIAL_EOC:
                # Special EOC
                yield address
                return
            elif self.FAT_CLUSTER_VALUES[self.fat_type]["END_OF_CLUSTER_MIN"] <= self.fat[i] <= self.FAT_CLUSTER_VALUES[self.fat_type]["END_OF_CLUSTER_MAX"]:
                # End of cluster, end chain
                yield address
                return
            elif self.fat[i] == self.FAT_CLUSTER_VALUES[self.fat_type]["BAD_CLUSTER"]:
                # Bad cluster, cannot follow chain, file broken!
                raise PyFATException("Bad cluster found in FAT cluster "
                                     "chain, cannot access file")
            elif self.fat[i] == self.FAT_CLUSTER_VALUES[self.fat_type]["FREE_CLUSTER"]:
                # FREE_CLUSTER mark when following a chain is treated as an error
                raise PyFATException("FREE_CLUSTER mark found in FAT cluster "
                                     "chain, cannot access file")
            else:
                raise PyFATException("Invalid or unknown FAT cluster "
                                     "entry found with value "
                                     "\'{}\'".format(hex(self.fat[i])))

            i = self.fat[i]

    @_init_check
    def close(self):
        """Close session and free up all handles."""
        self.__fp.close()
        self.initialised = False

    def __del__(self):
        try:
            self.close()
        except PyFATException:
            pass

    def __determine_fat_type(self):
        """Determine FAT size

        An internal method to determine whether this volume is FAT12, FAT16
        or FAT32
        """

        if self.bpb_header["BPB_TotSec16"] != 0:
            total_sectors = self.bpb_header["BPB_TotSec16"]
        else:
            total_sectors = self.bpb_header["BPB_TotSec32"]

        rsvd_sectors = self.bpb_header["BPB_RsvdSecCnt"]
        fat_sz = self.bpb_header["BPB_NumFATS"] * self._get_fat_size_count()
        root_dir_sectors = self.root_dir_sectors
        data_sec = total_sectors - (rsvd_sectors + fat_sz + root_dir_sectors)
        count_of_clusters = data_sec // self.bpb_header["BPB_SecPerClus"]

        if count_of_clusters < 4085:
            fat_type = self.FAT_TYPE_FAT12
        elif count_of_clusters < 65525:
            fat_type = self.FAT_TYPE_FAT16
        else:
            fat_type = self.FAT_TYPE_FAT32

        return fat_type

    def __parse_fat12_header(self):
        """Parse FAT12/16 header"""
        self.__seek(0)
        boot_sector = self.__fp.read(512)
        header = struct.unpack(self.fat12_header_layout,
                               boot_sector[36:][:26])
        self.fat_header = dict(zip(self.fat12_header_vars, header))

    def __parse_fat32_header(self):
        """Parse FAT32 header."""
        self.__seek(0)
        boot_sector = self.__fp.read(512)
        header = struct.unpack(self.fat32_header_layout,
                               boot_sector[36:][:54])
        self.fat_header = dict(zip(self.fat32_header_vars, header))

    def parse_header(self):
        self.__seek(0)
        boot_sector = self.__fp.read(512)

        header = struct.unpack(self.bpb_header_layout, boot_sector[:36])
        self.bpb_header = dict(zip(self.bpb_header_vars, header))

        # Verify BPB headers
        self.__verify_bpb_header()

        # Calculate number of root directory sectors and starting point of root directory
        self.root_dir_sectors = ((self.bpb_header["BPB_RootEntCnt"] * FATDirectoryEntry.FAT_DIRECTORY_HEADER_SIZE) + (self.bpb_header["BPB_BytsPerSec"] - 1)) // self.bpb_header["BPB_BytsPerSec"]
        self.root_dir_sector = self.bpb_header["BPB_RsvdSecCnt"] + (self._get_fat_size_count() * self.bpb_header["BPB_NumFATS"])

        # Calculate first data sector
        self.first_data_sector = self.bpb_header["BPB_RsvdSecCnt"] + (self.bpb_header["BPB_NumFATS"] * self._get_fat_size_count()) + self.root_dir_sectors

        # Determine FAT type
        self.fat_type = self.__determine_fat_type()

        # Parse FAT type specific header
        if self.fat_type in [self.FAT_TYPE_FAT12, self.FAT_TYPE_FAT16]:
            self.__parse_fat12_header()

            self.__verify_fat12_header()
        else:
            # FAT32, probably - probe for it
            # TODO: Verify that BPB_FATSz16 is 0
            self.__parse_fat32_header()

            # TODO: Verify FAT32 header

        # Check signature
        self.__seek(510)
        signature = struct.unpack("<H", self.__fp.read(2))[0]

        if signature != 0xAA55:
            raise PyFATException("Invalid signature")

        # Initialisation finished
        self.initialised = True

    def __verify_fat12_header(self):
        """Verify FAT12/16 header for correctness."""
        if self.fat_type == self.FAT_TYPE_FAT12 and self.fat_header[
            "BS_FilSysType"] not in [self.FS_TYPES[self.FAT_TYPE_UNKNOWN],
                                     self.FS_TYPES[self.FAT_TYPE_FAT12]]:
            raise PyFATException("Invalid filesystem type \'{}\' "
                                 "for FAT12".format(self.fat_type))
        elif self.fat_type == self.FAT_TYPE_FAT16 and self.fat_header[
            "BS_FilSysType"] not in [self.FS_TYPES[self.FAT_TYPE_UNKNOWN],
                                     self.FS_TYPES[self.FAT_TYPE_FAT16]]:
            raise PyFATException("Invalid filesystem type \'{}\' "
                                 "for FAT16".format(self.fat_type))

        if self.fat_header["BPB_DrvNum"] not in [0x00, 0x80]:
            raise PyFATException("Invalid drive number \'"
                                 "{}\'".format(self.fat_header["BPB_DrvNum"]))

    def __verify_bpb_header(self):
        """Verify BPB header for correctness."""
        if self.bpb_header["BS_jmpBoot"][0] == 0xEB:
            if self.bpb_header["BS_jmpBoot"][2] != 0x90:
                raise PyFATException("Boot code must end with 0x90")
        elif self.bpb_header["BS_jmpBoot"][0] == 0xE9:
            pass
        else:
            raise PyFATException("Boot code must start with 0xEB or 0xE9. Is this a FAT partition?")

        if self.bpb_header["BPB_BytsPerSec"] not in [2**x for x in range(9, 13)]:
            raise PyFATException("Expected one of {} bytes per sector, got: "
                                 "\'{}\'.".format([2**x for x in range(9, 13)],
                                                  self.bpb_header[
                                                      "BPB_BytsPerSec"]))

        if self.bpb_header["BPB_SecPerClus"] not in [2**x for x in range(8)]:
            raise PyFATException("Expected one of {} sectors per cluster, got"
                                 ": \'{}\'.".format([2**x for x in range(8)],
                                                    self.bpb_header[
                                                        "BPB_SecPerClus"]))

        bytes_per_cluster = self.bpb_header["BPB_BytsPerSec"] * self.bpb_header["BPB_SecPerClus"]
        if bytes_per_cluster > 32768:
            warnings.warn("Bytes per cluster should not be more than 32K, "
                          "but got: {}K. Trying to continue "
                          "anyway.".format(bytes_per_cluster // 1024), Warning)

        if self.bpb_header["BPB_RsvdSecCnt"] == 0:
            raise PyFATException("Number of reserved sectors must not be 0")

        if self.bpb_header["BPB_Media"] not in [0xf0, 0xf8, 0xf9, 0xfa, 0xfb,
                                                0xfc, 0xfd, 0xfe, 0xff]:
            raise PyFATException("Invalid media type")

        if self.bpb_header["BPB_NumFATS"] < 1:
            raise PyFATException("At least one FAT expected, None found.")

        root_entry_count = (self.bpb_header["BPB_RootEntCnt"] * 32) % self.bpb_header["BPB_BytsPerSec"]
        if self.bpb_header["BPB_RootEntCnt"] != 0 and root_entry_count != 0:
            raise PyFATException("Root entry count does not cleanly align with"
                                 " bytes per sector!")

        if self.bpb_header["BPB_TotSec16"] == 0 and self.bpb_header["BPB_TotSec32"] == 0:
            raise PyFATException("16-Bit and 32-Bit total sector count "
                                 "value empty.")

    @staticmethod
    @contextmanager
    def open_fs(filename: PathLike, offset: int = 0,
                encoding="ibm437"):
        """Context manager for direct use of PyFAT."""
        pf = PyFat(encoding=encoding, offset=offset)
        pf.open(filename)
        yield pf
        pf.close()
