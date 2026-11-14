import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from incident_agent.agents.classical import LearningAgent
from incident_agent.domain.models import AgentResult, EvidenceItem, IncidentScenario
from incident_agent.domain.scenarios import load_scenarios
from incident_agent.orchestration import IncidentOrchestrator
from incident_agent.storage.experience_store import ExperienceRecord, ExperienceStore

_AGENT_IDS = (
    "simple_reflex",
    "model_based_reflex",
    "goal_based",
    "utility_based",
    "learning",
    "llm_ollama",
)
_SEED_PATH = Path(__file__).resolve().parents[2] / "data" / "learning" / "experience.json"


class StubAgent:
    def __init__(
        self,
        agent_id: str,
        *,
        failure: Exception | None = None,
        received_scenarios: list[IncidentScenario] | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.failure = failure
        self.received_scenarios = received_scenarios

    def analyze(self, scenario: IncidentScenario) -> AgentResult:
        if self.received_scenarios is not None:
            self.received_scenarios.append(scenario)
        if self.failure is not None:
            raise self.failure
        return AgentResult(
            agent_id=self.agent_id,
            scenario_id=scenario.scenario_id,
            incident_summary=scenario.incident_summary,
            evidence=(EvidenceItem(source="test fixture", detail=scenario.title),),
            likely_cause="Test cause",
            confidence=0.5,
            recommended_action="Test action",
            rationale="Deterministic orchestration test result.",
            verification_steps=("Verify test health.",),
            limitations=("Test-only output.",),
        )


class SharedScenarioRunTests(unittest.TestCase):
    def test_all_six_agents_receive_the_same_scenario_and_return_results(self) -> None:
        scenarios = load_scenarios()
        received: list[IncidentScenario] = []
        agents = tuple(
            StubAgent(agent_id, received_scenarios=received) for agent_id in _AGENT_IDS
        )
        orchestrator = IncidentOrchestrator(scenarios=scenarios, agents=agents)

        for scenario_id in scenarios:
            with self.subTest(scenario=scenario_id):
                received.clear()
                run = orchestrator.run(scenario_id)

                self.assertEqual(len(run.executions), 6)
                self.assertEqual(
                    tuple(result.agent_id for result in run.results), _AGENT_IDS
                )
                self.assertEqual(run.failures, ())
                self.assertIs(run.scenario, scenarios[scenario_id])
                self.assertEqual(len(received), 6)
                self.assertTrue(all(scenario is run.scenario for scenario in received))
                self.assertTrue(
                    all(
                        scenario.scenario_id == run.scenario.scenario_id
                        and scenario == run.scenario
                        for scenario in received
                    )
                )

    def test_one_agent_failure_is_visible_without_hiding_other_results(self) -> None:
        agents = tuple(
            StubAgent(
                agent_id,
                failure=RuntimeError("simulated model connection failure")
                if agent_id == "llm_ollama"
                else None,
            )
            for agent_id in _AGENT_IDS
        )

        run = IncidentOrchestrator(agents=agents).run("B")

        self.assertEqual(len(run.executions), 6)
        self.assertEqual(len(run.results), 5)
        self.assertEqual(len(run.failures), 1)
        failure = run.failures[0]
        self.assertEqual(failure.agent_id, "llm_ollama")
        self.assertFalse(failure.succeeded)
        self.assertIsNone(failure.result)
        self.assertEqual(
            failure.error, "RuntimeError: simulated model connection failure"
        )

    def test_learning_store_changes_only_after_explicit_outcome(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            experience_path = Path(temporary_directory) / "experience.json"
            experience_path.write_text(_SEED_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            store = ExperienceStore(experience_path)
            original_document = json.loads(experience_path.read_text(encoding="utf-8"))
            agents = tuple(
                LearningAgent(store)
                if agent_id == "learning"
                else StubAgent(agent_id)
                for agent_id in _AGENT_IDS
            )
            orchestrator = IncidentOrchestrator(agents=agents)

            orchestrator.run("B")

            self.assertEqual(
                json.loads(experience_path.read_text(encoding="utf-8")),
                original_document,
            )
            updated = orchestrator.record_learning_outcome(
                "bounded_load_shedding", succeeded=False
            )
            self.assertEqual(updated, ExperienceRecord(successes=4, failures=1))
            self.assertEqual(
                ExperienceStore(experience_path).get("bounded_load_shedding"),
                updated,
            )

    def test_rejects_an_agent_set_that_omits_a_required_agent(self) -> None:
        agents = tuple(StubAgent(agent_id) for agent_id in _AGENT_IDS[:-1])

        with self.assertRaisesRegex(ValueError, "missing=.*llm_ollama"):
            IncidentOrchestrator(agents=agents)

    def test_unknown_scenario_is_not_replaced_with_a_default(self) -> None:
        orchestrator = IncidentOrchestrator(
            agents=tuple(StubAgent(agent_id) for agent_id in _AGENT_IDS)
        )

        with self.assertRaises(KeyError):
            orchestrator.run("UNKNOWN")


if __name__ == "__main__":
    unittest.main()
