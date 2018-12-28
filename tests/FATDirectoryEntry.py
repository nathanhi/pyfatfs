#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest

from pyfat.FATDirectoryEntry import FATDirectoryEntry


class TestFATDirectoryEntry:
    def test_invalid_dirname(self):
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
                              encoding="ibm437",
                              lfn_entry=None)
