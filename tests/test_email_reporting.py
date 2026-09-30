from datetime import date
from email.message import EmailMessage
from pathlib import Path

import pytest

import filters_reporting.reporting.email_reporting as email_reporting
from filters_reporting.reporting.email_reporting import (
    EmailConfig,
    add_excel_attachment,
    add_text_attachment,
    create_report_email,
    create_smtp_client,
    get_email_password,
    login_smtp,
    send_email,
    send_generated_report,
    send_report_email,
)

TEST_SENDER = "sender@example.com"
TEST_RECIPIENTS = [
    "receiver@example.com",
]
TEST_SMTP_HOST = "smtp.example.com"
TEST_PASSWORD = "test_password"

CHOSEN_DAY = date.today()


class FakeSMTP:
    def __init__(self):
        self.sent_message = None
        self.tls_started = False
        self.username = None
        self.password = None
        self.closed = False

    def send_message(
        self,
        msg,
    ):
        self.sent_message = msg

    def login(
        self,
        username,
        password,
    ):
        self.username = username
        self.password = password

    def quit(self):
        self.closed = True


called = {}


def fake_smtp(
    host,
    port,
    timeout=None,
):
    called["host"] = host
    called["port"] = port
    called["timeout"] = timeout

    return FakeSMTP()


def fake_create_report_email(
    chosen_day: date,
    sender: str,
    recipients: list[str],
):
    called["chosen_day"] = chosen_day
    called["sender"] = sender
    called["recipients"] = recipients

    return EmailMessage()


def fake_add_excel_attachment(
    msg_arg,
    excel_path_arg,
):
    called["msg"] = msg_arg
    called["excel_path"] = excel_path_arg


def fake_add_text_attachment(
    msg_arg,
    txt_path_arg,
):
    called["msg"] = msg_arg
    called["txt_path"] = txt_path_arg


def fake_send_report_email(
    msg_arg,
    email_config_arg,
):
    called["msg"] = msg_arg
    called["email_config"] = email_config_arg


def make_email_config() -> EmailConfig:
    return EmailConfig(
        smtp_host=TEST_SMTP_HOST,
        smtp_port=465,
        username="user@example.com",
        sender=TEST_SENDER,
        recipients=[
            "receiver@example.com",
        ],
    )


# ======================================================
# CREATE REPORT EMAIL
# ======================================================


def test_create_report_email_has_correct_subject():
    msg = create_report_email(
        CHOSEN_DAY,
        TEST_SENDER,
        TEST_RECIPIENTS,
    )

    expected_subject = f"Raport filtry_{CHOSEN_DAY}"

    assert msg["Subject"] == expected_subject


def test_create_report_email_has_correct_body():
    msg = create_report_email(
        CHOSEN_DAY,
        TEST_SENDER,
        TEST_RECIPIENTS,
    )

    expected_body = "Raport filtrów na dzień " f"{CHOSEN_DAY} " "w załączniku.\n"

    assert msg.get_content() == expected_body


def test_create_report_email_has_correct_sender_from():
    msg = create_report_email(
        CHOSEN_DAY,
        TEST_SENDER,
        TEST_RECIPIENTS,
    )

    assert msg["From"] == TEST_SENDER


def test_create_report_email_has_all_recipients():
    recipients = [
        "first@example.com",
        "second@example.com",
    ]

    msg = create_report_email(
        CHOSEN_DAY,
        TEST_SENDER,
        recipients,
    )

    addresses = [address.addr_spec for address in msg["To"].addresses]

    assert addresses == recipients


# ======================================================
# ATTACHMENTS
# ======================================================


def test_add_excel_attachment_adds_one_attachment(
    tmp_path,
):
    attachment_path = tmp_path / "test.xlsx"

    attachment_path.write_bytes(b"test data for filters reporting")

    msg = create_report_email(
        CHOSEN_DAY,
        TEST_SENDER,
        TEST_RECIPIENTS,
    )

    add_excel_attachment(
        msg,
        attachment_path,
    )

    assert len(list(msg.iter_attachments())) == 1


def test_add_text_attachment_adds_one_attachment(
    tmp_path,
):
    attachment_path = tmp_path / "test.txt"

    attachment_path.write_text(
        "test data for filters reporting",
        encoding="utf-8",
    )

    msg = create_report_email(
        CHOSEN_DAY,
        TEST_SENDER,
        TEST_RECIPIENTS,
    )

    add_text_attachment(
        msg,
        attachment_path,
    )

    assert len(list(msg.iter_attachments())) == 1


