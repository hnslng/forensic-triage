import csv
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from forensic_triage.period import evaluate_file_period, period_timezone_info, timestamp_coverage, validate_period
from forensic_triage.reporting import write_files_csv


@pytest.mark.parametrize(("start", "end", "valid"), [
    ("", "", True), ("2026-10-01", "", False), ("", "2026-10-01", False),
    ("2026-10-02", "2026-10-01", False), ("2026-10-01", "2026-10-01", True),
    ("2026-02-30", "2026-03-01", False),
])
def test_period_validation(start, end, valid):
    if valid:
        validate_period(start, end)
    else:
        with pytest.raises(ValueError):
            validate_period(start, end)


def test_bmca_matches_once_and_latest_type_is_preserved():
    day = lambda value: int(datetime.strptime(value, "%Y-%m-%d").timestamp())
    result = evaluate_file_period({"crtime": day("2026-09-30"), "mtime": day("2026-10-04"),
                                   "ctime": day("2026-10-05"), "atime": day("2026-10-05")},
                                  {"date_from": "2026-10-01", "date_to": "2026-10-05"})
    assert result == {"in_period": True, "period_matches": "M+C+A",
                      "latest_period_timestamp": day("2026-10-05"), "latest_period_timestamp_type": "C+A"}


def test_no_period_is_not_configured_and_invalid_timestamp_is_ignored():
    assert evaluate_file_period({"mtime": "invalid"}, None)["in_period"] is None
    assert evaluate_file_period({"mtime": "invalid"}, {"date_from": "2026-01-01", "date_to": "2026-01-02"}) == {
        "in_period": False, "period_matches": "", "latest_period_timestamp": None,
        "latest_period_timestamp_type": None,
    }


@pytest.mark.parametrize("field", ["crtime", "mtime", "ctime", "atime"])
def test_each_bmca_timestamp_counts_independently(field):
    stamp = datetime(2026, 7, 14, 12, tzinfo=ZoneInfo("Europe/Vienna")).timestamp()
    result = evaluate_file_period({field: stamp}, {"date_from": "2026-07-14", "date_to": "2026-07-14", "timezone": "Europe/Vienna"})
    assert result["in_period"] is True
    assert result["period_matches"] == {"crtime": "B", "mtime": "M", "ctime": "C", "atime": "A"}[field]


@pytest.mark.parametrize("stamp,expected", [
    (datetime(2026, 3, 28, 23, 59, 59, tzinfo=ZoneInfo("Europe/Vienna")).timestamp(), False),
    (datetime(2026, 3, 29, 0, 0, 0, tzinfo=ZoneInfo("Europe/Vienna")).timestamp(), True),
    (datetime(2026, 3, 29, 1, 59, 59, tzinfo=ZoneInfo("Europe/Vienna")).timestamp(), True),
    (datetime(2026, 3, 29, 3, 0, 0, tzinfo=ZoneInfo("Europe/Vienna")).timestamp(), True),
    (datetime(2026, 3, 30, 0, 0, 0, tzinfo=ZoneInfo("Europe/Vienna")).timestamp(), False),
    (datetime(2026, 10, 25, 2, 30, fold=0, tzinfo=ZoneInfo("Europe/Vienna")).timestamp(), True),
    (datetime(2026, 10, 25, 2, 30, fold=1, tzinfo=ZoneInfo("Europe/Vienna")).timestamp(), True),
])
def test_local_day_boundaries_and_dst(stamp, expected):
    result = evaluate_file_period({"mtime": stamp}, {"date_from": "2026-03-29", "date_to": "2026-03-29", "timezone": "Europe/Vienna"}) if stamp < datetime(2026, 10, 1, tzinfo=ZoneInfo("UTC")).timestamp() else evaluate_file_period({"mtime": stamp}, {"date_from": "2026-10-25", "date_to": "2026-10-25", "timezone": "Europe/Vienna"})
    assert result["in_period"] is expected


