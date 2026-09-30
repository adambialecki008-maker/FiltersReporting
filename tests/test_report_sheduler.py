from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

from filters_reporting.scheduling.report_scheduler import (
    ReportScheduler,
)
from filters_reporting.settings_service import (
    AppSettings,
)


def make_settings(
    tmp_path,
    **overrides,
):
    data = dict(
        reports_dir=(tmp_path / "reports"),
        smtp_host="smtp.example.com",
        smtp_port=465,
        username="user@example.com",
        sender="sender@example.com",
        recipients=["a@example.com"],
        auto_report_enabled=True,
        auto_report_time="06:00",
        auto_report_send_email=False,
    )

    data.update(overrides)

    return AppSettings(**data)


def make_scheduler(
    tmp_path,
    settings,
    repository=None,
    **kwargs,
):
    repository = repository or Mock()

    scheduler = ReportScheduler(
        repository,
        settings_loader=(lambda: settings),
        state_file=(tmp_path / "auto_report_state.json"),
        **kwargs,
    )

    return (
        scheduler,
        repository,
    )


def test_disabled_scheduler_does_nothing(
    tmp_path,
):
    settings = make_settings(
        tmp_path,
        auto_report_enabled=False,
    )

    generator = Mock()

    scheduler, _ = make_scheduler(
        tmp_path,
        settings,
        report_generator=generator,
    )

    result = scheduler.check(
        datetime(
            2026,
            9,
            24,
            7,
            0,
        )
    )

    assert result is None

    generator.assert_not_called()


def test_scheduler_waits_until_configured_time(
    tmp_path,
):
    settings = make_settings(
        tmp_path,
        auto_report_time="06:00",
    )

    generator = Mock()

    scheduler, _ = make_scheduler(
        tmp_path,
        settings,
        report_generator=generator,
    )

    result = scheduler.check(
        datetime(
            2026,
            9,
            24,
            5,
            59,
        )
    )

    assert result is None

    generator.assert_not_called()


def test_scheduler_generates_previous_day_report_once(
    tmp_path,
):
    settings = make_settings(tmp_path)

    repository = Mock()

    generator = Mock(
        return_value=(
            Path("a.xlsx"),
            Path("a.txt"),
        )
    )

    mover = Mock(
        return_value=(
            tmp_path / "a.xlsx",
            tmp_path / "a.txt",
        )
    )

    sender = Mock()

    scheduler, _ = make_scheduler(
        tmp_path,
        settings,
        repository=repository,
        report_generator=generator,
        report_mover=mover,
        report_sender=sender,
    )

    first = scheduler.check(
        datetime(
            2026,
            9,
            24,
            6,
            0,
        )
    )

    second = scheduler.check(
        datetime(
            2026,
            9,
            24,
            12,
            0,
        )
    )

    assert first == "generated"

    assert second is None

    generator.assert_called_once_with(
        repository,
        "2026-09-23",
    )

    mover.assert_called_once_with(
        Path("a.xlsx"),
        Path("a.txt"),
        settings.reports_dir,
    )

    sender.assert_not_called()

    repository.add_event.assert_called_once_with(
        "auto_report_generated",
        ("Automatycznie wygenerowano " "raport za 2026-09-23"),
    )


def test_scheduler_can_generate_and_send_report(
    tmp_path,
):
    settings = make_settings(
        tmp_path,
        auto_report_send_email=True,
    )

    repository = Mock()

    generator = Mock(
        return_value=(
            Path("a.xlsx"),
            Path("a.txt"),
        )
    )

    moved_excel = tmp_path / "reports" / "a.xlsx"

    moved_txt = tmp_path / "reports" / "a.txt"

    mover = Mock(
        return_value=(
            moved_excel,
            moved_txt,
        )
    )

    sender = Mock()

    scheduler, _ = make_scheduler(
        tmp_path,
        settings,
        repository=repository,
        report_generator=generator,
        report_mover=mover,
        report_sender=sender,
    )

    result = scheduler.check(
        datetime(
            2026,
            9,
            24,
            6,
            30,
        )
    )

    assert result == "sent"

    sender.assert_called_once()

    call = sender.call_args.kwargs

    assert call["excel_path"] == moved_excel

    assert call["txt_path"] == moved_txt

    assert call["chosen_day"] == "2026-09-23"

    assert call["email_config"].sender == settings.sender

    repository.add_event.assert_called_once_with(
        "auto_report_sent",
        ("Automatycznie wygenerowano " "i wysłano raport " "za 2026-09-23"),
    )


def test_no_data_is_recorded_and_not_retried_same_day(
    tmp_path,
):
    settings = make_settings(tmp_path)

    repository = Mock()

    generator = Mock(return_value=False)

    scheduler, _ = make_scheduler(
        tmp_path,
        settings,
        repository=repository,
        report_generator=generator,
    )

    first = scheduler.check(
        datetime(
            2026,
            9,
            24,
            7,
            0,
        )
    )

    second = scheduler.check(
        datetime(
            2026,
            9,
            24,
            8,
            0,
        )
    )

    assert first == "no_data"

    assert second is None

    assert generator.call_count == 1


def test_scheduler_catches_error_and_records_event(
    tmp_path,
):
    settings = make_settings(tmp_path)

    repository = Mock()

    generator = Mock(side_effect=RuntimeError("boom"))

    scheduler, _ = make_scheduler(
        tmp_path,
        settings,
        repository=repository,
        report_generator=generator,
    )

    result = scheduler.check(
        datetime(
            2026,
            9,
            24,
            7,
            0,
        )
    )

    assert result == "error"

    repository.add_event.assert_called_once()

    event_type, message = repository.add_event.call_args.args

    assert event_type == "auto_report_error"

    assert "RuntimeError: boom" in message
