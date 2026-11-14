"""Opt-in live test for the grounded LangChain/Ollama incident agent."""

import os
import unittest

from incident_agent.agents.llm.ollama_agent import OllamaIncidentAgent
from incident_agent.domain.scenarios import load_scenarios

_RUN_OLLAMA_TESTS = os.environ.get("RUN_OLLAMA_INTEGRATION") == "1"


@unittest.skipUnless(
    _RUN_OLLAMA_TESTS,
    "Set RUN_OLLAMA_INTEGRATION=1 to run the local Ollama integration test.",
)
class OllamaToolCallingSmokeTest(unittest.TestCase):
    def test_agent_calls_tools_and_cites_their_returned_evidence(self) -> None:
        scenario = load_scenarios()["B"]
        result = OllamaIncidentAgent(max_tool_rounds=3).analyze(scenario)

        called_tools = {call.tool_name for call in result.tool_calls}
        cited_tools = {item.source for item in result.evidence}
        self.assertEqual(result.scenario_id, scenario.scenario_id)
        self.assertGreaterEqual(len(called_tools), 2)
        self.assertGreaterEqual(len(cited_tools), 2)
        self.assertTrue(cited_tools.issubset(called_tools))
        self.assertTrue(all(item.detail.strip() for item in result.evidence))
        self.assertTrue(result.likely_cause.strip())
        self.assertTrue(result.recommended_action.strip())
        self.assertTrue(result.verification_steps)
        self.assertTrue(result.limitations)


if __name__ == "__main__":
    unittest.main()
