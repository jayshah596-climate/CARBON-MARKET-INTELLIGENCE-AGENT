"""
Word Report Generator for Carbon Market Intelligence Reports.

Produces a professional, consulting-grade .docx file using python-docx.
"""

from __future__ import annotations
import logging
from pathlib import Path
from datetime import datetime

from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from models.carbon_models import CarbonIntelligenceReport

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Colour constants (RGB)
# ---------------------------------------------------------------------------
C_NAVY = RGBColor(0x1F, 0x38, 0x64)       # dark navy
C_BLUE = RGBColor(0x2E, 0x75, 0xB6)       # medium blue
C_GREEN = RGBColor(0x00, 0xB0, 0x50)
C_YELLOW = RGBColor(0xFF, 0xC0, 0x00)
C_RED = RGBColor(0xFF, 0x00, 0x00)
C_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
C_LIGHT_BLUE = RGBColor(0xD9, 0xE1, 0xF2)
C_DARK_GREY = RGBColor(0x40, 0x40, 0x40)
C_LIGHT_GREY = RGBColor(0xF2, 0xF2, 0xF2)

HEX_GREEN = "00B050"
HEX_YELLOW = "FFC000"
HEX_RED = "FF0000"
HEX_NAVY = "1F3864"
HEX_BLUE = "2E75B6"
HEX_LIGHT_BLUE = "D9E1F2"
HEX_LIGHT_GREY = "F2F2F2"


def _hex_to_rgb(hex_color: str) -> RGBColor:
    h = hex_color.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _color_code_hex(color_code: str) -> str:
    return {"Green": HEX_GREEN, "Yellow": HEX_YELLOW, "Red": HEX_RED}.get(
        color_code, HEX_YELLOW
    )


