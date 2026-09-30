from __future__ import annotations

import os
from pathlib import Path

from filters_reporting import (
    collector_launcher,
)
from filters_reporting.collection import (
    data_collector,
)


def test_launcher_does_not_set_log_env_in_development(
    monkeypatch,
    tmp_path,
):
    log_file = (
        tmp_path
        / "runtime"
        / "logs"
        / "collector.log"
    )

    monkeypatch.setattr(
        collector_launcher,
        "LOG_FILE",
        log_file,
    )

    monkeypatch.setattr(
        collector_launcher,
        "is_frozen",
        lambda: False,
    )

    monkeypatch.delenv(
        collector_launcher.LOG_FILE_ENV,
        raising=False,
    )

    collector_launcher.get_collector_command(
        60
    )

    assert (
        collector_launcher.LOG_FILE_ENV
        not in os.environ
    )


def test_launcher_hands_exact_log_path_when_frozen(
    monkeypatch,
    tmp_path,
):
    gui_dir = (
        tmp_path
        / "FiltersReporting"
    )

    collector_dir = (
        tmp_path
        / "FiltersReportingCollector"
    )

    gui_dir.mkdir()
    collector_dir.mkdir()

    gui_exe = (
        gui_dir
        / "FiltersReporting.exe"
    )

    collector_exe = (
        collector_dir
        / "FiltersReportingCollector.exe"
    )

    gui_exe.write_bytes(b"")
    collector_exe.write_bytes(b"")

    log_file = (
        tmp_path
        / "runtime"
        / "logs"
        / "collector.log"
    )

    monkeypatch.setattr(
        collector_launcher,
        "LOG_FILE",
        log_file,
    )

    monkeypatch.setattr(
        collector_launcher,
        "is_frozen",
        lambda: True,
    )

    monkeypatch.setattr(
        collector_launcher.sys,
        "executable",
        str(gui_exe),
    )

    monkeypatch.delenv(
        collector_launcher.LOG_FILE_ENV,
        raising=False,
    )

    collector_launcher.get_collector_command(
        60
    )

    assert os.environ[
        collector_launcher.LOG_FILE_ENV
    ] == str(
        log_file.resolve()
    )


def test_collector_uses_log_file_directly_in_development(
    monkeypatch,
    tmp_path,
):
    log_file = (
        tmp_path
        / "dev"
        / "collector.log"
    )

    monkeypatch.setattr(
        data_collector,
        "LOG_FILE",
        log_file,
    )

    monkeypatch.setattr(
        data_collector.sys,
        "frozen",
        False,
        raising=False,
    )

    monkeypatch.setenv(
        data_collector.LOG_FILE_ENV,
        str(
            tmp_path
            / "wrong"
            / "collector.log"
        ),
    )

    configured_path = (
        data_collector
        .configure_logging()
    )

    assert configured_path == (
        log_file.resolve()
    )


def test_collector_uses_handed_off_log_path_when_frozen(
    monkeypatch,
    tmp_path,
):
    gui_log_file = (
        tmp_path
        / "gui-runtime"
        / "logs"
        / "collector.log"
    )

    different_default = (
        tmp_path
        / "collector-runtime"
        / "logs"
        / "collector.log"
    )

    monkeypatch.setattr(
        data_collector,
        "LOG_FILE",
        different_default,
    )

    monkeypatch.setattr(
        data_collector.sys,
        "frozen",
        True,
        raising=False,
    )

    monkeypatch.setenv(
        data_collector.LOG_FILE_ENV,
        str(
            gui_log_file.resolve()
        ),
    )

    configured_path = (
        data_collector
        .configure_logging()
    )

    data_collector.logger.info(
        "same-log-file-test"
    )

    data_collector.flush_logging()

    assert configured_path == (
        gui_log_file.resolve()
    )

    assert gui_log_file.is_file()

    assert (
        "same-log-file-test"
        in gui_log_file.read_text(
            encoding="utf-8"
        )
    )
