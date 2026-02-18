import os
from datetime import datetime
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from models.assessment import AssessmentSummary, Severity
from config.settings import settings
from loguru import logger

DARK_BLUE = colors.HexColor("#0D2B45")
BLUE = colors.HexColor("#1565C0")
GRAY = colors.HexColor("#F5F7FA")
SEV_COLORS = {
    Severity.CRITICAL: colors.HexColor("#D32F2F"),
    Severity.HIGH: colors.HexColor("#F57C00"),
    Severity.MEDIUM: colors.HexColor("#FBC02D"),
    Severity.LOW: colors.HexColor("#388E3C"),
}

class PDFReportGenerator:
    def __init__(self, summary: AssessmentSummary):
        self.summary = summary
        self.styles = getSampleStyleSheet()
        Path(settings.REPORT_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    def generate(self) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(
            settings.REPORT_OUTPUT_DIR,
            f"MPIV_HealthCheck_{self.summary.engagement_id}_{ts}.pdf"
        )
        doc = SimpleDocTemplate(path, pagesize=letter,
                                rightMargin=0.75*inch, leftMargin=0.75*inch,
                                topMargin=0.75*inch, bottomMargin=0.75*inch)
        story = []
        story += self._cover()
        story.append(PageBreak())
        story += self._exec_summary()
        story += self._maturity()
        story += self._findings()
        story += self._recommendations()
        doc.build(story)
        logger.info(f"PDF generated: {path}")
        return path

    def _h1(self, text):
        return Paragraph(f"<font color='#0D2B45'><b>{text}</b></font>",
                         ParagraphStyle("h1", fontSize=16, spaceAfter=8, spaceBefore=16))

    def _body(self, text):
        return Paragraph(text, ParagraphStyle("body", fontSize=10, leading=14,
                                              alignment=TA_JUSTIFY, spaceAfter=8))

    def _cover(self):
        title_style = ParagraphStyle("title", fontSize=24, textColor=colors.white,
                                     alignment=TA_CENTER, fontName="Helvetica-Bold")
        header = Table([[Paragraph(
            f'<b>MPIV Consulting</b><br/>Tenable TVM Health Check<br/>'
            f'<font size="14">{self.summary.customer_name}</font>', title_style
        )]], colWidths=[7*inch])
        header.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), DARK_BLUE),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("TOPPADDING", (0,0), (-1,-1), 40),
            ("BOTTOMPADDING", (0,0), (-1,-1), 40),
        ]))
        meta = Table([
            ["Engagement ID:", self.summary.engagement_id],
            ["Date:", self.summary.assessment_date.strftime("%B %d, %Y")],
            ["Maturity:", f"{self.summary.maturity_level.value} ({self.summary.maturity_score}/5.0)"],
            ["Classification:", "CONFIDENTIAL"],
        ], colWidths=[2*inch, 5*inch])
        meta.setStyle(TableStyle([
            ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 10),
            ("ROWBACKGROUNDS", (0,0), (-1,-1), [GRAY, colors.white]),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING", (0,0), (-1,-1), 8),
        ]))
        return [header, Spacer(1, 0.3*inch), meta]

    def _exec_summary(self):
        els = [self._h1("Executive Summary")]
        if self.summary.executive_narrative:
            for para in self.summary.executive_narrative.split("\n\n"):
                if para.strip():
                    els.append(self._body(para.strip()))
        return els

    def _maturity(self):
        els = [self._h1("Maturity Assessment")]
        data = [
            ["Metric", "Value"],
            ["Maturity Level", self.summary.maturity_level.value],
            ["Maturity Score", f"{self.summary.maturity_score} / 5.0"],
            ["Total Assets", str(self.summary.total_assets)],
            ["Authenticated Coverage", f"{self.summary.authenticated_scans_pct:.1f}%"],
            ["Scanner Health", f"{self.summary.scanner_health_pct:.1f}%"],
            ["Critical Findings", str(len(self.summary.critical_findings))],
            ["Total Findings", str(len(self.summary.findings))],
        ]
        t = Table(data, colWidths=[3.5*inch, 3.5*inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), BLUE),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [GRAY, colors.white]),
            ("GRID", (0,0), (-1,-1), 0.5, colors.lightgrey),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING", (0,0), (-1,-1), 8),
        ]))
        els.append(t)
        return els

    def _findings(self):
        els = [self._h1("Findings")]
        rows = [["ID", "Severity", "Category", "Title"]]
        for f in self.summary.findings:
            rows.append([f.id, f.severity.upper(), f.category.value, f.title])
        t = Table(rows, colWidths=[0.6*inch, 0.9*inch, 1.8*inch, 3.7*inch], repeatRows=1)
        style = [
            ("BACKGROUND", (0,0), (-1,0), DARK_BLUE),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 9),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [GRAY, colors.white]),
            ("GRID", (0,0), (-1,-1), 0.5, colors.lightgrey),
            ("TOPPADDING", (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
        ]
        for i, f in enumerate(self.summary.findings, 1):
            c = SEV_COLORS.get(f.severity, colors.gray)
            style += [("TEXTCOLOR", (1,i), (1,i), c),
                      ("FONTNAME", (1,i), (1,i), "Helvetica-Bold")]
        t.setStyle(TableStyle(style))
        els.append(t)
        return els

    def _recommendations(self):
        els = [PageBreak(), self._h1("Recommendations")]
        type_labels = {"quick-win": "QUICK WIN", "strategic": "STRATEGIC", "roadmap": "ROADMAP"}
        for r in self.summary.recommendations:
            label = type_labels.get(r.type, r.type.upper())
            els.append(self._body(f"<b>#{r.priority} [{label}] — {r.title}</b>"))
            for line in r.description.split("\n"):
                if line.strip():
                    els.append(self._body(line.strip()))
            els.append(Spacer(1, 0.1*inch))
        return els