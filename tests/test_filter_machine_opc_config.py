import sqlite3

from filters_reporting.database.filters_repository import FiltersRepository
from filters_reporting.models.filter import Filter


EXPECTED_OPC_COLUMNS = {
    "opc_security_policy",
    "opc_security_mode",
    "opc_application_uri",
    "opc_client_certificate_path",
    "opc_client_private_key_path",
    "opc_trusted_certificates_dir",
    "opc_server_certificate_path",
    "opc_validate_server_certificate",
    "opc_auth_type",
    "opc_username",
    "opc_connect_timeout_seconds",
    "opc_request_timeout_seconds",
    "opc_reconnect_delay_seconds",
}


def test_create_table_migrates_legacy_filters_table_without_losing_data(tmp_path):
    database_path = tmp_path / "legacy.db"

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE filters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                opc_url TEXT UNIQUE NOT NULL,
                delta_p_threshold INTEGER NOT NULL DEFAULT 2000,
                delta_p_node_id TEXT,
                status_node_id TEXT,
                alarm_node_id TEXT
            )
            """
        )
        connection.execute(
            """
            INSERT INTO filters (
                name,
                active,
                opc_url,
                delta_p_threshold,
                delta_p_node_id,
                status_node_id,
                alarm_node_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "F1",
                1,
                "opc.tcp://192.168.1.10:4840",
                2300,
                "ns=3;s=DeltaP",
                "ns=3;s=Status",
                "ns=3;s=Alarm",
            ),
        )

    repository = FiltersRepository(database_path)
    repository.create_table()

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(filters)")
        }

    assert EXPECTED_OPC_COLUMNS.issubset(columns)

    result = repository.get_filter_by_name("F1")

    assert result is not None
    assert result.name == "F1"
    assert result.opc_url == "opc.tcp://192.168.1.10:4840"
    assert result.delta_p_threshold == 2300
    assert result.opc_security_policy == "None"
    assert result.opc_security_mode == "None"
    assert result.opc_auth_type == "Anonymous"
    assert result.opc_username == ""
    assert result.opc_connect_timeout_seconds == 5.0
    assert result.opc_request_timeout_seconds == 5.0
    assert result.opc_reconnect_delay_seconds == 5.0


def test_save_and_load_filter_preserves_machine_opc_config(tmp_path):
    repository = FiltersRepository(tmp_path / "test.db")
    repository.create_table()

    filter_obj = Filter(
        name="F1",
        opc_url="opc.tcp://192.168.1.101:4840",
        opc_security_policy="Basic256Sha256",
        opc_security_mode="SignAndEncrypt",
        opc_application_uri="urn:filters-reporting:f1",
        opc_client_certificate_path=r"C:\certs\f1\client.der",
        opc_client_private_key_path=r"C:\certs\f1\client.pem",
        opc_trusted_certificates_dir=r"C:\certs\f1\trusted",
        opc_server_certificate_path=r"C:\certs\f1\server.der",
        opc_validate_server_certificate=True,
        opc_auth_type="UsernamePassword",
        opc_username="operator_f1",
        opc_connect_timeout_seconds=7.5,
        opc_request_timeout_seconds=8.5,
        opc_reconnect_delay_seconds=12.0,
    )

    repository.save_filter(filter_obj)

    result = repository.get_filter_by_name("F1")

    assert result == filter_obj


def test_update_filter_opc_settings_updates_only_selected_filter(tmp_path):
    repository = FiltersRepository(tmp_path / "test.db")
    repository.create_table()

    filter_1 = Filter(
        name="F1",
        opc_url="opc.tcp://192.168.1.101:4840",
    )
    filter_2 = Filter(
        name="F2",
        opc_url="opc.tcp://192.168.1.102:4840",
    )

    repository.save_filter(filter_1)
    repository.save_filter(filter_2)

    filter_1.opc_security_policy = "Basic256Sha256"
    filter_1.opc_security_mode = "SignAndEncrypt"
    filter_1.opc_auth_type = "UsernamePassword"
    filter_1.opc_username = "operator_f1"

    repository.update_filter_opc_settings(filter_1)

    stored_1 = repository.get_filter_by_name("F1")
    stored_2 = repository.get_filter_by_name("F2")

    assert stored_1.opc_security_policy == "Basic256Sha256"
    assert stored_1.opc_security_mode == "SignAndEncrypt"
    assert stored_1.opc_auth_type == "UsernamePassword"
    assert stored_1.opc_username == "operator_f1"

    assert stored_2.opc_security_policy == "None"
    assert stored_2.opc_security_mode == "None"
    assert stored_2.opc_auth_type == "Anonymous"
    assert stored_2.opc_username == ""


def test_basic_filter_update_does_not_overwrite_opc_machine_settings(tmp_path):
    repository = FiltersRepository(tmp_path / "test.db")
    repository.create_table()

    filter_obj = Filter(
        name="F1",
        opc_url="opc.tcp://192.168.1.101:4840",
        opc_security_policy="Basic256Sha256",
        opc_security_mode="SignAndEncrypt",
        opc_auth_type="UsernamePassword",
        opc_username="operator_f1",
    )
    repository.save_filter(filter_obj)

    basic_edit_from_filters_page = Filter(
        filter_id=filter_obj.filter_id,
        name="F1 renamed",
        active=False,
        opc_url="opc.tcp://192.168.1.111:4840",
        delta_p_threshold=2500,
        delta_p_node_id="ns=3;s=DeltaP2",
        status_node_id="ns=3;s=Status2",
        alarm_node_id="ns=3;s=Alarm2",
    )

    repository.update_filter(basic_edit_from_filters_page)

    result = repository.get_filter_by_name("F1 renamed")

    assert result.opc_url == "opc.tcp://192.168.1.111:4840"
    assert result.delta_p_threshold == 2500
    assert result.opc_security_policy == "Basic256Sha256"
    assert result.opc_security_mode == "SignAndEncrypt"
    assert result.opc_auth_type == "UsernamePassword"
    assert result.opc_username == "operator_f1"
