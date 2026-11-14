"""Opt-in live smoke test for Qwen3 tool calling through LangChain and Ollama."""

import json
import os
import unittest

from langchain_core.tools import tool
from langchain_ollama import ChatOllama

from incident_agent.domain.scenarios import load_scenarios

_RUN_OLLAMA_TESTS = os.environ.get("RUN_OLLAMA_INTEGRATION") == "1"
_MODEL = os.environ.get("INCIDENT_AGENT_OLLAMA_MODEL", "qwen3:4b")
_SCENARIO = load_scenarios()["B"]


@tool
def get_metrics() -> str:
    """Return metrics for the selected synthetic incident scenario."""

    return json.dumps(
        [
            {
                "name": metric.name,
                "value": metric.value,
                "unit": metric.unit,
                "source": metric.source,
            }
            for metric in _SCENARIO.metrics
        ]
    )


@tool
def search_logs() -> str:
    """Return relevant log evidence for the selected synthetic incident scenario."""

    return json.dumps(
        [
            {
                "timestamp": entry.timestamp,
                "level": entry.level,
                "service": entry.service,
                "message": entry.message,
                "source": entry.source,
            }
            for entry in _SCENARIO.logs
        ]
    )


@unittest.skipUnless(
    _RUN_OLLAMA_TESTS,
    "Set RUN_OLLAMA_INTEGRATION=1 to run the local Ollama model smoke test.",
)
class OllamaToolCallingSmokeTest(unittest.TestCase):
    def test_model_calls_two_scenario_tools_and_tools_return_evidence(self) -> None:
        model = ChatOllama(
            model=_MODEL,
            temperature=0,
            validate_model_on_init=True,
        ).bind_tools([get_metrics, search_logs])
        response = model.invoke(
            "Investigate scenario B, a synthetic production incident. "
            "Before recommending an action, call both get_metrics and search_logs. "
            "Use only the evidence returned by those tools."
        )

        calls_by_name = {
            call["name"]: call for call in response.tool_calls
        }
        self.assertIn("get_metrics", calls_by_name)
        self.assertIn("search_logs", calls_by_name)

        tools_by_name = {
            "get_metrics": get_metrics,
            "search_logs": search_logs,
        }
        tool_results = {
            name: tools_by_name[name].invoke(call["args"])
            for name, call in calls_by_name.items()
            if name in tools_by_name
        }
        self.assertEqual(set(tool_results), {"get_metrics", "search_logs"})
        self.assertIn("request_rate", tool_results["get_metrics"])
        self.assertIn("Worker queue", tool_results["search_logs"])


if __name__ == "__main__":
    unittest.main()
