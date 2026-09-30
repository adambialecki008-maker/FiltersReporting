from __future__ import annotations

import argparse
import asyncio
import random
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

# Ten plik leży w tools/, poza pakietem aplikacji.
# Dodajemy katalog projektu do sys.path tylko po to,
# żeby móc użyć istniejących helperów FiltersReporting.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from asyncua import Server, ua

from filters_reporting.opcua.auth import (
    FiltersReportingUserManager,
    OpcUaAuthenticationConfig,
    build_identity_tokens,
    hash_password,
)
from filters_reporting.opcua.certificate_service import (
    ApplicationCertificatePaths,
    create_default_certificate_paths,
    generate_application_certificate,
)
from filters_reporting.opcua.security import (
    build_server_security_policies,
)


@dataclass(frozen=True)
class SimulatedMachineConfig:
    name: str
    port: int
    username: str
    password: str

    security_policy: str = "Aes256Sha256RsaPss"
    security_mode: str = "SignAndEncrypt"

    delta_p_alarm_threshold: float = 1800.0

    @property
    def endpoint(self) -> str:
        machine_slug = self.name.casefold().replace("_", "")

        return f"opc.tcp://localhost:{self.port}/" f"{machine_slug}/"

    @property
    def application_uri(self) -> str:
        return "urn:localhost:" "FiltersReportingSimulator:" f"{self.name}"

    @property
    def namespace_uri(self) -> str:
        return "urn:FiltersReportingSimulator:" f"{self.name}"


DEFAULT_MACHINES = (
    SimulatedMachineConfig(
        name="Esta_01",
        port=4851,
        username="esta01",
        password="Esta01_Test!",
        security_policy="Aes256Sha256RsaPss",
        security_mode="SignAndEncrypt",
        delta_p_alarm_threshold=1800.0,
    ),
    SimulatedMachineConfig(
        name="DustCollector_02",
        port=4852,
        username="dust02",
        password="Dust02_Test!",
        security_policy="Basic256Sha256",
        security_mode="SignAndEncrypt",
        delta_p_alarm_threshold=1500.0,
    ),
    SimulatedMachineConfig(
        name="Ventilation_03",
        port=4853,
        username="vent03",
        password="Vent03_Test!",
        security_policy="Aes128Sha256RsaOaep",
        security_mode="SignAndEncrypt",
        delta_p_alarm_threshold=1200.0,
    ),
    SimulatedMachineConfig(
        name="FilterStation_04",
        port=4854,
        username="filter04",
        password="Filter04_Test!",
        security_policy="Basic256Sha256",
        security_mode="Sign",
        delta_p_alarm_threshold=900.0,
    ),
    SimulatedMachineConfig(
        name="ProcessAir_05",
        port=4855,
        username="air05",
        password="Air05_Test!",
        security_policy="Aes256Sha256RsaPss",
        security_mode="Sign",
        delta_p_alarm_threshold=2100.0,
    ),
)


@dataclass
class SimulatedMachineRuntime:
    config: SimulatedMachineConfig

    server: Serverprint

    namespace_index: int

    certificate_paths: ApplicationCertificatePaths

    client_trusted_dir: Path

    delta_p_node: object
    status_node: object
    alarm_node: object

    delta_p: float = 300.0


def build_node_ids(
    namespace_index: int,
) -> dict[str, str]:
    return {
        "delta_p": (f"ns={namespace_index};s=DeltaP"),
        "status": (f"ns={namespace_index};s=Status"),
        "alarm": (f"ns={namespace_index};s=AlarmActive"),
    }


