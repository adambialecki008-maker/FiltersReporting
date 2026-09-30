from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from datetime import datetime

from asyncua import Client

from filters_reporting.config import (
    LOGGER_NAME,
)
from filters_reporting.models.filter_sample import (
    FilterSample,
)
from filters_reporting.opcua.client_credentials import (
    get_filter_password,
)
from filters_reporting.opcua.security import (
    OpcUaSecurityConfig,
    configure_client_security,
)
from filters_reporting.settings_service import (
    load_settings,
)

logger = logging.getLogger(LOGGER_NAME)

communication_status = {}
last_seen = {}
opc_clients = {}

OPC_READ_TIMEOUT_SECONDS = 5


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------
#
# Starsze testy / fragmenty kodu mogą nadal importować tę funkcję. Dla v1.0
# konfiguracja klienta OPC UA nie jest już pobierana globalnie z settings.json.
# Każdy filtr / maszyna ma własną konfigurację zapisaną w rekordzie Filter.
# Funkcję zostawiamy wyłącznie po to, żeby nie zerwać publicznego API projektu.
#

def get_current_security_config() -> OpcUaSecurityConfig:
    settings = load_settings()

    return settings.to_opc_client_security_config()


def _path_or_none(
    value,
) -> Path | None:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    return Path(text)


def build_filter_security_config(
    filter_obj,
) -> OpcUaSecurityConfig:
    """Build OPC UA security config for one filter / machine.

    In FiltersReporting v1.0 one filter is treated as one independent machine.
    Nothing in this function reads the global OPC UA client settings.
    """

    return OpcUaSecurityConfig(
        policy=(
            getattr(
                filter_obj,
                "opc_security_policy",
                "None",
            )
            or "None"
        ),
        mode=(
            getattr(
                filter_obj,
                "opc_security_mode",
                "None",
            )
            or "None"
        ),
        application_uri=(
            getattr(
                filter_obj,
                "opc_application_uri",
                "",
            )
            or ""
        ),
        certificate_path=_path_or_none(
            getattr(
                filter_obj,
                "opc_client_certificate_path",
                None,
            )
        ),
        private_key_path=_path_or_none(
            getattr(
                filter_obj,
                "opc_client_private_key_path",
                None,
            )
        ),
        trusted_certificates_dir=_path_or_none(
            getattr(
                filter_obj,
                "opc_trusted_certificates_dir",
                None,
            )
        ),
        server_certificate_path=_path_or_none(
            getattr(
                filter_obj,
                "opc_server_certificate_path",
                None,
            )
        ),
        validate_server_certificate=bool(
            getattr(
                filter_obj,
                "opc_validate_server_certificate",
                True,
            )
        ),
    )


def security_config_signature(
    config: OpcUaSecurityConfig,
):
    return (
        config.policy,
        config.mode,
        config.application_uri,
        (
            str(config.certificate_path)
            if config.certificate_path
            else None
        ),
        (
            str(config.private_key_path)
            if config.private_key_path
            else None
        ),
        (
            str(config.trusted_certificates_dir)
            if config.trusted_certificates_dir
            else None
        ),
        (
            str(config.server_certificate_path)
            if config.server_certificate_path
            else None
        ),
        config.validate_server_certificate,
    )


def _normalize_auth_type(
    auth_type,
) -> str:
    value = str(auth_type or "Anonymous").strip().casefold()

    if value in {
        "",
        "anonymous",
        "anon",
        "none",
    }:
        return "anonymous"

    if value in {
        "usernamepassword",
        "username/password",
        "username_password",
        "userpassword",
        "user/password",
    }:
        return "username_password"

    raise ValueError(
        "Nieobsługiwana metoda uwierzytelniania OPC UA: "
        f"{auth_type}"
    )


def authentication_signature(
    filter_obj,
):
    return (
        _normalize_auth_type(
            getattr(
                filter_obj,
                "opc_auth_type",
                "Anonymous",
            )
        ),
        str(
            getattr(
                filter_obj,
                "opc_username",
                "",
            )
            or ""
        ).strip(),
    )


def timeout_signature(
    filter_obj,
):
    return (
        _positive_timeout(
            getattr(
                filter_obj,
                "opc_connect_timeout_seconds",
                None,
            ),
            5.0,
        ),
        _positive_timeout(
            getattr(
                filter_obj,
                "opc_request_timeout_seconds",
                None,
            ),
            float(OPC_READ_TIMEOUT_SECONDS),
        ),
        _positive_timeout(
            getattr(
                filter_obj,
                "opc_reconnect_delay_seconds",
                None,
            ),
            5.0,
        ),
    )


def _positive_timeout(
    value,
    default: float,
) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return float(default)

    if result <= 0:
        return float(default)

    return result


