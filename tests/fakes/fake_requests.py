# -*- coding: utf-8 -*-
from __future__ import annotations

from unittest.mock import Mock


def make_response(status_code: int = 200, json_data=None):
    response = Mock()
    response.status_code = status_code
    response.json = lambda: json_data if json_data is not None else {}
    return response


class RecordingGet:
    """Drop-in replacement for `requests.get` that records every call's
    arguments and returns a fixed scripted response."""

    def __init__(self, response):
        self.response = response
        self.calls: list[dict] = []

    def __call__(self, url, params=None, headers=None, timeout=None):
        self.calls.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        return self.response


class RecordingPost:
    """Drop-in replacement for `requests.post`. Can raise a scripted
    exception (e.g. requests.exceptions.ConnectionError) to simulate a
    network drop mid-send."""

    def __init__(self, response=None, exception: Exception | None = None):
        self.response = response
        self.exception = exception
        self.calls: list[dict] = []

    def __call__(self, url, json=None, headers=None, timeout=None):
        self.calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        if self.exception is not None:
            raise self.exception
        return self.response
