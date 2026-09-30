from __future__ import annotations

import json
from datetime import datetime, timedelta, time
from pathlib import Path
from typing import Callable

from filters_reporting.config import DATA_DIR
from filters_reporting.reporting.email_reporting import (
    send_generated_report,
)
from filters_reporting.reporting.filter_attention import (
    build_filter_attention,
)
from filters_reporting.reporting.report_service import (
    generate_reports_for_day,
)
from filters_reporting.settings_service import (
    AppSettings,
    load_settings,
    move_generated_report_files,
)

AUTO_REPORT_STATE_FILE = DATA_DIR / "auto_report_state.json"


class ReportScheduler:
    def __init__(
        self,
        repository,
        *,
        settings_loader: Callable[
            [],
            AppSettings,
        ] = load_settings,
        report_generator=generate_reports_for_day,
        report_mover=move_generated_report_files,
        report_sender=send_generated_report,
        state_file: Path = AUTO_REPORT_STATE_FILE,
        now_provider: Callable[
            [],
            datetime,
        ] = datetime.now,
    ):
        self.repository = repository
        self.settings_loader = settings_loader
        self.report_generator = report_generator
        self.report_mover = report_mover
        self.report_sender = report_sender
        self.state_file = Path(state_file)
        self.now_provider = now_provider

    def check(
        self,
        now: datetime | None = None,
    ) -> str | None:
        settings = self.settings_loader()

        if not settings.auto_report_enabled:
            return None

        current = now or self.now_provider()

        scheduled_time = self._parse_time(settings.auto_report_time)

        if (
            current.time().replace(
                second=0,
                microsecond=0,
            )
            < scheduled_time
        ):
            return None

        today_key = current.date().isoformat()

        state = self._load_state()

        if state.get("last_attempt_date") == today_key:
            return None

        target_day = (current.date() - timedelta(days=1)).isoformat()

        outcome = "error"

        try:
            result = self.report_generator(
                self.repository,
                target_day,
            )

            if not result:
                outcome = "no_data"

                self._add_event(
                    "auto_report_no_data",
                    ("Brak danych do " "automatycznego raportu " f"za {target_day}"),
                )

                return outcome

            (
                excel_path,
                txt_path,
            ) = result

            (
                excel_path,
                txt_path,
            ) = self.report_mover(
                excel_path,
                txt_path,
                settings.reports_dir,
            )

            if settings.auto_report_send_email:
                stats = self.repository.get_daily_filter_stats(target_day)

                samples = self.repository.get_daily_samples_for_report(target_day)

                if not isinstance(
                    stats,
                    list,
                ):
                    stats = []

                if not isinstance(
                    samples,
                    list,
                ):
                    samples = []

                attention_items = build_filter_attention(
                    stats,
                    samples,
                )

                self.report_sender(
                    excel_path=excel_path,
                    txt_path=txt_path,
                    chosen_day=target_day,
                    email_config=(settings.to_email_config()),
                    attention_items=(attention_items),
                )

                outcome = "sent"

                self._add_event(
                    "auto_report_sent",
                    (
                        "Automatycznie "
                        "wygenerowano i wysłano "
                        f"raport za {target_day}"
                    ),
                )

            else:
                outcome = "generated"

                self._add_event(
                    "auto_report_generated",
                    ("Automatycznie " "wygenerowano raport " f"za {target_day}"),
                )

            return outcome

        except Exception as error:
            self._add_event(
                "auto_report_error",
                (
                    "Błąd automatycznego "
                    f"raportu za {target_day}: "
                    f"{type(error).__name__}: "
                    f"{error}"
                ),
            )

            return "error"

        finally:
            self._save_state(
                last_attempt_date=today_key,
                target_day=target_day,
                outcome=outcome,
            )

    @staticmethod
    def _parse_time(
        value: str,
    ) -> time:
        try:
            parsed = time.fromisoformat(value)

        except (
            TypeError,
            ValueError,
        ) as error:
            raise ValueError(
                ("Nieprawidłowa godzina " "automatycznego raportu: " f"{value!r}")
            ) from error

        return parsed.replace(
            second=0,
            microsecond=0,
        )

    def _load_state(
        self,
    ) -> dict:
        if not self.state_file.exists():
            return {}

        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))

        except (
            OSError,
            json.JSONDecodeError,
            TypeError,
        ):
            return {}

        return (
            data
            if isinstance(
                data,
                dict,
            )
            else {}
        )

    def _save_state(
        self,
        *,
        last_attempt_date: str,
        target_day: str,
        outcome: str,
    ) -> None:
        self.state_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        data = {
            "last_attempt_date": (last_attempt_date),
            "target_day": target_day,
            "outcome": outcome,
        }

        self.state_file.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=4,
            ),
            encoding="utf-8",
        )

    def _add_event(
        self,
        event_type: str,
        message: str,
    ) -> None:
        if hasattr(
            self.repository,
            "add_event",
        ):
            self.repository.add_event(
                event_type,
                message,
            )
