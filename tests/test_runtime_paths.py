from pathlib import Path

import filters_reporting.runtime_paths as runtime_paths


def test_runtime_root_uses_project_root_when_not_frozen(
    monkeypatch,
):
    monkeypatch.setattr(
        runtime_paths,
        "is_frozen",
        lambda: False,
    )

    expected = Path(runtime_paths.__file__).resolve().parent.parent

    assert runtime_paths.get_runtime_root() == expected


def test_runtime_root_uses_local_app_data_when_frozen(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        runtime_paths,
        "is_frozen",
        lambda: True,
    )

    monkeypatch.setenv(
        "LOCALAPPDATA",
        str(tmp_path),
    )

    assert runtime_paths.get_runtime_root() == tmp_path / "FiltersReporting"


def test_database_path_is_inside_data_directory():
    assert runtime_paths.DATABASE_PATH.name == "filters.db"

    assert runtime_paths.DATABASE_PATH.parent.name == "data"
