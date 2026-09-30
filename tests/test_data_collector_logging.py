from __future__ import annotations

import logging
from pathlib import Path

from filters_reporting.collection import (
    data_collector,
)


def test_configure_logging_creates_file_and_writes_info(
    monkeypatch,
    tmp_path,
):
    log_file = (
        tmp_path
        / "logs"
        / "collector.log"
    )

    monkeypatch.setattr(
        data_collector,
        "LOG_FILE",
        log_file,
    )

    configured_path = (
        data_collector
        .configure_logging()
    )

    data_collector.logger.info(
        "collector-test-entry"
    )

    data_collector.flush_logging()

    assert configured_path == (
        log_file.resolve()
    )

    assert log_file.is_file()

    content = (
        log_file.read_text(
            encoding="utf-8"
        )
    )

    assert (
        "collector-test-entry"
        in content
    )


def test_configure_logging_does_not_duplicate_owned_handler(
    monkeypatch,
    tmp_path,
):
    log_file = (
        tmp_path
        / "collector.log"
    )

    monkeypatch.setattr(
        data_collector,
        "LOG_FILE",
        log_file,
    )

    data_collector.configure_logging()
    data_collector.configure_logging()

    owned_handlers = [
        handler
        for handler
        in data_collector.logger.handlers
        if getattr(
            handler,
            data_collector._HANDLER_MARKER,
            False,
        )
    ]

    assert len(
        owned_handlers
    ) == 1


def test_configure_logging_forces_info_level(
    monkeypatch,
    tmp_path,
):
    log_file = (
        tmp_path
        / "collector.log"
    )

    monkeypatch.setattr(
        data_collector,
        "LOG_FILE",
        log_file,
    )

    data_collector.configure_logging()

    assert (
        data_collector.logger.level
        == logging.INFO
    )

    owned_handler = next(
        handler
        for handler
        in data_collector.logger.handlers
        if getattr(
            handler,
            data_collector._HANDLER_MARKER,
            False,
        )
    )

    assert (
        owned_handler.level
        == logging.INFO
    )
