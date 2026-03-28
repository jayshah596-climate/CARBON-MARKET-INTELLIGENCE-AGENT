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
            user_content = AUTO_SEARCH_PROMPT
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
