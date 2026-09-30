from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from filters_reporting.opcua.server import (
    FiltersReportingOpcUaServer,
    build_server_snapshot,
    calculate_dirty_percent,
)


def test_calculate_dirty_percent():
    result = calculate_dirty_percent(
        2100,
        2000,
    )

    assert result == pytest.approx(105.0)


def test_calculate_dirty_percent_returns_zero_without_threshold():
    assert (
        calculate_dirty_percent(
            2100,
            0,
        )
        == 0.0
    )


def test_calculate_dirty_percent_returns_zero_for_none_values():
    assert (
        calculate_dirty_percent(
            None,
            None,
        )
        == 0.0
    )


def test_build_server_snapshot_returns_active_filter_data():
    now = datetime(
        2026,
        9,
        25,
        12,
        0,
        0,
    )

    repository = Mock()

    repository.get_all_filters.return_value = [
        SimpleNamespace(
            filter_id=1,
            name="F1",
            active=True,
            delta_p_threshold=2000,
        )
    ]

    repository.get_collector_heartbeat.return_value = now

    repository.get_latest_active_filter_samples.return_value = [
        {
            "filter_name": "F1",
            "filter_id": 1,
            "timestamp": now,
            "alarm_active": False,
            "status": True,
            "delta_p": 1800,
            "last_working_delta_p": 1800,
            "last_working_timestamp": now,
            "delta_p_threshold": 2000,
        }
    ]

    result = build_server_snapshot(
        repository,
        now,
    )

    assert result.collector_running is True
    assert result.total_filters == 1
    assert result.active_filters == 1

    assert len(result.filters) == 1

    filter_data = result.filters[0]

    assert filter_data.filter_id == 1
    assert filter_data.name == "F1"
    assert filter_data.active is True

    assert filter_data.delta_p == 1800

    assert filter_data.delta_p_threshold == 2000

    assert filter_data.working is True

    assert filter_data.alarm_active is False

    assert filter_data.last_working_delta_p == 1800

    assert filter_data.dirty_percent == pytest.approx(90.0)

    assert filter_data.status == "clean-working"

    assert filter_data.last_update == "2026-09-25T12:00:00"


def test_build_server_snapshot_marks_inactive_filter():
    now = datetime(
        2026,
        9,
        25,
        12,
        0,
        0,
    )

    repository = Mock()

    repository.get_all_filters.return_value = [
        SimpleNamespace(
            filter_id=1,
            name="F1",
            active=False,
            delta_p_threshold=2000,
        )
    ]

    repository.get_collector_heartbeat.return_value = now

    repository.get_latest_active_filter_samples.return_value = []

    result = build_server_snapshot(
        repository,
        now,
    )

    assert result.active_filters == 0

    filter_data = result.filters[0]

    assert filter_data.active is False

    assert filter_data.status == "inactive"

    assert filter_data.working is False

    assert filter_data.alarm_active is False


def test_build_server_snapshot_marks_missing_active_sample_offline():
    now = datetime(
        2026,
        9,
        25,
        12,
        0,
        0,
    )

    repository = Mock()

    repository.get_all_filters.return_value = [
        SimpleNamespace(
            filter_id=1,
            name="F1",
            active=True,
            delta_p_threshold=2000,
        )
    ]

    repository.get_collector_heartbeat.return_value = now

    repository.get_latest_active_filter_samples.return_value = []

    result = build_server_snapshot(
        repository,
        now,
    )

    filter_data = result.filters[0]

    assert filter_data.status == "offline"

    assert filter_data.delta_p == 0


def test_server_rejects_invalid_refresh_interval():
    settings = Mock()

    with pytest.raises(ValueError):
        FiltersReportingOpcUaServer(
            repository=Mock(),
            settings=settings,
            refresh_interval=0,
        )


def test_server_is_initially_stopped():
    server = FiltersReportingOpcUaServer(
        repository=Mock(),
        settings=Mock(),
    )

    assert server.running is False

    assert server.server is None


def test_request_stop_sets_flag():
    server = FiltersReportingOpcUaServer(
        repository=Mock(),
        settings=Mock(),
    )

    server.request_stop()

    assert server._stop_requested is True