def configure_client_authentication(
    client,
    filter_obj,
) -> None:
    """Configure authentication for one machine.

    Password is loaded from the DPAPI-backed credential store using filter_id.
    It is not stored in Filter, SQLite or settings.json.
    """

    auth_type = _normalize_auth_type(
        getattr(
            filter_obj,
            "opc_auth_type",
            "Anonymous",
        )
    )

    if auth_type == "anonymous":
        return

    filter_id = getattr(
        filter_obj,
        "filter_id",
        None,
    )

    if filter_id is None:
        raise ValueError(
            "Nie można pobrać hasła OPC UA: filtr nie ma filter_id."
        )

    username = str(
        getattr(
            filter_obj,
            "opc_username",
            "",
        )
        or ""
    ).strip()

    if not username:
        raise ValueError(
            "OPC UA: dla Username/Password brakuje nazwy użytkownika."
        )

    password = get_filter_password(
        filter_id
    )

    if not password:
        raise ValueError(
            "OPC UA: dla Username/Password brakuje hasła."
        )

    client.set_user(username)
    client.set_password(password)


class OpcUaFilterClient:
    def __init__(
        self,
        filter_obj,
        security_config: OpcUaSecurityConfig | None = None,
    ):
        self.filter_obj = filter_obj

        if security_config is None:
            security_config = build_filter_security_config(
                filter_obj
            )

        self.security_config = security_config

        self.security_signature = security_config_signature(
            security_config
        )

        self.auth_signature = authentication_signature(
            filter_obj
        )

        self.timeout_signature = timeout_signature(
            filter_obj
        )

        self.client = None

        self.delta_p_node = None
        self.status_node = None
        self.alarm_active_node = None

    async def connect(self):
        endpoint = str(
            self.filter_obj.opc_url or ""
        ).strip()

        if not endpoint:
            raise ValueError(
                f"{self.filter_obj.name}: brak endpointu OPC UA."
            )

        connect_timeout = _positive_timeout(
            getattr(
                self.filter_obj,
                "opc_connect_timeout_seconds",
                None,
            ),
            5.0,
        )

        request_timeout = _positive_timeout(
            getattr(
                self.filter_obj,
                "opc_request_timeout_seconds",
                None,
            ),
            float(OPC_READ_TIMEOUT_SECONDS),
        )

        self.client = Client(
            url=endpoint,
            timeout=request_timeout,
        )

        try:
            await configure_client_security(
                self.client,
                self.security_config,
            )

            configure_client_authentication(
                self.client,
                self.filter_obj,
            )

            await asyncio.wait_for(
                self.client.connect(),
                connect_timeout,
            )

            self.delta_p_node = self.client.get_node(
                self.filter_obj.delta_p_node_id
            )

            self.status_node = self.client.get_node(
                self.filter_obj.status_node_id
            )

            self.alarm_active_node = self.client.get_node(
                self.filter_obj.alarm_node_id
            )

        except Exception:
            try:
                await self.disconnect()

            except Exception:
                pass

            raise

    async def disconnect(self):
        try:
            if self.client is not None:
                await self.client.disconnect()

        finally:
            self.client = None

            self.delta_p_node = None
            self.status_node = None
            self.alarm_active_node = None

    async def read_sample(self):
        delta_p = await self.delta_p_node.read_value()

        status = await self.status_node.read_value()

        alarm_active = await self.alarm_active_node.read_value()

        timestamp = datetime.now().replace(
            microsecond=0
        )

        last_seen[
            self.filter_obj.filter_id
        ] = timestamp

        update_communication_status(
            self.filter_obj,
            True,
        )

        return FilterSample(
            filter_id=self.filter_obj.filter_id,
            delta_p=delta_p,
            status=status,
            alarm_active=alarm_active,
            timestamp=timestamp,
        )

    async def read_sample_reconnect(
        self,
    ):
        try:
            if self.client is None:
                await self.connect()

            return await self.read_sample()

        except Exception as error:
            update_communication_status(
                self.filter_obj,
                False,
                error,
            )

            try:
                await self.disconnect()

                # Każdy filtr ma własny klient i reconnect. Nie blokujemy
                # pozostałych maszyn poza czasem tej jednej coroutine.
                await self.connect()

                return await self.read_sample()

            except Exception as reconnect_error:
                update_communication_status(
                    self.filter_obj,
                    False,
                    reconnect_error,
                )

                return None


async def read_opc_ua_samples(
    active_filters,
):
    await sync_opc_clients(
        active_filters
    )

    samples = await asyncio.gather(
        *(
            get_filter_sample_with_timeout(
                filter_obj
            )
            for filter_obj in active_filters
        )
    )

    return [
        sample
        for sample in samples
        if sample is not None
    ]


