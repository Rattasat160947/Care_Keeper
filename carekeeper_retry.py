# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable, TypeVar

from carekeeper_logging import log_thread_identity

logger = logging.getLogger(__name__)
T = TypeVar("T")

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_RETRY_DELAY_SECONDS = 2.0  # linear backoff: delay * (attempt - 1)


@dataclass
class SubsystemState:
    """Per-subsystem disable/enable state, thread-safe."""

    name: str
    disabled: bool = False
    disabled_reason: str = ""
    consecutive_failures: int = 0
    last_attempt_ts: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def mark_failure(self, reason: str) -> None:
        with self._lock:
            self.consecutive_failures += 1
            self.last_attempt_ts = time.time()
            self.disabled_reason = reason

    def mark_success(self) -> None:
        with self._lock:
            self.consecutive_failures = 0
            self.disabled = False
            self.disabled_reason = ""
            self.last_attempt_ts = time.time()

    def disable(self, reason: str) -> None:
        with self._lock:
            self.disabled = True
            self.disabled_reason = reason

    def enable(self) -> None:
        with self._lock:
            self.disabled = False
            self.consecutive_failures = 0
            self.disabled_reason = ""


class SubsystemRegistry:
    """Process-wide registry of SubsystemState, one per subsystem name."""

    _states: dict[str, SubsystemState] = {}
    _lock = threading.Lock()

    @classmethod
    def get(cls, name: str) -> SubsystemState:
        with cls._lock:
            if name not in cls._states:
                cls._states[name] = SubsystemState(name=name)
            return cls._states[name]

    @classmethod
    def all_states(cls) -> dict[str, SubsystemState]:
        with cls._lock:
            return dict(cls._states)

    @classmethod
    def reset(cls) -> None:
        """Test-only helper: clear all tracked subsystem state."""
        with cls._lock:
            cls._states.clear()


def retry_with_notify(
    action: Callable[[], T],
    *,
    subsystem: str,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
    on_attempt: Callable[[int, int], None] | None = None,
    on_give_up: Callable[[str], None] | None = None,
    on_success: Callable[[], None] | None = None,
) -> T:
    """Run `action` up to `max_attempts` times. Before each retry (attempt
    2..N), sleeps `delay_seconds * (attempt - 1)` and calls `on_attempt`.

    On success: clears the subsystem's disabled state and calls `on_success`.
    On exhausting all attempts: disables the subsystem, calls `on_give_up`
    with the last error message, then re-raises the last exception.

    Must be called from a worker thread, never the GUI thread, since it
    sleeps between attempts.
    """
    log_thread_identity(f"retry:{subsystem}")
    state = SubsystemRegistry.get(subsystem)
    last_exc: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            logger.info(
                "[retry] %s attempt %d/%d (thread=%s)",
                subsystem, attempt, max_attempts, threading.current_thread().name,
            )
            if on_attempt:
                on_attempt(attempt, max_attempts)
            time.sleep(delay_seconds * (attempt - 1))

        try:
            result = action()
            state.mark_success()
            if on_success:
                on_success()
            return result
        except Exception as exc:
            last_exc = exc
            state.mark_failure(str(exc))
            logger.warning("[retry] %s attempt %d failed: %s", subsystem, attempt, exc)

    state.disable(str(last_exc))
    logger.error("[retry] %s exhausted %d attempts, disabling", subsystem, max_attempts)
    if on_give_up:
        on_give_up(str(last_exc))
    raise last_exc  # type: ignore[misc]


async def retry_with_notify_async(
    action: Callable[[], Awaitable[T]],
    *,
    subsystem: str,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
    on_attempt: Callable[[int, int], None] | None = None,
    on_give_up: Callable[[str], None] | None = None,
    on_success: Callable[[], None] | None = None,
) -> T:
    """Async sibling of `retry_with_notify`, for coroutines (e.g. BLE calls)."""
    log_thread_identity(f"retry_async:{subsystem}")
    state = SubsystemRegistry.get(subsystem)
    last_exc: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            logger.info(
                "[retry] %s attempt %d/%d (thread=%s)",
                subsystem, attempt, max_attempts, threading.current_thread().name,
            )
            if on_attempt:
                on_attempt(attempt, max_attempts)
            await asyncio.sleep(delay_seconds * (attempt - 1))

        try:
            result = await action()
            state.mark_success()
            if on_success:
                on_success()
            return result
        except Exception as exc:
            last_exc = exc
            state.mark_failure(str(exc))
            logger.warning("[retry] %s attempt %d failed: %s", subsystem, attempt, exc)

    state.disable(str(last_exc))
    logger.error("[retry] %s exhausted %d attempts, disabling", subsystem, max_attempts)
    if on_give_up:
        on_give_up(str(last_exc))
    raise last_exc  # type: ignore[misc]
