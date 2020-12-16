# -*- coding: utf-8 -*-

"""Enhancement of datetime for DOS date/time format compatibility."""
from datetime import datetime, time


class DosDateTime(datetime):
    """DOS-specific date/time format serialization."""
    def serialize_date(self) -> int:
        """Convert current datetime to FAT date."""
        date = self.year - 1980 << 9 | self.month << 5 | self.day
        return date

    def serialize_time(self) -> int:
        """Convert current datetime to FAT time."""
        time = self.hour << 11 | self.minute << 5 | ((self.second - (self.second % 2)) // 2)
        return time

    @staticmethod
    def deserialize_date(dt: int) -> "DosDateTime":
        """Convert a DOS date format to a Python object."""
        day = dt & ((1 << 5) - 1)
        month = (dt >> 5) & ((1 << 4) - 1)
        year = ((dt >> 9) & (1 << 8) - 1) + 1980
        return DosDateTime(year, month, day)

    @staticmethod
    def deserialize_time(tm: int) -> time:
        """Convert a DOS time format to a Python object."""
        second = (tm & (1 << 5) - 1) * 2
        minute = (tm >> 5) & ((1 << 5) - 1)
        hour = (tm >> 11) & ((1 << 5) - 1)
        return time(hour, minute, second)
