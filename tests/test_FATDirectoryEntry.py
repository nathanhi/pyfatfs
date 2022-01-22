# -*- coding: utf-8 -*-

"""Tests the FATDirectoryEntry module."""

import datetime

from pyfatfs.EightDotThree import EightDotThree
from pyfatfs.FATDirectoryEntry import FATDirectoryEntry


def test_bytes_0xe5():
    """Test that 0xE5 (Kanji lead byte) is properly serialized as 0x05."""
    sfn = EightDotThree(encoding='MS-Kanji')
    sfn.set_str_name("褪せる褪")
    assert str(sfn) == "褪せる褪"
    dentry = FATDirectoryEntry.new(name=sfn, tz=datetime.timezone.utc,
                                   encoding='MS-Kanji')
    assert bytes(dentry)[:2] == b'\xe5\xf2'
    assert bytes(dentry)[:8][-2:] == b'\xe5\xf2'
    assert str(dentry) == "褪せる褪"