def update_communication_status(
    filter_obj,
    is_ok,
    error=None,
):
    previous_status = communication_status.get(
        filter_obj.filter_id,
        True,
    )

    communication_status[
        filter_obj.filter_id
    ] = is_ok

    last_ok = last_seen.get(
        filter_obj.filter_id
    )

    if previous_status == is_ok:
        return

    if is_ok:
        logger.info(
            f"{filter_obj.name}: "
            "Komunikacja OPC_UA przywrócona"
        )

    else:
        logger.error(
            f"{filter_obj.name}: "
            "Błąd komunikacji OPC_UA: "
            f"{error} | "
            "Ostatnia aktywność: "
            f"{last_ok}"
        )


async def get_filter_sample_with_timeout(
    filter_obj,
):
    client = opc_clients[
        filter_obj.filter_id
    ]

    timeout_seconds = _positive_timeout(
        getattr(
            filter_obj,
            "opc_request_timeout_seconds",
            None,
        ),
        float(OPC_READ_TIMEOUT_SECONDS),
    )

    try:
        return await asyncio.wait_for(
            client.read_sample_reconnect(),
            timeout_seconds,
        )

    except TimeoutError:
        update_communication_status(
            filter_obj,
            False,
            (
                "Timeout "
                f"{timeout_seconds:g} s"
            ),
        )

        return None


async def disconnect_all_clients():
    for (
        filter_id,
        client,
    ) in list(opc_clients.items()):
        await client.disconnect()

        logger.info(
            "Rozłączono OPC UA dla "
            f"filter_id={filter_id}"
        )

    opc_clients.clear()


async def sync_opc_clients(
    active_filters,
):
    active_filter_ids = {
        filter_obj.filter_id
        for filter_obj in active_filters
    }

    for client_id in list(
        opc_clients.keys()
    ):
        if client_id not in active_filter_ids:
            await opc_clients[
                client_id
            ].disconnect()

            del opc_clients[client_id]

    for filter_obj in active_filters:
        filter_id = filter_obj.filter_id

        if filter_id not in opc_clients:
            opc_clients[
                filter_id
            ] = OpcUaFilterClient(
                filter_obj
            )

            continue

        client = opc_clients[
            filter_id
        ]

        if client_config_changed(
            filter_obj,
            client,
        ):
            await client.disconnect()

            opc_clients[
                filter_id
            ] = OpcUaFilterClient(
                filter_obj
            )


def client_config_changed(
    filter_obj,
    client,
    security_config: OpcUaSecurityConfig | None = None,
):
    filter_changed = (
        filter_obj.opc_url
        != client.filter_obj.opc_url
        or filter_obj.name
        != client.filter_obj.name
        or filter_obj.delta_p_node_id
        != client.filter_obj.delta_p_node_id
        or filter_obj.status_node_id
        != client.filter_obj.status_node_id
        or filter_obj.alarm_node_id
        != client.filter_obj.alarm_node_id
    )

    if filter_changed:
        return True

    if security_config is None:
        security_config = build_filter_security_config(
            filter_obj
        )

    if (
        security_config_signature(
            security_config
        )
        != client.security_signature
    ):
        return True

    if (
        authentication_signature(
            filter_obj
        )
        != client.auth_signature
    ):
        return True

    return (
        timeout_signature(
            filter_obj
        )
        != client.timeout_signature
    )


async def test_filter_connection(
    filter_obj,
    timeout_seconds=5,
    security_config: OpcUaSecurityConfig | None = None,
):
    if security_config is None:
        security_config = build_filter_security_config(
            filter_obj
        )

    endpoint = str(
        filter_obj.opc_url or ""
    ).strip()

    if not endpoint:
        raise ValueError(
            "Endpoint OPC UA nie może być pusty."
        )

    timeout_seconds = _positive_timeout(
        timeout_seconds,
        _positive_timeout(
            getattr(
                filter_obj,
                "opc_connect_timeout_seconds",
                None,
            ),
            5.0,
        ),
    )

    request_timeout = _positive_timeout(
        getattr(
            filter_obj,
            "opc_request_timeout_seconds",
            None,
        ),
        float(OPC_READ_TIMEOUT_SECONDS),
    )

    client = Client(
        url=endpoint,
        timeout=request_timeout,
    )

    connected = False

    try:
        await asyncio.wait_for(
            configure_client_security(
                client,
                security_config,
            ),
            timeout_seconds,
        )

        configure_client_authentication(
            client,
            filter_obj,
        )

        await asyncio.wait_for(
            client.connect(),
            timeout_seconds,
        )

        connected = True

        delta_p_node = client.get_node(
            filter_obj.delta_p_node_id
        )

        status_node = client.get_node(
            filter_obj.status_node_id
        )

        alarm_node = client.get_node(
            filter_obj.alarm_node_id
        )

        (
            delta_p,
            status,
            alarm_active,
        ) = await asyncio.wait_for(
            asyncio.gather(
                delta_p_node.read_value(),
                status_node.read_value(),
                alarm_node.read_value(),
            ),
            timeout_seconds,
        )

        return {
            "delta_p": delta_p,
            "status": status,
            "alarm_active": alarm_active,
        }

    finally:
        if connected:
            await client.disconnect()
