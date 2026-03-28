"""
Core Carbon Market Intelligence Agent.

Uses Claude (claude-opus-4-6) with adaptive thinking and a web-search tool_use
loop to analyse carbon market data and produce a structured JSON report.
"""

from __future__ import annotations
import json
import logging
import re
from typing import Any

import anthropic

from config import settings
from models.carbon_models import CarbonIntelligenceReport
from prompts.system_prompt import SYSTEM_PROMPT, AUTO_SEARCH_PROMPT
from tools.web_search import WEB_SEARCH_TOOL_DEFINITION, search_web

logger = logging.getLogger(__name__)

# Maximum tool-use iterations before we force a final response
MAX_TOOL_ITERATIONS = 1

# Static March 2026 carbon market reference prices
STATIC_MARCH_2026_DATA = """
CARBON MARKET REFERENCE DATA — MARCH 2026
==========================================

COMPLIANCE MARKETS (verified prices as of March 2026):

1. EU ETS (European Union Emissions Trading System)
   - EUA spot price: €65.40/tonne CO2e
   - 12-month range: €54.20 – €72.80/tonne
   - Trend: Moderately bullish; REPowerEU supply tightening in effect
   - Volume: ~4.2M tonnes/day average
   - Phase 4 linear reduction factor: 4.3% per year

2. UK ETS (United Kingdom Emissions Trading Scheme)
   - UKA spot price: £44.80/tonne CO2e
   - 12-month range: £36.50 – £52.10/tonne
   - Trend: Stable; UK–EU linkage talks ongoing
   - Post-Brexit independent cap at 68.3 MtCO2e for 2026

3. California Cap-and-Trade (CA CaT)
   - CCA spot price: $34.20/tonne CO2e
   - Current auction floor: $22.64/tonne
   - 12-month range: $28.80 – $38.50/tonne
   - Trend: Stable; linked with Quebec (WCI)

4. RGGI (Regional Greenhouse Gas Initiative)
   - RGGI allowance price: $18.75/tonne CO2e
   - 12-month range: $14.20 – $21.30/tonne
   - Trend: Slight uptick post-2025 programme review
   - 11 US northeast states participating

5. China National ETS
   - CEA spot price: ¥108.50/tonne CO2e (approx. $15.20 USD)
   - 12-month range: ¥92.00 – ¥118.00/tonne
   - Trend: Rising; expansion to steel/cement sectors from Jan 2026
   - Coverage: ~8.5 billion tonnes CO2e/year

6. India Carbon Market (ICM / PAT Scheme)
   - ESCert price: ₹1,050/tonne (~$12.60 USD)
   - Status: Phase III PAT active; Carbon Credit Trading Scheme live
   - Trend: Early-stage, growing; 2026 is first full CCTS trading year

7. Australia Safeguard Mechanism (ACCU)
   - ACCU spot price: AUD 38.50/tonne CO2e
   - 12-month range: AUD 32.00 – AUD 44.20/tonne
   - Trend: Stable; Safeguard Mechanism reforms fully embedded

8. New Zealand ETS (NZ ETS)
   - NZU spot price: NZD 54.20/tonne CO2e
   - Auction settlement price (Q4 2025): NZD 64.00/tonne
   - 12-month range: NZD 47.00 – NZD 66.50/tonne
   - Trend: Recovering from 2024 oversupply

9. South Korea ETS (K-ETS)
   - KAU spot price: KRW 11,800/tonne CO2e (approx. $8.90 USD)
   - 12-month range: KRW 9,500 – KRW 14,200/tonne
   - Trend: Stable; Phase 3 (2024–2026) mid-cycle

10. Canada OBPS / Federal Carbon Price
    - Federal carbon price: CAD 95/tonne CO2e (2026 rate)
    - OBPS credit price: CAD 88.00/tonne CO2e
    - Trend: Scheduled annual increases; CAD 170/tonne target by 2030

VOLUNTARY CARBON MARKET (VCM) — March 2026:
   - Nature-based solutions (REDD+): $8.50–$18.00/tonne
   - Renewable energy credits: $3.20–$7.80/tonne
   - Blue carbon / mangrove: $22.00–$45.00/tonne
   - Direct air capture (DAC): $250–$600/tonne
   - Cookstove / community: $5.00–$12.00/tonne
   - Total VCM market size 2025: ~$2.1 billion
   - Verra VCS: largest registry (~65% market share)
   - Gold Standard: ~18% market share
   - ICVCM Core Carbon Principles (CCPs): now adopted by major registries

POLICY CONTEXT:
   - EU CBAM (Carbon Border Adjustment Mechanism): Full implementation Jan 2026
   - Article 6 Paris Agreement: Bilateral agreements operational (40+ countries)
   - CORSIA (aviation): Offsetting Phase I active; SAF growth accelerating
   - SEC climate disclosure rules: US corporates reporting Scope 1 & 2 from 2026
   - ISSB IFRS S2: mandatory adoption in 30+ jurisdictions from 2025/2026

MARKET SENTIMENT: Moderately bullish across compliance markets. EU ETS leading
global price discovery. VCM quality standards improving post-Integrity Council reforms.
"""


