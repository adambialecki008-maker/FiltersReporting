from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

from filters_reporting.opcua.server_runner import (
    OpcUaServerRunner,
)


class FakeServer:
    def __init__(
        self,
        repository,
        settings,
    ):
        self.repository = repository
        self.settings = settings

        self.refresh_interval = 0.01

        self.started = False
        self.stopped = False
        self.refresh_count = 0

    async def start(
        self,
    ):
        self.started = True

    async def refresh(
        self,
    ):
        self.refresh_count += 1

    async def stop(
        self,
    ):
        self.stopped = True


class FailingServer:
    refresh_interval = 0.01

    def __init__(
        self,
        repository,
        settings,
    ):
        self.repository = repository
        self.settings = settings

    async def start(
        self,
    ):
        raise RuntimeError("Test server start error")

    async def refresh(
        self,
    ):
        pass

    async def stop(
        self,
    ):
        pass


def test_runner_does_not_start_when_server_is_disabled():
    repository = object()

    settings = SimpleNamespace(
        opc_server_enabled=False,
    )

    created_servers = []

    def server_factory(
        repository,
        settings,
    ):
        server = FakeServer(
            repository,
            settings,
        )

        created_servers.append(server)

        return server

    runner = OpcUaServerRunner(
        repository,
        settings_loader=lambda: settings,
        server_factory=server_factory,
    )

    result = runner.start()

    assert result is False

    assert runner.running is False

    assert created_servers == []


def test_runner_starts_enabled_server():
    repository = object()

    settings = SimpleNamespace(
        opc_server_enabled=True,
        opc_server_endpoint=("opc.tcp://localhost:" "4840/filtersreporting/"),
    )

    created_servers = []

    def server_factory(
        repository,
        settings,
    ):
        server = FakeServer(
            repository,
            settings,
        )

        created_servers.append(server)

        return server

    runner = OpcUaServerRunner(
        repository,
        settings_loader=lambda: settings,
        server_factory=server_factory,
    )

    try:
        result = runner.start()

        assert result is True

        assert runner.running is True

        assert len(created_servers) == 1

        assert created_servers[0].started is True

    finally:
        runner.stop()


def test_runner_refreshes_server():
    repository = object()

    settings = SimpleNamespace(
        opc_server_enabled=True,
        opc_server_endpoint=("opc.tcp://localhost:" "4840/filtersreporting/"),
    )

    created_servers = []

    def server_factory(
        repository,
        settings,
    ):
        server = FakeServer(
            repository,
            settings,
        )

        created_servers.append(server)

        return server

    runner = OpcUaServerRunner(
        repository,
        settings_loader=lambda: settings,
        server_factory=server_factory,
    )

    try:
        runner.start()

        time.sleep(0.05)

        assert created_servers[0].refresh_count > 0

    finally:
        runner.stop()


def test_runner_stops_server():
    repository = object()

    settings = SimpleNamespace(
        opc_server_enabled=True,
        opc_server_endpoint=("opc.tcp://localhost:" "4840/filtersreporting/"),
    )

    created_servers = []

    def server_factory(
        repository,
        settings,
    ):
        server = FakeServer(
            repository,
            settings,
        )

        created_servers.append(server)

        return server

    runner = OpcUaServerRunner(
        repository,
        settings_loader=lambda: settings,
        server_factory=server_factory,
    )

    runner.start()

    result = runner.stop()

    assert result is True

    assert runner.running is False

    assert created_servers[0].stopped is True


def test_runner_start_is_idempotent():
    repository = object()

    settings = SimpleNamespace(
        opc_server_enabled=True,
        opc_server_endpoint=("opc.tcp://localhost:" "4840/filtersreporting/"),
    )

    created_servers = []

    def server_factory(
        repository,
        settings,
    ):
        server = FakeServer(
            repository,
            settings,
        )

        created_servers.append(server)

        return server

    runner = OpcUaServerRunner(
        repository,
        settings_loader=lambda: settings,
        server_factory=server_factory,
    )

    try:
        assert runner.start() is True

        assert runner.start() is True

        assert len(created_servers) == 1

    finally:
        runner.stop()


def test_runner_exposes_start_error():
    repository = object()

    settings = SimpleNamespace(
        opc_server_enabled=True,
        opc_server_endpoint=("opc.tcp://localhost:" "4840/filtersreporting/"),
    )

    runner = OpcUaServerRunner(
        repository,
        settings_loader=lambda: settings,
        server_factory=FailingServer,
    )

    with pytest.raises(
        RuntimeError,
        match=("Test server start error"),
    ):
        runner.start()

    assert runner.running is False

    assert isinstance(
        runner.last_error,
        RuntimeError,
    )


def test_runner_validates_timeouts():
    with pytest.raises(ValueError):
        OpcUaServerRunner(
            object(),
            start_timeout=0,
        )

    with pytest.raises(ValueError):
        OpcUaServerRunner(
            object(),
            stop_timeout=0,
        )
