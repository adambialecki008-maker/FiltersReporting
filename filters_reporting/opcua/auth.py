from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass

from asyncua import ua
from asyncua.crypto.permission_rules import (
    User,
    UserRole,
)

PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 600_000
PASSWORD_SALT_BYTES = 16


@dataclass(frozen=True)
class OpcUaAuthenticationConfig:
    allow_anonymous: bool = True

    username: str = ""

    password_hash: str = ""

    @property
    def username_enabled(
        self,
    ) -> bool:
        return bool(self.username.strip() and self.password_hash.strip())

    def validate(
        self,
    ) -> None:
        username = self.username.strip()

        password_hash = self.password_hash.strip()

        if username and not password_hash:
            raise ValueError(
                "OPC UA Server: " "dla skonfigurowanego użytkownika " "brakuje hasła."
            )

        if password_hash and not username:
            raise ValueError(
                "OPC UA Server: "
                "dla skonfigurowanego hasła "
                "brakuje nazwy użytkownika."
            )

        if not self.allow_anonymous and not self.username_enabled:
            raise ValueError(
                "OPC UA Server: "
                "Anonymous jest wyłączony, "
                "ale nie skonfigurowano "
                "username/password."
            )


def hash_password(
    password: str,
    *,
    iterations: int = (PASSWORD_HASH_ITERATIONS),
) -> str:
    if not isinstance(
        password,
        str,
    ):
        raise TypeError("Hasło musi być tekstem.")

    if not password:
        raise ValueError("Hasło nie może być puste.")

    if iterations <= 0:
        raise ValueError("iterations musi być " "większe od 0.")

    salt = os.urandom(PASSWORD_SALT_BYTES)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )

    salt_encoded = base64.urlsafe_b64encode(salt).decode("ascii")

    digest_encoded = base64.urlsafe_b64encode(digest).decode("ascii")

    return (
        f"{PASSWORD_HASH_ALGORITHM}"
        f"${iterations}"
        f"${salt_encoded}"
        f"${digest_encoded}"
    )


def verify_password(
    password: str,
    encoded_hash: str,
) -> bool:
    if not isinstance(
        password,
        str,
    ):
        return False

    if not isinstance(
        encoded_hash,
        str,
    ):
        return False

    try:
        (
            algorithm,
            iterations_text,
            salt_encoded,
            digest_encoded,
        ) = encoded_hash.split(
            "$",
            3,
        )

        if algorithm != PASSWORD_HASH_ALGORITHM:
            return False

        iterations = int(iterations_text)

        if iterations <= 0:
            return False

        salt = base64.urlsafe_b64decode(salt_encoded.encode("ascii"))

        expected_digest = base64.urlsafe_b64decode(digest_encoded.encode("ascii"))

    except (
        ValueError,
        TypeError,
        base64.binascii.Error,
    ):
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )

    return hmac.compare_digest(
        actual_digest,
        expected_digest,
    )


def build_identity_tokens(
    config: OpcUaAuthenticationConfig,
) -> list[type]:
    config.validate()

    tokens = []

    if config.allow_anonymous:
        tokens.append(ua.AnonymousIdentityToken)

    if config.username_enabled:
        tokens.append(ua.UserNameIdentityToken)

    return tokens


class FiltersReportingUserManager:
    def __init__(
        self,
        config: OpcUaAuthenticationConfig,
    ):
        config.validate()

        self.config = config

    def get_user(
        self,
        iserver,
        username=None,
        password=None,
        certificate=None,
    ) -> User | None:
        # ----------------------------------------------
        # ANONYMOUS
        # ----------------------------------------------

        if username is None:
            if self.config.allow_anonymous:
                return User(role=(UserRole.Anonymous))

            return None

        # ----------------------------------------------
        # USERNAME / PASSWORD
        # ----------------------------------------------

        if not (self.config.username_enabled):
            return None

        expected_username = self.config.username.strip()

        if username != expected_username:
            return None

        if password is None:
            return None

        if not verify_password(
            password,
            self.config.password_hash,
        ):
            return None

        return User(
            role=UserRole.User,
            name=expected_username,
        )
