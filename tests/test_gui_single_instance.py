from __future__ import annotations

from filters_reporting.gui import app as app_module
from filters_reporting.single_instance import AlreadyRunningError


class _Signal:
    def __init__(self):
        self.connected = []

    def connect(self, callback):
        self.connected.append(callback)


class _FakeApplication:
    def __init__(self, _args):
        self.aboutToQuit = _Signal()

    def exec(self):
        return 0


class _FakeLock:
    def __init__(self):
        self.released = 0

    def release(self):
        self.released += 1


class _FakeServerRunner:
    def __init__(self, repository):
        self.repository = repository
        self.started = 0
        self.stopped = 0

    def start(self):
        self.started += 1

    def stop(self):
        self.stopped += 1


class _FakeWindow:
    def __init__(self, repository):
        self.repository = repository
        self.shown = 0

    def show(self):
        self.shown += 1


def test_second_gui_instance_does_not_open_repository(monkeypatch):
    messages = []

    monkeypatch.setattr(
        app_module,
        "QApplication",
        _FakeApplication,
    )

    def reject_second_instance(_name):
        raise AlreadyRunningError("already running")

    monkeypatch.setattr(
        app_module,
        "acquire_single_instance",
        reject_second_instance,
    )

    def repository_must_not_be_created():
        raise AssertionError(
            "Repository nie może być tworzony dla drugiej instancji GUI."
        )

    monkeypatch.setattr(
        app_module,
        "create_repository",
        repository_must_not_be_created,
    )
    monkeypatch.setattr(
        app_module.QMessageBox,
        "information",
        lambda parent, title, message: messages.append(
            (parent, title, message)
        ),
    )

    result = app_module.main()

    assert result is None
    assert messages == [
        (
            None,
            "FiltersReporting",
            "FiltersReporting jest już uruchomiony.",
        )
    ]


def test_gui_releases_single_instance_lock_on_exit(monkeypatch):
    lock = _FakeLock()
    repository = object()
    exit_codes = []

    monkeypatch.setattr(
        app_module,
        "QApplication",
        _FakeApplication,
    )
    monkeypatch.setattr(
        app_module,
        "acquire_single_instance",
        lambda _name: lock,
    )
    monkeypatch.setattr(
        app_module,
        "create_repository",
        lambda: repository,
    )
    monkeypatch.setattr(
        app_module,
        "OpcUaServerRunner",
        _FakeServerRunner,
    )
    monkeypatch.setattr(
        app_module,
        "MainWindow",
        _FakeWindow,
    )
    monkeypatch.setattr(
        app_module.sys,
        "exit",
        lambda code: exit_codes.append(code),
    )

    app_module.main()

    assert exit_codes == [0]
    assert lock.released == 1
