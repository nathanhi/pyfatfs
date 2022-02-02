# -*- coding: utf-8 -*-

"""Test PyFat core functionality."""
from io import BytesIO
from unittest import mock

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
