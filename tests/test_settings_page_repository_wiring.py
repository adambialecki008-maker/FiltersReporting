from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from filters_reporting.gui.pages import (
    settings_page as settings_page_module,
)
from filters_reporting.settings_service import AppSettings


class FakeRepository:
    def get_all_filters(self):
        return []


def _settings(tmp_path):
    return AppSettings(
        reports_dir=tmp_path,
        smtp_host="",
        smtp_port=587,
        username="",
        sender="",
        recipients=[],
    )


def test_settings_page_passes_repository_to_opc_client_tab(
    monkeypatch,
    tmp_path,
):
    app = QApplication.instance() or QApplication([])

    settings = _settings(tmp_path)
    repository = FakeRepository()

    monkeypatch.setattr(
        settings_page_module,
        "load_settings",
        lambda: settings,
    )

    page = settings_page_module.SettingsPage(
        repository=repository,
    )

    assert page.repository is repository
    assert page.opc_client_tab.repository is repository

    machine_combo = page.opc_client_tab.machine_combo

    assert machine_combo.count() == 1
    assert machine_combo.itemText(0) == "Brak filtrów"
    assert machine_combo.currentData() is None
    assert not machine_combo.isEnabled()

    page.close()
    app.processEvents()
