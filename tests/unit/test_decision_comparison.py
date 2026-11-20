"""Tests for the shared-scenario decision comparison."""

import unittest

from incident_agent.domain.models import AgentResult, IncidentScenario, ScenarioType
from incident_agent.orchestration.decision_comparison import (
    distinct_recommendation_count,
    explain_decision_differences,
)
from incident_agent.orchestration.incident_orchestrator import AgentExecution, IncidentRun

_AGENT_IDS = (
    "simple_reflex",
    "model_based_reflex",
    "goal_based",
    "utility_based",
    "learning",
    "llm_ollama",
)


def _scenario() -> IncidentScenario:
    return IncidentScenario(
        scenario_id="A",
        scenario_type=ScenarioType.NORMAL,
        title="Pool exhaustion",
        incident_summary="API latency rose.",
        affected_services=("api",),
        time_window="window",
        metrics=(),
        logs=(),
        deployment_history=(),
        previous_version=None,
        missing_evidence=(),
        conflicting_evidence=(),
    )


def _result(agent_id: str, action: str) -> AgentResult:
    return AgentResult(
        agent_id=agent_id,
        scenario_id="A",
        incident_summary="API latency rose.",
        evidence=(),
        likely_cause="Database pool exhaustion.",
        confidence=None,
        recommended_action=action,
        rationale="Test rationale.",
        verification_steps=("Check pool waiters.",),
        limitations=("Synthetic test result.",),
    )


def _run(actions: dict[str, str | None]) -> IncidentRun:
    executions = []
    for agent_id in _AGENT_IDS:
        action = actions[agent_id]
        if action is None:
            executions.append(
                AgentExecution(
                    agent_id=agent_id,
                    result=None,
                    error="test model unavailable",
                )
            )
            continue
        executions.append(
            AgentExecution(
                agent_id=agent_id,
                result=_result(agent_id, action),
                error=None,
            )
        )
    return IncidentRun(scenario=_scenario(), executions=tuple(executions))


class DecisionComparisonTests(unittest.TestCase):
    def test_identical_action_text_is_counted_once_and_mechanisms_stay_visible(self) -> None:
        action = "Inspect slow queries before changing the pool."
        run = _run({agent_id: action for agent_id in _AGENT_IDS})

        explanation = explain_decision_differences(run)

        self.assertEqual(distinct_recommendation_count(run), 1)
        self.assertIn("same recommended-action text", explanation)
        self.assertIn(
            'Simple Reflex recommended "Inspect slow queries before changing the pool." '
            "by matching the current observations to a condition-action rule.",
            explanation,
        )
        self.assertIn("recorded success and failure counts", explanation)
        self.assertIn("evidence returned from its tools", explanation)

    def test_a_different_action_is_called_out_with_its_mechanism(self) -> None:
        actions = {agent_id: "Inspect slow queries." for agent_id in _AGENT_IDS}
        actions["llm_ollama"] = "Scale the database connection pool."
        run = _run(actions)

        explanation = explain_decision_differences(run)

        self.assertEqual(distinct_recommendation_count(run), 2)
        self.assertIn("2 different recommended-action texts", explanation)
        self.assertIn(
            'Local Ollama LLM recommended "Scale the database connection pool." '
            "by grounding the action in evidence returned from its tools.",
            explanation,
        )

    def test_a_failed_agent_is_excluded_from_the_action_count(self) -> None:
        actions = {agent_id: "Collect more evidence." for agent_id in _AGENT_IDS}
        actions["llm_ollama"] = None
        run = _run(actions)

        explanation = explain_decision_differences(run)

        self.assertEqual(distinct_recommendation_count(run), 1)
        self.assertIn(
            "Local Ollama LLM did not return a recommendation: test model unavailable",
            explanation,
        )


if __name__ == "__main__":
    unittest.main()
