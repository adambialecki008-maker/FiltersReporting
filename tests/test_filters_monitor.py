from filters_reporting.monitoring.filter_monitor import *
from unittest.mock import Mock
from datetime import datetime
from datetime import datetime, timedelta
from filters_reporting.config import SAMPLE_INTERVAL_SECONDS
from filters_reporting.monitoring.filter_monitor import (
    is_collector_running,
    get_filters_for_attention_table,
)


def test_build_filter_statuses_adds_status_to_filter_data():
    now = datetime.now()

    samples = [
        {
            "filter_name": "F1",
            "filter_id": 1,
            "timestamp": now,
            "alarm_active": False,
            "status": True,
            "delta_p": 1800,
            "last_working_delta_p": 1800,
            "delta_p_threshold": 2000,
        }
    ]

    result = build_filter_statuses(samples, now, True)

    assert result[0]["filter_status"] == "clean-working"


def test_build_filter_statuses_adds_status_to_multiple_filters():
    now = datetime.now()

    samples = [
        {
            "filter_name": "F1",
            "filter_id": 1,
            "timestamp": now,
            "alarm_active": False,
            "status": True,
            "delta_p": 1800,
            "last_working_delta_p": 1800,
            "delta_p_threshold": 2000,
        },
        {
            "filter_name": "F2",
            "filter_id": 2,
            "timestamp": now,
            "alarm_active": True,
            "status": True,
            "delta_p": 1800,
            "last_working_delta_p": 1800,
            "delta_p_threshold": 2000,
        },
    ]

    result = build_filter_statuses(samples, now, True)

    assert result[0]["filter_status"] == "clean-working"
    assert result[0]["filter_name"] == "F1"
    assert result[1]["filter_status"] == "error"
    assert result[1]["filter_name"] == "F2"


def test_build_filter_statuses_adds_status_offline_to_filter_data_if_no_samples():
    now = datetime.now()

    samples = []
    result = build_filter_statuses(samples, now, True)

    assert result == []


def test_get_current_filter_statuses_returns_filter_status():
    now = datetime.now()
    repository = Mock()
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
            "delta_p_threshold": 2000,
        }
    ]

    result = get_current_filter_statuses(repository, now)
    assert result[0]["filter_status"] == "clean-working"
    repository.get_latest_active_filter_samples.assert_called_once()


def test_get_current_filter_statuses_returns_monitoring_stopped_when_collector_is_not_running():
    repository = Mock()

    now = datetime(2026, 9, 20, 14, 0, 0)

    repository.get_latest_active_filter_samples.return_value = [
        {
            "filter_name": "F1",
            "filter_id": 1,
            "delta_p": 1000,
            "alarm_active": False,
            "status": True,
            "timestamp": now,
            "delta_p_threshold": 2000,
            "last_working_delta_p": 1000,
            "last_working_timestamp": now,
        }
    ]

    repository.get_collector_heartbeat.return_value = None

    result = get_current_filter_statuses(
        repository,
        now,
    )

    assert result[0]["filter_status"] == "monitoring-stopped"


def test_count_attention_fitlers_returns_number_of_fitlers_that_needs_attention():
    filters = [
        {"filter_name": "F1", "filter_status": "offline"},
        {"filter_name": "F2", "filter_status": "error"},
        {"filter_name": "F3", "filter_status": "dirty-working"},
        {"filter_name": "F4", "filter_status": "clean-working"},
        {"filter_name": "F5", "filter_status": "clean-stopped"},
    ]

    result = count_attention_filters(filters)
    assert result == 3


def test_get_attention_state_returns_error():
    filters = [
        {"filter_name": "F1", "filter_status": "offline"},
        {"filter_name": "F2", "filter_status": "error"},
        {"filter_name": "F3", "filter_status": "dirty-working"},
        {"filter_name": "F4", "filter_status": "clean-working"},
        {"filter_name": "F5", "filter_status": "clean-stopped"},
    ]
    assert get_attention_state(filters) == "error"


