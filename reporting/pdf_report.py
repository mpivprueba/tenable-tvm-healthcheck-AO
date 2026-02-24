import os
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, Image, KeepTogether
)

MPIV_NAVY  = colors.HexColor("#1B3A6B")
MPIV_BLUE  = colors.HexColor("#2E5FA3")
MPIV_LIGHT = colors.HexColor("#EBF0F8")
MPIV_GRAY  = colors.HexColor("#F4F6F9")
MPIV_DARK  = colors.HexColor("#1A1A2E")
MPIV_WHITE = colors.white
MPIV_ACCENT= colors.HexColor("#4A90D9")
SEV_CRITICAL = colors.HexColor("#C62828")
SEV_HIGH     = colors.HexColor("#EF6C00")
SEV_MEDIUM   = colors.HexColor("#F9A825")
SEV_LOW      = colors.HexColor("#2E7D32")

PAGE_W, PAGE_H = A4
MARGIN = 2 * cm


class MPIVDocTemplate(SimpleDocTemplate):
    def __init__(self, filename, logo_path, customer_name, engagement_id, **kwargs):
        super().__init__(filename, **kwargs)
        self.logo_path = logo_path
        self.customer_name = customer_name
        self.engagement_id = engagement_id

    def afterPage(self):
        c = self.canv
        page_num = self.page
        # Top bar
        c.setFillColor(MPIV_NAVY)
        c.rect(0, PAGE_H - 1.1*cm, PAGE_W, 1.1*cm, fill=1, stroke=0)
        if page_num > 1 and self.logo_path and os.path.exists(self.logo_path):
            c.drawImage(self.logo_path, MARGIN, PAGE_H - 1.0*cm,
                        width=2.4*cm, height=0.8*cm,
                        preserveAspectRatio=True, mask='auto')
        if page_num > 1:
            c.setFillColor(MPIV_WHITE)
            c.setFont("Helvetica", 7.5)
            c.drawRightString(PAGE_W - MARGIN, PAGE_H - 0.65*cm,
                f"Tenable TVM Health Check  |  {self.customer_name}  |  CONFIDENTIAL")
        # Bottom bar
        c.setFillColor(MPIV_NAVY)
        c.rect(0, 0, PAGE_W, 0.9*cm, fill=1, stroke=0)
        c.setFillColor(MPIV_WHITE)
        c.setFont("Helvetica", 7)
        c.drawString(MARGIN, 0.3*cm, f"MPIV Partners  |  {self.engagement_id}")
        c.drawRightString(PAGE_W - MARGIN, 0.3*cm, f"Page {page_num}")
        c.setStrokeColor(MPIV_ACCENT)
        c.setLineWidth(1.5)
        c.line(0, PAGE_H - 1.1*cm, PAGE_W, PAGE_H - 1.1*cm)


def _S(name, **kw):
    return ParagraphStyle(name, **kw)


STYLES = {
    "cover_company": _S("cc", fontName="Helvetica-Bold", fontSize=11,
        textColor=MPIV_WHITE, alignment=TA_CENTER, leading=14),
    "cover_title": _S("ct", fontName="Helvetica-Bold", fontSize=26,
        textColor=MPIV_WHITE, alignment=TA_CENTER, leading=32, spaceAfter=6),
    "cover_sub": _S("cs", fontName="Helvetica", fontSize=14,
        textColor=colors.HexColor("#A8C4E0"), alignment=TA_CENTER, leading=20),
    "cover_meta_label": _S("cml", fontName="Helvetica-Bold", fontSize=9,
        textColor=MPIV_NAVY),
    "cover_meta_value": _S("cmv", fontName="Helvetica", fontSize=9,
        textColor=MPIV_DARK),
    "section_title": _S("st", fontName="Helvetica-Bold", fontSize=14,
        textColor=MPIV_NAVY, spaceBefore=18, spaceAfter=8, leading=18),
    "subsection": _S("ss", fontName="Helvetica-Bold", fontSize=10,
        textColor=MPIV_BLUE, spaceBefore=10, spaceAfter=4),
    "body": _S("body", fontName="Helvetica", fontSize=9.5,
        textColor=MPIV_DARK, leading=15, spaceAfter=6, alignment=TA_JUSTIFY),
    "body_center": _S("bc", fontName="Helvetica", fontSize=9,
        textColor=MPIV_DARK, leading=13, alignment=TA_CENTER),
    "table_header": _S("th", fontName="Helvetica-Bold", fontSize=8.5,
        textColor=MPIV_WHITE, alignment=TA_CENTER),
    "table_cell": _S("tc", fontName="Helvetica", fontSize=8.5,
        textColor=MPIV_DARK, leading=12),
    "finding_title": _S("ft", fontName="Helvetica-Bold", fontSize=9,
        textColor=MPIV_NAVY, leading=12),
    "roadmap_item": _S("ri", fontName="Helvetica", fontSize=8.5,
        textColor=MPIV_DARK, leading=13, spaceAfter=3),
    "next_steps": _S("ns", fontName="Helvetica", fontSize=9.5,
        textColor=MPIV_DARK, leading=16, spaceAfter=4),
    "footer_note": _S("fn", fontName="Helvetica-Oblique", fontSize=8,
        textColor=colors.HexColor("#888888"), alignment=TA_CENTER),
}


