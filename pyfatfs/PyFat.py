#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""FAT and BPB parsing for files."""

import errno
import itertools

import math
import struct
import threading
import warnings

from contextlib import contextmanager
from io import BufferedReader, open
from typing import Union

from pyfatfs import FAT_OEM_ENCODING
from pyfatfs.EightDotThree import EightDotThree
from pyfatfs.FATDirectoryEntry import FATDirectoryEntry, FATLongDirectoryEntry
from pyfatfs._exceptions import PyFATException, NotAFatEntryException


def _init_check(func):
    def _wrapper(*args, **kwargs):
        initialised = args[0].initialised

        if initialised is True:
            return func(*args, **kwargs)
        else:
            raise PyFATException("Class has not yet been fully initialised, "
                                 "please instantiate first.")

    return _wrapper


def _readonly_check(func):
    def _wrapper(*args, **kwargs):
        read_only = args[0].is_read_only

        if read_only is False:
            return func(*args, **kwargs)
        else:
            raise PyFATException("Filesystem has been opened read-only, not "
                                 "able to perform a write operation!")

    return _wrapper


class PyFat(object):
    """PyFAT base class, parses generic filesystem information."""

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
                            'MAX_DATA_CLUSTER': 0xFEF,
                            'BAD_CLUSTER': 0xFF7,
                            'END_OF_CLUSTER_MIN': 0xFF8,
                            'END_OF_CLUSTER_MAX': 0xFFF}
    FAT12_SPECIAL_EOC = 0xFF0
    #: Possible cluster values for FAT16 partitions
    FAT16_CLUSTER_VALUES = {'FREE_CLUSTER': 0x0000,
                            'MIN_DATA_CLUSTER': 0x0002,
                            'MAX_DATA_CLUSTER': 0xFFEF,
                            'BAD_CLUSTER': 0xFFF7,
                            'END_OF_CLUSTER_MIN': 0xFFF8,
                            'END_OF_CLUSTER_MAX': 0xFFFF}
    #: Possible cluster values for FAT32 partitions
    FAT32_CLUSTER_VALUES = {'FREE_CLUSTER': 0x0000000,
                            'MIN_DATA_CLUSTER': 0x0000002,
                            'MAX_DATA_CLUSTER': 0x0FFFFFEF,
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
    fat12_header_vars = ["BS_DrvNum", "BS_Reserved1", "BS_BootSig",
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
        """Set up PyFat class instance.

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
        self.first_free_cluster = 0
        self.fat_type = self.FAT_TYPE_UNKNOWN
        self.fat = {}
        self.initialised = False
        self.encoding = encoding
        self.is_read_only = True
        self.__lock = threading.Lock()

    def __set_fp(self, fp):
        if isinstance(self.__fp, BufferedReader):
            raise PyFATException("Cannot overwrite existing file handle, "
                                 "create new class instance of PyFAT.")
        self.__fp = fp

    def __seek(self, address: int):
        """Seek to given address with offset."""
        if self.__fp is None:
            raise PyFATException("Cannot seek without a file handle!",
                                 errno=errno.ENXIO)
        self.__fp.seek(address + self.__fp_offset)

    @_init_check
    def read_cluster_contents(self, cluster: int) -> bytes:
        """Read contents of given cluster.

        :param cluster: Cluster number to read contents from
        :returns: Contents of cluster as `bytes`
        """
        sz = self.bytes_per_cluster
        cluster_address = self.get_data_cluster_address(cluster)
        with self.__lock:
            self.__seek(cluster_address)
            return self.__fp.read(sz)

    def open(self, filename: str, read_only: bool = False):
        """Open filesystem for usage with PyFat.

        :param filename: `str`: Name of file to open for usage with PyFat.
        :param read_only: `bool`: Force read-only mode of filesystem.
        """
        self.is_read_only = read_only
        if read_only is True:
            mode = 'rb'
        else:
            mode = 'rb+'

        try:
            self.__set_fp(open(filename, mode=mode))
        except OSError as ex:
            raise PyFATException(f"Cannot open given file \'{filename}\'.",
                                 errno=ex.errno)

        # Parse BPB & FAT headers of given file
        self.parse_header()

        # Parse FAT
        self._parse_fat()

        # Parse root directory
        # TODO: Inefficient to always recursively parse the root dir.
        #       It would make sense to parse it on demand instead.
        self.parse_root_dir()

    @_init_check
    def get_fs_location(self):
        """Retrieve path of opened filesystem."""
        return self.__fp.name

    @_init_check
    def _get_total_sectors(self):
        """Get total number of sectors for all FAT sizes."""
        if self.bpb_header["BPB_TotSec16"] != 0:
            return self.bpb_header["BPB_TotSec16"]

        return self.bpb_header["BPB_TotSec32"]

    def _get_fat_size_count(self):
        """Get BPB_FATsz value."""
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
        fat_size = self.bpb_header["BPB_BytsPerSec"]
        fat_size *= self._get_fat_size_count()

        # Seek FAT entries
        first_fat_bytes = self.bpb_header["BPB_RsvdSecCnt"]
        first_fat_bytes *= self.bpb_header["BPB_BytsPerSec"]
        fats = []
        for i in range(self.bpb_header["BPB_NumFATS"]):
            with self.__lock:
                self.__seek(first_fat_bytes + (i * fat_size))
                fats += [self.__fp.read(fat_size)]

        if len(fats) < 1:
            raise PyFATException("Invalid number of FATs configured, "
                                 "cannot continue")
        elif len(set(fats)) > 1:
            warnings.warn("One or more FATs differ, filesystem most "
                          "likely corrupted. Using first FAT.")

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
        total_entries = int(fat_size // fat_entry_size)
        self.fat = [None] * total_entries

        curr = 0
        cluster = 0
        incr = self.fat_type / 8
        while curr < fat_size:
            offset = curr + incr

            if self.fat_type == self.FAT_TYPE_FAT12:
                fat_nibble = fats[0][int(curr):math.ceil(offset)]
                fat_nibble = fat_nibble.ljust(2, b"\0")
                try:
                    self.fat[cluster] = struct.unpack("<H", fat_nibble)[0]
                except IndexError:
                    # Out of bounds, FAT size is not cleanly divisible by 3
                    # Do not touch last clusters
                    break

                if cluster % 2 == 0:
                    # Even: Keep low 12-bits of word
                    self.fat[cluster] &= 0x0FFF
                else:
                    # Odd: Keep high 12-bits of word
                    self.fat[cluster] >>= 4

                if math.ceil(offset) == (fat_size - 1):
                    # Sector boundary case for FAT12
                    del self.fat[-1]
                    break

            elif self.fat_type == self.FAT_TYPE_FAT16:
                self.fat[cluster] = struct.unpack("<H",
                                                  fats[0][int(curr):
                                                          int(offset)])[0]
            elif self.fat_type == self.FAT_TYPE_FAT32:
                self.fat[cluster] = struct.unpack("<L",
                                                  fats[0][int(curr):
                                                          int(offset)])[0]
                # Ignore first four bits, FAT32 clusters are
                # actually just 28bits long
                self.fat[cluster] &= 0x0FFFFFFF
            else:
                raise PyFATException("Unknown FAT type, cannot continue")

            curr += incr
            cluster += 1

        if None in self.fat:
            raise AssertionError("Unknown error during FAT parsing, please "
                                 "report this error.")

    @_init_check
    def byte_repr(self) -> bytearray:
        """Represent current state of FAT as bytes.

        :returns: `bytes` representation of FAT.
        """
        b = bytearray(b'')
        if self.fat_type == self.FAT_TYPE_FAT12:
            fat_size = self.bpb_header["BPB_BytsPerSec"]
            fat_size *= self._get_fat_size_count()

            for i, e in enumerate(self.fat):
                if i % 2 == 0:
                    b += struct.pack("<H", e)
                else:
                    nibble = b[-1:]
                    nibble = struct.unpack("<B", nibble)[0]
                    b = b[:-1]
                    b += struct.pack("<BB", ((e & 0xF) << 4) | nibble, e >> 4)

        else:
            if self.fat_type == self.FAT_TYPE_FAT16:
                fmt = "<H"
            else:
                # FAT32
                fmt = "<L"

            for c in self.fat:
                b += struct.pack(fmt, c)
        return b

    @_init_check
    @_readonly_check
    def _write_data_to_address(self, data: bytes,
                               address: int):
        """Write given data directly to the filesystem.

        Directly writes to the filesystem without any consistency check.
        **Use with caution**

        :param data: `bytes`: Data to write to address
        :param address: `int`: Offset to write data to.
        """
        with self.__lock:
            self.__seek(address)
            self.__fp.write(data)

    @_init_check
    @_readonly_check
    def free_cluster_chain(self, cluster: int):
        """Mark a cluster(chain) as free in FAT.

        :param cluster: `int`: Cluster to mark as free
        """
        _freeclus = self.FAT_CLUSTER_VALUES[self.fat_type]['FREE_CLUSTER']
        with self.__lock:
            tmp_fat = self.fat.copy()
            for cl in self.get_cluster_chain(cluster):
                tmp_fat[cl] = _freeclus
                self.first_free_cluster = min(cl, self.first_free_cluster)
            self.fat = tmp_fat

    @_init_check
    @_readonly_check
    def write_data_to_cluster(self, data: bytes,
                              cluster: int,
                              extend_cluster: bool = True,
                              erase: bool = False) -> None:
        """Write given data to cluster.

        Extends cluster chain if needed.

        :param data: `bytes`: Data to write to cluster
        :param cluster: `int`: Cluster to write data to.
        :param extend_cluster: `bool`: Automatically extend cluster chain
                               if not enough space is available.
        :param erase: `bool`: Erase cluster contents before writing.
                      This is useful when writing `FATDirectoryEntry` data.
        """
        data_sz = len(data)
        cluster_sz = 0
        last_cluster = None
        for c in self.get_cluster_chain(cluster):
            cluster_sz += self.bytes_per_cluster
            last_cluster = c
            if cluster_sz >= data_sz:
                break

        if data_sz > cluster_sz:
            if extend_cluster is False:
                raise PyFATException("Cannot write data to cluster, "
                                     "not enough space available.",
                                     errno=errno.ENOSPC)

            new_chain = self.allocate_bytes(data_sz - cluster_sz,
                                            erase=erase)[0]
            self.fat[last_cluster] = new_chain

        # Fill rest of data with zeroes if erase is set to True
        if erase:
            new_sz = max(1, math.ceil(data_sz / self.bytes_per_cluster))
            new_sz *= self.bytes_per_cluster
            data += b'\0' * (new_sz - data_sz)

        # Write actual data
        bytes_written = 0
        for c in self.get_cluster_chain(cluster):
            b = self.get_data_cluster_address(c)
            t = bytes_written
            bytes_written += self.bytes_per_cluster
            self._write_data_to_address(data[t:bytes_written], b)
            if bytes_written >= len(data):
                break

    @_init_check
    @_readonly_check
    def flush_fat(self) -> None:
        """Flush FAT(s) to disk."""
        fat_size = self.bpb_header["BPB_BytsPerSec"]
        fat_size *= self._get_fat_size_count()

        first_fat_bytes = self.bpb_header["BPB_RsvdSecCnt"]
        first_fat_bytes *= self.bpb_header["BPB_BytsPerSec"]

        for i in range(self.bpb_header["BPB_NumFATS"]):
            with self.__lock:
                self.__seek(first_fat_bytes + (i * fat_size))
                self.__fp.write(self.byte_repr())

    def calc_num_clusters(self, size: int = 0) -> int:
        """Calculate the number of required clusters.

        :param size: `int`: required bytes to allocate
        :returns: Number of required clusters
        """
        num_clusters = size / self.bytes_per_cluster
        num_clusters = math.ceil(num_clusters)

        return num_clusters

    @_init_check
    @_readonly_check
    def allocate_bytes(self, size: int, erase: bool = False) -> list:
        """Try to allocate a cluster (-chain) in FAT for `size` bytes.

        :param size: `int`: Size in bytes to try to allocate.
        :param erase: `bool`: If set to true, the newly allocated
                              space is zeroed-out for clean allocation.
        :returns: List of newly-allocated clusters.
        """
        free_clus = self.FAT_CLUSTER_VALUES[self.fat_type]["FREE_CLUSTER"]
        min_clus = self.FAT_CLUSTER_VALUES[self.fat_type]["MIN_DATA_CLUSTER"]
        max_clus = self.FAT_CLUSTER_VALUES[self.fat_type]["MAX_DATA_CLUSTER"]
        num_clusters = self.calc_num_clusters(size)

        # Fill list of found free clusters
        free_clusters = []
        for i in range(self.first_free_cluster, len(self.fat)):
            if min_clus > i or i > max_clus:
                # Ignore out of bound entries
                continue

            if num_clusters == len(free_clusters):
                # Allocated enough clusters!
                break

            if self.fat[i] == free_clus:
                if i == self.FAT_CLUSTER_VALUES[self.fat_type]["BAD_CLUSTER"]:
                    # Do not allocate a BAD_CLUSTER
                    continue

                if self.fat_type == self.FAT_TYPE_FAT12 and \
                        i == self.FAT12_SPECIAL_EOC:
                    # Do not allocate special EOC marker on FAT12
                    continue

                free_clusters += [i]
        else:
            free_space = len(free_clusters) * self.bytes_per_cluster
            raise PyFATException(f"Not enough free space to allocate "
                                 f"{size} bytes ({free_space} bytes free)",
                                 errno=errno.ENOSPC)
        self.first_free_cluster = i

        # Allocate cluster chain in FAT
        eoc_max = self.FAT_CLUSTER_VALUES[self.fat_type]["END_OF_CLUSTER_MAX"]
        for i, _ in enumerate(free_clusters):
            try:
                self.fat[free_clusters[i]] = free_clusters[i+1]
            except IndexError:
                self.fat[free_clusters[i]] = eoc_max

            if erase is True:
                with self.__lock:
                    self.__seek(self.get_data_cluster_address(i))
                    self.__fp.write(b'\0' * self.bytes_per_cluster)

        return free_clusters

    @_init_check
    @_readonly_check
    def update_directory_entry(self, dir_entry: FATDirectoryEntry) -> None:
        """Update directory entry on disk.

        Special handling is required, since the root directory
        on FAT12/16 is on a fixed location on disk.

        :param dir_entry: `FATDirectoryEntry`: Directory to write to disk
        """
        is_root_dir = False
        extend_cluster_chain = True
        if self.root_dir == dir_entry:
            if self.fat_type != self.FAT_TYPE_FAT32:
                # FAT12/16 doesn't have a root directory cluster,
                # which cannot be enhanced
                extend_cluster_chain = False
            is_root_dir = True

        # Gather all directory entries
        dir_entries = b''
        d, f, s = dir_entry.get_entries()
        for d in list(itertools.chain(d, f, s)):
            dir_entries += d.byte_repr()

        # Write content
        if not is_root_dir or self.fat_type == self.FAT_TYPE_FAT32:
            # FAT32 and non-root dir entries can be handled normally
            self.write_data_to_cluster(dir_entries,
                                       dir_entry.get_cluster(),
                                       extend_cluster=extend_cluster_chain,
                                       erase=True)
        else:
            # FAT12/16 does not have a root directory cluster
            root_dir_addr = self.root_dir_sector * \
                self.bpb_header["BPB_BytsPerSec"]
            root_dir_sz = self.root_dir_sectors * \
                self.bpb_header["BPB_BytsPerSec"]

            if len(dir_entries) > root_dir_sz:
                raise PyFATException("Cannot create directory, maximum number "
                                     "of root directory entries exhausted!",
                                     errno=errno.ENOSPC)

            # Overwrite empty space as well
            dir_entries += b'\0' * (root_dir_sz - len(dir_entries))
            self._write_data_to_address(dir_entries, root_dir_addr)

    def _fat12_parse_root_dir(self):
        """Parse FAT12/16 root dir entries.

        FAT12/16 has a fixed location of root directory entries
        and is therefore size limited (BPB_RootEntCnt).
        """
        root_dir_byte = self.root_dir_sector * \
            self.bpb_header["BPB_BytsPerSec"]
        self.root_dir.set_cluster(self.root_dir_sector //
                                  self.bpb_header["BPB_SecPerClus"])
        max_bytes = self.bpb_header["BPB_RootEntCnt"] * \
            FATDirectoryEntry.FAT_DIRECTORY_HEADER_SIZE

        # Parse all directory entries in root directory
        subdirs, _ = self.parse_dir_entries_in_address(root_dir_byte,
                                                       root_dir_byte +
                                                       max_bytes)
        for dir_entry in subdirs:
            self.root_dir.add_subdirectory(dir_entry)

    def _fat32_parse_root_dir(self):
        """Parse FAT32 root dir entries.

        FAT32 actually has its root directory entries distributed
        across a cluster chain that we need to follow
        """
        root_cluster = self.fat_header["BPB_RootClus"]
        self.root_dir.set_cluster(root_cluster)

        # Follow root directory cluster chain
        for dir_entry in self.parse_dir_entries_in_cluster_chain(root_cluster):
            self.root_dir.add_subdirectory(dir_entry)

    def parse_root_dir(self):
        """Parse root directory entry."""
        root_dir_sfn = EightDotThree()
        root_dir_sfn.set_str_name("")
        dir_attr = FATDirectoryEntry.ATTR_DIRECTORY
        self.root_dir = FATDirectoryEntry(DIR_Name=root_dir_sfn,
                                          DIR_Attr=dir_attr,
                                          DIR_NTRes=0,
                                          DIR_CrtTimeTenth=0,
                                          DIR_CrtTime=0,
                                          DIR_CrtDate=0,
                                          DIR_LstAccessDate=0,
                                          DIR_FstClusHI=0,
                                          DIR_WrtTime=0,
                                          DIR_WrtDate=0,
                                          DIR_FstClusLO=0,
                                          DIR_FileSize=0,
                                          encoding=self.encoding)

        if self.fat_type in [self.FAT_TYPE_FAT12, self.FAT_TYPE_FAT16]:
            self._fat12_parse_root_dir()
        else:
            self._fat32_parse_root_dir()

    def parse_lfn_entry(self,
                        lfn_entry: FATLongDirectoryEntry = None,
                        address: int = 0):
        """Parse LFN entry at given address."""
        dir_hdr_sz = FATDirectoryEntry.FAT_DIRECTORY_HEADER_SIZE

        with self.__lock:
            self.__seek(address)
            lfn_dir_data = self.__fp.read(dir_hdr_sz)

        lfn_hdr_layout = FATLongDirectoryEntry.FAT_LONG_DIRECTORY_LAYOUT
        lfn_dir_hdr = struct.unpack(lfn_hdr_layout, lfn_dir_data)
        lfn_dir_hdr = dict(zip(FATLongDirectoryEntry.FAT_LONG_DIRECTORY_VARS,
                               lfn_dir_hdr))

        lfn_entry.add_lfn_entry(**lfn_dir_hdr)

    def __parse_dir_entry(self, address):
        """Parse directory entry at given address."""
        with self.__lock:
            self.__seek(address)
            dir_hdr_size = FATDirectoryEntry.FAT_DIRECTORY_HEADER_SIZE
            dir_data = self.__fp.read(dir_hdr_size)

        dir_hdr = struct.unpack(FATDirectoryEntry.FAT_DIRECTORY_LAYOUT,
                                dir_data)
        dir_hdr = dict(zip(FATDirectoryEntry.FAT_DIRECTORY_VARS, dir_hdr))
        return dir_hdr

    def parse_dir_entries_in_address(self,
                                     address: int = 0,
                                     max_address: int = 0,
                                     tmp_lfn_entry: FATLongDirectoryEntry =
                                     None):
        """Parse directory entries in address range."""
        if tmp_lfn_entry is None:
            tmp_lfn_entry = FATLongDirectoryEntry()

        dir_hdr_size = FATDirectoryEntry.FAT_DIRECTORY_HEADER_SIZE

        if max_address == 0:
            max_address = FATDirectoryEntry.FAT_DIRECTORY_HEADER_SIZE

        dir_entries = []

        for hdr_addr in range(address, max_address, dir_hdr_size):
            # Parse each entry
            dir_hdr = self.__parse_dir_entry(hdr_addr)
            dir_sn = EightDotThree(encoding=self.encoding)
            dir_first_byte = dir_hdr["DIR_Name"][0]
            try:
                dir_sn.set_byte_name(dir_hdr["DIR_Name"])
            except NotAFatEntryException as ex:
                # Not a directory of any kind, invalidate temporary LFN entries
                tmp_lfn_entry = FATLongDirectoryEntry()
                if ex.free_type == ex.FREE_ENTRY:
                    # Empty directory entry,
                    continue
                elif ex.free_type == ex.LAST_ENTRY:
                    # Last directory entry, do not parse any further
                    break
            else:
                dir_hdr["DIR_Name"] = dir_sn

            # Long File Names
            if FATLongDirectoryEntry.is_lfn_entry(dir_first_byte,
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
                cluster = dir_entry.get_cluster()
                subdirs = self.parse_dir_entries_in_cluster_chain(cluster)
                for d in subdirs:
                    dir_entry.add_subdirectory(d)

            # Reset temporary LFN entry
            tmp_lfn_entry = FATLongDirectoryEntry()

        return dir_entries, tmp_lfn_entry

    def parse_dir_entries_in_cluster_chain(self, cluster):
        """Parse directory entries while following given cluster chain."""
        dir_entries = []
        tmp_lfn_entry = FATLongDirectoryEntry()
        max_bytes = (self.bpb_header["BPB_SecPerClus"] *
                     self.bpb_header["BPB_BytsPerSec"])
        for c in self.get_cluster_chain(cluster):
            # Parse all directory entries in chain
            b = self.get_data_cluster_address(c)
            ret = self.parse_dir_entries_in_address(b, b+max_bytes,
                                                    tmp_lfn_entry)
            tmp_dir_entries, tmp_lfn_entry = ret
            dir_entries += tmp_dir_entries

        return dir_entries

    def get_data_cluster_address(self, cluster: int) -> int:
        """Get offset of given cluster in bytes.

        :param cluster: Cluster number as `int`
        :returns: Bytes address location of cluster
        """
        # First two cluster entries are reserved
        sector = (cluster - 2) * self.bpb_header["BPB_SecPerClus"] + \
            self.first_data_sector
        return sector * self.bpb_header["BPB_BytsPerSec"]

    @_init_check
    def get_cluster_chain(self, first_cluster):
        """Follow a cluster chain beginning with the first cluster address."""
        cluster_vals = self.FAT_CLUSTER_VALUES[self.fat_type]
        min_data_cluster = cluster_vals["MIN_DATA_CLUSTER"]
        max_data_cluster = cluster_vals["MAX_DATA_CLUSTER"]
        eoc_min = cluster_vals["END_OF_CLUSTER_MIN"]
        eoc_max = cluster_vals["END_OF_CLUSTER_MAX"]

        i = first_cluster
        while i <= len(self.fat):
            if min_data_cluster <= self.fat[i] <= max_data_cluster:
                # Normal data cluster, follow chain
                yield i
            elif self.fat_type == self.FAT_TYPE_FAT12 and \
                    self.fat[i] == self.FAT12_SPECIAL_EOC:
                # Special EOC
                yield i
                return
            elif eoc_min <= self.fat[i] <= eoc_max:
                # End of cluster, end chain
                yield i
                return
            elif self.fat[i] == cluster_vals["BAD_CLUSTER"]:
                # Bad cluster, cannot follow chain, file broken!
                raise PyFATException("Bad cluster found in FAT cluster "
                                     "chain, cannot access file")
            elif self.fat[i] == cluster_vals["FREE_CLUSTER"]:
                # FREE_CLUSTER mark when following a chain is treated an error
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
        if not self.is_read_only:
            self.flush_fat()

        self.__fp.close()
        self.initialised = False

    def __del__(self):
        """Try to close open handles."""
        try:
            self.close()
        except PyFATException:
            pass

    def __determine_fat_type(self) -> Union["PyFat.FAT_TYPE_FAT12",
                                            "PyFat.FAT_TYPE_FAT16",
                                            "PyFat.FAT_TYPE_FAT32"]:
        """Determine FAT type.

        An internal method to determine whether this volume is FAT12,
        FAT16 or FAT32.

        returns: `str`: Any of PyFat.FAT_TYPE_FAT12, PyFat.FAT_TYPE_FAT16
                 or PyFat.FAT_TYPE_FAT32
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
            msft_fat_type = self.FAT_TYPE_FAT12
        elif count_of_clusters < 65525:
            msft_fat_type = self.FAT_TYPE_FAT16
        else:
            msft_fat_type = self.FAT_TYPE_FAT32

        if self.bpb_header["BPB_FATSz16"] == 0:
            self.__parse_fat32_header()
            if self.fat_header["BPB_FATSz32"] != 0:
                linux_fat_type = self.FAT_TYPE_FAT32
            else:
                self.fat_header = None
                linux_fat_type = msft_fat_type
        elif count_of_clusters >= 4085:
            linux_fat_type = self.FAT_TYPE_FAT16
        else:
            linux_fat_type = self.FAT_TYPE_FAT12

        if msft_fat_type != linux_fat_type:
            warnings.warn(f"Unable to reliably determine FAT type, "
                          f"guessing either FAT{msft_fat_type} or "
                          f"FAT{linux_fat_type}. Opting for "
                          f"FAT{linux_fat_type}.")
        return linux_fat_type

    def __parse_fat12_header(self):
        """Parse FAT12/16 header."""
        with self.__lock:
            self.__seek(0)
            boot_sector = self.__fp.read(512)

        header = struct.unpack(self.fat12_header_layout,
                               boot_sector[36:][:26])
        self.fat_header = dict(zip(self.fat12_header_vars, header))

    def __parse_fat32_header(self):
        """Parse FAT32 header."""
        with self.__lock:
            self.__seek(0)
            boot_sector = self.__fp.read(512)

        header = struct.unpack(self.fat32_header_layout,
                               boot_sector[36:][:54])
        self.fat_header = dict(zip(self.fat32_header_vars, header))

    def parse_header(self):
        """Parse BPB & FAT headers in opened file."""
        with self.__lock:
            self.__seek(0)
            boot_sector = self.__fp.read(512)

        header = struct.unpack(self.bpb_header_layout, boot_sector[:36])
        self.bpb_header = dict(zip(self.bpb_header_vars, header))

        # Verify BPB headers
        self.__verify_bpb_header()

        # Calculate root directory sectors and starting point of root directory
        root_entries = self.bpb_header["BPB_RootEntCnt"]
        hdr_size = FATDirectoryEntry.FAT_DIRECTORY_HEADER_SIZE
        bytes_per_sec = self.bpb_header["BPB_BytsPerSec"]
        rsvd_secs = self.bpb_header["BPB_RsvdSecCnt"]
        num_fats = self.bpb_header["BPB_NumFATS"]

        self.root_dir_sectors = ((root_entries * hdr_size) +
                                 (bytes_per_sec - 1)) // bytes_per_sec
        self.root_dir_sector = rsvd_secs + (self._get_fat_size_count() *
                                            num_fats)

        # Calculate first data sector
        self.first_data_sector = rsvd_secs + (num_fats *
                                              self._get_fat_size_count()) + \
            self.root_dir_sectors

        # Determine FAT type
        self.fat_type = self.__determine_fat_type()

        # Parse FAT type specific header
        if self.fat_type in [self.FAT_TYPE_FAT12, self.FAT_TYPE_FAT16]:
            self.__parse_fat12_header()
        elif self.fat_type == self.FAT_TYPE_FAT32:
            # FAT32, probably - probe for it
            if self.bpb_header["BPB_FATSz16"] != 0:
                raise PyFATException(f"Invalid BPB_FATSz16 value of "
                                     f"'{self.bpb_header['BPB_FATSz16']}', "
                                     f"filesystem corrupt?",
                                     errno=errno.EINVAL)

            self.__parse_fat32_header()
        else:
            raise PyFATException("Unknown FAT filesystem type, "
                                 "filesystem corrupt?", errno=errno.EINVAL)

        # Check signature
        with self.__lock:
            self.__seek(510)
            signature = struct.unpack("<H", self.__fp.read(2))[0]

        if signature != 0xAA55:
            raise PyFATException(f"Invalid signature: \'{hex(signature)}\'.")

        # Initialisation finished
        self.initialised = True

    def __verify_bpb_header(self):
        """Verify BPB header for correctness."""
        if self.bpb_header["BS_jmpBoot"][0] == 0xEB:
            if self.bpb_header["BS_jmpBoot"][2] != 0x90:
                raise PyFATException("Boot code must end with 0x90")
        elif self.bpb_header["BS_jmpBoot"][0] == 0xE9:
            pass
        else:
            raise PyFATException("Boot code must start with 0xEB or "
                                 "0xE9. Is this a FAT partition?")

        #: 512,1024,2048,4096: As per fatgen103.doc
        byts_per_sec_range = [2**x for x in range(9, 13)]
        if self.bpb_header["BPB_BytsPerSec"] not in byts_per_sec_range:
            raise PyFATException(f"Expected one of {byts_per_sec_range} "
                                 f"bytes per sector, got: "
                                 f"\'{self.bpb_header['BPB_BytsPerSec']}\'.")

        #: 1,2,4,8,16,32,64,128: As per fatgen103.doc
        sec_per_clus_range = [2**x for x in range(8)]
        if self.bpb_header["BPB_SecPerClus"] not in sec_per_clus_range:
            raise PyFATException(f"Expected one of {sec_per_clus_range} "
                                 f"sectors per cluster, got: "
                                 f"\'{self.bpb_header['BPB_SecPerClus']}\'.")

        bytes_per_cluster = self.bpb_header["BPB_BytsPerSec"]
        bytes_per_cluster *= self.bpb_header["BPB_SecPerClus"]
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

        root_entry_count = self.bpb_header["BPB_RootEntCnt"] * 32
        root_entry_count %= self.bpb_header["BPB_BytsPerSec"]
        if self.bpb_header["BPB_RootEntCnt"] != 0 and root_entry_count != 0:
            raise PyFATException("Root entry count does not cleanly align with"
                                 " bytes per sector!")

        if self.bpb_header["BPB_TotSec16"] == 0 and \
                self.bpb_header["BPB_TotSec32"] == 0:
            raise PyFATException("16-Bit and 32-Bit total sector count "
                                 "value empty.")

    @staticmethod
    @contextmanager
    def open_fs(filename: str, offset: int = 0,
                encoding=FAT_OEM_ENCODING):
        """Context manager for direct use of PyFAT."""
        pf = PyFat(encoding=encoding, offset=offset)
        pf.open(filename)
        yield pf
        pf.close()
