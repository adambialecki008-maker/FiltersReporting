from __future__ import annotations

import hashlib
import socket
from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import (
    hashes,
    serialization,
)
from cryptography.hazmat.primitives.asymmetric import (
    rsa,
)
from cryptography.x509.oid import (
    ExtendedKeyUsageOID,
    NameOID,
)

from filters_reporting.runtime_paths import CERTIFICATES_DIR

DEFAULT_CERTIFICATE_DIR = CERTIFICATES_DIR

DEFAULT_CERTIFICATE_FILENAME = "filters_reporting_client_server.der"

DEFAULT_PRIVATE_KEY_FILENAME = "filters_reporting_client_server_key.pem"


@dataclass(frozen=True)
class ApplicationCertificatePaths:
    certificate: Path
    private_key: Path
    trusted: Path
    rejected: Path


@dataclass(frozen=True)
class CertificateInfo:
    common_name: str
    serial_number: int

    valid_from: datetime
    valid_until: datetime

    sha256_thumbprint: str

    application_uris: tuple[str, ...]
    dns_names: tuple[str, ...]

    client_auth: bool
    server_auth: bool


def get_default_application_uri() -> str:
    hostname = socket.gethostname()

    return f"urn:{hostname}:FiltersReporting"


def create_default_certificate_paths(
    base_dir: Path | str | None = None,
) -> ApplicationCertificatePaths:
    if base_dir is None:
        base_dir = DEFAULT_CERTIFICATE_DIR

    base_dir = Path(base_dir)

    return ApplicationCertificatePaths(
        certificate=(base_dir / DEFAULT_CERTIFICATE_FILENAME),
        private_key=(base_dir / "private" / DEFAULT_PRIVATE_KEY_FILENAME),
        trusted=(base_dir / "trusted"),
        rejected=(base_dir / "rejected"),
    )


def ensure_certificate_directories(
    paths: ApplicationCertificatePaths,
) -> None:
    paths.certificate.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    paths.private_key.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    paths.trusted.mkdir(
        parents=True,
        exist_ok=True,
    )

    paths.rejected.mkdir(
        parents=True,
        exist_ok=True,
    )


def generate_application_certificate(
    *,
    paths: ApplicationCertificatePaths | None = None,
    application_uri: str | None = None,
    hostname: str | None = None,
    common_name: str = ("FiltersReporting Client/Server"),
    organization: str = ("FiltersReporting"),
    valid_days: int = 365,
    overwrite: bool = True,
) -> CertificateInfo:
    if paths is None:
        paths = create_default_certificate_paths()

    if application_uri is None:
        application_uri = get_default_application_uri()

    if hostname is None:
        hostname = socket.gethostname()

    application_uri = application_uri.strip()

    hostname = hostname.strip()

    if not application_uri:
        raise ValueError("Application URI nie może " "być pusty.")

    if not hostname:
        raise ValueError("Hostname nie może być pusty.")

    if valid_days <= 0:
        raise ValueError("valid_days musi być " "większe od 0.")

    ensure_certificate_directories(paths)

    if not overwrite:
        if paths.certificate.exists() or paths.private_key.exists():
            raise FileExistsError("Certyfikat lub klucz prywatny " "już istnieje.")

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    subject = x509.Name(
        [
            x509.NameAttribute(
                NameOID.COMMON_NAME,
                common_name,
            ),
            x509.NameAttribute(
                NameOID.ORGANIZATION_NAME,
                organization,
            ),
        ]
    )

    now = datetime.now(timezone.utc)

    certificate_builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=valid_days))
        .add_extension(
            x509.BasicConstraints(
                ca=False,
                path_length=None,
            ),
            critical=True,
        )
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.UniformResourceIdentifier(application_uri),
                    x509.DNSName(hostname),
                ]
            ),
            critical=False,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=True,
                key_encipherment=True,
                data_encipherment=True,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage(
                [
                    ExtendedKeyUsageOID.CLIENT_AUTH,
                    ExtendedKeyUsageOID.SERVER_AUTH,
                ]
            ),
            critical=False,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
            critical=False,
        )
    )

    certificate = certificate_builder.sign(
        private_key=(private_key),
        algorithm=(hashes.SHA256()),
    )

    private_key_bytes = private_key.private_bytes(
        encoding=(serialization.Encoding.PEM),
        format=(serialization.PrivateFormat.PKCS8),
        encryption_algorithm=(serialization.NoEncryption()),
    )

    certificate_bytes = certificate.public_bytes(serialization.Encoding.DER)

    paths.private_key.write_bytes(private_key_bytes)

    paths.certificate.write_bytes(certificate_bytes)

    try:
        paths.private_key.chmod(0o600)

    except OSError:
        pass

    return certificate_info_from_object(certificate)


def load_certificate(
    certificate_path: Path | str,
) -> x509.Certificate:
    certificate_path = Path(certificate_path)

    data = certificate_path.read_bytes()

    try:
        return x509.load_der_x509_certificate(data)

    except ValueError:
        return x509.load_pem_x509_certificate(data)


def load_certificate_info(
    certificate_path: Path | str,
) -> CertificateInfo:
    certificate = load_certificate(certificate_path)

    return certificate_info_from_object(certificate)


def certificate_info_from_object(
    certificate: x509.Certificate,
) -> CertificateInfo:
    common_name = ""

    common_names = certificate.subject.get_attributes_for_oid(NameOID.COMMON_NAME)

    if common_names:
        common_name = common_names[0].value

    application_uris: list[str] = []
    dns_names: list[str] = []

    try:
        san = certificate.extensions.get_extension_for_class(
            x509.SubjectAlternativeName
        ).value

        application_uris = san.get_values_for_type(x509.UniformResourceIdentifier)

        dns_names = san.get_values_for_type(x509.DNSName)

    except x509.ExtensionNotFound:
        pass

    extended_key_usage = []

    try:
        extended_key_usage = list(
            certificate.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
        )

    except x509.ExtensionNotFound:
        pass

    valid_from = getattr(
        certificate,
        "not_valid_before_utc",
        None,
    )

    if valid_from is None:
        valid_from = certificate.not_valid_before.replace(tzinfo=timezone.utc)

    valid_until = getattr(
        certificate,
        "not_valid_after_utc",
        None,
    )

    if valid_until is None:
        valid_until = certificate.not_valid_after.replace(tzinfo=timezone.utc)

    thumbprint = (
        hashlib.sha256(certificate.public_bytes(serialization.Encoding.DER))
        .hexdigest()
        .upper()
    )

    formatted_thumbprint = ":".join(
        thumbprint[index : index + 2]
        for index in range(
            0,
            len(thumbprint),
            2,
        )
    )

    return CertificateInfo(
        common_name=(common_name),
        serial_number=(certificate.serial_number),
        valid_from=(valid_from),
        valid_until=(valid_until),
        sha256_thumbprint=(formatted_thumbprint),
        application_uris=tuple(application_uris),
        dns_names=tuple(dns_names),
        client_auth=(ExtendedKeyUsageOID.CLIENT_AUTH in extended_key_usage),
        server_auth=(ExtendedKeyUsageOID.SERVER_AUTH in extended_key_usage),
    )
