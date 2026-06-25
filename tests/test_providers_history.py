# -*- coding: utf-8 -*-
from __future__ import annotations

import carekeeper_providers as cp
from tests.fakes.fake_requests import RecordingGet, make_response


def _provider():
    p = cp.RealCareKeeperProvider.__new__(cp.RealCareKeeperProvider)
    p.device_mac = "aa:bb:cc:dd:ee:ff"
    p.history_api_url = cp.TEST_HISTORY_API_URL
    return p


def test_get_measurement_history_includes_mac_param(monkeypatch):
    provider = _provider()
    fake_get = RecordingGet(make_response(200, {"data": []}))
    monkeypatch.setattr(cp.requests, "get", fake_get)

    provider.get_measurement_history("1-2345-67890-12-3")

    assert len(fake_get.calls) == 1
    params = fake_get.calls[0]["params"]
    assert params["mac"] == "aa:bb:cc:dd:ee:ff"
    assert params[cp.TEST_HISTORY_PATIENT_ID_PARAM] == "1-2345-67890-12-3"
    assert params["limit"] == 4


def test_get_measurement_history_parses_records(monkeypatch):
    provider = _provider()
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


def test_get_measurement_history_raises_on_non_2xx(monkeypatch):
    import pytest

    provider = _provider()
    monkeypatch.setattr(cp.requests, "get", RecordingGet(make_response(500, {})))

    with pytest.raises(RuntimeError):
        provider.get_measurement_history("1-2345-67890-12-3")
