# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest

import carekeeper_ui as ui_module
from carekeeper_queue import SubmissionQueue
from tests.fakes.fake_provider import FakeFailingProvider


@pytest.fixture
def window(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(ui_module, "SubmissionQueue", lambda: SubmissionQueue(db_path=tmp_path / "queue.db"))
    provider = FakeFailingProvider()
    win = ui_module.CareKeeperWindow(provider, mode_name="Test")
    qtbot.addWidget(win)
    # Stop the background drain worker so it doesn't race with the
    # assertions below — each test exercises _submit_data's own immediate
    # send path deterministically.
    win.queue_worker.stop()
    win.queue_worker.join(timeout=2)
    yield win


def _set_full_vitals(window) -> None:
    window.vitals.systolic = 120
    window.vitals.diastolic = 80
    window.vitals.pulse = 70
    window.vitals.spo2 = 98


def test_submit_data_enqueues_before_send_attempt(window):
    _set_full_vitals(window)
    window._submit_data()
    # Enqueue is synchronous (local disk write) and happens before the
    # background ProviderTask even starts, so this is true immediately.
    assert window.submission_queue.count_pending() == 1


def test_submit_data_success_path_clears_queue_row(window, qtbot):
    _set_full_vitals(window)
    window._submit_data()
    qtbot.waitUntil(lambda: window.submission_queue.count_pending() == 0, timeout=3000)
    assert window.provider.sent_payloads[0]["mac"] == window.provider.device_mac


def test_submit_data_failure_path_leaves_row_for_background_worker(window, qtbot):
    window.provider.send_data_exception = RuntimeError("network down")
    _set_full_vitals(window)
    window._submit_data()
    qtbot.waitUntil(lambda: window.btn_finish.isEnabled(), timeout=3000)
    # Data stays queued for the background worker — the operator is not
    # blocked waiting for the network per the confirmed UX decision.
    assert window.submission_queue.count_pending() == 1
