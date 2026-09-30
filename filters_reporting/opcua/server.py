from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime

from asyncua import Server, ua

from filters_reporting.monitoring.filter_monitor import (
    build_filter_statuses,
    is_collector_running,
)
from filters_reporting.opcua.auth import (
    FiltersReportingUserManager,
    build_identity_tokens,
)
from filters_reporting.opcua.certificate_service import (
    load_certificate_info,
)
from filters_reporting.opcua.security import (
    build_server_security_policies,
)
from filters_reporting.settings_service import (
    AppSettings,
)

DEFAULT_REFRESH_INTERVAL_SECONDS = 2.0


@dataclass(frozen=True)
class FilterServerSnapshot:
    filter_id: int
    name: str
    active: bool

    delta_p: float
    delta_p_threshold: float

    working: bool
    alarm_active: bool

    last_working_delta_p: float
    dirty_percent: float

    status: str
    last_update: str


@dataclass(frozen=True)
class ServerSnapshot:
    collector_running: bool
    total_filters: int
    active_filters: int
    last_update: str

    filters: tuple[FilterServerSnapshot, ...]


@dataclass
class FilterOpcUaNodes:
    object_node: object

    filter_id: object
    active: object

    delta_p: object
    delta_p_threshold: object

    working: object
    alarm_active: object

    last_working_delta_p: object
    dirty_percent: object

    status: object
    last_update: object


@dataclass
class SystemOpcUaNodes:
    server_running: object
    collector_running: object

    total_filters: object
    active_filters: object

    last_update: object


def _number_or_zero(
    value,
) -> float:
    if value is None:
        return 0.0

    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return 0.0


def calculate_dirty_percent(
    last_working_delta_p,
    threshold,
) -> float:
    last_working = _number_or_zero(last_working_delta_p)

    threshold_value = _number_or_zero(threshold)

    if threshold_value <= 0:
        return 0.0

    return last_working / threshold_value * 100.0


def build_server_snapshot(
    repository,
    now: datetime | None = None,
) -> ServerSnapshot:
    if now is None:
        now = datetime.now()

    all_filters = repository.get_all_filters()

    heartbeat = repository.get_collector_heartbeat()

    collector_running = is_collector_running(
        heartbeat,
        now,
    )

    latest_samples = repository.get_latest_active_filter_samples()

    active_statuses = build_filter_statuses(
        latest_samples,
        now,
        collector_running,
    )

    status_by_id = {row["filter_id"]: row for row in active_statuses}

    snapshots = []

    for filter_obj in all_filters:
        filter_id = filter_obj.filter_id

        active = bool(filter_obj.active)

        threshold = _number_or_zero(
            getattr(
                filter_obj,
                "delta_p_threshold",
                0,
            )
        )

        row = status_by_id.get(filter_id)

        if not active:
            snapshot = FilterServerSnapshot(
                filter_id=filter_id,
                name=filter_obj.name,
                active=False,
                delta_p=0.0,
                delta_p_threshold=(threshold),
                working=False,
                alarm_active=False,
                last_working_delta_p=0.0,
                dirty_percent=0.0,
                status="inactive",
                last_update="",
            )

            snapshots.append(snapshot)

            continue

        if row is None:
            snapshot = FilterServerSnapshot(
                filter_id=filter_id,
                name=filter_obj.name,
                active=True,
                delta_p=0.0,
                delta_p_threshold=(threshold),
                working=False,
                alarm_active=False,
                last_working_delta_p=0.0,
                dirty_percent=0.0,
                status="offline",
                last_update="",
            )

            snapshots.append(snapshot)

            continue

        delta_p = _number_or_zero(row.get("delta_p"))

        last_working_delta_p = _number_or_zero(row.get("last_working_delta_p"))

        dirty_percent = calculate_dirty_percent(
            last_working_delta_p,
            threshold,
        )

        timestamp = row.get("timestamp")

        if isinstance(
            timestamp,
            datetime,
        ):
            last_update = timestamp.isoformat(timespec="seconds")

        elif timestamp is None:
            last_update = ""

        else:
            last_update = str(timestamp)

        snapshot = FilterServerSnapshot(
            filter_id=filter_id,
            name=filter_obj.name,
            active=True,
            delta_p=delta_p,
            delta_p_threshold=(threshold),
            working=bool(row.get("status")),
            alarm_active=bool(row.get("alarm_active")),
            last_working_delta_p=(last_working_delta_p),
            dirty_percent=(dirty_percent),
            status=str(
                row.get(
                    "filter_status",
                    "offline",
                )
            ),
            last_update=(last_update),
        )

        snapshots.append(snapshot)

    return ServerSnapshot(
        collector_running=(collector_running),
        total_filters=len(all_filters),
        active_filters=sum(1 for filter_obj in all_filters if filter_obj.active),
        last_update=(now.isoformat(timespec="seconds")),
        filters=tuple(snapshots),
    )


