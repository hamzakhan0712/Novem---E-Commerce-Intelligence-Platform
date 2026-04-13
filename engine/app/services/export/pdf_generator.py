"""
PDF Report Generator — Renders the structured report dict from
report_builder into a professional, branded PDF using ReportLab.
"""

import logging
import os
import tempfile
from app.services.currency.currency_helper import sym as _sym
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)

EXPORT_DIR = os.path.join(tempfile.gettempdir(), "novem_exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

# ── Font registration (Unicode-capable for ₹ rendering) ─────────
FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

_FONT_CANDIDATES = [
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
]

for _regular_path, _bold_path in _FONT_CANDIDATES:
    if os.path.exists(_regular_path) and os.path.exists(_bold_path):
        try:
            pdfmetrics.registerFont(TTFont("NovemSans", _regular_path))
            pdfmetrics.registerFont(TTFont("NovemSans-Bold", _bold_path))
            FONT_REGULAR = "NovemSans"
            FONT_BOLD = "NovemSans-Bold"
            break
        except Exception:
            logger.warning("Failed to register font %s", _regular_path)
else:
    logger.warning("No Unicode TTF font found — ₹ may not render correctly")

# ── Brand colors ─────────────────────────────────────────────────
NOVEM_GREEN = colors.HexColor("#52c41a")
NOVEM_DARK = colors.HexColor("#1a1a2e")
NOVEM_GRAY = colors.HexColor("#6b7280")
NOVEM_LIGHT = colors.HexColor("#f5f5f5")
WHITE = colors.white
BLACK = colors.black
RED = colors.HexColor("#ff4d4f")
ORANGE = colors.HexColor("#faad14")
BLUE = colors.HexColor("#1890ff")


# ── Styles ───────────────────────────────────────────────────────


def _build_styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "NovemTitle",
            parent=base["Title"],
            fontName=FONT_BOLD,
            fontSize=28,
            textColor=WHITE,
            alignment=TA_CENTER,
            spaceAfter=6 * mm,
        ),
        "subtitle": ParagraphStyle(
            "NovemSubtitle",
            parent=base["Normal"],
            fontName=FONT_REGULAR,
            fontSize=13,
            textColor=colors.HexColor("#d0d0d0"),
            alignment=TA_CENTER,
            spaceAfter=4 * mm,
        ),
        "section_heading": ParagraphStyle(
            "SectionHeading",
            parent=base["Heading1"],
            fontName=FONT_BOLD,
            fontSize=16,
            textColor=NOVEM_DARK,
            spaceBefore=10 * mm,
            spaceAfter=4 * mm,
            borderPadding=(0, 0, 2, 0),
        ),
        "body": ParagraphStyle(
            "NovemBody",
            parent=base["Normal"],
            fontName=FONT_REGULAR,
            fontSize=10,
            textColor=NOVEM_DARK,
            leading=14,
            spaceAfter=3 * mm,
        ),
        "body_bold": ParagraphStyle(
            "NovemBodyBold",
            parent=base["Normal"],
            fontName=FONT_BOLD,
            fontSize=10,
            textColor=NOVEM_DARK,
            leading=14,
            spaceAfter=3 * mm,
        ),
        "bullet": ParagraphStyle(
            "NovemBullet",
            parent=base["Normal"],
            fontName=FONT_REGULAR,
            fontSize=10,
            textColor=NOVEM_DARK,
            leading=14,
            leftIndent=12,
            spaceAfter=2 * mm,
            bulletIndent=0,
        ),
        "small": ParagraphStyle(
            "NovemSmall",
            parent=base["Normal"],
            fontName=FONT_REGULAR,
            fontSize=8,
            textColor=NOVEM_GRAY,
            leading=10,
        ),
        "kpi_value": ParagraphStyle(
            "KpiValue",
            parent=base["Normal"],
            fontName=FONT_BOLD,
            fontSize=18,
            textColor=NOVEM_DARK,
            alignment=TA_CENTER,
        ),
        "kpi_label": ParagraphStyle(
            "KpiLabel",
            parent=base["Normal"],
            fontName=FONT_REGULAR,
            fontSize=9,
            textColor=NOVEM_GRAY,
            alignment=TA_CENTER,
        ),
        "kpi_change_pos": ParagraphStyle(
            "KpiChangePos",
            parent=base["Normal"],
            fontName=FONT_BOLD,
            fontSize=10,
            textColor=NOVEM_GREEN,
            alignment=TA_CENTER,
        ),
        "kpi_change_neg": ParagraphStyle(
            "KpiChangeNeg",
            parent=base["Normal"],
            fontName=FONT_BOLD,
            fontSize=10,
            textColor=RED,
            alignment=TA_CENTER,
        ),
        "footer": ParagraphStyle(
            "NovemFooter",
            parent=base["Normal"],
            fontName=FONT_REGULAR,
            fontSize=7,
            textColor=NOVEM_GRAY,
            alignment=TA_RIGHT,
        ),
    }


