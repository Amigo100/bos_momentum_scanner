"""Tests for timezone-aware scheduling (Audit Issue #3).

Verifies that SLOT_TIMES_UTC is dynamically computed from SLOT_TIMES_ET
using ZoneInfo, correctly handling both EST and EDT offsets.
"""

import pytest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta


class TestSlotTimesUTC:
    """Verify get_slot_times_utc() produces correct UTC slot times."""

    def test_get_slot_times_utc_returns_all_slots(self):
        """All 5 slots present in result."""
        from config.settings import get_slot_times_utc

        result = get_slot_times_utc()
        assert len(result) == 5
        for slot in range(1, 6):
            assert slot in result, f"Slot {slot} missing from UTC times"

    def test_slot_times_utc_values_reasonable(self):
        """UTC hours are in valid range (00-23) and minutes preserved."""
        from config.settings import get_slot_times_utc

        result = get_slot_times_utc()
        for slot, time_str in result.items():
            parts = time_str.split(":")
            assert len(parts) == 2, f"Slot {slot} has invalid format: {time_str}"
            hour, minute = int(parts[0]), int(parts[1])
            assert 0 <= hour <= 23, f"Slot {slot} UTC hour {hour} out of range"
            assert 0 <= minute <= 59, f"Slot {slot} UTC minute {minute} out of range"

    def test_slot_times_et_unchanged(self):
        """SLOT_TIMES_ET still has canonical 5-slot structure with expected times."""
        from config.settings import SLOT_TIMES_ET

        assert len(SLOT_TIMES_ET) == 5
        assert SLOT_TIMES_ET[1] == "08:00"
        assert SLOT_TIMES_ET[2] == "10:00"
        assert SLOT_TIMES_ET[3] == "12:30"
        assert SLOT_TIMES_ET[4] == "15:30"
        assert SLOT_TIMES_ET[5] == "18:00"

    def test_slot_times_utc_module_level_populated(self):
        """SLOT_TIMES_UTC at module level is populated (not empty/None)."""
        from config.settings import SLOT_TIMES_UTC

        assert SLOT_TIMES_UTC is not None
        assert isinstance(SLOT_TIMES_UTC, dict)
        assert len(SLOT_TIMES_UTC) == 5

    def test_est_offset_produces_correct_utc(self):
        """During EST (UTC-5), 08:00 ET → 13:00 UTC.

        Verifies the conversion math directly using a known EST datetime.
        """
        try:
            from zoneinfo import ZoneInfo
        except ImportError:
            from backports.zoneinfo import ZoneInfo

        # Create a datetime in January (definitely EST)
        est_winter = datetime(2026, 1, 15, 12, 0, 0, tzinfo=ZoneInfo("America/New_York"))
        utc_offset = est_winter.utcoffset().total_seconds() / 3600
        assert utc_offset == -5.0, f"EST offset should be -5, got {utc_offset}"

        # Apply same formula as get_slot_times_utc()
        # 08:00 ET - (-5) = 13:00 UTC
        hour, minute = 8, 0
        utc_hour = int(hour - utc_offset) % 24
        assert utc_hour == 13

        # 15:30 ET - (-5) = 20:30 UTC
        hour, minute = 15, 30
        utc_hour = int(hour - utc_offset) % 24
        assert utc_hour == 20

    def test_edt_offset_produces_correct_utc(self):
        """During EDT (UTC-4), 08:00 ET → 12:00 UTC."""
        try:
            from zoneinfo import ZoneInfo
        except ImportError:
            from backports.zoneinfo import ZoneInfo

        # Create a datetime in July (definitely EDT)
        edt_summer = datetime(2026, 7, 15, 12, 0, 0, tzinfo=ZoneInfo("America/New_York"))
        utc_offset = edt_summer.utcoffset().total_seconds() / 3600
        assert utc_offset == -4.0, f"EDT offset should be -4, got {utc_offset}"

        # 08:00 ET - (-4) = 12:00 UTC
        hour, minute = 8, 0
        utc_hour = int(hour - utc_offset) % 24
        assert utc_hour == 12

    def test_minutes_preserved_in_conversion(self):
        """Minutes from ET times are preserved in UTC conversion (e.g., 12:30 → XX:30)."""
        from config.settings import get_slot_times_utc, SLOT_TIMES_ET

        result = get_slot_times_utc()
        for slot in result:
            et_minute = SLOT_TIMES_ET[slot].split(":")[1]
            utc_minute = result[slot].split(":")[1]
            assert et_minute == utc_minute, (
                f"Slot {slot}: ET minute {et_minute} != UTC minute {utc_minute}"
            )
