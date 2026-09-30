import pytest
import asyncio
from filters_reporting.models.filter import Filter
from filters_reporting.collection.opc_ua_client import (
    opc_clients,
    sync_opc_clients,
    OpcUaFilterClient,
    get_filter_sample_with_timeout,
    client_config_changed,
    read_opc_ua_samples,
)
import filters_reporting.collection.opc_ua_client as opc_ua_client
from fake_clients import (
    FakeDisconnectedClient,
    FakeReconnectClient,
    FakeReconnectFailClient,
)
from unittest.mock import Mock, AsyncMock
from filters_reporting.opcua.security import OpcUaSecurityConfig


@pytest.mark.asyncio
async def test_sync_opc_clients_adds_missing_clients():
    opc_clients.clear()

    filters = [
        Filter(name="F1", filter_id=1, opc_url="opc.tcp://localhost:4841/filters/"),
        Filter(name="F2", filter_id=2, opc_url="opc.tcp://localhost:4842/filters/"),
    ]

    await sync_opc_clients(filters)

    assert len(opc_clients) == 2
    assert 1 in opc_clients
    assert 2 in opc_clients


@pytest.mark.asyncio
async def test_sync_opc_clients_removes_inactive_client():
    opc_clients.clear()

    filter_1 = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4841/filters/",
    )
    filter_2 = Filter(
        name="F2",
        filter_id=2,
        opc_url="opc.tcp://localhost:4842/filters/",
    )

    await sync_opc_clients([filter_1, filter_2])

    await sync_opc_clients([filter_1])

    assert 1 in opc_clients
    assert 2 not in opc_clients


@pytest.mark.asyncio
async def test_sync_opc_clients_replaces_client_when_url_changes():
    opc_clients.clear()

    old_filter = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4841/filters/",
    )

    await sync_opc_clients([old_filter])

    old_client = opc_clients[1]

    new_filter = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4999/filters/",
    )

    await sync_opc_clients([new_filter])

    new_client = opc_clients[1]

    assert new_client is not old_client
    assert new_client.filter_obj.opc_url == "opc.tcp://localhost:4999/filters/"


@pytest.mark.asyncio
async def test_sync_opc_clients_replaces_client_when_name_changes():
    opc_clients.clear()

    old_filter = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4841/filters/",
    )

    await sync_opc_clients([old_filter])
    old_client = opc_clients[1]

    new_filter = Filter(
        name="F1_NEW",
        filter_id=1,
        opc_url="opc.tcp://localhost:4841/filters/",
    )

    await sync_opc_clients([new_filter])

    new_client = opc_clients[1]

    assert new_client is not old_client


@pytest.mark.asyncio
async def test_sync_opc_clients_reuses_client_when_config_unchanged():
    opc_clients.clear()

    filter_1 = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4841/filters/",
    )

    await sync_opc_clients([filter_1])
    old_client = opc_clients[1]

    same_filter = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4841/filters/",
    )

    await sync_opc_clients([same_filter])
    new_client = opc_clients[1]

    assert new_client is old_client


@pytest.mark.asyncio
async def test_read_sample_reconnect_retries_after_error():
    filter_obj = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4841/filters/",
    )

    expected_sample = object()

    client = FakeReconnectClient(
        filter_obj=filter_obj,
        expected_sample=expected_sample,
    )

    result = await client.read_sample_reconnect()

    assert result is expected_sample
    assert client.read_count == 2
    assert client.disconnect_count == 1
    assert client.connect_count == 1


@pytest.mark.asyncio
async def test_read_sample_reconnect_returns_none_when_reconnect_fails():
    filter_obj = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4841/filters/",
    )

    client = FakeReconnectFailClient(filter_obj)

    result = await client.read_sample_reconnect()

    assert result is None


class FakeSlowClient:
    async def read_sample_reconnect(self):
        await asyncio.sleep(1)


@pytest.mark.asyncio
async def test_get_filter_sample_returns_none_on_timeout(monkeypatch):
    filter_obj = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4841/filters/",
    )

    opc_clients.clear()
    opc_clients[1] = FakeSlowClient()

    monkeypatch.setattr(
        opc_ua_client,
        "OPC_READ_TIMEOUT_SECONDS",
        0.01,
    )

    result = await get_filter_sample_with_timeout(filter_obj)

    assert result is None


