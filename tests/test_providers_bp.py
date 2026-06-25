# -*- coding: utf-8 -*-
from __future__ import annotations

import serial
import pytest

import carekeeper_providers as cp
from carekeeper_retry import SubsystemRegistry
from tests.fakes.fake_serial import FakeSerialFactory


@pytest.fixture
def provider():
    p = cp.RealCareKeeperProvider.__new__(cp.RealCareKeeperProvider)
    p.device_mac = "aa:bb:cc:dd:ee:ff"
    p.bp_port = "/dev/fake-port"
    p.on_retry_attempt = None
    p.on_retry_giveup = None
    return p


def test_bp_connect_retries_on_serial_exception_then_succeeds(provider, monkeypatch):
    factory = FakeSerialFactory(fail_times=2, lines=["SYS:120,DIA:80,PUL:70", "READY"])
    monkeypatch.setattr("lib.bp_monitor.serial.Serial", factory)

    result = provider.measure_blood_pressure()

    assert factory.calls == 3
    assert result.systolic == 120
    assert result.diastolic == 80
    assert result.pulse == 70
    assert SubsystemRegistry.get("bp_monitor").disabled is False


def test_bp_connect_exhausts_and_disables(provider, monkeypatch):
    factory = FakeSerialFactory(fail_times=99)
    monkeypatch.setattr("lib.bp_monitor.serial.Serial", factory)

    # connect() propagates serial.SerialException as-is (lib/bp_monitor.py is
    # left unchanged per the plan); retry_with_notify re-raises the original
    # exception type once attempts are exhausted, it doesn't wrap it.
    with pytest.raises(serial.SerialException):
        provider.measure_blood_pressure()

    assert factory.calls == 3
    assert SubsystemRegistry.get("bp_monitor").disabled is True


def test_bp_measure_timeout_is_not_retried(provider, monkeypatch):
    """Connect succeeds but the device never reports a result/READY line
    (simulated timeout). measure_blood_pressure should raise once, with no
    extra connect-retry attempts — only the connect step is retried, not a
    timed-out measurement (which can already take up to 120s)."""
    factory = FakeSerialFactory(fail_times=0, lines=[])
    monkeypatch.setattr("lib.bp_monitor.serial.Serial", factory)

    import lib.bp_monitor as bp_monitor_module
    monkeypatch.setattr(bp_monitor_module.BPMonitor, "measure", lambda self, blocking=True: None)

    with pytest.raises(RuntimeError):
        provider.measure_blood_pressure()

    assert factory.calls == 1
    assert SubsystemRegistry.get("bp_monitor").disabled is False
