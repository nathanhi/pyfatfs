# -*- coding: utf-8 -*-

"""Tests the FATDirectoryEntry module."""

import datetime
import errno

import pytest
from pyfatfs import PyFATException
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


def test_get_entries_raw():
    """Test that _get_entries_raw returns an unsorted list of entries."""
    tz = datetime.timezone.utc
    rootdir = FATDirectoryEntry.new(name="rootdir", tz=tz, encoding='ASCII',
                                    attr=FATDirectoryEntry.ATTR_DIRECTORY)
    entries = [("1", FATDirectoryEntry.ATTR_READ_ONLY),
               ("3", 0),
               ("2", FATDirectoryEntry.ATTR_DIRECTORY),
               ("a", 0),
               ("4", FATDirectoryEntry.ATTR_DIRECTORY),
               ("11", FATDirectoryEntry.ATTR_SYSTEM)]
    for (name, attr) in entries:
        rootdir.add_subdirectory(FATDirectoryEntry.new(name, tz=tz,
                                                       encoding='ASCII',
                                                       attr=attr))

    i = 0
    for e in rootdir._get_entries_raw():
        assert e.name == entries[i][0]
        assert e.attr == entries[i][1]
        i += 1


def test_walk():
    """Test that walk behaves like os.walk."""
    tz = datetime.timezone.utc
    sfn = EightDotThree()
    sfn.initialized = True
    sfn.name = b"ROOTDIR"
    rootdir = FATDirectoryEntry.new(name=sfn, tz=tz, encoding='ASCII',
                                    attr=FATDirectoryEntry.ATTR_DIRECTORY)
    entries = [(b".", 0),
               (b"..", 0),
               (b"1", FATDirectoryEntry.ATTR_READ_ONLY),
               (b"3", 0),
               (b"2", FATDirectoryEntry.ATTR_DIRECTORY),
               (b"a", 0),
               (b"4", FATDirectoryEntry.ATTR_DIRECTORY),
               (b"11", FATDirectoryEntry.ATTR_SYSTEM)]

    # Build directory tree
    for (name, attr) in entries:
        sfn = EightDotThree()
        sfn.initialized = True
        sfn.name = name
        dentry = FATDirectoryEntry.new(sfn, tz=tz,
                                       encoding='ASCII',
                                       attr=attr)
        if attr == FATDirectoryEntry.ATTR_DIRECTORY:
            for (subname, subattr) in entries:
                if entries == FATDirectoryEntry.ATTR_DIRECTORY:
                    continue
                sfn = EightDotThree()
                sfn.initialized = True
                sfn.name = subname
                subdentry = FATDirectoryEntry.new(sfn, tz=tz,
                                                  encoding='ASCII',
                                                  attr=subattr)
                dentry.add_subdirectory(subdentry)
        rootdir.add_subdirectory(dentry)

    roots = [b"/",
             b"ROOTDIR/2", b"ROOTDIR/2/2", b"ROOTDIR/2/4",
             b"ROOTDIR/4", b"ROOTDIR/4/2", b"ROOTDIR/4/4"]
    dirs = [[b"2", b"4"], [b"2", b"4"], [], [], [b"2", b"4"], [], []]
    files = [[b"1", b"3", b"a", b"11"],
             [b"1", b"3", b"a", b"11"],
             [], [],
             [b"1", b"3", b"a", b"11"],
             [], []]
    for _root, _dirs, _files in rootdir.walk():
        assert _root.encode('ASCII') == roots[0]
        roots.pop(0)
        for i, d in enumerate(dirs[0]):
            assert bytes(_dirs[i].name) == d
        dirs.pop(0)
        for i, f in enumerate(files[0]):
            assert bytes(_files[i].name) == f
        files.pop(0)


def test_filesize_2big_new():
    """Verify that file size is boundary checked in constructor."""
    tz = datetime.timezone.utc
    dentry_name = EightDotThree()
    dentry_name.set_str_name("FOO")
    dentry = FATDirectoryEntry.new(name=dentry_name, tz=tz, encoding='ASCII',
                                   filesize=0xefbeadde)
    assert dentry.filesize == 0xefbeadde
    assert bytes(dentry)[-4:] == b'\xde\xad\xbe\xef'

    with pytest.raises(PyFATException) as e:
        FATDirectoryEntry.new(name=dentry_name, tz=tz, encoding='ASCII',
                              filesize=FATDirectoryEntry.MAX_FILE_SIZE+1)
    assert e.value.errno == errno.E2BIG


def test_filesize_2big_set():
    """Verify that file size is boundary checked in constructor."""
    tz = datetime.timezone.utc
    dentry_name = EightDotThree()
    dentry_name.set_str_name("FOO")
    dentry = FATDirectoryEntry.new(name=dentry_name, tz=tz,
                                   encoding='ASCII', filesize=1)
    with pytest.raises(PyFATException) as e:
        dentry.filesize = FATDirectoryEntry.MAX_FILE_SIZE+1
    assert e.value.errno == errno.E2BIG
    assert dentry.filesize == 1
    assert bytes(dentry)[-4:] == b'\x01\x00\x00\x00'

    dentry.filesize = FATDirectoryEntry.MAX_FILE_SIZE
    assert dentry.filesize == FATDirectoryEntry.MAX_FILE_SIZE
    assert bytes(dentry)[-4:] == b'\xff\xff\xff\xff'
