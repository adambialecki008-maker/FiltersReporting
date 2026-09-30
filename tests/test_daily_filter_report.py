from datetime import datetime, date
from pathlib import Path

import pytest
import main
import filters_reporting.reporting.report_service as report_service

from main import daily_filter_report, generate_samples
from filters_reporting.reporting.report_service import generate_reports_for_day
from filters_reporting.models.filter_report_models import (
    DailyFilterReportSample,
    DailyFilterStats,
)
from filters_reporting.database.filters_repository import FiltersRepository

called = {}


def fake_generate_reports_for_day(repository_arg, chosen_day_arg):
    called["repository"] = repository_arg
    called["chosen_day"] = chosen_day_arg


def fake_create_excel_report(stats_arg, samples_arg, chosen_day_arg):
    called["stats"] = stats_arg
    called["samples"] = samples_arg
    called["chosen_day"] = chosen_day_arg
    return Path("report.xlsx")


def fake_create_excel_empty_report(stats, samples, chosen_day):
    return None


def fake_save_report_to_txt(report_arg, chosen_day_arg):
    called["report"] = report_arg
    called["chosen_day"] = chosen_day_arg
    return Path("report.txt")


def fake_build_filter_statistics_report(stats):
    return "TEST REPORT"


def should_not_be_called(*args, **kwargs):
    raise AssertionError("Funkcja nie powinna zostać wywołana")


@pytest.fixture
def create_stats():
    stat_1 = DailyFilterStats(
        filter_name="F1",
        min_delta_p=100,
        max_delta_p=300,
        avg_delta_p=200,
        sample_count=10,
        alarm_count=7,
        status_count=2,
    )

    stat_2 = DailyFilterStats(
        filter_name="F2",
        min_delta_p=400,
        max_delta_p=600,
        avg_delta_p=500,
        sample_count=20,
        alarm_count=4,
        status_count=5,
    )

    stats = [stat_1, stat_2]

    return stat_1, stat_2, stats


def test_generate_reports_for_day_generates_excel_when_samples_exist(
    monkeypatch,
    tmp_path,
    create_stats,
):
    called.clear()

    chosen_day = date.today()
    _, _, stats = create_stats

    sample_1 = DailyFilterReportSample(
        sample_id=1,
        filter_name="F1",
        filter_id=1,
        delta_p=500.0,
        alarm_active=True,
        status=False,
        timestamp=datetime.now(),
    )

    samples = [sample_1]

    test_database = tmp_path / "test.db"
    repository = FiltersRepository(test_database)

    monkeypatch.setattr(
        repository,
        "get_daily_filter_stats",
        lambda chosen_day: stats,
    )

    monkeypatch.setattr(
        repository,
        "get_daily_samples_for_report",
        lambda chosen_day: samples,
    )

    monkeypatch.setattr(
        report_service,
        "create_excel_report",
        fake_create_excel_report,
    )

    monkeypatch.setattr(
        report_service,
        "build_filter_statistics_report",
        fake_build_filter_statistics_report,
    )

    monkeypatch.setattr(
        report_service,
        "save_report_to_txt",
        fake_save_report_to_txt,
    )

    generate_reports_for_day(repository, chosen_day)

    assert called["stats"] == stats
    assert called["samples"] == samples
    assert called["chosen_day"] == chosen_day


def test_generate_reports_for_day_generates_txt_when_samples_exist(
    monkeypatch,
    tmp_path,
    create_stats,
):
    called.clear()

    chosen_day = date.today()
    _, _, stats = create_stats

    sample_1 = DailyFilterReportSample(
        sample_id=1,
        filter_name="F1",
        filter_id=1,
        delta_p=500.0,
        alarm_active=True,
        status=False,
        timestamp=datetime.now(),
    )

    samples = [sample_1]

    test_database = tmp_path / "test.db"
    repository = FiltersRepository(test_database)

    monkeypatch.setattr(
        repository,
        "get_daily_filter_stats",
        lambda chosen_day: stats,
    )

    monkeypatch.setattr(
        repository,
        "get_daily_samples_for_report",
        lambda chosen_day: samples,
    )

    monkeypatch.setattr(
        report_service,
        "create_excel_report",
        fake_create_excel_empty_report,
    )

    monkeypatch.setattr(
        report_service,
        "build_filter_statistics_report",
        fake_build_filter_statistics_report,
    )

    monkeypatch.setattr(
        report_service,
        "save_report_to_txt",
        fake_save_report_to_txt,
    )

    generate_reports_for_day(repository, chosen_day)

    assert called["report"] == "TEST REPORT"
    assert called["chosen_day"] == chosen_day


