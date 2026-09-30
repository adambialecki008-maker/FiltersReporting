from filters_reporting.opcua import certificate_service
from filters_reporting import runtime_paths


def test_default_certificate_directory_uses_runtime_directory():
    assert (
        certificate_service.DEFAULT_CERTIFICATE_DIR
        == runtime_paths.CERTIFICATES_DIR
    )
