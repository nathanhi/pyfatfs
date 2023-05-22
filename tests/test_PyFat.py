# -*- coding: utf-8 -*-

"""Test PyFat core functionality."""
import datetime
import errno
from io import BytesIO
from unittest import mock

import pyfatfs
import pytest

from pyfatfs import PyFATException
from pyfatfs.FATDirectoryEntry import FATDirectoryEntry
from pyfatfs.PyFat import PyFat


def test_set_fp_bytesio():
    """Test that BytesIO can be set via PyFat.set_fp."""
    pf = PyFat(encoding='UTF-8')
    in_memory_fs = BytesIO(b'\0' * 4 * 1024 * 1024)
    pf._PyFat__fp = in_memory_fs
    with mock.patch('pyfatfs.PyFat.PyFat._PyFat__set_fp',
                    mock.Mock()):
        with mock.patch('pyfatfs.PyFat.open'):
            pf.mkfs("/this/does/not/exist.img",
                    fat_type=PyFat.FAT_TYPE_FAT12,
                    label="FOOBARBAZ",
                    size=1024 * 1024 * 4)

    pf2 = PyFat()
    in_memory_fs.seek(0)
    pf2.set_fp(BytesIO(in_memory_fs.read()))
    assert isinstance(pf2.root_dir, FATDirectoryEntry)
    assert pf2.bpb_header["BS_VolLab"] == b'FOOBARBAZ  '


def test_set_fp_twice():
    """Test that set_fp cannot be called twice per instance."""
    pf = PyFat(encoding='UTF-8')
    in_memory_fs = BytesIO(b'\0' * 4 * 1024 * 1024)
    pf._PyFat__fp = in_memory_fs
    with mock.patch('pyfatfs.PyFat.PyFat._PyFat__set_fp',
                    mock.Mock()):
        with mock.patch('pyfatfs.PyFat.open'):
            pf.mkfs("/this/does/not/exist.img",
                    fat_type=PyFat.FAT_TYPE_FAT12,
                    label="FOOBARBAZ",
                    size=1024 * 1024 * 4)

    in_memory_fs.seek(0)
    with pytest.raises(PyFATException) as e:
        pf.set_fp(BytesIO(in_memory_fs.read()))
    assert e.value.errno == errno.EMFILE


def test_set_fp_unreadable():
    """Test that files marked as unreadable cannot be opened."""
    pf = PyFat()
    fp = mock.Mock()
    fp.readable.return_value = False
    with pytest.raises(PyFATException) as e:
        pf.set_fp(fp)
    assert e.value.errno == errno.EACCES


def test_set_fp_unseekable():
    """Test that files marked as unseekable cannot be opened."""
    pf = PyFat()
    fp = mock.Mock()
    fp.readable.return_value = True
    fp.seekable.return_value = False
    with pytest.raises(PyFATException) as e:
        pf.set_fp(fp)
    assert e.value.errno == errno.EINVAL


def test_open_mode_readonly():
    """Verify rb mode if readonly on open()."""
    pf = PyFat()
    with mock.patch('pyfatfs.PyFat.PyFat.set_fp'):
        with mock.patch('pyfatfs.PyFat.open') as mock_open:
            pf.open("foo", read_only=True)
    mock_open.assert_called_once_with("foo", mode="rb")


def test_open_mode_readwrite():
    """Verify rb+ mode if readonly=False on open()."""
    pf = PyFat()
    with mock.patch('pyfatfs.PyFat.PyFat.set_fp'):
        with mock.patch('pyfatfs.PyFat.open') as mock_open:
            pf.open("foo", read_only=False)
    mock_open.assert_called_once_with("foo", mode="rb+")


def test_is_dirty_fat12_not_dirty():
    """Test that is_dirty is affected by nt_dirty."""
    pf = PyFat()
    pf.fat_type = pf.FAT_TYPE_FAT12
    pf.fat = [0xFF8, 0xFFF]
    pf.bpb_header = {"BS_Reserved1": 0x0}
    assert not pf._is_dirty()


