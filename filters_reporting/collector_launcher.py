from __future__ import annotations

import os
import sys
from pathlib import Path

from filters_reporting.config import LOG_FILE


COLLECTOR_MODULE = (
    "filters_reporting.collection.data_collector"
)

COLLECTOR_EXE_NAME = (
    "FiltersReportingCollector.exe"
)

LOG_FILE_ENV = "FILTERSREPORTING_LOG_FILE"


def is_frozen() -> bool:
    return bool(
        getattr(
            sys,
            "frozen",
            False,
        )
    )


def _normalise_sample_interval(
    sample_interval: int,
) -> int:
    return max(
        5,
        min(
            int(sample_interval),
            300,
        ),
    )


def get_installed_collector_path() -> Path:
    """
    Return the dedicated collector executable used by
    a PyInstaller / Inno Setup installation.

    Expected production layout:

        <app>/
            FiltersReporting/
                FiltersReporting.exe

            FiltersReportingCollector/
                FiltersReportingCollector.exe

    Additional candidates make development smoke builds
    more tolerant of slightly different directory layouts.
    """

    gui_executable = Path(
        sys.executable
    ).resolve()

    candidates = (
        gui_executable.parent.parent
        / "FiltersReportingCollector"
        / COLLECTOR_EXE_NAME,

        gui_executable.parent
        / "FiltersReportingCollector"
        / COLLECTOR_EXE_NAME,

        gui_executable.parent
        / COLLECTOR_EXE_NAME,
    )

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    checked = "\n".join(
        f"- {candidate}"
        for candidate in candidates
    )

    raise FileNotFoundError(
        "Nie znaleziono programu collectora.\n\n"
        "Sprawdzone lokalizacje:\n"
        f"{checked}"
    )


def get_collector_command(
    sample_interval: int = 60,
) -> tuple[str, list[str]]:
    """
    Build the QProcess command for the current runtime.

    Development:
        python -m filters_reporting.collection.data_collector 60

    Installed build:
        FiltersReportingCollector.exe 60
    """

    interval = _normalise_sample_interval(
        sample_interval
    )

    if is_frozen():
        # QProcess inherits the parent process environment.
        # Only frozen GUI/collector builds need an explicit
        # log-path handoff. Development uses LOG_FILE
        # directly and must not leak environment state
        # between tests/process launches.
        log_file = Path(
            LOG_FILE
        ).expanduser()

        if not log_file.is_absolute():
            log_file = (
                log_file.resolve()
            )

        os.environ[
            LOG_FILE_ENV
        ] = str(
            log_file
        )

        collector_path = (
            get_installed_collector_path()
        )

        return (
            str(collector_path),
            [
                str(interval),
            ],
        )

    return (
        sys.executable,
        [
            "-m",
            COLLECTOR_MODULE,
            str(interval),
        ],
    )
