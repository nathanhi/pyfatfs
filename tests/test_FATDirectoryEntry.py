# -*- coding: utf-8 -*-

"""Tests the FATDirectoryEntry module."""
import datetime

from pyfatfs.EightDotThree import EightDotThree
from pyfatfs.FATDirectoryEntry import FATDirectoryEntry


def test_bytes_0xe5():
    """Test that 0xE5 (Kanji lead byte) is properly converted to 0x05."""
    sfn = EightDotThree(encoding='MS-Kanji')
    sfn.set_str_name("褪せる 褪")
    dentry = FATDirectoryEntry.new(name=sfn, tz=datetime.timezone.utc,
                                   encoding='MS-Kanji')
    assert bytes(dentry)[:2] == b'\x05\xf2'
    assert bytes(dentry)[:9][-2:] == b'\xe5\xf2'
