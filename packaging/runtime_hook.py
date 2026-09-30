from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

APP_NAME = "FiltersReporting"


def get_runtime_root() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")

    if local_app_data:
        return Path(local_app_data) / APP_NAME

    return Path.home() / "AppData" / "Local" / APP_NAME


def configure_runtime_directory() -> Path | None:
    if not getattr(
        sys,
        "frozen",
        False,
    ):
        return None

    runtime_root = get_runtime_root()

    for directory in (
        runtime_root,
        runtime_root / "data",
        runtime_root / "logs",
        runtime_root / "reports",
        runtime_root / "certificates",
    ):
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    os.chdir(runtime_root)

    return runtime_root


def clear_collector_stop_request(
    runtime_root: Path | None,
) -> None:
    if runtime_root is None:
        return

    executable_name = Path(sys.executable).stem.lower()

    if executable_name != "filtersreportingcollector":
        return

    database_path = runtime_root / "data" / "filters.db"

    if not database_path.is_file():
        return

    try:
        with sqlite3.connect(database_path) as connection:
            connection.execute("""
                UPDATE collector_control
                SET stop_requested = 0
                WHERE id = 1
                """)

            connection.commit()

    except sqlite3.Error:
        return


runtime_root = configure_runtime_directory()

clear_collector_stop_request(runtime_root)
