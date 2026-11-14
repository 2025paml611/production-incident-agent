"""LangChain/Ollama agent that grounds recommendations in fixture tool results."""

import json
import os
from collections.abc import Mapping, Sequence
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama

from incident_agent.domain.models import (
    AgentResult,
    EvidenceItem,
    IncidentScenario,
    ToolCallEvidence,
)
from incident_agent.tools.evidence_tools import ScenarioEvidenceTools

_DEFAULT_MODEL = "qwen3:4b"
_MIN_DISTINCT_TOOLS = 2
_MAX_CONSECUTIVE_RESPONSES_WITHOUT_TOOLS = 2
_DEFAULT_MAX_TOOL_ROUNDS = 4
_OLLAMA_REQUEST_TIMEOUT_SECONDS = 120
_FINAL_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "incident_summary": {"type": "string"},
        "likely_cause": {"type": "string"},
        "confidence": {
            "anyOf": [
                {"type": "number", "minimum": 0, "maximum": 1},
                {"type": "null"},
            ]
        },
        "recommended_action": {"type": "string"},
        "rationale": {"type": "string"},
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tool_name": {"type": "string"},
                    "quote": {"type": "string"},
                },
                "required": ["tool_name", "quote"],
                "additionalProperties": False,
            },
        },
        "verification_steps": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "incident_summary",
        "likely_cause",
        "confidence",
        "recommended_action",
        "rationale",
        "evidence",
        "verification_steps",
        "limitations",
    ],
    "additionalProperties": False,
}
_SYSTEM_PROMPT = """You are an advisory production incident analyst.
On your first response, call both get_metrics and search_logs using the bound tools.
Do not write prose or simulate tool results before those calls. Never invent
telemetry, deployments, or previous-version health. Treat missing and conflicting
evidence as uncertainty.

After inspecting tool results, recommend a safe, reversible action and respond with
one JSON object only, with exactly these fields:
{
  "incident_summary": "string",
  "likely_cause": "string",
  "confidence": number from 0 to 1 or null,
  "recommended_action": "string",
  "rationale": "string",
  "evidence": [
    {"tool_name": "name of a tool actually called",
     "quote": "an exact substring copied from that tool's result"}
  ],
  "verification_steps": ["string"],
  "limitations": ["string"]
}
Include exact evidence quotes from at least two different tools. Do not put Markdown
around the JSON. For metric citations, copy a metric's evidence field verbatim; for
log citations, copy the message field verbatim. Never paraphrase a citation.
"""


