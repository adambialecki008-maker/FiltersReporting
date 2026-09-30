from filters_reporting.database.filters_repository import FiltersRepository, Filter
from filters_reporting.models.filter_sample import FilterSample
from datetime import datetime, date, timedelta
import pytest
from filters_reporting.models.filter_report_models import DailyFilterStats


@pytest.fixture
def repository(tmp_path):
    test_database = tmp_path / "test.db"
    repository = FiltersRepository(test_database)
    repository.create_table()
    return repository


@pytest.fixture
def prepared_filters(repository):
    filter_1 = Filter(
        name="F1",
        opc_url="opc.tcp://localhost:4841/filters/",
    )

    filter_2 = Filter(
        name="F2",
        opc_url="opc.tcp://localhost:4842/filters/",
    )

    repository.save_filter(filter_1)
    repository.save_filter(filter_2)

    return filter_1, filter_2


@pytest.fixture
def expected_daily_stats(prepared_filters):
    filter_1, filter_2 = prepared_filters
    expected_f1 = DailyFilterStats(
        filter_name=filter_1.name,
        min_delta_p=100,
        max_delta_p=200,
        avg_delta_p=150,
        sample_count=2,
        alarm_count=0,
        status_count=2,
    )
    expected_f2 = DailyFilterStats(
        filter_name=filter_2.name,
        min_delta_p=300,
        max_delta_p=500,
        avg_delta_p=400,
        sample_count=2,
        alarm_count=0,
        status_count=2,
    )
    return expected_f1, expected_f2


def test_save_filter_saves_filter_to_database(repository):
    filter_obj = Filter(
        name="F1",
        opc_url="opc.tcp://localhost:4841/filters/",
        delta_p_threshold=420,
    )

    repository.save_filter(filter_obj)

    result = repository.get_filter_by_name(filter_obj.name)

    assert result.name == filter_obj.name
    assert result.filter_id == filter_obj.filter_id
    assert result.filter_id is not None
    assert result.opc_url == filter_obj.opc_url
    assert result.delta_p_threshold == 420


def test_get_all_filters_returns_all_with_correct_id(repository, prepared_filters):
    filter_1, filter_2 = prepared_filters

    result = repository.get_all_filters()

    assert len(result) == 2
    assert result[0].filter_id == filter_1.filter_id
    assert result[1].filter_id == filter_2.filter_id


def test_get_filter_by_name_returns_none_when_filter_does_not_exist(repository):
    assert repository.get_filter_by_name("F1") is None


def test_update_filters_activity(repository, prepared_filters):
    filter_1, filter_2 = prepared_filters

    repository.update_filter_activity(filter_1.name, False)
    result_false = repository.get_filter_by_name(filter_1.name)

    repository.update_filter_activity(filter_1.name, True)
    result_true = repository.get_filter_by_name(filter_1.name)

    assert result_false.active is False
    assert result_true.active is True


def test_get_active_filters_returns_only_active_filters(
    repository,
    prepared_filters,
):
    filter_1, filter_2 = prepared_filters

    repository.update_filter_activity(filter_2.name, False)

    result = repository.get_active_filters()

    assert len(result) == 1
    assert result[0].name == filter_1.name


def test_save_filter_sample_saves_sample_to_database(
    repository,
    prepared_filters,
):
    filter_1, filter_2 = prepared_filters

    sample = FilterSample(
        filter_id=filter_1.filter_id,
        delta_p=10,
        status=True,
        alarm_active=False,
        timestamp=datetime.now(),
    )

    repository.save_filter_sample(sample)

    result = repository.get_filter_samples_by_filter_id(
        filter_1.filter_id,
        date.today().isoformat(),
    )

    assert len(result) == 1

    saved_sample = result[0]

    assert saved_sample[0] == filter_1.name
    assert saved_sample[1] == sample.delta_p
    assert saved_sample[2] == sample.timestamp.isoformat()


