from dataclasses import dataclass


@dataclass
class Filter:
    name: str
    filter_id: int | None = None
    active: bool = True
    opc_url: str | None = None
    delta_p_threshold: int = 2000
    delta_p_node_id: str | None = None
    status_node_id: str | None = None
    alarm_node_id: str | None = None

    # OPC UA security.
    # Każdy filtr traktujemy jako niezależną maszynę / serwer OPC UA.
    opc_security_policy: str = "None"
    opc_security_mode: str = "None"
    opc_application_uri: str = ""

    opc_client_certificate_path: str | None = None
    opc_client_private_key_path: str | None = None
    opc_trusted_certificates_dir: str | None = None
    opc_server_certificate_path: str | None = None
    opc_validate_server_certificate: bool = True

    # Uwierzytelnianie OPC UA per maszyna.
    #
    # Hasła NIE przechowujemy tutaj ani w SQLite.
    # Hasło będzie przechowywane osobno przez zaszyfrowany
    # magazyn credentials i identyfikowane przez filter_id.
    opc_auth_type: str = "Anonymous"
    opc_username: str = ""

    # Parametry połączenia per maszyna.
    opc_connect_timeout_seconds: float = 5.0
    opc_request_timeout_seconds: float = 5.0
    opc_reconnect_delay_seconds: float = 5.0
