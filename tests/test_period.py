from datetime import datetime

import pytest

from forensic_triage.period import evaluate_file_period, validate_period


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
