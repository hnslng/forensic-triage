"""Tests for the bounded diagnostics ring buffer, handler and API (Alpha 70)."""

import logging
import threading
from pathlib import Path

import pytest

from forensic_triage import diagnostics as diag


@pytest.fixture(autouse=True)
def fresh_diagnostics(monkeypatch):
    monkeypatch.delenv(diag.LOG_BUFFER_ENV, raising=False)
    diag.reset_state()
    yield
    diag.reset_state()


def make_record(name="root", level=logging.INFO, msg="System läuft", args=(), pathname="/opt/web.py"):
    return logging.LogRecord(name, level, pathname, 1, msg, args, None)


def test_ring_buffer_drops_oldest_entries_beyond_maximum() -> None:
    ring = diag.LogRing(max_entries=3)
    for word in ("a", "b", "c", "d", "e"):
        ring.append(level="INFO", category="USB", message=word)
    assert [entry["message"] for entry in ring.since()[0]] == ["c", "d", "e"]


def test_ring_sequence_is_strictly_monotonic() -> None:
    ring = diag.LogRing()
    sequences = [ring.append(level="INFO", category="SCAN", message=str(index))["seq"] for index in range(10)]
    assert sequences == sorted(sequences)
    assert sequences == list(range(1, 11))


def test_ring_since_returns_only_newer_entries_in_order() -> None:
    ring = diag.LogRing()
    for index in range(5):
        ring.append(level="INFO", category="USB", message=str(index))
    entries, latest = ring.since(since=3, limit=10)
    assert [entry["seq"] for entry in entries] == [4, 5]
    assert latest == 5


def test_ring_initial_request_returns_newest_slice() -> None:
    ring = diag.LogRing()
    for index in range(8):
        ring.append(level="INFO", category="USB", message=f"n{index}")
    entries, _ = ring.since(limit=3)
    assert [entry["message"] for entry in entries] == ["n5", "n6", "n7"]


def test_ring_filters_level_and_category() -> None:
    ring = diag.LogRing()
    ring.append(level="DEBUG", category="ANDROID", message="detail")
    ring.append(level="WARNING", category="USB", message="warn")
    ring.append(level="INFO", category="ANDROID", message="info")
    entries, _ = ring.since(min_level="WARNING")
    assert [entry["level"] for entry in entries] == ["WARNING"]
    entries, _ = ring.since(category="android")
    assert [entry["message"] for entry in entries] == ["detail", "info"]


def test_ring_entries_demand_no_unbounded_growth() -> None:
    ring = diag.LogRing(max_entries=diag.LOG_BUFFER_MAX)
    for index in range(750):
        ring.append(level="INFO", category="SYSTEM", message=f"zeile {index}")
    assert len(ring._entries) == diag.LOG_BUFFER_MAX
    streamed, _ = ring.since(since=0, limit=diag.LOG_BUFFER_MAX)
    assert len(streamed) == diag.LOG_BUFFER_MAX


@pytest.mark.parametrize(
    ("value", "expected"),
    [(diag.LOG_BUFFER_CEILING, diag.LOG_BUFFER_CEILING), ("abc", diag.LOG_BUFFER_MAX), ("0", diag.LOG_BUFFER_MAX), (None, diag.LOG_BUFFER_MAX)],
)
def test_ring_size_is_configurable_with_ceiling(monkeypatch, value, expected) -> None:
    if value is not None:
        monkeypatch.setenv(diag.LOG_BUFFER_ENV, str(value))
    diag.reset_state()
    assert diag.buffer_size() == expected