def test_get_filter_samples_by_filter_id_returns_only_samples_for_chosen_filter(
    repository,
    prepared_filters,
):
    filter_1, filter_2 = prepared_filters

    sample_1 = FilterSample(
        filter_id=filter_1.filter_id,
        delta_p=100,
        status=True,
        alarm_active=False,
        timestamp=datetime.now(),
    )

    sample_2 = FilterSample(
        filter_id=filter_2.filter_id,
        delta_p=200,
        status=True,
        alarm_active=False,
        timestamp=datetime.now(),
    )

    repository.save_filter_sample(sample_1)
    repository.save_filter_sample(sample_2)

    result = repository.get_filter_samples_by_filter_id(
        filter_1.filter_id,
        date.today().isoformat(),
    )

    assert len(result) == 1

    saved_sample = result[0]

    assert saved_sample[0] == filter_1.name
    assert saved_sample[1] == sample_1.delta_p
    assert saved_sample[2] == sample_1.timestamp.isoformat()


def test_get_delta_p_stats_by_filter_id_returns_correct_stats(
    repository,
    prepared_filters,
):
    filter_1, filter_2 = prepared_filters

    sample_1 = FilterSample(
        filter_id=filter_1.filter_id,
        delta_p=100,
        status=True,
        alarm_active=True,
        timestamp=datetime.now(),
    )

    sample_2 = FilterSample(
        filter_id=filter_1.filter_id,
        delta_p=200,
        status=True,
        alarm_active=False,
        timestamp=datetime.now(),
    )

    sample_3 = FilterSample(
        filter_id=filter_1.filter_id,
        delta_p=300,
        status=False,
        alarm_active=False,
        timestamp=datetime.now(),
    )

    repository.save_filter_sample(sample_1)
    repository.save_filter_sample(sample_2)
    repository.save_filter_sample(sample_3)

    result = repository.get_delta_p_stats_by_filter_id(
        filter_1.filter_id,
        date.today().isoformat(),
    )

    expected_min = 100
    expected_max = 300
    expected_avg = 200
    expected_count = 3
    expected_alarms_count = 1
    expected_status_count = 2

    assert result[0] == expected_min
    assert result[1] == expected_max
    assert result[2] == expected_avg
    assert result[3] == expected_count
    assert result[4] == expected_alarms_count
    assert result[5] == expected_status_count


def test_get_daily_filter_stats_returns_stats_for_each_filter(
    repository,
    prepared_filters,
    expected_daily_stats,
):
    filter_1, filter_2 = prepared_filters

    sample_f1_1 = FilterSample(
        filter_id=filter_1.filter_id,
        delta_p=100,
        status=True,
        alarm_active=False,
        timestamp=datetime.now(),
    )

    sample_f1_2 = FilterSample(
        filter_id=filter_1.filter_id,
        delta_p=200,
        status=True,
        alarm_active=False,
        timestamp=datetime.now(),
    )

    sample_f2_1 = FilterSample(
        filter_id=filter_2.filter_id,
        delta_p=300,
        status=True,
        alarm_active=False,
        timestamp=datetime.now(),
    )

    sample_f2_2 = FilterSample(
        filter_id=filter_2.filter_id,
        delta_p=500,
        status=True,
        alarm_active=False,
        timestamp=datetime.now(),
    )
    expected_f1, expected_f2 = expected_daily_stats
    repository.save_filter_sample(sample_f1_1)
    repository.save_filter_sample(sample_f1_2)
    repository.save_filter_sample(sample_f2_1)
    repository.save_filter_sample(sample_f2_2)

    result = repository.get_daily_filter_stats(date.today().isoformat())

    assert len(result) == 2

    assert result[0] == expected_f1
    assert result[1] == expected_f2