def prepare_server_certificate(
    config: SimulatedMachineConfig,
    base_dir: Path,
) -> tuple[
    ApplicationCertificatePaths,
    Path,
]:
    machine_dir = base_dir / config.name

    certificate_paths = create_default_certificate_paths(machine_dir / "server")

    generate_application_certificate(
        paths=certificate_paths,
        application_uri=config.application_uri,
        hostname="localhost",
        common_name=("FiltersReporting Simulator " f"- {config.name}"),
        organization=("FiltersReporting Simulator"),
        overwrite=True,
    )

    # Folder, który można wskazać
    # w FiltersReporting jako Trusted certificates.
    client_trusted_dir = machine_dir / "trusted_for_client"

    client_trusted_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    trusted_server_certificate = client_trusted_dir / f"{config.name}_server.der"

    shutil.copy2(
        certificate_paths.certificate,
        trusted_server_certificate,
    )

    return (
        certificate_paths,
        client_trusted_dir,
    )


async def create_machine(
    config: SimulatedMachineConfig,
    base_dir: Path,
) -> SimulatedMachineRuntime:
    (
        certificate_paths,
        client_trusted_dir,
    ) = prepare_server_certificate(
        config,
        base_dir,
    )

    authentication = OpcUaAuthenticationConfig(
        allow_anonymous=False,
        username=config.username,
        password_hash=hash_password(
            config.password,
        ),
    )

    server = Server(
        user_manager=(
            FiltersReportingUserManager(
                authentication,
            )
        )
    )

    await server.init()

    server.set_endpoint(
        config.endpoint,
    )

    server.set_server_name("FiltersReporting Simulator " f"- {config.name}")

    await server.set_application_uri(
        config.application_uri,
    )

    server.set_security_policy(
        build_server_security_policies(
            policy=(config.security_policy),
            mode=(config.security_mode),
            allow_no_security=False,
        )
    )

    server.set_identity_tokens(
        build_identity_tokens(
            authentication,
        )
    )

    await server.load_certificate(
        certificate_paths.certificate,
    )

    await server.load_private_key(
        certificate_paths.private_key,
    )

    namespace_index = await server.register_namespace(
        config.namespace_uri,
    )

    machine_object = await server.nodes.objects.add_object(
        ua.NodeId(
            f"Machine:{config.name}",
            namespace_index,
        ),
        config.name,
    )

    delta_p_node = await machine_object.add_variable(
        ua.NodeId(
            "DeltaP",
            namespace_index,
        ),
        "DeltaP",
        ua.Variant(
            300.0,
            ua.VariantType.Double,
        ),
    )

    status_node = await machine_object.add_variable(
        ua.NodeId(
            "Status",
            namespace_index,
        ),
        "Status",
        ua.Variant(
            True,
            ua.VariantType.Boolean,
        ),
    )

    alarm_node = await machine_object.add_variable(
        ua.NodeId(
            "AlarmActive",
            namespace_index,
        ),
        "AlarmActive",
        ua.Variant(
            False,
            ua.VariantType.Boolean,
        ),
    )

    return SimulatedMachineRuntime(
        config=config,
        server=server,
        namespace_index=namespace_index,
        certificate_paths=(certificate_paths),
        client_trusted_dir=(client_trusted_dir),
        delta_p_node=delta_p_node,
        status_node=status_node,
        alarm_node=alarm_node,
    )


def print_machine_configuration(
    runtime: SimulatedMachineRuntime,
) -> None:
    config = runtime.config

    node_ids = build_node_ids(
        runtime.namespace_index,
    )

    print()
    print("=" * 76)
    print(f"MASZYNA: {config.name}")
    print("=" * 76)

    print("Endpoint:             " f"{config.endpoint}")

    print("Security Policy:      " f"{config.security_policy}")

    print("Security Mode:        " f"{config.security_mode}")

    print("Authentication:       " "UsernamePassword")

    print("Username:             " f"{config.username}")

    print("Password:             " f"{config.password}")

    print("Server certificate:   " f"{runtime.certificate_paths.certificate}")

    print("Server private key:   " f"{runtime.certificate_paths.private_key}")

    print("Trusted certificates: " f"{runtime.client_trusted_dir}")

    print()
    print("NodeId:")

    print("  DeltaP:             " f"{node_ids['delta_p']}")

    print("  Status:             " f"{node_ids['status']}")

    print("  AlarmActive:        " f"{node_ids['alarm']}")

    print()
    print("W FiltersReporting:")

    print("  1. Ustaw powyższy endpoint.")

    print("  2. Ustaw Security Policy " "Aes256Sha256RsaPss.")

    print("  3. Ustaw Security Mode " "SignAndEncrypt.")

    print("  4. Ustaw UsernamePassword " "i login/hasło tej maszyny.")

    print("  5. Wskaż Server certificate.")

    print("  6. Wskaż Trusted certificates.")

    print(
        "  7. Kliknij 'Generuj certyfikat "
        "dla tej maszyny', aby klient "
        "FiltersReporting miał własny certyfikat."
    )

    print("=" * 76)