def test_client_config_changed_returns_false_when_name_and_url_are_same():
    filter_1 = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4841/filters/",
    )
    client = OpcUaFilterClient(filter_1)

    filter_2 = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4841/filters/",
    )
    assert client_config_changed(filter_2, client) is False


def test_client_config_changed_returns_true_when_name_changed():
    filter_1 = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4841/filters/",
    )
    client = OpcUaFilterClient(filter_1)
    filter_2 = Filter(
        name="F2",
        filter_id=1,
        opc_url="opc.tcp://localhost:4841/filters/",
    )

    assert client_config_changed(filter_2, client)


def test_client_config_changed_returns_true_when_url_changed():
    filter_1 = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4841/filters/",
    )
    client = OpcUaFilterClient(filter_1)
    filter_2 = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4899/filters/",
    )

    assert client_config_changed(filter_2, client)


def test_client_config_changed_returns_true_when_name_and_url_changed():
    filter_1 = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4841/filters/",
    )
    client = OpcUaFilterClient(filter_1)
    filter_2 = Filter(
        name="F2",
        filter_id=1,
        opc_url="opc.tcp://localhost:4899/filters/",
    )

    assert client_config_changed(filter_2, client)


@pytest.mark.asyncio
async def test_read_opc_ua_sample_skips_failed_sample(monkeypatch):
    filter_1 = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4841/filters",
    )
    filter_2 = Filter(
        name="F2",
        filter_id=2,
        opc_url="opc.tcp://localhost:4842/filters/",
    )
    expected_sample = object()
    opc_clients.clear()

    async def fake_get_filter_sample_with_timeout(filter_obj):
        if filter_obj.filter_id == 1:
            return expected_sample
        return None

    monkeypatch.setattr(
        opc_ua_client,
        "get_filter_sample_with_timeout",
        fake_get_filter_sample_with_timeout,
    )

    result = await read_opc_ua_samples([filter_1, filter_2])
    assert len(result) == 1
    assert result == [expected_sample]


@pytest.mark.asyncio
async def test_read_opc_ua_samples_returns_empty_list_when_all_reads_fail(monkeypatch):
    filter_1 = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4841/filters/",
    )
    filter_2 = Filter(
        name="F2",
        filter_id=2,
        opc_url="opc.tcp://localhost:4842/filters/",
    )

    opc_clients.clear()

    async def fake_get_filter_sample_with_timeout(filter_obj):
        return None

    monkeypatch.setattr(
        opc_ua_client,
        "get_filter_sample_with_timeout",
        fake_get_filter_sample_with_timeout,
    )

    result = await read_opc_ua_samples([filter_1, filter_2])
    assert result == []


@pytest.mark.asyncio
async def test_read_opc_ua_samples_keeps_input_order_when_reads_finish_out_of_order(
    monkeypatch,
):
    filter_1 = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4841/filters/",
    )
    filter_2 = Filter(
        name="F2",
        filter_id=2,
        opc_url="opc.tcp://localhost:4842/filters/",
    )
    expected_sample_1 = object()
    expected_sample_2 = object()
    opc_clients.clear()

    async def fake_get_filter_sample_with_timeout(filter_obj):
        if filter_obj.filter_id == 1:
            await asyncio.sleep(0.05)
            return expected_sample_1
        elif filter_obj.filter_id == 2:
            await asyncio.sleep(0.01)
            return expected_sample_2
        else:
            return None

    monkeypatch.setattr(
        opc_ua_client,
        "get_filter_sample_with_timeout",
        fake_get_filter_sample_with_timeout,
    )

    result = await read_opc_ua_samples([filter_1, filter_2])

    assert result == [expected_sample_1, expected_sample_2]


@pytest.mark.asyncio
async def test_sync_opc_clients_removes_all_clients_when_no_active_filters():
    opc_clients.clear()
    filter_1 = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4841/filters/",
    )

    filter_2 = Filter(
        name="F2",
        filter_id=2,
        opc_url="opc.tcp://localhost:4842/filters/",
    )

    await sync_opc_clients([filter_1, filter_2])
    await sync_opc_clients([])

    assert opc_clients == {}


@pytest.mark.asyncio
async def test_read_sample_reconnect_connects_when_client_is_none():
    filter_obj = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4841/filters/",
    )
    expected_sample = object()
    client = FakeDisconnectedClient(filter_obj, expected_sample)
    result = await client.read_sample_reconnect()
    assert client.connect_count == 1
    assert client.read_count == 1
    assert client.disconnect_count == 0
    assert result is expected_sample