def test_get_daily_samples_for_report_returns_all_daily_samples_in_order(
    repository,
    prepared_filters,
):
    filter_1, filter_2 = prepared_filters

    sample_f1_1 = FilterSample(
        filter_id=filter_1.filter_id,
        delta_p=100,
        status=True,
        alarm_active=False,
        timestamp=datetime.now(),
    )

    sample_f1_2 = FilterSample(
        filter_id=filter_1.filter_id,
        delta_p=200,
        status=True,
        alarm_active=False,
        timestamp=datetime.now(),
    )

    sample_f2_1 = FilterSample(
        filter_id=filter_2.filter_id,
        delta_p=300,
        status=True,
        alarm_active=False,
        timestamp=datetime.now(),
    )

    sample_f2_2 = FilterSample(
        filter_id=filter_2.filter_id,
        delta_p=500,
        status=True,
        alarm_active=False,
        timestamp=datetime.now(),
    )

    repository.save_filter_sample(sample_f1_1)
    repository.save_filter_sample(sample_f1_2)
    repository.save_filter_sample(sample_f2_1)
    repository.save_filter_sample(sample_f2_2)

    result = repository.get_daily_samples_for_report(date.today().isoformat())
    assert len(result) == 4

    sample_1 = result[0]
    sample_2 = result[1]
    sample_3 = result[2]
    sample_4 = result[3]

    assert sample_1.filter_name == filter_1.name
    assert sample_1.delta_p == sample_f1_1.delta_p

    assert sample_2.filter_name == filter_1.name
    assert sample_2.delta_p == sample_f1_2.delta_p

    assert sample_3.filter_name == filter_2.name
    assert sample_3.delta_p == sample_f2_1.delta_p

    assert sample_4.filter_name == filter_2.name
    assert sample_4.delta_p == sample_f2_2.delta_p


def test_delete_samples_for_day_deletes_only_samples_from_chosen_day(
    repository,
    prepared_filters,
):
    filter_1, filter_2 = prepared_filters

    today = datetime.now()
    yesterday = today - timedelta(days=1)

    sample_1 = FilterSample(
        filter_id=filter_1.filter_id,
        delta_p=100,
        status=True,
        alarm_active=False,
        timestamp=today,
    )

    sample_2 = FilterSample(
        filter_id=filter_1.filter_id,
        delta_p=200,
        status=True,
        alarm_active=False,
        timestamp=today,
    )

    sample_old = FilterSample(
        filter_id=filter_1.filter_id,
        delta_p=300,
        status=True,
        alarm_active=False,
        timestamp=yesterday,
    )

    repository.save_filter_sample(sample_1)
    repository.save_filter_sample(sample_2)
    repository.save_filter_sample(sample_old)

    deleted_count = repository.delete_samples_for_day(today.date().isoformat())

    today_result = repository.get_daily_samples_for_report(today.date().isoformat())

    old_result = repository.get_daily_samples_for_report(yesterday.date().isoformat())

    assert deleted_count == 2
    assert len(today_result) == 0
    assert len(old_result) == 1

    old_sample = old_result[0]

    assert old_sample.filter_name == filter_1.name
    assert old_sample.delta_p == sample_old.delta_p


def test_get_filter_by_opc_url_returns_correct_filter(
    repository,
    prepared_filters,
):
    filter_1, filter_2 = prepared_filters

    result = repository.get_filter_by_opc_url(filter_2.opc_url)

    assert result.name == filter_2.name
    assert result.filter_id == filter_2.filter_id
    assert result.opc_url == filter_2.opc_url


def test_update_filter_opc_url_changes_url(
    repository,
    prepared_filters,
):
    filter_1, filter_2 = prepared_filters

    new_url = "opc.tcp://localhost:4843/filters/"

    repository.update_filter_opc_url(
        filter_1.name,
        new_url,
    )

    result = repository.get_filter_by_opc_url(new_url)

    assert result.name == filter_1.name
    assert result.opc_url == new_url


