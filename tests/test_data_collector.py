import asyncio

import pytest

from unittest.mock import (
    AsyncMock,
    Mock,
    call,
)

from filters_reporting.collection import data_collector


def test_save_samples_saves_all_samples():
    repository = Mock()

    sample_1 = Mock(filter_id=1)
    sample_2 = Mock(filter_id=2)

    data_collector.save_samples(
        repository,
        [sample_1, sample_2],
    )

    assert repository.save_filter_sample.call_args_list == [
        call(sample_1),
        call(sample_2),
    ]


def test_save_samples_continues_when_one_sample_fails(
    monkeypatch,
):
    repository = Mock()

    sample_1 = Mock(filter_id=1)
    sample_2 = Mock(filter_id=2)

    repository.save_filter_sample.side_effect = [
        Exception("DB error"),
        None,
    ]

    logger_exception = Mock()

    monkeypatch.setattr(
        data_collector.logger,
        "exception",
        logger_exception,
    )

    data_collector.save_samples(
        repository,
        [sample_1, sample_2],
    )

    assert repository.save_filter_sample.call_count == 2

    logger_exception.assert_called_once_with("Błąd zapisu próbki filter_id=1")


def test_update_connection_statuses_marks_successful_filters_as_connected():
    repository = Mock()

    filter_1 = Mock(filter_id=1)
    filter_2 = Mock(filter_id=2)

    sample_1 = Mock(filter_id=1)
    sample_2 = Mock(filter_id=2)

    data_collector.update_connection_statuses(
        repository,
        [filter_1, filter_2],
        [sample_1, sample_2],
    )

    assert repository.set_filter_connection_status.call_args_list == [
        call(1, True),
        call(2, True),
    ]


def test_update_connection_statuses_marks_failed_filter_as_disconnected():
    repository = Mock()

    filter_1 = Mock(filter_id=1)
    filter_2 = Mock(filter_id=2)

    sample_1 = Mock(filter_id=1)

    data_collector.update_connection_statuses(
        repository,
        [filter_1, filter_2],
        [sample_1],
    )

    assert repository.set_filter_connection_status.call_args_list == [
        call(1, True),
        call(2, False),
    ]


@pytest.mark.asyncio
async def test_run_collector_runs_one_complete_successful_cycle(
    monkeypatch,
):
    repository = Mock()

    filter_1 = Mock(filter_id=1)
    filter_2 = Mock(filter_id=2)

    sample_1 = Mock(filter_id=1)
    sample_2 = Mock(filter_id=2)

    repository.get_active_filters.return_value = [
        filter_1,
        filter_2,
    ]

    repository_class = Mock(return_value=repository)

    get_current_samples = AsyncMock(
        return_value=[
            sample_1,
            sample_2,
        ]
    )

    disconnect_all_clients = AsyncMock()

    logger_info = Mock()

    monkeypatch.setattr(
        data_collector,
        "wait_for_next_cycle_or_stop",
        AsyncMock(
            side_effect=[
                False,
                True,
            ]
        ),
    )
    monkeypatch.setattr(
        data_collector,
        "FiltersRepository",
        repository_class,
    )

    monkeypatch.setattr(
        data_collector,
        "get_current_samples",
        get_current_samples,
    )

    monkeypatch.setattr(
        data_collector,
        "disconnect_all_clients",
        disconnect_all_clients,
    )
    monkeypatch.setattr(
        data_collector.logger,
        "info",
        logger_info,
    )
    monkeypatch.setattr(
        data_collector,
        "start_stop_listener",
        Mock(),
    )
    await data_collector.run_collector()

    repository.create_table.assert_called_once()

    repository.get_active_filters.assert_called_once()

    get_current_samples.assert_awaited_once_with(
        [
            filter_1,
            filter_2,
        ]
    )

    assert repository.save_filter_sample.call_args_list == [
        call(sample_1),
        call(sample_2),
    ]

    disconnect_all_clients.assert_awaited_once()

    assert any(
        "OPC_OK" in call_args.args[0] for call_args in logger_info.call_args_list
    )


