from __future__ import annotations

import filters_reporting.database.database_location as database_location


def test_saving_new_database_location_does_not_copy_or_create_database(
    monkeypatch,
    tmp_path,
):
    location_file = tmp_path / "runtime" / "database_location.json"
    new_database = tmp_path / "moved" / "filters.db"

    monkeypatch.setattr(
        database_location,
        "DATABASE_LOCATION_FILE",
        location_file,
    )

    saved = database_location.save_database_path(new_database)

    assert saved == new_database
    assert new_database.parent.is_dir()
    assert not new_database.exists()
    assert location_file.is_file()
    assert database_location.load_database_path() == new_database
