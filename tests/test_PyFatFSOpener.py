# -*- coding: utf-8 -*-

"""Make sure the fat PyFilesystem2 protocol gets registered properly."""

import fs
import pytest


def test_fsopener_protocol(mocker):
    """Test 'fat' protocol registration in PyFilesystem2."""
    pfs = mocker.patch('pyfatfs.PyFatFS.PyFatFS')
    fs.open_fs('fat:///dev/null')
    pfs.assert_called_once_with(filename='/dev/null')


def test_fsopener_unknown_arg_ignored(mocker):
    """Make sure that unknown opener arguments are ignored."""
    pfs = mocker.patch('pyfatfs.PyFatFSOpener.PyFatFS')
    mock_th = mocker.patch('pyfatfs.PyFatFSOpener.get_type_hints')
    mock_th.return_value = {'filename': str, 'test': str}
    mock_warn = mocker.patch('pyfatfs.PyFatFSOpener.warnings.warn')
    fs.open_fs('fat:///dev/null?foo=Hello, World')
    mock_warn.assert_called_once_with('Unknown opener argument \'foo\' '
                                      'specified.')
    pfs.assert_called_once_with(filename='/dev/null')


def test_fsopener_str_arg(mocker):
    """Verify that string arguments are passed through to PyFatFS."""
    pfs = mocker.patch('pyfatfs.PyFatFSOpener.PyFatFS')
    mock_th = mocker.patch('pyfatfs.PyFatFSOpener.get_type_hints')
    mock_th.return_value = {'filename': str, 'test': str}
    fs.open_fs('fat:///dev/null?test=Hello, World')
    pfs.assert_called_once_with(filename='/dev/null', test='Hello, World')


def test_fsopener_int_arg(mocker):
    """Verify that int arguments are parsed and passed through to PyFatFS."""
    pfs = mocker.patch('pyfatfs.PyFatFSOpener.PyFatFS')
    mock_th = mocker.patch('pyfatfs.PyFatFSOpener.get_type_hints')
    mock_th.return_value = {'filename': str, 'test': int}
    fs.open_fs('fat:///dev/null?test=4711')
    pfs.assert_called_once_with(filename='/dev/null', test=4711)


def test_fsopener_int_arg_invalid(mocker):
    """Verify that non-int values for int arguments lead to exception."""
    mocker.patch('pyfatfs.PyFatFSOpener.PyFatFS')
    mock_th = mocker.patch('pyfatfs.PyFatFSOpener.get_type_hints')
    mock_th.return_value = {'filename': str, 'test': int}
    with pytest.raises(ValueError):
        fs.open_fs('fat:///dev/null?test=abcd')


def test_fsopener_bool_arg_1(mocker):
    """Verify that bool argument value '1' is interpreted as True."""
    pfs = mocker.patch('pyfatfs.PyFatFSOpener.PyFatFS')
    mock_th = mocker.patch('pyfatfs.PyFatFSOpener.get_type_hints')
    mock_th.return_value = {'filename': str, 'test': bool}
    fs.open_fs('fat:///dev/null?test=1')
    pfs.assert_called_once_with(filename='/dev/null', test=True)


def test_fsopener_bool_arg_itrue(mocker):
    """Verify that bool argument value 'true' is interpreted as True."""
    pfs = mocker.patch('pyfatfs.PyFatFSOpener.PyFatFS')
    mock_th = mocker.patch('pyfatfs.PyFatFSOpener.get_type_hints')
    mock_th.return_value = {'filename': str, 'test': bool}
    fs.open_fs('fat:///dev/null?test=true')
    pfs.assert_called_once_with(filename='/dev/null', test=True)


def test_fsopener_bool_arg_true(mocker):
    """Verify that bool argument value 'True' is interpreted as True."""
    pfs = mocker.patch('pyfatfs.PyFatFSOpener.PyFatFS')
    mock_th = mocker.patch('pyfatfs.PyFatFSOpener.get_type_hints')
    mock_th.return_value = {'filename': str, 'test': bool}
    fs.open_fs('fat:///dev/null?test=True')
    pfs.assert_called_once_with(filename='/dev/null', test=True)


