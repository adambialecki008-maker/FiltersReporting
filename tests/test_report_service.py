from datetime import date
from pathlib import Path
from unittest.mock import Mock

import filters_reporting.reporting.report_service as report_service


def test_generate_reports_for_day_returns_false_when_stats_missing():
    repository = Mock()
    repository.get_daily_filter_stats.return_value = []
    repository.get_daily_samples_for_report.return_value = [object()]

    assert (
        report_service.generate_reports_for_day(
            repository,
            date.today(),
        )
        is False
    )


def test_generate_reports_for_day_returns_false_when_samples_missing():
    repository = Mock()
    repository.get_daily_filter_stats.return_value = [object()]
    repository.get_daily_samples_for_report.return_value = []

    assert (
        report_service.generate_reports_for_day(
            repository,
            date.today(),
        )
        is False
    )


def test_generate_reports_for_day_returns_false_when_output_creation_fails(
    monkeypatch,
):
    repository = Mock()

    stats = [object()]
    samples = [object()]

    repository.get_daily_filter_stats.return_value = stats
    repository.get_daily_samples_for_report.return_value = samples

    monkeypatch.setattr(
        report_service,
        "build_filter_statistics_report",
        Mock(return_value="report"),
    )

    monkeypatch.setattr(
        report_service,
        "save_report_to_txt",
        Mock(return_value=Path("report.txt")),
    )

    monkeypatch.setattr(
        report_service,
        "create_excel_report",
        Mock(return_value=False),
    )

    assert (
        report_service.generate_reports_for_day(
            repository,
            date.today(),
        )
        is False
    )


def test_generate_reports_for_day_returns_generated_paths(monkeypatch):
    repository = Mock()
    chosen_day = date.today()

    stats = [object()]
    samples = [object()]

    repository.get_daily_filter_stats.return_value = stats
    repository.get_daily_samples_for_report.return_value = samples

    build = Mock(return_value="report")
    save_txt = Mock(return_value=Path("report.txt"))
    create_excel = Mock(return_value=Path("report.xlsx"))

    monkeypatch.setattr(
        report_service,
        "build_filter_statistics_report",
        build,
    )

    monkeypatch.setattr(
        report_service,
        "save_report_to_txt",
        save_txt,
    )

    monkeypatch.setattr(
        report_service,
        "create_excel_report",
        create_excel,
    )

    result = report_service.generate_reports_for_day(
        repository,
        chosen_day,
    )

    assert result == (
        Path("report.xlsx"),
        Path("report.txt"),
    )

    build.assert_called_once_with(stats)

    save_txt.assert_called_once_with(
        "report",
        chosen_day,
    )

    create_excel.assert_called_once_with(
        stats,
        samples,
        chosen_day,
    )


def test_generate_and_send_reports_returns_false_without_generated_reports(
    monkeypatch,
):
    monkeypatch.setattr(
        report_service,
        "generate_reports_for_day",
        Mock(return_value=False),
    )

    send = Mock()

    monkeypatch.setattr(
        report_service,
        "send_generated_report",
        send,
    )

    result = report_service.generate_and_send_reports_for_day(
        Mock(),
        date.today(),
        object(),
    )

    assert result is False
    send.assert_not_called()


def test_generate_and_send_reports_sends_both_files(monkeypatch):
    chosen_day = date.today()
    repository = Mock()
    email_config = object()

    excel_path = Path("report.xlsx")
    txt_path = Path("report.txt")

    monkeypatch.setattr(
        report_service,
        "generate_reports_for_day",
        Mock(
            return_value=(
                excel_path,
                txt_path,
            )
        ),
    )

    send = Mock()

    monkeypatch.setattr(
        report_service,
        "send_generated_report",
        send,
    )

    result = report_service.generate_and_send_reports_for_day(
        repository,
        chosen_day,
        email_config,
    )

    assert result is True

    send.assert_called_once_with(
        excel_path=excel_path,
        txt_path=txt_path,
        chosen_day=chosen_day,
        email_config=email_config,
    )
