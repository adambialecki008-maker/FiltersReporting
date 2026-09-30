from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from filters_reporting.gui.pages import settings_page as settings_page_module
from filters_reporting.settings_service import AppSettings


class FakeRepository:
    def get_all_filters(self):
        return []


def _settings(tmp_path: Path) -> AppSettings:
    return AppSettings(
        reports_dir=tmp_path / "reports",
        smtp_host="smtp.example.com",
        smtp_port=587,
        username="user@example.com",
        sender="sender@example.com",
        recipients=["recipient@example.com"],
    )


def test_database_change_message_explains_manual_copy(
    monkeypatch,
    tmp_path,
):
    app = QApplication.instance() or QApplication([])
    settings = _settings(tmp_path)
    selected_database = tmp_path / "new" / "filters.db"
    repository = FakeRepository()

    monkeypatch.setattr(
        settings_page_module,
        "load_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        settings_page_module,
        "save_settings",
        lambda value: None,
    )

    messages = []

    monkeypatch.setattr(
        settings_page_module.QMessageBox,
        "information",
        lambda parent, title, message: messages.append(
            (title, message)
        ),
    )

    page = settings_page_module.SettingsPage(
        repository=repository,
    )

    monkeypatch.setattr(
        page.general_tab,
        "database_location_changed",
        lambda: True,
    )
    monkeypatch.setattr(
        page.general_tab,
        "get_database_path_from_form",
        lambda: selected_database,
    )
    monkeypatch.setattr(
        page.general_tab,
        "save_database_location",
        lambda: selected_database,
    )
    monkeypatch.setattr(
        page.general_tab,
        "get_smtp_password",
        lambda: "",
    )
    monkeypatch.setattr(
        page,
        "build_settings_from_tabs",
        lambda: settings,
    )
    monkeypatch.setattr(
        page,
        "validate_tabs",
        lambda value: (True, ""),
    )
    monkeypatch.setattr(
        page,
        "load_tabs_from_settings",
        lambda: None,
    )

    page.save_settings_from_tabs()

    assert len(messages) == 1

    title, message = messages[0]

    assert title == "Ustawienia"
    assert str(selected_database) in message
    assert "nową, pustą bazę" in message
    assert "NIE jest przenoszona automatycznie" in message
    assert "ręcznie" in message
    assert ".db" in message
    assert "collector" in message

    page.close()
    app.processEvents()
