import json

import pytest

from filters_reporting.opcua import (
    client_credentials,
)


def _fake_protect(data: bytes) -> bytes:
    return b"encrypted:" + data


def _fake_unprotect(data: bytes) -> bytes:
    prefix = b"encrypted:"

    if not data.startswith(prefix):
        raise ValueError("Invalid fake blob")

    return data[len(prefix):]


@pytest.fixture
def credential_store(
    monkeypatch,
    tmp_path,
):
    store_file = (
        tmp_path / "opc_credentials.json"
    )

    monkeypatch.setattr(
        client_credentials,
        "CREDENTIALS_FILE",
        store_file,
    )

    monkeypatch.setattr(
        client_credentials,
        "_protect_windows_dpapi",
        _fake_protect,
    )

    monkeypatch.setattr(
        client_credentials,
        "_unprotect_windows_dpapi",
        _fake_unprotect,
    )

    return store_file


def test_credential_reference_uses_filter_id():
    assert (
        client_credentials.credential_reference(12)
        == "opc-filter-12"
    )


@pytest.mark.parametrize(
    "filter_id",
    [
        None,
        0,
        -1,
        "abc",
    ],
)
def test_credential_reference_rejects_invalid_filter_id(
    filter_id,
):
    with pytest.raises(ValueError):
        client_credentials.credential_reference(
            filter_id
        )


def test_filter_password_roundtrip(
    credential_store,
):
    client_credentials.set_filter_password(
        1,
        "Secret-F1",
    )

    assert (
        client_credentials.get_filter_password(1)
        == "Secret-F1"
    )

    assert (
        client_credentials.has_filter_password(1)
        is True
    )

    assert credential_store.is_file()



def test_each_filter_has_independent_password(
    credential_store,
):
    client_credentials.set_filter_password(
        1,
        "Password-F1",
    )

    client_credentials.set_filter_password(
        2,
        "Password-F2",
    )

    assert (
        client_credentials.get_filter_password(1)
        == "Password-F1"
    )

    assert (
        client_credentials.get_filter_password(2)
        == "Password-F2"
    )



def test_password_is_not_stored_as_plain_text(
    credential_store,
):
    password = "VerySecret123!"

    client_credentials.set_filter_password(
        7,
        password,
    )

    raw_text = credential_store.read_text(
        encoding="utf-8"
    )

    assert password not in raw_text

    raw = json.loads(raw_text)

    assert (
        raw["credentials"]["opc-filter-7"]["scheme"]
        == "windows-dpapi-current-user-v1"
    )



def test_empty_password_deletes_existing_password(
    credential_store,
):
    client_credentials.set_filter_password(
        3,
        "Password-F3",
    )

    client_credentials.set_filter_password(
        3,
        "",
    )

    assert (
        client_credentials.get_filter_password(3)
        == ""
    )

    assert (
        client_credentials.has_filter_password(3)
        is False
    )



def test_delete_filter_password_only_deletes_selected_filter(
    credential_store,
):
    client_credentials.set_filter_password(
        1,
        "Password-F1",
    )

    client_credentials.set_filter_password(
        2,
        "Password-F2",
    )

    client_credentials.delete_filter_password(1)

    assert (
        client_credentials.has_filter_password(1)
        is False
    )

    assert (
        client_credentials.get_filter_password(2)
        == "Password-F2"
    )



def test_missing_password_returns_empty_string(
    credential_store,
):
    assert (
        client_credentials.get_filter_password(999)
        == ""
    )



def test_corrupted_store_does_not_crash(
    credential_store,
):
    credential_store.write_text(
        "{not-json",
        encoding="utf-8",
    )

    assert (
        client_credentials.get_filter_password(1)
        == ""
    )

    assert (
        client_credentials.has_filter_password(1)
        is False
    )



def test_corrupted_encrypted_blob_does_not_crash(
    credential_store,
):
    credential_store.write_text(
        json.dumps(
            {
                "version": 1,
                "credentials": {
                    "opc-filter-1": {
                        "scheme": (
                            "windows-dpapi-current-user-v1"
                        ),
                        "blob": "not base64!!!",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    assert (
        client_credentials.get_filter_password(1)
        == ""
    )



def test_generic_reference_api_stays_compatible(
    credential_store,
):
    client_credentials.set_password(
        "legacy-reference",
        "LegacyPassword",
    )

    assert (
        client_credentials.get_password(
            "legacy-reference"
        )
        == "LegacyPassword"
    )

    assert (
        client_credentials.has_password(
            "legacy-reference"
        )
        is True
    )
