# -*- coding: utf-8 -*-

"""Tests the BootSectorHeader."""
from collections import OrderedDict

import pytest

from pyfatfs.BootSectorHeader import \
    BootSectorHeader, FAT12BootSectorHeader, FAT32BootSectorHeader

BOOTSECTOR_COMMON_PARSED_DATA = OrderedDict({
    "BS_jmpBoot": bytearray([0xEB, 0x33, 0x90]),
    "BS_OEMName": b"foo     ",
    "BPB_BytsPerSec": 0x42,
    "BPB_SecPerClus": 0x43,
    "BPB_RsvdSecCnt": 0x44,
    "BPB_NumFATs": 0x45,
    "BPB_RootEntCnt": 0x46,
    "BPB_TotSec16": 0x47,
    "BPB_Media": 0x48,
    "BPB_FATSz16": 0x49,
    "BPB_SecPerTrk": 0x50,
    "BPB_NumHeads": 0x51,
    "BPB_HiddSec": 0x52,
    "BPB_TotSec32": 0x53,
})

BOOTSECTOR_COMMON_DATA_HEADER = \
     b'\xEB\x33\x90foo     \x42\x00\x43\x44\x00\x45' \
     b'\x46\x00\x47\x00\x48\x49\x00\x50\x00\x51\x00' \
     b'\x52\x00\x00\x00\x53\x00\x00\x00'


BOOTSECTOR12_HEADER_DATA = BOOTSECTOR_COMMON_DATA_HEADER + b'\x80\x00)' \
                           b'\xef\xbe\xad\xdeFAT12TEST  FAT12   '

BOOTSECTOR12_PARSED_HEADER_DATA = OrderedDict(
    list(BOOTSECTOR_COMMON_PARSED_DATA.items()) +
    list(OrderedDict({
        "BS_DrvNum": 0x80,
        "BS_Reserved1": 0x00,
        "BS_BootSig": 0x29,
        "BS_VolID": 0xdeadbeef,
        "BS_VolLab": b"FAT12TEST  ",
        "BS_FilSysType": b"FAT12   "
    }).items()))
BOOTSECTOR16_HEADER_DATA = BOOTSECTOR_COMMON_DATA_HEADER + b'\x80\x00)' \
                           b'\xef\xbe\xad\xdeFAT16TEST  FAT16   '
BOOTSECTOR16_PARSED_HEADER_DATA = OrderedDict(
    list(BOOTSECTOR_COMMON_PARSED_DATA.items()) +
    list(OrderedDict({
        "BS_DrvNum": 0x80,
        "BS_Reserved1": 0x00,
        "BS_BootSig": 0x29,
        "BS_VolID": 0xdeadbeef,
        "BS_VolLab": b"FAT16TEST  ",
        "BS_FilSysType": b"FAT16   "
    }).items()))
BOOTSECTOR32_HEADER_DATA = BOOTSECTOR_COMMON_DATA_HEADER + b'\xc1\x0f\x00' \
                           b'\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01\x00' \
                           b'\x06\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
                           b'\x00\x00\x00\x80\x00)\xef\xbe\xad'            \
                           b'\xdeFAT32TEST  FAT32   '
BOOTSECTOR32_PARSED_HEADER_DATA = OrderedDict(
    list(BOOTSECTOR_COMMON_PARSED_DATA.items()) +
    list(OrderedDict({
        'BPB_FATSz32': 4033,
        'BPB_ExtFlags': 0x00,
        'BPB_FSVer': 0x00,
        'BPB_RootClus': 2,
        'BPB_FSInfo': 1,
        'BPB_BkBootSec': 6,
        'BPB_Reserved': b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        'BS_DrvNum': 0x80,
        'BS_Reserved1': 0x00,
        'BS_BootSig': 0x29,
        'BS_VolID': 0xdeadbeef,
        'BS_VolLab': b'FAT32TEST  ',
        'BS_FilSysType': b'FAT32   '
    }).items()))


def test_base_parse_invalid_header():
    """Test that an invalid header leads to an error in the base class."""
    fh = BootSectorHeader()
    with pytest.raises(ValueError):
        fh.parse_header(b'foo')


def test_fat12_parse_fat12_header():
    """Test that a proper FAT12 header can be parsed."""
    fh = FAT12BootSectorHeader()
    fh.parse_header(BOOTSECTOR12_HEADER_DATA)
    assert fh == OrderedDict(BOOTSECTOR12_PARSED_HEADER_DATA)


def test_fat12_parse_fat16_header():
    """Test that a proper FAT16 header can be parsed."""
    fh = FAT12BootSectorHeader()
    fh.parse_header(BOOTSECTOR16_HEADER_DATA)
    assert fh == OrderedDict(BOOTSECTOR16_PARSED_HEADER_DATA)


def test_fat12_serialize_fat12_header():
    """Test that a FAT12 header can be serialized."""
    fh = FAT12BootSectorHeader()
    fh.update(BOOTSECTOR12_PARSED_HEADER_DATA)
    assert bytes(fh) == BOOTSECTOR12_HEADER_DATA


def test_fat12_serialize_fat16_header():
    """Test that a FAT12 header can be serialized."""
    fh = FAT12BootSectorHeader()
    fh.update(BOOTSECTOR16_PARSED_HEADER_DATA)
    assert bytes(fh) == BOOTSECTOR16_HEADER_DATA


def test_fat12_parse_empty_header():
    """Test that an empty header leads to an error in FAT12."""
    fh = FAT12BootSectorHeader()
    with pytest.raises(ValueError):
        fh.parse_header(b'')


def test_fat12_parse_invalid_header():
    """Test that an invalid header leads to an error in FAT12."""
    fh = FAT12BootSectorHeader()
    with pytest.raises(ValueError):
        fh.parse_header(b'foo')


def test_fat32_parse_fat32_header():
    """Test that a proper FAT32 header can be parsed."""
    fh = FAT32BootSectorHeader()
    fh.parse_header(BOOTSECTOR32_HEADER_DATA)
    assert fh == OrderedDict(BOOTSECTOR32_PARSED_HEADER_DATA)


def test_fat32_serialize_fat32_header():
    """Test that a FAT32 header can be serialized."""
    fh = FAT32BootSectorHeader()
    fh.update(BOOTSECTOR32_PARSED_HEADER_DATA)
    assert bytes(fh) == BOOTSECTOR32_HEADER_DATA


def test_fat32_parse_empty_header():
    """Test that an empty header leads to an error in FAT32."""
    fh = FAT32BootSectorHeader()
    with pytest.raises(ValueError):
        fh.parse_header(b'')


def test_fat32_parse_invalid_header():
    """Test that an invalid header leads to an error in FAT32."""
    fh = FAT32BootSectorHeader()
    with pytest.raises(ValueError):
        fh.parse_header(b'foo')


def test_fat32_parse_invalid_header2():
    """Test that an invalid header leads to an error in FAT32."""
    fh = FAT32BootSectorHeader()
    with pytest.raises(ValueError):
        fh.parse_header(BOOTSECTOR16_HEADER_DATA)
