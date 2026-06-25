# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import threading

from PySide6.QtCore import QThread

logger = logging.getLogger("carekeeper.threads")


def log_thread_identity(context: str) -> None:
    """Log Python + Qt thread identity for `context` to prove background work
    runs off the GUI thread. Call this at the start of any function expected
    to run on a worker thread (ProviderTask.run, QueueDrainWorker.run, retry
    loops, etc)."""
    py_thread = threading.current_thread()
    qt_thread = QThread.currentThread()
    is_main = py_thread is threading.main_thread()
    # Format qt_thread to str() immediately: log handlers may format the
    # record's args lazily, by which point the underlying Qt/C++ thread
    # object can already be destroyed (e.g. a short-lived worker thread),
    # raising "Internal C++ object already deleted".
    logger.info(
        "[thread] context=%s py_name=%s py_id=%s qt_thread=%s is_main_thread=%s",
        context, py_thread.name, threading.get_ident(), str(qt_thread), is_main,
    )


def configure_logging(level: int = logging.INFO) -> None:
    """Call once at app startup so thread-identity logs are visible with
    timestamps and thread names."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(threadName)s: %(message)s",
    )