def test_daily_filter_report_returns_when_date_is_none(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        main,
        "get_date_from_user",
        lambda: None,
    )

    test_database = tmp_path / "test.db"
    repository = FiltersRepository(test_database)

    monkeypatch.setattr(
        main,
        "generate_reports_for_day",
        should_not_be_called,
    )

    daily_filter_report(repository)


def test_generate_reports_for_day_returns_when_no_samples(
    monkeypatch,
    tmp_path,
):
    called.clear()

    chosen_day = date.today()
    samples = []

    test_database = tmp_path / "test.db"
    repository = FiltersRepository(test_database)

    monkeypatch.setattr(
        repository,
        "get_daily_filter_stats",
        lambda chosen_day: [],
    )

    monkeypatch.setattr(
        repository,
        "get_daily_samples_for_report",
        lambda chosen_day: samples,
    )

    monkeypatch.setattr(
        report_service,
        "create_excel_report",
        should_not_be_called,
    )

    monkeypatch.setattr(
        report_service,
        "build_filter_statistics_report",
        should_not_be_called,
    )

    monkeypatch.setattr(
        report_service,
        "save_report_to_txt",
        should_not_be_called,
    )

    result = generate_reports_for_day(repository, chosen_day)

    assert result is False


def test_daily_report_generates_report(
    monkeypatch,
    tmp_path,
):
    called.clear()

    chosen_day = date.today()

    test_database = tmp_path / "test.db"
    repository = FiltersRepository(test_database)

    monkeypatch.setattr(
        main,
        "get_date_from_user",
        lambda: chosen_day,
    )

    monkeypatch.setattr(
        main,
        "generate_reports_for_day",
        fake_generate_reports_for_day,
    )

    daily_filter_report(repository)

    assert called["repository"] is repository
    assert called["chosen_day"] == chosen_day


def test_generate_reports_for_a_day_returns_excel_and_txt_path(
    monkeypatch,
    tmp_path,
    create_stats,
):
    called.clear()

    chosen_day = date.today()
    _, _, stats = create_stats

    sample_1 = DailyFilterReportSample(
        sample_id=1,
        filter_name="F1",
        filter_id=1,
        delta_p=500.0,
        alarm_active=True,
        status=False,
        timestamp=datetime.now(),
    )

    samples = [sample_1]

    test_database = tmp_path / "test.db"
    repository = FiltersRepository(test_database)

    monkeypatch.setattr(
        repository,
        "get_daily_filter_stats",
        lambda chosen_day: stats,
    )

    monkeypatch.setattr(
        repository,
        "get_daily_samples_for_report",
        lambda chosen_day: samples,
    )

    monkeypatch.setattr(
        report_service,
        "create_excel_report",
        fake_create_excel_report,
    )

    monkeypatch.setattr(
        report_service,
        "build_filter_statistics_report",
        fake_build_filter_statistics_report,
    )

    monkeypatch.setattr(
        report_service,
        "save_report_to_txt",
        fake_save_report_to_txt,
    )

    excel_path = Path("report.xlsx")
    txt_path = Path("report.txt")

    result = generate_reports_for_day(repository, chosen_day)

    assert result == (excel_path, txt_path)


def test_generate_samples_returns_when_no_active_filters():
    class FakeRepository:
        def get_active_filters(self):
            return []

        def save_filter_sample(self, sample):
            raise AssertionError("Próbka nie powinna zostać zapisana")

    repository = FakeRepository()

    generate_samples(repository)


def test_generate_and_send_reports_does_not_send_when_no_data(monkeypatch):
    repository = object()
    chosen_day = date(2026, 9, 18)

    monkeypatch.setattr(
        main,
        "get_date_from_user",
        lambda: chosen_day,
    )

    monkeypatch.setattr(
        main,
        "send_reports_for_day",
        lambda *args, **kwargs: None,
    )

    main.generate_and_send_reports_for_day(repository)
