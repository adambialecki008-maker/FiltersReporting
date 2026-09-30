from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from asyncua import ua
from asyncua.crypto.security_policies import (
    SecurityPolicyAes128Sha256RsaOaep,
    SecurityPolicyAes256Sha256RsaPss,
    SecurityPolicyBasic256Sha256,
)
from asyncua.crypto.truststore import TrustStore
from asyncua.crypto.validator import (
    CertificateValidator,
    CertificateValidatorOptions,
)

OPC_UA_SECURITY_POLICIES = (
    "None",
    "Basic256Sha256",
    "Aes128Sha256RsaOaep",
    "Aes256Sha256RsaPss",
)

OPC_UA_SECURITY_MODES = (
    "None",
    "Sign",
    "SignAndEncrypt",
)


CLIENT_SECURITY_POLICIES = {
    "Basic256Sha256": (SecurityPolicyBasic256Sha256),
    "Aes128Sha256RsaOaep": (SecurityPolicyAes128Sha256RsaOaep),
    "Aes256Sha256RsaPss": (SecurityPolicyAes256Sha256RsaPss),
}


@dataclass(frozen=True)
class OpcUaSecurityConfig:
    policy: str = "None"
    mode: str = "None"

    application_uri: str = ""

    certificate_path: Path | None = None
    private_key_path: Path | None = None

    trusted_certificates_dir: Path | None = None

    server_certificate_path: Path | None = None

    validate_server_certificate: bool = True

    @property
    def enabled(self) -> bool:
        return self.policy != "None" and self.mode != "None"

    def validate(self) -> None:
        if self.policy not in OPC_UA_SECURITY_POLICIES:
            raise ValueError("Nieobsługiwana OPC UA " f"Security Policy: {self.policy}")

        if self.mode not in OPC_UA_SECURITY_MODES:
            raise ValueError("Nieobsługiwany OPC UA " f"Security Mode: {self.mode}")

        policy_is_none = self.policy == "None"

        mode_is_none = self.mode == "None"

        if policy_is_none != mode_is_none:
            raise ValueError(
                "Security Policy i Security Mode "
                "muszą być jednocześnie None "
                "albo jednocześnie zabezpieczone."
            )

        if not self.enabled:
            return

        if not self.application_uri.strip():
            raise ValueError("Brak OPC UA Application URI.")

        if self.certificate_path is None:
            raise ValueError("Brak ścieżki do certyfikatu " "OPC UA aplikacji.")

        if self.private_key_path is None:
            raise ValueError("Brak ścieżki do klucza " "prywatnego OPC UA.")

        certificate_path = Path(self.certificate_path)

        private_key_path = Path(self.private_key_path)

        if not certificate_path.is_file():
            raise FileNotFoundError(
                "Nie znaleziono certyfikatu OPC UA: " f"{certificate_path}"
            )

        if not private_key_path.is_file():
            raise FileNotFoundError(
                "Nie znaleziono klucza " f"prywatnego OPC UA: " f"{private_key_path}"
            )

        if self.server_certificate_path:
            server_certificate_path = Path(self.server_certificate_path)

            if not server_certificate_path.is_file():
                raise FileNotFoundError(
                    "Nie znaleziono certyfikatu "
                    "serwera OPC UA: "
                    f"{server_certificate_path}"
                )

        if self.validate_server_certificate:
            if self.trusted_certificates_dir is None:
                raise ValueError(
                    "Walidacja certyfikatu serwera "
                    "jest włączona, ale nie ustawiono "
                    "katalogu trusted."
                )

            trusted_dir = Path(self.trusted_certificates_dir)

            if not trusted_dir.is_dir():
                raise FileNotFoundError(
                    "Nie znaleziono katalogu "
                    "zaufanych certyfikatów OPC UA: "
                    f"{trusted_dir}"
                )


def get_client_security_policy(
    policy_name: str,
):
    if policy_name == "None":
        return None

    try:
        return CLIENT_SECURITY_POLICIES[policy_name]

    except KeyError as error:
        raise ValueError(
            "Nieobsługiwana OPC UA " f"Security Policy: {policy_name}"
        ) from error


def get_message_security_mode(
    mode_name: str,
):
    if mode_name == "None":
        return ua.MessageSecurityMode.None_

    if mode_name == "Sign":
        return ua.MessageSecurityMode.Sign

    if mode_name == "SignAndEncrypt":
        return ua.MessageSecurityMode.SignAndEncrypt

    raise ValueError("Nieobsługiwany OPC UA " f"Security Mode: {mode_name}")


def get_server_security_policy_type(
    policy_name: str,
    mode_name: str,
):
    if policy_name == "None" and mode_name == "None":
        return ua.SecurityPolicyType.NoSecurity

    if policy_name == "None" or mode_name == "None":
        raise ValueError(
            "Dla połączenia zabezpieczonego " "policy i mode nie mogą być None."
        )

    if policy_name not in OPC_UA_SECURITY_POLICIES:
        raise ValueError("Nieobsługiwana OPC UA " f"Security Policy: {policy_name}")

    if mode_name not in (
        "Sign",
        "SignAndEncrypt",
    ):
        raise ValueError("Nieobsługiwany tryb serwera OPC UA: " f"{mode_name}")

    enum_name = f"{policy_name}_{mode_name}"

    try:
        return getattr(
            ua.SecurityPolicyType,
            enum_name,
        )

    except AttributeError as error:
        raise ValueError(
            "Aktualna wersja asyncua "
            "nie udostępnia polityki serwera: "
            f"{enum_name}"
        ) from error


async def configure_client_security(
    client,
    config: OpcUaSecurityConfig,
) -> None:
    config.validate()

    if not config.enabled:
        return

    policy_class = get_client_security_policy(config.policy)

    mode = get_message_security_mode(config.mode)

    client.application_uri = config.application_uri

    server_certificate = None

    if config.server_certificate_path:
        server_certificate = str(config.server_certificate_path)

    await client.set_security(
        policy_class,
        certificate=str(config.certificate_path),
        private_key=str(config.private_key_path),
        server_certificate=(server_certificate),
        mode=mode,
    )

    if not config.validate_server_certificate:
        return

    trusted_dir = Path(config.trusted_certificates_dir)

    trust_store = TrustStore(
        [
            trusted_dir,
        ],
        [],
    )

    await trust_store.load()

    validator = CertificateValidator(
        (
            CertificateValidatorOptions.TRUSTED_VALIDATION
            | CertificateValidatorOptions.PEER_SERVER
        ),
        trust_store,
    )

    client.certificate_validator = validator


def build_server_security_policies(
    *,
    policy: str,
    mode: str,
    allow_no_security: bool = False,
):
    selected_policy = get_server_security_policy_type(
        policy,
        mode,
    )

    policies = [
        selected_policy,
    ]

    if allow_no_security and selected_policy != ua.SecurityPolicyType.NoSecurity:
        policies.append(ua.SecurityPolicyType.NoSecurity)

    return policies
