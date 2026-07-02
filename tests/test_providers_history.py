# -*- coding: utf-8 -*-
from __future__ import annotations

import carekeeper_providers as cp
from tests.fakes.fake_requests import RecordingGet, make_response


def _provider(monkeypatch):
    # Tests must not depend on the developer's local .env, so pin every
    # env-derived constant the history call reads to fixed values here.
    monkeypatch.setattr(cp, "TEST_HISTORY_PATIENT_ID_PARAM", "patient_id")
    monkeypatch.setattr(cp, "TEST_HISTORY_MAC_PARAM", "mac")
    monkeypatch.setattr(cp, "TEST_API_KEY_HEADER", "api-key")
    monkeypatch.setattr(cp, "TEST_API_KEY", "test-key")
    p = cp.RealCareKeeperProvider.__new__(cp.RealCareKeeperProvider)
    p.device_mac = "aa:bb:cc:dd:ee:ff"
    p.history_api_url = "https://example.test/health_history"
    return p


def test_get_measurement_history_includes_mac_param(monkeypatch):
    provider = _provider(monkeypatch)
    fake_get = RecordingGet(make_response(200, {"data": []}))
    monkeypatch.setattr(cp.requests, "get", fake_get)

    provider.get_measurement_history("1-2345-67890-12-3")

    assert len(fake_get.calls) == 1
    params = fake_get.calls[0]["params"]
    assert params["mac"] == "aa:bb:cc:dd:ee:ff"
    assert params["patient_id"] == "1-2345-67890-12-3"
    assert params["limit"] == 4


def test_get_measurement_history_sends_api_key_header(monkeypatch):
    provider = _provider(monkeypatch)
    fake_get = RecordingGet(make_response(200, {"data": []}))
    monkeypatch.setattr(cp.requests, "get", fake_get)

    provider.get_measurement_history("1-2345-67890-12-3")

    headers = fake_get.calls[0]["headers"]
    assert headers["api-key"] == "test-key"


def test_get_measurement_history_returns_empty_without_url(monkeypatch):
    provider = _provider(monkeypatch)
    provider.history_api_url = ""
    fake_get = RecordingGet(make_response(200, {"data": []}))
    monkeypatch.setattr(cp.requests, "get", fake_get)

    assert provider.get_measurement_history("1-2345-67890-12-3") == []
    assert fake_get.calls == []


def test_get_measurement_history_parses_records(monkeypatch):
    provider = _provider(monkeypatch)
    fake_get = RecordingGet(make_response(200, {"data": [
        {"measured_at": "24/06/69 12:00", "sys": 120, "dia": 78, "pulse": 70, "spo2": 98, "temperature": 36.5},
    ]}))
    monkeypatch.setattr(cp.requests, "get", fake_get)

    records = provider.get_measurement_history("1-2345-67890-12-3")

    assert len(records) == 1
    assert records[0].systolic == 120
    assert records[0].diastolic == 78
    assert records[0].pulse == 70
    assert records[0].spo2 == 98
    assert records[0].temperature == 36.5


def test_get_measurement_history_accepts_alternate_field_names(monkeypatch):
    provider = _provider(monkeypatch)
    fake_get = RecordingGet(make_response(200, {"records": [
        {"date": "25/06/69 09:30", "systolic": 118, "diastolic": 76, "pr_bpm": 68, "spo2": 97, "temp": 36.8},
    ]}))
    monkeypatch.setattr(cp.requests, "get", fake_get)

    records = provider.get_measurement_history("1-2345-67890-12-3")

    assert len(records) == 1
    assert records[0].measured_at == "25/06/69 09:30"
    assert records[0].systolic == 118
    assert records[0].diastolic == 76
    assert records[0].pulse == 68
    assert records[0].temperature == 36.8


def test_get_measurement_history_caps_at_four_records(monkeypatch):
    provider = _provider(monkeypatch)
    items = [
        {"measured_at": f"0{i}/06/69", "sys": 110 + i, "dia": 70, "pulse": 70, "spo2": 98, "temperature": 36.5}
        for i in range(6)
    ]
    fake_get = RecordingGet(make_response(200, {"data": items}))
    monkeypatch.setattr(cp.requests, "get", fake_get)

    records = provider.get_measurement_history("1-2345-67890-12-3")

    assert len(records) == 4


def test_get_measurement_history_skips_non_dict_items(monkeypatch):
    provider = _provider(monkeypatch)
    fake_get = RecordingGet(make_response(200, {"data": [
        "garbage",
        {"measured_at": "24/06/69", "sys": 120, "dia": 78, "pulse": 70, "spo2": 98, "temperature": 36.5},
    ]}))
    monkeypatch.setattr(cp.requests, "get", fake_get)

    records = provider.get_measurement_history("1-2345-67890-12-3")

    assert len(records) == 1
    assert records[0].systolic == 120


def test_get_measurement_history_handles_top_level_list(monkeypatch):
    provider = _provider(monkeypatch)
    fake_get = RecordingGet(make_response(200, [
        {"measured_at": "24/06/69", "sys": 120, "dia": 78, "pulse": 70, "spo2": 98, "temperature": 36.5},
    ]))
    monkeypatch.setattr(cp.requests, "get", fake_get)

    records = provider.get_measurement_history("1-2345-67890-12-3")

    assert len(records) == 1


def test_get_measurement_history_raises_on_non_2xx(monkeypatch):
    import pytest

    provider = _provider(monkeypatch)
    monkeypatch.setattr(cp.requests, "get", RecordingGet(make_response(500, {})))

    with pytest.raises(RuntimeError):
        provider.get_measurement_history("1-2345-67890-12-3")
