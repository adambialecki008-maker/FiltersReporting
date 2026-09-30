from __future__ import annotations

import base64
import ctypes
import json
import os
from pathlib import Path
from typing import Any

from filters_reporting.runtime_paths import RUNTIME_ROOT

CREDENTIALS_FILE = RUNTIME_ROOT / "opc_credentials.json"

_STORE_VERSION = 1
_SCHEME = "windows-dpapi-current-user-v1"
_DPAPI_DESCRIPTION = "FiltersReporting OPC UA credentials"


def credential_reference(filter_id: int) -> str:
    """Return the stable credential key used for one filter / machine."""

    try:
        normalized_filter_id = int(filter_id)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "filter_id musi być dodatnią liczbą."
        ) from error

    if normalized_filter_id <= 0:
        raise ValueError(
            "filter_id musi być dodatnią liczbą."
        )

    return f"opc-filter-{normalized_filter_id}"


def _normalize_reference(
    reference: str | None,
) -> str:
    return str(reference or "").strip()


def _load_store() -> dict[str, dict[str, str]]:
    """Load encrypted credentials.

    A damaged/missing store is treated as an empty store. Individual malformed
    entries are ignored so one bad record cannot block every machine.
    """

    if not CREDENTIALS_FILE.is_file():
        return {}

    try:
        raw_data: Any = json.loads(
            CREDENTIALS_FILE.read_text(
                encoding="utf-8",
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
        TypeError,
    ):
        return {}

    if not isinstance(raw_data, dict):
        return {}

    credentials = raw_data.get(
        "credentials",
        {},
    )

    if not isinstance(credentials, dict):
        return {}

    result: dict[str, dict[str, str]] = {}

    for reference, entry in credentials.items():
        if not isinstance(reference, str):
            continue

        if not isinstance(entry, dict):
            continue

        scheme = entry.get("scheme")
        blob = entry.get("blob")

        if not isinstance(scheme, str):
            continue

        if not isinstance(blob, str):
            continue

        result[reference] = {
            "scheme": scheme,
            "blob": blob,
        }

    return result


def _save_store(
    entries: dict[str, dict[str, str]],
) -> None:
    """Atomically persist encrypted credentials."""

    CREDENTIALS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_file = CREDENTIALS_FILE.with_name(
        f"{CREDENTIALS_FILE.name}.tmp"
    )

    payload = {
        "version": _STORE_VERSION,
        "credentials": entries,
    }

    try:
        temp_file.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        os.replace(
            temp_file,
            CREDENTIALS_FILE,
        )
    finally:
        try:
            if temp_file.exists():
                temp_file.unlink()
        except OSError:
            pass

    # Best effort for development/non-Windows environments. On Windows the
    # secret itself is protected by DPAPI; file permissions are only an
    # additional layer.
    try:
        CREDENTIALS_FILE.chmod(0o600)
    except OSError:
        pass


def _protect_windows_dpapi(
    data: bytes,
) -> bytes:
    if os.name != "nt":
        raise RuntimeError(
            "Szyfrowanie haseł OPC UA jest obsługiwane przez Windows DPAPI."
        )

    if not data:
        return b""

    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            (
                "cbData",
                wintypes.DWORD,
            ),
            (
                "pbData",
                ctypes.POINTER(
                    ctypes.c_ubyte
                ),
            ),
        ]

    input_buffer = ctypes.create_string_buffer(
        data
    )

    input_blob = DATA_BLOB(
        len(data),
        ctypes.cast(
            input_buffer,
            ctypes.POINTER(
                ctypes.c_ubyte
            ),
        ),
    )

    output_blob = DATA_BLOB()

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32

    crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(DATA_BLOB),
        wintypes.LPCWSTR,
        ctypes.POINTER(DATA_BLOB),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(DATA_BLOB),
    ]
    crypt32.CryptProtectData.restype = (
        wintypes.BOOL
    )

    kernel32.LocalFree.argtypes = [
        ctypes.c_void_p,
    ]
    kernel32.LocalFree.restype = (
        ctypes.c_void_p
    )

    cryptprotect_ui_forbidden = 0x01

    success = crypt32.CryptProtectData(
        ctypes.byref(input_blob),
        _DPAPI_DESCRIPTION,
        None,
        None,
        None,
        cryptprotect_ui_forbidden,
        ctypes.byref(output_blob),
    )

    if not success:
        raise ctypes.WinError()

    try:
        return ctypes.string_at(
            output_blob.pbData,
            output_blob.cbData,
        )
    finally:
        kernel32.LocalFree(
            output_blob.pbData
        )