def test_is_dirty_fat12_dirty_nt():
    """Test that is_dirty is only affected by nt_dirty."""
    pf = PyFat()
    pf.fat_type = pf.FAT_TYPE_FAT12
    pf.fat = [0xFF8, 0x000]
    pf.bpb_header = {"BS_Reserved1": 0x1}
    assert pf._is_dirty()


def test_is_dirty_fat16_not_dirty():
    """Test that is_dirty detects that a volume has been cleanly shut down."""
    pf = PyFat()
    pf.fat_type = pf.FAT_TYPE_FAT16
    pf.fat = [0xFFF8, 0xFFFF]
    pf.bpb_header = {"BS_Reserved1": 0x0}
    assert not pf._is_dirty()


def test_is_dirty_fat16_dirty_dos():
    """Test that is_dirty detects dirty bit set by DOS."""
    pf = PyFat()
    pf.fat_type = pf.FAT_TYPE_FAT16
    pf.fat = [0xFFF8, 0x7FFF]
    pf.bpb_header = {"BS_Reserved1": 0x0}
    assert pf._is_dirty()


def test_is_dirty_fat16_dirty_dos2():
    """Test that is_dirty detects dirty bit set by DOS."""
    pf = PyFat()
    pf.fat_type = pf.FAT_TYPE_FAT16
    pf.fat = [0xFFF8, 0x7ABC]
    pf.bpb_header = {"BS_Reserved1": 0x0}
    assert pf._is_dirty()


def test_is_dirty_fat16_dirty_dos3():
    """Test that is_dirty detects dirty bit set by DOS."""
    pf = PyFat()
    pf.fat_type = pf.FAT_TYPE_FAT16
    pf.fat = [0xFFF8, 0x0ABC]
    pf.bpb_header = {"BS_Reserved1": 0x0}
    assert pf._is_dirty()


def test_is_dirty_fat16_dirty_nt():
    """Test that is_dirty detects dirty bit set by NT."""
    pf = PyFat()
    pf.fat_type = pf.FAT_TYPE_FAT12
    pf.fat = [0xFFF8, 0xFFFF]
    pf.bpb_header = {"BS_Reserved1": 0x1}
    assert pf._is_dirty()


def test_is_dirty_fat16_dirty_both():
    """Test that is_dirty detects dirty bit set by both DOS and NT."""
    pf = PyFat()
    pf.fat_type = pf.FAT_TYPE_FAT16
    pf.fat = [0xFFF8, 0x7FFF]
    pf.bpb_header = {"BS_Reserved1": 0x1}
    assert pf._is_dirty()


def test_is_dirty_fat32_not_dirty():
    """Test that is_dirty detects that a volume has been cleanly shut down."""
    pf = PyFat()
    pf.fat_type = pf.FAT_TYPE_FAT32
    pf.fat = [0xFFFFFF8, 0xFFFFFFF]
    pf.bpb_header = {"BS_Reserved1": 0x0}
    assert not pf._is_dirty()


def test_is_dirty_fat32_dirty_dos():
    """Test that is_dirty detects dirty bit set by DOS."""
    pf = PyFat()
    pf.fat_type = pf.FAT_TYPE_FAT32
    pf.fat = [0xFFFFFF8, 0x7FFFFFF]
    pf.bpb_header = {"BS_Reserved1": 0x0}
    assert pf._is_dirty()


def test_is_dirty_fat32_dirty_nt():
    """Test that is_dirty detects dirty bit set by NT."""
    pf = PyFat()
    pf.fat_type = pf.FAT_TYPE_FAT32
    pf.fat = [0xFFFFFF8, 0xFFFFFFF]
    pf.bpb_header = {"BS_Reserved1": 0x1}
    assert pf._is_dirty()


def test_is_dirty_fat32_dirty_both():
    """Test that is_dirty detects dirty bit set by both DOS and NT."""
    pf = PyFat()
    pf.fat_type = pf.FAT_TYPE_FAT32
    pf.fat = [0xFFFFFF8, 0xF7FFFFF]
    pf.bpb_header = {"BS_Reserved1": 0x1}
    assert pf._is_dirty()


