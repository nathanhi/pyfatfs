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


class BrokenLFNEntryException(PyFATException):
    """Indicates that given LFN entry is invalid."""


class NotAFatEntryException(NotADirectoryError):
    """Custom handling for FAT `NotADirectoryError`'s."""

    #: Indicates a free entry, but not an end of chain.
    FREE_ENTRY = 0xE5
    #: Indicates an end of directory cluster, do not search further.
    LAST_ENTRY = 0x00

    def __init__(self, msg: str, free_type=FREE_ENTRY):
        """Construct base class for PyFAT exceptions.

        :param msg: Exception message describing what happened
        :param free_type: Either `FREE_ENTRY` or `LAST_ENTRY`.
        """
        NotADirectoryError.__init__(self, msg)
        self.free_type = free_type
