# -*- coding: utf-8 -*-


class PyFATException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)


class NotAnLFNEntryException(PyFATException):
    pass
