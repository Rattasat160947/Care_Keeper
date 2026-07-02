# -*- coding: utf-8 -*-
"""Unit tests for the Thai national ID card helpers (lib/thaiidcard/card.py).

Covers the pure formatting/decoding helpers and the APDU response protocol
(GET RESPONSE on SW1=0x61, error on non-9000) using a scripted fake
connection — no physical smart-card reader involved.
"""
from __future__ import annotations

import pytest

from lib.thaiidcard.card import ThaiIDCard, format_thai_birth_date


# ── format_thai_birth_date: YYYYMMDD (พ.ศ.) → "D เดือน YYYY" ─────────────

def test_birth_date_formats_buddhist_era_date():
    assert format_thai_birth_date("25320415") == "15 เมษายน 2532"


def test_birth_date_formats_single_digit_day_without_padding():
    assert format_thai_birth_date("25401201") == "1 ธันวาคม 2540"


def test_birth_date_all_twelve_months_map_to_thai_names():
    names = [format_thai_birth_date(f"2530{m:02d}15").split()[1] for m in range(1, 13)]
    assert names == [
        "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
        "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
    ]


def test_birth_date_rejects_wrong_length():
    assert format_thai_birth_date("2532041") == "2532041"


def test_birth_date_rejects_non_digits():
    assert format_thai_birth_date("25AB0415") == "25AB0415"


def test_birth_date_rejects_month_zero_and_thirteen():
    assert format_thai_birth_date("25320015") == "25320015"
    assert format_thai_birth_date("25321315") == "25321315"


def test_birth_date_rejects_day_zero():
    # Cards for people who only registered a birth year store day 00.
    assert format_thai_birth_date("25320400") == "25320400"


def test_birth_date_strips_surrounding_whitespace():
    assert format_thai_birth_date(" 25320415 ") == "15 เมษายน 2532"


# ── _decode: TIS-620 bytes → clean text ───────────────────────────────────

def _card():
    return ThaiIDCard.__new__(ThaiIDCard)


def test_decode_replaces_hash_separator_with_space():
    card = _card()
    assert card._decode(b"Mr.#John#Doe") == "Mr. John Doe"


def test_decode_strips_trailing_padding():
    card = _card()
    assert card._decode(b"1234567890123   ") == "1234567890123"


def test_decode_reads_tis620_thai_characters():
    card = _card()
    raw = "นาย#สมชาย#ใจดี".encode("tis-620")
    assert card._decode(raw) == "นาย สมชาย ใจดี"


# ── APDU transport protocol ───────────────────────────────────────────────

class ScriptedConnection:
    """Fake pyscard connection returning queued (data, sw1, sw2) tuples."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.transmitted = []

    def transmit(self, apdu):
        self.transmitted.append(apdu)
        return self.responses.pop(0)


def test_transmit_issues_get_response_on_sw1_61():
    card = _card()
    card.conn = ScriptedConnection([
        ([], 0x61, 0x0D),                     # card says: 13 bytes waiting
        (list(b"1234567890123"), 0x90, 0x00),  # GET RESPONSE returns them
    ])

    data, sw1, sw2 = card._transmit([0x80, 0xB0, 0x00, 0x04, 0x02, 0x00, 0x0D])

    assert (sw1, sw2) == (0x90, 0x00)
    assert bytes(data) == b"1234567890123"
    # Second APDU must be GET RESPONSE 00 C0 00 00 <len from sw2>.
    assert card.conn.transmitted[1] == [0x00, 0xC0, 0x00, 0x00, 0x0D]


def test_transmit_passes_through_direct_response():
    card = _card()
    card.conn = ScriptedConnection([(list(b"OK"), 0x90, 0x00)])

    data, sw1, sw2 = card._transmit([0x00, 0xA4])

    assert (sw1, sw2) == (0x90, 0x00)
    assert len(card.conn.transmitted) == 1


def test_read_apdu_raises_on_error_status():
    card = _card()
    card.conn = ScriptedConnection([([], 0x6A, 0x82)])  # file not found

    with pytest.raises(RuntimeError):
        card._read_apdu([0x80, 0xB0])


def test_select_card_raises_when_select_rejected():
    card = _card()
    card.conn = ScriptedConnection([([], 0x6A, 0x82)])

    with pytest.raises(RuntimeError):
        card._select_card()
