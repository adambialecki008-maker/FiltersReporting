from datetime import datetime, timedelta

from filters_reporting.config import SAMPLE_INTERVAL_SECONDS
from filters_reporting.monitoring.filter_status import (
    get_filter_status,
)


def make_sample(
    *,
    timestamp,
    alarm_active=False,
    status=True,
    delta_p=1000,
    delta_p_threshold=2000,
    last_working_delta_p=1000,
):
    return {
        "timestamp": timestamp,
        "alarm_active": alarm_active,
        "status": status,
        "delta_p": delta_p,
        "delta_p_threshold": delta_p_threshold,
        "last_working_delta_p": last_working_delta_p,
    }


def test_get_filter_status_returns_monitoring_stopped_when_collector_is_not_running():
    now = datetime(2026, 9, 20, 14, 0, 0)

    sample = make_sample(
        timestamp=now,
    )

    result = get_filter_status(
        sample,
        now,
        collector_running=False,
    )

    assert result == "monitoring-stopped"


def test_get_filter_status_returns_offline_when_timestamp_is_none():
    now = datetime(2026, 9, 20, 14, 0, 0)

    sample = make_sample(
        timestamp=None,
    )

    result = get_filter_status(
        sample,
        now,
        collector_running=True,
    )

    assert result == "offline"


def test_get_filter_status_returns_offline_when_sample_is_too_old():
    now = datetime(2026, 9, 20, 14, 0, 0)

    sample = make_sample(
        timestamp=now
        - timedelta(
            seconds=2 * SAMPLE_INTERVAL_SECONDS,
        ),
    )

    result = get_filter_status(
        sample,
        now,
        collector_running=True,
    )

    assert result == "offline"


def test_get_filter_status_returns_error_when_alarm_is_active():
    now = datetime(2026, 9, 20, 14, 0, 0)

    sample = make_sample(
        timestamp=now,
        alarm_active=True,
    )

    result = get_filter_status(
        sample,
        now,
        collector_running=True,
    )

    assert result == "error"


def test_get_filter_status_returns_clean_working_when_running_below_threshold():
    now = datetime(2026, 9, 20, 14, 0, 0)

    sample = make_sample(
        timestamp=now,
        status=True,
        delta_p=1500,
        delta_p_threshold=2000,
    )

    result = get_filter_status(
        sample,
        now,
        collector_running=True,
    )

    assert result == "clean-working"


def test_get_filter_status_returns_dirty_working_when_running_above_threshold():
    now = datetime(2026, 9, 20, 14, 0, 0)

    sample = make_sample(
        timestamp=now,
        status=True,
        delta_p=2500,
        delta_p_threshold=2000,
    )

    result = get_filter_status(
        sample,
        now,
        collector_running=True,
    )

    assert result == "dirty-working"


def test_get_filter_status_returns_dirty_working_when_delta_p_equals_threshold():
    now = datetime(2026, 9, 20, 14, 0, 0)

    sample = make_sample(
        timestamp=now,
        status=True,
        delta_p=2000,
        delta_p_threshold=2000,
    )

    result = get_filter_status(
        sample,
        now,
        collector_running=True,
    )

    assert result == "dirty-working"


def test_get_filter_status_returns_clean_stopped_when_filter_never_worked():
    now = datetime(2026, 9, 20, 14, 0, 0)
    sample = make_sample(
        timestamp=now,
        status=False,
        delta_p=0,
        last_working_delta_p=None,
    )
    result = get_filter_status(
        sample,
        now,
        collector_running=True,
    )
    assert result == "clean-stopped"


def test_get_filter_status_returns_clean_stopped_when_last_working_delta_p_is_below_threshold():
    now = datetime(2026, 9, 20, 14, 0, 0)
    sample = make_sample(
        timestamp=now,
        status=False,
        delta_p=0,
        delta_p_threshold=2000,
        last_working_delta_p=1500,
    )
    result = get_filter_status(
        sample,
        now,
        collector_running=True,
    )
    assert result == "clean-stopped"


def test_get_filter_status_returns_dirty_stopped_when_last_working_delta_p_is_above_threshold():
    now = datetime(2026, 9, 20, 14, 0, 0)
    sample = make_sample(
        timestamp=now,
        status=False,
        delta_p=0,
        delta_p_threshold=2000,
        last_working_delta_p=2500,
    )
    result = get_filter_status(
        sample,
        now,
        collector_running=True,
    )
    assert result == "dirty-stopped"


def test_get_filter_status_returns_dirty_stopped_when_last_working_delta_p_equals_threshold():
    now = datetime(2026, 9, 20, 14, 0, 0)
    sample = make_sample(
        timestamp=now,
        status=False,
        delta_p=0,
        delta_p_threshold=2000,
        last_working_delta_p=2000,
    )
    result = get_filter_status(
        sample,
        now,
        collector_running=True,
    )
    assert result == "dirty-stopped"


def test_filter_does_not_go_offline_before_two_custom_intervals():
    now = datetime(
        2026,
        9,
        22,
        20,
        0,
        0,
    )
    sample_data = {
        "timestamp": now - timedelta(seconds=150),
        "alarm_active": False,
        "status": True,
        "delta_p": 1000,
        "delta_p_threshold": 2000,
        "last_working_delta_p": 1000,
    }
    result = get_filter_status(
        sample_data,
        now,
        True,
        120,
    )
    assert result == "clean-working"


def test_filter_goes_offline_after_two_custom_intervals():
    now = datetime(
        2026,
        9,
        22,
        20,
        0,
        0,
    )
    sample_data = {
        "timestamp": now - timedelta(seconds=241),
        "alarm_active": False,
        "status": True,
        "delta_p": 1000,
        "delta_p_threshold": 2000,
        "last_working_delta_p": 1000,
    }
    result = get_filter_status(
        sample_data,
        now,
        True,
        120,
    )
    assert result == "offline"