def test_mark_dirty_fat12():
    """Test that _mark_dirty is able to mark partition as dirty."""
    pf = PyFat()
    pf.fat_type = pf.FAT_TYPE_FAT12
    fat_orig = [0xFF8, 0xFFF]
    pf.fat = list(fat_orig)
    pf.bpb_header = {"BS_Reserved1": 0x0}
    with mock.patch('pyfatfs.PyFat.PyFat.flush_fat') as ff:
        with mock.patch('pyfatfs.PyFat.PyFat._write_bpb_header'):
            pf._mark_dirty()
            assert pf.fat == fat_orig
            assert pf.bpb_header["BS_Reserved1"] == 0x1
            assert ff.call_count == 0


def test_mark_dirty_fat16():
    """Test that _mark_dirty is able to mark partition as dirty."""
    pf = PyFat()
    pf.fat_type = pf.FAT_TYPE_FAT16
    fat_orig = [0xFFF8, 0xFFFF]
    pf.fat = list(fat_orig)
    pf.bpb_header = {"BS_Reserved1": 0x0}
    with mock.patch('pyfatfs.PyFat.PyFat.flush_fat') as ff:
        with mock.patch('pyfatfs.PyFat.PyFat._write_bpb_header'):
            pf._mark_dirty()
            assert pf.fat[1] == 0x7FFF
            assert pf.bpb_header["BS_Reserved1"] == 0x1
            assert ff.call_count == 1


def test_mark_dirty_fat32():
    """Test that _mark_dirty is able to mark partition as dirty."""
    pf = PyFat()
    pf.fat_type = pf.FAT_TYPE_FAT32
    fat_orig = [0xFFFFFF8, 0xFFFFFFF]
    pf.fat = list(fat_orig)
    pf.bpb_header = {"BS_Reserved1": 0x0}
    with mock.patch('pyfatfs.PyFat.PyFat.flush_fat') as ff:
        with mock.patch('pyfatfs.PyFat.PyFat._write_bpb_header'):
            pf._mark_dirty()
            assert pf.fat[1] == 0x7FFFFFF
            assert pf.bpb_header["BS_Reserved1"] == 0x1
            assert ff.call_count == 1


def test_mark_clean_fat12():
    """Test that _mark_clean is able to mark partition as clean."""
    pf = PyFat()
    pf.fat_type = pf.FAT_TYPE_FAT12
    fat_orig = [0xFF8, 0xFFF]
    pf.fat = list(fat_orig)
    pf.bpb_header = {"BS_Reserved1": 0x1}
    with mock.patch('pyfatfs.PyFat.PyFat.flush_fat') as ff:
        with mock.patch('pyfatfs.PyFat.PyFat._write_bpb_header'):
            pf._mark_clean()
            assert pf.fat == fat_orig
            assert pf.bpb_header["BS_Reserved1"] == 0x0
            assert ff.call_count == 0


def test_mark_clean_fat16():
    """Test that _mark_clean is able to mark partition as clean."""
    pf = PyFat()
    pf.fat_type = pf.FAT_TYPE_FAT16
    pf.fat = [0xFFF8, 0x0ABC]
    pf.bpb_header = {"BS_Reserved1": 0x1}
    with mock.patch('pyfatfs.PyFat.PyFat.flush_fat') as ff:
        with mock.patch('pyfatfs.PyFat.PyFat._write_bpb_header'):
            pf._mark_clean()
            assert pf.fat[1] == 0x8ABC
            assert pf.bpb_header["BS_Reserved1"] == 0x0
            assert ff.call_count == 1


def test_mark_clean_fat32():
    """Test that _mark_clean is able to mark partition as clean."""
    pf = PyFat()
    pf.fat_type = pf.FAT_TYPE_FAT32
    pf.fat = [0xFFFFFF8, 0x5ADBEEF]
    pf.bpb_header = {"BS_Reserved1": 0x1}
    with mock.patch('pyfatfs.PyFat.PyFat.flush_fat') as ff:
        with mock.patch('pyfatfs.PyFat.PyFat._write_bpb_header'):
            pf._mark_clean()
            assert pf.fat[1] == 0xDADBEEF
            assert pf.bpb_header["BS_Reserved1"] == 0x0
            assert ff.call_count == 1