def test_update_filter_opc_url_does_not_change_url_when_url_already_exists(
    repository,
    prepared_filters,
):
    filter_1, filter_2 = prepared_filters

    repository.update_filter_opc_url(
        filter_1.name,
        filter_2.opc_url,
    )

    result_f1 = repository.get_filter_by_name(filter_1.name)
    result_f2 = repository.get_filter_by_name(filter_2.name)

    assert result_f1.name == filter_1.name
    assert result_f1.opc_url == filter_1.opc_url

    assert result_f2.name == filter_2.name
    assert result_f2.opc_url == filter_2.opc_url


def test_get_filter_by_opc_url_returns_none_if_url_doesnt_exist(
    repository,
    prepared_filters,
):
    result = repository.get_filter_by_opc_url("opc.tcp://localhost:4843/filters/")

    assert result is None


def test_get_latest_active_filter_sample_gets_last_sample(repository):
    filter_1 = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4841/filters/",
    )
    repository_obj = repository
    repository_obj.save_filter(filter_1)
    sample_1 = FilterSample(
        filter_id=1,
        delta_p=500,
        status=True,
        alarm_active=False,
        timestamp=datetime(
            2026,
            9,
            19,
            7,
            24,
        ),
    )

    sample_2 = FilterSample(
        filter_id=1,
        delta_p=700,
        status=False,
        alarm_active=True,
        timestamp=datetime(
            2026,
            9,
            19,
            7,
            26,
        ),
    )
    repository_obj.save_filter_sample(sample_1)
    repository_obj.save_filter_sample(sample_2)
    result = repository_obj.get_latest_active_filter_samples()

    assert len(result) == 1
    assert result[0]["delta_p"] == sample_2.delta_p
    assert result[0]["timestamp"] == sample_2.timestamp
    assert result[0]["filter_name"] == filter_1.name


def test_gets_last_active_filter_samples_returns_filter_if_no_samples(tmp_path):
    filter_obj = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4841/filters/",
    )

    test_database = tmp_path / "test.db"
    repository = FiltersRepository(test_database)
    repository.create_table()
    repository.save_filter(filter_obj)
    result = repository.get_latest_active_filter_samples()
    assert len(result) == 1
    assert result[0]["filter_name"] == filter_obj.name
    assert result[0]["alarm_active"] is None
    assert result[0]["delta_p"] is None
    assert result[0]["status"] is None
    assert result[0]["timestamp"] is None


def test_get_last_active_filter_samples_returns_empty_if_filter_not_active(tmp_path):
    filter_obj = Filter(
        name="F1",
        filter_id=1,
        opc_url="opc.tcp://localhost:4841/filters/",
        active=False,
    )
    test_database = tmp_path / "test,db"
    repository = FiltersRepository(test_database)
    repository.create_table()
    repository.save_filter(filter_obj)
    result = repository.get_latest_active_filter_samples()
    assert result == []


def test_get_latest_active_filter_samples_returns_last_working_delta_p(
    repository,
    prepared_filters,
):
    filter_1, _ = prepared_filters

    now = datetime.now()

    working_sample = FilterSample(
        filter_id=filter_1.filter_id,
        delta_p=2300,
        status=True,
        alarm_active=False,
        timestamp=now - timedelta(minutes=1),
    )

    stopped_sample = FilterSample(
        filter_id=filter_1.filter_id,
        delta_p=100,
        status=False,
        alarm_active=False,
        timestamp=now,
    )

    repository.save_filter_sample(working_sample)
    repository.save_filter_sample(stopped_sample)

    result = repository.get_latest_active_filter_samples()

    filter_data = next(
        item for item in result if item["filter_id"] == filter_1.filter_id
    )

    assert filter_data["delta_p"] == 100
    assert filter_data["status"] is False

    assert filter_data["last_working_delta_p"] == 2300
    assert filter_data["last_working_timestamp"] == working_sample.timestamp


