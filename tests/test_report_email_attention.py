from datetime import date

from filters_reporting.reporting.email_reporting import (
    create_report_email,
)
from filters_reporting.reporting.filter_attention import (
    FilterAttention,
)


def test_report_email_contains_dirty_filter_summary():
    msg = create_report_email(
        date(
            2026,
            9,
            23,
        ),
        "sender@example.com",
        ["receiver@example.com"],
        [
            FilterAttention(
                filter_name="Esta_01",
                average_delta_p=2143.4,
                dirty_percent=107.17,
            )
        ],
    )

    body = msg.get_content()

    assert "WYMAGA UWAGI" in body

    assert "Esta_01 — zabrudzenie 107%" in body

    assert "Średnie ΔP: 2143 Pa" in body


def test_report_email_says_no_attention_when_list_is_empty():
    msg = create_report_email(
        date(
            2026,
            9,
            23,
        ),
        "sender@example.com",
        ["receiver@example.com"],
        [],
    )

    assert "Wymaga uwagi: brak" in msg.get_content()