# ── Page templates ───────────────────────────────────────────────


def _cover_page(canvas, doc):
    """Draw the cover page background."""
    canvas.saveState()
    w, h = A4
    # Dark gradient background
    canvas.setFillColor(NOVEM_DARK)
    canvas.rect(0, 0, w, h, fill=1, stroke=0)
    # Accent bar at top
    canvas.setFillColor(NOVEM_GREEN)
    canvas.rect(0, h - 8 * mm, w, 8 * mm, fill=1, stroke=0)
    # Accent bar at bottom
    canvas.rect(0, 0, w, 4 * mm, fill=1, stroke=0)
    canvas.restoreState()


def _body_page(canvas, doc):
    """Draw body page header and footer."""
    canvas.saveState()
    w, h = A4
    # Top accent line
    canvas.setStrokeColor(NOVEM_GREEN)
    canvas.setLineWidth(2)
    canvas.line(1.5 * cm, h - 1.2 * cm, w - 1.5 * cm, h - 1.2 * cm)
    # Header text
    canvas.setFont(FONT_BOLD, 8)
    canvas.setFillColor(NOVEM_GRAY)
    canvas.drawString(1.5 * cm, h - 1 * cm, "NOVEM — Business Intelligence Report")
    # Footer
    canvas.setFont(FONT_REGULAR, 7)
    canvas.setFillColor(NOVEM_GRAY)
    canvas.drawRightString(w - 1.5 * cm, 1 * cm, f"Page {doc.page}")
    canvas.drawString(1.5 * cm, 1 * cm, f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    canvas.restoreState()


# ── Main generator ───────────────────────────────────────────────


def generate_pdf(report: dict) -> str:
    """Render the report dict into a PDF file. Returns the file path."""
    meta = report.get("meta", {})
    store_id = meta.get("store_id", "unknown")
    mode = meta.get("mode", "technical")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"novem_report_{store_id[:8]}_{mode}_{ts}.pdf"
    filepath = os.path.join(EXPORT_DIR, filename)

    styles = _build_styles()
    w, h = A4
    margin = 1.5 * cm

    cover_frame = Frame(margin, 4 * cm, w - 2 * margin, h - 10 * cm, id="cover")
    body_frame = Frame(margin, 1.8 * cm, w - 2 * margin, h - 3.5 * cm, id="body")

    doc = BaseDocTemplate(
        filepath,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
    )
    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[cover_frame], onPage=_cover_page),
        PageTemplate(id="body", frames=[body_frame], onPage=_body_page),
    ])

    elements: list = []

    # ── Cover page ───────────────────────────────────────────
    elements.append(Spacer(1, 6 * cm))
    elements.append(Paragraph("NOVEM", styles["title"]))
    elements.append(Paragraph("Business Intelligence Report", styles["subtitle"]))

    mode_label = "CEO Brief" if mode == "ceo" else "Technical Analysis"
    period = meta.get("period", "30d")
    gen_at = meta.get("generated_at", "")[:10]
    score = meta.get("health_score", 0)
    score_label = meta.get("health_label", "")

    elements.append(Spacer(1, 2 * cm))
    elements.append(Paragraph(f"Report Type: {mode_label}", styles["subtitle"]))
    elements.append(Paragraph(f"Period: {period}  |  Health Score: {score:.0f}/100 ({score_label})", styles["subtitle"]))
    elements.append(Paragraph(f"Generated: {gen_at}", styles["subtitle"]))

    elements.append(NextPageTemplate("body"))
    elements.append(PageBreak())

    # ── Executive summary ────────────────────────────────────
    _add_section(elements, report.get("executive_summary", {}), styles)

    # ── KPI overview ─────────────────────────────────────────
    kpi_section = report.get("kpi_overview", {})
    elements.append(Paragraph(kpi_section.get("title", "KPI Overview"), styles["section_heading"]))
    _add_kpi_cards(elements, kpi_section.get("metrics", []), styles)

    # ── Root cause analysis ──────────────────────────────────
    rca = report.get("root_cause_analysis", {})
    _add_section(elements, rca, styles)
    drivers = rca.get("drivers", [])
    if drivers:
        _add_driver_table(elements, drivers, styles, _sym(store_id))

    # ── Key problems ─────────────────────────────────────────
    problems_section = report.get("key_problems", {})
    elements.append(Paragraph(problems_section.get("title", "Key Problems"), styles["section_heading"]))
    problems = problems_section.get("problems", [])
    if problems:
        _add_problem_table(elements, problems, styles)
    else:
        elements.append(Paragraph("No critical problems detected this period.", styles["body"]))

    # ── Recommendations ──────────────────────────────────────
    rec_section = report.get("recommendations", {})
    elements.append(Paragraph(rec_section.get("title", "Recommended Actions"), styles["section_heading"]))
    rec_items = rec_section.get("actions", [])
    if rec_items:
        _add_recommendation_table(elements, rec_items, styles)
        summary = rec_section.get("summary", "")
        if summary:
            elements.append(Spacer(1, 2 * mm))
            elements.append(Paragraph(f"<b>{summary}</b>", styles["body_bold"]))
    else:
        elements.append(Paragraph("No specific recommendations at this time.", styles["body"]))

    # ── Forecast ─────────────────────────────────────────────
    _add_section(elements, report.get("forecast", {}), styles)
    fc_metrics = report.get("forecast", {}).get("metrics", [])
    if fc_metrics:
        _add_forecast_table(elements, fc_metrics, styles)

    # ── Customer health ──────────────────────────────────────
    _add_section(elements, report.get("customer_health", {}), styles)

    # ── Product performance ──────────────────────────────────
    _add_section(elements, report.get("product_performance", {}), styles)

    # ── Sentiment ────────────────────────────────────────────
    _add_section(elements, report.get("sentiment_overview", {}), styles)

    # ── Health breakdown ─────────────────────────────────────
    health_section = report.get("health_components", {})
    if health_section.get("components"):
        elements.append(Paragraph(health_section.get("title", "Health Breakdown"), styles["section_heading"]))
        _add_health_table(elements, health_section["components"], styles, meta.get("mode", "technical"))

    doc.build(elements)
    logger.info("PDF report generated: %s", filepath)
    return filepath


