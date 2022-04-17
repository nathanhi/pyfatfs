# -*- coding: utf-8 -*-
"""Registers the PyFatFSOpener used by PyFilesystem2."""

import warnings
from typing import get_type_hints

from fs.opener.parse import ParseResult

__all__ = ['PyFatFSOpener']

from fs.opener import Opener

from pyfatfs.PyFatFS import PyFatFS


class PyFatFSOpener(Opener):
    """Registers fat:// protocol for PyFilesystem2."""

    protocols = ['fat']

    @staticmethod
    def __convert_bool(value: str) -> bool:
        """Convert given string to bool."""
        if value.lower() in ['true', '1', 't', 'y']:
            return True
        elif value.lower() in ['false', '0', 'f', 'n']:
            return False
        raise ValueError(f'Invalid parameter supplied, cannot '
                         f'convert to boolean parameter: {value}')

    @staticmethod
    def __param_parse(params: dict) -> dict:
        """Parse parameters and convert to correct type."""
        _params = {}
        types = get_type_hints(PyFatFS.__init__)
        for p in params:
            try:
                t = types[p]
            except KeyError:
                warnings.warn(f'Unknown opener argument \'{p}\' specified.')
                continue

            if t == bool:
                t = PyFatFSOpener.__convert_bool

            _params[p] = t(params[p])
        return _params

    def open_fs(self, fs_url: str,  # pylint: disable=R0201
                parse_result: ParseResult, create: bool,
                cwd: str, writeable: bool = True):
        """Handle PyFilesystem2's protocol opening interface."""
        fs = PyFatFS(filename=parse_result.resource,
                     **self.__param_parse(parse_result.params))
        return fs
