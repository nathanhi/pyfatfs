# -*- coding: utf-8 -*-
"""Registers the PyFatFSOpener used by PyFilesystem2."""

from fs.opener.parse import ParseResult

__all__ = ['PyFatFSOpener']

from fs.opener import Opener

from pyfatfs.PyFatFS import PyFatFS


class PyFatFSOpener(Opener):
    """Registers fat:// protocol for PyFilesystem2."""

    protocols = ['fat']

    @staticmethod
    def __param_parse(params: dict) -> dict:
        """Parse parameters and convert strings to bool."""
        _params = params.copy()
        for p in params:
            v = params[p]
            if isinstance(v, str):
                if v.lower() in ['true', '1', 't', 'y']:
                    v = True
                elif v.lower() in ['false', '0', 'f', 'n']:
                    v = False
            _params[p] = v
        return _params

    def open_fs(self, fs_url: str,  # pylint: disable=R0201
                parse_result: ParseResult, create: bool,
                cwd: str, writeable: bool = True):
        """Handle PyFilesystem2's protocol opening interface."""
        fs = PyFatFS(filename=parse_result.resource,
                     **self.__param_parse(parse_result.params))
        return fs
