from email.message import EmailMessage
from datetime import date
import smtplib
from dataclasses import dataclass
import os
from pathlib import Path

from filters_reporting.smtp_credentials import get_smtp_password


@dataclass
class EmailConfig:
    smtp_host: str
    smtp_port: int
    username: str
    sender: str
    recipients: list[str]


def build_report_email_body(
    chosen_day: date | str,
    attention_items=None,
) -> str:
    lines = [
        f"Raport filtrów na dzień {chosen_day} w załączniku.",
    ]

    if attention_items is None:
        return "\n".join(lines)

    if attention_items:
        lines.extend(
            [
                "",
                "WYMAGA UWAGI",
                "",
            ]
        )

        for item in attention_items:
            lines.append(f"{item.filter_name} — zabrudzenie {item.dirty_percent:.0f}%")
            lines.append(f"Średnie ΔP: {item.average_delta_p:.0f} Pa")
            lines.append("")

        if lines[-1] == "":
            lines.pop()
    else:
        lines.extend(
            [
                "",
                "Wymaga uwagi: brak",
            ]
        )

    return "\n".join(lines)


def create_report_email(
    chosen_day: date | str,
    sender: str,
    recipients: list[str],
    attention_items=None,
):
    msg = EmailMessage()
    msg["Subject"] = f"Raport filtry_{chosen_day}"
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content(
        build_report_email_body(
            chosen_day,
            attention_items,
        )
    )
    return msg


def add_excel_attachment(
    msg,
    attachment_path,
):
    attachment_path = Path(attachment_path)
    attach = attachment_path.read_bytes()
    msg.add_attachment(
        attach,
        maintype="application",
        subtype=("vnd.openxmlformats-officedocument." "spreadsheetml.sheet"),
        filename=attachment_path.name,
    )


def add_text_attachment(
    msg,
    attachment_path,
):
    attachment_path = Path(attachment_path)
    attach = attachment_path.read_bytes()
    msg.add_attachment(
        attach,
        maintype="text",
        subtype="plain",
        filename=attachment_path.name,
    )


def send_email(msg, smtp):
    smtp.send_message(msg)


def create_smtp_client(host, port):
    return smtplib.SMTP_SSL(
        host,
        port,
        timeout=10,
    )


def login_smtp(smtp, username, password):
    smtp.login(username, password)


def send_report_email(msg, email_config):
    password = get_email_password()

    smtp = create_smtp_client(
        email_config.smtp_host,
        email_config.smtp_port,
    )

    login_smtp(
        smtp,
        email_config.username,
        password,
    )

    try:
        send_email(
            msg,
            smtp,
        )

    finally:
        smtp.quit()


def get_email_password():
    password = os.getenv(
        "EMAIL_PASSWORD"
    )

    if password:
        return password

    password = get_smtp_password()

    if password:
        return password

    raise ValueError(
        "Brak hasła SMTP. "
        "Wpisz je w Ustawienia → Ogólne "
        "albo ustaw EMAIL_PASSWORD."
    )


def send_generated_report(
    excel_path,
    txt_path,
    chosen_day,
    email_config,
    attention_items=None,
):
    if attention_items is None:
        msg = create_report_email(
            chosen_day,
            email_config.sender,
            email_config.recipients,
        )

    else:
        msg = create_report_email(
            chosen_day,
            email_config.sender,
            email_config.recipients,
            attention_items,
        )

    add_excel_attachment(
        msg,
        excel_path,
    )

    add_text_attachment(
        msg,
        txt_path,
    )

    send_report_email(
        msg,
        email_config,
    )
