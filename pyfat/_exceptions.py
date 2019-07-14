# -*- coding: utf-8 -*-


class PyFATException(Exception):
    def __init__(self, msg, errno=None):
        Exception.__init__(self, msg)
        self.errno = errno


class NotAnLFNEntryException(PyFATException):
    pass