def test_fsopener_bool_arg_t(mocker):
    """Verify that bool argument value 't' is interpreted as True."""
    pfs = mocker.patch('pyfatfs.PyFatFSOpener.PyFatFS')
    mock_th = mocker.patch('pyfatfs.PyFatFSOpener.get_type_hints')
    mock_th.return_value = {'filename': str, 'test': bool}
    fs.open_fs('fat:///dev/null?test=t')
    pfs.assert_called_once_with(filename='/dev/null', test=True)


def test_fsopener_bool_arg_y(mocker):
    """Verify that bool argument value 'y' is interpreted as True."""
    pfs = mocker.patch('pyfatfs.PyFatFSOpener.PyFatFS')
    mock_th = mocker.patch('pyfatfs.PyFatFSOpener.get_type_hints')
    mock_th.return_value = {'filename': str, 'test': bool}
    fs.open_fs('fat:///dev/null?test=y')
    pfs.assert_called_once_with(filename='/dev/null', test=True)


def test_fsopener_bool_arg_0(mocker):
    """Verify that bool argument value '0' is interpreted as False."""
    pfs = mocker.patch('pyfatfs.PyFatFSOpener.PyFatFS')
    mock_th = mocker.patch('pyfatfs.PyFatFSOpener.get_type_hints')
    mock_th.return_value = {'filename': str, 'test': bool}
    fs.open_fs('fat:///dev/null?test=0')
    pfs.assert_called_once_with(filename='/dev/null', test=False)


def test_fsopener_bool_arg_ifalse(mocker):
    """Verify that bool argument value 'false' is interpreted as False."""
    pfs = mocker.patch('pyfatfs.PyFatFSOpener.PyFatFS')
    mock_th = mocker.patch('pyfatfs.PyFatFSOpener.get_type_hints')
    mock_th.return_value = {'filename': str, 'test': bool}
    fs.open_fs('fat:///dev/null?test=false')
    pfs.assert_called_once_with(filename='/dev/null', test=False)


def test_fsopener_bool_arg_false(mocker):
    """Verify that bool argument value 'False' is interpreted as False."""
    pfs = mocker.patch('pyfatfs.PyFatFSOpener.PyFatFS')
    mock_th = mocker.patch('pyfatfs.PyFatFSOpener.get_type_hints')
    mock_th.return_value = {'filename': str, 'test': bool}
    fs.open_fs('fat:///dev/null?test=False')
    pfs.assert_called_once_with(filename='/dev/null', test=False)


def test_fsopener_bool_arg_f(mocker):
    """Verify that bool argument value 'f' is interpreted as False."""
    pfs = mocker.patch('pyfatfs.PyFatFSOpener.PyFatFS')
    mock_th = mocker.patch('pyfatfs.PyFatFSOpener.get_type_hints')
    mock_th.return_value = {'filename': str, 'test': bool}
    fs.open_fs('fat:///dev/null?test=f')
    pfs.assert_called_once_with(filename='/dev/null', test=False)


def test_fsopener_bool_arg_n(mocker):
    """Verify that bool argument value 'n' is interpreted as False."""
    pfs = mocker.patch('pyfatfs.PyFatFSOpener.PyFatFS')
    mock_th = mocker.patch('pyfatfs.PyFatFSOpener.get_type_hints')
    mock_th.return_value = {'filename': str, 'test': bool}
    fs.open_fs('fat:///dev/null?test=n')
    pfs.assert_called_once_with(filename='/dev/null', test=False)


def test_fsopener_bool_arg_invalid(mocker):
    """Verify that unknown values for bool argument lead to exception."""
    mocker.patch('pyfatfs.PyFatFSOpener.PyFatFS')
    mock_th = mocker.patch('pyfatfs.PyFatFSOpener.get_type_hints')
    mock_th.return_value = {'filename': str, 'test': bool}
    with pytest.raises(ValueError):
        fs.open_fs('fat:///dev/null?test=invalid')
