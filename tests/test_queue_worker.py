# -*- coding: utf-8 -*-
from __future__ import annotations

import time

from carekeeper_queue import QueueDrainWorker


def _wait_until(predicate, timeout=5.0, interval=0.02):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


def test_drain_worker_sends_pending_row_and_deletes_it(submission_queue):
    sent = []

    def send_fn(payload):
        sent.append(payload)
        return True

    submission_queue.enqueue({"mac": "aa:bb"})
    worker = QueueDrainWorker(submission_queue, send_fn, poll_interval=0.05)
    worker.start()
    try:
        assert _wait_until(lambda: submission_queue.count_pending() == 0)
        assert sent == [{"mac": "aa:bb"}]
    finally:
        worker.stop()
        worker.join(timeout=2)


def test_drain_worker_retries_on_failure_next_cycle(submission_queue):
    calls = {"n": 0}

    def send_fn(payload):
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("simulated network drop")
        return True

    submission_queue.enqueue({"mac": "aa:bb"})
    worker = QueueDrainWorker(submission_queue, send_fn, poll_interval=0.05)
    worker.start()
    try:
        assert _wait_until(lambda: submission_queue.count_pending() == 0, timeout=5)
        assert calls["n"] == 3
    finally:
        worker.stop()
        worker.join(timeout=2)


def test_drain_worker_respects_is_online_fn(submission_queue):
    send_calls = []
    submission_queue.enqueue({"mac": "aa:bb"})
    worker = QueueDrainWorker(
        submission_queue,
        send_fn=lambda payload: send_calls.append(payload) or True,
        is_online_fn=lambda: False,
        poll_interval=0.05,
    )
    worker.start()
    try:
        time.sleep(0.3)
        assert send_calls == []
        assert submission_queue.count_pending() == 1
    finally:
        worker.stop()
        worker.join(timeout=2)


def test_drain_worker_processes_fifo_order(submission_queue):
    order = []

    def send_fn(payload):
        order.append(payload["n"])
        return True

    for n in range(3):
        submission_queue.enqueue({"n": n})

    worker = QueueDrainWorker(submission_queue, send_fn, poll_interval=0.05)
    worker.start()
    try:
        assert _wait_until(lambda: submission_queue.count_pending() == 0, timeout=5)
        assert order == [0, 1, 2]
    finally:
        worker.stop()
        worker.join(timeout=2)


def test_drain_worker_stop_terminates_thread(submission_queue):
    worker = QueueDrainWorker(submission_queue, send_fn=lambda payload: True, poll_interval=0.05)
    worker.start()
    assert worker.is_alive()
    worker.stop()
    worker.join(timeout=2)
    assert not worker.is_alive()