@pytest.mark.asyncio
async def test_disconnect_all_clients_disconnects_every_client(monkeypatch):
    disconnected = []

    class FakeClient:
        def __init__(self, name):
            self.name = name

        async def disconnect(self):
            disconnected.append(self.name)

    fake_clients = {
        "filter_1": FakeClient("filter_1"),
        "filter_2": FakeClient("filter_2"),
    }

    monkeypatch.setattr(
        opc_ua_client,
        "opc_clients",
        fake_clients,
    )

    await opc_ua_client.disconnect_all_clients()

    assert disconnected == ["filter_1", "filter_2"]


def test_client_config_changed_returns_true_when_node_id_changed():
    old_filter = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4840",
        delta_p_node_id="ns=3;s=OldDeltaP",
        status_node_id="ns=3;s=Status",
        alarm_node_id="ns=3;s=Alarm",
    )
    client = OpcUaFilterClient(old_filter)
    new_filter = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4840",
        delta_p_node_id="ns=3;s=NewDeltaP",
        status_node_id="ns=3;s=Status",
        alarm_node_id="ns=3;s=Alarm",
    )
    assert (
        client_config_changed(
            new_filter,
            client,
        )
        is True
    )


@pytest.mark.asyncio
async def test_connect_uses_configured_node_ids(monkeypatch):
    filter_obj = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4840",
        delta_p_node_id="ns=3;s=Filter.DeltaP",
        status_node_id="ns=3;s=Filter.Status",
        alarm_node_id="ns=3;s=Filter.Alarm",
    )
    fake_client = Mock()
    fake_client.connect = AsyncMock()
    # Potrzebne tylko dlatego, że STARY connect()
    # nadal używa namespace + get_child()
    fake_client.get_namespace_index = AsyncMock(return_value=3)
    opc_node = Mock()
    opc_node.get_child = AsyncMock(
        side_effect=[
            "OLD_DELTA_P",
            "OLD_STATUS",
            "OLD_ALARM",
        ]
    )
    filter_node = Mock()
    filter_node.get_child = AsyncMock(return_value=opc_node)
    objects_node = Mock()
    objects_node.get_child = AsyncMock(return_value=filter_node)
    fake_client.nodes = Mock()
    fake_client.nodes.objects = objects_node
    # Tego będzie używał NOWY connect()
    fake_client.get_node = Mock(side_effect=lambda node_id: node_id)
    monkeypatch.setattr(
        opc_ua_client,
        "Client",
        Mock(return_value=fake_client),
    )

    client = OpcUaFilterClient(filter_obj)
    await client.connect()
    assert client.delta_p_node == "ns=3;s=Filter.DeltaP"
    assert client.status_node == "ns=3;s=Filter.Status"
    assert client.alarm_active_node == "ns=3;s=Filter.Alarm"


@pytest.mark.asyncio
async def test_test_filter_connection_reads_configured_nodes(
    monkeypatch,
):
    filter_obj = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4840",
        delta_p_node_id="ns=3;s=F1.DeltaP",
        status_node_id="ns=3;s=F1.Status",
        alarm_node_id="ns=3;s=F1.Alarm",
    )
    delta_p_node = Mock()
    delta_p_node.read_value = AsyncMock(return_value=1234)
    status_node = Mock()
    status_node.read_value = AsyncMock(return_value=True)
    alarm_node = Mock()
    alarm_node.read_value = AsyncMock(return_value=False)
    fake_client = Mock()
    fake_client.connect = AsyncMock()
    fake_client.disconnect = AsyncMock()
    fake_client.get_node = Mock(
        side_effect=[
            delta_p_node,
            status_node,
            alarm_node,
        ]
    )
    monkeypatch.setattr(
        opc_ua_client,
        "Client",
        Mock(return_value=fake_client),
    )
    monkeypatch.setattr(
        opc_ua_client,
        "get_current_security_config",
        Mock(
            return_value=OpcUaSecurityConfig(
                policy="None",
                mode="None",
            )
        ),
    )
    result = await opc_ua_client.test_filter_connection(filter_obj)
    assert result == {
        "delta_p": 1234,
        "status": True,
        "alarm_active": False,
    }
    fake_client.disconnect.assert_awaited_once()
