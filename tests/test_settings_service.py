import json

import filters_reporting.settings_service as settings_service
from filters_reporting.settings_service import (
    AppSettings,
)


def make_settings(
    tmp_path,
):
    return AppSettings(
        reports_dir=(tmp_path / "reports"),
        smtp_host="smtp.example.com",
        smtp_port=465,
        username="user@example.com",
        sender="sender@example.com",
        recipients=[
            "a@example.com",
            "b@example.com",
        ],
    )


def test_app_settings_to_email_config_copies_values_and_recipients(
    tmp_path,
):
    settings = make_settings(tmp_path)

    config = settings.to_email_config()

    assert config.smtp_host == "smtp.example.com"

    assert config.smtp_port == 465

    assert config.username == "user@example.com"

    assert config.sender == "sender@example.com"

    assert config.recipients == [
        "a@example.com",
        "b@example.com",
    ]

    assert config.recipients is not settings.recipients


def test_load_settings_returns_defaults_when_file_does_not_exist(
    monkeypatch,
    tmp_path,
):
    defaults = make_settings(tmp_path)

    monkeypatch.setattr(
        settings_service,
        "SETTINGS_FILE",
        tmp_path / "missing.json",
    )

    monkeypatch.setattr(
        settings_service,
        "get_default_settings",
        lambda: defaults,
    )

    applied = []

    monkeypatch.setattr(
        settings_service,
        "apply_settings_runtime",
        applied.append,
    )

    result = settings_service.load_settings()

    assert result is defaults

    assert applied == [defaults]


def test_load_settings_returns_defaults_for_invalid_json(
    monkeypatch,
    tmp_path,
):
    settings_file = tmp_path / "settings.json"

    settings_file.write_text(
        "{broken json",
        encoding="utf-8",
    )

    defaults = make_settings(tmp_path)

    applied = []

    monkeypatch.setattr(
        settings_service,
        "SETTINGS_FILE",
        settings_file,
    )

    monkeypatch.setattr(
        settings_service,
        "get_default_settings",
        lambda: defaults,
    )

    monkeypatch.setattr(
        settings_service,
        "apply_settings_runtime",
        applied.append,
    )

    result = settings_service.load_settings()

    assert result is defaults

    assert applied == [defaults]


