from datetime import date

import filters_reporting.reporting.text_report as text_report
from filters_reporting.models.filter_report_models import DailyFilterStats
from filters_reporting.reporting.text_report import save_report_to_txt


def test_save_report_to_txt_saves_file_and_returns_path(monkeypatch, tmp_path):
    chosen_day = date.today()

    test_reports_dir = tmp_path / "reports"

    monkeypatch.setattr(
        text_report,
        "REPORTS_DIR",
        test_reports_dir,
    )

    expected_path = test_reports_dir / f"Raport_filtry_{chosen_day}.txt"

    result = save_report_to_txt(
        "TEST REPORT",
        chosen_day,
    )

    assert result.resolve() == expected_path.resolve()
    assert expected_path.is_file()
    assert expected_path.read_text(encoding="utf-8") == "TEST REPORT"


def test_build_filter_statistics_report_includes_percentages_and_threshold_exceeded():
    stats = [
        DailyFilterStats(
            filter_name="F1",
            min_delta_p=100,
            max_delta_p=2200,
            avg_delta_p=1200.4,
            sample_count=10,
            alarm_count=2,
            status_count=7,
            delta_p_threshold=2000,
        )
    ]

    report = text_report.build_filter_statistics_report(stats)

    assert "Filtr: F1" in report
    assert "Minimum ΔP: 100 Pa" in report
    assert "Maximum ΔP: 2200 Pa" in report
    assert "Średnia ΔP: 1200 Pa" in report
    assert "Próg ΔP: 2000 Pa" in report
    assert "Liczba próbek: 10" in report
    assert "Liczba alarmów: 2" in report

    assert "Alarm był aktywny w 20.0% próbek" in report

    assert "Liczba próbek podczas pracy filtra: 7" in report

    assert "Filtr pracował w 70.0% próbek" in report

    assert "Próg ΔP został przekroczony: TAK" in report


def test_build_filter_statistics_report_handles_threshold_not_exceeded():
    stats = [
        DailyFilterStats(
            filter_name="F1",
            min_delta_p=100,
            max_delta_p=1500,
            avg_delta_p=800,
            sample_count=4,
            alarm_count=0,
            status_count=1,
            delta_p_threshold=2000,
        )
    ]

    report = text_report.build_filter_statistics_report(stats)

    assert "Próg ΔP został przekroczony: NIE" in report


def test_build_filter_statistics_report_handles_zero_samples():
    stats = [
        DailyFilterStats(
            filter_name="F1",
            min_delta_p=0,
            max_delta_p=0,
            avg_delta_p=0,
            sample_count=0,
            alarm_count=0,
            status_count=0,
        )
    ]

    report = text_report.build_filter_statistics_report(stats)

    assert "Brak próbek" in report

    assert "Alarm był aktywny" not in report

    assert "Filtr pracował" not in report


def test_build_filter_statistics_report_handles_multiple_filters():
    stats = [
        DailyFilterStats(
            filter_name="F1",
            min_delta_p=100,
            max_delta_p=200,
            avg_delta_p=150,
            sample_count=2,
            alarm_count=0,
            status_count=2,
            delta_p_threshold=1000,
        ),
        DailyFilterStats(
            filter_name="F2",
            min_delta_p=300,
            max_delta_p=2500,
            avg_delta_p=1400,
            sample_count=4,
            alarm_count=1,
            status_count=3,
            delta_p_threshold=2000,
        ),
    ]

    report = text_report.build_filter_statistics_report(stats)

    assert "Filtr: F1" in report
    assert "Filtr: F2" in report

    assert "\n\n" in report


def test_build_filter_statistics_report_returns_empty_string_for_empty_stats():
    report = text_report.build_filter_statistics_report([])

    assert report == ""
