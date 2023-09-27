# -*- coding: utf-8 -*-

"""Tests the DosDateTime serialization and deserialization."""

from datetime import datetime, time

from pyfatfs.DosDateTime import DosDateTime


def test_deserialize_date():
    """Verify raw date data is correctly deserialized."""
    assert DosDateTime.deserialize_date(0x5490) == datetime(2022, 4, 16)


def test_deserialize_date_min():
    """Verify that the minimum date value (0x21) leads to 1980-01-01.

    YEAR   | MO | DAY
    -------+----+-----
    0000000|0001|00001
    0      | 1  | 1
    100001 → 33 → 0x21
    """
    assert DosDateTime.deserialize_date(0x21) == datetime(1980, 1, 1)


def test_serialize_date_min():
    """Verify that 1980-01-01 is serialized as 0x21.

    YEAR   | MO | DAY
    -------+----+-----
    0000000|0001|00001
    0      | 1  | 1
    100001 → 33 → 0x21
    """
    ddt = DosDateTime(1980, 1, 1)
    assert ddt.serialize_date() == 0x21


def test_deserialize_date_max():
    """Verify that the max date value can be serialized.

    YEAR   | MO | DAY
    -------+----+-----
    1111111|1100|11111
    127    | 12 | 31
    1111111110011111 → 65439 → 0xFF9F
    """
    assert DosDateTime.deserialize_date(0xFF9F) == datetime(2107, 12, 31)


def test_deserialize_date_exceed_max():
    """Verify that the max date value cannot be exceeded."""
    assert DosDateTime.deserialize_date(0xFFA0) == datetime(1980, 1, 1)


def test_deserialize_time_min():
    """Deserialize an empty time."""
    assert DosDateTime.deserialize_time(0x0) == time(0, 0, 0)


def test_serialize_time_min():
    """Test that the minimum time value is properly serialized."""
    ddt = DosDateTime(1980, 1, 1, 0, 0, 0)
    assert ddt.serialize_time() == 0x0


def test_serialize_time_max():
    """Verify that the maximum time value can be properly serialized.

    HOUR |MINUTE|SECND
    -----+------+-----
    10111|111011|11101
    23   |  59  | 58
    1011111101111101 → 49021 → 0xBF7D
    """
    ddt = DosDateTime(1980, 1, 1, 23, 59, 59)
    assert ddt.serialize_time() == 0xBF7D


def test_deserialize_max():
    """Deserialize highest time value possible.

    HOUR |MINUTE|SECND
    -----+------+-----
    10111|111011|11101
    23   |  59  | 58
    1011111101111101 → 49021 → 0xBF7D
    """
    assert DosDateTime.deserialize_time(0xBF7D) == time(23, 59, 58)


def test_deserialize_exceed_max():
    """Deserialize invalid time value to 00:00:00."""
    assert DosDateTime.deserialize_time(0xBF7E) == time(0, 0, 0)


def test_deserialize_minutes_high():
    """Verify that minutes can be properly deserialized."""
    #: Raw data for 08:59:59
    tm = 18301

    # Seconds value only has an accuracy of 2 seconds
    assert DosDateTime.deserialize_time(tm) == time(8, 59, 58)


def test_fromtimestamp():
    """Test that DosDateTime can be created from datetime object.

    YEAR   | MO | DAY
    -------+----+-----
    0101010|0100|10000
    42     | 4  | 16
    0101010010010000 → 21648 → 0x5490

    HOUR |MINUTE|SECND
    -----+------+-----
    10001|000101|01010
    17   | 5    | 20 (10)
    1000100010101010 → 34986 → 0x88AA
    """
    dt = datetime(2022, 4, 16, 17, 5, 20)
    ddt = DosDateTime.fromtimestamp(dt.timestamp())
    assert ddt.serialize_date() == 0x5490
    assert ddt.serialize_time() == 0x88AA
