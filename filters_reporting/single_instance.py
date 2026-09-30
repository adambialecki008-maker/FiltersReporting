from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO


class AlreadyRunningError(RuntimeError):
    """Raised when another instance already owns the same application lock."""


@dataclass
class SingleInstanceLock:
    """Process-wide single-instance guard.

    On Windows a named mutex is used. This is the mechanism used by the
    installed FiltersReporting applications.

    On non-Windows systems a small lock file is used only as a development
    and test fallback.
    """

    name: str
    _windows_handle: int | None = field(default=None, init=False, repr=False)
    _lock_file: IO[str] | None = field(default=None, init=False, repr=False)
    _released: bool = field(default=False, init=False, repr=False)

    def acquire(self) -> None:
        if self._windows_handle is not None or self._lock_file is not None:
            return

        if os.name == "nt":
            self._acquire_windows_mutex()
        else:
            self._acquire_file_lock()

    def release(self) -> None:
        if self._released:
            return

        self._released = True

        if os.name == "nt":
            self._release_windows_mutex()
        else:
            self._release_file_lock()

    def __enter__(self) -> "SingleInstanceLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.release()

    def _acquire_windows_mutex(self) -> None:
        import ctypes
        from ctypes import wintypes

        ERROR_ALREADY_EXISTS = 183

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        create_mutex = kernel32.CreateMutexW
        create_mutex.argtypes = (
            wintypes.LPVOID,
            wintypes.BOOL,
            wintypes.LPCWSTR,
        )
        create_mutex.restype = wintypes.HANDLE

        handle = create_mutex(
            None,
            False,
            self._windows_mutex_name(),
        )

        if not handle:
            error_code = ctypes.get_last_error()
            raise OSError(
                error_code,
                "Nie udało się utworzyć blokady pojedynczej instancji.",
            )

        error_code = ctypes.get_last_error()

        if error_code == ERROR_ALREADY_EXISTS:
            self._close_windows_handle(handle)
            raise AlreadyRunningError(
                f"Inna instancja '{self.name}' jest już uruchomiona."
            )

        self._windows_handle = int(handle)

    def _release_windows_mutex(self) -> None:
        if self._windows_handle is None:
            return

        self._close_windows_handle(self._windows_handle)
        self._windows_handle = None

    @staticmethod
    def _close_windows_handle(handle: int) -> None:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = (wintypes.HANDLE,)
        close_handle.restype = wintypes.BOOL
        close_handle(handle)

    def _windows_mutex_name(self) -> str:
        # Local\ keeps the mutex scoped to the currently logged-in Windows
        # session and does not require administrator privileges.
        safe_name = "".join(
            character if character.isalnum() or character in "._-" else "_"
            for character in self.name
        )
        return f"Local\\FiltersReporting.{safe_name}"

    def _acquire_file_lock(self) -> None:
        import fcntl

        lock_path = self._fallback_lock_path()
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        lock_file = lock_path.open("a+", encoding="utf-8")

        try:
            fcntl.flock(
                lock_file.fileno(),
                fcntl.LOCK_EX | fcntl.LOCK_NB,
            )
        except BlockingIOError as exc:
            lock_file.close()
            raise AlreadyRunningError(
                f"Inna instancja '{self.name}' jest już uruchomiona."
            ) from exc

        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(str(os.getpid()))
        lock_file.flush()

        self._lock_file = lock_file

    def _release_file_lock(self) -> None:
        if self._lock_file is None:
            return

        import fcntl

        try:
            fcntl.flock(
                self._lock_file.fileno(),
                fcntl.LOCK_UN,
            )
        finally:
            self._lock_file.close()
            self._lock_file = None

    def _fallback_lock_path(self) -> Path:
        base_dir = Path(
            os.environ.get(
                "TMPDIR",
                os.environ.get("TEMP", "/tmp"),
            )
        )
        return base_dir / f"filters_reporting_{self.name}.lock"


def acquire_single_instance(name: str) -> SingleInstanceLock:
    """Create and acquire a single-instance lock.

    The returned object must remain alive for as long as the application is
    running. Call ``release()`` only during normal application shutdown.
    """

    lock = SingleInstanceLock(name=name)
    lock.acquire()
    return lock
