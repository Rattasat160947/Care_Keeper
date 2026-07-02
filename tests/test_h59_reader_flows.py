# -*- coding: utf-8 -*-
"""Unit tests for the full HR/SpO2 read() flows (lib/h59_ble).

A scripted async device stands in for the real watch: it records every
write and can inject a notification packet in response, so the command
sequence (warm-up → start → value → stop/disconnect) is verified without
Bluetooth hardware. Follows the asyncio.run() pattern used in
test_retry_helper.py.
"""
from __future__ import annotations

import asyncio

import pytest

from lib.h59_ble.heart_rate import HeartRateReader
from lib.h59_ble.spo2 import SpO2Reader


class FakeAsyncDevice:
    """Records writes; optionally injects a notify packet after a write."""

    def __init__(self, inject_on=None, write_ok=True):
        self.inject_on = inject_on or (lambda data: None)
        self.write_ok = write_ok
        self.handlers = []
        self.writes = []
        self.disconnect_calls = 0
        self.is_connected = True

    def add_notify_handler(self, handler):
        self.handlers.append(handler)

    def remove_notify_handler(self, handler):
        self.handlers = [h for h in self.handlers if h != handler]

    async def write(self, data, uart="UART1"):
        self.writes.append((bytes(data), uart))
        if not self.write_ok:
            return False
        packet = self.inject_on(bytes(data))
        if packet is not None:
            for handler in list(self.handlers):
                handler(bytearray(packet))
        return True

    async def disconnect(self):
        self.disconnect_calls += 1
        self.is_connected = False


# ── HeartRateReader.read() ────────────────────────────────────────────────

def _hr_device(bpm=76, **kwargs):
    return FakeAsyncDevice(
        inject_on=lambda data: [0x1E, bpm] if data[0] == 0x1E else None,
        **kwargs,
    )


def test_hr_read_returns_streamed_value():
    device = _hr_device(bpm=76)
    reader = HeartRateReader(device, timeout=1.0, warmup_delay=0)

    value = asyncio.run(reader.read())

    assert value == 76


def test_hr_read_sends_four_warmups_then_start():
    device = _hr_device()
    reader = HeartRateReader(device, timeout=1.0, warmup_delay=0)

    asyncio.run(reader.read())

    assert len(device.writes) == 5
    start_packet, uart = device.writes[4]
    assert start_packet[0] == 0x1E and start_packet[1] == 0x01
    assert uart == "UART1"


def test_hr_read_disconnects_after_value_to_reset_stream_timer():
    device = _hr_device()
    reader = HeartRateReader(device, timeout=1.0, warmup_delay=0)

    asyncio.run(reader.read())

    assert device.disconnect_calls == 1


def test_hr_read_keeps_connection_when_disconnect_after_false():
    device = _hr_device()
    reader = HeartRateReader(device, timeout=1.0, warmup_delay=0, disconnect_after=False)

    asyncio.run(reader.read())

    assert device.disconnect_calls == 0


def test_hr_read_returns_none_when_write_fails():
    device = _hr_device(write_ok=False)
    reader = HeartRateReader(device, timeout=1.0, warmup_delay=0)

    value = asyncio.run(reader.read())

    assert value is None
    assert len(device.writes) == 1  # aborts on the first failed warm-up


def test_hr_read_times_out_and_returns_none():
    device = FakeAsyncDevice()  # never injects a packet
    reader = HeartRateReader(device, timeout=0.05, warmup_delay=0)

    value = asyncio.run(reader.read())

    assert value is None


def test_hr_read_raises_when_device_not_connected():
    device = _hr_device()
    device.is_connected = False
    reader = HeartRateReader(device, timeout=1.0, warmup_delay=0)

    with pytest.raises(RuntimeError):
        asyncio.run(reader.read())


# ── SpO2Reader.read() ─────────────────────────────────────────────────────

def _spo2_device(spo2=98, **kwargs):
    def inject(data):
        if data[0] == 0x69 and data[1] == 0x03 and data[2] == 0x01:
            return [0x69, 0x03, 0x00, spo2, 0x01]
        return None

    return FakeAsyncDevice(inject_on=inject, **kwargs)


def test_spo2_read_returns_measured_value():
    device = _spo2_device(spo2=98)
    reader = SpO2Reader(device, timeout=1.0)

    value = asyncio.run(reader.read())

    assert value == 98


def test_spo2_read_sends_start_then_stop_command():
    device = _spo2_device()
    reader = SpO2Reader(device, timeout=1.0)

    asyncio.run(reader.read())

    assert len(device.writes) == 2
    start, stop = device.writes[0][0], device.writes[1][0]
    assert (start[0], start[1], start[2]) == (0x69, 0x03, 0x01)
    assert (stop[0], stop[1], stop[2]) == (0x69, 0x03, 0x00)


def test_spo2_read_timeout_returns_none_but_still_stops_stream():
    device = FakeAsyncDevice()  # never responds
    reader = SpO2Reader(device, timeout=0.05)

    value = asyncio.run(reader.read())

    assert value is None
    assert len(device.writes) == 2  # start + stop even on timeout


def test_spo2_read_returns_none_when_start_write_fails():
    device = _spo2_device(write_ok=False)
    reader = SpO2Reader(device, timeout=1.0)

    value = asyncio.run(reader.read())

    assert value is None
    assert len(device.writes) == 1  # no stop command after failed start


def test_spo2_read_raises_when_device_not_connected():
    device = _spo2_device()
    device.is_connected = False
    reader = SpO2Reader(device, timeout=1.0)

    with pytest.raises(RuntimeError):
        asyncio.run(reader.read())
