# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from carekeeper_logging import log_thread_identity

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent / "data" / "carekeeper_queue.db"
DRAIN_POLL_INTERVAL_SECONDS = 5.0

_SCHEMA = """
CREATE TABLE IF NOT EXISTS submission_queue (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    payload_json  TEXT    NOT NULL,
    created_at    REAL    NOT NULL,
    attempts      INTEGER NOT NULL DEFAULT 0,
    last_error    TEXT,
    status        TEXT    NOT NULL DEFAULT 'pending'
);
CREATE INDEX IF NOT EXISTS idx_queue_status_created
    ON submission_queue(status, created_at);
"""


@dataclass
class QueuedSubmission:
    id: int
    payload: dict
    created_at: float
    attempts: int
    last_error: str | None


class SubmissionQueue:
    """Thread-safe SQLite-backed FIFO queue for health-data POST payloads.

    Each public method opens and closes its own short-lived connection,
    since sqlite3 connections must not be shared across threads. Rows are
    deleted immediately on successful send so the table never grows
    unbounded, and survive process restarts since the database is a real
    file on disk.
    """

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_lock = threading.Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_schema(self) -> None:
        with self._init_lock, self._connect() as conn:
            conn.executescript(_SCHEMA)

    def enqueue(self, payload: dict) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO submission_queue (payload_json, created_at, attempts, status) "
                "VALUES (?, ?, 0, 'pending')",
                (json.dumps(payload), time.time()),
            )
            conn.commit()
            row_id = cur.lastrowid
        logger.info("[queue] enqueued id=%d (thread=%s)", row_id, threading.current_thread().name)
        return row_id

    def peek_pending(self, limit: int = 1) -> list[QueuedSubmission]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, payload_json, created_at, attempts, last_error "
                "FROM submission_queue WHERE status = 'pending' "
                "ORDER BY created_at ASC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            QueuedSubmission(id=r[0], payload=json.loads(r[1]), created_at=r[2], attempts=r[3], last_error=r[4])
            for r in rows
        ]

    def mark_sending(self, row_id: int) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE submission_queue SET status='sending' WHERE id=?", (row_id,))
            conn.commit()

    def mark_failed(self, row_id: int, error: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE submission_queue SET status='pending', attempts = attempts + 1, last_error=? WHERE id=?",
                (error, row_id),
            )
            conn.commit()

    def mark_sent_and_delete(self, row_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM submission_queue WHERE id=?", (row_id,))
            conn.commit()
        logger.info("[queue] sent + deleted id=%d", row_id)

    def count_pending(self) -> int:
        with self._connect() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM submission_queue WHERE status IN ('pending','sending')"
            ).fetchone()[0]

    def reset_stuck_sending(self) -> None:
        """Call at startup: rows left in 'sending' from a crash go back to 'pending'."""
        with self._connect() as conn:
            conn.execute("UPDATE submission_queue SET status='pending' WHERE status='sending'")
            conn.commit()


class QueueDrainWorker(threading.Thread):
    """Background daemon thread that polls the SubmissionQueue and sends
    pending rows in FIFO order via `send_fn(payload) -> bool` (or raises on
    failure). On success the row is deleted; on failure it's marked pending
    again with attempts incremented, retried on the next poll cycle."""

    def __init__(
        self,
        queue: SubmissionQueue,
        send_fn: Callable[[dict], bool],
        is_online_fn: Callable[[], bool] | None = None,
        on_drain_success: Callable[[int], None] | None = None,
        on_drain_failure: Callable[[int, str], None] | None = None,
        poll_interval: float = DRAIN_POLL_INTERVAL_SECONDS,
    ) -> None:
        super().__init__(name="QueueDrainWorker", daemon=True)
        self.queue = queue
        self.send_fn = send_fn
        self.is_online_fn = is_online_fn
        self.on_drain_success = on_drain_success
        self.on_drain_failure = on_drain_failure
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        log_thread_identity("QueueDrainWorker")
        self.queue.reset_stuck_sending()
        while not self._stop_event.is_set():
            try:
                self._drain_once()
            except Exception:
                logger.exception("[queue] drain loop error")
            self._stop_event.wait(self.poll_interval)

    def _drain_once(self) -> None:
        if self.is_online_fn and not self.is_online_fn():
            return
        pending = self.queue.peek_pending(limit=1)
        if not pending:
            return
        item = pending[0]
        self.queue.mark_sending(item.id)
        try:
            ok = self.send_fn(item.payload)
            if not ok:
                raise RuntimeError("send_fn returned False")
            self.queue.mark_sent_and_delete(item.id)
            if self.on_drain_success:
                self.on_drain_success(item.id)
        except Exception as exc:
            self.queue.mark_failed(item.id, str(exc))
            logger.warning("[queue] drain send failed id=%d: %s", item.id, exc)
            if self.on_drain_failure:
                self.on_drain_failure(item.id, str(exc))