# ── Component renderers ──────────────────────────────────────────


def _add_section(elements: list, section: dict, styles: dict):
    """Add a simple section with title and paragraphs."""
    title = section.get("title", "")
    paragraphs = section.get("paragraphs", [])
    if title:
        elements.append(Paragraph(title, styles["section_heading"]))
    for p in paragraphs:
        elements.append(Paragraph(p, styles["body"]))


def _add_kpi_cards(elements: list, metrics: list, styles: dict):
    """Render KPI metrics as a table grid of styled cards."""
    if not metrics:
        return

    rows = []
    for m in metrics:
        chg = m.get("change_pct", 0)
        chg_style = styles["kpi_change_pos"] if chg >= 0 else styles["kpi_change_neg"]
        arrow = "▲" if chg > 0 else "▼" if chg < 0 else "—"

        cell = [
            Paragraph(m["label"], styles["kpi_label"]),
            Spacer(1, 1 * mm),
            Paragraph(str(m["value"]), styles["kpi_value"]),
            Paragraph(f"{arrow} {abs(chg):.1f}%", chg_style),
            Spacer(1, 1 * mm),
            Paragraph(m.get("explanation", ""), styles["small"]),
        ]
        rows.append(cell)

    # Arrange in 2x2 grid
    table_data = []
    for i in range(0, len(rows), 2):
        row_pair = rows[i: i + 2]
        while len(row_pair) < 2:
            row_pair.append([Spacer(1, 1)])
        table_data.append(row_pair)

    col_w = (A4[0] - 3 * cm) / 2
    table = Table(table_data, colWidths=[col_w, col_w])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("BOX", (0, 0), (0, -1), 0.5, colors.HexColor("#e0e0e0")),
        ("BOX", (1, 0), (1, -1), 0.5, colors.HexColor("#e0e0e0")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e8e8e8")),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fafafa")),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 4 * mm))


def _add_driver_table(elements: list, drivers: list, styles: dict, currency_sym: str = "₹"):
    """Render revenue drivers as a formatted table."""
    header = [
        Paragraph("<b>Driver</b>", styles["small"]),
        Paragraph("<b>Impact</b>", styles["small"]),
        Paragraph("<b>Direction</b>", styles["small"]),
        Paragraph("<b>Detail</b>", styles["small"]),
    ]
    data = [header]
    for d in drivers[:5]:
        impact = d.get("impact", 0)
        impact_color = NOVEM_GREEN if impact > 0 else RED
        data.append([
            Paragraph(d.get("driver", ""), styles["body"]),
            Paragraph(f"<font color='{impact_color}'>{currency_sym}{abs(impact):,.0f}</font>", styles["body"]),
            Paragraph("↑" if d.get("direction") == "up" else "↓", styles["body"]),
            Paragraph(d.get("detail", ""), styles["small"]),
        ])

    col_widths = [3.5 * cm, 2.5 * cm, 1.5 * cm, 9.5 * cm]
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NOVEM_LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 3 * mm))


