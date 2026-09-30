from pathlib import Path

from filters_reporting.opcua.security import (
    OpcUaSecurityConfig,
)
from filters_reporting.settings_service import (
    AppSettings,
)


def make_settings(
    tmp_path,
):
    return AppSettings(
        reports_dir=(tmp_path / "reports"),
        smtp_host=("smtp.example.com"),
        smtp_port=465,
        username=("test@example.com"),
        sender=("test@example.com"),
        recipients=["receiver@example.com"],
        opc_client_security_policy=("Basic256Sha256"),
        opc_client_security_mode=("SignAndEncrypt"),
        opc_client_application_uri=("urn:test:FiltersReporting"),
        opc_client_certificate_path=(tmp_path / "application.der"),
        opc_client_private_key_path=(tmp_path / "application.pem"),
        opc_client_trusted_dir=(tmp_path / "trusted"),
        opc_client_server_certificate_path=(tmp_path / "server.der"),
        opc_client_validate_server_certificate=(True),
    )


def test_settings_build_opc_client_security_config(
    tmp_path,
):
    settings = make_settings(tmp_path)

    config = settings.to_opc_client_security_config()

    assert isinstance(
        config,
        OpcUaSecurityConfig,
    )

    assert config.policy == "Basic256Sha256"

    assert config.mode == "SignAndEncrypt"

    assert config.application_uri == "urn:test:FiltersReporting"

    assert config.certificate_path == (tmp_path / "application.der")

    assert config.private_key_path == (tmp_path / "application.pem")

    assert config.trusted_certificates_dir == (tmp_path / "trusted")

    assert config.server_certificate_path == (tmp_path / "server.der")

    assert config.validate_server_certificate is True


def test_default_no_security_config_is_disabled(
    tmp_path,
):
    settings = AppSettings(
        reports_dir=tmp_path,
        smtp_host="smtp",
        smtp_port=465,
        username="user",
        sender="sender",
        recipients=["receiver"],
    )

    config = settings.to_opc_client_security_config()

    assert config.policy == "None"

    assert config.mode == "None"

    assert config.enabled is False


def test_server_settings_have_secure_defaults(
    tmp_path,
):
    settings = AppSettings(
        reports_dir=tmp_path,
        smtp_host="smtp",
        smtp_port=465,
        username="user",
        sender="sender",
        recipients=["receiver"],
    )

    assert settings.opc_server_enabled is False

    assert settings.opc_server_security_policy == "Aes256Sha256RsaPss"

    assert settings.opc_server_security_mode == "SignAndEncrypt"

    assert settings.opc_server_allow_no_security is False
