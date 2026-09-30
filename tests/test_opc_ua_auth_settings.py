import json
from pathlib import Path

from filters_reporting import settings_service
from filters_reporting.opcua.auth import (
    OpcUaAuthenticationConfig,
    hash_password,
)
from filters_reporting.settings_service import (
    AppSettings,
    load_settings,
    save_settings,
)


def build_settings(
    **kwargs,
) -> AppSettings:
    base = {
        "reports_dir": Path("reports"),
        "smtp_host": "smtp.example.com",
        "smtp_port": 465,
        "username": "smtp-user",
        "sender": "sender@example.com",
        "recipients": [
            "receiver@example.com",
        ],
    }

    base.update(kwargs)

    return AppSettings(
        **base,
    )


def test_app_settings_has_default_opc_server_authentication():
    settings = build_settings()

    assert settings.opc_server_allow_anonymous is True

    assert settings.opc_server_username == ""

    assert settings.opc_server_password_hash == ""


def test_app_settings_builds_opc_server_authentication_config():
    password_hash = hash_password("Password123!")

    settings = build_settings(
        opc_server_allow_anonymous=False,
        opc_server_username="operator",
        opc_server_password_hash=(password_hash),
    )

    config = settings.to_opc_server_authentication_config()

    assert isinstance(
        config,
        OpcUaAuthenticationConfig,
    )

    assert config.allow_anonymous is False

    assert config.username == "operator"

    assert config.password_hash == password_hash


def test_opc_server_authentication_config_supports_anonymous_and_login():
    password_hash = hash_password("Password123!")

    settings = build_settings(
        opc_server_allow_anonymous=True,
        opc_server_username="operator",
        opc_server_password_hash=(password_hash),
    )

    config = settings.to_opc_server_authentication_config()

    assert config.allow_anonymous is True

    assert config.username_enabled is True


def test_opc_server_authentication_config_supports_login_only():
    password_hash = hash_password("Password123!")

    settings = build_settings(
        opc_server_allow_anonymous=False,
        opc_server_username="operator",
        opc_server_password_hash=(password_hash),
    )

    config = settings.to_opc_server_authentication_config()

    config.validate()

    assert config.allow_anonymous is False

    assert config.username_enabled is True


def test_opc_server_authentication_is_saved_and_loaded(
    monkeypatch,
    tmp_path,
):
    settings_file = tmp_path / "settings.json"

    monkeypatch.setattr(
        settings_service,
        "SETTINGS_FILE",
        settings_file,
    )

    password_hash = hash_password("Password123!")

    settings = build_settings(
        reports_dir=(tmp_path / "reports"),
        opc_server_allow_anonymous=False,
        opc_server_username="operator",
        opc_server_password_hash=(password_hash),
    )

    save_settings(settings)

    raw = json.loads(
        settings_file.read_text(
            encoding="utf-8",
        )
    )

    assert raw["opc_ua_server"]["allow_anonymous"] is False

    assert raw["opc_ua_server"]["username"] == "operator"

    assert raw["opc_ua_server"]["password_hash"] == password_hash

    loaded = load_settings()

    assert loaded.opc_server_allow_anonymous is False

    assert loaded.opc_server_username == "operator"

    assert loaded.opc_server_password_hash == password_hash