def validate_server_settings(
    settings: AppSettings,
) -> None:
    if not settings.opc_server_endpoint:
        raise ValueError("Brak endpointu OPC UA Server.")

    if not (settings.opc_server_endpoint.startswith("opc.tcp://")):
        raise ValueError("Endpoint OPC UA musi zaczynać " "się od opc.tcp://")

    if not settings.opc_server_namespace:
        raise ValueError("Brak namespace OPC UA Server.")

    if not (settings.opc_server_application_uri):
        raise ValueError("Brak Application URI " "OPC UA Server.")

    authentication_config = settings.to_opc_server_authentication_config()

    authentication_config.validate()

    policy = settings.opc_server_security_policy

    mode = settings.opc_server_security_mode

    if authentication_config.username_enabled and policy == "None":
        raise ValueError(
            "OPC UA Server: username/password " "wymaga zabezpieczonego endpointu."
        )

    build_server_security_policies(
        policy=policy,
        mode=mode,
        allow_no_security=(settings.opc_server_allow_no_security),
    )

    if policy == "None":
        return

    certificate_path = settings.opc_server_certificate_path

    private_key_path = settings.opc_server_private_key_path

    if certificate_path is None or not certificate_path.is_file():
        raise FileNotFoundError("Nie znaleziono certyfikatu " "OPC UA Server.")

    if private_key_path is None or not private_key_path.is_file():
        raise FileNotFoundError("Nie znaleziono klucza prywatnego " "OPC UA Server.")

    certificate_info = load_certificate_info(certificate_path)

    if settings.opc_server_application_uri not in certificate_info.application_uris:
        raise ValueError(
            "Application URI serwera nie jest "
            "zgodne z URI zapisanym "
            "w certyfikacie."
        )

    if not certificate_info.server_auth:
        raise ValueError("Certyfikat nie posiada " "Server Authentication EKU.")


