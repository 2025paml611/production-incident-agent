import json
import unittest
from collections.abc import Sequence
from typing import Any

from langchain_core.messages import AIMessage

from incident_agent.agents.llm.ollama_agent import OllamaIncidentAgent
from incident_agent.domain.scenarios import load_scenarios


class ScriptedChatModel:
    """Deterministic chat-model stand-in for agent control-flow tests."""

    def __init__(self, responses: Sequence[AIMessage]) -> None:
        self.responses = list(responses)
        self.bound_tools: tuple[Any, ...] = ()
        self.bound_options: dict[str, Any] = {}
        self.received_messages: list[list[Any]] = []

    def bind_tools(self, tools: Sequence[Any]) -> ScriptedChatModel:
        self.bound_tools = tuple(tools)
        return self

    def bind(self, **options: Any) -> ScriptedChatModel:
        self.bound_options.update(options)
        return self

    def invoke(self, messages: Sequence[Any]) -> AIMessage:
        self.received_messages.append(list(messages))
        if not self.responses:
            raise AssertionError("Scripted model has no remaining responses")
        return self.responses.pop(0)


def _tool_call(name: str, call_id: str, args: dict[str, Any]) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": name,
                "args": args,
                "id": call_id,
                "type": "tool_call",
            }
        ],
    )


def _final_response(
    *,
    metrics_quote: str = '"name": "cpu_utilization"',
    logs_quote: str = (
        '"message": "Worker queue wait time increased during elevated request volume."'
    ),
) -> AIMessage:
    return AIMessage(
        content=json.dumps(
            {
                "incident_summary": "Traffic and CPU increased in the API scenario.",
                "likely_cause": "Traffic-driven API CPU pressure is likely.",
                "confidence": 0.78,
                "recommended_action": "Use bounded scaling while profiling CPU.",
                "rationale": "The metric and worker-queue log support application-tier pressure.",
                "evidence": [
                    {"tool_name": "get_metrics", "quote": metrics_quote},
                    {"tool_name": "search_logs", "quote": logs_quote},
                ],
                "verification_steps": [
                    "Check per-instance CPU and queue depth.",
                    "Verify latency and error rate after an approved action.",
                ],
                "limitations": ["Per-instance CPU measurements are unavailable."],
            }
        )
    )


class OllamaIncidentAgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scenario = load_scenarios()["B"]

    def test_runs_two_tools_and_returns_grounded_structured_result(self) -> None:
        model = ScriptedChatModel(
            (
                _tool_call(
                    "get_metrics",
                    "metrics-call",
                    {},
                ),
                _tool_call(
                    "search_logs",
                    "logs-call",
                    {},
                ),
                _final_response(),
            )
        )
        agent = OllamaIncidentAgent(chat_model=model)

        result = agent.analyze(self.scenario)

        self.assertEqual(result.agent_id, "llm_ollama")
        self.assertEqual(result.scenario_id, "B")
        self.assertEqual(
            {call.tool_name for call in result.tool_calls},
            {"get_metrics", "search_logs"},
        )
        self.assertEqual({item.source for item in result.evidence}, {"get_metrics", "search_logs"})
        self.assertIn("Worker queue", result.evidence[1].detail)
        self.assertIn("synthetic fixture data", " ".join(result.limitations))
        self.assertEqual(len(model.bound_tools), 4)
        self.assertEqual(model.bound_options["format"]["type"], "object")
        self.assertEqual(len(model.responses), 0)
        self.assertEqual(len(model.received_messages), 3)

    def test_rejects_a_citation_not_present_in_returned_tool_result(self) -> None:
        model = ScriptedChatModel(
            (
                _tool_call(
                    "get_metrics",
                    "metrics-call",
                    {},
                ),
                _tool_call("search_logs", "logs-call", {}),
                _final_response(metrics_quote="CPU is always high"),
            )
        )

        with self.assertRaisesRegex(ValueError, "not present in the returned"):
            OllamaIncidentAgent(chat_model=model).analyze(self.scenario)

    def test_rejects_malformed_final_json(self) -> None:
        model = ScriptedChatModel(
            (
                _tool_call(
                    "get_metrics",
                    "metrics-call",
                    {},
                ),
                _tool_call("search_logs", "logs-call", {}),
                AIMessage(content="This is not JSON"),
            )
        )

        with self.assertRaisesRegex(ValueError, "must be valid JSON"):
            OllamaIncidentAgent(chat_model=model).analyze(self.scenario)

    def test_rejects_citations_from_fewer_than_two_tools(self) -> None:
        response = _final_response()
        payload = json.loads(response.content)
        payload["evidence"] = [payload["evidence"][0], payload["evidence"][0]]
        response = AIMessage(content=json.dumps(payload))
        model = ScriptedChatModel(
            (
                _tool_call(
                    "get_metrics",
                    "metrics-call",
                    {},
                ),
                _tool_call("search_logs", "logs-call", {}),
                response,
            )
        )

        with self.assertRaisesRegex(ValueError, "two different tools"):
            OllamaIncidentAgent(chat_model=model).analyze(self.scenario)

    def test_retries_when_model_finalizes_before_two_distinct_tool_calls(self) -> None:
        premature_final = _final_response()
        model = ScriptedChatModel(
            (
                _tool_call(
                    "get_metrics",
                    "metrics-call",
                    {},
                ),
                premature_final,
                premature_final,
            )
        )

        with self.assertRaisesRegex(RuntimeError, "at least two different evidence tools"):
            OllamaIncidentAgent(chat_model=model, max_tool_rounds=3).analyze(
                self.scenario
            )
        self.assertEqual(len(model.received_messages), 3)

    def test_rejects_unregistered_tool_calls(self) -> None:
        model = ScriptedChatModel(
            (_tool_call("read_unregistered_source", "unexpected-call", {}),)
        )

        with self.assertRaisesRegex(ValueError, "unregistered tool"):
            OllamaIncidentAgent(chat_model=model).analyze(self.scenario)

    def test_model_errors_are_not_converted_to_success_results(self) -> None:
        model = ScriptedChatModel(())

        with self.assertRaisesRegex(AssertionError, "no remaining responses"):
            OllamaIncidentAgent(chat_model=model).analyze(self.scenario)

    def test_requires_at_least_two_tool_rounds(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least 2"):
            OllamaIncidentAgent(max_tool_rounds=1)


if __name__ == "__main__":
    unittest.main()
