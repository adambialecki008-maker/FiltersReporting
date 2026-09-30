from __future__ import annotations

import base64
import ctypes
import json
import os
from pathlib import Path
from typing import Any

from filters_reporting.runtime_paths import RUNTIME_ROOT

CREDENTIALS_FILE = RUNTIME_ROOT / "smtp_credentials.json"

_STORE_VERSION = 1
_SCHEME = "windows-dpapi-current-user-v1"
_DPAPI_DESCRIPTION = "FiltersReporting SMTP credentials"


def _load_store() -> dict[str, Any]:
    if not CREDENTIALS_FILE.is_file():
        return {}

    try:
        data = json.loads(
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

    if not isinstance(data, dict):
        return {}

    return data


def _save_store(
    encrypted: bytes,
) -> None:
    CREDENTIALS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "version": _STORE_VERSION,
        "scheme": _SCHEME,
        "blob": base64.b64encode(
            encrypted
        ).decode("ascii"),
    }

    temp_file = CREDENTIALS_FILE.with_name(
        f"{CREDENTIALS_FILE.name}.tmp"
    )

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

    try:
        CREDENTIALS_FILE.chmod(0o600)
    except OSError:
        pass


def _protect_windows_dpapi(
    data: bytes,
) -> bytes:
    if os.name != "nt":
        raise RuntimeError(
            "Szyfrowanie hasła SMTP wymaga Windows DPAPI."
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

    success = crypt32.CryptProtectData(
        ctypes.byref(input_blob),
        _DPAPI_DESCRIPTION,
        None,
        None,
        None,
        0x01,
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
            "Odczyt hasła SMTP wymaga Windows DPAPI."
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
    description = wintypes.LPWSTR()

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

    success = crypt32.CryptUnprotectData(
        ctypes.byref(input_blob),
        ctypes.byref(description),
        None,
        None,
        None,
        0x01,
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


def set_smtp_password(
    password: str,
) -> None:
    password = str(password or "")

    if not password:
        delete_smtp_password()
        return

    encrypted = _protect_windows_dpapi(
        password.encode("utf-8")
    )

    _save_store(encrypted)


def get_smtp_password() -> str:
    data = _load_store()

    if data.get("scheme") != _SCHEME:
        return ""

    encoded_blob = data.get(
        "blob",
        "",
    )

    if not isinstance(
        encoded_blob,
        str,
    ):
        return ""

    try:
        encrypted = base64.b64decode(
            encoded_blob,
            validate=True,
        )

        decrypted = (
            _unprotect_windows_dpapi(
                encrypted
            )
        )

        return decrypted.decode(
            "utf-8"
        )
    except (
        ValueError,
        UnicodeDecodeError,
        OSError,
        RuntimeError,
    ):
        return ""


def has_smtp_password() -> bool:
    return bool(
        get_smtp_password()
    )


def delete_smtp_password() -> None:
    try:
        CREDENTIALS_FILE.unlink()
    except FileNotFoundError:
        pass
