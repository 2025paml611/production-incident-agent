"""Validated persistence for explicit learning-agent action outcomes."""

import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from collections.abc import Mapping
from typing import Any

_DEFAULT_EXPERIENCE_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "learning"
    / "experience.json"
)


@dataclass(frozen=True, slots=True)
class ExperienceRecord:
    """Success and failure counts for one action identifier."""

    successes: int = 0
    failures: int = 0

    def __post_init__(self) -> None:
        for field_name in ("successes", "failures"):
            count = getattr(self, field_name)
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")

    @property
    def total(self) -> int:
        return self.successes + self.failures

    @property
    def smoothed_success_rate(self) -> float:
        """Beta(1, 1) posterior mean used as a decision preference."""

        return (self.successes + 1) / (self.total + 2)


class ExperienceStore:
    """Load, query, and explicitly update experience records stored as JSON."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else _DEFAULT_EXPERIENCE_PATH
        self._actions = self._load()

    @property
    def actions(self) -> Mapping[str, ExperienceRecord]:
        """Return a read-only snapshot of known action histories."""

        return MappingProxyType(self._actions.copy())

    def get(self, action_id: str) -> ExperienceRecord:
        _require_action_id(action_id)
        return self._actions.get(action_id, ExperienceRecord())

    def record_outcome(self, action_id: str, succeeded: bool) -> ExperienceRecord:
        """Persist one explicitly observed outcome for an action."""

        _require_action_id(action_id)
        if not isinstance(succeeded, bool):
            raise TypeError("succeeded must be a bool outcome")

        current = self.get(action_id)
        updated = ExperienceRecord(
            successes=current.successes + int(succeeded),
            failures=current.failures + int(not succeeded),
        )
        updated_actions = self._actions.copy()
        updated_actions[action_id] = updated
        self._write(updated_actions)
        self._actions = updated_actions
        return updated

    def _load(self) -> dict[str, ExperienceRecord]:
        document = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValueError("experience document must be a JSON object")
        if set(document) != {"schema_version", "data_kind", "actions"}:
            raise ValueError("experience document must contain schema_version, data_kind, and actions")
        if type(document["schema_version"]) is not int or document["schema_version"] != 1:
            raise ValueError("experience schema_version must be 1")
        if document["data_kind"] != "synthetic_seeded_outcomes":
            raise ValueError("experience data_kind must be 'synthetic_seeded_outcomes'")
        actions = document["actions"]
        if not isinstance(actions, dict):
            raise ValueError("experience actions must be a JSON object")

        records: dict[str, ExperienceRecord] = {}
        for action_id, counts in actions.items():
            _require_action_id(action_id)
            if not isinstance(counts, dict) or set(counts) != {"successes", "failures"}:
                raise ValueError(f"experience record for {action_id!r} is malformed")
            records[action_id] = ExperienceRecord(
                successes=counts["successes"],
                failures=counts["failures"],
            )
        return records

    def _write(self, actions: dict[str, ExperienceRecord]) -> None:
        document = {
            "schema_version": 1,
            "data_kind": "synthetic_seeded_outcomes",
            "actions": {
                action_id: {
                    "successes": record.successes,
                    "failures": record.failures,
                }
                for action_id, record in sorted(actions.items())
            },
        }
        temporary_path = self.path.with_name(f".{self.path.name}.tmp")
        try:
            temporary_path.write_text(
                json.dumps(document, indent=2) + "\n",
                encoding="utf-8",
            )
            temporary_path.replace(self.path)
        finally:
            temporary_path.unlink(missing_ok=True)


def _require_action_id(action_id: Any) -> None:
    if not isinstance(action_id, str) or not action_id.strip():
        raise ValueError("action_id must be a non-empty string")