def test_get_latest_active_filter_samples_returns_none_when_filter_never_worked(
    repository,
    prepared_filters,
):
    filter_1, _ = prepared_filters

    stopped_sample = FilterSample(
        filter_id=filter_1.filter_id,
        delta_p=150,
        status=False,
        alarm_active=False,
        timestamp=datetime.now(),
    )

    repository.save_filter_sample(stopped_sample)

    result = repository.get_latest_active_filter_samples()

    filter_data = next(
        item for item in result if item["filter_id"] == filter_1.filter_id
    )

    assert filter_data["status"] is False
    assert filter_data["delta_p"] == 150
    assert filter_data["last_working_delta_p"] is None
    assert filter_data["last_working_timestamp"] is None


def test_get_connection_counts_returns_zero_connected_when_no_status_saved(
    repository,
    prepared_filters,
):
    active_count, connected_count = repository.get_connection_counts()

    assert active_count == 2
    assert connected_count == 0


def test_get_connection_counts_returns_connected_filter(
    repository,
    prepared_filters,
):
    filter_1, filter_2 = prepared_filters

    repository.set_filter_connection_status(
        filter_1.filter_id,
        True,
    )

    active_count, connected_count = repository.get_connection_counts()

    assert active_count == 2
    assert connected_count == 1


def test_set_filter_connection_status_updates_existing_status(
    repository,
    prepared_filters,
):
    filter_1, filter_2 = prepared_filters

    repository.set_filter_connection_status(
        filter_1.filter_id,
        True,
    )

    repository.set_filter_connection_status(
        filter_1.filter_id,
        False,
    )

    active_count, connected_count = repository.get_connection_counts()

    assert active_count == 2
    assert connected_count == 0


def test_get_connection_counts_ignores_inactive_filters(
    repository,
    prepared_filters,
):
    filter_1, filter_2 = prepared_filters

    repository.set_filter_connection_status(
        filter_1.filter_id,
        True,
    )

    repository.set_filter_connection_status(
        filter_2.filter_id,
        True,
    )

    repository.update_filter_activity(
        filter_2.name,
        False,
    )

    active_count, connected_count = repository.get_connection_counts()

    assert active_count == 1
    assert connected_count == 1


def test_set_collector_heartbeat_saves_timestamp(
    repository,
):
    timestamp = datetime.now()

    repository.set_collector_heartbeat(timestamp)

    result = repository.get_collector_heartbeat()

    assert result == timestamp


def test_set_collector_heartbeat_updates_existing_timestamp(
    repository,
):
    old_timestamp = datetime.now() - timedelta(minutes=5)

    new_timestamp = datetime.now()

    repository.set_collector_heartbeat(old_timestamp)

    repository.set_collector_heartbeat(new_timestamp)

    result = repository.get_collector_heartbeat()

    assert result == new_timestamp


def test_get_collector_heartbeat_returns_none_when_not_saved(
    repository,
):
    result = repository.get_collector_heartbeat()

    assert result is None


def test_request_collector_stop_sets_stop_requested(
    repository,
):
    repository.request_collector_stop()
    assert repository.is_collector_stop_requested() is True


def test_clear_collector_stop_request_resets_stop_requested(
    repository,
):
    repository.request_collector_stop()
    repository.clear_collector_stop_request()
    assert repository.is_collector_stop_requested() is False


def test_add_event_saves_event(
    repository,
):
    timestamp = datetime(
        2026,
        9,
        22,
        18,
        30,
    )
    repository.add_event(
        event_type="report_generated",
        message="Wygenerowano raport",
        timestamp=timestamp,
    )
    events = repository.get_recent_events()
    assert len(events) == 1
    assert events[0] == (
        timestamp,
        "report_generated",
        "Wygenerowano raport",
    )


def test_get_recent_events_returns_newest_first_and_respects_limit(
    repository,
):
    repository.add_event(
        "test",
        "Pierwsze",
        datetime(2026, 9, 22, 18, 0),
    )
    repository.add_event(
        "test",
        "Drugie",
        datetime(2026, 9, 22, 18, 1),
    )
    repository.add_event(
        "test",
        "Trzecie",
        datetime(2026, 9, 22, 18, 2),
    )
    events = repository.get_recent_events(limit=2)
    assert len(events) == 2
    assert events[0][2] == "Trzecie"
    assert events[1][2] == "Drugie"


