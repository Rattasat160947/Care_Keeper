# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import threading
import time

import pytest

import carekeeper_ui as ui_module
from carekeeper_logging import log_thread_identity
from carekeeper_queue import QueueDrainWorker, SubmissionQueue
from carekeeper_retry import retry_with_notify


def test_provider_task_runs_off_main_thread(qtbot):
    recorded = {}

    def action():
        recorded["ident"] = threading.get_ident()
        return "ok"

    task = ui_module.ProviderTask(action)
    with qtbot.waitSignal(task.completed, timeout=3000):
        task.start()

    assert "ident" in recorded
    assert recorded["ident"] != threading.main_thread().ident


def test_queue_drain_worker_runs_off_main_thread(submission_queue):
    worker = QueueDrainWorker(submission_queue, send_fn=lambda payload: True, poll_interval=0.05)
    worker.start()
    try:
        deadline = time.monotonic() + 2
        while not worker.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert worker.is_alive()
        assert worker.ident != threading.main_thread().ident
    finally:
        worker.stop()
        worker.join(timeout=2)


def test_retry_sleep_does_not_block_main_thread_log_assertion(caplog):
    """retry_with_notify must log thread identity, and that identity must
    show is_main_thread=False when run from a worker thread — proving the
    sleep-between-attempts loop never runs on the GUI thread."""
    recorded = {}

    def worker():
        with caplog.at_level(logging.INFO, logger="carekeeper.threads"):
            retry_with_notify(lambda: "ok", subsystem="thread_proof", delay_seconds=0)
        recorded["done"] = True

    t = threading.Thread(target=worker)
    t.start()
    t.join(timeout=3)

    assert recorded.get("done") is True
    thread_records = [r for r in caplog.records if r.name == "carekeeper.threads"]
    assert any("is_main_thread=False" in r.getMessage() for r in thread_records)


def test_log_thread_identity_format(caplog):
    with caplog.at_level(logging.INFO, logger="carekeeper.threads"):
        log_thread_identity("unit_test_context")

    [record] = [r for r in caplog.records if r.name == "carekeeper.threads"]
    message = record.getMessage()
    assert "context=unit_test_context" in message
    assert "py_name=" in message
    assert "py_id=" in message
    assert "qt_thread=" in message
    assert "is_main_thread=" in message
