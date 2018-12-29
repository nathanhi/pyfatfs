# coding: utf-8
"""Defines the PyFatFSOpener."""

__all__ = ['PyFatFSOpener']

from fs.opener import Opener

from pyfat.PyFatFS import PyFatFS


class PyFatFSOpener(Opener):
    protocols = ['fat']

    def open_fs(self, fs_url, parse_result, writeable, create, cwd):
        kwargs = {'offset': parse_result.params.get('offset', 0)}
        if parse_result.params.get('encoding', None) is not None:
            kwargs['encoding'] = parse_result.params.get('encoding')

        fs = PyFatFS(filename=parse_result.resource,
                     **kwargs)
        return fs
