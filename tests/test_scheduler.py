import pytest
from src.scheduler import calculate_batch_timestamps


def test_calculate_batch_timestamps():
    timestamps = calculate_batch_timestamps(
        count=3,
        start_time_iso="2026-07-25T12:00:00+00:00",
        interval_hours=3
    )
    assert len(timestamps) == 3
    assert "2026-07-25T12:00:00" in timestamps[0]
    assert "2026-07-25T15:00:00" in timestamps[1]
    assert "2026-07-25T18:00:00" in timestamps[2]
