# -*- coding: utf-8 -*-

"""Tests from PyFilesystem2."""

from datetime import datetime
from unittest import TestCase, mock
from io import BytesIO

import fs.errors
from fs.test import FSTestCases

from pyfatfs.PyFat import PyFat
from pyfatfs.PyFatFS import PyFatBytesIOFS


class TestPyFatFS16(FSTestCases, TestCase):
    """Integration tests with PyFilesystem2 for FAT16."""

    FAT_TYPE = PyFat.FAT_TYPE_FAT16

    def make_fs(self):  # pylint: disable=R0201
        """Create filesystem for PyFilesystem2 integration tests."""
        pf = PyFat()
        part_sz = 1024 * 1024 * (4 if self.FAT_TYPE == PyFat.FAT_TYPE_FAT12
                                 else 33)
        in_memory_fs = BytesIO(b'\0' * part_sz)
        pf._PyFat__fp = in_memory_fs
        with mock.patch('pyfatfs.PyFat.PyFat._PyFat__set_fp',
                        mock.Mock()):
            with mock.patch('pyfatfs.PyFat.open'):
                pf.mkfs("/this/does/not/exist.img",
                        fat_type=self.FAT_TYPE,
                        label=f"FAT{self.FAT_TYPE}TST",
                        size=part_sz)
                pf.flush_fat()

        in_memory_fs.seek(0)
        return PyFatBytesIOFS(BytesIO(in_memory_fs.read()), encoding='UTF-8')

    def test_create_file_folder_dupe(self):
        """Verify that file creation with duplicate name to a folder fails."""
        self.fs.makedir("/test")
        with self.assertRaises(fs.errors.FileExpected):
            self.fs.create("/test")

    def test_create_folder_file_dupe(self):
        """Verify that folder creation with duplicate name to a file fails."""
        self.fs.create("/test")
        with self.assertRaises(fs.errors.DirectoryExists):
            self.fs.makedir("/test", recreate=True)

    def test_create_wipe_update_mtime(self):
        """Verify that file creation updates mtime on wipe."""
        self.fs.create("/test")
        self.fs.settimes("/test", datetime(1999, 12, 31, 23, 59, 59, 9999),
                         datetime(2000, 1, 1, 0, 0, 0, 0))
        orig_info = self.fs.getinfo("/test")
        self.fs.create("/test", wipe=True)
        new_info = self.fs.getinfo("/test")
        assert orig_info != new_info


class TestPyFatFS32(TestPyFatFS16, FSTestCases, TestCase):
    """Integration tests with PyFilesystem2 for FAT32."""

    FAT_TYPE = PyFat.FAT_TYPE_FAT32


class TestPyFatFS12(TestPyFatFS16, FSTestCases, TestCase):
    """Test specifics of FAT12 filesystem."""

    FAT_TYPE = PyFat.FAT_TYPE_FAT12

    @mock.patch('pyfatfs.PyFat.PyFat.close')
    def test_fat_serialize(self, mock_close):
        """Make sure the FAT is properly serialized in case of FAT12."""
        pf = PyFat()
        pf.initialized = True
        pf.fat_type = pf.FAT_TYPE_FAT12
        pf.bpb_header = {
            'BPB_BytsPerSec': 512,
            'BPB_SecPerClus': 4,
            'BPB_RsvdSecCnt': 1,
            'BPB_NumFATs': 1,
            'BPB_FATSz16': 1
        }
        pf._fat_size = pf._get_fat_size_count()
        pf.fat = [4088, 4095, 4095, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
                  16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
                  31, 32, 33, 34, 4095, 4095, 4095, 4095, 4095, 4095, 4095,
                  4095, 4095, 4095, 4095, 4095, 4095, 4095, 4095, 4095, 4095,
                  4095, 4095] + ([0] * 288)
        expected_fat = bytearray(b'\xf8\xff\xff\xffO\x00\x05`\x00\x07\x80'
                                 b'\x00\t\xa0\x00\x0b\xc0\x00\r\xe0\x00'
                                 b'\x0f\x00\x01\x11 \x01\x13@\x01\x15`'
                                 b'\x01\x17\x80\x01\x19\xa0\x01\x1b\xc0'
                                 b'\x01\x1d\xe0\x01\x1f\x00\x02! \x02\xff'
                                 b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                                 b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
                                 b'\xff\xff\xff\xff\xff\xff\xff'
                                 b'\x0f' + (b'\x00' * 432))
        fat = bytes(pf)
        self.assertEqual(expected_fat, fat)

        # Check that size is correct
        fat_size = pf.bpb_header["BPB_BytsPerSec"]
        fat_size *= pf._get_fat_size_count()
        self.assertEqual(fat_size, len(fat))
