from pathlib import Path

import filters_reporting.database.database_location as database_location


def test_load_database_path_returns_default_when_file_is_missing(
    monkeypatch,
    tmp_path,
):
    location_file = tmp_path / "database_location.json"
    default_path = tmp_path / "data" / "filters.db"

    monkeypatch.setattr(
        database_location,
        "DATABASE_LOCATION_FILE",
        location_file,
    )

    monkeypatch.setattr(
        database_location,
        "DEFAULT_DATABASE_PATH",
        default_path,
    )

    assert (
        database_location.load_database_path()
        == default_path
    )


def test_save_and_load_database_path(
    monkeypatch,
    tmp_path,
):
    location_file = tmp_path / "database_location.json"
    selected_path = tmp_path / "custom" / "client.db"

    monkeypatch.setattr(
        database_location,
        "DATABASE_LOCATION_FILE",
        location_file,
    )

    saved_path = database_location.save_database_path(
        selected_path
    )

    loaded_path = database_location.load_database_path()

    assert saved_path == selected_path
    assert loaded_path == selected_path
    assert selected_path.parent.is_dir()


def test_load_database_path_returns_default_for_invalid_json(
    monkeypatch,
    tmp_path,
):
    location_file = tmp_path / "database_location.json"
    default_path = tmp_path / "data" / "filters.db"

    location_file.write_text(
        "{broken json",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        database_location,
        "DATABASE_LOCATION_FILE",
        location_file,
    )

    monkeypatch.setattr(
        database_location,
        "DEFAULT_DATABASE_PATH",
        default_path,
    )

    assert (
        database_location.load_database_path()
        == default_path
    )


def test_save_database_path_rejects_directory(
    monkeypatch,
    tmp_path,
):
    location_file = tmp_path / "database_location.json"

    monkeypatch.setattr(
        database_location,
        "DATABASE_LOCATION_FILE",
        location_file,
    )

    directory = tmp_path / "database_directory"
    directory.mkdir()

    try:
        database_location.save_database_path(
            directory
        )

    except ValueError:
        pass

    else:
        raise AssertionError(
            "Expected ValueError for directory path"
        )


def test_reset_database_path_removes_saved_location(
    monkeypatch,
    tmp_path,
):
    location_file = tmp_path / "database_location.json"
    default_path = tmp_path / "data" / "filters.db"

    location_file.write_text(
        '{"database_path": "custom.db"}',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        database_location,
        "DATABASE_LOCATION_FILE",
        location_file,
    )

    monkeypatch.setattr(
        database_location,
        "DEFAULT_DATABASE_PATH",
        default_path,
    )

    result = database_location.reset_database_path()

    assert result == default_path
    assert not location_file.exists()
