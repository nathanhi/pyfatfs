# -*- coding: utf-8 -*-

"""Tests the FATDirectoryEntry module."""

from unittest import mock

import pytest

from pyfat.FATDirectoryEntry import FATDirectoryEntry, is_8dot3_conform,\
    make_8dot3_name


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
