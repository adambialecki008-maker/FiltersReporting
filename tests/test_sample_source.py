from unittest.mock import AsyncMock, Mock

import pytest

import filters_reporting.collection.sample_source as sample_source


@pytest.mark.asyncio
async def test_get_current_samples_uses_simulator(monkeypatch):
    filters = [object(), object()]
    expected = [object()]
    generate = Mock(return_value=expected)

    monkeypatch.setattr(sample_source, "DATA_SOURCE", "SIMULATOR")
    monkeypatch.setattr(
        sample_source,
        "generate_current_samples",
        generate,
    )

    result = await sample_source.get_current_samples(filters)

    assert result is expected
    generate.assert_called_once_with(filters)


@pytest.mark.asyncio
async def test_get_current_samples_simulator_requires_filters(monkeypatch):
    monkeypatch.setattr(sample_source, "DATA_SOURCE", "SIMULATOR")

    with pytest.raises(
        ValueError,
        match="Simulator wymaga listy filtrów",
    ):
        await sample_source.get_current_samples()


@pytest.mark.asyncio
async def test_get_current_samples_uses_opc_ua(monkeypatch):
    filters = [object()]
    expected = [object()]
    read = AsyncMock(return_value=expected)

    monkeypatch.setattr(sample_source, "DATA_SOURCE", "OPC_UA")
    monkeypatch.setattr(
        sample_source,
        "read_opc_ua_samples",
        read,
    )

    result = await sample_source.get_current_samples(filters)

    assert result is expected
    read.assert_awaited_once_with(filters)


@pytest.mark.asyncio
async def test_get_current_samples_opc_ua_requires_filters(monkeypatch):
    monkeypatch.setattr(sample_source, "DATA_SOURCE", "OPC_UA")

    with pytest.raises(
        ValueError,
        match="OPC_UA wymaga listy filtrów",
    ):
        await sample_source.get_current_samples()


@pytest.mark.asyncio
async def test_get_current_samples_rejects_unknown_source(monkeypatch):
    monkeypatch.setattr(sample_source, "DATA_SOURCE", "UNKNOWN")

    with pytest.raises(
        ValueError,
        match="Nieznane źródło danych: UNKNOWN",
    ):
        await sample_source.get_current_samples([])
