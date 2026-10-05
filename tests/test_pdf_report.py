from pathlib import Path

from reportlab.platypus import Paragraph, Table

from forensic_triage import pdf_report


def test_pdf_report_includes_current_and_historical_period_snapshots(tmp_path, monkeypatch):
    captured = []

    def collect(item):
        if isinstance(item, Paragraph):
            captured.append(item.getPlainText())
        elif isinstance(item, Table):
            for row in item._cellvalues:
                for cell in row:
                    collect(cell)

    class Document:
        def __init__(self, filename, **_kwargs):
            self.filename = Path(filename)

        def build(self, story, **_kwargs):
            for item in story:
                collect(item)
            self.filename.write_bytes(b"%PDF-test")

    monkeypatch.setattr(pdf_report, "SimpleDocTemplate", Document)
    pdf_report.build_case_pdf(
        tmp_path / "case-report.pdf",
        {"case_number": "FALL-1", "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-02T00:00:00Z",
         "date_from": "2026-01-01", "date_to": "2026-01-31", "period_timezone": "Europe/Vienna"},
        [{"sighting_number": "SICHT-001", "scanned_at": "2026-01-02T12:00:00Z", "device_path": "/dev/sdb",
          "vendor": "USB", "model": "Drive", "serial": "S", "size": 10, "file_count": 4,
          "directory_count": 1, "keyword_matches": 0, "duration_seconds": 1, "period_date_from": "2025-12-01",
          "period_date_to": "2025-12-31", "period_timezone": "UTC", "period_file_count": 2,
          "result_path": "missing", "decision": "open"}],
        [], tmp_path,
    )
    output = " ".join(captured)
    assert "AKTUELLER FALLZEITRAUM" in output
    assert "2026-01-01 – 2026-01-31" in output
    assert "Fallzeitraum beim Scan: 2025-12-01 – 2025-12-31 · UTC" in output
    assert "2 / 4 im Zeitraum" in output
