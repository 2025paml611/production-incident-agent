import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from streamlit.testing.v1 import AppTest

from incident_agent.agents.classical import LearningAgent
from incident_agent.domain.models import AgentResult, EvidenceItem, IncidentScenario
from incident_agent.domain.scenarios import load_scenarios
from incident_agent.orchestration import IncidentOrchestrator
from incident_agent.storage.experience_store import ExperienceStore

_AGENT_IDS = (
    "simple_reflex",
    "model_based_reflex",
    "goal_based",
    "utility_based",
    "learning",
    "llm_ollama",
)
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_SEED_PATH = _REPOSITORY_ROOT / "data" / "learning" / "experience.json"
_APP_PATH = _REPOSITORY_ROOT / "src" / "incident_agent" / "app" / "streamlit_app.py"


class UIStubAgent:
    def __init__(self, agent_id: str, *, failure: Exception | None = None) -> None:
        self.agent_id = agent_id
        self.failure = failure

    def analyze(self, scenario: IncidentScenario) -> AgentResult:
        if self.failure is not None:
            raise self.failure
        return AgentResult(
            agent_id=self.agent_id,
            scenario_id=scenario.scenario_id,
            incident_summary=scenario.incident_summary,
            evidence=(EvidenceItem(source="UI test fixture", detail=scenario.title),),
            likely_cause=f"Likely cause for {scenario.scenario_id}",
            confidence=0.75,
            recommended_action=f"Safe action for {scenario.scenario_id}",
            rationale="The deterministic UI test agent uses the selected fixture.",
            verification_steps=("Verify service health.",),
            limitations=("Synthetic UI test result.",),
            recommended_action_id=(
                "bounded_load_shedding" if self.agent_id == "learning" else None
            ),
        )


class StreamlitUIFlowTests(unittest.TestCase):
    def _orchestrator(
        self,
        experience_path: Path,
        *,
        failed_agent: str | None = None,
    ) -> tuple[IncidentOrchestrator, ExperienceStore]:
        shutil.copyfile(_SEED_PATH, experience_path)
        store = ExperienceStore(experience_path)
        agents = tuple(
            LearningAgent(store)
            if agent_id == "learning"
            else UIStubAgent(
                agent_id,
                failure=RuntimeError("test model unavailable")
                if agent_id == failed_agent
                else None,
            )
            for agent_id in _AGENT_IDS
        )
        return IncidentOrchestrator(agents=agents), store

    def test_metric_snapshot_formats_supplied_values_and_marks_missing_data(self) -> None:
        app = AppTest.from_file(str(_APP_PATH), default_timeout=30).run()

        metrics = {item.label: item.value for item in app.metric}
        self.assertEqual(metrics["CPU utilization"], "61%")
        self.assertEqual(metrics["Request rate"], "Not supplied")
        self.assertEqual(metrics["API latency (p95)"], "2,450 ms")
        self.assertEqual(
            metrics["Database pool usage"],
            "100 / 100 connections (100%)",
        )

        app.selectbox[0].select(
            next(
                option
                for option in app.selectbox[0].options
                if option.startswith("B ")
            )
        ).run()
        metrics = {item.label: item.value for item in app.metric}
        self.assertEqual(metrics["CPU utilization"], "96%")
        self.assertEqual(metrics["Request rate"], "5,100 req/s")
        self.assertEqual(metrics["API latency (p95)"], "1,680 ms")
        self.assertEqual(
            metrics["Database pool usage"],
            "32 / 100 connections (32%)",
        )
        self.assertTrue(
            any("not live telemetry" in item.value for item in app.caption)
        )
        self.assertTrue(
            any("synthetic metrics fixture" in item.value for item in app.markdown)
        )

        app.selectbox[0].select(
            next(option for option in app.selectbox[0].options if option.startswith("C "))
        ).run()
        metrics = {item.label: item.value for item in app.metric}
        self.assertEqual(metrics["CPU utilization"], "Not supplied")
        self.assertEqual(metrics["Request rate"], "Not supplied")
        self.assertEqual(metrics["Database pool usage"], "Not supplied")

        app.selectbox[0].select(
            next(
                option
                for option in app.selectbox[0].options
                if option.startswith("D ")
            )
        ).run()
        metrics = {item.label: item.value for item in app.metric}
        self.assertEqual(metrics["CPU utilization"], "91%")
        self.assertEqual(metrics["API latency (p95)"], "1,900 ms")
        self.assertEqual(
            metrics["Database pool usage"],
            "18 / 20 connections (90%)",
        )
        self.assertTrue(
            any("Aggregate CPU metric" in item.value for item in app.warning)
        )

    def test_scenario_selector_runs_comparison_and_records_only_explicit_feedback(
        self,
    ) -> None:
        with TemporaryDirectory() as temporary_directory:
            orchestrator, store = self._orchestrator(
                Path(temporary_directory) / "experience.json"
            )
            original_record = store.get("bounded_load_shedding")
            app = AppTest.from_file(str(_APP_PATH), default_timeout=30)
            app.session_state["incident_orchestrator"] = orchestrator
            app.run()

            self.assertEqual(len(app.selectbox), 1)
            self.assertEqual(len(app.selectbox[0].options), 4)
            self.assertTrue(
                all(
                    option.startswith(("A ", "B ", "C ", "D "))
                    for option in app.selectbox[0].options
                )
            )
            app.selectbox[0].select(app.selectbox[0].options[1]).run()
            self.assertTrue(any("Scenario B:" in item.value for item in app.subheader))
            self.assertEqual(store.get("bounded_load_shedding"), original_record)

            app.button(key="run-comparison").click().run()

            self.assertTrue(any("Agent comparison" in item.value for item in app.subheader))
            self.assertTrue(any("Simple Reflex" in item.value for item in app.markdown))
            agent_expanders = [
                item
                for item in app.expander
                if item.label.endswith(("— success", "— failed"))
            ]
            self.assertEqual(len(agent_expanders), 6)
            self.assertTrue(any("Local Ollama LLM — success" == item.label for item in app.expander))
            self.assertEqual(store.get("bounded_load_shedding"), original_record)

            app.button(key="learning-success-B-bounded_load_shedding").click().run()

            updated_record = store.get("bounded_load_shedding")
            self.assertEqual(updated_record.successes, original_record.successes + 1)
            self.assertEqual(updated_record.failures, original_record.failures)
            self.assertTrue(
                any(
                    "Recorded one success" in item.value
                    and f"{updated_record.successes} successes" in item.value
                    for item in app.success
                )
            )

    def test_agent_failure_is_shown_as_an_error_in_the_comparison(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            orchestrator, _ = self._orchestrator(
                Path(temporary_directory) / "experience.json",
                failed_agent="llm_ollama",
            )
            app = AppTest.from_file(str(_APP_PATH), default_timeout=30)
            app.session_state["incident_orchestrator"] = orchestrator
            app.run()
            app.selectbox[0].select(app.selectbox[0].options[2]).run()
            app.button(key="run-comparison").click().run()

            self.assertTrue(
                any("1 of 6 agents failed" in item.value for item in app.warning)
            )
            self.assertTrue(
                any("Local Ollama LLM failed" in item.value for item in app.error)
            )
            self.assertTrue(any("Scenario C:" in item.value for item in app.subheader))


if __name__ == "__main__":
    unittest.main()