def test_email_has_excel_and_text_attachments(
    tmp_path,
):
    excel_path = tmp_path / "test.xlsx"

    excel_path.write_bytes(b"Test excel path here")

    text_path = tmp_path / "test.txt"

    text_path.write_text(
        "Test text path here",
        encoding="utf-8",
    )

    msg = create_report_email(
        CHOSEN_DAY,
        TEST_SENDER,
        TEST_RECIPIENTS,
    )

    add_excel_attachment(
        msg,
        excel_path,
    )

    add_text_attachment(
        msg,
        text_path,
    )

    assert len(list(msg.iter_attachments())) == 2


def test_text_attachment_has_correct_content_type(
    tmp_path,
):
    attachment_path = tmp_path / "test.txt"

    attachment_path.write_text(
        "Test text path here",
        encoding="utf-8",
    )

    msg = create_report_email(
        CHOSEN_DAY,
        TEST_SENDER,
        TEST_RECIPIENTS,
    )

    add_text_attachment(
        msg,
        attachment_path,
    )

    attachment = list(msg.iter_attachments())[0]

    assert attachment.get_content_maintype() == "text"

    assert attachment.get_content_subtype() == "plain"


def test_excel_attachment_has_correct_content_type(
    tmp_path,
):
    attachment_path = tmp_path / "test.xlsx"

    attachment_path.write_bytes(b"Test excel path here")

    msg = create_report_email(
        CHOSEN_DAY,
        TEST_SENDER,
        TEST_RECIPIENTS,
    )

    add_excel_attachment(
        msg,
        attachment_path,
    )

    attachment = list(msg.iter_attachments())[0]

    assert attachment.get_content_maintype() == "application"

    assert attachment.get_content_subtype() == (
        "vnd.openxmlformats-officedocument." "spreadsheetml.sheet"
    )


# ======================================================
# SMTP
# ======================================================


def test_send_email_sends_message():
    msg = EmailMessage()

    smtp = FakeSMTP()

    send_email(
        msg,
        smtp,
    )

    assert smtp.sent_message is msg


def test_create_smtp_client_uses_correct_host_and_port(
    monkeypatch,
):
    called.clear()

    monkeypatch.setattr(
        email_reporting.smtplib,
        "SMTP_SSL",
        fake_smtp,
    )

    create_smtp_client(
        TEST_SMTP_HOST,
        587,
    )

    assert called["host"] == TEST_SMTP_HOST

    assert called["port"] == 587


def test_login_smtp_uses_correct_credentials():
    username = "user@example.com"
    password = TEST_PASSWORD

    smtp = FakeSMTP()

    login_smtp(
        smtp,
        username,
        password,
    )

    assert smtp.username == username

    assert smtp.password == password


def test_send_report_email_logs_in_and_sends_message(
    monkeypatch,
):
    msg = EmailMessage()

    email_config = make_email_config()

    monkeypatch.setenv(
        "EMAIL_PASSWORD",
        TEST_PASSWORD,
    )

    smtp = FakeSMTP()

    monkeypatch.setattr(
        email_reporting,
        "create_smtp_client",
        lambda host, port: smtp,
    )

    send_report_email(
        msg,
        email_config,
    )

    assert smtp.username == email_config.username

    assert smtp.password == TEST_PASSWORD

    assert smtp.sent_message is msg


def test_get_email_password_returns_password_from_environment(
    monkeypatch,
):
    monkeypatch.setenv(
        "EMAIL_PASSWORD",
        TEST_PASSWORD,
    )

    password = get_email_password()

    assert password == TEST_PASSWORD


def test_get_email_password_raises_error_when_password_is_missing(
    monkeypatch,
):
    monkeypatch.delenv(
        "EMAIL_PASSWORD",
        raising=False,
    )

    with pytest.raises(ValueError):
        get_email_password()


# ======================================================
# GENERATED REPORT
# ======================================================


def test_send_generated_report_creates_email(
    monkeypatch,
):
    called.clear()

    email_config = make_email_config()

    monkeypatch.setattr(
        email_reporting,
        "create_report_email",
        fake_create_report_email,
    )

    monkeypatch.setattr(
        email_reporting,
        "send_report_email",
        lambda *args: None,
    )

    monkeypatch.setattr(
        email_reporting,
        "add_excel_attachment",
        lambda *args: None,
    )

    monkeypatch.setattr(
        email_reporting,
        "add_text_attachment",
        lambda *args: None,
    )

    excel_path = Path("test.xlsx")

    txt_path = Path("test.txt")

    send_generated_report(
        excel_path,
        txt_path,
        CHOSEN_DAY,
        email_config,
    )

    assert called["chosen_day"] == CHOSEN_DAY

    assert called["sender"] == email_config.sender

    assert called["recipients"] == email_config.recipients


