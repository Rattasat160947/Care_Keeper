# -*- coding: utf-8 -*-
"""Unit tests for the H59Device BLE transport layer (lib/h59_ble/device.py).

A fake BleakClient verifies UART characteristic routing, write error
handling, notify fan-out, disconnect bookkeeping, and the keepalive loop —
all without a Bluetooth adapter.
"""
from __future__ import annotations

import asyncio

from lib.h59_ble.device import H59Device, WRITE_UART1, WRITE_UART2


class FakeBleakClient:
    def __init__(self, is_connected=True, write_raises=False):
        self.is_connected = is_connected
        self.write_raises = write_raises
        self.writes = []
        self.notify_subscriptions = []

    async def write_gatt_char(self, uuid, data, response=False):
        if self.write_raises:
            raise RuntimeError("gatt write failed")
        self.writes.append((uuid, bytes(data)))

    async def start_notify(self, uuid, handler):
        self.notify_subscriptions.append((uuid, handler))


def _device(client) -> H59Device:
    device = H59Device()
    device._client = client
    device._connected = True
    return device


# ── write() routing and error handling ────────────────────────────────────

def test_write_routes_uart1_to_uart1_characteristic():
    client = FakeBleakClient()
    device = _device(client)

    ok = asyncio.run(device.write(b"\x01\x02", uart="UART1"))

    assert ok is True
    assert client.writes == [(WRITE_UART1, b"\x01\x02")]


def test_write_routes_uart2_to_uart2_characteristic():
    client = FakeBleakClient()
    device = _device(client)

    asyncio.run(device.write(b"\x01\x02", uart="UART2"))

    assert client.writes[0][0] == WRITE_UART2


def test_write_returns_false_on_gatt_error_instead_of_raising():
    client = FakeBleakClient(write_raises=True)
    device = _device(client)

    ok = asyncio.run(device.write(b"\x01\x02"))

    assert ok is False


# ── notify fan-out ────────────────────────────────────────────────────────

def test_subscribe_registers_both_uart_notify_channels(monkeypatch):
    import lib.h59_ble.device as device_module

    async def instant_sleep(*_args, **_kwargs):
        return None

    monkeypatch.setattr(device_module.asyncio, "sleep", instant_sleep)
    client = FakeBleakClient()
    device = _device(client)

    asyncio.run(device._subscribe())

    assert len(client.notify_subscriptions) == 2


def test_notify_fanout_survives_a_raising_handler(monkeypatch):
    import lib.h59_ble.device as device_module

    async def instant_sleep(*_args, **_kwargs):
        return None

    monkeypatch.setattr(device_module.asyncio, "sleep", instant_sleep)
    client = FakeBleakClient()
    device = _device(client)

    received = []

    def bad_handler(_data):
        raise ValueError("boom")

    device.add_notify_handler(bad_handler)
    device.add_notify_handler(received.append)

    asyncio.run(device._subscribe())
    _uuid, dispatch = client.notify_subscriptions[0]
    dispatch("sender", bytearray([0x1E, 72]))

    assert received == [bytearray([0x1E, 72])]


# ── connection state bookkeeping ──────────────────────────────────────────

def test_on_disconnect_callback_clears_connected_flag():
    device = _device(FakeBleakClient())
    assert device.is_connected is True

    device._on_disconnect(device._client)

    assert device.is_connected is False


def test_is_connected_false_when_client_reports_dropped_link():
    client = FakeBleakClient(is_connected=False)
    device = _device(client)

    assert device.is_connected is False


# ── keepalive loop ────────────────────────────────────────────────────────

def test_keepalive_loop_sends_16_byte_keepalive_packets():
    client = FakeBleakClient()
    device = _device(client)
    device.keepalive_interval = 0.01

    async def run():
        device._start_keepalive()
        await asyncio.sleep(0.05)
        device._stop_keepalive()

    asyncio.run(run())

    assert len(client.writes) >= 1
    uuid, packet = client.writes[0]
    assert uuid == WRITE_UART1
    assert len(packet) == 16
    assert packet[0] == 0x04 and packet[-1] == 0x04


def test_stop_keepalive_cancels_the_task():
    device = _device(FakeBleakClient())
    device.keepalive_interval = 0.01

    async def run():
        device._start_keepalive()
        task = device._keepalive_task
        await asyncio.sleep(0)
        device._stop_keepalive()
        await asyncio.sleep(0)
        return task

    task = asyncio.run(run())

    assert device._keepalive_task is None
    assert task.cancelled()
