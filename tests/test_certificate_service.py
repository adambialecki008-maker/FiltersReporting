from cryptography import x509
from cryptography.x509.oid import (
    ExtendedKeyUsageOID,
)

from filters_reporting.opcua.certificate_service import (
    create_default_certificate_paths,
    generate_application_certificate,
    load_certificate,
    load_certificate_info,
)


def test_create_default_certificate_paths(
    tmp_path,
):
    paths = create_default_certificate_paths(tmp_path)

    assert paths.certificate == (tmp_path / "filters_reporting_client_server.der")

    assert paths.private_key == (
        tmp_path / "private" / "filters_reporting_client_server_key.pem"
    )

    assert paths.trusted == (tmp_path / "trusted")

    assert paths.rejected == (tmp_path / "rejected")


def test_generate_application_certificate_creates_files(
    tmp_path,
):
    paths = create_default_certificate_paths(tmp_path)

    info = generate_application_certificate(
        paths=paths,
        application_uri=("urn:test:FiltersReporting"),
        hostname=("test-machine"),
    )

    assert paths.certificate.is_file()

    assert paths.private_key.is_file()

    assert paths.trusted.is_dir()

    assert paths.rejected.is_dir()

    assert info.common_name == "FiltersReporting Client/Server"

    assert "urn:test:FiltersReporting" in info.application_uris

    assert "test-machine" in info.dns_names

    assert info.client_auth is True

    assert info.server_auth is True


def test_generated_certificate_has_client_and_server_eku(
    tmp_path,
):
    paths = create_default_certificate_paths(tmp_path)

    generate_application_certificate(
        paths=paths,
        application_uri=("urn:test:FiltersReporting"),
        hostname=("test-machine"),
    )

    certificate = load_certificate(paths.certificate)

    eku = certificate.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value

    assert ExtendedKeyUsageOID.CLIENT_AUTH in eku

    assert ExtendedKeyUsageOID.SERVER_AUTH in eku


def test_load_certificate_info_reads_generated_certificate(
    tmp_path,
):
    paths = create_default_certificate_paths(tmp_path)

    generate_application_certificate(
        paths=paths,
        application_uri=("urn:test:FiltersReporting"),
        hostname=("test-machine"),
    )

    info = load_certificate_info(paths.certificate)

    assert info.common_name == "FiltersReporting Client/Server"

    assert info.sha256_thumbprint

    assert ":" in info.sha256_thumbprint


def test_generate_certificate_refuses_overwrite_when_disabled(
    tmp_path,
):
    paths = create_default_certificate_paths(tmp_path)

    generate_application_certificate(
        paths=paths,
        application_uri=("urn:test:FiltersReporting"),
        hostname=("test-machine"),
    )

    try:
        generate_application_certificate(
            paths=paths,
            application_uri=("urn:test:FiltersReporting"),
            hostname=("test-machine"),
            overwrite=False,
        )

    except FileExistsError:
        pass

    else:
        raise AssertionError("Expected FileExistsError")
