from datetime import datetime
from contextlib import closing
import pytest

from filters_reporting.database.filters_repository import (
    FiltersRepository,
)
from filters_reporting.models.filter import Filter
from filters_reporting.models.filter_sample import (
    FilterSample,
)


@pytest.fixture
def repository(tmp_path):
    database_path = tmp_path / "test_filters.db"

    repository = FiltersRepository(database_path)

    repository.create_table()

    return repository


def test_delete_filter_removes_filter_and_related_data(
    repository,
):
    filter_obj = Filter(
        name="DELETE_TEST",
        opc_url="opc.tcp://localhost:4999/",
        delta_p_threshold=2000,
        delta_p_node_id=("ns=2;s=DELETE_TEST.DeltaP"),
        status_node_id=("ns=2;s=DELETE_TEST.Status"),
        alarm_node_id=("ns=2;s=DELETE_TEST.Alarm"),
    )

    repository.save_filter(filter_obj)

    sample = FilterSample(
        filter_id=filter_obj.filter_id,
        delta_p=1234,
        status=True,
        alarm_active=False,
        timestamp=datetime.now(),
    )

    repository.save_filter_sample(sample)

    repository.set_filter_connection_status(
        filter_obj.filter_id,
        True,
    )

    result = repository.delete_filter(filter_obj.filter_id)

    assert result is True

    assert repository.get_filter_by_name("DELETE_TEST") is None

    with closing(repository.connect()) as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM filter_samples
            WHERE filter_id = ?
            """,
            (filter_obj.filter_id,),
        )

        sample_count = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM filter_connection_status
            WHERE filter_id = ?
            """,
            (filter_obj.filter_id,),
        )

        connection_status_count = cursor.fetchone()[0]

    assert sample_count == 0
    assert connection_status_count == 0


def test_delete_filter_returns_false_for_unknown_id(
    repository,
):
    result = repository.delete_filter(999999)

    assert result is False
