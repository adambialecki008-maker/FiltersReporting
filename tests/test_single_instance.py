from __future__ import annotations

import os
import uuid

import pytest

from filters_reporting.single_instance import (
    AlreadyRunningError,
    SingleInstanceLock,
    acquire_single_instance,
)


def _unique_name() -> str:
    return f"pytest-{os.getpid()}-{uuid.uuid4().hex}"


def test_first_instance_can_acquire_lock():
    lock = acquire_single_instance(_unique_name())

    try:
        assert isinstance(lock, SingleInstanceLock)
    finally:
        lock.release()


def test_second_instance_with_same_name_is_rejected():
    name = _unique_name()
    first = acquire_single_instance(name)

    try:
        with pytest.raises(AlreadyRunningError):
            acquire_single_instance(name)
    finally:
        first.release()


def test_lock_can_be_acquired_again_after_release():
    name = _unique_name()

    first = acquire_single_instance(name)
    first.release()

    second = acquire_single_instance(name)
    second.release()


def test_release_is_idempotent():
    lock = acquire_single_instance(_unique_name())

    lock.release()
    lock.release()


def test_context_manager_releases_lock():
    name = _unique_name()

    with SingleInstanceLock(name):
        with pytest.raises(AlreadyRunningError):
            acquire_single_instance(name)

    lock = acquire_single_instance(name)
    lock.release()