def test_utc_timezone_is_valid_and_coverage_matches_timestamp_evaluation():
    stamp = datetime(2026, 1, 1, tzinfo=ZoneInfo("UTC")).timestamp()
    files = [{"crtime": float("nan"), "mtime": float("inf"), "ctime": 1e100, "atime": stamp}]
    period = {"date_from": "2026-01-01", "date_to": "2026-01-01", "timezone": "UTC"}
    coverage = timestamp_coverage(files, period)
    assert coverage == {"files_total": 1, "files_with_any_timestamp": 1, "B_available": 0, "B_invalid": 1,
                        "M_available": 0, "M_invalid": 1, "C_available": 0, "C_invalid": 1,
                        "A_available": 1, "A_invalid": 0}
    assert evaluate_file_period(files[0], period)["period_matches"] == "A"


def test_vienna_winter_day_is_interpreted_in_standard_time():
    stamp = datetime(2026, 1, 15, 23, 30, tzinfo=ZoneInfo("Europe/Vienna")).timestamp()
    result = evaluate_file_period({"mtime": stamp}, {"date_from": "2026-01-15", "date_to": "2026-01-15", "timezone": "Europe/Vienna"})
    assert result["in_period"] is True


def test_period_start_and_inclusive_end_use_exact_local_midnights():
    zone = ZoneInfo("Europe/Vienna")
    period = {"date_from": "2026-03-28", "date_to": "2026-03-29", "timezone": "Europe/Vienna"}
    before = datetime(2026, 3, 27, 23, 59, 59, tzinfo=zone).timestamp()
    first = datetime(2026, 3, 28, 0, 0, 0, tzinfo=zone).timestamp()
    last = datetime(2026, 3, 29, 23, 59, 59, tzinfo=zone).timestamp()
    after = datetime(2026, 3, 30, 0, 0, 0, tzinfo=zone).timestamp()
    assert evaluate_file_period({"mtime": before}, period)["in_period"] is False
    assert evaluate_file_period({"mtime": first}, period)["in_period"] is True
    assert evaluate_file_period({"mtime": last}, period)["in_period"] is True
    assert evaluate_file_period({"mtime": after}, period)["in_period"] is False


def test_outside_missing_and_future_timestamp_do_not_match_or_become_latest():
    zone = ZoneInfo("UTC")
    outside = datetime(2026, 2, 1, tzinfo=zone).timestamp()
    start = datetime(2026, 1, 1, tzinfo=zone).timestamp()
    end = datetime(2026, 1, 31, 23, 59, 59, tzinfo=zone).timestamp()
    none = evaluate_file_period({"crtime": None, "mtime": outside, "ctime": "", "atime": "null"},
                               {"date_from": "2026-01-01", "date_to": "2026-01-31", "timezone": "UTC"})
    assert none["in_period"] is False
    assert none["period_matches"] == ""
    result = evaluate_file_period({"mtime": start, "ctime": end + 86400},
                                  {"date_from": "2026-01-01", "date_to": "2026-01-31", "timezone": "UTC"})
    assert result["latest_period_timestamp"] == start
    assert result["latest_period_timestamp_type"] == "M"


def test_timezone_resolver_accepts_utc_without_optional_dependency(monkeypatch):
    monkeypatch.setenv("TZ", "UTC")
    assert period_timezone_info() == {"timezone": "UTC", "timezone_source": "TZ", "timezone_reproducible": True}


def test_files_csv_keeps_period_fields(tmp_path):
    path = tmp_path / "files.csv"
    file_record = {"path": "evidence.txt", "atime": 1760000000, "mtime": 1760000000,
                   "ctime": 1760000001, "crtime": None, "in_period": True, "period_matches": "M+C+A",
                   "latest_period_timestamp": 1760000001, "latest_period_timestamp_type": "C"}
    write_files_csv(path, [file_record])
    with path.open(encoding="utf-8", newline="") as handle:
        saved = next(csv.DictReader(handle))
    assert saved["in_period"] == "True"
    assert saved["period_matches"] == "M+C+A"
    assert saved["latest_period_timestamp"] == "1760000001"
    assert saved["latest_period_timestamp_type"] == "C"
