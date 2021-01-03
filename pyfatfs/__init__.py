# -*- coding: utf-8 -*-

"""
Python FAT filesystem module with :doc:`PyFilesystem2 <pyfilesystem2:index>` \
compatibility.

pyfatfs allows interaction with FAT12/16/32 filesystems, either via
:doc:`PyFilesystem2 <pyfilesystem2:index>` for file-level abstraction
or direct interaction with the filesystem for low-level access.
"""

__name__ = 'pyfatfs'
__author__ = 'Nathan-J. Hirschauer'
__author_email__ = 'nathanhi@deepserve.info'
__license__ = 'MIT License'


#: Specifies default ("OEM") encoding
FAT_OEM_ENCODING = 'ibm437'
#: Specifies the long file name encoding, which is always UTF-16 (LE)
FAT_LFN_ENCODING = 'utf-16-le'
