# -*- coding: utf-8 -*-
"""Unit tests for the H59 BLE packet builder (lib/h59_ble/device.py).

The watch expects fixed 16-byte packets whose last byte is a checksum
(sum of the first 15 bytes mod 256). These tests pin that wire format.
"""
from __future__ import annotations

from lib.h59_ble.device import H59Device, _build


def test_build_packet_is_16_bytes():
    packet = _build(0x1E, 0x01)
    assert len(packet) == 16


def test_build_packet_places_cmd_and_sub_first():
    packet = _build(0x69, 0x03, [0x01])
    assert packet[0] == 0x69
    assert packet[1] == 0x03
    assert packet[2] == 0x01


def test_build_packet_pads_with_zeros():
    packet = _build(0x1E, 0x01)
    assert all(b == 0x00 for b in packet[2:15])


def test_build_packet_checksum_is_sum_mod_256():
    packet = _build(0x69, 0x03, [0x01])
    assert packet[15] == sum(packet[:15]) & 0xFF
    assert packet[15] == (0x69 + 0x03 + 0x01) & 0xFF


def test_build_packet_checksum_wraps_at_256():
    packet = _build(0xFF, 0xFF, [0xFF])
    assert packet[15] == (0xFF * 3) & 0xFF == 0xFD


def test_notify_handler_registration_is_deduplicated():
    device = H59Device()

    def handler(_data):
        pass

    device.add_notify_handler(handler)
    device.add_notify_handler(handler)
    assert device._notify_handlers.count(handler) == 1

    device.remove_notify_handler(handler)
    assert handler not in device._notify_handlers


def test_device_reports_not_connected_before_connect():
    device = H59Device()
    assert device.is_connected is False