def test_ring_append_is_thread_safe(monkeypatch) -> None:
    monkeypatch.setenv(diag.LOG_BUFFER_ENV, "10000")
    diag.reset_state()
    def writer(base):
        for offset in range(50):
            diag._append(level="INFO", category="USB", message=f"{base}-{offset}")
    threads = [threading.Thread(target=writer, args=(index,)) for index in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    entries, latest = diag.recent(limit=2000)
    sequences = {entry["seq"] for entry in entries}
    assert len(entries) == 400
    assert len(sequences) == 400
    assert latest == 400


def test_handler_keeps_normal_mode_clear_of_debug_records() -> None:
    ring = diag.LogRing()
    handler = diag.DiagHandler(ring)
    handler.emit(make_record())
    handler.emit(make_record(level=logging.DEBUG, msg="detail", args=()))
    assert [entry["message"] for entry in ring.since()[0]] == ["System läuft"]


def test_debug_mode_records_controlled_namespace_debug_records() -> None:
    ring = diag.LogRing()
    handler = diag.DiagHandler(ring)
    diag.set_mode("debug")
    handler.emit(make_record(name=diag.LOGGER_NAME, level=logging.DEBUG, msg="vendor=04e8"))
    handler.emit(make_record(name="urllib3.charset", level=logging.DEBUG, msg="fremd"))
    entries, _ = ring.since()
    assert [entry["message"] for entry in entries] == ["vendor=04e8"]
    assert entries[0]["category"] == "SYSTEM"


def test_handler_derives_category_from_explicit_and_module() -> None:
    ring = diag.LogRing()
    handler = diag.DiagHandler(ring)
    record = make_record(name=diag.LOGGER_NAME, msg="Strukturwert")
    record.diag_category = "ANDROID"
    handler.emit(record)
    handler.emit(make_record(pathname="/opt/android.py"))
    handler.emit(make_record(level=logging.ERROR, pathname="/opt/senseless.py"))
    entries, _ = ring.since()
    assert [entry["category"] for entry in entries] == ["ANDROID", "ANDROID", "ERROR"]


def test_handler_swallows_broken_sinks_and_payloads() -> None:
    class BrokenRing(diag.LogRing):
        def append(self, **kwargs):
            raise RuntimeError("kaputt")

    handler = diag.DiagHandler(BrokenRing())
    handler.emit(make_record())  # Darf nicht eskalieren.

    handler = diag.DiagHandler(diag.LogRing())
    record = make_record(args=("X", "Zusatz"))  # msg ohne Platzhalter: getMessage() wirft.
    handler.emit(record)  # Darf nicht eskalieren.
    record = make_record()
    record.diag_details = object()  # Kein verwertbares Details-Objekt.
    handler.emit(record)
    record = make_record()
    record.diag_details = {"vendor": "04e8", "exc": RuntimeError("alles kaputt")}
    handler.emit(record)
    entries, _ = handler.ring.since()
    assert len(entries) == 2
    assert entries[-1]["details"]["vendor"] == "04e8"
    assert "exc" not in entries[-1]["details"] or "kaputt" in str(entries[-1]["details"].get("exc"))


def test_details_are_bounded_and_sanitized() -> None:
    details = {f"key{index}": "x" * 400 for index in range(14)}
    details["nan"] = float("nan")
    cleaned = diag._clean_details(details)
    assert len(cleaned) == diag.DETAIL_KEYS_LIMIT + 1  # begrenzte Keys plus "_hinweis"
    assert cleaned["key0"] == "x" * diag.DETAIL_VALUE_LIMIT
    assert "nan" not in cleaned
    assert cleaned["_hinweis"] == "weitere Details unterdrückt"


def test_once_rate_limits_repeated_errors() -> None:
    assert diag.once("a", "ERROR", "Kaputt") is True
    assert diag.once("a", "ERROR", "Kaputt") is False
    assert diag.once("b", "ERROR", "Kaputt") is True


def test_once_cooldown_allows_repeat_after_window(monkeypatch) -> None:
    original_monotonic = diag.time.monotonic
    diag.once("a", "ERROR", "Kaputt")
    assert diag.once("a", "ERROR", "Kaputt") is False
    monkeypatch.setattr(diag.time, "monotonic", lambda: original_monotonic() + 61.0)
    assert diag.once("a", "ERROR", "Kaputt") is True


def test_change_logs_only_on_state_change() -> None:
    assert diag.change("k", "USB", "Zustand a", signature="a") is True
    assert diag.change("k", "USB", "Zustand alter Text", signature="a") is False
    assert diag.change("k", "USB", "Zustand b", signature="b") is True


def test_change_defers_debug_details_until_debug_mode(monkeypatch) -> None:
    diag.install(stream=False)
    assert diag.change("k", "ANDROID", "vendor=04e8", debug=True) is False
    assert diag.recent()[0] == []
    diag.set_mode("debug")
    assert diag.change("k", "ANDROID", "vendor=04e8", debug=True) is True
    entries, _ = diag.recent()
    assert entries and entries[-1]["category"] == "ANDROID"
    assert entries[-1]["level"] == "DEBUG"


def test_install_is_idempotent() -> None:
    diag.install(stream=False)
    root_handler_count = len(logging.getLogger().handlers)
    diag.install(stream=False)
    assert len(logging.getLogger().handlers) == root_handler_count


def test_recent_endpoint_delivers_entries_mode_and_latest(stub_diags=None) -> None:
    import forensic_triage.web as web

    handler = web.TriageHandler.__new__(web.TriageHandler)
    handler.path = "/api/logs/recent"
    responses = []
    handler._json = lambda status, body: responses.append((status, body))
    handler.do_GET()
    status, body = responses[0]
    assert status.value == 200
    assert set(body) == {"entries", "mode", "count", "latest"}
    assert body["mode"] in diag.MODES
    assert body["entries"] == []
    assert body["count"] == 0


@pytest.mark.parametrize("path", [
    "/api/logs/recent?since=abc",
    "/api/logs/recent?since=-1",
    "/api/logs/recent?limit=99999",
    "/api/logs/recent?category=galaxy",
    "/api/logs/recent?level=critical",
])
def test_recent_endpoint_validates_parameters(path) -> None:
    import forensic_triage.web as web

    handler = web.TriageHandler.__new__(web.TriageHandler)
    handler.path = path
    responses = []
    handler._json = lambda status, body: responses.append((status, body))
    handler.do_GET()
    assert responses[0][0].value == 400
    assert responses[0][1]["error"]


def test_logs_endpoint_campaign_timestamps_can_be_cursord() -> None:
    """Browser cursor poll (since) only produces newer entries (Kern PR-Notiz)."""
    entries, _ = diag.recent(since=0)
    assert entries == []
    first = diag._append(level="INFO", category="USB", message="früh")
    second = diag._append(level="INFO", category="USB", message="spät")
    streamed, latest = diag.recent(since=first["seq"], limit=200)
    assert [entry["seq"] for entry in streamed] == [second["seq"]]
    assert latest == second["seq"]
