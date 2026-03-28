"""
FastAPI REST API for the Carbon Market Intelligence Agent.

Endpoints
---------
POST /analyze          — Accept text input, return full JSON report
GET  /report/excel     — Generate and download colour-coded Excel workbook
GET  /report/word      — Generate and download Word report
GET  /health           — Health check
GET  /markets          — List supported carbon markets
"""

from __future__ import annotations
import logging
import uuid
from pathlib import Path
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from config import settings
from agent import CarbonMarketAgent
from models.carbon_models import CarbonIntelligenceReport
from tools.excel_generator import ExcelGenerator
from tools.word_generator import WordGenerator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Carbon Market Intelligence Agent API",
    description=(
        "AI-powered carbon market analytics platform. "
        "Tracks compliance and voluntary carbon markets globally, "
        "produces investment-grade insights, and generates Excel dashboards "
        "and Word reports automatically."
    ),
    version="1.0.0",
)

# In-memory store: analysis_id → CarbonIntelligenceReport
_analysis_store: dict[str, CarbonIntelligenceReport] = {}

settings.ensure_output_dir()

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    text: str = ""
    """
    Input text about carbon markets to analyse.
    Leave empty or set to 'auto' to trigger autonomous web-search mode.
    """


class AnalyzeResponse(BaseModel):
    analysis_id: str
    report: dict[str, Any]
    generated_at: str


class ReportRequest(BaseModel):
    report: dict[str, Any]
    """Full report JSON from a prior /analyze response."""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "ok",
        "model": settings.MODEL_NAME,
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/markets")
def list_markets() -> dict[str, Any]:
    """Return the list of carbon markets tracked by the agent."""
    return {
        "compliance_markets": [
            {"name": "EU ETS", "region": "European Union", "currency": "EUR"},
            {"name": "UK ETS", "region": "United Kingdom", "currency": "GBP"},
            {"name": "California Cap-and-Trade", "region": "California, USA", "currency": "USD"},
            {"name": "RGGI", "region": "Northeast USA", "currency": "USD"},
            {"name": "China National ETS", "region": "China", "currency": "CNY"},
            {"name": "Australia ERF / Safeguard", "region": "Australia", "currency": "AUD"},
            {"name": "New Zealand ETS", "region": "New Zealand", "currency": "NZD"},
            {"name": "South Korea ETS", "region": "South Korea", "currency": "KRW"},
            {"name": "Canada Federal OBPS", "region": "Canada", "currency": "CAD"},
            {"name": "India Carbon Market / PAT", "region": "India", "currency": "INR"},
        ],
        "voluntary_standards": [
            "Verra VCS (Verified Carbon Standard)",
            "Gold Standard",
            "American Carbon Registry (ACR)",
            "Climate Action Reserve (CAR)",
            "Plan Vivo",
            "CORSIA (aviation offsets)",
        ],
    }


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Analyse carbon market data and return a structured intelligence report.

    - Send `text` with carbon market data/news for text-based analysis.
    - Send empty `text` or `"auto"` for autonomous live web-search mode.
    """
    try:
        settings.validate()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    try:
        agent = CarbonMarketAgent()
        report = agent.analyze(request.text)
    except Exception as exc:
        logger.exception("Agent analysis failed")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}")

    analysis_id = str(uuid.uuid4())
    _analysis_store[analysis_id] = report

    # Best-effort persist to /tmp for cross-invocation access on Vercel
    try:
        tmp_path = Path(f"/tmp/analysis_{analysis_id}.json")
        tmp_path.write_text(report.model_dump_json(), encoding="utf-8")
    except Exception:
        pass

    return AnalyzeResponse(
        analysis_id=analysis_id,
        report=report.model_dump(),
        generated_at=datetime.now().isoformat(),
    )


@app.post("/report/excel")
def download_excel(request: ReportRequest) -> StreamingResponse:
    """
    Generate and stream a colour-coded Excel dashboard.

    Pass the full `report` dict from a prior /analyze response in the body.
    """
    try:
        report = CarbonIntelligenceReport.model_validate(request.report)
        buffer = ExcelGenerator().generate_bytes(report)
    except Exception as exc:
        logger.exception("Excel generation failed")
        raise HTTPException(status_code=500, detail=f"Excel generation failed: {exc}")

    return StreamingResponse(
        content=buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="Carbon_Report.xlsx"'},
    )


@app.post("/report/word")
def download_word(request: ReportRequest) -> StreamingResponse:
    """
    Generate and stream a professional Word report.

    Pass the full `report` dict from a prior /analyze response in the body.
    """
    try:
        report = CarbonIntelligenceReport.model_validate(request.report)
        buffer = WordGenerator().generate_bytes(report)
    except Exception as exc:
        logger.exception("Word generation failed")
        raise HTTPException(status_code=500, detail=f"Word generation failed: {exc}")

    return StreamingResponse(
        content=buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="Carbon_Report.docx"'},
    )


@app.get("/report/json")
def get_json_report(analysis_id: str) -> dict[str, Any]:
    """Return the raw JSON report for a prior analysis."""
    report = _analysis_store.get(analysis_id)
    if not report:
        # Fall back to /tmp (best-effort, same Vercel instance)
        tmp_path = Path(f"/tmp/analysis_{analysis_id}.json")
        if tmp_path.exists():
            import json as _json
            report = CarbonIntelligenceReport.model_validate(_json.loads(tmp_path.read_text()))
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis '{analysis_id}' not found. Run POST /analyze first.",
            )
    return report.model_dump()


