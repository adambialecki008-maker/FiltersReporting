from unittest.mock import Mock

import pytest

import filters_reporting.collection.simulator as simulator
from filters_reporting.models.filter import Filter


@pytest.fixture(autouse=True)
def clear_last_delta_p():
    simulator.last_delta_p.clear()
    yield
    simulator.last_delta_p.clear()


def test_generate_delta_p_initializes_value_and_applies_change(monkeypatch):
    randint = Mock(side_effect=[100, 20])
    monkeypatch.setattr(simulator.random, "randint", randint)

    result = simulator.generate_delta_p(1)

    assert result == 120
    assert simulator.last_delta_p[1] == 120
    assert randint.call_count == 2


def test_generate_delta_p_reuses_previous_value(monkeypatch):
    simulator.last_delta_p[1] = 500
    randint = Mock(return_value=-80)
    monkeypatch.setattr(simulator.random, "randint", randint)

    result = simulator.generate_delta_p(1)

    assert result == 420
    randint.assert_called_once_with(-80, 80)


def test_generate_delta_p_clamps_to_zero(monkeypatch):
    simulator.last_delta_p[1] = 10
    monkeypatch.setattr(
        simulator.random,
        "randint",
        Mock(return_value=-80),
    )

    assert simulator.generate_delta_p(1) == 0


def test_generate_delta_p_clamps_to_2500(monkeypatch):
    simulator.last_delta_p[1] = 2490
    monkeypatch.setattr(
        simulator.random,
        "randint",
        Mock(return_value=80),
    )

    assert simulator.generate_delta_p(1) == 2500


def test_generate_current_samples_creates_one_sample_per_filter(monkeypatch):
    filters = [
        Filter(name="F1", filter_id=1),
        Filter(name="F2", filter_id=2),
    ]

    monkeypatch.setattr(
        simulator,
        "generate_delta_p",
        Mock(side_effect=[111, 222]),
    )

    monkeypatch.setattr(
        simulator.random,
        "choice",
        Mock(side_effect=[True, False, False, True]),
    )

    samples = simulator.generate_current_samples(filters)

    assert [sample.filter_id for sample in samples] == [1, 2]
    assert [sample.delta_p for sample in samples] == [111, 222]

    assert samples[0].status is True
    assert samples[0].alarm_active is False

    assert samples[1].status is False
    assert samples[1].alarm_active is True

    assert samples[0].timestamp == samples[1].timestamp
    assert samples[0].timestamp.microsecond == 0