def test_send_generated_report_adds_excel_attachment(
    monkeypatch,
):
    called.clear()

    msg = EmailMessage()

    def fake_create_email(
        *args,
    ):
        return msg

    email_config = make_email_config()

    monkeypatch.setattr(
        email_reporting,
        "create_report_email",
        fake_create_email,
    )

    monkeypatch.setattr(
        email_reporting,
        "send_report_email",
        lambda *args: None,
    )

    monkeypatch.setattr(
        email_reporting,
        "add_text_attachment",
        lambda *args: None,
    )

    monkeypatch.setattr(
        email_reporting,
        "add_excel_attachment",
        fake_add_excel_attachment,
    )

    excel_path = "test.xlsx"
    txt_path = "test.txt"

    send_generated_report(
        excel_path,
        txt_path,
        CHOSEN_DAY,
        email_config,
    )

    assert called["excel_path"] == excel_path

    assert called["msg"] is msg


def test_send_generated_report_adds_text_attachment(
    monkeypatch,
):
    called.clear()

    msg = EmailMessage()

    def fake_create_email(
        *args,
    ):
        return msg

    email_config = make_email_config()

    monkeypatch.setattr(
        email_reporting,
        "send_report_email",
        lambda *args: None,
    )

    monkeypatch.setattr(
        email_reporting,
        "create_report_email",
        fake_create_email,
    )

    monkeypatch.setattr(
        email_reporting,
        "add_text_attachment",
        fake_add_text_attachment,
    )

    monkeypatch.setattr(
        email_reporting,
        "add_excel_attachment",
        lambda *args: None,
    )

    excel_path = "test.xlsx"
    txt_path = "test.txt"

    send_generated_report(
        excel_path,
        txt_path,
        CHOSEN_DAY,
        email_config,
    )

    assert called["txt_path"] == txt_path

    assert called["msg"] is msg


def test_send_generated_report_sends_email(
    monkeypatch,
):
    called.clear()

    msg = EmailMessage()

    def fake_create_email(
        *args,
    ):
        return msg

    email_config = make_email_config()

    monkeypatch.setattr(
        email_reporting,
        "create_report_email",
        fake_create_email,
    )

    monkeypatch.setattr(
        email_reporting,
        "add_text_attachment",
        lambda *args: None,
    )

    monkeypatch.setattr(
        email_reporting,
        "add_excel_attachment",
        lambda *args: None,
    )

    monkeypatch.setattr(
        email_reporting,
        "send_report_email",
        fake_send_report_email,
    )

    excel_path = "test.xlsx"
    text_path = "test.txt"

    send_generated_report(
        excel_path,
        text_path,
        CHOSEN_DAY,
        email_config,
    )

    assert called["msg"] is msg

    assert called["email_config"] is email_config


# ======================================================
# SMTP CLEANUP
# ======================================================


def test_send_report_email_quits_in_the_end(
    monkeypatch,
):
    email_config = make_email_config()

    msg = EmailMessage()

    smtp = FakeSMTP()

    monkeypatch.setenv(
        "EMAIL_PASSWORD",
        TEST_PASSWORD,
    )

    monkeypatch.setattr(
        email_reporting,
        "create_smtp_client",
        lambda host, port: smtp,
    )

    send_report_email(
        msg,
        email_config,
    )

    assert smtp.closed is True


def test_send_report_email_closes_smtp_when_send_fails(
    monkeypatch,
):
    smtp = FakeSMTP()

    email_config = make_email_config()

    monkeypatch.setenv(
        "EMAIL_PASSWORD",
        TEST_PASSWORD,
    )

    monkeypatch.setattr(
        email_reporting,
        "create_smtp_client",
        lambda host, port: smtp,
    )

    def fake_send_email(
        msg,
        smtp_client,
    ):
        raise RuntimeError("SMTP error")

    monkeypatch.setattr(
        email_reporting,
        "send_email",
        fake_send_email,
    )

    with pytest.raises(RuntimeError):
        send_report_email(
            EmailMessage(),
            email_config,
        )

    assert smtp.closed is True