def test_get_attention_state_returns_warning():
    filters = [
        {"filter_name": "F1", "filter_status": "clean-working"},
        {"filter_name": "F2", "filter_status": "clean-stopped"},
        {"filter_name": "F3", "filter_status": "dirty-working"},
        {"filter_name": "F4", "filter_status": "clean-working"},
        {"filter_name": "F5", "filter_status": "clean-stopped"},
    ]
    assert get_attention_state(filters) == "warning"


def test_get_attention_state_returns_ok():
    filters = [
        {"filter_name": "F1", "filter_status": "clean-working"},
        {"filter_name": "F2", "filter_status": "clean-stopped"},
        {"filter_name": "F3", "filter_status": "clean-working"},
        {"filter_name": "F4", "filter_status": "clean-working"},
        {"filter_name": "F5", "filter_status": "clean-stopped"},
    ]
    assert get_attention_state(filters) == "ok"


def test_get_attention_state_returns_neutral_when_no_filters():
    result = get_attention_state([])

    assert result == "neutral"


def test_get_attention_summary_returns_no_problems_when_all_filters_are_clean():
    filters = [
        {"filter_status": "clean-working"},
        {"filter_status": "clean-stopped"},
    ]

    result = get_attention_summary(filters)

    assert result == "Brak problemów"


def test_get_attention_summary_counts_dirty_filters():
    filters = [
        {"filter_status": "dirty-working"},
        {"filter_status": "dirty-stopped"},
        {"filter_status": "clean-working"},
    ]

    result = get_attention_summary(filters)

    assert result == "Zabrudzone: 2"


def test_get_attention_summary_counts_errors_and_offline_filters():
    filters = [
        {"filter_status": "error"},
        {"filter_status": "offline"},
        {"filter_status": "offline"},
    ]

    result = get_attention_summary(filters)

    assert result == "Awaria: 1 · Offline: 2"


def test_get_attention_summary_returns_full_summary():
    filters = [
        {"filter_status": "error"},
        {"filter_status": "offline"},
        {"filter_status": "dirty-working"},
        {"filter_status": "dirty-stopped"},
        {"filter_status": "clean-working"},
    ]

    result = get_attention_summary(filters)

    assert result == "Awaria: 1 · Offline: 1 · Zabrudzone: 2"


def test_get_attnetion_filters_returns_only_filters_that_needs_attention():
    filters = [
        {"filter_name": "F1", "filter_status": "error"},
        {"filter_name": "F2", "filter_status": "offline"},
        {"filter_name": "F3", "filter_status": "dirty-working"},
        {"filter_name": "F4", "filter_status": "clean-working"},
        {"filter_name": "F5", "filter_status": "dirty-stopped"},
    ]
    result = get_attention_filters(filters)
    assert len(result) == 4
    assert result[0]["filter_name"] == "F1"
    assert result[1]["filter_name"] == "F2"
    assert result[2]["filter_name"] == "F3"
    assert result[3]["filter_name"] == "F5"


from datetime import datetime


def test_build_attention_rows_returns_rows_for_attention_filters_only():
    now = datetime(
        2026,
        9,
        20,
        8,
        30,
        0,
    )
    filters = [
        {
            "filter_name": "F1",
            "delta_p": 1200,
            "filter_status": "clean-working",
            "timestamp": now,
        },
        {
            "filter_name": "F2",
            "delta_p": 2200,
            "filter_status": "dirty-working",
            "timestamp": now,
        },
        {
            "filter_name": "F3",
            "delta_p": 0,
            "filter_status": "offline",
            "timestamp": None,
        },
    ]
    result = build_attention_rows(filters)
    assert result == [
        [
            "F2",
            "2200 Pa",
            "dirty-working",
            "OK",
            "2026-09-20 08:30:00",
        ],
        [
            "F3",
            "0 Pa",
            "offline",
            "Offline",
            "—",
        ],
    ]


def test_get_filter_status_label_returns_human_readable_label():
    assert get_filter_status_label("dirty-working") == "Zabrudzony / pracuje"
    assert get_filter_status_label("dirty-stopped") == "Zabrudzony / postój"
    assert get_filter_status_label("error") == "Awaria"
    assert get_filter_status_label("offline") == "Offline"


