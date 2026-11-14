import unittest
from dataclasses import FrozenInstanceError

from incident_agent.domain.models import AgentResult, ScenarioType
from incident_agent.domain.scenarios import ScenarioCatalog, load_scenarios


class ScenarioCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_scenarios()

    def test_loads_all_four_synthetic_scenarios(self) -> None:
        self.assertEqual(tuple(self.catalog), ("A", "B", "C", "D"))
        self.assertEqual(len(self.catalog), 4)

    def test_scenario_a_contains_database_pool_exhaustion_evidence(self) -> None:
        scenario = self.catalog["A"]
        metrics = {metric.name: metric.value for metric in scenario.metrics}

        self.assertEqual(scenario.scenario_type, ScenarioType.NORMAL)
        self.assertEqual(metrics["db_pool_active"], metrics["db_pool_max"])
        self.assertTrue(any("database connection" in log.message for log in scenario.logs))

    def test_scenario_b_keeps_database_connections_normal(self) -> None:
        scenario = self.catalog["B"]
        metrics = {metric.name: metric.value for metric in scenario.metrics}

        self.assertGreater(metrics["cpu_utilization"], 90)
        self.assertLess(metrics["db_pool_active"], metrics["db_pool_max"])
        self.assertEqual(scenario.deployment_history, ())

    def test_scenario_c_records_config_change_and_healthy_previous_version(self) -> None:
        scenario = self.catalog["C"]

        self.assertEqual(scenario.scenario_type, ScenarioType.CRITICAL_FAILURE)
        self.assertEqual(len(scenario.deployment_history), 1)
        self.assertEqual(scenario.deployment_history[0].change_type, "configuration")
        self.assertIsNotNone(scenario.previous_version)
        self.assertEqual(scenario.previous_version.status.value, "healthy")

    def test_scenario_d_exposes_missing_and_conflicting_evidence(self) -> None:
        scenario = self.catalog["D"]

        self.assertEqual(scenario.scenario_type, ScenarioType.EDGE_AMBIGUOUS)
        self.assertGreaterEqual(len(scenario.missing_evidence), 2)
        self.assertGreaterEqual(len(scenario.conflicting_evidence), 2)

    def test_loaded_scenarios_are_immutable(self) -> None:
        with self.assertRaises(FrozenInstanceError):
            self.catalog["A"].title = "modified"

        with self.assertRaises(AttributeError):
            self.catalog["A"].metrics.append(None)

    def test_catalog_rejects_duplicate_ids(self) -> None:
        scenario = self.catalog["A"]

        with self.assertRaisesRegex(ValueError, "duplicate scenario_id"):
            ScenarioCatalog((scenario, scenario))

    def test_unknown_scenario_id_is_not_silently_defaulted(self) -> None:
        with self.assertRaises(KeyError):
            self.catalog["unknown"]

    def test_agent_result_rejects_out_of_range_confidence(self) -> None:
        with self.assertRaisesRegex(ValueError, "confidence must be between"):
            AgentResult(
                agent_id="test-agent",
                scenario_id="A",
                incident_summary="A test incident.",
                evidence=(),
                likely_cause="Unknown",
                confidence=1.1,
                recommended_action="Gather more evidence.",
                rationale="The supplied evidence is incomplete.",
                verification_steps=(),
                limitations=("Cause is uncertain.",),
            )

    def test_agent_result_requires_immutable_collections(self) -> None:
        with self.assertRaisesRegex(TypeError, "evidence must be a tuple"):
            AgentResult(
                agent_id="test-agent",
                scenario_id="A",
                incident_summary="A test incident.",
                evidence=[],
                likely_cause="Unknown",
                confidence=None,
                recommended_action="Gather more evidence.",
                rationale="The supplied evidence is incomplete.",
                verification_steps=(),
                limitations=(),
            )


if __name__ == "__main__":
    unittest.main()
