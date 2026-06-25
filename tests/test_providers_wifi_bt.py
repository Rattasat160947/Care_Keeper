# -*- coding: utf-8 -*-
from __future__ import annotations

import subprocess

import pytest

import carekeeper_providers as cp
from carekeeper_retry import SubsystemRegistry


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setattr(cp.RealCareKeeperProvider, "__init__", lambda self: None)
    p = cp.RealCareKeeperProvider()
    p.device_mac = "aa:bb:cc:dd:ee:ff"
    p.api_url = cp.TEST_API_URL
    p.history_api_url = cp.TEST_HISTORY_API_URL
    p.on_retry_attempt = None
    p.on_retry_giveup = None
    return p


def _subprocess_factory(fail_times: int, success_return=None, exc_cls=subprocess.CalledProcessError):
    calls = {"n": 0}

    def fake_run(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] <= fail_times:
            if exc_cls is subprocess.CalledProcessError:
                raise exc_cls(1, args[0], output="", stderr="fake nmcli failure")
            raise exc_cls("fake failure")
        return success_return

    fake_run.calls = calls
    return fake_run


def test_connect_wifi_retries_and_succeeds(provider, monkeypatch):
    fake_run = _subprocess_factory(2, success_return=None)
    monkeypatch.setattr(cp.subprocess, "run", fake_run)

    attempts = []
    provider.on_retry_attempt = lambda s, a, m: attempts.append((s, a, m))

    ok = provider.connect_wifi("SomeSSID", "password")
    assert ok is True
    assert fake_run.calls["n"] == 3
    assert attempts == [("wifi", 2, 3), ("wifi", 3, 3)]
    assert SubsystemRegistry.get("wifi").disabled is False


def test_connect_wifi_exhausts_and_disables(provider, monkeypatch):
    fake_run = _subprocess_factory(99)
    monkeypatch.setattr(cp.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError):
        provider.connect_wifi("SomeSSID")

    assert fake_run.calls["n"] == 3
    assert SubsystemRegistry.get("wifi").disabled is True
    assert provider.get_device_status().wifi_disabled is True


def test_scan_wifi_networks_retry_and_disable(provider, monkeypatch):
    calls = {"n": 0}

    def fake_check_output(*args, **kwargs):
        calls["n"] += 1
        raise subprocess.CalledProcessError(1, args[0])

    monkeypatch.setattr(cp.subprocess, "check_output", fake_check_output)

    with pytest.raises(RuntimeError):
        provider.scan_wifi_networks()
    assert calls["n"] == 3
    assert SubsystemRegistry.get("wifi").disabled is True


def test_connect_bluetooth_retry_and_disable(provider, monkeypatch):
    calls = {"n": 0}

    def fake_run(*args, **kwargs):
        calls["n"] += 1
        if "connect" in args[0] and kwargs.get("check"):
            raise subprocess.CalledProcessError(1, args[0], output="", stderr="fail")
        return None

    monkeypatch.setattr(cp.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError):
        provider.connect_bluetooth("AA:BB:CC:DD:EE:FF")
    assert SubsystemRegistry.get("bluetooth").disabled is True


def test_scan_bluetooth_devices_retry_and_disable(provider, monkeypatch):
    def fake_run(*args, **kwargs):
        return None

    def fake_check_output(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0])

    monkeypatch.setattr(cp.subprocess, "run", fake_run)
    monkeypatch.setattr(cp.subprocess, "check_output", fake_check_output)

    with pytest.raises(RuntimeError):
        provider.scan_bluetooth_devices()
    assert SubsystemRegistry.get("bluetooth").disabled is True


def test_wifi_status_check_not_retried(provider, monkeypatch):
    """Regression guard: the 6s-poll status check must never be wrapped in
    retry_with_notify, or it would stall the UI poll for several seconds
    during an outage."""
    calls = {"n": 0}

    def fake_check_output(*args, **kwargs):
        calls["n"] += 1
        raise subprocess.CalledProcessError(1, args[0])

    monkeypatch.setattr(cp.subprocess, "check_output", fake_check_output)
    monkeypatch.setattr(cp.sys, "platform", "linux")

    result = provider._is_wifi_connected()
    assert result is False
    assert calls["n"] == 1


def test_bluetooth_status_check_not_retried(provider, monkeypatch):
    calls = {"n": 0}

    def fake_check_output(*args, **kwargs):
        calls["n"] += 1
        raise subprocess.CalledProcessError(1, args[0])

    monkeypatch.setattr(cp.subprocess, "check_output", fake_check_output)

    result = provider._is_bluetooth_connected()
    assert result is False
    assert calls["n"] == 1
