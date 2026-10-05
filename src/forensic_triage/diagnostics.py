"""Bounded, RAM-only diagnostics view of TRIAGE//BOX application logging.

This module is a diagnostic instrument, not a second logging system: a custom
``logging.Handler`` feeds selected records of the existing Python logging into
a thread-safe in-memory ring buffer, which the local web console exposes
read-only through ``/api/logs/recent``. Nothing here is persisted to disk and
no handler failure may ever break scanning or the web service.
"""

from __future__ import annotations

import collections
import itertools
import logging
import math
import os
import threading
import time
from datetime import UTC, datetime
from typing import Any


CATEGORIES = ("SYSTEM", "USB", "ANDROID", "IPHONE", "SCAN", "UPDATE", "WEB", "CASE", "ERROR")
LEVEL_ORDER = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40}
MODES = ("normal", "debug")

# Ring size: default and ceiling keep memory strictly bounded. The ceiling is
# deliberately modest; the diagnostics view is a live instrument, not an
# archive. journalctl and the per-scan scan.log files remain the durable logs.
LOG_BUFFER_MAX = 500
LOG_BUFFER_CEILING = 2000
LOG_BUFFER_ENV = "FORENSIC_TRIAGE_DIAG_BUFFER_MAX"

MESSAGE_LIMIT = 600
DETAIL_KEYS_LIMIT = 12
DETAIL_KEY_LIMIT = 64
DETAIL_VALUE_LIMIT = 200
COOLDOWN_SECONDS = 60.0

LOGGER_NAME = "forensic-triage"

# Root-level records without an explicit diag_category derive their category
# from the emitting module. Everything unknown stays SYSTEM or becomes ERROR.
_CATEGORY_BY_MODULE = {
    "web": "WEB", "android": "ANDROID", "iphone": "IPHONE", "scanner": "SCAN",
    "scan_worker": "SCAN", "scan_process": "SCAN", "fast_inventory": "SCAN",
    "container_inventory": "SCAN", "partitions": "SCAN", "filesystem": "SCAN",
    "classifier": "SCAN", "crypto_rules": "SCAN", "reporting": "SCAN",
    "pdf_report": "SCAN", "statistics": "SCAN", "backup_detection": "SCAN",
    "offline_update": "UPDATE", "casefiles": "CASE", "commands": "SYSTEM",
    "settings": "SYSTEM", "keywords": "SYSTEM", "validation": "SYSTEM",
}

def _configure_size() -> int:
    try:
        requested = int(os.environ.get(LOG_BUFFER_ENV, ""))
    except ValueError:
        return LOG_BUFFER_MAX
    if requested <= 0:
        return LOG_BUFFER_MAX
    return min(requested, LOG_BUFFER_CEILING)


_LOGGER = logging.getLogger(LOGGER_NAME)
_RING_LOCK = threading.Lock()
_RING: collections.deque[dict[str, Any]] = collections.deque(maxlen=_configure_size())
_SEQUENCE = itertools.count(1)
_MODE = "normal"
_MODE_LOCK = threading.Lock()
_CHANGED: dict[str, str] = {}
_CHANGES_LOCK = threading.Lock()
_ONCE: dict[str, float] = {}
_ONCE_LOCK = threading.Lock()
_INSTALLED = False
_INSTALL_LOCK = threading.Lock()


def reset_state() -> None:
    """Reset buffer, trackers and mode; used by automated tests only."""
    global _RING, _SEQUENCE, _MODE, _INSTALLED
    with _RING_LOCK:
        _RING = collections.deque(maxlen=_configure_size())
        _SEQUENCE = itertools.count(1)
    with _MODE_LOCK:
        _MODE = "normal"
    with _CHANGES_LOCK:
        _CHANGED.clear()
    with _ONCE_LOCK:
        _ONCE.clear()
    _LOGGER.setLevel(logging.DEBUG)
    _INSTALLED = False


def buffer_size() -> int:
    return _RING.maxlen


def mode() -> str:
    return _MODE


def set_mode(value: str) -> str:
    """Switch the server-side diagnostics level between normal and debug."""
    global _MODE
    if value not in MODES:
        raise ValueError("Ungültiger Diagnosemodus.")
    with _MODE_LOCK:
        _MODE = value
    return _MODE


def latest_sequence() -> int:
    with _RING_LOCK:
        return _RING[-1]["seq"] if _RING else 0


