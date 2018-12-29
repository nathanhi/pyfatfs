#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from fs.base import FS
from fs.permissions import Permissions

from pyfat.PyFat import PyFat


class PyFatFS(FS):
    def __init__(self, filename: str, encoding: str = 'ibm437',
                 offset: int = 0):
        super(PyFatFS, self).__init__()
        self.fs = PyFat(encoding=encoding, offset=offset)
        self.fs.open(filename)
        print("opened FS!")

    def close(self):
        self.fs.close()
        print("Closed FS!")
        super(PyFatFS, self).close()

    def getinfo(self, path: str, namespaces):
        print("getinfo")

    def listdir(self, path: str):

        print("listdir")

    def makedir(self, path: str, permissions: Permissions = None,
                recreate: bool = False):
        print("makedir")

    def openbin(self, path: str, mode: str = "r",
                buffering: int = -1, **options):
        print("openbin")

    def remove(self, path: str):
        print("remove")

    def removedir(self, path: str):
        print("removedir")

    def setinfo(self, path: str, info):
        print("setinfo")
