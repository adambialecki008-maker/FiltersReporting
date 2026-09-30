from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

import filters_reporting.collection.opc_ua_client as opc_ua_client
from filters_reporting.collection.opc_ua_client import (
    OpcUaFilterClient,
    build_filter_security_config,
    client_config_changed,
    configure_client_authentication,
    sync_opc_clients,
)
from filters_reporting.models.filter import Filter


def test_build_filter_security_config_uses_machine_settings():
    filter_obj = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://10.0.0.1:4840",
        opc_security_policy="Aes256Sha256RsaPss",
        opc_security_mode="SignAndEncrypt",
        opc_application_uri="urn:test:F1",
        opc_client_certificate_path="certs/f1.der",
        opc_client_private_key_path="certs/f1.pem",
        opc_trusted_certificates_dir="certs/trusted-f1",
        opc_server_certificate_path="certs/server-f1.der",
        opc_validate_server_certificate=True,
    )

    config = build_filter_security_config(filter_obj)

    assert config.policy == "Aes256Sha256RsaPss"
    assert config.mode == "SignAndEncrypt"
    assert config.application_uri == "urn:test:F1"
    assert config.certificate_path == Path("certs/f1.der")
    assert config.private_key_path == Path("certs/f1.pem")
    assert config.trusted_certificates_dir == Path("certs/trusted-f1")
    assert config.server_certificate_path == Path("certs/server-f1.der")
    assert config.validate_server_certificate is True


def test_username_password_authentication_is_loaded_per_filter(
    monkeypatch,
):
    filter_obj = Filter(
        name="F7",
        filter_id=7,
        opc_url="opc.tcp://10.0.0.7:4840",
        opc_auth_type="UsernamePassword",
        opc_username="operator7",
    )

    fake_client = Mock()

    monkeypatch.setattr(
        opc_ua_client,
        "get_filter_password",
        Mock(return_value="secret7"),
    )

    configure_client_authentication(
        fake_client,
        filter_obj,
    )

    opc_ua_client.get_filter_password.assert_called_once_with(7)
    fake_client.set_user.assert_called_once_with("operator7")
    fake_client.set_password.assert_called_once_with("secret7")


def test_anonymous_authentication_does_not_touch_credentials(
    monkeypatch,
):
    filter_obj = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://10.0.0.1:4840",
        opc_auth_type="Anonymous",
    )

    fake_client = Mock()

    get_password = Mock(
        side_effect=AssertionError(
            "Anonymous nie może czytać hasła."
        )
    )

    monkeypatch.setattr(
        opc_ua_client,
        "get_filter_password",
        get_password,
    )

    configure_client_authentication(
        fake_client,
        filter_obj,
    )

    get_password.assert_not_called()
    fake_client.set_user.assert_not_called()
    fake_client.set_password.assert_not_called()


@pytest.mark.asyncio
async def test_two_filters_keep_independent_security_configs():
    opc_ua_client.opc_clients.clear()

    filter_1 = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://10.0.0.1:4840",
        opc_security_policy="None",
        opc_security_mode="None",
    )

    filter_2 = Filter(
        name="F2",
        filter_id=2,
        opc_url="opc.tcp://10.0.0.2:4840",
        opc_security_policy="Basic256Sha256",
        opc_security_mode="SignAndEncrypt",
        opc_application_uri="urn:test:F2",
        opc_client_certificate_path="f2.der",
        opc_client_private_key_path="f2.pem",
        opc_trusted_certificates_dir="trusted-f2",
    )

    await sync_opc_clients(
        [filter_1, filter_2]
    )

    assert (
        opc_ua_client.opc_clients[1]
        .security_config.policy
        == "None"
    )

    assert (
        opc_ua_client.opc_clients[2]
        .security_config.policy
        == "Basic256Sha256"
    )

    assert (
        opc_ua_client.opc_clients[2]
        .security_config.application_uri
        == "urn:test:F2"
    )

    opc_ua_client.opc_clients.clear()


def test_client_is_replaced_when_machine_security_changes():
    old_filter = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://10.0.0.1:4840",
        opc_security_policy="None",
        opc_security_mode="None",
    )

    client = OpcUaFilterClient(old_filter)

    new_filter = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://10.0.0.1:4840",
        opc_security_policy="Basic256Sha256",
        opc_security_mode="Sign",
        opc_application_uri="urn:test:F1",
        opc_client_certificate_path="f1.der",
        opc_client_private_key_path="f1.pem",
        opc_trusted_certificates_dir="trusted-f1",
    )

    assert (
        client_config_changed(
            new_filter,
            client,
        )
        is True
    )


def test_client_is_replaced_when_username_changes():
    old_filter = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://10.0.0.1:4840",
        opc_auth_type="UsernamePassword",
        opc_username="operator-a",
    )

    client = OpcUaFilterClient(old_filter)

    new_filter = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://10.0.0.1:4840",
        opc_auth_type="UsernamePassword",
        opc_username="operator-b",
    )

    assert (
        client_config_changed(
            new_filter,
            client,
        )
        is True
    )


@pytest.mark.asyncio
async def test_connect_uses_per_filter_username_password(
    monkeypatch,
):
    filter_obj = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://10.0.0.1:4840",
        delta_p_node_id="ns=3;s=F1.DeltaP",
        status_node_id="ns=3;s=F1.Status",
        alarm_node_id="ns=3;s=F1.Alarm",
        opc_auth_type="UsernamePassword",
        opc_username="operator-f1",
    )

    fake_client = Mock()
    fake_client.connect = AsyncMock()
    fake_client.disconnect = AsyncMock()
    fake_client.get_node = Mock(
        side_effect=lambda node_id: node_id
    )

    monkeypatch.setattr(
        opc_ua_client,
        "Client",
        Mock(return_value=fake_client),
    )

    monkeypatch.setattr(
        opc_ua_client,
        "get_filter_password",
        Mock(return_value="password-f1"),
    )

    monkeypatch.setattr(
        opc_ua_client,
        "configure_client_security",
        AsyncMock(),
    )

    client = OpcUaFilterClient(filter_obj)

    await client.connect()

    fake_client.set_user.assert_called_once_with(
        "operator-f1"
    )
    fake_client.set_password.assert_called_once_with(
        "password-f1"
    )
    fake_client.connect.assert_awaited_once()

    assert client.delta_p_node == "ns=3;s=F1.DeltaP"
    assert client.status_node == "ns=3;s=F1.Status"
    assert client.alarm_active_node == "ns=3;s=F1.Alarm"
