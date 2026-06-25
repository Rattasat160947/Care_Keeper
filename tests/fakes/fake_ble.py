# -*- coding: utf-8 -*-
from __future__ import annotations


class FailNTimesThenSucceed:
    """Async-callable replacement for `H59Device.connect`. Raises for the
    first `fail_times` calls, then succeeds (returns None). Assigning an
    instance directly as a class attribute (`H59Device.connect = instance`)
    works without binding `self`, since plain objects aren't descriptors."""

    def __init__(self, fail_times: int = 0, exception_msg: str = "fake ble connect failure"):
        self.fail_times = fail_times
        self.exception_msg = exception_msg
        self.calls = 0

    async def __call__(self, *args, **kwargs):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError(f"{self.exception_msg} #{self.calls}")
        return None


class FakeSpO2Reader:
    """Replacement for SpO2Reader that returns a scripted value (or None to
    simulate a timeout) without touching real BLE notify handlers."""

    def __init__(self, device, timeout: float = 60.0, value=98):
        self._device = device
        self._timeout = timeout
        self._value = value

    async def read(self):
        return self._value

    def close(self) -> None:
        pass
