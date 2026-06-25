# -*- coding: utf-8 -*-
from __future__ import annotations

import serial


class FakeSerial:
    """Fake pyserial.Serial replacement for BPMonitor tests. Scripted
    response lines only become readable once a "START" command is written,
    mirroring real hardware timing — BPMonitor's background read thread
    starts as soon as connect() returns, so if lines were available
    immediately it could process (and the subsequent measure() call could
    clear) a result before the test ever sends START."""

    def __init__(self, lines=None):
        self.is_open = True
        self._pending_lines = list(lines or [])
        self._available_lines: list[str] = []
        self.in_waiting = 0

    def write(self, data: bytes) -> None:
        text = data.decode(errors="ignore").strip()
        if text == "START":
            self._available_lines = self._pending_lines
            self._pending_lines = []
            self.in_waiting = 1 if self._available_lines else 0

    def readline(self) -> bytes:
        if self._available_lines:
            line = self._available_lines.pop(0)
            self.in_waiting = 1 if self._available_lines else 0
            return (line + "\n").encode()
        return b""

    def close(self) -> None:
        self.is_open = False


class FakeSerialFactory:
    """Callable replacement for `serial.Serial(...)`. Raises SerialException
    for the first `fail_times` calls, then returns a FakeSerial seeded with
    `lines`."""

    def __init__(self, fail_times: int = 0, lines=None):
        self.fail_times = fail_times
        self.lines = lines or []
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise serial.SerialException("fake port not found")
        return FakeSerial(lines=list(self.lines))