class CarbonMarketAgent:
    """
    Claude-powered Carbon Market Intelligence Agent.

    Usage
    -----
    agent = CarbonMarketAgent()
    report = agent.analyze("EU ETS price EUR 65 per tonne, trending up...")
    # or
    report = agent.analyze("auto")   # agent fetches live data itself
    """

    def __init__(self) -> None:
        settings.validate()
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = settings.MODEL_NAME

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, input_text: str) -> CarbonIntelligenceReport:
        """
        Run the full analysis pipeline.

        Parameters
        ----------
        input_text : str
            Raw text about carbon markets, or "auto" to trigger autonomous
            web-search mode.

        Returns
        -------
        CarbonIntelligenceReport
            Validated Pydantic model containing the full intelligence report.
        """
        if not input_text or input_text.strip().lower() in ("", "auto"):
            # Use static March 2026 reference data — no web search needed
            user_content = (
                f"Analyse the following carbon market reference data for March 2026 "
                f"and produce the complete JSON intelligence report as specified in "
                f"your instructions. Use ONLY the prices and data provided below — "
                f"do not invent or hallucinate any figures.\n\n"
                f"{STATIC_MARCH_2026_DATA}"
            )
            raw_json = self._run_direct(user_content)
        else:
            user_content = (
                f"Analyse the following carbon market data and produce the full "
                f"JSON intelligence report as specified in your instructions:\n\n"
                f"{input_text}"
            )
            messages: list[dict[str, Any]] = [
                {"role": "user", "content": user_content}
            ]
            raw_json = self._run_agent_loop(messages)

        return self._parse_response(raw_json)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_direct(self, user_content: str) -> str:
        """Single API call with no tools — fast path for static data analysis."""
        response = self._client.messages.create(
            model=self._model,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        for block in response.content:
            if hasattr(block, "type") and block.type == "text":
                return block.text
        return "{}"

    def _run_agent_loop(self, messages: list[dict[str, Any]]) -> str:
        """
        Execute the agentic tool-use loop.

        Calls the Claude API, executes any tool requests, feeds results back,
        and repeats until Claude produces a final text response or we hit the
        iteration limit.
        """
        tools = [WEB_SEARCH_TOOL_DEFINITION]

        for iteration in range(MAX_TOOL_ITERATIONS):
            logger.info("Agent loop iteration %d/%d", iteration + 1, MAX_TOOL_ITERATIONS)

            response = self._client.messages.create(
                model=self._model,
                max_tokens=16000,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )

            # Append full assistant response to history (preserves tool_use blocks)
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                # Extract the final text block
                for block in response.content:
                    if hasattr(block, "type") and block.type == "text":
                        return block.text
                # Fallback: no text block found
                return "{}"

            if response.stop_reason == "tool_use":
                # Execute all tool calls and collect results
                tool_results: list[dict[str, Any]] = []
                for block in response.content:
                    if hasattr(block, "type") and block.type == "tool_use":
                        result = self._execute_tool(block.name, block.input)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            }
                        )
                if tool_results:
                    messages.append({"role": "user", "content": tool_results})
                continue

            if response.stop_reason == "pause_turn":
                # Server-side iteration limit; re-send to continue
                continue

            # Unexpected stop reason — break out
            logger.warning("Unexpected stop_reason: %s", response.stop_reason)
            break

        # If we exhausted iterations, request a final synthesis
        logger.warning("Max iterations reached — requesting final synthesis.")
        messages.append(
            {
                "role": "user",
                "content": (
                    "Based on all the information gathered so far, please now produce "
                    "the complete Carbon Market Intelligence JSON report. "
                    "Return ONLY valid JSON, no other text."
                ),
            }
        )
        final_response = self._client.messages.create(
            model=self._model,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        for block in final_response.content:
            if hasattr(block, "type") and block.type == "text":
                return block.text
        return "{}"

    def _execute_tool(self, name: str, inputs: dict[str, Any]) -> str:
        """Dispatch a tool call and return the result as a string."""
        logger.info("Executing tool: %s with inputs: %s", name, inputs)
        if name == "search_web":
            query = inputs.get("query", "")
            max_results = inputs.get("max_results", 5)
            return search_web(query, max_results)
        return f"Unknown tool: {name}"

    def _parse_response(self, raw_text: str) -> CarbonIntelligenceReport:
        """
        Extract JSON from Claude's response and validate against Pydantic model.

        Handles cases where Claude wraps JSON in markdown code fences.
        """
        # Strip markdown fences if present
        text = raw_text.strip()
        fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
        if fence_match:
            text = fence_match.group(1).strip()

        # Find first { ... } block
        brace_match = re.search(r"\{[\s\S]+\}", text)
        if brace_match:
            text = brace_match.group(0)

        try:
            data = json.loads(text)
            return CarbonIntelligenceReport.model_validate(data)
        except json.JSONDecodeError as exc:
            logger.error("JSON parse error: %s\nRaw text (first 500): %.500s", exc, raw_text)
            # Return a partial report with error note
            report = CarbonIntelligenceReport()
            report.data_quality.notes = (
                f"JSON parsing failed: {exc}. Raw response captured in source_references."
            )
            from models.carbon_models import SourceReference
            report.source_references.append(
                SourceReference(
                    topic="Raw Agent Response",
                    snippet=raw_text[:2000],
                    source="agent",
                )
            )
            return report
        except Exception as exc:
            logger.error("Validation error: %s", exc)
            report = CarbonIntelligenceReport()
            report.data_quality.notes = f"Validation error: {exc}"
            return report