class OllamaIncidentAgent:
    """Investigate a single scenario using LangChain tools and a local Ollama model."""

    agent_id = "llm_ollama"

    def __init__(
        self,
        model_name: str | None = None,
        max_tool_rounds: int = _DEFAULT_MAX_TOOL_ROUNDS,
        chat_model: ChatOllama | None = None,
    ) -> None:
        if isinstance(max_tool_rounds, bool) or not isinstance(max_tool_rounds, int):
            raise TypeError("max_tool_rounds must be an integer")
        if max_tool_rounds < 2:
            raise ValueError("max_tool_rounds must be at least 2")
        configured_name = model_name or os.environ.get(
            "INCIDENT_AGENT_OLLAMA_MODEL", _DEFAULT_MODEL
        )
        if not isinstance(configured_name, str) or not configured_name.strip():
            raise ValueError("model_name must be a non-empty string")

        self.model_name = configured_name.strip()
        self.max_tool_rounds = max_tool_rounds
        self._chat_model = chat_model or ChatOllama(
            model=self.model_name,
            temperature=0,
            num_predict=1024,
            client_kwargs={"timeout": _OLLAMA_REQUEST_TIMEOUT_SECONDS},
        )

    def analyze(self, scenario: IncidentScenario) -> AgentResult:
        """Call at least two distinct tools and return only evidence-grounded output."""

        evidence_tools = ScenarioEvidenceTools(scenario).as_langchain_tools()
        tools_by_name = {tool.name: tool for tool in evidence_tools}
        model_with_tools = self._chat_model.bind_tools(evidence_tools).bind(
            reasoning=False
        )
        json_model = self._chat_model.bind(
            format=_FINAL_RESPONSE_SCHEMA,
            reasoning=False,
        )
        messages: list[BaseMessage] = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=self._scenario_prompt(scenario)),
        ]
        tool_results: dict[str, list[str]] = {}
        tool_evidence: list[ToolCallEvidence] = []
        latest_response: AIMessage | None = None
        consecutive_responses_without_tools = 0

        for _ in range(self.max_tool_rounds):
            if len(tool_results) >= _MIN_DISTINCT_TOOLS:
                messages.append(
                    HumanMessage(
                        content=(
                            "You have evidence from at least two tools. Now return "
                            "the required final JSON object with exact evidence quotes."
                        )
                    )
                )
                response = json_model.invoke(messages)
            else:
                response = model_with_tools.invoke(messages)
            if not isinstance(response, AIMessage):
                raise TypeError("Ollama chat model must return an AIMessage")
            latest_response = response
            if not response.tool_calls:
                if len(tool_results) >= _MIN_DISTINCT_TOOLS:
                    return self._build_result(
                        scenario,
                        response,
                        tool_results,
                        tuple(tool_evidence),
                    )
                consecutive_responses_without_tools += 1
                if (
                    consecutive_responses_without_tools
                    >= _MAX_CONSECUTIVE_RESPONSES_WITHOUT_TOOLS
                ):
                    called_tools = ", ".join(sorted(tool_results)) or "none"
                    raise RuntimeError(
                        "Ollama did not call at least two different evidence tools "
                        f"after {consecutive_responses_without_tools} responses "
                        f"(tools called: {called_tools})."
                    )
                messages.append(response)
                messages.append(
                    HumanMessage(
                        content=(
                            "You have not yet collected evidence from two different "
                            "tools. Call at least one additional relevant tool before "
                            "giving your final answer."
                        )
                    )
                )
                continue

            consecutive_responses_without_tools = 0
            messages.append(AIMessage(content="", tool_calls=response.tool_calls))
            for call in response.tool_calls:
                tool_name = call["name"]
                tool = tools_by_name.get(tool_name)
                if tool is None:
                    raise ValueError(f"Ollama requested an unregistered tool: {tool_name}")
                tool_call_id = call.get("id")
                if not isinstance(tool_call_id, str) or not tool_call_id:
                    raise ValueError(f"Tool call {tool_name!r} did not include a call ID")
                result = tool.invoke(call["args"])
                if not isinstance(result, str):
                    raise TypeError(f"Tool {tool_name!r} returned a non-string result")
                tool_results.setdefault(tool_name, []).append(result)
                tool_evidence.append(
                    ToolCallEvidence(
                        tool_name=tool_name,
                        result_summary=self._summarize_result(result),
                    )
                )
                messages.append(
                    ToolMessage(content=result, tool_call_id=tool_call_id)
                )

        called_tools = ", ".join(sorted(tool_results)) or "none"
        response_state = "no response" if latest_response is None else "response incomplete"
        raise RuntimeError(
            f"Ollama did not complete a grounded investigation within "
            f"{self.max_tool_rounds} tool rounds; at least two different evidence "
            f"tools and a grounded final response are required "
            f"({response_state}; tools called: {called_tools})."
        )

    @staticmethod
    def _scenario_prompt(scenario: IncidentScenario) -> str:
        prompt = {
            "scenario_id": scenario.scenario_id,
            "title": scenario.title,
            "incident_summary": scenario.incident_summary,
            "affected_services": scenario.affected_services,
            "time_window": scenario.time_window,
            "missing_evidence": scenario.missing_evidence,
            "conflicting_evidence": scenario.conflicting_evidence,
            "instructions": (
                "The evidence tools are bound to this exact fixture. First call "
                "get_metrics and search_logs with their default arguments. Return "
                "tool calls only; do not describe or simulate their results."
            ),
        }
        return (
            json.dumps(prompt, ensure_ascii=False)
            + "\nBefore recommending an action, call both get_metrics and search_logs. "
            "Use only evidence returned by those tools."
        )

    def _build_result(
        self,
        scenario: IncidentScenario,
        response: AIMessage,
        tool_results: Mapping[str, Sequence[str]],
        tool_evidence: tuple[ToolCallEvidence, ...],
    ) -> AgentResult:
        distinct_tools_called = set(tool_results)
        if len(distinct_tools_called) < _MIN_DISTINCT_TOOLS:
            raise RuntimeError("At least two different evidence tools must be called")

        payload = self._parse_final_response(response.content)
        citations = payload["evidence"]
        if not isinstance(citations, list) or not citations:
            raise ValueError("Ollama response must contain at least two evidence citations")

        evidence: list[EvidenceItem] = []
        cited_tool_names: set[str] = set()
        for index, citation in enumerate(citations):
            if not isinstance(citation, dict) or set(citation) != {
                "tool_name",
                "quote",
            }:
                raise ValueError(
                    f"evidence[{index}] must contain exactly tool_name and quote"
                )
            tool_name = citation["tool_name"]
            quote = citation["quote"]
            if not isinstance(tool_name, str) or tool_name not in tool_results:
                raise ValueError(f"evidence[{index}] cites a tool that was not called")
            if not isinstance(quote, str) or not quote.strip():
                raise ValueError(f"evidence[{index}].quote must be non-empty text")
            if not any(quote in result for result in tool_results[tool_name]):
                raise ValueError(
                    f"evidence[{index}] quote is not present in the returned "
                    f"{tool_name} evidence"
                )
            cited_tool_names.add(tool_name)
            evidence.append(EvidenceItem(source=tool_name, detail=quote))

        if len(cited_tool_names) < _MIN_DISTINCT_TOOLS:
            raise ValueError("Final recommendation must cite evidence from two different tools")

        limitations = tuple(payload["limitations"])
        limitations += (
            "Evidence is synthetic fixture data, not live production telemetry.",
            f"Recommendation generated with local model {self.model_name}.",
        )
        return AgentResult(
            agent_id=self.agent_id,
            scenario_id=scenario.scenario_id,
            incident_summary=payload["incident_summary"],
            evidence=tuple(evidence),
            likely_cause=payload["likely_cause"],
            confidence=payload["confidence"],
            recommended_action=payload["recommended_action"],
            rationale=payload["rationale"],
            verification_steps=tuple(payload["verification_steps"]),
            limitations=limitations,
            tool_calls=tool_evidence,
        )

    @staticmethod
    def _parse_final_response(content: Any) -> dict[str, Any]:
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Ollama returned an empty final response")
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as error:
            raise ValueError("Ollama final response must be valid JSON") from error
        if not isinstance(payload, dict):
            raise ValueError("Ollama final response must be a JSON object")
        required_fields = {
            "incident_summary",
            "likely_cause",
            "confidence",
            "recommended_action",
            "rationale",
            "evidence",
            "verification_steps",
            "limitations",
        }
        missing_fields = required_fields - payload.keys()
        extra_fields = payload.keys() - required_fields
        if missing_fields or extra_fields:
            raise ValueError(
                f"Ollama response fields invalid; missing={sorted(missing_fields)}, "
                f"unexpected={sorted(extra_fields)}"
            )
        for field_name in (
            "incident_summary",
            "likely_cause",
            "recommended_action",
            "rationale",
        ):
            if not isinstance(payload[field_name], str) or not payload[field_name].strip():
                raise ValueError(f"Ollama response {field_name} must be non-empty text")

        confidence = payload["confidence"]
        if confidence is not None and (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not 0 <= confidence <= 1
        ):
            raise ValueError("Ollama response confidence must be between 0 and 1 or null")

        for field_name in ("verification_steps", "limitations"):
            values = payload[field_name]
            if not isinstance(values, list) or any(
                not isinstance(value, str) or not value.strip() for value in values
            ):
                raise ValueError(
                    f"Ollama response {field_name} must be a list of non-empty strings"
                )
        return payload

    @staticmethod
    def _summarize_result(result: str) -> str:
        try:
            payload = json.loads(result)
        except json.JSONDecodeError:
            return result
        if not isinstance(payload, dict):
            return result
        if "metrics" in payload:
            entries = payload["metrics"]
            return f"Returned {len(entries)} metric(s) for scenario {payload.get('scenario_id')}."
        if "logs" in payload:
            entries = payload["logs"]
            return f"Returned {len(entries)} log entry/entries for scenario {payload.get('scenario_id')}."
        if "deployment_history" in payload:
            entries = payload["deployment_history"]
            return (
                f"Returned {len(entries)} deployment event(s) for scenario "
                f"{payload.get('scenario_id')}."
            )
        if "status" in payload:
            return (
                f"Previous-version status for scenario {payload.get('scenario_id')}: "
                f"{payload['status']}."
            )
        return result
