# -*- coding: utf-8 -*-

"""Tests the FatHeader."""
from collections import OrderedDict

import pytest

from pyfatfs.FATHeader import FATHeader, FAT12Header, FAT32Header

FAT12_HEADER_DATA = b'\x80\x00)\xef\xbe\xad\xdeFAT12TEST  FAT12   '
FAT12_PARSED_HEADER_DATA = OrderedDict({
    "BS_DrvNum": 0x80,
    "BS_Reserved1": 0x00,
    "BS_BootSig": 0x29,
    "BS_VolID": 0xdeadbeef,
    "BS_VolLab": b"FAT12TEST  ",
    "BS_FilSysType": b"FAT12   "
})
FAT16_HEADER_DATA = b'\x80\x00)\xef\xbe\xad\xdeFAT16TEST  FAT16   '
FAT16_PARSED_HEADER_DATA = OrderedDict({
    "BS_DrvNum": 0x80,
    "BS_Reserved1": 0x00,
    "BS_BootSig": 0x29,
    "BS_VolID": 0xdeadbeef,
    "BS_VolLab": b"FAT16TEST  ",
    "BS_FilSysType": b"FAT16   "
})
FAT32_HEADER_DATA = b'\xc1\x0f\x00\x00\x00\x00\x00\x00\x02\x00\x00' \
                    b'\x00\x01\x00\x06\x00\x00\x00\x00\x00\x00\x00' \
                    b'\x00\x00\x00\x00\x00\x00\x80\x00)\xef\xbe\xad' \
                    b'\xdeFAT32TEST  FAT32   '
FAT32_PARSED_HEADER_DATA = OrderedDict({
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
})


def test_base_parse_empty_header():
    """Test that an empty header can be parsed in the base class."""
    fh = FATHeader()
    fh.parse_header(b'')


def test_base_parse_invalid_header():
    """Test that an invalid header leads to an error in the base class."""
    fh = FATHeader()
    with pytest.raises(ValueError):
        fh.parse_header(b'foo')


def test_fat12_parse_fat12_header():
    """Test that a proper FAT12 header can be parsed."""
    fh = FAT12Header()
    fh.parse_header(FAT12_HEADER_DATA)
    assert fh == OrderedDict(FAT12_PARSED_HEADER_DATA)


def test_fat12_parse_fat16_header():
    """Test that a proper FAT16 header can be parsed."""
    fh = FAT12Header()
    fh.parse_header(FAT16_HEADER_DATA)
    assert fh == OrderedDict(FAT16_PARSED_HEADER_DATA)


def test_fat12_serialize_fat12_header():
    """Test that a FAT12 header can be serialized."""
    fh = FAT12Header()
    fh.update(FAT12_PARSED_HEADER_DATA)
    assert bytes(fh) == FAT12_HEADER_DATA


def test_fat12_serialize_fat16_header():
    """Test that a FAT12 header can be serialized."""
    fh = FAT12Header()
    fh.update(FAT16_PARSED_HEADER_DATA)
    assert bytes(fh) == FAT16_HEADER_DATA


def test_fat12_parse_empty_header():
    """Test that an empty header leads to an error in FAT12."""
    fh = FAT12Header()
    with pytest.raises(ValueError):
        fh.parse_header(b'')


def test_fat12_parse_invalid_header():
    """Test that an invalid header leads to an error in FAT12."""
    fh = FAT12Header()
    with pytest.raises(ValueError):
        fh.parse_header(b'foo')


def test_fat12_parse_invalid_header2():
    """Test that an invalid header leads to an error in FAT12."""
    fh = FAT12Header()
    with pytest.raises(ValueError):
        fh.parse_header(FAT32_HEADER_DATA)


def test_fat32_parse_fat32_header():
    """Test that a proper FAT32 header can be parsed."""
    fh = FAT32Header()
    fh.parse_header(FAT32_HEADER_DATA)
    assert fh == OrderedDict(FAT32_PARSED_HEADER_DATA)


def test_fat32_serialize_fat32_header():
    """Test that a FAT32 header can be serialized."""
    fh = FAT32Header()
    fh.update(FAT32_PARSED_HEADER_DATA)
    assert bytes(fh) == FAT32_HEADER_DATA


def test_fat32_parse_empty_header():
    """Test that an empty header leads to an error in FAT32."""
    fh = FAT32Header()
    with pytest.raises(ValueError):
        fh.parse_header(b'')


def test_fat32_parse_invalid_header():
    """Test that an invalid header leads to an error in FAT32."""
    fh = FAT32Header()
    with pytest.raises(ValueError):
        fh.parse_header(b'foo')


def test_fat32_parse_invalid_header2():
    """Test that an invalid header leads to an error in FAT32."""
    fh = FAT32Header()
    with pytest.raises(ValueError):
        fh.parse_header(FAT16_HEADER_DATA)