@pytest.mark.asyncio
async def test_run_collector_sets_opc_error_when_not_all_filters_return_sample(
    monkeypatch,
):
    repository = Mock()

    filter_1 = Mock(filter_id=1)
    filter_2 = Mock(filter_id=2)

    sample_1 = Mock(filter_id=1)

    repository.get_active_filters.return_value = [
        filter_1,
        filter_2,
    ]

    monkeypatch.setattr(
        data_collector,
        "FiltersRepository",
        Mock(return_value=repository),
    )

    monkeypatch.setattr(
        data_collector,
        "get_current_samples",
        AsyncMock(return_value=[sample_1]),
    )

    disconnect_all_clients = AsyncMock()

    monkeypatch.setattr(
        data_collector,
        "disconnect_all_clients",
        disconnect_all_clients,
    )

    logger_info = Mock()

    monkeypatch.setattr(
        data_collector.logger,
        "info",
        logger_info,
    )

    monkeypatch.setattr(
        data_collector,
        "wait_for_next_cycle_or_stop",
        AsyncMock(
            side_effect=[
                False,
                True,
            ]
        ),
    )
    monkeypatch.setattr(
        data_collector,
        "start_stop_listener",
        Mock(),
    )

    await data_collector.run_collector()

    assert repository.save_filter_sample.call_args_list == [
        call(sample_1),
    ]

    assert any(
        "OPC_ERROR" in call_args.args[0] for call_args in logger_info.call_args_list
    )

    disconnect_all_clients.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_collector_logs_cycle_error_and_keeps_running(
    monkeypatch,
):
    repository = Mock()

    repository.get_active_filters.side_effect = RuntimeError("Test error")

    monkeypatch.setattr(
        data_collector,
        "FiltersRepository",
        Mock(return_value=repository),
    )

    disconnect_all_clients = AsyncMock()

    monkeypatch.setattr(
        data_collector,
        "disconnect_all_clients",
        disconnect_all_clients,
    )

    logger_exception = Mock()

    monkeypatch.setattr(
        data_collector.logger,
        "exception",
        logger_exception,
    )

    monkeypatch.setattr(
        data_collector,
        "wait_for_next_cycle_or_stop",
        AsyncMock(
            side_effect=[
                False,
                True,
            ]
        ),
    )
    monkeypatch.setattr(
        data_collector,
        "start_stop_listener",
        Mock(),
    )
    await data_collector.run_collector()

    logger_exception.assert_called_once_with("Błąd całego cyklu collectora")

    disconnect_all_clients.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_collector_updates_connection_statuses(
    monkeypatch,
):
    repository = Mock()

    filter_1 = Mock(filter_id=1)
    filter_2 = Mock(filter_id=2)

    sample_1 = Mock(filter_id=1)

    repository.get_active_filters.return_value = [
        filter_1,
        filter_2,
    ]

    monkeypatch.setattr(
        data_collector,
        "FiltersRepository",
        Mock(return_value=repository),
    )

    monkeypatch.setattr(
        data_collector,
        "get_current_samples",
        AsyncMock(return_value=[sample_1]),
    )

    update_connection_statuses = Mock()

    monkeypatch.setattr(
        data_collector,
        "update_connection_statuses",
        update_connection_statuses,
    )

    monkeypatch.setattr(
        data_collector,
        "disconnect_all_clients",
        AsyncMock(),
    )

    monkeypatch.setattr(
        data_collector,
        "wait_for_next_cycle_or_stop",
        AsyncMock(
            side_effect=[
                False,
                True,
            ]
        ),
    )
    monkeypatch.setattr(
        data_collector,
        "start_stop_listener",
        Mock(),
    )
    await data_collector.run_collector()

    update_connection_statuses.assert_called_once_with(
        repository,
        [filter_1, filter_2],
        [sample_1],
    )


@pytest.mark.asyncio
async def test_wait_for_next_cycle_returns_true_when_database_stop_is_requested():
    repository = Mock()
    repository.is_collector_stop_requested.return_value = True
    stop_event = asyncio.Event()
    result = await data_collector.wait_for_next_cycle_or_stop(
        repository,
        stop_event,
        60,
    )
    assert result is True


@pytest.mark.asyncio
async def test_wait_for_next_cycle_returns_true_when_local_stop_event_is_set():
    repository = Mock()
    repository.is_collector_stop_requested.return_value = False
    stop_event = asyncio.Event()
    stop_event.set()
    result = await data_collector.wait_for_next_cycle_or_stop(
        repository,
        stop_event,
        60,
    )
    assert result is True