def _add_problem_table(elements: list, problems: list, styles: dict):
    """Render problems as a severity-colored table."""
    severity_colors = {"high": RED, "medium": ORANGE, "low": BLUE}

    header = [
        Paragraph("<b>Severity</b>", styles["small"]),
        Paragraph("<b>Problem</b>", styles["small"]),
        Paragraph("<b>Details</b>", styles["small"]),
    ]
    data = [header]
    for p in problems[:8]:
        sev = p.get("severity", "medium")
        sev_color = severity_colors.get(sev, NOVEM_GRAY)
        data.append([
            Paragraph(f"<font color='{sev_color}'><b>{sev.upper()}</b></font>", styles["body"]),
            Paragraph(p.get("title", ""), styles["body"]),
            Paragraph(p.get("description", ""), styles["small"]),
        ])

    col_widths = [2 * cm, 5.5 * cm, 9.5 * cm]
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NOVEM_LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 3 * mm))


def _add_recommendation_table(elements: list, actions: list, styles: dict):
    """Render actions as a ranked table with potential impact."""
    header = [
        Paragraph("<b>#</b>", styles["small"]),
        Paragraph("<b>Action</b>", styles["small"]),
        Paragraph("<b>Potential</b>", styles["small"]),
        Paragraph("<b>Effort</b>", styles["small"]),
    ]
    data = [header]
    for a in actions:
        data.append([
            Paragraph(str(a.get("rank", "")), styles["body"]),
            Paragraph(f"<b>{a.get('action', '')}</b><br/>{a.get('description', '')}", styles["body"]),
            Paragraph(f"<font color='{NOVEM_GREEN}'><b>{a.get('potential', '—')}</b></font>", styles["body"]),
            Paragraph(a.get("effort", "").title(), styles["body"]),
        ])

    col_widths = [1 * cm, 10 * cm, 3 * cm, 3 * cm]
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NOVEM_LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 3 * mm))


def _add_forecast_table(elements: list, metrics: list, styles: dict):
    """Render forecast metric overview as a compact table."""
    header = [
        Paragraph("<b>Metric</b>", styles["small"]),
        Paragraph("<b>Trend</b>", styles["small"]),
        Paragraph("<b>Change</b>", styles["small"]),
    ]
    data = [header]
    for m in metrics:
        chg = m.get("change_pct", 0)
        trend = m.get("trend", "")
        trend_arrow = "↑" if trend == "up" else "↓" if trend == "down" else "→"
        chg_color = NOVEM_GREEN if chg > 0 else RED if chg < 0 else NOVEM_GRAY
        data.append([
            Paragraph(m.get("metric", ""), styles["body"]),
            Paragraph(f"{trend_arrow} {trend.title()}", styles["body"]),
            Paragraph(f"<font color='{chg_color}'>{chg:+.1f}%</font>", styles["body"]),
        ])

    col_widths = [6 * cm, 5 * cm, 6 * cm]
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NOVEM_LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 3 * mm))


def _add_health_table(elements: list, components: list, styles: dict, mode: str):
    """Render health score components."""
    if mode == "ceo":
        header = [
            Paragraph("<b>Area</b>", styles["small"]),
            Paragraph("<b>Score</b>", styles["small"]),
            Paragraph("<b>Status</b>", styles["small"]),
        ]
        data = [header]
        for c in components:
            score = c.get("score", 0)
            score_color = NOVEM_GREEN if score >= 70 else ORANGE if score >= 40 else RED
            data.append([
                Paragraph(c.get("label", ""), styles["body"]),
                Paragraph(f"<font color='{score_color}'><b>{score:.0f}</b></font>", styles["body"]),
                Paragraph(c.get("status", ""), styles["body"]),
            ])
        col_widths = [6 * cm, 3 * cm, 8 * cm]
    else:
        header = [
            Paragraph("<b>Component</b>", styles["small"]),
            Paragraph("<b>Score</b>", styles["small"]),
            Paragraph("<b>Weight</b>", styles["small"]),
            Paragraph("<b>Detail</b>", styles["small"]),
        ]
        data = [header]
        for c in components:
            score = c.get("score", 0)
            score_color = NOVEM_GREEN if score >= 70 else ORANGE if score >= 40 else RED
            data.append([
                Paragraph(c.get("label", ""), styles["body"]),
                Paragraph(f"<font color='{score_color}'><b>{score:.0f}</b></font>", styles["body"]),
                Paragraph(str(c.get("weight", "")), styles["body"]),
                Paragraph(c.get("detail", ""), styles["small"]),
            ])
        col_widths = [4 * cm, 2 * cm, 2 * cm, 9 * cm]

    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NOVEM_LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0e0e0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)
