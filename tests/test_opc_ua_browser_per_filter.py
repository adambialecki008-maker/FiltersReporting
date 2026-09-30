from types import SimpleNamespace

import filters_reporting.collection.opc_ua_browser as browser


class FakeConfig:
    enabled = True
    policy = "Aes256Sha256RsaPss"
    mode = "SignAndEncrypt"
    application_uri = "urn:filters:f1"
    certificate_path = "certs/f1.der"
    private_key_path = "certs/f1.pem"
    server_certificate_path = "certs/server-f1.der"
    trusted_certificates_dir = None
    validate_server_certificate = False

    def validate(self):
        self.validated = True


class FakeLoop:
    def post(self, awaitable):
        raise AssertionError("Trust store must not be used when validation is disabled")


class FakeSecureClient:
    def __init__(self):
        self.aio_obj = SimpleNamespace(
            application_uri="",
            certificate_validator=None,
        )
        self.tloop = FakeLoop()
        self.security_calls = []

    def set_security(self, *args, **kwargs):
        self.security_calls.append((args, kwargs))


class FakeBrowseClient:
    def __init__(self):
        self.aio_obj = SimpleNamespace(
            application_uri="",
            certificate_validator=None,
        )
        self.tloop = FakeLoop()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get_namespace_array(self):
        return ["urn:test"]

    def get_objects_node(self):
        node_class = SimpleNamespace(name="Object")
        return SimpleNamespace(
            nodeid=SimpleNamespace(
                NamespaceIndex=0,
                to_string=lambda: "i=85",
            ),
            read_browse_name=lambda: SimpleNamespace(Name="Objects"),
            read_display_name=lambda: SimpleNamespace(Text="Objects"),
            read_node_class=lambda: node_class,
            get_children=lambda: [],
        )


def test_sync_browser_security_uses_filter_specific_config(monkeypatch):
    config = FakeConfig()
    client = FakeSecureClient()
    filter_obj = SimpleNamespace(filter_id=7)
    auth_calls = []

    monkeypatch.setattr(
        browser,
        "build_filter_security_config",
        lambda value: config,
    )
    monkeypatch.setattr(
        browser,
        "get_client_security_policy",
        lambda value: "POLICY",
    )
    monkeypatch.setattr(
        browser,
        "get_message_security_mode",
        lambda value: "MODE",
    )
    monkeypatch.setattr(
        browser,
        "configure_client_authentication",
        lambda target, value: auth_calls.append((target, value)),
    )

    browser._configure_sync_client_security(
        client,
        filter_obj,
    )

    assert config.validated is True
    assert client.aio_obj.application_uri == "urn:filters:f1"
    assert client.security_calls == [
        (
            ("POLICY",),
            {
                "certificate": "certs/f1.der",
                "private_key": "certs/f1.pem",
                "server_certificate": "certs/server-f1.der",
                "mode": "MODE",
            },
        )
    ]
    assert auth_calls == [(client, filter_obj)]


def test_browse_applies_configuration_for_selected_filter(monkeypatch):
    client = FakeBrowseClient()
    filter_obj = SimpleNamespace(filter_id=3)
    configure_calls = []

    monkeypatch.setattr(
        browser,
        "Client",
        lambda *args, **kwargs: client,
    )
    monkeypatch.setattr(
        browser,
        "_configure_sync_client_security",
        lambda target, value: configure_calls.append((target, value)),
    )

    result = browser.browse_opc_ua_server(
        "opc.tcp://localhost:4840",
        filter_obj=filter_obj,
    )

    assert result.endpoint == "opc.tcp://localhost:4840"
    assert configure_calls == [(client, filter_obj)]