def test_mkfs_no_size():
    """Test size detection of mkfs."""
    pf = PyFat()
    part_sz = 1024 * 1024
    in_memory_fs = BytesIO(b'\0' * part_sz)
    pf._PyFat__fp = in_memory_fs
    with mock.patch('pyfatfs.PyFat.PyFat._PyFat__set_fp',
                    mock.Mock()):
        with mock.patch('pyfatfs.PyFat.open'):
            pf.mkfs("/this/does/not/exist.img",
                    fat_type=PyFat.FAT_TYPE_FAT12,
                    label="FAT12TST")
            pf.flush_fat()

    in_memory_fs.seek(0)


def test___seek_no_fp():
    """Make sure __seek() without a file handle is not possible."""
    pf = PyFat()
    with pytest.raises(PyFATException) as e:
        pf._PyFat__seek(1234)
    assert e.value.errno == errno.ENXIO


def test__get_fat_size_count_fat1216():
    """Verify the correct FATSz is returned on FAT12/16."""
    pf = PyFat()
    pf.bpb_header = {}
    pf.bpb_header["BPB_FATSz16"] = 1234
    assert pf._get_fat_size_count() == 1234
    pf.bpb_header["BPB_FATSz32"] = 5678
    assert pf._get_fat_size_count() == 1234


def test__get_fat_size_count_fat32():
    """Verify the correct FATSz is returned on FAT32."""
    pf = PyFat()
    pf.bpb_header = {}
    pf.bpb_header["BPB_FATSz16"] = 0
    pf.bpb_header["BPB_FATSz32"] = 42
    assert pf._get_fat_size_count() == 42
    del pf.bpb_header["BPB_FATSz32"]
    with pytest.raises(PyFATException):
        pf._get_fat_size_count()


def test_get_fs_location():
    """Verify that the file pointer is properly queried for location."""
    pf = PyFat()
    pf._PyFat__fp = mock.Mock()
    pf._PyFat__fp.name = "/foo"
    pf.initialized = True
    assert pf.get_fs_location() == "/foo"
    pf.initialized = False
    with pytest.raises(PyFATException):
        pf.get_fs_location()


def test_allocate_bytes_readonly():
    """Test that allocate_bytes cannot be called on read-only FS."""
    pf = PyFat()
    pf.initialized = True
    pf.is_read_only = True
    with pytest.raises(PyFATException) as e:
        pf.allocate_bytes(0)
    assert e.value.errno == errno.EROFS


def test_flush_fat_readonly():
    """Test that flush_fat cannot be called on read-only FS."""
    pf = PyFat()
    pf.initialized = True
    pf.is_read_only = True
    with pytest.raises(PyFATException) as e:
        pf.flush_fat()
    assert e.value.errno == errno.EROFS


def test_free_cluster_chain_readonly():
    """Test that free_cluster_chain cannot be called on read-only FS."""
    pf = PyFat()
    pf.initialized = True
    pf.is_read_only = True
    with pytest.raises(PyFATException) as e:
        pf.free_cluster_chain(4711)
    assert e.value.errno == errno.EROFS


def test_update_directory_entry_readonly():
    """Test that update_directory_entry cannot be called on read-only FS."""
    pf = PyFat()
    pf.initialized = True
    pf.is_read_only = True
    dentry = FATDirectoryEntry.new(name="foo",
                                   tz=datetime.timezone.utc,
                                   encoding=pyfatfs.FAT_OEM_ENCODING)
    with pytest.raises(PyFATException) as e:
        pf.update_directory_entry(dentry)
    assert e.value.errno == errno.EROFS


def test_write_data_to_cluster_readonly():
    """Test that write_data_to_cluster cannot be called on read-only FS."""
    pf = PyFat()
    pf.initialized = True
    pf.is_read_only = True
    with pytest.raises(PyFATException) as e:
        pf.write_data_to_cluster(b'foo', 4711)
    assert e.value.errno == errno.EROFS