class DiagHandler(logging.Handler):
    """Feed regular Python log records into the diagnostics ring buffer.

    Only conscious application logging is captured: INFO and above from every
    logger, plus DEBUG records from the controlled ``forensic-triage``
    namespace (recorded only while debug mode is active). The handler never
    raises and never logs about itself, so it cannot recurse or deadlock.

    ``ring=None`` marks the production handler that appends to the module
    singleton buffer; a passed :class:`LogRing` is used by tests.
    """

    def __init__(self, ring: "LogRing | None" = None) -> None:
        super().__init__(level=logging.NOTSET)
        self.ring = ring

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D102
        try:
            if getattr(record, "diag_silent", False):
                return
            if record.levelno >= logging.INFO:
                pass
            elif record.name == LOGGER_NAME and mode() == "debug":
                pass
            else:
                return
            message = str(record.getMessage())[:MESSAGE_LIMIT]
            details = _clean_details(getattr(record, "diag_details", None))
            category = _category_for(record)
            if self.ring is not None:
                self.ring.append(level=record.levelname, category=category, message=message, details=details)
            else:
                _append(level=record.levelname, category=category, message=message, details=details)
        except Exception:  # Never let logging diagnostics break the app.
            return


class LogRing:
    """Thread-safe bounded ring of structured diagnostic entries."""

    def __init__(self, max_entries: int = LOG_BUFFER_MAX) -> None:
        self._entries: collections.deque[dict[str, Any]] = collections.deque(
            maxlen=max(1, int(max_entries)),
        )
        self._sequence = itertools.count(1)
        self._lock = threading.Lock()

    def append(
        self, *, level: str, category: str, message: str, details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": str(level),
            "category": str(category),
            "message": str(message),
        }
        if details:
            entry["details"] = details
        with self._lock:
            entry["seq"] = next(self._sequence)
            self._entries.append(entry)
        return entry

    def since(
        self, since: int = 0, limit: int = 200,
        min_level: str | None = None, category: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return (entries newer than ``since`` ascending, newest known seq).

        An incremental request (``since`` > 0) returns the oldest matching
        entries first so a polling cursor advances step by step. A request
        without cursor returns the newest matching entries instead, so a
        freshly opened console shows the current situation.
        """
        floor = LEVEL_ORDER.get(str(min_level).upper(), 0) if min_level else 0
        wanted = str(category).upper() if category else None
        with self._lock:
            candidates = [entry for entry in self._entries if since < entry["seq"]]
        matching = [
            entry for entry in candidates
            if LEVEL_ORDER.get(entry["level"], 20) >= floor
            and (wanted is None or entry["category"] == wanted)
        ]
        bounded = max(1, limit)
        selected = matching[:bounded] if since > 0 else matching[-bounded:]
        with self._lock:
            newest = self._entries[-1]["seq"] if self._entries else 0
        return selected, newest


def _append(
    *, level: str, category: str, message: str, details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append to the module singleton ring in one short critical section."""
    entry: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
        "level": str(level),
        "category": str(category),
        "message": str(message),
    }
    if details:
        entry["details"] = details
    with _RING_LOCK:
        entry["seq"] = next(_SEQUENCE)
        _RING.append(entry)
    return entry


def _clean_details(details: Any) -> dict[str, Any] | None:
    """Bound and normalize detail payloads; never trust or crash on them."""
    try:
        if not isinstance(details, dict):
            return None
        cleaned: dict[str, Any] = {}
        for index, (raw_key, raw_value) in enumerate(details.items()):
            if index >= DETAIL_KEYS_LIMIT:
                cleaned["_hinweis"] = "weitere Details unterdrückt"
                break
            key = str(raw_key)[:DETAIL_KEY_LIMIT]
            if isinstance(raw_value, str):
                value: Any = raw_value[:DETAIL_VALUE_LIMIT]
            elif isinstance(raw_value, bool) or raw_value is None or isinstance(raw_value, int):
                value = raw_value
            elif isinstance(raw_value, float):
                value = raw_value if math.isfinite(raw_value) else str(raw_value)
            else:
                value = str(raw_value)[:DETAIL_VALUE_LIMIT]
            cleaned[key] = value
        return cleaned or None
    except Exception:
        return None