def _divider():
    return HRFlowable(width="100%", thickness=1.5, color=MPIV_NAVY,
                      spaceAfter=8, spaceBefore=4)


class PDFReportGenerator:
    def __init__(self, summary, logo_path=None):
        self.summary = summary
        self.logo_path = logo_path
        try:
            from config.settings import settings
            self.output_dir = Path(settings.REPORT_OUTPUT_DIR)
        except Exception:
            self.output_dir = Path("./reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = str(self.output_dir /
                   f"MPIV_HealthCheck_{self.summary.engagement_id}_{ts}.pdf")
        doc = MPIVDocTemplate(
            path,
            logo_path=self.logo_path,
            customer_name=self.summary.customer_name,
            engagement_id=self.summary.engagement_id,
            pagesize=A4,
            leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=1.5*cm, bottomMargin=1.5*cm,
        )
        story = []
        story += self._cover()
        story.append(PageBreak())
        story += self._toc()
        story.append(PageBreak())
        story += self._exec_summary()
        story += self._maturity()
        story.append(PageBreak())
        story += self._findings()
        story.append(PageBreak())
        story += self._roadmap()
        story.append(PageBreak())
        story += self._next_steps()
        doc.build(story)
        try:
            from loguru import logger
            logger.info(f"PDF generated: {path}")
        except Exception:
            print(f"PDF generated: {path}")
        return path

    # ── COVER ─────────────────────────────────────────────────────────────────
    def _cover(self):
        els = []
        logo_cell = ""
        if self.logo_path and os.path.exists(self.logo_path):
            img = Image(self.logo_path, width=4*cm, height=4*cm)
            img.hAlign = "CENTER"
            logo_cell = img

        top = Table([[logo_cell or Paragraph("MPIV PARTNERS", STYLES["cover_company"])]],
                    colWidths=[PAGE_W - 2*MARGIN])
        top.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), MPIV_NAVY),
            ("ALIGN",         (0,0),(-1,-1), "CENTER"),
            ("TOPPADDING",    (0,0),(-1,-1), 30),
            ("BOTTOMPADDING", (0,0),(-1,-1), 30),
        ]))
        els.append(top)

        title_band = Table([
           [Paragraph("TENABLE VULNERABILITY MANAGEMENT", STYLES["cover_company"])],
           [Paragraph("Health Check", STYLES["cover_title"])],
           [Paragraph(self.summary.customer_name, STYLES["cover_sub"])],
        ], colWidths=[PAGE_W - 2*MARGIN])
        title_band.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), MPIV_BLUE),
            ("ALIGN",         (0,0),(-1,-1), "CENTER"),
            ("TOPPADDING",    (0,0),(-1,-1), 12),
            ("BOTTOMPADDING", (0,0),(-1,-1), 12),
        ]))
        els.append(title_band)
        els.append(Spacer(1, 0.8*cm))

        s = self.summary
        score_color = ("#2E7D32" if s.maturity_score >= 3.5
                       else "#F9A825" if s.maturity_score >= 2.5 else "#C62828")
        meta_rows = [
            ["Engagement ID",   s.engagement_id],
            ["Assessment Date", s.assessment_date.strftime("%B %d, %Y")],
            ["Prepared by",     "MPIV Partners — Professional Services"],
            ["Classification",  "CONFIDENTIAL"],
            ["Maturity Level",
             f'<font color="{score_color}"><b>{s.maturity_level.value} ({s.maturity_score}/5.0)</b></font>'],
        ]
        meta_data = [[Paragraph(r[0], STYLES["cover_meta_label"]),
                      Paragraph(r[1], STYLES["cover_meta_value"])] for r in meta_rows]
        meta_t = Table(meta_data, colWidths=[5*cm, PAGE_W - 2*MARGIN - 5*cm])
        meta_t.setStyle(TableStyle([
            ("ROWBACKGROUNDS",(0,0),(-1,-1), [MPIV_WHITE, MPIV_LIGHT]),
            ("GRID",          (0,0),(-1,-1), 0.3, colors.HexColor("#C8D8F0")),
            ("TOPPADDING",    (0,0),(-1,-1), 7),
            ("BOTTOMPADDING", (0,0),(-1,-1), 7),
            ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ]))
        els.append(meta_t)
        els.append(Spacer(1, 0.8*cm))

        kpi_w = (PAGE_W - 2*MARGIN) / 5
        kpi = Table([[
            Paragraph(f"<b>{s.total_assets}</b><br/>Total Assets", STYLES["body_center"]),
            Paragraph(f"<b>{s.authenticated_scans_pct:.0f}%</b><br/>Auth. Coverage", STYLES["body_center"]),
            Paragraph(f"<b>{s.scanner_health_pct:.0f}%</b><br/>Scanner Health", STYLES["body_center"]),
            Paragraph(f'<b><font color="#C62828">{len(s.critical_findings)}</font></b><br/>Critical', STYLES["body_center"]),
            Paragraph(f"<b>{len(s.findings)}</b><br/>Total Findings", STYLES["body_center"]),
        ]], colWidths=[kpi_w]*5)
        kpi.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), MPIV_NAVY),
            ("TEXTCOLOR",     (0,0),(-1,-1), MPIV_WHITE),
            ("ALIGN",         (0,0),(-1,-1), "CENTER"),
            ("TOPPADDING",    (0,0),(-1,-1), 12),
            ("BOTTOMPADDING", (0,0),(-1,-1), 12),
            ("LINEAFTER",     (0,0),(-2,-1), 0.5, colors.HexColor("#3A5A9B")),
        ]))
        els.append(kpi)
        els.append(Spacer(1, 0.5*cm))
        els.append(Paragraph(
            f"Confidential — Prepared exclusively for {s.customer_name}. "
            "Do not distribute without written authorization.",
            STYLES["footer_note"]))
        return els

    # ── TOC ───────────────────────────────────────────────────────────────────
    def _toc(self):
        els = [Spacer(1, 1.5*cm)]
        els.append(Paragraph("Table of Contents", STYLES["section_title"]))
        els.append(_divider())
        for num, title in [
            ("1.", "Executive Summary"),
            ("2.", "Maturity Assessment"),
            ("3.", "Detailed Findings"),
            ("4.", "Remediation Roadmap (30-60-90 Days)"),
            ("5.", "Next Steps & Document Acceptance"),
        ]:
            row = Table([[Paragraph(num, STYLES["body"]),
                          Paragraph(title, STYLES["body"])]],
                        colWidths=[1.2*cm, PAGE_W - 2*MARGIN - 1.2*cm])
            row.setStyle(TableStyle([
                ("TOPPADDING",    (0,0),(-1,-1), 5),
                ("BOTTOMPADDING", (0,0),(-1,-1), 5),
                ("LINEBELOW",     (0,0),(-1,-1), 0.3, colors.HexColor("#CCCCCC")),
            ]))
            els.append(row)
        return els

    # ── EXECUTIVE SUMMARY ─────────────────────────────────────────────────────
    def _exec_summary(self):
        els = [Paragraph("1. Executive Summary", STYLES["section_title"]), _divider()]
        narrative = self.summary.executive_narrative or self._default_narrative()
        for para in narrative.split("\n\n"):
            if para.strip():
                els.append(Paragraph(para.strip(), STYLES["body"]))
        return els

    def _default_narrative(self):
        s = self.summary
        return (
            f"MPIV Partners conducted a Tenable Vulnerability Management Health Check "
            f"for {s.customer_name} on {s.assessment_date.strftime('%B %d, %Y')}. "
            f"The assessment evaluated the organization's VM program across five key dimensions: "
            f"scanner health, credential coverage, asset lifecycle management, tagging governance, "
            f"and scan policy adherence.\n\n"
            f"The program achieved a maturity score of {s.maturity_score}/5.0, classified as "
            f"<b>{s.maturity_level.value}</b>. Of the {len(s.findings)} findings identified, "
            f"{len(s.critical_findings)} are Critical and {len(s.high_findings)} are High severity, "
            f"requiring immediate attention. Authenticated scan coverage stands at "
            f"{s.authenticated_scans_pct:.1f}%, well below the industry benchmark of 90%+, "
            f"meaning the organization may be detecting fewer than 40% of actual vulnerabilities.\n\n"
            f"MPIV Partners recommends a structured 90-day remediation roadmap beginning with "
            f"quick-win items achievable within 30 days. Strategic and long-term roadmap items "
            f"should be addressed in subsequent phases with dedicated project sponsorship and "
            f"executive visibility."
        )

    # ── MATURITY ──────────────────────────────────────────────────────────────
    def _maturity(self):
        els = [Spacer(1, 0.4*cm),
               Paragraph("2. Maturity Assessment", STYLES["section_title"]), _divider()]
        s = self.summary

        levels = [
            ("1.0-1.9", "Initial",    "#C62828"),
            ("2.0-2.9", "Developing", "#EF6C00"),
            ("3.0-3.9", "Defined",    "#F9A825"),
            ("4.0-4.9", "Managed",    "#388E3C"),
            ("5.0",     "Optimized",  "#1565C0"),
        ]
        gauge_cells = []
        gauge_style = [
            ("ALIGN",   (0,0),(-1,-1), "CENTER"),
            ("TOPPADDING",    (0,0),(-1,-1), 10),
            ("BOTTOMPADDING", (0,0),(-1,-1), 10),
        ]
        for i, (rng, label, hx) in enumerate(levels):
            is_cur = s.maturity_level.value == label
            marker = ">" if is_cur else ""
            gauge_cells.append(Paragraph(
                f"<b>{marker} {label}</b><br/>{rng}",
                ParagraphStyle("g", fontName="Helvetica-Bold" if is_cur else "Helvetica",
                    fontSize=8 if not is_cur else 9,
                    textColor=MPIV_WHITE, alignment=TA_CENTER, leading=12)
            ))
            gauge_style.append(("BACKGROUND", (i,0),(i,0), colors.HexColor(hx)))
            if is_cur:
                gauge_style.append(("BOX", (i,0),(i,0), 2.5, MPIV_WHITE))

        col_w = (PAGE_W - 2*MARGIN) / 5
        gauge = Table([gauge_cells], colWidths=[col_w]*5)
        gauge.setStyle(TableStyle(gauge_style))
        els.append(gauge)
        els.append(Spacer(1, 0.4*cm))

        score_color = ("#2E7D32" if s.maturity_score >= 3.5
                       else "#F9A825" if s.maturity_score >= 2.5 else "#C62828")
        metrics = [
            ["Metric", "Value", "Benchmark", "Status"],
            ["Maturity Score",
             f'<font color="{score_color}"><b>{s.maturity_score}/5.0</b></font>',
             ">=3.5", "OK" if s.maturity_score >= 3.5 else "FAIL"],
            ["Total Assets", str(s.total_assets), "-", "-"],
            ["Authenticated Coverage", f"{s.authenticated_scans_pct:.1f}%",
             ">=90%", "OK" if s.authenticated_scans_pct >= 90 else "FAIL"],
            ["Scanner Health", f"{s.scanner_health_pct:.1f}%",
             ">=95%", "OK" if s.scanner_health_pct >= 95 else "FAIL"],
            ["Critical Findings", str(len(s.critical_findings)),
             "0", "OK" if not s.critical_findings else "FAIL"],
            ["Total Findings", str(len(s.findings)), "-", "-"],
        ]
        m_data = [[Paragraph(str(c), STYLES["table_header" if r == 0 else "table_cell"])
                   for c in row] for r, row in enumerate(metrics)]
        m_t = Table(m_data, colWidths=[6.5*cm, 3*cm, 3*cm, 2.5*cm], repeatRows=1)
        m_t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,0), MPIV_NAVY),
            ("TEXTCOLOR",     (0,0),(-1,0), MPIV_WHITE),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [MPIV_WHITE, MPIV_GRAY]),
            ("GRID",          (0,0),(-1,-1), 0.3, colors.HexColor("#C8D8F0")),
            ("ALIGN",         (1,0),(-1,-1), "CENTER"),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0),(-1,-1), 7),
            ("BOTTOMPADDING", (0,0),(-1,-1), 7),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ]))
        els.append(m_t)
        return els

    # ── FINDINGS ──────────────────────────────────────────────────────────────
    def _findings(self):
        els = [Paragraph("3. Detailed Findings", STYLES["section_title"]), _divider()]
        s = self.summary
        sev_order = {"critical":0, "high":1, "medium":2, "low":3}
        findings = sorted(s.findings, key=lambda f: sev_order.get(f.severity.value, 9))
        sev_colors_map = {"critical": SEV_CRITICAL, "high": SEV_HIGH,
                          "medium": SEV_MEDIUM, "low": SEV_LOW}

        from collections import Counter
        counts = Counter(f.severity.value for f in findings)
        cw = (PAGE_W - 2*MARGIN) / 4
        count_t = Table([[
            Paragraph(f'<b><font color="#C62828">{counts.get("critical",0)}</font></b><br/><font size="7">Critical</font>', STYLES["body_center"]),
            Paragraph(f'<b><font color="#EF6C00">{counts.get("high",0)}</font></b><br/><font size="7">High</font>', STYLES["body_center"]),
            Paragraph(f'<b><font color="#F9A825">{counts.get("medium",0)}</font></b><br/><font size="7">Medium</font>', STYLES["body_center"]),
            Paragraph(f'<b><font color="#2E7D32">{counts.get("low",0)}</font></b><br/><font size="7">Low</font>', STYLES["body_center"]),
        ]], colWidths=[cw]*4)
        count_t.setStyle(TableStyle([
            ("BACKGROUND", (0,0),(-1,-1), MPIV_LIGHT),
            ("ALIGN",      (0,0),(-1,-1), "CENTER"),
            ("TOPPADDING", (0,0),(-1,-1), 10),
            ("BOTTOMPADDING",(0,0),(-1,-1), 10),
            ("BOX",        (0,0),(-1,-1), 0.5, colors.HexColor("#C8D8F0")),
        ]))
        els.append(count_t)
        els.append(Spacer(1, 0.4*cm))

        # Summary table
        rows = [["ID", "Severity", "Category", "Title", "Effort"]]
        for f in findings:
            rows.append([f.id, f.severity.value.upper(), f.category.value, f.title, f.effort.upper()])
        t_data = [[Paragraph(c, STYLES["table_header" if r == 0 else "table_cell"])
                   for c in row] for r, row in enumerate(rows)]
        f_t = Table(t_data, colWidths=[1.2*cm, 2.2*cm, 3.8*cm, 6.3*cm, 1.8*cm], repeatRows=1)
        f_style = [
            ("BACKGROUND",    (0,0),(-1,0), MPIV_NAVY),
            ("TEXTCOLOR",     (0,0),(-1,0), MPIV_WHITE),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [MPIV_WHITE, MPIV_GRAY]),
            ("GRID",          (0,0),(-1,-1), 0.3, colors.HexColor("#C8D8F0")),
            ("ALIGN",         (0,0),(1,-1), "CENTER"),
            ("ALIGN",         (4,0),(4,-1), "CENTER"),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
            ("TOPPADDING",    (0,0),(-1,-1), 6),
            ("BOTTOMPADDING", (0,0),(-1,-1), 6),
            ("LEFTPADDING",   (0,0),(-1,-1), 6),
        ]
        for i, f in enumerate(findings, 1):
            c = sev_colors_map.get(f.severity.value, MPIV_DARK)
            f_style += [("TEXTCOLOR", (1,i),(1,i), c), ("FONTNAME", (1,i),(1,i), "Helvetica-Bold")]
        f_t.setStyle(TableStyle(f_style))
        els.append(f_t)

        # Detail cards
        els.append(Spacer(1, 0.6*cm))
        els.append(Paragraph("Finding Details", STYLES["subsection"]))
        for f in findings:
            sev_c = sev_colors_map.get(f.severity.value, MPIV_DARK)
            card = Table([
                [Paragraph(f"<b>{f.id}</b> — {f.title}", STYLES["finding_title"]),
                 Paragraph(f.severity.value.upper(), ParagraphStyle("sev",
                     fontName="Helvetica-Bold", fontSize=8,
                     textColor=MPIV_WHITE, alignment=TA_CENTER))],
                [Paragraph(f"<b>Category:</b> {f.category.value}  |  <b>Effort:</b> {f.effort.upper()}", STYLES["table_cell"]), ""],
                [Paragraph(f"<b>Description:</b> {f.description}", STYLES["body"]), ""],
                [Paragraph(f"<b>Evidence:</b> {f.evidence or 'N/A'}", STYLES["body"]), ""],
                [Paragraph(f"<b>Recommendation:</b> {f.recommendation}", STYLES["body"]), ""],
            ], colWidths=[PAGE_W - 2*MARGIN - 2.5*cm, 2.5*cm])
            card.setStyle(TableStyle([
                ("BACKGROUND",   (0,0),(-1,0), MPIV_LIGHT),
                ("BACKGROUND",   (1,0),(1,0), sev_c),
                ("SPAN",         (0,1),(1,1)),
                ("SPAN",         (0,2),(1,2)),
                ("SPAN",         (0,3),(1,3)),
                ("SPAN",         (0,4),(1,4)),
                ("BOX",          (0,0),(-1,-1), 0.8, colors.HexColor("#C8D8F0")),
                ("LINEBELOW",    (0,0),(-1,0), 0.5, colors.HexColor("#C8D8F0")),
                ("TOPPADDING",   (0,0),(-1,-1), 6),
                ("BOTTOMPADDING",(0,0),(-1,-1), 6),
                ("LEFTPADDING",  (0,0),(-1,-1), 8),
                ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
            ]))
            els.append(KeepTogether([card, Spacer(1, 0.3*cm)]))
        return els

    # ── ROADMAP ───────────────────────────────────────────────────────────────
    def _roadmap(self):
        els = [Paragraph("4. Remediation Roadmap", STYLES["section_title"]), _divider()]
        els.append(Paragraph(
            "Remediation activities are organized into three phases based on complexity and impact. "
            "Quick-win items deliver immediate program improvement with minimal effort.",
            STYLES["body"]))
        els.append(Spacer(1, 0.4*cm))

        phases = [
            ("30 Days", "Quick Wins", MPIV_NAVY,  "quick-win"),
            ("60 Days", "Strategic",  MPIV_BLUE,  "strategic"),
            ("90 Days", "Roadmap",    MPIV_ACCENT,"roadmap"),
        ]
        type_map = {"quick-win": 0, "strategic": 1, "roadmap": 2}
        buckets = [[], [], []]
        for r in self.summary.recommendations:
            buckets[type_map.get(r.type, 2)].append(r)

        ph_w = (PAGE_W - 2*MARGIN) / 3
        # Header
        ph_header = Table([[
            Paragraph(f"<b>{p[0]}</b><br/>{p[1]}", ParagraphStyle(
                "ph", fontName="Helvetica-Bold", fontSize=11,
                textColor=MPIV_WHITE, alignment=TA_CENTER, leading=16))
            for p in phases
        ]], colWidths=[ph_w]*3)
        ph_style = [("TOPPADDING",(0,0),(-1,-1),12), ("BOTTOMPADDING",(0,0),(-1,-1),12),
                    ("ALIGN",(0,0),(-1,-1),"CENTER")]
        for i, p in enumerate(phases):
            ph_style.append(("BACKGROUND",(i,0),(i,0), p[2]))
        ph_header.setStyle(TableStyle(ph_style))
        els.append(ph_header)

        # Content
        bucket_content = []
        for bucket in buckets:
            items = []
            if bucket:
                for r in bucket:
                    items.append(Paragraph(f"<b>#{r.priority}</b> {r.title}", STYLES["roadmap_item"]))
                    for line in r.description.split("\n"):
                        if line.strip():
                            items.append(Paragraph(f"  {line.strip()}", ParagraphStyle(
                                "ri2", fontName="Helvetica", fontSize=7.5,
                                textColor=colors.HexColor("#555555"), leading=11, leftIndent=8)))
            else:
                items = [Paragraph("No items in this phase.", STYLES["roadmap_item"])]
            bucket_content.append(items)

        content_t = Table([bucket_content], colWidths=[ph_w]*3)
        content_t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), MPIV_WHITE),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            ("TOPPADDING",    (0,0),(-1,-1), 10),
            ("BOTTOMPADDING", (0,0),(-1,-1), 10),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
            ("RIGHTPADDING",  (0,0),(-1,-1), 8),
            ("BOX",           (0,0),(-1,-1), 0.5, colors.HexColor("#C8D8F0")),
            ("LINEBEFORE",    (1,0),(2,-1), 0.5, colors.HexColor("#C8D8F0")),
        ]))
        els.append(content_t)
        return els

    # ── NEXT STEPS ────────────────────────────────────────────────────────────
    def _next_steps(self):
        els = [Paragraph("5. Next Steps & Acceptance", STYLES["section_title"]), _divider()]
        for num, step in [
            ("1", "Schedule remediation kickoff meeting with IT Security and Operations teams within 5 business days."),
            ("2", "Assign owners to each Critical and High finding within 5 business days."),
            ("3", "Implement Quick-Win items (30-day phase) with MPIV Partners advisory support."),
            ("4", "Establish bi-weekly progress reviews for the 60-day strategic phase."),
            ("5", "Schedule 90-day follow-up assessment to validate maturity score improvement."),
        ]:
            row = Table([[Paragraph(f"<b>{num}</b>", STYLES["body_center"]),
                          Paragraph(step, STYLES["next_steps"])]],
                        colWidths=[0.8*cm, PAGE_W - 2*MARGIN - 0.8*cm])
            row.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(0,0), MPIV_NAVY),
                ("TEXTCOLOR",     (0,0),(0,0), MPIV_WHITE),
                ("ALIGN",         (0,0),(0,0), "CENTER"),
                ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
                ("TOPPADDING",    (0,0),(-1,-1), 6),
                ("BOTTOMPADDING", (0,0),(-1,-1), 6),
                ("LEFTPADDING",   (0,0),(-1,-1), 6),
                ("LINEBELOW",     (0,0),(-1,-1), 0.3, colors.HexColor("#CCCCCC")),
            ]))
            els.append(row)

        els.append(Spacer(1, 1.5*cm))
        els.append(Paragraph("Document Acceptance", STYLES["subsection"]))
        els.append(Paragraph(
            "By signing below, both parties acknowledge receipt of this assessment report "
            "and agree to pursue the recommended remediation activities in good faith.",
            STYLES["body"]))
        els.append(Spacer(1, 1.2*cm))

        half = (PAGE_W - 2*MARGIN) / 2
        sig_t = Table([
            [Paragraph("<b>MPIV Partners</b>", STYLES["body_center"]),
             Paragraph(f"<b>{self.summary.customer_name}</b>", STYLES["body_center"])],
            [Paragraph("Consultant Signature", STYLES["footer_note"]),
             Paragraph("Client Signature", STYLES["footer_note"])],
            [Paragraph("_" * 36, STYLES["body_center"]),
             Paragraph("_" * 36, STYLES["body_center"])],
            [Paragraph("Name: _______________________", STYLES["body"]),
             Paragraph("Name: _______________________", STYLES["body"])],
            [Paragraph("Title: _______________________", STYLES["body"]),
             Paragraph("Title: _______________________", STYLES["body"])],
            [Paragraph(f"Date:  {self.summary.assessment_date.strftime('%B %d, %Y')}", STYLES["body"]),
             Paragraph("Date:  _______________________", STYLES["body"])],
        ], colWidths=[half, half])
        sig_t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,0), MPIV_LIGHT),
            ("ALIGN",         (0,0),(-1,1), "CENTER"),
            ("TOPPADDING",    (0,0),(-1,-1), 6),
            ("BOTTOMPADDING", (0,0),(-1,-1), 6),
            ("LEFTPADDING",   (0,0),(-1,-1), 10),
            ("LINEBETWEEN",   (0,0),(1,-1), 0.5, colors.HexColor("#C8D8F0")),
            ("BOX",           (0,0),(-1,-1), 0.8, colors.HexColor("#C8D8F0")),
        ]))
        els.append(sig_t)
        els.append(Spacer(1, 1*cm))
        els.append(Paragraph(
            f"MPIV Partners Professional Services  |  Engagement: {self.summary.engagement_id}",
            STYLES["footer_note"]))
        return els