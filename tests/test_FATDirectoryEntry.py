# -*- coding: utf-8 -*-

import pytest

from pyfat.FATDirectoryEntry import FATDirectoryEntry, is_8dot3_conform


def test_invalid_dirname():
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


def test_is_8dot3_conform_true():
    """Test that 8.3 file names are correctly detected."""
    assert is_8dot3_conform("TESTFILE.TXT")


def test_is_8dot3_conform_false():
    """Test that non-8.3 file names are correctly detected."""
    assert not is_8dot3_conform("This is a Long file.txt")