def test_save_filter_saves_opc_node_ids(
    repository,
):
    filter_obj = Filter(
        name="F1",
        opc_url="opc.tcp://localhost:4840",
        delta_p_node_id="ns=3;s=Filter.DeltaP",
        status_node_id="ns=3;s=Filter.Status",
        alarm_node_id="ns=3;s=Filter.Alarm",
    )
    repository.save_filter(filter_obj)
    result = repository.get_filter_by_name("F1")
    assert result.delta_p_node_id == "ns=3;s=Filter.DeltaP"
    assert result.status_node_id == "ns=3;s=Filter.Status"
    assert result.alarm_node_id == "ns=3;s=Filter.Alarm"


def test_get_all_filters_returns_node_ids(
    repository,
):
    filter_obj = Filter(
        name="F1",
        opc_url="opc.tcp://localhost:4840",
        delta_p_node_id="ns=3;s=Filter.DeltaP",
        status_node_id="ns=3;s=Filter.Status",
        alarm_node_id="ns=3;s=Filter.Alarm",
    )

    repository.save_filter(filter_obj)

    result = repository.get_all_filters()

    assert len(result) == 1
    assert result[0].delta_p_node_id == "ns=3;s=Filter.DeltaP"
    assert result[0].status_node_id == "ns=3;s=Filter.Status"
    assert result[0].alarm_node_id == "ns=3;s=Filter.Alarm"


def test_get_active_filters_returns_node_ids(
    repository,
):
    filter_obj = Filter(
        name="F1",
        opc_url="opc.tcp://localhost:4840",
        delta_p_node_id="ns=3;s=Filter.DeltaP",
        status_node_id="ns=3;s=Filter.Status",
        alarm_node_id="ns=3;s=Filter.Alarm",
    )
    repository.save_filter(filter_obj)
    result = repository.get_active_filters()
    assert len(result) == 1
    assert result[0].delta_p_node_id == "ns=3;s=Filter.DeltaP"
    assert result[0].status_node_id == "ns=3;s=Filter.Status"
    assert result[0].alarm_node_id == "ns=3;s=Filter.Alarm"


def test_update_filter_updates_full_configuration(
    repository,
):
    filter_obj = Filter(
        name="F1",
        opc_url="opc.tcp://localhost:4840",
        delta_p_threshold=2000,
        delta_p_node_id="ns=3;s=OldDeltaP",
        status_node_id="ns=3;s=OldStatus",
        alarm_node_id="ns=3;s=OldAlarm",
    )
    repository.save_filter(filter_obj)
    filter_obj.name = "F1_NEW"
    filter_obj.active = False
    filter_obj.opc_url = "opc.tcp://localhost:4841"
    filter_obj.delta_p_threshold = 2500
    filter_obj.delta_p_node_id = "ns=4;s=NewDeltaP"
    filter_obj.status_node_id = "ns=4;s=NewStatus"
    filter_obj.alarm_node_id = "ns=4;s=NewAlarm"
    repository.update_filter(filter_obj)
    result = repository.get_filter_by_name("F1_NEW")
    assert result.filter_id == filter_obj.filter_id
    assert result.active is False
    assert result.opc_url == "opc.tcp://localhost:4841"
    assert result.delta_p_threshold == 2500
    assert result.delta_p_node_id == "ns=4;s=NewDeltaP"
    assert result.status_node_id == "ns=4;s=NewStatus"
    assert result.alarm_node_id == "ns=4;s=NewAlarm"


def test_connect_creates_database_parent_directory(
    tmp_path,
):
    database_path = tmp_path / "data" / "filters.db"

    repository = FiltersRepository(database_path)

    connection = repository.connect()
    connection.close()

    assert database_path.parent.is_dir()
    assert database_path.is_file()
