# -*- coding: utf-8 -*-

"""FAT header specific implementation for FAT12/16 and FAT32."""

import struct
from collections import OrderedDict


class FATHeader(OrderedDict):
    """Base/Interface class for FAT header implementation."""

    HEADER_LAYOUT = ""
    HEADER_VARS = []

    def __init__(self):
        """Initialize an empty FAT header."""
        super().__init__()
        self.update(dict.fromkeys(self.HEADER_VARS))

    def __bytes__(self):
        """Serialize header data back to bytes."""
        return struct.pack(self.HEADER_LAYOUT, *self.values())

    def parse_header(self, data: bytes):
        """Parse header data from bytes.

        :param data: `bytes`: Raw header data from disk
        """
        if len(data) != struct.calcsize(self.HEADER_LAYOUT):
            raise ValueError("Invalid FAT header data supplied")

        header = struct.unpack(self.HEADER_LAYOUT,
                               data)
        self.update(dict(zip(self.HEADER_VARS, header)))


class FAT12Header(FATHeader):
    """FAT12/16-specific header implementation."""

    #: FAT12/16 header layout in struct formatted string
    HEADER_LAYOUT = "<BBBL11s8s"
    #: FAT12/16 header fields when extracted with fat12_header_layout
    HEADER_VARS = ["BS_DrvNum", "BS_Reserved1", "BS_BootSig", "BS_VolID",
                   "BS_VolLab", "BS_FilSysType"]


class FAT32Header(FATHeader):
    """FAT32-specific header implementation."""

    #: FAT32 header layout in struct formatted string
    HEADER_LAYOUT = "<LHHLHH12sBBBL11s8s"
    #: FAT32 header fields when extracted with fat32_header_layout
    HEADER_VARS = ["BPB_FATSz32", "BPB_ExtFlags", "BPB_FSVer", "BPB_RootClus",
                   "BPB_FSInfo", "BPB_BkBootSec", "BPB_Reserved", "BS_DrvNum",
                   "BS_Reserved1", "BS_BootSig", "BS_VolID", "BS_VolLab",
                   "BS_FilSysType"]
