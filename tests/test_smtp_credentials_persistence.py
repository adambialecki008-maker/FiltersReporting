import json

import filters_reporting.smtp_credentials as credentials


def test_smtp_password_is_persisted_without_plaintext(
    monkeypatch,
    tmp_path,
):
    store = tmp_path / "smtp_credentials.json"

    monkeypatch.setattr(
        credentials,
        "CREDENTIALS_FILE",
        store,
    )

    monkeypatch.setattr(
        credentials,
        "_protect_windows_dpapi",
        lambda value: b"encrypted:" + value[::-1],
    )

    monkeypatch.setattr(
        credentials,
        "_unprotect_windows_dpapi",
        lambda value: value.removeprefix(b"encrypted:")[::-1],
    )

    credentials.set_smtp_password(
        "SuperSecret123!",
    )

    assert store.is_file()
    assert credentials.has_smtp_password() is True
    assert (
        credentials.get_smtp_password()
        == "SuperSecret123!"
    )

    text = store.read_text(
        encoding="utf-8",
    )

    assert "SuperSecret123!" not in text

    payload = json.loads(text)

    assert (
        payload["scheme"]
        == "windows-dpapi-current-user-v1"
    )


def test_delete_smtp_password(
    monkeypatch,
    tmp_path,
):
    store = tmp_path / "smtp_credentials.json"

    monkeypatch.setattr(
        credentials,
        "CREDENTIALS_FILE",
        store,
    )

    monkeypatch.setattr(
        credentials,
        "_protect_windows_dpapi",
        lambda value: value,
    )

    monkeypatch.setattr(
        credentials,
        "_unprotect_windows_dpapi",
        lambda value: value,
    )

    credentials.set_smtp_password(
        "abc",
    )

    assert credentials.has_smtp_password() is True

    credentials.delete_smtp_password()

    assert credentials.has_smtp_password() is False
    assert credentials.get_smtp_password() == ""