def test_load_settings_reads_and_normalizes_saved_values(
    monkeypatch,
    tmp_path,
):
    settings_file = tmp_path / "settings.json"

    settings_file.write_text(
        json.dumps(
            {
                "reports_dir": str(tmp_path / "custom_reports"),
                "smtp": {
                    "host": ("  smtp.test.pl  "),
                    "port": "587",
                    "username": "  test_user  ",
                    "sender": ("  sender@test.pl  "),
                    "recipients": [
                        "  one@test.pl ",
                        "",
                        " two@test.pl",
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    defaults = make_settings(tmp_path)

    applied = []

    monkeypatch.setattr(
        settings_service,
        "SETTINGS_FILE",
        settings_file,
    )

    monkeypatch.setattr(
        settings_service,
        "get_default_settings",
        lambda: defaults,
    )

    monkeypatch.setattr(
        settings_service,
        "apply_settings_runtime",
        applied.append,
    )

    result = settings_service.load_settings()

    assert result.reports_dir == tmp_path / "custom_reports"

    assert result.smtp_host == "smtp.test.pl"

    assert result.smtp_port == 587

    assert result.username == "test_user"

    assert result.sender == "sender@test.pl"

    assert result.recipients == [
        "one@test.pl",
        "two@test.pl",
    ]

    assert applied == [result]


def test_load_settings_uses_defaults_for_invalid_port_and_recipients(
    monkeypatch,
    tmp_path,
):
    settings_file = tmp_path / "settings.json"

    settings_file.write_text(
        json.dumps(
            {
                "smtp": {
                    "port": ("not-a-number"),
                    "recipients": ("not-a-list"),
                }
            }
        ),
        encoding="utf-8",
    )

    defaults = make_settings(tmp_path)

    monkeypatch.setattr(
        settings_service,
        "SETTINGS_FILE",
        settings_file,
    )

    monkeypatch.setattr(
        settings_service,
        "get_default_settings",
        lambda: defaults,
    )

    monkeypatch.setattr(
        settings_service,
        "apply_settings_runtime",
        lambda _settings: None,
    )

    result = settings_service.load_settings()

    assert result.smtp_port == defaults.smtp_port

    assert result.recipients == defaults.recipients


def test_save_settings_writes_json_creates_directories_and_applies_runtime(
    monkeypatch,
    tmp_path,
):
    settings_file = tmp_path / "data" / "settings.json"

    settings = make_settings(tmp_path)

    applied = []

    monkeypatch.setattr(
        settings_service,
        "SETTINGS_FILE",
        settings_file,
    )

    monkeypatch.setattr(
        settings_service,
        "apply_settings_runtime",
        applied.append,
    )

    settings_service.save_settings(settings)

    assert settings.reports_dir.is_dir()

    saved = json.loads(settings_file.read_text(encoding="utf-8"))

    assert saved == {
        "reports_dir": str(settings.reports_dir),
        "smtp": {
            "host": ("smtp.example.com"),
            "port": 465,
            "username": ("user@example.com"),
            "sender": ("sender@example.com"),
            "recipients": [
                "a@example.com",
                "b@example.com",
            ],
        },
        "auto_report": {
            "enabled": False,
            "time": "06:00",
            "send_email": False,
        },
        "opc_ua_client": {
            "security_policy": "None",
            "security_mode": "None",
            "application_uri": "",
            "certificate_path": "",
            "private_key_path": "",
            "trusted_dir": "",
            "server_certificate_path": "",
            "validate_server_certificate": True,
        },
        "opc_ua_server": {
            "enabled": False,
            "endpoint": ("opc.tcp://0.0.0.0:" "4840/filtersreporting/"),
            "namespace": ("urn:FiltersReporting:Server"),
            "application_uri": "",
            "security_policy": ("Aes256Sha256RsaPss"),
            "security_mode": ("SignAndEncrypt"),
            "allow_no_security": False,
            "certificate_path": "",
            "private_key_path": "",
            "allow_anonymous": True,
            "username": "",
            "password_hash": "",
        },
    }

    assert applied == [settings]


def test_apply_settings_runtime_updates_email_config(
    monkeypatch,
    tmp_path,
):
    settings = make_settings(tmp_path)

    email_config = settings_service.EmailConfig(
        smtp_host="old",
        smtp_port=1,
        username="old",
        sender="old",
        recipients=["old@example.com"],
    )

    monkeypatch.setattr(
        settings_service,
        "EMAIL_CONFIG",
        email_config,
    )

    settings_service.apply_settings_runtime(settings)

    assert email_config.smtp_host == settings.smtp_host

    assert email_config.smtp_port == settings.smtp_port

    assert email_config.username == settings.username

    assert email_config.sender == settings.sender

    assert email_config.recipients == settings.recipients

    assert email_config.recipients is not settings.recipients


def test_runtime_email_password_is_trimmed_and_empty_value_does_not_replace_existing(
    monkeypatch,
):
    monkeypatch.delenv(
        "EMAIL_PASSWORD",
        raising=False,
    )

    settings_service.set_runtime_email_password("  secret  ")

    assert settings_service.has_runtime_email_password() is True

    assert settings_service.os.environ["EMAIL_PASSWORD"] == "secret"

    settings_service.set_runtime_email_password("   ")

    assert settings_service.os.environ["EMAIL_PASSWORD"] == "secret"


def test_has_runtime_email_password_returns_false_when_missing(
    monkeypatch,
):
    monkeypatch.delenv(
        "EMAIL_PASSWORD",
        raising=False,
    )

    assert settings_service.has_runtime_email_password() is False


def test_move_generated_report_files_moves_both_files_and_overwrites_target(
    tmp_path,
):
    source_dir = tmp_path / "source"

    target_dir = tmp_path / "target"

    source_dir.mkdir()

    target_dir.mkdir()

    excel = source_dir / "report.xlsx"

    txt = source_dir / "report.txt"

    excel.write_text(
        "new excel",
        encoding="utf-8",
    )

    txt.write_text(
        "new txt",
        encoding="utf-8",
    )

    (target_dir / "report.xlsx").write_text(
        "old excel",
        encoding="utf-8",
    )

    (
        moved_excel,
        moved_txt,
    ) = settings_service.move_generated_report_files(
        excel,
        txt,
        target_dir,
    )

    assert moved_excel == target_dir / "report.xlsx"

    assert moved_txt == target_dir / "report.txt"

    assert moved_excel.read_text(encoding="utf-8") == "new excel"

    assert moved_txt.read_text(encoding="utf-8") == "new txt"

    assert not excel.exists()

    assert not txt.exists()


def test_move_generated_report_files_keeps_file_when_already_in_target(
    tmp_path,
):
    target_dir = tmp_path / "reports"

    target_dir.mkdir()

    excel = target_dir / "report.xlsx"

    txt = target_dir / "report.txt"

    excel.write_text(
        "excel",
        encoding="utf-8",
    )

    txt.write_text(
        "txt",
        encoding="utf-8",
    )

    result = settings_service.move_generated_report_files(
        excel,
        txt,
        target_dir,
    )

    assert result == (
        excel,
        txt,
    )

    assert excel.read_text(encoding="utf-8") == "excel"

    assert txt.read_text(encoding="utf-8") == "txt"


def test_load_settings_reads_auto_report_configuration(
    monkeypatch,
    tmp_path,
):
    settings_file = tmp_path / "settings.json"

    settings_file.write_text(
        json.dumps(
            {
                "auto_report": {
                    "enabled": True,
                    "time": "07:30",
                    "send_email": True,
                }
            }
        ),
        encoding="utf-8",
    )

    defaults = make_settings(tmp_path)

    monkeypatch.setattr(
        settings_service,
        "SETTINGS_FILE",
        settings_file,
    )

    monkeypatch.setattr(
        settings_service,
        "get_default_settings",
        lambda: defaults,
    )

    monkeypatch.setattr(
        settings_service,
        "apply_settings_runtime",
        lambda _settings: None,
    )

    result = settings_service.load_settings()

    assert result.auto_report_enabled is True

    assert result.auto_report_time == "07:30"

    assert result.auto_report_send_email is True
