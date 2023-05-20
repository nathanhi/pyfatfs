# -*- coding: utf-8 -*-

"""Tests the 8DOT3 short name module."""
import errno
import string
import random
from unittest import mock

import pytest

import pyfatfs
from pyfatfs.EightDotThree import EightDotThree


def test_bytename_set_invalid_length():
    """Test that a byte name can only be set with the correct length."""
    sfn = EightDotThree()
    for n in [b'', b'1234567890', b'123456789011']:
        with pytest.raises(ValueError):
            sfn.set_byte_name(n)


def test_bytename_set_non_bytes():
    """Test that a byte name only accepts bytes."""
    sfn = EightDotThree()
    for n in ['FILENAME.TXT', 1234, bytearray('FILENAME.TXT', 'ASCII')]:
        with pytest.raises(TypeError) as e:
            sfn.set_byte_name(n)
            assert e.errno == errno.EINVAL


def test_bytename_set_not_a_directory_last_entry():
    """Test that 0x00 is detect as the last entry of the directory cluster."""
    sfn = EightDotThree()
    with pytest.raises(NotADirectoryError) as ex:
        sfn.set_byte_name(b'\0          ')
        assert ex.free_type == ex.LAST_ENTRY


def test_bytename_set_not_a_directory_free_entry():
    """Test that 0x00 is detect as the last entry of the directory cluster."""
    sfn = EightDotThree()
    with pytest.raises(NotADirectoryError) as ex:
        sfn.set_byte_name(b'\xE5          ')
        assert ex.free_type == ex.FREE_ENTRY


def test_checksum_calculation_precalculated():
    """Test that the checksum calculation works, with a precalculated value."""
    sfn = EightDotThree()
    sfn.set_str_name("FILENAME.TXT")
    assert sfn.checksum() == 58


def calculate_checksum_referenceimpl(fname: bytes) -> int:
    """Calculate checksum of a string based on reference implementation.

    This is taken from the Microsoft Extensible Firmware Initiative
    FAT32 File System Spec v1.03.

    .. code-block:
       short FcbNameLen;
       unsigned char Sum;

       Sum = 0;
       for (FcbNameLen=11; FcbNameLen!=0; FcbNameLen--) {
           Sum = ((Sum & 1) ? 0x80 : 0) + (Sum >> 1) + *pFcbName++;
       }

    """
    s = 0
    for i in range(0, 11):
        s = (0x80 if (s & 1) == 1 else 0x0) + (s >> 1) + fname[i]
        s &= 0xFF

    return s


def test_checksum_calculation_referenceimpl():
    """Test that the checksum calculation works, following reference impl."""
    sfn = EightDotThree()
    sfn.set_str_name("FILENAME.TXT")
    assert sfn.checksum() == calculate_checksum_referenceimpl(sfn.name)


def test_checksum_calculation_referenceimpl_random():
    """Test that the checksum calculation works, following reference impl."""
    base = ''.join(random.choices(string.ascii_letters + string.digits,
                                  k=8)).upper()
    ext = ''.join(random.choices(string.ascii_letters + string.digits,
                                 k=3)).upper()
    sfn = EightDotThree()
    sfn.set_str_name(f"{base}.{ext}")

    assert sfn.checksum() == calculate_checksum_referenceimpl(sfn.name)


def test_make_8dot3_name():
    """Test that make_8dot3_filename generates valid 8dot3 filenames."""
    fde = mock.MagicMock()
    fde._encoding = "ASCII"
    fde.get_entries.return_value = ([], [], [])
    sfn = EightDotThree()
    n = sfn.make_8dot3_name("This is a long filename.txt", fde)
    sfn.set_str_name(n)
    assert "THISIS.TXT" == n
    assert sfn.is_8dot3_conform(sfn.get_unpadded_filename())


def test_set_str_name_nonconform():
    """Test that set_str_name detects nonconforming names."""
    sfn = EightDotThree()
    sfn.set_str_name("FOO")
    with pytest.raises(pyfatfs.PyFATException):
        sfn.set_str_name("foo")


def test_is_8dot3_conform_invchars():
    """Check that invalid characters are correctly handled."""
    sfn = EightDotThree()
    assert sfn.is_8dot3_conform('"TEST"', 'ASCII') is False


