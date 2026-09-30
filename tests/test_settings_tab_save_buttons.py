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


def test_settings_page_has_separate_save_buttons(
    monkeypatch,
    tmp_path,
):
    app = QApplication.instance() or QApplication([])

    settings = AppSettings(
        reports_dir=tmp_path,
        smtp_host="",
        smtp_port=587,
        username="",
        sender="",
        recipients=[],
    )

    monkeypatch.setattr(
        settings_page_module,
        "load_settings",
        lambda: settings,
    )

    page = settings_page_module.SettingsPage(
        repository=FakeRepository(),
    )

    assert page.general_save_button.text() == "Zapisz Ogólne"
    assert (
        page.server_save_button.text()
        == "Zapisz OPC UA Server"
    )

    # Globalny przycisk "Zapisz ustawienia" został usunięty.
    assert not hasattr(page, "save_button")

    # OPC UA Client ma własny zapis per maszyna.
    assert hasattr(
        page.opc_client_tab,
        "save_current_machine",
    )

    page.close()
    app.processEvents()