def test_get_filter_status_state_returns_correct_state():
    assert get_filter_status_state("error") == "error"
    assert get_filter_status_state("offline") == "error"
    assert get_filter_status_state("dirty-working") == "warning"
    assert get_filter_status_state("dirty-stopped") == "warning"
    assert get_filter_status_state("clean-working") == "ok"
    assert get_filter_status_state("clean-stopped") == "ok"


def test_get_system_status_counts_returns_correct_counts():
    filters = [
        {"filter_status": "clean-working"},
        {"filter_status": "clean-stopped"},
        {"filter_status": "dirty-working"},
        {"filter_status": "error"},
        {"filter_status": "offline"},
    ]

    result = get_system_status_counts(filters)

    assert result["total"] == 5
    assert result["ok"] == 2
    assert result["attention"] == 2
    assert result["offline"] == 1


def test_is_collector_running_returns_true_for_fresh_heartbeat():
    now = datetime(2026, 9, 20, 14, 0, 0)
    heartbeat = now - timedelta(seconds=30)
    assert (
        is_collector_running(
            heartbeat,
            now,
        )
        is True
    )


def test_is_collector_running_returns_false_for_old_heartbeat():
    now = datetime(2026, 9, 20, 14, 0, 0)
    heartbeat = now - timedelta(
        seconds=2 * SAMPLE_INTERVAL_SECONDS,
    )
    assert (
        is_collector_running(
            heartbeat,
            now,
        )
        is False
    )


def test_is_collector_running_returns_false_without_heartbeat():
    now = datetime(2026, 9, 20, 14, 0, 0)
    assert (
        is_collector_running(
            None,
            now,
        )
        is False
    )


def test_attention_table_returns_only_problem_filters():
    filter_statuses = [
        {
            "filter_name": "F1",
            "filter_status": "clean-working",
        },
        {
            "filter_name": "F2",
            "filter_status": "dirty-working",
        },
        {
            "filter_name": "F3",
            "filter_status": "offline",
        },
        {
            "filter_name": "F4",
            "filter_status": "error",
        },
    ]
    result = get_filters_for_attention_table(
        filter_statuses,
        show_all=False,
    )

    assert len(result) == 3
    assert [filter_data["filter_name"] for filter_data in result] == [
        "F2",
        "F3",
        "F4",
    ]


def test_attention_table_returns_all_filters_when_show_all():
    filter_statuses = [
        {
            "filter_name": "F1",
            "filter_status": "clean-working",
        },
        {
            "filter_name": "F2",
            "filter_status": "dirty-working",
        },
        {
            "filter_name": "F3",
            "filter_status": "offline",
        },
    ]
    result = get_filters_for_attention_table(
        filter_statuses,
        show_all=True,
    )
    assert result == filter_statuses


def test_monitoring_stopped_does_not_require_attention():
    filter_statuses = [
        {
            "filter_name": "F1",
            "filter_status": ("monitoring-stopped"),
        },
    ]
    result = get_filters_for_attention_table(
        filter_statuses,
        show_all=False,
    )
    assert result == []


def test_filters_for_attention_table_returns_only_attention_filters():
    filters = [
        {
            "filter_name": "F1",
            "filter_status": "clean-working",
        },
        {
            "filter_name": "F2",
            "filter_status": "dirty-working",
        },
        {
            "filter_name": "F3",
            "filter_status": "offline",
        },
    ]
    result = get_filters_for_attention_table(
        filters,
        show_all=False,
    )
    assert len(result) == 2
    assert result[0]["filter_name"] == "F2"
    assert result[1]["filter_name"] == "F3"


def test_filters_for_attention_table_returns_all_filters():
    filters = [
        {
            "filter_name": "F1",
            "filter_status": "clean-working",
        },
        {
            "filter_name": "F2",
            "filter_status": "dirty-working",
        },
    ]
    result = get_filters_for_attention_table(
        filters,
        show_all=True,
    )
    assert result == filters


def test_is_collector_running_uses_custom_interval():
    now = datetime(
        2026,
        9,
        22,
        20,
        0,
        0,
    )
    heartbeat = now - timedelta(seconds=150)
    assert (
        is_collector_running(
            heartbeat,
            now,
            60,
        )
        is False
    )
    assert (
        is_collector_running(
            heartbeat,
            now,
            120,
        )
        is True
    )
