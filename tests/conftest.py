# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest

import carekeeper_retry
from carekeeper_queue import SubmissionQueue
from carekeeper_retry import SubsystemRegistry


async def _instant_async_sleep(*_args, **_kwargs):
    return None


@pytest.fixture(autouse=True)
def reset_subsystem_registry():
    """SubsystemRegistry is a process-global dict; isolate tests from each other."""
    SubsystemRegistry.reset()
    yield
    SubsystemRegistry.reset()


@pytest.fixture(autouse=True)
def fast_retry_sleep(monkeypatch):
    """Provider-level retry tests don't pass delay_seconds=0 explicitly (the
    provider methods use the helper's default backoff), so neutralize the
    real sleep here to keep the suite fast without weakening the retry-count
    assertions, which don't depend on wall-clock time."""
    monkeypatch.setattr(carekeeper_retry.time, "sleep", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(carekeeper_retry.asyncio, "sleep", _instant_async_sleep)


@pytest.fixture
def tmp_queue_db(tmp_path):
    return tmp_path / "test_queue.db"


@pytest.fixture
def submission_queue(tmp_queue_db):
    return SubmissionQueue(db_path=tmp_queue_db)
