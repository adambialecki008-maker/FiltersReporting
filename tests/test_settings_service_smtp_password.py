import filters_reporting.settings_service as settings_service


def test_save_email_password_persists_and_sets_runtime(
    monkeypatch,
):
    persisted = []
    runtime = []

    monkeypatch.setattr(
        settings_service,
        "set_smtp_password",
        persisted.append,
    )

    monkeypatch.setattr(
        settings_service,
        "set_runtime_email_password",
        runtime.append,
    )

    settings_service.save_email_password(
        "  secret123  ",
    )

    assert persisted == ["secret123"]
    assert runtime == ["secret123"]


def test_save_email_password_ignores_empty_value(
    monkeypatch,
):
    persisted = []
    runtime = []

    monkeypatch.setattr(
        settings_service,
        "set_smtp_password",
        persisted.append,
    )

    monkeypatch.setattr(
        settings_service,
        "set_runtime_email_password",
        runtime.append,
    )

    settings_service.save_email_password(
        "   ",
    )

    assert persisted == []
    assert runtime == []


def test_has_email_password_accepts_persistent_password(
    monkeypatch,
):
    monkeypatch.setattr(
        settings_service,
        "has_runtime_email_password",
        lambda: False,
    )

    monkeypatch.setattr(
        settings_service,
        "has_smtp_password",
        lambda: True,
    )

    assert settings_service.has_email_password() is True