def test_is_8dot3_conform_length():
    """Check that 8dot3 length limits are properly verified."""
    sfn = EightDotThree()
    assert sfn.is_8dot3_conform("TESTTEST.EXE") is True
    assert sfn.is_8dot3_conform("TESTTEST.EX") is True
    assert sfn.is_8dot3_conform("TESTTESTT.EX") is False
    assert sfn.is_8dot3_conform("TESTTES.EXEE") is False
    assert sfn.is_8dot3_conform("TESTTESTT.EXE") is False
    assert sfn.is_8dot3_conform("TESTTEST.EXEE") is False


def test_make_8dot3_name_cut_ext():
    """Test that make_8dot3_filename generates valid 8dot3 filenames."""
    fde = mock.MagicMock()
    fde._encoding = "ASCII"
    fde.get_entries.return_value = ([], [], [])
    sfn = EightDotThree()
    lfn = sfn.make_8dot3_name("This is a long filename.TeXT", fde)
    assert "THISIS.TEX" == lfn
    assert sfn.is_8dot3_conform(lfn)


def test_make_8dot3_name_invchars():
    """Verify that invalid characters are mapped to _."""
    fde = mock.MagicMock()
    fde._encoding = "ASCII"
    fde.get_entries.return_value = ([], [], [])
    sfn = EightDotThree()
    assert sfn.make_8dot3_name('"TEST".EXE', fde) == '_TEST_.EXE'
    assert sfn.make_8dot3_name('🐈.TXT', fde) == '_.TXT'


def test_make_8dot3_name_noext():
    """Test that make_8dot3_filename generates valid 8dot3 filenames."""
    fde = mock.MagicMock()
    fde._encoding = "ASCII"
    fde.get_entries.return_value = ([], [], [])
    sfn = EightDotThree()
    lfn = sfn.make_8dot3_name("This is a long filename", fde)
    assert "THISIS" == lfn
    assert sfn.is_8dot3_conform(lfn)


def test_make_8dot3_name_emptyext():
    """Test that make_8dot3_filename generates valid 8dot3 filenames."""
    fde = mock.MagicMock()
    fde._encoding = "ASCII"
    fde.get_entries.return_value = ([], [], [])
    sfn = EightDotThree()
    lfn = sfn.make_8dot3_name("This is a long filename.", fde)
    assert "THISIS" == lfn
    assert sfn.is_8dot3_conform(lfn)


def test_make_8dot3_name_unicode():
    """Test that make_8dot3_filename generates valid 8dot3 filenames."""
    fde = mock.MagicMock()
    fde._encoding = "UTF-8"
    fde.get_entries.return_value = ([], [], [])
    sfn = EightDotThree(encoding='UTF-8')
    strname = sfn.make_8dot3_name("🤷.🤷", fde)
    assert "🤷.🤷" == strname
    assert not sfn.is_8dot3_conform(strname)
    assert sfn.is_8dot3_conform(strname, encoding='UTF-8')


def test_make_8dot3_name_collision():
    """Test that make_8dot3_filename generates valid 8dot3 filenames."""
    fde = mock.MagicMock()
    fde._encoding = "ASCII"
    fde_sub = mock.MagicMock()
    fde_sub.get_short_name.side_effect = ["THISIS.TXT", "THISIS~1.TXT",
                                          "THISIS~2.TXT"]
    fde.get_entries.return_value = ([fde_sub, fde_sub], [fde_sub], [])
    sfn = EightDotThree()
    lfn = sfn.make_8dot3_name("This is a long filename.txt", fde)
    assert "THISIS~3.TXT" == lfn
    assert sfn.is_8dot3_conform(lfn)


def test_is_8dot3_conform_true():
    """Test that 8.3 file names are correctly detected."""
    assert EightDotThree.is_8dot3_conform("TESTFILE.TXT")


def test_is_8dot3_conform_false():
    """Test that non-8.3 file names are correctly detected."""
    assert not EightDotThree.is_8dot3_conform("This is a Long file.txt")


def test_set_str_name_non_str():
    """Test that set_str_name raises an exception on unsupported types."""
    sfn = EightDotThree()
    with pytest.raises(TypeError):
        sfn.set_str_name(b"FILENAME.TXT")


def test_set_str_name_non8dot3():
    """Test that set_str_name raises an exception on non-conformant names."""
    sfn = EightDotThree()
    for n in [b'FILENAME.TXT', 1234, bytearray('FILENAME.TXT', 'ASCII')]:
        with pytest.raises(TypeError) as e:
            sfn.set_str_name(n)
            assert e.errno == errno.EINVAL
