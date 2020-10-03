# -*- coding: utf-8 -*-

"""Enhancement of datetime for DOS date/time format compatibility."""
from datetime import datetime


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
