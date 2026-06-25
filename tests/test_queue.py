# -*- coding: utf-8 -*-
from __future__ import annotations

import sqlite3
import threading

from carekeeper_queue import SubmissionQueue


def _raw_rows(db_path):
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("SELECT id, status, attempts, last_error FROM submission_queue").fetchall()
    conn.close()
    return rows


def test_enqueue_creates_row_with_pending_status(submission_queue, tmp_queue_db):
    row_id = submission_queue.enqueue({"mac": "aa:bb"})
    rows = _raw_rows(tmp_queue_db)
    assert len(rows) == 1
    assert rows[0][0] == row_id
    assert rows[0][1] == "pending"
    assert rows[0][2] == 0


def test_peek_pending_returns_fifo_order(submission_queue):
    id1 = submission_queue.enqueue({"n": 1})
    id2 = submission_queue.enqueue({"n": 2})
    id3 = submission_queue.enqueue({"n": 3})

    pending = submission_queue.peek_pending(limit=3)

    assert [item.id for item in pending] == [id1, id2, id3]
    assert [item.payload["n"] for item in pending] == [1, 2, 3]


def test_mark_sent_and_delete_removes_row(submission_queue, tmp_queue_db):
    row_id = submission_queue.enqueue({"mac": "aa:bb"})
    submission_queue.mark_sent_and_delete(row_id)

    assert submission_queue.count_pending() == 0
    assert _raw_rows(tmp_queue_db) == []


def test_mark_failed_increments_attempts_and_keeps_pending(submission_queue):
    row_id = submission_queue.enqueue({"mac": "aa:bb"})
    submission_queue.mark_failed(row_id, "boom")

    pending = submission_queue.peek_pending(limit=1)
    assert len(pending) == 1
    assert pending[0].attempts == 1
    assert pending[0].last_error == "boom"
    assert submission_queue.count_pending() == 1


def test_queue_persists_across_restart(tmp_queue_db):
    queue_a = SubmissionQueue(db_path=tmp_queue_db)
    queue_a.enqueue({"mac": "aa:bb"})

    # Simulate an app restart: a brand-new SubmissionQueue instance pointed
    # at the same db file should see the same pending row.
    queue_b = SubmissionQueue(db_path=tmp_queue_db)
    assert queue_b.count_pending() == 1


def test_reset_stuck_sending_recovers_after_crash(tmp_queue_db):
    queue_a = SubmissionQueue(db_path=tmp_queue_db)
    row_id = queue_a.enqueue({"mac": "aa:bb"})
    queue_a.mark_sending(row_id)  # simulate a crash mid-send

    queue_b = SubmissionQueue(db_path=tmp_queue_db)
    queue_b.reset_stuck_sending()

    pending = queue_b.peek_pending(limit=1)
    assert len(pending) == 1
    assert pending[0].id == row_id


def test_concurrent_enqueue_from_multiple_threads(submission_queue):
    def worker(n):
        submission_queue.enqueue({"n": n})

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert submission_queue.count_pending() == 10