def _category_for(record: logging.LogRecord) -> str:
    explicit = str(getattr(record, "diag_category", "") or "")
    if explicit in CATEGORIES:
        return explicit
    if record.name == LOGGER_NAME or record.name.startswith(LOGGER_NAME + "."):
        return "SYSTEM"
    module = getattr(record, "module", "") or str(record.name or "").rsplit(".", 1)[-1]
    mapped = _CATEGORY_BY_MODULE.get(module)
    if mapped:
        return mapped
    if record.levelno >= logging.ERROR:
        return "ERROR"
    return "SYSTEM"


def _internal(level: int, category: str, message: str, details: dict[str, Any] | None) -> None:
    """Emit one structured event through the standard logging framework."""
    try:
        _LOGGER.log(
            level, str(message)[:MESSAGE_LIMIT],
            extra={
                "diag_category": category if category in CATEGORIES else "SYSTEM",
                "diag_details": _clean_details(details),
            },
        )
    except Exception:
        pass


def event(category: str, message: str, details: dict[str, Any] | None = None, *, level: str = "info") -> None:
    """Record one application event (INFO and above; visible in NORMAL mode)."""
    _internal(LEVEL_ORDER.get(level.upper(), 20), category, message, details)


def debug_event(category: str, message: str, details: dict[str, Any] | None = None) -> None:
    """Record one DEBUG-only diagnostic detail (kept only in debug mode)."""
    if mode() != "debug":
        return
    _internal(logging.DEBUG, category, message, details)


def once(
    key: str, category: str, message: str, details: dict[str, Any] | None = None,
    *, level: str = "warning", cooldown: float = COOLDOWN_SECONDS,
) -> bool:
    """Rate-limit identical conditions: first hit logs, repeats stay silent.

    Returns whether the message was emitted now. Repeated identical errors
    therefore appear once, then at most once per cooldown window.
    """
    now = time.monotonic()
    with _ONCE_LOCK:
        previous = _ONCE.get(key)
        _ONCE[key] = now
    if previous is not None and now - previous < cooldown:
        return False
    _internal(LEVEL_ORDER.get(level.upper(), 30), category, message, details)
    return True


def change(
    key: str, category: str, message: str, details: dict[str, Any] | None = None,
    *, level: str = "info", signature: str | None = None, debug: bool = False,
) -> bool:
    """Log one condition only when its state (signature) actually changed.

    While debug mode is off, DEBUG-only conditions (``debug=True``) stay
    silent and do not consume the change, so enabling debug mode shows the
    current state once.
    """
    fingerprint = signature if signature is not None else message
    if debug and mode() != "debug":
        return False
    with _CHANGES_LOCK:
        previous = _CHANGED.get(key)
        _CHANGED[key] = fingerprint
    if previous == fingerprint:
        return False
    if debug:
        debug_event(category, message, details)
    else:
        _internal(LEVEL_ORDER.get(level.upper(), 20), category, message, details)
    return True


def recent(
    since: int = 0, limit: int = 200, min_level: str | None = None, category: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Read-only copy for the web API; see :meth:`LogRing.since`."""
    floor = LEVEL_ORDER.get(str(min_level).upper(), 0) if min_level else 0
    wanted = str(category).upper() if category else None
    with _RING_LOCK:
        candidates = [entry for entry in _RING if since < entry["seq"]]
    matching = [
        entry for entry in candidates
        if LEVEL_ORDER.get(entry["level"], 20) >= floor
        and (wanted is None or entry["category"] == wanted)
    ]
    bounded = max(1, limit)
    selected = matching[:bounded] if since > 0 else matching[-bounded:]
    with _RING_LOCK:
        newest = _RING[-1]["seq"] if _RING else 0
    return selected, newest


def install(*, stream: bool = True) -> None:
    """Attach the diagnostics handler to the root logger, once per process.

    Also raises the root logger level to INFO so deliberately emitted
    application ``logging.info`` records reach the console view, and routes
    warnings and errors to stderr exactly as before, so journald keeps seeing
    them. Third-party DEBUG logging stays suppressed at the root logger.
    """
    global _INSTALLED
    with _INSTALL_LOCK:
        if _INSTALLED:
            return
        root = logging.getLogger()
        if any(isinstance(handler, DiagHandler) for handler in root.handlers):
            _INSTALLED = True
            return
        _LOGGER.setLevel(logging.DEBUG)
        root.setLevel(logging.INFO)
        root.addHandler(DiagHandler())
        if stream:
            stderr_handler = logging.StreamHandler()
            stderr_handler.setLevel(logging.WARNING)
            stderr_handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
            root.addHandler(stderr_handler)
        _INSTALLED = True