def _unprotect_windows_dpapi(
    data: bytes,
) -> bytes:
    if os.name != "nt":
        raise RuntimeError(
            "Odczyt haseł OPC UA jest obsługiwany przez Windows DPAPI."
        )

    if not data:
        return b""

    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            (
                "cbData",
                wintypes.DWORD,
            ),
            (
                "pbData",
                ctypes.POINTER(
                    ctypes.c_ubyte
                ),
            ),
        ]

    input_buffer = ctypes.create_string_buffer(
        data
    )

    input_blob = DATA_BLOB(
        len(data),
        ctypes.cast(
            input_buffer,
            ctypes.POINTER(
                ctypes.c_ubyte
            ),
        ),
    )

    output_blob = DATA_BLOB()

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32

    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(DATA_BLOB),
        ctypes.POINTER(
            wintypes.LPWSTR
        ),
        ctypes.POINTER(DATA_BLOB),
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(DATA_BLOB),
    ]
    crypt32.CryptUnprotectData.restype = (
        wintypes.BOOL
    )

    kernel32.LocalFree.argtypes = [
        ctypes.c_void_p,
    ]
    kernel32.LocalFree.restype = (
        ctypes.c_void_p
    )

    cryptprotect_ui_forbidden = 0x01

    description = wintypes.LPWSTR()

    success = crypt32.CryptUnprotectData(
        ctypes.byref(input_blob),
        ctypes.byref(description),
        None,
        None,
        None,
        cryptprotect_ui_forbidden,
        ctypes.byref(output_blob),
    )

    if not success:
        raise ctypes.WinError()

    try:
        return ctypes.string_at(
            output_blob.pbData,
            output_blob.cbData,
        )
    finally:
        if description:
            kernel32.LocalFree(
                description
            )

        kernel32.LocalFree(
            output_blob.pbData
        )


def set_password(
    reference: str,
    password: str,
) -> None:
    """Store one encrypted password under a stable reference.

    Passing an empty password intentionally removes the existing credential.
    """

    normalized_reference = (
        _normalize_reference(reference)
    )

    if not normalized_reference:
        raise ValueError(
            "Brak identyfikatora poświadczeń OPC UA."
        )

    password = str(password or "")

    if not password:
        delete_password(
            normalized_reference
        )
        return

    encrypted = _protect_windows_dpapi(
        password.encode("utf-8")
    )

    entries = _load_store()

    entries[normalized_reference] = {
        "scheme": _SCHEME,
        "blob": base64.b64encode(
            encrypted
        ).decode("ascii"),
    }

    _save_store(entries)


def get_password(
    reference: str | None,
) -> str:
    normalized_reference = (
        _normalize_reference(reference)
    )

    if not normalized_reference:
        return ""

    entry = _load_store().get(
        normalized_reference
    )

    if not isinstance(entry, dict):
        return ""

    if entry.get("scheme") != _SCHEME:
        return ""

    try:
        encoded_blob = entry.get(
            "blob",
            "",
        )

        encrypted = base64.b64decode(
            encoded_blob,
            validate=True,
        )

        decrypted = (
            _unprotect_windows_dpapi(
                encrypted
            )
        )

        return decrypted.decode("utf-8")
    except (
        ValueError,
        UnicodeDecodeError,
        OSError,
        RuntimeError,
    ):
        # A password encrypted for a different Windows user, damaged store,
        # unsupported platform, etc. must not crash the collector or GUI.
        return ""


def delete_password(
    reference: str | None,
) -> None:
    normalized_reference = (
        _normalize_reference(reference)
    )

    if not normalized_reference:
        return

    entries = _load_store()

    if normalized_reference not in entries:
        return

    del entries[normalized_reference]
    _save_store(entries)


def has_password(
    reference: str | None,
) -> bool:
    normalized_reference = (
        _normalize_reference(reference)
    )

    if not normalized_reference:
        return False

    entry = _load_store().get(
        normalized_reference
    )

    if not isinstance(entry, dict):
        return False

    return (
        entry.get("scheme") == _SCHEME
        and bool(entry.get("blob"))
    )


def set_filter_password(
    filter_id: int,
    password: str,
) -> None:
    set_password(
        credential_reference(filter_id),
        password,
    )


def get_filter_password(
    filter_id: int,
) -> str:
    return get_password(
        credential_reference(filter_id)
    )


def delete_filter_password(
    filter_id: int,
) -> None:
    delete_password(
        credential_reference(filter_id)
    )


def has_filter_password(
    filter_id: int,
) -> bool:
    return has_password(
        credential_reference(filter_id)
    )
