# -*- coding: utf-8 -*-
"""Unit tests for RealCareKeeperProvider.send_data (POST measurement upload)."""
from __future__ import annotations

import pytest

import carekeeper_providers as cp
from tests.fakes.fake_requests import RecordingPost, make_response


def _provider(monkeypatch):
    # Pin env-derived constants so tests never depend on a local .env file.
    monkeypatch.setattr(cp, "TEST_API_KEY_HEADER", "api-key")
    monkeypatch.setattr(cp, "TEST_API_KEY", "test-key")
    p = cp.RealCareKeeperProvider.__new__(cp.RealCareKeeperProvider)
    p.api_url = "https://example.test/add_health"
    return p


def test_send_data_posts_payload_as_json(monkeypatch):
    provider = _provider(monkeypatch)
    fake_post = RecordingPost(make_response(200, {}))
    monkeypatch.setattr(cp.requests, "post", fake_post)
    payload = {"cid": "1234567890123", "sys": 120, "dia": 80, "pulse": 72, "spo2": 98}

    assert provider.send_data(payload) is True
    assert len(fake_post.calls) == 1
    assert fake_post.calls[0]["url"] == "https://example.test/add_health"
    assert fake_post.calls[0]["json"] == payload


def test_send_data_sends_api_key_header(monkeypatch):
    provider = _provider(monkeypatch)
    fake_post = RecordingPost(make_response(200, {}))
    monkeypatch.setattr(cp.requests, "post", fake_post)

    provider.send_data({"cid": "1234567890123"})

    headers = fake_post.calls[0]["headers"]
    assert headers["api-key"] == "test-key"
    assert headers["Content-Type"] == "application/json"


def test_send_data_omits_api_key_header_when_unset(monkeypatch):
    provider = _provider(monkeypatch)
    monkeypatch.setattr(cp, "TEST_API_KEY", "")
    fake_post = RecordingPost(make_response(200, {}))
    monkeypatch.setattr(cp.requests, "post", fake_post)

    provider.send_data({"cid": "1234567890123"})

    assert "api-key" not in fake_post.calls[0]["headers"]


def test_send_data_accepts_any_2xx_status(monkeypatch):
    provider = _provider(monkeypatch)
    fake_post = RecordingPost(make_response(201, {}))
    monkeypatch.setattr(cp.requests, "post", fake_post)

    assert provider.send_data({"cid": "1234567890123"}) is True


def test_send_data_raises_on_server_rejection(monkeypatch):
    provider = _provider(monkeypatch)
    fake_post = RecordingPost(make_response(500, {}))
    monkeypatch.setattr(cp.requests, "post", fake_post)

    with pytest.raises(RuntimeError):
        provider.send_data({"cid": "1234567890123"})


def test_send_data_raises_on_client_error_status(monkeypatch):
    provider = _provider(monkeypatch)
    fake_post = RecordingPost(make_response(401, {}))
    monkeypatch.setattr(cp.requests, "post", fake_post)

    with pytest.raises(RuntimeError):
        provider.send_data({"cid": "1234567890123"})


def test_send_data_raises_when_api_url_not_configured(monkeypatch):
    provider = _provider(monkeypatch)
    provider.api_url = ""
    fake_post = RecordingPost(make_response(200, {}))
    monkeypatch.setattr(cp.requests, "post", fake_post)

    with pytest.raises(RuntimeError):
        provider.send_data({"cid": "1234567890123"})
    assert fake_post.calls == []


def test_send_data_propagates_network_exception(monkeypatch):
    provider = _provider(monkeypatch)
    fake_post = RecordingPost(exception=cp.requests.exceptions.ConnectionError("network down"))
    monkeypatch.setattr(cp.requests, "post", fake_post)

    with pytest.raises(cp.requests.exceptions.ConnectionError):
        provider.send_data({"cid": "1234567890123"})
