# -*- coding: utf-8 -*-

"""
FAT Filesystem Module for PyFilesystem2.

PyFAT is a filesystem module for use with PyFilesystem2 for anyone
who needs to access or modify files on a FAT filesystem.
"""

__version__ = '0.0.0'
__author__ = 'nathanhi'
__author_email__ = 'nathanhi <at> deepserve.info'
__license__ = 'MIT License'


#: Specifies default ("OEM") encoding
FAT_OEM_ENCODING = 'ibm437'
#: Specifies the long file name encoding, which is always UTF-16 (LE)
FAT_LFN_ENCODING = 'utf-16-le'
