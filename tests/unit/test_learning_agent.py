import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from incident_agent.agents.classical.learning import LearningAgent
from incident_agent.domain.scenarios import load_scenarios
from incident_agent.storage.experience_store import ExperienceRecord, ExperienceStore

_SEED_PATH = Path(__file__).resolve().parents[2] / "data" / "learning" / "experience.json"


class LearningAgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scenarios = load_scenarios()

    def test_learning_agent_uses_counts_and_explains_the_selected_action(self) -> None:
        store = ExperienceStore()
        before = store.actions.copy()
        result = LearningAgent(store).analyze(self.scenarios["B"])

        self.assertEqual(result.recommended_action_id, "bounded_load_shedding")
        self.assertIn("4 successes, 0 failures", result.rationale)
        self.assertTrue(
            any(
                item.source == "synthetic seeded experience store"
                for item in result.evidence
            )
        )
        self.assertEqual(store.actions, before)

    def test_explicit_feedback_changes_counts_and_can_change_preference(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            experience_path = Path(temporary_directory) / "experience.json"
            experience_path.write_text(_SEED_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            store = ExperienceStore(experience_path)
            agent = LearningAgent(store)

            initial_result = agent.analyze(self.scenarios["B"])
            self.assertEqual(initial_result.recommended_action_id, "bounded_load_shedding")
            updated_record = None
            for _ in range(7):
                updated_record = store.record_outcome(
                    "bounded_load_shedding", succeeded=False
                )
            self.assertEqual(updated_record, ExperienceRecord(successes=4, failures=7))
            updated_agent = LearningAgent(ExperienceStore(experience_path))
            updated_result = updated_agent.analyze(self.scenarios["B"])

            self.assertEqual(updated_result.recommended_action_id, "bounded_app_scaling")

    def test_new_store_reads_persisted_feedback(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            experience_path = Path(temporary_directory) / "experience.json"
            experience_path.write_text(_SEED_PATH.read_text(encoding="utf-8"), encoding="utf-8")
            store = ExperienceStore(experience_path)
            updated = store.record_outcome("review_config_rollback", succeeded=True)

            reloaded = ExperienceStore(experience_path)
            self.assertEqual(updated, ExperienceRecord(successes=5, failures=0))
            self.assertEqual(reloaded.get("review_config_rollback"), updated)
            document = json.loads(experience_path.read_text(encoding="utf-8"))
            self.assertEqual(document["actions"]["review_config_rollback"]["successes"], 5)

    def test_unknown_action_has_explicit_neutral_prior(self) -> None:
        record = ExperienceStore().get("action-with-no-history")

        self.assertEqual(record.total, 0)
        self.assertEqual(record.smoothed_success_rate, 0.5)


if __name__ == "__main__":
    unittest.main()
