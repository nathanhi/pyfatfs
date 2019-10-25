# -*- coding: utf-8 -*-
"""Registers the PyFatFSOpener used by PyFilesystem2."""

from fs.opener.parse import ParseResult

__all__ = ['PyFatFSOpener']

from fs.opener import Opener

from pyfat.PyFatFS import PyFatFS


class PyFatFSOpener(Opener):
    """Registers fat:// protocol for PyFilesystem2."""

    protocols = ['fat']

    def open_fs(self, fs_url: str, parse_result: ParseResult,
                create: bool, cwd: str, writeable: bool = True):
        """Handle PyFilesystem2's protocol opening interface."""
        kwargs = {'offset': parse_result.params.get('offset', 0)}
        if parse_result.params.get('encoding', None) is not None:
            kwargs['encoding'] = parse_result.params.get('encoding')

        fs = PyFatFS(filename=parse_result.resource,
                     **kwargs)
        return fs
