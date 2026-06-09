"""
Time Parser Utility
Parse natural language time expressions into datetime objects.
"""
import re
from datetime import datetime, time, timedelta
from typing import Optional, Tuple
import pytz


class TimeParser:
    """Parse natural language time expressions."""

    TIME_PATTERNS = [
        # "at 10", "at 10:30", "at 2 pm", "at 14:00"
        (r'\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b', 'at_time'),
        # "in 30 minutes", "in 2 hours", "in 1 hour"
        (r'\bin\s+(\d+)\s+(minute|hour|min|hr)s?\b', 'in_duration'),
        # "tomorrow at 10", "today at 3pm"
        (r'\b(today|tomorrow)\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b', 'relative_at_time'),
        # Just numbers like "10", "10:30", "2pm"
        (r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b', 'bare_time'),
    ]

    def __init__(self, timezone: str = "Asia/Tbilisi"):
        """Initialize with default timezone (Tbilisi, Georgia)."""
        try:
            self.timezone = pytz.timezone(timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            self.timezone = pytz.timezone("UTC")

    def parse_time(self, text: str) -> Optional[datetime]:
        """
        Parse time from natural language text.

        Examples:
        - "send me news at 10" -> 10:00 today or tomorrow
        - "brief me in 30 minutes" -> 30 minutes from now
        - "tomorrow at 2pm" -> 2:00 PM tomorrow
        """
        text = text.lower().strip()

        for pattern, pattern_type in self.TIME_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if pattern_type == 'at_time':
                    return self._parse_at_time(match)
                elif pattern_type == 'in_duration':
                    return self._parse_in_duration(match)
                elif pattern_type == 'relative_at_time':
                    return self._parse_relative_at_time(match)
                elif pattern_type == 'bare_time':
                    return self._parse_bare_time(match)

        return None

    def _parse_at_time(self, match) -> Optional[datetime]:
        """Parse 'at 10', 'at 10:30', 'at 2 pm'."""
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        am_pm = match.group(3)

        hour = self._adjust_hour_for_am_pm(hour, am_pm)
        if hour is None:
            return None

        return self._get_next_time(hour, minute)

    def _parse_in_duration(self, match) -> Optional[datetime]:
        """Parse 'in 30 minutes', 'in 2 hours'."""
        amount = int(match.group(1))
        unit = match.group(2)

        now = datetime.now(self.timezone)

        if unit in ['minute', 'min']:
            delta = timedelta(minutes=amount)
        elif unit in ['hour', 'hr']:
            delta = timedelta(hours=amount)
        else:
            return None

        return now + delta

    def _parse_relative_at_time(self, match) -> Optional[datetime]:
        """Parse 'today at 10', 'tomorrow at 2pm'."""
        relative = match.group(1)
        hour = int(match.group(2))
        minute = int(match.group(3)) if match.group(3) else 0
        am_pm = match.group(4)

        hour = self._adjust_hour_for_am_pm(hour, am_pm)
        if hour is None:
            return None

        base_date = datetime.now(self.timezone)

        if relative == 'tomorrow':
            base_date = base_date + timedelta(days=1)

        return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    def _parse_bare_time(self, match) -> Optional[datetime]:
        """Parse bare time like '10', '10:30', '2pm'."""
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        am_pm = match.group(3)

        hour = self._adjust_hour_for_am_pm(hour, am_pm)
        if hour is None:
            return None

        return self._get_next_time(hour, minute)

    def _adjust_hour_for_am_pm(self, hour: int, am_pm: Optional[str]) -> Optional[int]:
        """Adjust hour based on AM/PM."""
        if am_pm:
            if am_pm.lower() == 'pm' and hour != 12:
                hour += 12
            elif am_pm.lower() == 'am' and hour == 12:
                hour = 0
        else:
            # If no AM/PM specified, assume 24-hour format
            if hour > 23:
                return None

        return hour

    def _get_next_time(self, hour: int, minute: int) -> datetime:
        """Get the next occurrence of the specified time."""
        now = datetime.now(self.timezone)
        target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # If the time has already passed today, schedule for tomorrow
        if target_time <= now:
            target_time = target_time + timedelta(days=1)

        return target_time


def parse_time_from_text(text: str, timezone: str = "Asia/Tbilisi") -> Optional[datetime]:
    """Convenience function to parse time from text."""
    parser = TimeParser(timezone)
    return parser.parse_time(text)