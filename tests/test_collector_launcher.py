from __future__ import annotations

import sys
from pathlib import Path

import pytest

from filters_reporting import (
    collector_launcher,
)


def test_get_collector_command_uses_python_module_in_development(
    monkeypatch,
):
    monkeypatch.setattr(
        collector_launcher,
        "is_frozen",
        lambda: False,
    )

    monkeypatch.setattr(
        collector_launcher.sys,
        "executable",
        r"C:\Python\python.exe",
    )

    program, arguments = (
        collector_launcher.get_collector_command(
            45
        )
    )

    assert program == r"C:\Python\python.exe"

    assert arguments == [
        "-m",
        (
            "filters_reporting.collection."
            "data_collector"
        ),
        "45",
    ]


def test_get_collector_command_uses_dedicated_exe_when_frozen(
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

    program, arguments = (
        collector_launcher.get_collector_command(
            30
        )
    )

    assert Path(program) == (
        collector_exe.resolve()
    )

    assert arguments == [
        "30",
    ]


def test_get_installed_collector_path_raises_clear_error_when_missing(
    monkeypatch,
    tmp_path,
):
    gui_dir = (
        tmp_path
        / "FiltersReporting"
    )

    gui_dir.mkdir()

    gui_exe = (
        gui_dir
        / "FiltersReporting.exe"
    )

    gui_exe.write_bytes(b"")

    monkeypatch.setattr(
        collector_launcher.sys,
        "executable",
        str(gui_exe),
    )

    with pytest.raises(
        FileNotFoundError,
        match=(
            "Nie znaleziono programu "
            "collectora"
        ),
    ):
        (
            collector_launcher
            .get_installed_collector_path()
        )


@pytest.mark.parametrize(
    (
        "requested",
        "expected",
    ),
    [
        (1, 5),
        (5, 5),
        (60, 60),
        (300, 300),
        (999, 300),
    ],
)
def test_get_collector_command_clamps_interval(
    monkeypatch,
    requested,
    expected,
):
    monkeypatch.setattr(
        collector_launcher,
        "is_frozen",
        lambda: False,
    )

    _, arguments = (
        collector_launcher.get_collector_command(
            requested
        )
    )

    assert arguments[-1] == str(
        expected
    )
