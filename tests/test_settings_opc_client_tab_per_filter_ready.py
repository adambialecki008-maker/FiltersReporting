from __future__ import annotations

import os
from dataclasses import replace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from filters_reporting.gui.pages import settings_opc_client_tab as module
from filters_reporting.gui.pages.settings_opc_client_tab import (
    OpcClientSettingsTab,
)
from filters_reporting.models.filter import Filter
from filters_reporting.settings_service import get_default_settings


class FakeRepository:
    def __init__(self, filters):
        self.filters = {
            int(item.filter_id): item
            for item in filters
        }
        self.opc_url_updates = []
        self.opc_settings_updates = []

    def get_all_filters(self):
        return [
            self.filters[key]
            for key in sorted(self.filters)
        ]

    def update_filter_opc_url(self, name, opc_url):
        self.opc_url_updates.append((name, opc_url))

        for filter_id, item in self.filters.items():
            if item.name == name:
                self.filters[filter_id] = replace(
                    item,
                    opc_url=opc_url,
                )
                return

        raise AssertionError("Nie znaleziono filtra")

    def update_filter_opc_settings(self, filter_obj):
        self.opc_settings_updates.append(filter_obj)
        self.filters[int(filter_obj.filter_id)] = filter_obj


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def credential_store(monkeypatch):
    passwords = {}

    monkeypatch.setattr(
        module,
        "set_filter_password",
        lambda filter_id, password: passwords.__setitem__(
            int(filter_id),
            password,
        ),
    )
    monkeypatch.setattr(
        module,
        "delete_filter_password",
        lambda filter_id: passwords.pop(
            int(filter_id),
            None,
        ),
    )
    monkeypatch.setattr(
        module,
        "has_filter_password",
        lambda filter_id: bool(
            passwords.get(int(filter_id))
        ),
    )

    return passwords


def _make_repository():
    return FakeRepository(
        [
            Filter(
                filter_id=1,
                name="Filter 1",
                opc_url="opc.tcp://10.0.0.1:4840",
            ),
            Filter(
                filter_id=2,
                name="Filter 2",
                opc_url="opc.tcp://10.0.0.2:4840",
            ),
        ]
    )


def test_saves_authentication_and_endpoint_per_filter(
    qapp,
    credential_store,
):
    repository = _make_repository()

    tab = OpcClientSettingsTab(
        get_default_settings(),
        repository=repository,
    )

    assert tab.current_filter_id() == 1

    tab.endpoint_edit.setText(
        "opc.tcp://192.168.10.101:4840"
    )
    tab.auth_combo.setCurrentText(
        "UsernamePassword"
    )
    tab.username_edit.setText("operator_f1")
    tab.password_edit.setText("secret-f1")

    assert tab.save_current_machine(
        show_message=False
    )

    filter_1 = repository.filters[1]
    filter_2 = repository.filters[2]

    assert filter_1.opc_url == (
        "opc.tcp://192.168.10.101:4840"
    )
    assert filter_1.opc_auth_type == (
        "UsernamePassword"
    )
    assert filter_1.opc_username == "operator_f1"
    assert credential_store[1] == "secret-f1"

    assert filter_2.opc_url == (
        "opc.tcp://10.0.0.2:4840"
    )
    assert filter_2.opc_auth_type == "Anonymous"
    assert 2 not in credential_store


def test_each_machine_keeps_own_security_configuration(
    qapp,
    credential_store,
    tmp_path,
):
    repository = _make_repository()

    tab = OpcClientSettingsTab(
        get_default_settings(),
        repository=repository,
    )

    certificate = tmp_path / "f1.der"
    private_key = tmp_path / "f1.pem"
    trusted = tmp_path / "trusted"

    certificate.write_bytes(b"certificate")
    private_key.write_bytes(b"private-key")
    trusted.mkdir()

    tab.policy_combo.setCurrentText(
        "Basic256Sha256"
    )
    tab.mode_combo.setCurrentText(
        "SignAndEncrypt"
    )
    tab.application_uri_edit.setText(
        "urn:test:filter:1"
    )
    tab.certificate_edit.setText(
        str(certificate)
    )
    tab.private_key_edit.setText(
        str(private_key)
    )
    tab.trusted_dir_edit.setText(
        str(trusted)
    )
    tab.validate_checkbox.setChecked(True)

    assert tab.save_current_machine(
        show_message=False
    )

    filter_1 = repository.filters[1]
    filter_2 = repository.filters[2]

    assert filter_1.opc_security_policy == (
        "Basic256Sha256"
    )
    assert filter_1.opc_security_mode == (
        "SignAndEncrypt"
    )
    assert filter_1.opc_application_uri == (
        "urn:test:filter:1"
    )
    assert filter_1.opc_client_certificate_path == (
        str(certificate)
    )

    assert filter_2.opc_security_policy == "None"
    assert filter_2.opc_security_mode == "None"
    assert filter_2.opc_client_certificate_path is None


def test_switch_to_anonymous_removes_stored_password(
    qapp,
    credential_store,
):
    repository = _make_repository()
    credential_store[1] = "old-secret"

    repository.filters[1] = replace(
        repository.filters[1],
        opc_auth_type="UsernamePassword",
        opc_username="operator",
    )

    tab = OpcClientSettingsTab(
        get_default_settings(),
        repository=repository,
    )

    tab.auth_combo.setCurrentText("Anonymous")

    assert tab.save_current_machine(
        show_message=False
    )

    assert 1 not in credential_store
    assert repository.filters[1].opc_auth_type == (
        "Anonymous"
    )
