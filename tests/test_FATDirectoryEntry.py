# -*- coding: utf-8 -*-

"""Tests the FATDirectoryEntry module."""
import random
import string
from unittest import mock

import pytest

from pyfat.FATDirectoryEntry import FATDirectoryEntry, is_8dot3_conform, \
    make_8dot3_name, calculate_checksum


def test_invalid_dirname():
    """Test that invalid directory names are correctly detected."""
    with pytest.raises(NotADirectoryError):
        FATDirectoryEntry(DIR_Name=b'\x00',
                          DIR_Attr=FATDirectoryEntry.ATTR_DIRECTORY,
                          DIR_NTRes="0",
                          DIR_CrtTimeTenth="0",
                          DIR_CrtDateTenth="0",
                          DIR_LstAccessDate="0",
                          DIR_FstClusHI="0",
                          DIR_WrtTime="0",
                          DIR_WrtDate="0",
                          DIR_FstClusLO="0",
                          DIR_FileSize="0",
                          encoding="ibm437")


def test_checksum_calculation_precalculated():
    """Test that the checksum calculation works, with a precalculated value."""
    assert calculate_checksum(b'FILENAMETXT') == 58


def test_checksum_calculation_referenceimpl():
    """Test that the checksum calculation works, following reference impl.

    This is taken from the Microsoft Extensible Firmware Initiative
    FAT32 File System Spec v1.03.

    .. code-block:
       short FcbNameLen;
       unsigned char Sum;

       Sum = 0;
       for (FcbNameLen=11; FcbNameLen!=0; FcbNameLen--) {
           Sum = ((Sum & 1) ? 0x80 : 0) + (Sum >> 1) + *pFcbName++;
       }

    """
    fname = b'FILENAMETXT'

    s = 0
    for i in range(0, 11):
        s = (0x80 if (s & 1) == 1 else 0x0) + (s >> 1) + fname[i]
        s &= 0xFF

    assert calculate_checksum(fname) == s


def test_checksum_calculation_referenceimpl_random():
    """Test that the checksum calculation works, following reference impl.

    This is taken from the Microsoft Extensible Firmware Initiative
    FAT32 File System Spec v1.03 and uses random data.

    .. code-block:
       short FcbNameLen;
       unsigned char Sum;

       Sum = 0;
       for (FcbNameLen=11; FcbNameLen!=0; FcbNameLen--) {
           Sum = ((Sum & 1) ? 0x80 : 0) + (Sum >> 1) + *pFcbName++;
       }

    """
    fname = ''.join(random.choices(string.ascii_letters + string.digits,
                                   k=11)).upper().encode('ASCII')

    s = 0
    for i in range(0, 11):
        s = (0x80 if (s & 1) == 1 else 0x0) + (s >> 1) + fname[i]
        s &= 0xFF

    assert calculate_checksum(fname) == s


def test_make_8dot3_name():
    """Test that make_8dot3_filename generates valid 8dot3 filenames."""
    fde = mock.MagicMock()
    fde.get_entries.return_value = ([], [], [])
    lfn = make_8dot3_name("This is a long filename.txt", fde)
    assert "THIS IS .TXT" == lfn
    assert is_8dot3_conform(lfn)


def test_make_8dot3_name_cut_ext():
    """Test that make_8dot3_filename generates valid 8dot3 filenames."""
    fde = mock.MagicMock()
    fde.get_entries.return_value = ([], [], [])
    lfn = make_8dot3_name("This is a long filename.TeXT", fde)
    assert "THIS IS .TEX" == lfn
    assert is_8dot3_conform(lfn)


def test_make_8dot3_name_noext():
    """Test that make_8dot3_filename generates valid 8dot3 filenames."""
    fde = mock.MagicMock()
    fde.get_entries.return_value = ([], [], [])
    lfn = make_8dot3_name("This is a long filename", fde)
    assert "THIS IS " == lfn
    assert is_8dot3_conform(lfn)


def test_make_8dot3_name_emptyext():
    """Test that make_8dot3_filename generates valid 8dot3 filenames."""
    fde = mock.MagicMock()
    fde.get_entries.return_value = ([], [], [])
    lfn = make_8dot3_name("This is a long filename.", fde)
    assert "THIS IS " == lfn
    assert is_8dot3_conform(lfn)


def test_make_8dot3_name_collision():
    """Test that make_8dot3_filename generates valid 8dot3 filenames."""
    fde = mock.MagicMock()
    fde_sub = mock.MagicMock()
    fde_sub.get_short_name.side_effect = ["THIS IS .TXT", "THIS I~1.TXT",
                                          "THIS I~2.TXT"]
    fde.get_entries.return_value = ([fde_sub, fde_sub], [fde_sub], [])
    lfn = make_8dot3_name("This is a long filename.txt", fde)
    assert "THIS I~3.TXT" == lfn
    assert is_8dot3_conform(lfn)


def test_is_8dot3_conform_true():
    """Test that 8.3 file names are correctly detected."""
    assert is_8dot3_conform("TESTFILE.TXT")


def test_is_8dot3_conform_false():
    """Test that non-8.3 file names are correctly detected."""
    assert not is_8dot3_conform("This is a Long file.txt")


def test_is_8dot3_conform_noext_true():
    """Test that 8.3 file names without extension are correctly detected."""
    assert is_8dot3_conform("88888888333")


def test_is_8dot3_conform_noext_false():
    """Test that 8.3 file names without extension are correctly detected."""
    assert not is_8dot3_conform("88888888333_")
