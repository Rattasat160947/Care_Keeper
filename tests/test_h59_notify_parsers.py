# -*- coding: utf-8 -*-
"""Unit tests for the H59 BLE notification parsers.

HeartRateReader and SpO2Reader receive raw BLE packets via _on_notify and
must accept only physiologically valid values (HR 30-220 bpm, SpO2 70-100 %).
The parsers are exercised directly with hand-built byte arrays, so no real
Bluetooth stack or watch is needed.
"""
from __future__ import annotations

from lib.h59_ble.heart_rate import HeartRateReader
from lib.h59_ble.spo2 import SpO2Reader


class StubDevice:
    """Minimal stand-in for H59Device: readers only need handler registration."""

    def __init__(self):
        self.handlers = []
        self.is_connected = True

    def add_notify_handler(self, handler):
        self.handlers.append(handler)

    def remove_notify_handler(self, handler):
        self.handlers = [h for h in self.handlers if h != handler]


def _hr_reader():
    return HeartRateReader(StubDevice())


def _spo2_reader():
    return SpO2Reader(StubDevice())


# ── Heart rate: primary stream packet 1E [bpm] ────────────────────────────

def test_hr_stream_packet_accepts_valid_bpm():
    reader = _hr_reader()
    reader._on_notify(bytearray([0x1E, 72]))
    assert reader.last_value == 72


def test_hr_accepts_lower_bound_30_bpm():
    reader = _hr_reader()
    reader._on_notify(bytearray([0x1E, 30]))
    assert reader.last_value == 30


def test_hr_accepts_upper_bound_220_bpm():
    reader = _hr_reader()
    reader._on_notify(bytearray([0x1E, 220]))
    assert reader.last_value == 220


def test_hr_rejects_29_bpm_below_range():
    reader = _hr_reader()
    reader._on_notify(bytearray([0x1E, 29]))
    assert reader.last_value is None


def test_hr_rejects_221_bpm_above_range():
    reader = _hr_reader()
    reader._on_notify(bytearray([0x1E, 221]))
    assert reader.last_value is None


def test_hr_ignores_zero_bpm_placeholder():
    reader = _hr_reader()
    reader._on_notify(bytearray([0x1E, 0x00]))
    assert reader.last_value is None


def test_hr_ignores_packet_shorter_than_2_bytes():
    reader = _hr_reader()
    reader._on_notify(bytearray([0x1E]))
    assert reader.last_value is None


def test_hr_ignores_packets_after_lock():
    reader = _hr_reader()
    reader._locked = True
    reader._on_notify(bytearray([0x1E, 72]))
    assert reader.last_value is None


def test_hr_stream_keeps_latest_value_until_locked():
    reader = _hr_reader()
    reader._on_notify(bytearray([0x1E, 72]))
    reader._on_notify(bytearray([0x1E, 90]))
    # _locked is only set by read(); the raw handler tracks the newest value.
    assert reader.last_value == 90


# ── Heart rate: fallback packets ──────────────────────────────────────────

def test_hr_fallback_6a01_packet_parses_third_byte():
    reader = _hr_reader()
    reader._on_notify(bytearray([0x6A, 0x01, 65]))
    assert reader.last_value == 65


def test_hr_fallback_6a01_rejects_out_of_range():
    reader = _hr_reader()
    reader._on_notify(bytearray([0x6A, 0x01, 250]))
    assert reader.last_value is None


def test_hr_snapshot_0c_packet_parses_byte_7():
    reader = _hr_reader()
    packet = bytearray([0x0C, 0, 0, 0, 0, 0, 0, 88])
    reader._on_notify(packet)
    assert reader.last_value == 88


def test_hr_snapshot_0c_too_short_is_ignored():
    reader = _hr_reader()
    reader._on_notify(bytearray([0x0C, 0, 0, 0, 0, 0, 88]))
    assert reader.last_value is None


# ── SpO2: completion packet 69 03 00 [spo2] 01 ────────────────────────────

def test_spo2_complete_packet_parses_value():
    reader = _spo2_reader()
    reader._on_notify(bytearray([0x69, 0x03, 0x00, 98, 0x01]))
    assert reader.last_value == 98


def test_spo2_accepts_lower_bound_70_percent():
    reader = _spo2_reader()
    reader._on_notify(bytearray([0x69, 0x03, 0x00, 70, 0x01]))
    assert reader.last_value == 70


def test_spo2_accepts_upper_bound_100_percent():
    reader = _spo2_reader()
    reader._on_notify(bytearray([0x69, 0x03, 0x00, 100, 0x01]))
    assert reader.last_value == 100


def test_spo2_rejects_69_percent_below_range():
    reader = _spo2_reader()
    reader._on_notify(bytearray([0x69, 0x03, 0x00, 69, 0x01]))
    assert reader.last_value is None


def test_spo2_rejects_101_percent_above_range():
    reader = _spo2_reader()
    reader._on_notify(bytearray([0x69, 0x03, 0x00, 101, 0x01]))
    assert reader.last_value is None


def test_spo2_ignores_still_measuring_packet():
    # byte[4] == 0x00 means "still measuring" — value byte is not final yet.
    reader = _spo2_reader()
    reader._on_notify(bytearray([0x69, 0x03, 0x00, 98, 0x00]))
    assert reader.last_value is None


def test_spo2_ignores_packet_shorter_than_5_bytes():
    reader = _spo2_reader()
    reader._on_notify(bytearray([0x69, 0x03, 0x00]))
    assert reader.last_value is None


def test_spo2_confirmed_6a03_packet_parses_value():
    reader = _spo2_reader()
    reader._on_notify(bytearray([0x6A, 0x03, 97]))
    assert reader.last_value == 97


def test_spo2_unrelated_command_is_ignored():
    reader = _spo2_reader()
    reader._on_notify(bytearray([0x1E, 72]))
    assert reader.last_value is None


# ── Reader lifecycle ──────────────────────────────────────────────────────

def test_reader_close_unregisters_handler():
    device = StubDevice()
    reader = SpO2Reader(device)
    assert len(device.handlers) == 1
    reader.close()
    assert device.handlers == []