class FiltersReportingOpcUaServer:
    def __init__(
        self,
        repository,
        settings: AppSettings,
        *,
        refresh_interval: float = (DEFAULT_REFRESH_INTERVAL_SECONDS),
    ):
        self.repository = repository
        self.settings = settings

        self.refresh_interval = float(refresh_interval)

        if self.refresh_interval <= 0:
            raise ValueError("refresh_interval musi być " "większe od 0.")

        self.server: Server | None = None

        self.namespace_index: int | None = None

        self.root_object = None
        self.filters_object = None
        self.system_object = None

        self.system_nodes: SystemOpcUaNodes | None = None

        self.filter_nodes: dict[
            int,
            FilterOpcUaNodes,
        ] = {}

        self.running = False

        self._stop_requested = False

    async def initialise(
        self,
    ) -> None:
        validate_server_settings(self.settings)

        authentication_config = self.settings.to_opc_server_authentication_config()

        user_manager = FiltersReportingUserManager(authentication_config)

        server = Server(user_manager=user_manager)

        await server.init()

        server.set_endpoint(self.settings.opc_server_endpoint)

        server.set_server_name("FiltersReporting OPC UA Server")

        await server.set_application_uri(self.settings.opc_server_application_uri)

        policies = build_server_security_policies(
            policy=(self.settings.opc_server_security_policy),
            mode=(self.settings.opc_server_security_mode),
            allow_no_security=(self.settings.opc_server_allow_no_security),
        )

        server.set_security_policy(policies)

        server.set_identity_tokens(build_identity_tokens(authentication_config))

        if self.settings.opc_server_security_policy != "None":
            await server.load_certificate(self.settings.opc_server_certificate_path)

            await server.load_private_key(self.settings.opc_server_private_key_path)

        namespace_index = await server.register_namespace(
            self.settings.opc_server_namespace
        )

        self.server = server

        self.namespace_index = namespace_index

        await self._create_address_space()

    async def _create_address_space(
        self,
    ) -> None:
        if self.server is None:
            raise RuntimeError("OPC UA Server nie został " "zainicjalizowany.")

        if self.namespace_index is None:
            raise RuntimeError("Brak namespace index.")

        index = self.namespace_index

        self.root_object = await self.server.nodes.objects.add_object(
            index,
            "FiltersReporting",
        )

        self.system_object = await self.root_object.add_object(
            index,
            "System",
        )

        self.filters_object = await self.root_object.add_object(
            index,
            "Filters",
        )

        server_running = await self.system_object.add_variable(
            index,
            "ServerRunning",
            ua.Variant(
                False,
                ua.VariantType.Boolean,
            ),
        )

        collector_running = await self.system_object.add_variable(
            index,
            "CollectorRunning",
            ua.Variant(
                False,
                ua.VariantType.Boolean,
            ),
        )

        total_filters = await self.system_object.add_variable(
            index,
            "TotalFilters",
            ua.Variant(
                0,
                ua.VariantType.Int64,
            ),
        )

        active_filters = await self.system_object.add_variable(
            index,
            "ActiveFilters",
            ua.Variant(
                0,
                ua.VariantType.Int64,
            ),
        )

        last_update = await self.system_object.add_variable(
            index,
            "LastUpdate",
            ua.Variant(
                "",
                ua.VariantType.String,
            ),
        )

        self.system_nodes = SystemOpcUaNodes(
            server_running=(server_running),
            collector_running=(collector_running),
            total_filters=(total_filters),
            active_filters=(active_filters),
            last_update=(last_update),
        )

    async def _create_filter_nodes(
        self,
        snapshot: FilterServerSnapshot,
    ) -> FilterOpcUaNodes:
        if self.filters_object is None:
            raise RuntimeError("Address space OPC UA " "nie został utworzony.")

        if self.namespace_index is None:
            raise RuntimeError("Brak namespace index.")

        index = self.namespace_index

        filter_object = await self.filters_object.add_object(
            index,
            snapshot.name,
        )

        filter_id = await filter_object.add_variable(
            index,
            "FilterId",
            ua.Variant(
                snapshot.filter_id,
                ua.VariantType.Int64,
            ),
        )

        active = await filter_object.add_variable(
            index,
            "Active",
            ua.Variant(
                snapshot.active,
                ua.VariantType.Boolean,
            ),
        )

        delta_p = await filter_object.add_variable(
            index,
            "DeltaP",
            ua.Variant(
                snapshot.delta_p,
                ua.VariantType.Double,
            ),
        )

        threshold = await filter_object.add_variable(
            index,
            "DeltaPThreshold",
            ua.Variant(
                snapshot.delta_p_threshold,
                ua.VariantType.Double,
            ),
        )

        working = await filter_object.add_variable(
            index,
            "Working",
            ua.Variant(
                snapshot.working,
                ua.VariantType.Boolean,
            ),
        )

        alarm_active = await filter_object.add_variable(
            index,
            "AlarmActive",
            ua.Variant(
                snapshot.alarm_active,
                ua.VariantType.Boolean,
            ),
        )

        last_working_delta_p = await filter_object.add_variable(
            index,
            "LastWorkingDeltaP",
            ua.Variant(
                snapshot.last_working_delta_p,
                ua.VariantType.Double,
            ),
        )

        dirty_percent = await filter_object.add_variable(
            index,
            "DirtyPercent",
            ua.Variant(
                snapshot.dirty_percent,
                ua.VariantType.Double,
            ),
        )

        status = await filter_object.add_variable(
            index,
            "Status",
            ua.Variant(
                snapshot.status,
                ua.VariantType.String,
            ),
        )

        last_update = await filter_object.add_variable(
            index,
            "LastUpdate",
            ua.Variant(
                snapshot.last_update,
                ua.VariantType.String,
            ),
        )

        # Celowo NIE wywołujemy
        # set_writable().
        # Klienci OPC UA mają tylko odczyt.

        return FilterOpcUaNodes(
            object_node=(filter_object),
            filter_id=(filter_id),
            active=(active),
            delta_p=(delta_p),
            delta_p_threshold=(threshold),
            working=(working),
            alarm_active=(alarm_active),
            last_working_delta_p=(last_working_delta_p),
            dirty_percent=(dirty_percent),
            status=(status),
            last_update=(last_update),
        )

    async def _write_filter_snapshot(
        self,
        nodes: FilterOpcUaNodes,
        snapshot: FilterServerSnapshot,
    ) -> None:
        await nodes.filter_id.write_value(
            ua.Variant(
                snapshot.filter_id,
                ua.VariantType.Int64,
            )
        )

        await nodes.active.write_value(
            ua.Variant(
                snapshot.active,
                ua.VariantType.Boolean,
            )
        )

        await nodes.delta_p.write_value(
            ua.Variant(
                snapshot.delta_p,
                ua.VariantType.Double,
            )
        )

        await nodes.delta_p_threshold.write_value(
            ua.Variant(
                snapshot.delta_p_threshold,
                ua.VariantType.Double,
            )
        )

        await nodes.working.write_value(
            ua.Variant(
                snapshot.working,
                ua.VariantType.Boolean,
            )
        )

        await nodes.alarm_active.write_value(
            ua.Variant(
                snapshot.alarm_active,
                ua.VariantType.Boolean,
            )
        )

        await nodes.last_working_delta_p.write_value(
            ua.Variant(
                snapshot.last_working_delta_p,
                ua.VariantType.Double,
            )
        )

        await nodes.dirty_percent.write_value(
            ua.Variant(
                snapshot.dirty_percent,
                ua.VariantType.Double,
            )
        )

        await nodes.status.write_value(
            ua.Variant(
                snapshot.status,
                ua.VariantType.String,
            )
        )

        await nodes.last_update.write_value(
            ua.Variant(
                snapshot.last_update,
                ua.VariantType.String,
            )
        )

    async def _sync_filter_nodes(
        self,
        snapshot: ServerSnapshot,
    ) -> None:
        current_ids = {item.filter_id for item in snapshot.filters}

        stale_ids = set(self.filter_nodes) - current_ids

        for filter_id in stale_ids:
            nodes = self.filter_nodes[filter_id]

            await nodes.object_node.delete(recursive=True)

            del self.filter_nodes[filter_id]

        for filter_snapshot in snapshot.filters:
            nodes = self.filter_nodes.get(filter_snapshot.filter_id)

            if nodes is None:
                nodes = await self._create_filter_nodes(filter_snapshot)

                self.filter_nodes[filter_snapshot.filter_id] = nodes

            await self._write_filter_snapshot(
                nodes,
                filter_snapshot,
            )

    async def refresh(
        self,
    ) -> ServerSnapshot:
        if self.system_nodes is None:
            raise RuntimeError("OPC UA Server nie jest " "zainicjalizowany.")

        snapshot = build_server_snapshot(self.repository)

        await self.system_nodes.server_running.write_value(
            ua.Variant(
                self.running,
                ua.VariantType.Boolean,
            )
        )

        await self.system_nodes.collector_running.write_value(
            ua.Variant(
                snapshot.collector_running,
                ua.VariantType.Boolean,
            )
        )

        await self.system_nodes.total_filters.write_value(
            ua.Variant(
                snapshot.total_filters,
                ua.VariantType.Int64,
            )
        )

        await self.system_nodes.active_filters.write_value(
            ua.Variant(
                snapshot.active_filters,
                ua.VariantType.Int64,
            )
        )

        await self.system_nodes.last_update.write_value(
            ua.Variant(
                snapshot.last_update,
                ua.VariantType.String,
            )
        )

        await self._sync_filter_nodes(snapshot)

        return snapshot

    async def start(
        self,
    ) -> None:
        if self.running:
            return

        if self.server is None:
            await self.initialise()

        self._stop_requested = False

        await self.server.start()

        self.running = True

        await self.refresh()

    async def stop(
        self,
    ) -> None:
        self._stop_requested = True

        if self.server is None or not self.running:
            self.running = False

            return

        if self.system_nodes is not None:
            try:
                await self.system_nodes.server_running.write_value(
                    ua.Variant(
                        False,
                        ua.VariantType.Boolean,
                    )
                )

            except Exception:
                pass

        await self.server.stop()

        self.running = False

    def request_stop(
        self,
    ) -> None:
        self._stop_requested = True

    async def serve_forever(
        self,
    ) -> None:
        await self.start()

        try:
            while not self._stop_requested:
                await asyncio.sleep(self.refresh_interval)

                await self.refresh()

        finally:
            await self.stop()
