# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest

import carekeeper_providers as cp
import lib.h59_ble as h59_ble_module
from carekeeper_retry import SubsystemRegistry
from lib.h59_ble.device import H59Device
from tests.fakes.fake_ble import FailNTimesThenSucceed, FakeSpO2Reader


@pytest.fixture
def provider():
    p = cp.RealCareKeeperProvider.__new__(cp.RealCareKeeperProvider)
    p.device_mac = "aa:bb:cc:dd:ee:ff"
    p.h59_device_name = "H59_D105"
    p.h59_device_address = "EC9C2DA6-F503-4660-0ABB-3ABFA92F9E5D"
    p.on_retry_attempt = None
    p.on_retry_giveup = None
    return p


def test_spo2_connect_retries_and_succeeds(provider, monkeypatch):
    connect_fn = FailNTimesThenSucceed(fail_times=2)
    monkeypatch.setattr(H59Device, "connect", connect_fn)
    monkeypatch.setattr(H59Device, "is_connected", True, raising=False)
    monkeypatch.setattr(H59Device, "disconnect", FailNTimesThenSucceed(fail_times=0))
    monkeypatch.setattr(h59_ble_module, "SpO2Reader", lambda device, timeout=60: FakeSpO2Reader(device, timeout, value=97))

    attempts = []
    provider.on_retry_attempt = lambda s, a, m: attempts.append((s, a, m))

    result = provider.measure_spo2()

    assert result == 97
    assert connect_fn.calls == 3
    assert attempts == [("spo2", 2, 3), ("spo2", 3, 3)]
    assert SubsystemRegistry.get("spo2").disabled is False


def test_spo2_connect_exhausts_and_disables(provider, monkeypatch):
    connect_fn = FailNTimesThenSucceed(fail_times=99)
    monkeypatch.setattr(H59Device, "connect", connect_fn)
    monkeypatch.setattr(H59Device, "is_connected", False, raising=False)

    with pytest.raises(RuntimeError):
        provider.measure_spo2()

    assert connect_fn.calls == 3
    assert SubsystemRegistry.get("spo2").disabled is True


def test_spo2_read_timeout_returns_none_raises_runtime_error(provider, monkeypatch):
    """Connect succeeds, but the read times out (returns None). This should
    raise once and must NOT re-trigger the connect-retry path again — read
    timeouts and connect failures are separate failure domains."""
    connect_fn = FailNTimesThenSucceed(fail_times=0)
    monkeypatch.setattr(H59Device, "connect", connect_fn)
    monkeypatch.setattr(H59Device, "is_connected", True, raising=False)
    monkeypatch.setattr(H59Device, "disconnect", FailNTimesThenSucceed(fail_times=0))
    monkeypatch.setattr(h59_ble_module, "SpO2Reader", lambda device, timeout=60: FakeSpO2Reader(device, timeout, value=None))

    with pytest.raises(RuntimeError):
        provider.measure_spo2()

    assert connect_fn.calls == 1
    assert SubsystemRegistry.get("spo2").disabled is False
