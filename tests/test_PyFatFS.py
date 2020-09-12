# -*- coding: utf-8 -*-

"""Tests from PyFilesystem2."""
import gzip
import os
from unittest import TestCase

from fs.test import FSTestCases

from pyfat.PyFatFS import PyFatFS


class TestPyFatFS16(FSTestCases, TestCase):
    """Integration tests with PyFilesystem2 for FAT16."""
    def make_fs(self):
        img_file = os.path.join(os.path.dirname(__file__),
                                "data", "pyfat16.img")
        with gzip.open(img_file + '.gz', "r") as imggz:
            with open(img_file, 'wb') as img:
                img.write(imggz.read())

        return PyFatFS(img_file)
