from unittest.mock import Mock

from filters_reporting.collection import data_collector
from filters_reporting.single_instance import AlreadyRunningError


def test_main_does_not_start_second_collector(monkeypatch):
    acquire = Mock(
        side_effect=AlreadyRunningError("already running")
    )
    asyncio_run = Mock()
    logger_warning = Mock()

    monkeypatch.setattr(
        data_collector,
        "acquire_single_instance",
        acquire,
    )
    monkeypatch.setattr(
        data_collector.asyncio,
        "run",
        asyncio_run,
    )
    monkeypatch.setattr(
        data_collector.logger,
        "warning",
        logger_warning,
    )

    result = data_collector.main(
        ["FiltersReportingCollector.exe"]
    )

    assert result == 0
    acquire.assert_called_once_with("Collector")
    asyncio_run.assert_not_called()
    logger_warning.assert_called_once()


def test_main_releases_lock_after_collector_finishes(monkeypatch):
    instance_lock = Mock()
    acquire = Mock(return_value=instance_lock)
    asyncio_run = Mock()
    collector_coroutine = object()

    monkeypatch.setattr(
        data_collector,
        "acquire_single_instance",
        acquire,
    )
    monkeypatch.setattr(
        data_collector,
        "get_sample_interval",
        Mock(return_value=30),
    )
    monkeypatch.setattr(
        data_collector,
        "run_collector",
        Mock(return_value=collector_coroutine),
    )
    monkeypatch.setattr(
        data_collector.asyncio,
        "run",
        asyncio_run,
    )

    result = data_collector.main(
        ["FiltersReportingCollector.exe", "30"]
    )

    assert result == 0
    acquire.assert_called_once_with("Collector")
    data_collector.get_sample_interval.assert_called_once_with(
        ["FiltersReportingCollector.exe", "30"]
    )
    data_collector.run_collector.assert_called_once_with(30)
    asyncio_run.assert_called_once_with(collector_coroutine)
    instance_lock.release.assert_called_once_with()


def test_main_releases_lock_when_collector_crashes(monkeypatch):
    instance_lock = Mock()

    monkeypatch.setattr(
        data_collector,
        "acquire_single_instance",
        Mock(return_value=instance_lock),
    )
    monkeypatch.setattr(
        data_collector,
        "get_sample_interval",
        Mock(return_value=60),
    )
    monkeypatch.setattr(
        data_collector,
        "run_collector",
        Mock(return_value=object()),
    )
    monkeypatch.setattr(
        data_collector.asyncio,
        "run",
        Mock(side_effect=RuntimeError("boom")),
    )

    try:
        data_collector.main(["collector"])
    except RuntimeError as error:
        assert str(error) == "boom"
    else:
        raise AssertionError("RuntimeError was not raised")

    instance_lock.release.assert_called_once_with()