async def update_machine(
    runtime: SimulatedMachineRuntime,
    interval_seconds: float,
) -> None:
    config = runtime.config

    # Każda maszyna startuje z innej losowej wartości.
    runtime.delta_p = random.uniform(
        150.0,
        2200.0,
    )

    while True:
        # DeltaP czasem lekko się zmienia,
        # a czasem dostaje większy skok.
        if random.random() < 0.08:
            runtime.delta_p = random.uniform(
                100.0,
                2400.0,
            )
        else:
            runtime.delta_p += random.uniform(
                -180.0,
                180.0,
            )

        runtime.delta_p = max(
            0.0,
            min(
                2500.0,
                runtime.delta_p,
            ),
        )

        # Około 95% czasu maszyna pracuje.
        working = random.random() > 0.05

        # Alarm głównie zależy od DeltaP,
        # ale sporadycznie możemy zasymulować
        # dodatkowy alarm procesowy.
        alarm = (
            runtime.delta_p >= config.delta_p_alarm_threshold or random.random() < 0.02
        )

        await runtime.delta_p_node.write_value(
            ua.Variant(
                round(
                    runtime.delta_p,
                    2,
                ),
                ua.VariantType.Double,
            )
        )

        await runtime.status_node.write_value(
            ua.Variant(
                working,
                ua.VariantType.Boolean,
            )
        )

        await runtime.alarm_node.write_value(
            ua.Variant(
                alarm,
                ua.VariantType.Boolean,
            )
        )

        await asyncio.sleep(
            interval_seconds,
        )


async def run_simulator(
    *,
    base_dir: Path,
    interval_seconds: float,
) -> None:
    if interval_seconds <= 0:
        raise ValueError("interval_seconds musi być > 0.")

    base_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    runtimes: list[SimulatedMachineRuntime] = []

    tasks: list[asyncio.Task] = []

    try:
        for config in DEFAULT_MACHINES:
            runtime = await create_machine(
                config,
                base_dir,
            )

            await runtime.server.start()

            runtimes.append(
                runtime,
            )

            tasks.append(
                asyncio.create_task(
                    update_machine(
                        runtime,
                        interval_seconds,
                    )
                )
            )

        print()
        print("Niezależne serwery OPC UA działają.")

        print("Ctrl+C kończy symulator.")

        print()

        await asyncio.gather(
            *tasks,
        )

    finally:
        for task in tasks:
            task.cancel()

        if tasks:
            await asyncio.gather(
                *tasks,
                return_exceptions=True,
            )

        for runtime in reversed(
            runtimes,
        ):
            try:
                await runtime.server.stop()

            except Exception:
                pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Dwa niezależne serwery OPC UA " "do smoke testów FiltersReporting v1.0."
        )
    )

    parser.add_argument(
        "--data-dir",
        type=Path,
        default=(PROJECT_ROOT / ".filters_reporting_simulator"),
        help=("Katalog danych/certyfikatów symulatora."),
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help=("Interwał zmian danych w sekundach."),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    try:
        asyncio.run(
            run_simulator(
                base_dir=args.data_dir,
                interval_seconds=args.interval,
            )
        )

    except KeyboardInterrupt:
        print()
        print("Symulator zatrzymany.")


if __name__ == "__main__":
    main()
