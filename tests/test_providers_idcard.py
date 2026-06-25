# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass

import pytest

import carekeeper_providers as cp
from carekeeper_retry import SubsystemRegistry
from lib.thaiidcard.card import ThaiIDCard


@dataclass
class _FakeCardInfo:
    cid: str = "1-2345-67890-12-3"
    th_name: str = "นายทดสอบ"
    en_name: str = "Mr. Test"
    birth_date: str = "1 มกราคม 2530"
    address: str = "123 ถนนทดสอบ"


@pytest.fixture
def provider():
    p = cp.RealCareKeeperProvider.__new__(cp.RealCareKeeperProvider)
    p.device_mac = "aa:bb:cc:dd:ee:ff"
    p.on_retry_attempt = None
    p.on_retry_giveup = None
    return p


class _FailNTimesThenSucceed:
    def __init__(self, fail_times: int, result):
        self.fail_times = fail_times
        self.result = result
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("fake card read failure")
        return self.result


def test_read_patient_retries_and_succeeds(provider, monkeypatch):
    read_fn = _FailNTimesThenSucceed(2, _FakeCardInfo())
    monkeypatch.setattr(ThaiIDCard, "read", lambda self: read_fn())

    attempts = []
    provider.on_retry_attempt = lambda s, a, m: attempts.append((s, a, m))

    result = provider.read_patient()

    assert result.cid == "1-2345-67890-12-3"
    assert read_fn.calls == 3
    assert attempts == [("idcard", 2, 3), ("idcard", 3, 3)]
    assert SubsystemRegistry.get("idcard").disabled is False


def test_read_patient_exhausts_and_disables(provider, monkeypatch):
    read_fn = _FailNTimesThenSucceed(99, _FakeCardInfo())
    monkeypatch.setattr(ThaiIDCard, "read", lambda self: read_fn())

    with pytest.raises(RuntimeError):
        provider.read_patient()

    assert read_fn.calls == 3
    assert SubsystemRegistry.get("idcard").disabled is True