def _set_cell_bg(cell, hex_color: str) -> None:
    """Set table cell background colour via direct XML manipulation."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color.lstrip("#"))
    tcPr.append(shd)


def _set_table_borders(table) -> None:
    """Add thin borders to all cells of a table."""
    tbl = table._tbl
    tblPr = tbl.tblPr if tbl.tblPr is not None else OxmlElement("w:tblPr")
    tblBorders = OxmlElement("w:tblBorders")
    for border_name in ("top", "left", "bottom", "right", "insideH", "insideV"):
        border = OxmlElement(f"w:{border_name}")
        border.set(qn("w:val"), "single")
        border.set(qn("w:sz"), "4")
        border.set(qn("w:space"), "0")
        border.set(qn("w:color"), "BFBFBF")
        tblBorders.append(border)
    tblPr.append(tblBorders)


class WordGenerator:
    """Generates a consulting-grade Word report from a CarbonIntelligenceReport."""

    def generate(self, report: CarbonIntelligenceReport, output_path: str | Path) -> str:
        """
        Build the Word document and save to *output_path*.

        Returns the absolute path to the saved file.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        doc = Document()
        self._configure_page(doc)

        # Cover page
        self._add_cover_page(doc, report)

        # Table of Contents placeholder
        doc.add_page_break()
        self._heading(doc, "Table of Contents", level=1)
        toc_items = [
            "1. Executive Summary",
            "2. Market Overview",
            "3. Pricing Analysis",
            "4. Carbon Offsets Analysis",
            "5. Policy & Regulatory Environment",
            "6. Risk Analysis",
            "7. Opportunities & Strategy",
            "8. Forecast & Outlook",
            "9. Conclusion & Recommendations",
        ]
        for item in toc_items:
            p = doc.add_paragraph(item)
            p.paragraph_format.left_indent = Cm(0.5)

        # --- Sections ---
        doc.add_page_break()
        self._add_executive_summary(doc, report)
        self._add_market_overview(doc, report)
        self._add_pricing_analysis(doc, report)
        self._add_offsets_analysis(doc, report)
        self._add_policy_section(doc, report)
        self._add_risk_section(doc, report)
        self._add_opportunity_section(doc, report)
        self._add_forecast_section(doc, report)
        self._add_conclusion(doc, report)

        doc.save(str(output_path))
        logger.info("Word document saved: %s", output_path)
        return str(output_path.resolve())

    # ------------------------------------------------------------------
    # Page configuration
    # ------------------------------------------------------------------

    def _configure_page(self, doc: Document) -> None:
        """Set A4 margins."""
        for section in doc.sections:
            section.top_margin = Cm(2.5)
            section.bottom_margin = Cm(2.5)
            section.left_margin = Cm(2.5)
            section.right_margin = Cm(2.5)

    # ------------------------------------------------------------------
    # Cover page
    # ------------------------------------------------------------------

    def _add_cover_page(self, doc: Document, report: CarbonIntelligenceReport) -> None:
        wr = report.word_report

        doc.add_paragraph()
        doc.add_paragraph()

        # Main title
        title_p = doc.add_paragraph()
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title_p.add_run(wr.title.upper())
        run.font.size = Pt(26)
        run.font.bold = True
        run.font.color.rgb = C_NAVY

        doc.add_paragraph()

        # Subtitle
        sub_p = doc.add_paragraph()
        sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sub_run = sub_p.add_run("ESG Analytics & Carbon Pricing Intelligence")
        sub_run.font.size = Pt(16)
        sub_run.font.color.rgb = C_BLUE

        doc.add_paragraph()
        doc.add_paragraph()

        # Metadata table
        table = doc.add_table(rows=3, cols=2)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = "Table Grid"

        meta = [
            ("Report Date:", wr.date or datetime.now().strftime("%d %B %Y")),
            ("Region / Market:", report.market_overview.region or "Global"),
            ("Confidence Level:", report.data_quality.confidence or "Medium"),
        ]
        for i, (label, value) in enumerate(meta):
            row = table.rows[i]
            label_cell = row.cells[0]
            label_cell.text = label
            label_cell.paragraphs[0].runs[0].font.bold = True
            label_cell.paragraphs[0].runs[0].font.color.rgb = C_NAVY
            _set_cell_bg(label_cell, HEX_LIGHT_BLUE)

            value_cell = row.cells[1]
            value_cell.text = value
            value_cell.paragraphs[0].runs[0].font.color.rgb = C_DARK_GREY

        doc.add_paragraph()
        doc.add_paragraph()

        # Disclaimer
        disc_p = doc.add_paragraph()
        disc_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        disc_run = disc_p.add_run(
            "CONFIDENTIAL — For internal use and authorised recipients only. "
            "This report is generated by an AI-powered analytics agent and should be "
            "reviewed by qualified carbon market professionals before acting on its content."
        )
        disc_run.font.size = Pt(9)
        disc_run.font.color.rgb = C_DARK_GREY
        disc_run.font.italic = True

    # ------------------------------------------------------------------
    # Section helpers
    # ------------------------------------------------------------------

    def _heading(self, doc: Document, text: str, level: int = 1) -> None:
        p = doc.add_heading(text, level=level)
        for run in p.runs:
            run.font.color.rgb = C_NAVY if level == 1 else C_BLUE

    def _body_para(self, doc: Document, text: str, bold: bool = False) -> None:
        p = doc.add_paragraph()
        run = p.add_run(text)
        run.font.bold = bold
        run.font.size = Pt(11)
        p.paragraph_format.space_after = Pt(6)

    def _bullet(self, doc: Document, text: str, level: int = 0) -> None:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.left_indent = Cm(0.5 * (level + 1))
        run = p.add_run(text)
        run.font.size = Pt(11)

    def _info_box(self, doc: Document, label: str, value: str, color_code: str = "Yellow") -> None:
        """Render a highlighted info box for key metrics."""
        table = doc.add_table(rows=1, cols=2)
        table.style = "Table Grid"
        _set_table_borders(table)
        label_cell = table.rows[0].cells[0]
        label_cell.text = label
        label_cell.paragraphs[0].runs[0].font.bold = True
        label_cell.paragraphs[0].runs[0].font.color.rgb = C_WHITE
        _set_cell_bg(label_cell, HEX_NAVY)

        value_cell = table.rows[0].cells[1]
        value_cell.text = value
        value_cell.paragraphs[0].runs[0].font.bold = True
        hex_c = _color_code_hex(color_code)
        _set_cell_bg(value_cell, hex_c)
        if color_code in ("Green", "Red"):
            value_cell.paragraphs[0].runs[0].font.color.rgb = C_WHITE
        doc.add_paragraph()

    def _color_badge_table(
        self,
        doc: Document,
        headers: list[str],
        rows_data: list[list[str]],
        color_col_index: int = -1,
    ) -> None:
        """Render a table where one column has traffic-light colour coding."""
        table = doc.add_table(rows=1 + len(rows_data), cols=len(headers))
        table.style = "Table Grid"
        _set_table_borders(table)

        # Header row
        header_row = table.rows[0]
        for col_i, header in enumerate(headers):
            cell = header_row.cells[col_i]
            cell.text = header
            p = cell.paragraphs[0]
            p.runs[0].font.bold = True
            p.runs[0].font.color.rgb = C_WHITE
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _set_cell_bg(cell, HEX_NAVY)

        # Data rows
        for row_i, row_data in enumerate(rows_data):
            bg = HEX_LIGHT_BLUE if row_i % 2 == 0 else "FFFFFF"
            table_row = table.rows[row_i + 1]
            for col_i, value in enumerate(row_data):
                cell = table_row.cells[col_i]
                actual_col = color_col_index if color_col_index >= 0 else len(row_data) + color_col_index
                if col_i == actual_col and value in ("Green", "Yellow", "Red"):
                    _set_cell_bg(cell, _color_code_hex(value))
                    cell.text = f"● {value}"
                    cell.paragraphs[0].runs[0].font.bold = True
                    cell.paragraphs[0].runs[0].font.color.rgb = C_WHITE
                else:
                    _set_cell_bg(cell, bg)
                    cell.text = str(value)
                cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
                cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

        doc.add_paragraph()

    # ------------------------------------------------------------------
    # Report sections
    # ------------------------------------------------------------------

    def _add_executive_summary(self, doc: Document, report: CarbonIntelligenceReport) -> None:
        self._heading(doc, "1. Executive Summary")
        wr = report.word_report
        text = wr.executive_summary
        if text and text != "missing":
            self._body_para(doc, text)
        else:
            ov = report.market_overview
            self._body_para(
                doc,
                f"This report provides a comprehensive analysis of global carbon markets as of "
                f"{wr.date or 'the latest available date'}. "
                f"The primary market analysed is {ov.market_type} with a focus on {ov.region}. "
                f"The current carbon price stands at {ov.latest_price.value} "
                f"{ov.latest_price.currency} per tCO2e, with a {ov.price_trend} trend. "
                f"Overall market performance is rated as {ov.performance_rating}.",
            )

        # Key findings table
        if report.compliance_markets:
            doc.add_paragraph()
            self._heading(doc, "Key Compliance Market Prices at a Glance", level=2)
            headers = ["Market", "Price", "Currency", "Trend", "Signal"]
            rows_data = [
                [m.market_name, m.price, m.currency, m.trend, m.color_code]
                for m in report.compliance_markets[:8]
            ]
            self._color_badge_table(doc, headers, rows_data, color_col_index=4)

    def _add_market_overview(self, doc: Document, report: CarbonIntelligenceReport) -> None:
        self._heading(doc, "2. Market Overview")
        ov = report.market_overview
        text = report.word_report.market_overview_section
        if text and text != "missing":
            self._body_para(doc, text)
        else:
            self._body_para(
                doc,
                f"The carbon market landscape currently spans both compliance and voluntary "
                f"segments. {ov.region} represents the primary focus of this analysis."
            )
        self._info_box(doc, "Market Type", ov.market_type, ov.color_code)
        self._info_box(doc, "Latest Price", f"{ov.latest_price.value} {ov.latest_price.currency}/tCO2e", ov.color_code)
        self._info_box(doc, "Price Trend", ov.price_trend, ov.color_code)

        if ov.key_drivers:
            self._heading(doc, "Key Market Drivers", level=2)
            for driver in ov.key_drivers:
                self._bullet(doc, driver)

        if ov.insight and ov.insight != "missing":
            self._heading(doc, "Market Insight", level=2)
            self._body_para(doc, ov.insight)

    def _add_pricing_analysis(self, doc: Document, report: CarbonIntelligenceReport) -> None:
        self._heading(doc, "3. Pricing Analysis")
        text = report.word_report.pricing_analysis_section
        if text and text != "missing":
            self._body_para(doc, text)

        if report.compliance_markets:
            self._heading(doc, "Compliance Markets", level=2)
            headers = ["Market", "Region", "Price", "Currency", "Trend", "Performance", "Signal"]
            rows_data = [
                [m.market_name, m.region, m.price, m.currency, m.trend, m.performance, m.color_code]
                for m in report.compliance_markets
            ]
            self._color_badge_table(doc, headers, rows_data, color_col_index=6)

        vcm = report.voluntary_carbon_market
        self._heading(doc, "Voluntary Carbon Market (VCM)", level=2)
        self._body_para(
            doc,
            f"Average VCM price: {vcm.average_price} {vcm.currency}/tCO2e "
            f"(range: {vcm.price_range}). "
            f"Market condition: {vcm.market_condition}. "
            f"Demand trend: {vcm.demand_trend}."
        )
        if vcm.insight and vcm.insight != "missing":
            self._body_para(doc, vcm.insight)

    def _add_offsets_analysis(self, doc: Document, report: CarbonIntelligenceReport) -> None:
        self._heading(doc, "4. Carbon Offsets Analysis")
        text = report.word_report.offsets_analysis_section
        if text and text != "missing":
            self._body_para(doc, text)

        if report.carbon_offsets:
            headers = ["Project Type", "Region", "Standard", "Price Range", "Quality", "Signal"]
            rows_data = [
                [o.project_type, o.region, o.standard,
                 f"{o.price_range} {o.currency}".strip(),
                 o.quality_assessment, o.color_code]
                for o in report.carbon_offsets
            ]
            self._color_badge_table(doc, headers, rows_data, color_col_index=5)

            # Detailed offset risks
            self._heading(doc, "Offset Quality Risk Factors", level=2)
            for offset in report.carbon_offsets:
                if offset.risks:
                    self._body_para(doc, f"{offset.project_type} — {offset.region}:", bold=True)
                    for risk in offset.risks:
                        self._bullet(doc, risk)

    def _add_policy_section(self, doc: Document, report: CarbonIntelligenceReport) -> None:
        self._heading(doc, "5. Policy & Regulatory Environment")
        pol = report.policy_and_regulation
        text = report.word_report.policy_section
        if text and text != "missing":
            self._body_para(doc, text)

        if pol.recent_updates:
            self._heading(doc, "Recent Policy Developments", level=2)
            for update in pol.recent_updates:
                self._bullet(doc, update)

        if pol.carbon_tax and pol.carbon_tax != "missing":
            self._info_box(doc, "Carbon Tax Status", pol.carbon_tax, "Yellow")
        if pol.ets_changes and pol.ets_changes != "missing":
            self._info_box(doc, "ETS Changes", pol.ets_changes, "Yellow")
        if pol.insight and pol.insight != "missing":
            self._body_para(doc, pol.insight)

    def _add_risk_section(self, doc: Document, report: CarbonIntelligenceReport) -> None:
        self._heading(doc, "6. Risk Analysis")
        risk = report.risk_analysis
        text = report.word_report.risk_section
        if text and text != "missing":
            self._body_para(doc, text)

        self._info_box(doc, "Overall Risk Level", risk.overall_risk_level.upper(), risk.color_code)

        risk_items = [
            ("Market Risks", risk.market_risks),
            ("Pricing Risks", risk.pricing_risks),
            ("Policy Risks", risk.policy_risks),
        ]
        for section_name, items in risk_items:
            if items:
                self._heading(doc, section_name, level=2)
                for item in items:
                    self._bullet(doc, item)

        if risk.insight and risk.insight != "missing":
            self._heading(doc, "Risk Insight", level=2)
            self._body_para(doc, risk.insight)

    def _add_opportunity_section(self, doc: Document, report: CarbonIntelligenceReport) -> None:
        self._heading(doc, "7. Opportunities & Strategy")
        opp = report.opportunity_analysis
        text = report.word_report.opportunity_section
        if text and text != "missing":
            self._body_para(doc, text)

        opp_sections = [
            ("Investment Opportunities", opp.investment_opportunities),
            ("Corporate Strategy Opportunities", opp.corporate_strategy_opportunities),
            ("ESG Opportunities", opp.esg_opportunities),
        ]
        for section_name, items in opp_sections:
            if items:
                self._heading(doc, section_name, level=2)
                for item in items:
                    self._bullet(doc, item)

        if opp.insight and opp.insight != "missing":
            self._body_para(doc, opp.insight)

    def _add_forecast_section(self, doc: Document, report: CarbonIntelligenceReport) -> None:
        self._heading(doc, "8. Forecast & Outlook")
        fc = report.forecast
        text = report.word_report.forecast_section
        if text and text != "missing":
            self._body_para(doc, text)

        headers = ["Horizon", "Outlook", "Price Target", "Confidence"]
        rows_data = [
            ["Short-Term (1-2 yr)", fc.short_term_outlook, fc.price_target_short_term, fc.confidence],
            ["Long-Term (5-10 yr)", fc.long_term_outlook, fc.price_target_long_term, fc.confidence],
        ]
        self._color_badge_table(doc, headers, rows_data)

        self._info_box(doc, "Price Direction", fc.price_direction, report.market_overview.color_code)

        if fc.insight and fc.insight != "missing":
            self._body_para(doc, fc.insight)

    def _add_conclusion(self, doc: Document, report: CarbonIntelligenceReport) -> None:
        self._heading(doc, "9. Conclusion & Strategic Recommendations")
        wr = report.word_report
        text = wr.conclusion
        if text and text != "missing":
            self._body_para(doc, text)

        if wr.strategic_recommendations:
            self._heading(doc, "Strategic Recommendations", level=2)
            for i, rec in enumerate(wr.strategic_recommendations, 1):
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Cm(0.5)
                p.paragraph_format.space_after = Pt(6)
                run = p.add_run(f"{i}. {rec}")
                run.font.size = Pt(11)
                run.font.bold = False

        # Disclaimer
        doc.add_paragraph()
        disc_p = doc.add_paragraph()
        disc_run = disc_p.add_run(
            "Disclaimer: This report is generated by an AI-powered carbon market analytics agent. "
            "All data and analyses should be verified by qualified professionals. "
            "Past market performance does not guarantee future results."
        )
        disc_run.font.size = Pt(9)
        disc_run.font.italic = True
        disc_run.font.color.rgb = C_DARK_GREY
