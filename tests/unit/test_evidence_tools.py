import json
import unittest

from incident_agent.domain.scenarios import load_scenarios
from incident_agent.tools.evidence_tools import ScenarioEvidenceTools


class ScenarioEvidenceToolsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scenarios = load_scenarios()

    def test_metric_tool_returns_evidence_from_bound_scenario(self) -> None:
        tools = ScenarioEvidenceTools(self.scenarios["A"])

        result = json.loads(tools.get_metrics(["db_pool_active"]))

        self.assertEqual(result["scenario_id"], "A")
        self.assertEqual(len(result["metrics"]), 1)
        metric = result["metrics"][0]
        self.assertEqual(metric["name"], "db_pool_active")
        self.assertEqual(metric["value"], 100)
        self.assertIn("source", metric)
        self.assertEqual(metric["evidence"], "db_pool_active=100 connections")
        self.assertEqual(result["not_found"], [])

    def test_metric_tool_reports_requested_names_not_in_fixture(self) -> None:
        result = json.loads(
            ScenarioEvidenceTools(self.scenarios["A"]).get_metrics(
                ["not_a_real_metric"]
            )
        )

        self.assertEqual(result["metrics"], [])
        self.assertEqual(result["not_found"], ["not_a_real_metric"])

    def test_log_search_filters_case_insensitively(self) -> None:
        result = json.loads(
            ScenarioEvidenceTools(self.scenarios["B"]).search_logs(
                query="worker QUEUE"
            )
        )

        self.assertEqual(result["scenario_id"], "B")
        self.assertEqual(len(result["logs"]), 1)
        self.assertIn("Worker queue", result["logs"][0]["message"])
        self.assertEqual(result["logs"][0]["source"], "synthetic application log")

    def test_empty_log_query_returns_all_fixture_logs(self) -> None:
        result = json.loads(
            ScenarioEvidenceTools(self.scenarios["D"]).search_logs()
        )

        self.assertEqual(len(result["logs"]), len(self.scenarios["D"].logs))

    def test_deployment_history_returns_config_change(self) -> None:
        result = json.loads(
            ScenarioEvidenceTools(self.scenarios["C"]).get_deployment_history()
        )

        self.assertEqual(result["scenario_id"], "C")
        self.assertTrue(result["available"])
        self.assertEqual(result["deployment_history"][0]["change_type"], "configuration")
        self.assertEqual(
            result["deployment_history"][0]["source"],
            "synthetic deployment history",
        )

    def test_missing_deployment_history_is_explicit(self) -> None:
        result = json.loads(
            ScenarioEvidenceTools(self.scenarios["A"]).get_deployment_history()
        )

        self.assertFalse(result["available"])
        self.assertTrue(result["missing_evidence"])

    def test_previous_version_health_and_missing_state_are_explicit(self) -> None:
        known = json.loads(
            ScenarioEvidenceTools(self.scenarios["C"]).check_previous_version()
        )
        unknown = json.loads(
            ScenarioEvidenceTools(self.scenarios["A"]).check_previous_version()
        )

        self.assertTrue(known["available"])
        self.assertEqual(known["status"], "healthy")
        self.assertEqual(known["version"], "release-2026.11.13.4")
        self.assertFalse(unknown["available"])
        self.assertEqual(unknown["status"], "not_provided")
        self.assertIn("not supplied", unknown["limitation"])

    def test_langchain_tools_are_bound_to_the_selected_fixture(self) -> None:
        tools = ScenarioEvidenceTools(self.scenarios["C"]).as_langchain_tools()

        self.assertEqual(
            {tool.name for tool in tools},
            {
                "get_metrics",
                "search_logs",
                "get_deployment_history",
                "check_previous_version",
            },
        )
        metrics_tool = next(tool for tool in tools if tool.name == "get_metrics")
        result = json.loads(metrics_tool.invoke({}))

        self.assertEqual(result["scenario_id"], "C")
        application_ready = next(
            metric for metric in result["metrics"] if metric["name"] == "application_ready"
        )
        self.assertEqual(application_ready["value"], 0)

    def test_search_limit_must_be_within_supported_range(self) -> None:
        tools = ScenarioEvidenceTools(self.scenarios["D"])

        with self.assertRaisesRegex(ValueError, "between 1 and 100"):
            tools.search_logs(limit=0)

    def test_metric_filter_rejects_invalid_names(self) -> None:
        tools = ScenarioEvidenceTools(self.scenarios["A"])

        with self.assertRaisesRegex(ValueError, "metric_names"):
            tools.get_metrics([""])


if __name__ == "__main__":
    unittest.main()
