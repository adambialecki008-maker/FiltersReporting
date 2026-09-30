from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "FiltersReporting"


def is_frozen() -> bool:
    return bool(
        getattr(
            sys,
            "frozen",
            False,
        )
    )


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_runtime_root() -> Path:
    if not is_frozen():
        return get_project_root()

    local_app_data = os.environ.get("LOCALAPPDATA")

    if local_app_data:
        return Path(local_app_data) / APP_NAME

    return Path.home() / "AppData" / "Local" / APP_NAME


RUNTIME_ROOT = get_runtime_root()
DATA_DIR = RUNTIME_ROOT / "data"
DATABASE_PATH = DATA_DIR / "filters.db"
LOG_DIR = RUNTIME_ROOT / "logs"
LOG_FILE = LOG_DIR / "filters_reporting.log"
REPORTS_DIR = RUNTIME_ROOT / "reports"
SETTINGS_FILE = RUNTIME_ROOT / "settings.json"
CERTIFICATES_DIR = RUNTIME_ROOT / "certificates"


def ensure_runtime_directories() -> None:
    for directory in (
        RUNTIME_ROOT,
        DATA_DIR,
        LOG_DIR,
        REPORTS_DIR,
        CERTIFICATES_DIR,
    ):
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )
