import unittest
from dataclasses import replace

from incident_agent.agents.classical import (
    GoalBasedAgent,
    LearningAgent,
    ModelBasedReflexAgent,
    SimpleReflexAgent,
    UtilityBasedAgent,
)
from incident_agent.domain.scenarios import load_scenarios


class ClassicalAgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scenarios = load_scenarios()

    def test_simple_reflex_matches_current_condition_action_rules(self) -> None:
        agent = SimpleReflexAgent()
        expected_actions = {
            "A": "Inspect slow or blocked queries",
            "B": "bounded, reversible capacity increase",
            "C": "review the configuration change",
            "D": "collect independent CPU",
        }

        for scenario_id, expected in expected_actions.items():
            with self.subTest(scenario=scenario_id):
                result = agent.analyze(self.scenarios[scenario_id])
                self.assertEqual(result.scenario_id, scenario_id)
                self.assertIn(expected.lower(), result.recommended_action.lower())

    def test_model_based_reflex_retains_observations_until_reset(self) -> None:
        agent = ModelBasedReflexAgent()
        original = self.scenarios["A"]
        first_result = agent.analyze(original)
        first_state = agent.state_for("A")
        self.assertIsNotNone(first_state)
        self.assertIn("database_pool_exhaustion", first_state.conditions)

        later_observation = replace(
            original,
            metrics=(),
            logs=(),
            deployment_history=(),
            missing_evidence=(),
        )
        second_result = agent.analyze(later_observation)
        self.assertIn("database-pool exhaustion", second_result.likely_cause)
        self.assertEqual(first_result.recommended_action, second_result.recommended_action)
        self.assertGreaterEqual(
            len(agent.state_for("A").observations), len(first_state.observations)
        )

        agent.reset("A")
        self.assertIsNone(agent.state_for("A"))
        reset_result = agent.analyze(later_observation)
        self.assertIn("insufficient or conflicting evidence", reset_result.likely_cause)

    def test_goal_based_agent_explains_goal_plan(self) -> None:
        clear_incident = GoalBasedAgent().analyze(self.scenarios["A"])
        ambiguous_incident = GoalBasedAgent().analyze(self.scenarios["D"])

        self.assertIn("satisfy these goals", clear_incident.rationale)
        self.assertIn("evidence-first plan", ambiguous_incident.rationale)
        self.assertIn("reduce uncertainty", ambiguous_incident.recommended_action)

    def test_utility_based_agent_reports_candidate_scores(self) -> None:
        result = UtilityBasedAgent().analyze(self.scenarios["B"])

        self.assertIn("using weights", result.rationale)
        self.assertIn("bounded_capacity=", result.rationale)
        self.assertIn("Selected bounded_capacity", result.rationale)
        self.assertIsNone(result.confidence)

    def test_all_five_classical_agents_handle_every_fixture(self) -> None:
        agents = (
            SimpleReflexAgent(),
            ModelBasedReflexAgent(),
            GoalBasedAgent(),
            UtilityBasedAgent(),
            LearningAgent(),
        )

        for agent in agents:
            for scenario in self.scenarios.scenarios:
                with self.subTest(agent=agent.agent_id, scenario=scenario.scenario_id):
                    result = agent.analyze(scenario)
                    self.assertEqual(result.scenario_id, scenario.scenario_id)
                    self.assertTrue(result.incident_summary)
                    self.assertTrue(result.evidence)
                    self.assertTrue(result.likely_cause)
                    self.assertTrue(result.recommended_action)
                    self.assertTrue(result.verification_steps)
                    self.assertTrue(result.limitations)


if __name__ == "__main__":
    unittest.main()
