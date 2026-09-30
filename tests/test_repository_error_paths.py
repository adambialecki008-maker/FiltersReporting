import sqlite3
from datetime import datetime

import pytest

from filters_reporting.database.filters_repository import FiltersRepository
from filters_reporting.models.filter import Filter
from filters_reporting.models.filter_sample import FilterSample


class ErrorCursor:
    rowcount = 0

    def execute(self, *args, **kwargs):
        raise sqlite3.OperationalError("forced db error")


class ErrorConnection:
    def __init__(self):
        self.rollback_called = False
        self.close_called = False

    def cursor(self):
        return ErrorCursor()

    def commit(self):
        raise AssertionError("commit should not be called after execute failure")

    def rollback(self):
        self.rollback_called = True

    def close(self):
        self.close_called = True


def repository_with_error_connection(monkeypatch):
    repository = FiltersRepository(":memory:")
    connection = ErrorConnection()
    monkeypatch.setattr(repository, "connect", lambda: connection)
    return repository, connection


def test_create_table_rolls_back_and_closes_on_sql_error(monkeypatch):
    repository, connection = repository_with_error_connection(monkeypatch)

    repository.create_table()

    assert connection.rollback_called is True
    assert connection.close_called is True


def test_save_filter_sample_rolls_back_and_closes_on_sql_error(monkeypatch):
    repository, connection = repository_with_error_connection(monkeypatch)
    sample = FilterSample(1, 100, True, False, datetime.now())

    repository.save_filter_sample(sample)

    assert connection.rollback_called is True
    assert connection.close_called is True


def test_save_filter_rolls_back_and_closes_on_sql_error(monkeypatch):
    repository, connection = repository_with_error_connection(monkeypatch)

    repository.save_filter(
        Filter(
            name="F1",
            opc_url="opc.tcp://localhost:4840",
        )
    )

    assert connection.rollback_called is True
    assert connection.close_called is True


@pytest.mark.parametrize(
    ("method_name", "args", "expected"),
    [
        ("get_all_filters", (), []),
        (
            "get_filter_by_opc_url",
            ("opc.tcp://localhost:4840",),
            None,
        ),
        ("get_active_filters", (), []),
        (
            "get_filter_samples_by_filter_id",
            (1, "2026-09-24"),
            [],
        ),
        (
            "get_delta_p_stats_by_filter_id",
            (1, "2026-09-24"),
            None,
        ),
        (
            "get_daily_filter_stats",
            ("2026-09-24",),
            None,
        ),
        (
            "get_daily_samples_for_report",
            ("2026-09-24",),
            None,
        ),
        ("get_connection_counts", (), (0, 0)),
        ("get_collector_heartbeat", (), None),
    ],
)
def test_read_methods_return_safe_value_on_sql_error(
    monkeypatch,
    method_name,
    args,
    expected,
):
    repository, connection = repository_with_error_connection(monkeypatch)

    result = getattr(repository, method_name)(*args)

    assert result == expected
    assert connection.close_called is True


@pytest.mark.parametrize(
    ("method_name", "args"),
    [
        ("update_filter_activity", ("F1", True)),
        (
            "update_filter_opc_url",
            ("F1", "opc.tcp://localhost:4840"),
        ),
        (
            "set_filter_connection_status",
            (1, True),
        ),
        (
            "set_collector_heartbeat",
            (
                datetime(
                    2026,
                    9,
                    24,
                    12,
                    0,
                    0,
                ),
            ),
        ),
    ],
)
def test_write_methods_roll_back_on_sql_error(
    monkeypatch,
    method_name,
    args,
):
    repository, connection = repository_with_error_connection(monkeypatch)

    getattr(repository, method_name)(*args)

    assert connection.rollback_called is True
    assert connection.close_called is True


def test_delete_samples_for_day_returns_zero_and_rolls_back_on_sql_error(
    monkeypatch,
):
    repository, connection = repository_with_error_connection(monkeypatch)

    result = repository.delete_samples_for_day("2026-09-24")

    assert result == 0
    assert connection.rollback_called is True
    assert connection.close_called is True


@pytest.mark.parametrize(
    ("method_name", "args"),
    [
        (
            "add_event",
            ("ERROR", "test event"),
        ),
        (
            "update_filter",
            (
                Filter(
                    name="F1",
                    filter_id=1,
                    opc_url="opc.tcp://localhost:4840",
                ),
            ),
        ),
        (
            "delete_filter",
            (1,),
        ),
    ],
)
def test_methods_that_must_propagate_sql_error_roll_back_and_raise(
    monkeypatch,
    method_name,
    args,
):
    repository, connection = repository_with_error_connection(monkeypatch)

    with pytest.raises(
        sqlite3.OperationalError,
        match="forced db error",
    ):
        getattr(repository, method_name)(*args)

    assert connection.rollback_called is True
    assert connection.close_called is True
