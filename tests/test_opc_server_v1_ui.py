from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from filters_reporting.gui.pages import (
    settings_opc_server_tab as server_tab_module,
)
from filters_reporting.opcua.security import (
    build_server_security_policies,
)
from filters_reporting.settings_service import AppSettings


def _app():
    return QApplication.instance() or QApplication([])


def _settings(
    tmp_path: Path,
    **overrides,
):
    values = dict(
        reports_dir=tmp_path / "reports",
        smtp_host="",
        smtp_port=465,
        username="",
        sender="",
        recipients=[],
        opc_server_enabled=True,
        opc_server_endpoint=(
            "opc.tcp://127.0.0.1:4850/filtersreporting/"
        ),
        opc_server_namespace="urn:FiltersReporting:Server",
        opc_server_application_uri=(
            "urn:test:FiltersReporting:OPCServer"
        ),
        opc_server_security_policy="None",
        opc_server_security_mode="None",
        opc_server_allow_no_security=False,
        opc_server_allow_anonymous=True,
        opc_server_username="",
        opc_server_password_hash="",
    )

    values.update(overrides)

    return AppSettings(**values)


def test_none_policy_is_already_no_security(
    tmp_path: Path,
):
    app = _app()

    tab = server_tab_module.OpcServerSettingsTab(
        _settings(tmp_path)
    )

    assert tab.allow_no_security_checkbox.isChecked()
    assert not tab.allow_no_security_checkbox.isEnabled()

    assert "już jako NoSecurity" in (
        tab.no_security_state_label.text()
    )

    tab.close()
    app.processEvents()


def test_secure_endpoint_can_add_no_security_for_anonymous(
    tmp_path: Path,
):
    app = _app()

    tab = server_tab_module.OpcServerSettingsTab(
        _settings(
            tmp_path,
            opc_server_security_policy="Basic256Sha256",
            opc_server_security_mode="SignAndEncrypt",
        )
    )

    assert tab.allow_no_security_checkbox.isEnabled()

    tab.allow_no_security_checkbox.setChecked(True)

    updated = tab.apply_to_settings(
        tab.settings
    )

    assert updated.opc_server_allow_no_security is True

    policies = build_server_security_policies(
        policy=(
            updated.opc_server_security_policy
        ),
        mode=(
            updated.opc_server_security_mode
        ),
        allow_no_security=(
            updated.opc_server_allow_no_security
        ),
    )

    policy_names = {
        policy.name
        for policy in policies
    }

    assert "NoSecurity" in policy_names

    tab.close()
    app.processEvents()


def test_username_password_disables_additional_no_security(
    tmp_path: Path,
):
    app = _app()

    tab = server_tab_module.OpcServerSettingsTab(
        _settings(
            tmp_path,
            opc_server_security_policy="Basic256Sha256",
            opc_server_security_mode="SignAndEncrypt",
            opc_server_username="operator",
            opc_server_password_hash="stored-hash",
        )
    )

    assert (
        not tab.allow_no_security_checkbox.isChecked()
    )

    assert (
        not tab.allow_no_security_checkbox.isEnabled()
    )

    assert "Username/Password" in (
        tab.no_security_state_label.text()
    )

    tab.close()
    app.processEvents()


def test_server_certificate_paths_are_separate_from_filter_certs(
    monkeypatch,
    tmp_path: Path,
):
    monkeypatch.setattr(
        server_tab_module,
        "CERTIFICATES_DIR",
        tmp_path,
    )

    paths = (
        server_tab_module
        .OpcServerSettingsTab
        ._server_certificate_paths()
    )

    assert paths.certificate == (
        tmp_path
        / "opc_server"
        / "filters_reporting_opc_server.der"
    )

    assert paths.private_key == (
        tmp_path
        / "opc_server"
        / "private"
        / "filters_reporting_opc_server_key.pem"
    )

    assert (
        paths.certificate
        != paths.private_key
    )
