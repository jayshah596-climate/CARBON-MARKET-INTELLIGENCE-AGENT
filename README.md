# 🌍 Carbon Market Intelligence Agent

An AI-powered Carbon Market Intelligence and ESG Analytics Platform built on **Claude** (`claude-opus-4-6`).

## What It Does

- Tracks **all major compliance carbon markets**: EU ETS, UK ETS, California Cap-and-Trade, RGGI, China ETS, Australia ERF, New Zealand ETS, South Korea ETS, Canada OBPS, India PAT/Carbon Market, and more
- Monitors the **Voluntary Carbon Market (VCM)** across all major standards (Verra VCS, Gold Standard, ACR, CAR, Plan Vivo)
- Analyses **carbon pricing trends**, volatility, and market dynamics
- Evaluates **carbon offset quality** using ICVCM Core Carbon Principles
- Identifies **regulatory developments** and policy risks
- Generates **investment-grade insights** with traffic-light (Green/Yellow/Red) performance ratings
- Produces **colour-coded Excel dashboards** (6 sheets) and **consulting-grade Word reports** automatically

---

## Architecture

```
CARBON-MARKET-INTELLIGENCE-AGENT/
├── agent.py                   # Core Claude agent (tool_use agentic loop)
├── main.py                    # CLI entry point (Rich-powered)
├── api.py                     # FastAPI REST API
├── config.py                  # Settings (python-dotenv)
├── models/
│   └── carbon_models.py       # Pydantic v2 data models
├── prompts/
│   └── system_prompt.py       # Full analysis specification for Claude
├── tools/
│   ├── web_search.py          # Real-time web search (Tavily / DuckDuckGo)
│   ├── excel_generator.py     # Colour-coded Excel workbook (openpyxl)
│   └── word_generator.py      # Professional Word report (python-docx)
├── outputs/                   # Generated reports saved here
├── requirements.txt
├── .env.example
└── README.md
```

### Agent Design

The core agent uses **Claude `claude-opus-4-6`** with:
- **Adaptive thinking** (`thinking: {type: "adaptive"}`) for deep analytical reasoning
- **Tool use loop** — Claude autonomously calls `search_web` to fetch live carbon prices and news before generating the analysis
- **Structured JSON output** validated against Pydantic v2 models
- Maximum 8 tool iterations before forcing a final synthesis

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
cp .env.example .env
# Edit .env and set:
#   ANTHROPIC_API_KEY=your_key_here
#   TAVILY_API_KEY=your_key_here  (optional, improves web search quality)
```

### 3. Run Analysis

**Autonomous mode** (agent searches for live carbon market data):
```bash
python main.py analyze --auto
```

**Autonomous mode + generate Excel and Word reports**:
```bash
python main.py analyze --auto --excel --word
```

**Custom text input**:
```bash
python main.py analyze --input "EU ETS EUA price is EUR 65 per tonne, trending upward..."
```

**Input from file**:
```bash
python main.py analyze --input market_data.txt --excel --word
```

**Save JSON output**:
```bash
python main.py analyze --auto --json-output report.json
```

### 4. Start the REST API

```bash
python main.py serve
```

API will be available at `http://localhost:8000`
Interactive docs: `http://localhost:8000/docs`

---

## REST API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/markets` | List tracked carbon markets |
| `POST` | `/analyze` | Analyse carbon markets (returns JSON report + `analysis_id`) |
| `GET` | `/report/excel?analysis_id=...` | Download colour-coded Excel dashboard |
| `GET` | `/report/word?analysis_id=...` | Download Word report |
| `GET` | `/report/json?analysis_id=...` | Get raw JSON report |

### Example API Usage

```bash
# Analyse with live web search
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "auto"}'

# Download Excel dashboard (use analysis_id from above response)
curl "http://localhost:8000/report/excel?analysis_id=<id>" -o dashboard.xlsx

# Download Word report
curl "http://localhost:8000/report/word?analysis_id=<id>" -o report.docx
```

---

## JSON Output Schema

The agent produces structured JSON covering:

```json
{
  "market_overview":        { "price", "trend", "performance_rating", "color_code", ... },
  "compliance_markets":     [ { "market_name", "price", "currency", "trend", ... } ],
  "voluntary_carbon_market":{ "average_price", "demand_trend", "market_condition", ... },
  "carbon_offsets":         [ { "project_type", "quality_assessment", "risks", ... } ],
  "policy_and_regulation":  { "recent_updates", "policy_risk_level", ... },
  "risk_analysis":          { "market_risks", "pricing_risks", "overall_risk_level", ... },
  "opportunity_analysis":   { "investment_opportunities", "corporate_strategy", ... },
  "forecast":               { "short_term_outlook", "price_direction", "confidence", ... },
  "excel_analysis":         [ { "metric", "value", "performance", "color_code" } ],
  "word_report":            { "executive_summary", "sections", "recommendations", ... },
  "data_quality":           { "confidence", "missing_information", ... },
  "source_references":      [ { "topic", "snippet", "source" } ]
}
```

### Performance Color Coding

| Signal | Color | Meaning |
|--------|-------|---------|
| ✅ Green | `Good` | Stable market, high-quality data, clear policy support |
| ⚠️ Yellow | `Moderate` | Mixed signals, moderate volatility, evolving situation |
| 🔴 Red | `Risk` | High volatility, weak offset quality, regulatory uncertainty |

---

## Excel Dashboard — 6 Sheets

1. **Carbon Dashboard** — KPI overview with traffic-light indicators
2. **Compliance Markets** — All global compliance market prices with regulatory updates
3. **Voluntary Carbon Market** — VCM metrics, standards, and market condition
4. **Carbon Offsets** — Project quality assessment (additionality, permanence, risks)
5. **Risk Analysis** — Market, pricing, and policy risk breakdown
6. **Opportunities & Forecast** — Investment opportunities and price forecast

---

## Word Report — Sections

1. Executive Summary (max 150 words)
2. Market Overview
3. Pricing Analysis (compliance + VCM)
4. Carbon Offsets Analysis
5. Policy & Regulatory Environment
6. Risk Analysis
7. Opportunities & Strategy
8. Forecast & Outlook
9. Conclusion & Strategic Recommendations

---

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | ✅ Yes | — | Anthropic API key |
| `TAVILY_API_KEY` | No | — | Tavily search API key (improves web search) |
| `MODEL_NAME` | No | `claude-opus-4-6` | Claude model to use |
| `API_HOST` | No | `0.0.0.0` | API server bind address |
| `API_PORT` | No | `8000` | API server port |
| `OUTPUT_DIR` | No | `./outputs` | Directory for generated files |

---

## Web Search

The agent uses real-time web search to fetch current carbon market data:

- **Tavily API** (recommended): High-quality, structured search with AI summaries. Set `TAVILY_API_KEY` in `.env`.
- **DuckDuckGo** (fallback): Free HTML scraping. No API key required. Automatically used when Tavily is not configured.

---

## Requirements

- Python 3.10+
- Anthropic API key (`ANTHROPIC_API_KEY`)
- Optional: Tavily API key for enhanced web search

---

## License

MIT License — Carbon Market Intelligence Agent
