"""LLM Analyst service — Claude integration for ticket reasoning.

4 integration points:
  - analyze_ticket: triage routing + initial hypotheses
  - interpret_evidence: confirm/falsify hypotheses from command output
  - suggest_next_step: explain what to do next and why
  - chat: freeform Q&A grounded in ticket state

All methods degrade gracefully — if ANTHROPIC_API_KEY is unset or the call
fails, a fallback result is returned and the app keeps working.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Add project root to sys.path for scripts.core.llm
_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))


# ── Structured output models ──────────────────────────────────────────────────


class TriageResult(BaseModel):
    routing_suggestion: str = ""
    recommended_pack: str = ""
    initial_hypotheses: List[str] = []
    triage_reasoning: str = ""


class EvidenceInterpretation(BaseModel):
    confirms: List[str] = []
    falsifies: List[str] = []
    suggested_follow_up: List[str] = []
    interpretation: str = ""


class NextStepReasoning(BaseModel):
    action: str = "gather_evidence"
    reasoning: str = ""
    suggested_commands: List[str] = []


class ChatResponse(BaseModel):
    response: str = ""
    hypothesis_updates: Dict[str, str] = {}
    suggested_commands: List[str] = []


# ── LLMAnalyst ────────────────────────────────────────────────────────────────


class LLMAnalyst:
    """Thin Claude wrapper for the 4 reasoning integration points."""

    def __init__(self) -> None:
        self._router_text: Optional[str] = None

    def _load_router_txt(self) -> str:
        if self._router_text is None:
            router_path = _root / "runtime" / "router.txt"
            try:
                self._router_text = router_path.read_text()
            except Exception:
                self._router_text = (
                    "You are QF_Wiz, an MSP service desk copilot. "
                    "Help technicians triage and resolve tickets efficiently."
                )
        return self._router_text

    def _get_client(self):
        """Return an AnthropicClient or None if unavailable."""
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return None
        try:
            from scripts.core.llm import get_client

            return get_client(provider="anthropic")
        except Exception as exc:
            logger.warning("LLM client unavailable: %s", exc)
            return None

    def _safe_complete(
        self,
        system: str,
        messages: List[Dict[str, str]],
        schema: Dict[str, Any],
    ) -> Optional[str]:
        """Run a completion and return raw text, or None on any failure."""
        client = self._get_client()
        if client is None:
            return None
        try:
            schema_instruction = (
                "\n\nYou MUST respond with a single valid JSON object matching "
                f"this schema (no markdown, no extra text):\n{json.dumps(schema, indent=2)}"
            )
            return client.complete(
                system=system + schema_instruction,
                messages=messages,
                max_tokens=1024,
            )
        except Exception as exc:
            logger.warning("LLM call failed: %s", exc)
            return None

    @staticmethod
    def _parse_json(text: str) -> Optional[Dict[str, Any]]:
        """Extract the first JSON object from a response string."""
        try:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass
        return None

    # ── Integration points ────────────────────────────────────────────────────

    def analyze_ticket(self, raw_text: str, cp: Dict[str, Any]) -> TriageResult:
        """Read raw ticket text → routing suggestion + initial hypotheses."""
        system = self._load_router_txt()
        schema = {
            "routing_suggestion": "category or pack family (e.g. 'network', 'auth')",
            "recommended_pack": "specific branch pack id from catalog",
            "initial_hypotheses": ["short hypothesis strings"],
            "triage_reasoning": "2-3 sentence explanation of your routing decision",
        }
        cp_snippet = {k: cp.get(k) for k in ("ticket", "problem", "environment")}
        messages = [
            {
                "role": "user",
                "content": (
                    f"New ticket received. Analyze it and suggest routing.\n\n"
                    f"Raw text:\n{raw_text}\n\n"
                    f"Parsed CP excerpt:\n{json.dumps(cp_snippet, default=str)}"
                ),
            }
        ]
        text = self._safe_complete(system, messages, schema)
        if text is None:
            return TriageResult(triage_reasoning="AI triage unavailable — set ANTHROPIC_API_KEY to enable.")
        data = self._parse_json(text)
        if data:
            valid = {k: v for k, v in data.items() if k in TriageResult.model_fields}
            try:
                return TriageResult(**valid)
            except Exception:
                pass
        return TriageResult(triage_reasoning=text[:500])

    def interpret_evidence(
        self,
        command_id: str,
        output: str,
        hypotheses: List[Dict[str, Any]],
    ) -> EvidenceInterpretation:
        """Given command output + active hypotheses → confirm/falsify + follow-up."""
        system = self._load_router_txt()
        schema = {
            "confirms": ["hypothesis IDs this output supports"],
            "falsifies": ["hypothesis IDs this output rules out"],
            "suggested_follow_up": ["next command IDs worth running"],
            "interpretation": "2-3 sentence plain-English interpretation",
        }
        hyp_summary = [{"id": h.get("id"), "hypothesis": h.get("hypothesis")} for h in hypotheses]
        messages = [
            {
                "role": "user",
                "content": (
                    f"Command '{command_id}' produced this output:\n\n{output}\n\n"
                    f"Active hypotheses:\n{json.dumps(hyp_summary)}\n\n"
                    "Interpret this evidence."
                ),
            }
        ]
        text = self._safe_complete(system, messages, schema)
        if text is None:
            return EvidenceInterpretation(
                interpretation="AI interpretation unavailable — set ANTHROPIC_API_KEY to enable."
            )
        data = self._parse_json(text)
        if data:
            valid = {k: v for k, v in data.items() if k in EvidenceInterpretation.model_fields}
            try:
                return EvidenceInterpretation(**valid)
            except Exception:
                pass
        return EvidenceInterpretation(interpretation=text[:500])

    def suggest_next_step(self, cp: Dict[str, Any]) -> NextStepReasoning:
        """Given full CP state → explain what to do next and why."""
        system = self._load_router_txt()
        schema = {
            "action": "one of: run_test, load_pack, decide, gather_evidence",
            "reasoning": "2-3 sentence explanation of why this is the right move",
            "suggested_commands": ["command IDs from the PS catalog to run next"],
        }
        cp_summary = {
            "css_score": cp.get("css", {}).get("score", 0),
            "css_target": cp.get("css", {}).get("target", 90),
            "decision_status": cp.get("decision", {}).get("status", "triage"),
            "hypotheses": [
                {"id": h.get("id"), "hypothesis": h.get("hypothesis")}
                for h in cp.get("branches", {}).get("active_hypotheses", [])[:3]
            ],
            "tests_run": cp.get("evidence", {}).get("tests_run", []),
            "missing_fields": cp.get("css", {}).get("missing_fields", [])[:5],
        }
        messages = [
            {
                "role": "user",
                "content": (
                    f"What should the technician do next?\n\nCurrent state:\n{json.dumps(cp_summary, indent=2)}"
                ),
            }
        ]
        text = self._safe_complete(system, messages, schema)
        if text is None:
            return NextStepReasoning(reasoning="AI reasoning unavailable — set ANTHROPIC_API_KEY to enable.")
        data = self._parse_json(text)
        if data:
            valid = {k: v for k, v in data.items() if k in NextStepReasoning.model_fields}
            try:
                return NextStepReasoning(**valid)
            except Exception:
                pass
        return NextStepReasoning(reasoning=text[:500])

    def chat(self, cp: Dict[str, Any], user_message: str) -> ChatResponse:
        """Freeform technician Q&A grounded in ticket state."""
        system = self._load_router_txt()
        schema = {
            "response": "direct answer to the technician's question",
            "hypothesis_updates": {"<hypothesis_id>": "confirmed | falsified | unchanged"},
            "suggested_commands": ["command IDs to run based on this exchange"],
        }
        cp_context = {
            "ticket_summary": cp.get("ticket", {}).get("summary", ""),
            "symptoms": cp.get("problem", {}).get("symptoms", []),
            "hypotheses": [
                {"id": h.get("id"), "hypothesis": h.get("hypothesis")}
                for h in cp.get("branches", {}).get("active_hypotheses", [])
            ],
            "tests_run": cp.get("evidence", {}).get("tests_run", []),
            "recent_results": [
                {
                    "command_id": r.get("command_id"),
                    "output": r.get("output", "")[:200],
                }
                for r in cp.get("evidence", {}).get("results", [])[-3:]
            ],
        }
        messages = [
            {
                "role": "user",
                "content": (
                    f"Ticket context:\n{json.dumps(cp_context, default=str)}\n\nTechnician question: {user_message}"
                ),
            }
        ]
        text = self._safe_complete(system, messages, schema)
        if text is None:
            return ChatResponse(response=("AI chat unavailable — set ANTHROPIC_API_KEY to enable Claude integration."))
        data = self._parse_json(text)
        if data:
            valid = {k: v for k, v in data.items() if k in ChatResponse.model_fields}
            try:
                return ChatResponse(**valid)
            except Exception:
                pass
        return ChatResponse(response=text[:1000])


# Singleton — imported by routers
llm_analyst = LLMAnalyst()
