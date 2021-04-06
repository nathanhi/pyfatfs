# -*- coding: utf-8 -*-

"""Tests from PyFilesystem2."""

import gzip
import os
from functools import lru_cache
from io import BytesIO
from unittest import TestCase, mock

from fs.test import FSTestCases

from pyfatfs.PyFat import PyFat
from pyfatfs.PyFatFS import PyFatFS


class TestPyFatFS16(FSTestCases, TestCase):
    """Integration tests with PyFilesystem2 for FAT16."""

    FS_IMG_FILE = "pyfat16.img.gz"

    @staticmethod
    @lru_cache()
    def __read_fsimg(img_file):
        with gzip.open(img_file, "r") as imggz:
            return imggz.read()

    def make_fs(self):  # pylint: disable=R0201
        """Create filesystem for pyfilesystem2 integration tests."""
        img_file = os.path.join(os.path.dirname(__file__),
                                "data", self.FS_IMG_FILE)
        with mock.patch('pyfatfs.PyFat.open') as mock_open:
            mock_open.return_value = BytesIO(self.__read_fsimg(img_file))
            return PyFatFS("/this/does/not/exist.img",
                           encoding='UTF-8')


class TestPyFatFS32(TestPyFatFS16, FSTestCases, TestCase):
    """Integration tests with PyFilesystem2 for FAT32."""

    FS_IMG_FILE = "pyfat32.img.gz"


class TestPyFatFS12(TestPyFatFS16, FSTestCases, TestCase):
    """Test specifics of FAT12 filesystem."""

    FS_IMG_FILE = "pyfat12.img.gz"

    @mock.patch('pyfatfs.PyFat.PyFat.close')
    def test_fat_serialize(self, mock_close):
        """Make sure the FAT is properly serialized in case of FAT12."""
        pf = PyFat()
        pf.initialised = True
        pf.fat_type = pf.FAT_TYPE_FAT12
        pf.bpb_header = {
            'BPB_BytsPerSec': 512,
            'BPB_SecPerClus': 4,
            'BPB_RsvdSecCnt': 1,
            'BPB_NumFATS': 1,
            'BPB_FATSz16': 1
        }
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
        fat = pf.byte_repr()
        self.assertEqual(expected_fat, fat)

        # Check that size is correct
        fat_size = pf.bpb_header["BPB_BytsPerSec"]
        fat_size *= pf._get_fat_size_count()
        self.assertEqual(fat_size, len(fat))
