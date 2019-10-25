# -*- coding: utf-8 -*-

"""Custom Exceptions for PyFAT"""


class PyFATException(Exception):
    """Generic PyFAT Exceptions"""
    def __init__(self, msg, errno=None):
        Exception.__init__(self, msg)
        self.errno = errno


class NotAnLFNEntryException(PyFATException):
    pass
