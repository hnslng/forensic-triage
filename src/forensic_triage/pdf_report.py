"""Compact, printable case summary for field-triage documentation."""

from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from . import __version__


INK = colors.HexColor("#171a16")
MUTED = colors.HexColor("#60665d")
LINE = colors.HexColor("#aeb5a8")
ACCENT = colors.HexColor("#5f761f")
LIGHT = colors.HexColor("#edf1e8")
AMBER = colors.HexColor("#9a5b00")
RED = colors.HexColor("#9b2d27")


def format_bytes(value: Any) -> str:
    size = float(value or 0)
    units = ("B", "KB", "MB", "GB", "TB")
    unit = 0
    while size >= 1024 and unit < len(units) - 1:
        size /= 1024
        unit += 1
    decimals = 0 if unit == 0 else 1
    return f"{size:.{decimals}f} {units[unit]}".replace(".", ",")


def format_count(value: Any) -> str:
    return f"{int(value or 0):,}".replace(",", ".")


def format_timestamp(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "-"
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    return parsed.strftime("%d.%m.%Y %H:%M UTC")


def load_summary(root: Path, result_path: Any) -> dict[str, Any]:
    path = root / str(result_path) / "summary.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def rough_content(summary: Mapping[str, Any], limit: int = 4) -> str:
    categories = sorted(
        (
            (str(name), int(count or 0))
            for name, count in dict(summary.get("categories_by_count") or {}).items()
            if int(count or 0) > 0
        ),
        key=lambda item: (-item[1], item[0].casefold()),
    )
    if not categories:
        return "Keine kategorisierbaren Dateien"
    shown = categories[:limit]
    parts = [f"{name}: {format_count(count)}" for name, count in shown]
    remaining = sum(count for _, count in categories[limit:])
    if remaining:
        parts.append(f"Weitere: {format_count(remaining)}")
    return ", ".join(parts)


def decision_summary(row: Mapping[str, Any]) -> tuple[str, colors.Color]:
    decision = str(row.get("decision") or "open")
    labels = {
        "open": "ENTSCHEIDUNG OFFEN",
        "secure": "ZUR SICHERUNG AUSGEWÄHLT",
        "not_selected": "NICHT AUSGEWÄHLT",
        "review": "WEITERE PRÜFUNG",
    }
    reasons = {
        "no_indicators": "Keine fallbezogenen Indikatoren",
        "known_media": "Bekanntes Installations-/Systemmedium",
        "empty": "Leer / keine zugänglichen Dateien",
        "duplicate": "Duplikat eines anderen Mediums",
        "out_of_scope": "Außerhalb des Untersuchungsumfangs",
        "technical": "Technische Grobsichtung nicht möglich",
        "other": "Sonstige Begründung",
    }
    lines = [labels.get(decision, decision.upper())]
    evidence = str(row.get("evidence_number") or "").strip()
    if evidence:
        lines.append(f"Beweismittel: {evidence}")
    reason = reasons.get(str(row.get("reason_code") or ""), "")
    if reason:
        lines.append(reason)
    note = str(row.get("reason_note") or "").strip()
    if note:
        lines.append(note)
    color = ACCENT if decision == "secure" else AMBER if decision in {"review", "open"} else RED
    return "<br/>".join(html.escape(line) for line in lines), color


def operator_names(audit: Iterable[Mapping[str, Any]]) -> str:
    names: list[str] = []
    for event in audit:
        name = str(event.get("operator") or "").strip()
        if name and name not in names:
            names.append(name)
    return ", ".join(names) or "-"


def build_case_pdf(
    output_path: Path,
    case: Mapping[str, Any],
    media: Iterable[Mapping[str, Any]],
    audit: Iterable[Mapping[str, Any]],
    casefiles_root: Path,
) -> None:
    """Write a compact A4-landscape report, one table row per medium."""
    rows = list(media)
    audit_rows = list(audit)
    case_number = str(case["case_number"])
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=19, leading=22, textColor=INK, spaceAfter=3 * mm,
    )
    meta_label = ParagraphStyle(
        "MetaLabel", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=7.5, leading=9, textColor=MUTED,
    )
    meta_value = ParagraphStyle(
        "MetaValue", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=10, leading=12, textColor=INK,
    )
    cell = ParagraphStyle(
        "Cell", parent=styles["Normal"], fontName="Helvetica",
        fontSize=8.2, leading=10.2, textColor=INK, splitLongWords=True,
    )
    cell_bold = ParagraphStyle("CellBold", parent=cell, fontName="Helvetica-Bold")
    header = ParagraphStyle(
        "TableHeader", parent=cell, fontName="Helvetica-Bold",
        fontSize=7.5, leading=9, textColor=colors.white,
    )
    small = ParagraphStyle(
        "Small", parent=cell, fontSize=7.3, leading=9, textColor=MUTED,
    )

    def on_page(canvas, document) -> None:
        canvas.saveState()
        canvas.setTitle(f"TRIAGE//BOX Grobsichtungsbericht {case_number}")
        canvas.setAuthor("TRIAGE//BOX")
        canvas.setStrokeColor(LINE)
        canvas.line(12 * mm, 9 * mm, landscape(A4)[0] - 12 * mm, 9 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(12 * mm, 5.5 * mm, f"TRIAGE//BOX {__version__} - Metadaten-Grobsichtung")
        canvas.drawRightString(
            landscape(A4)[0] - 12 * mm, 5.5 * mm,
            f"Fall {case_number} - Seite {document.page}",
        )
        canvas.restoreState()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    story: list[Any] = [
        Paragraph("TRIAGE//BOX - GROBSICHTUNGSBERICHT", title_style),
    ]
    meta = Table(
        [
            [Paragraph("FALLNUMMER", meta_label), Paragraph("BEARBEITER", meta_label), Paragraph("ZEITRAUM", meta_label), Paragraph("DATENTRÄGER", meta_label)],
            [
                Paragraph(html.escape(case_number), meta_value),
                Paragraph(html.escape(operator_names(audit_rows)), meta_value),
                Paragraph(f"{html.escape(format_timestamp(case.get('created_at')))}<br/>{html.escape(format_timestamp(case.get('updated_at')))}", meta_value),
                Paragraph(str(len(rows)), meta_value),
            ],
        ],
        colWidths=[65 * mm, 55 * mm, 90 * mm, 45 * mm],
    )
    meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([
        meta,
        Spacer(1, 4 * mm),
        Paragraph(
            "Kompakte Übersicht der vor Ort durchgeführten Metadaten-Grobsichtungen. "
            "Die Kategorien beruhen auf Dateiendungen und sind keine Inhalts- oder Dateisignaturanalyse.",
            small,
        ),
        Spacer(1, 2.5 * mm),
    ])

    table_data: list[list[Any]] = [[
        Paragraph("SICHTUNG", header),
        Paragraph("DATENTRÄGER", header),
        Paragraph("GROBINHALT", header),
        Paragraph("ERGEBNIS / BEGRÜNDUNG", header),
    ]]
    for row in rows:
        summary = load_summary(casefiles_root, row.get("result_path"))
        sighting = html.escape(str(row.get("sighting_number") or "-"))
        scanned = html.escape(format_timestamp(row.get("scanned_at")))
        device_name = " ".join(
            part for part in (str(row.get("vendor") or "").strip(), str(row.get("model") or "").strip()) if part
        ) or "USB-Datenträger"
        serial = str(row.get("serial") or "nicht gemeldet")
        content = rough_content(summary)
        total_bytes = summary.get("total_file_bytes", 0)
        decision, decision_color = decision_summary(row)
        table_data.append([
            Paragraph(f"<b>{sighting}</b><br/>{scanned}", cell),
            Paragraph(
                f"<b>{html.escape(device_name)}</b><br/>Seriennummer: {html.escape(serial)}"
                f"<br/>Kapazität: {html.escape(format_bytes(row.get('size')))}",
                cell,
            ),
            Paragraph(
                f"<b>{html.escape(content)}</b><br/>"
                f"{format_count(row.get('file_count'))} Dateien, {format_count(row.get('directory_count'))} Ordner, "
                f"{html.escape(format_bytes(total_bytes))}, {format_count(row.get('keyword_matches'))} Stichworttreffer",
                cell,
            ),
            Paragraph(f"<font color='{decision_color.hexval()}'><b>{decision}</b></font>", cell_bold),
        ])
    if not rows:
        table_data.append([
            Paragraph("-", cell),
            Paragraph("Noch keine Datenträger erfasst", cell),
            Paragraph("-", cell),
            Paragraph("-", cell),
        ])

    media_table = Table(
        table_data,
        colWidths=[31 * mm, 59 * mm, 86 * mm, 97 * mm],
        repeatRows=1,
        hAlign="LEFT",
    )
    media_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("BOX", (0, 0), (-1, -1), 0.7, INK),
        ("INNERGRID", (0, 1), (-1, -1), 0.35, LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f7f4")]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([
        media_table,
        Spacer(1, 4 * mm),
        Paragraph(
            "NACHWEIS: Vollständige Metadaten-Dateilisten, Audit-Ereignisse und technische Scanunterlagen "
            "liegen in der lokalen Fallakte. Ihre SHA-256-Prüfsummen stehen in manifest.sha256.",
            small,
        ),
        Spacer(1, 2 * mm),
        Paragraph(
            "HINWEIS: Dieser Bericht dokumentiert eine Grobsichtung und keine abschließende forensische "
            "Inhaltsanalyse oder rechtliche beziehungsweise fachliche Sicherstellungsentscheidung.",
            small,
        ),
    ])

    document = SimpleDocTemplate(
        str(temporary), pagesize=landscape(A4),
        leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=12 * mm, bottomMargin=13 * mm,
        title=f"TRIAGE//BOX Grobsichtungsbericht {case_number}",
        author="TRIAGE//BOX",
    )
    try:
        document.build(story, onFirstPage=on_page, onLaterPages=on_page)
        temporary.replace(output_path)
    finally:
        if temporary.exists():
            temporary.unlink()
