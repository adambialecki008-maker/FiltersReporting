from __future__ import annotations

import json
from pathlib import Path

from filters_reporting.config import DATA_DIR
from filters_reporting.runtime_paths import (
    DATABASE_PATH,
    RUNTIME_ROOT,
    is_frozen,
)


if is_frozen():
    DATABASE_LOCATION_FILE = (
        RUNTIME_ROOT
        / "database_location.json"
    )
else:
    DATABASE_LOCATION_FILE = (
        DATA_DIR
        / "database_location.json"
    )


DEFAULT_DATABASE_PATH = Path(DATABASE_PATH)


def normalise_database_path(
    database_path: str | Path,
) -> Path:
    path = Path(database_path).expanduser()

    if not path.is_absolute():
        path = path.resolve()

    return path


def load_database_path() -> Path:
    if not DATABASE_LOCATION_FILE.is_file():
        return DEFAULT_DATABASE_PATH

    try:
        data = json.loads(
            DATABASE_LOCATION_FILE.read_text(
                encoding="utf-8",
            )
        )

    except (
        OSError,
        json.JSONDecodeError,
        TypeError,
    ):
        return DEFAULT_DATABASE_PATH

    if not isinstance(data, dict):
        return DEFAULT_DATABASE_PATH

    raw_path = str(
        data.get(
            "database_path",
            "",
        )
    ).strip()

    if not raw_path:
        return DEFAULT_DATABASE_PATH

    return normalise_database_path(raw_path)


def save_database_path(
    database_path: str | Path,
) -> Path:
    path = normalise_database_path(database_path)

    if path.exists() and path.is_dir():
        raise ValueError(
            "Ścieżka bazy danych wskazuje katalog, "
            "a nie plik."
        )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    DATABASE_LOCATION_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    DATABASE_LOCATION_FILE.write_text(
        json.dumps(
            {
                "database_path": str(path),
            },
            ensure_ascii=False,
            indent=4,
        ),
        encoding="utf-8",
    )

    return path


def reset_database_path() -> Path:
    if DATABASE_LOCATION_FILE.exists():
        DATABASE_LOCATION_FILE.unlink()

    return DEFAULT_DATABASE_PATH
