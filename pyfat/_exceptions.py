# -*- coding: utf-8 -*-

"""Custom Exceptions for PyFAT."""


class PyFATException(Exception):
    """Generic PyFAT Exceptions."""

    def __init__(self, msg: str, errno=None):
        """Construct base class for PyFAT exceptions.

        :param msg: Exception message describing what happened
        :param errno: Error number, mostly based on POSIX errno where feasible
        """
        Exception.__init__(self, msg)
        self.errno = errno


class NotAnLFNEntryException(PyFATException):
    """Indicates that given dir entry cannot be interpreted as LFN entry."""

    pass


class BrokenLFNEntryException(PyFATException):
    """Indicates that given LFN entry is invalid."""

    pass
