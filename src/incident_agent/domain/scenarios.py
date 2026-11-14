"""Loading and validation for the synthetic incident scenario catalog."""

import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, TypeVar

from incident_agent.domain.models import (
    DeploymentEvent,
    IncidentScenario,
    LogEntry,
    Metric,
    PreviousVersion,
    PreviousVersionStatus,
    ScenarioType,
)

_DEFAULT_SCENARIO_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "scenarios" / "scenarios.json"
)
EnumValue = TypeVar("EnumValue", bound=Enum)


@dataclass(frozen=True, slots=True)
class ScenarioCatalog(Mapping[str, IncidentScenario]):
    """Read-only, ordered collection of uniquely identified scenarios."""

    scenarios: tuple[IncidentScenario, ...]
    _by_id: Mapping[str, IncidentScenario] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.scenarios, tuple):
            raise TypeError("scenarios must be a tuple")
        if not self.scenarios:
            raise ValueError("scenario catalog must contain at least one scenario")

        by_id: dict[str, IncidentScenario] = {}
        for scenario in self.scenarios:
            if not isinstance(scenario, IncidentScenario):
                raise TypeError("scenario catalog items must be IncidentScenario values")
            if scenario.scenario_id in by_id:
                raise ValueError(
                    f"duplicate scenario_id: {scenario.scenario_id!r}"
                )
            by_id[scenario.scenario_id] = scenario
        object.__setattr__(self, "_by_id", MappingProxyType(by_id))

    def __getitem__(self, scenario_id: str) -> IncidentScenario:
        return self._by_id[scenario_id]

    def __iter__(self) -> Iterator[str]:
        return iter(self._by_id)

    def __len__(self) -> int:
        return len(self._by_id)


def load_scenarios(path: str | Path | None = None) -> ScenarioCatalog:
    """Load synthetic scenarios from JSON and validate their input contract."""

    scenario_path = Path(path) if path is not None else _DEFAULT_SCENARIO_PATH
    raw = json.loads(scenario_path.read_text(encoding="utf-8"))
    document = _expect_object(
        raw,
        "scenario document",
        {"schema_version", "data_kind", "scenarios"},
    )
    if type(document["schema_version"]) is not int or document["schema_version"] != 1:
        raise ValueError("scenario document schema_version must be 1")
    if document["data_kind"] != "synthetic":
        raise ValueError("scenario document data_kind must be 'synthetic'")
    if not isinstance(document["scenarios"], list):
        raise ValueError("scenario document 'scenarios' must be a list")

    scenarios = tuple(
        _parse_scenario(item, f"scenarios[{index}]")
        for index, item in enumerate(document["scenarios"])
    )
    return ScenarioCatalog(scenarios)


def _parse_scenario(value: Any, context: str) -> IncidentScenario:
    record = _expect_object(
        value,
        context,
        {
            "scenario_id",
            "scenario_type",
            "title",
            "incident_summary",
            "affected_services",
            "time_window",
            "metrics",
            "logs",
            "deployment_history",
            "previous_version",
            "missing_evidence",
            "conflicting_evidence",
        },
    )
    if not isinstance(record["metrics"], list):
        raise ValueError(f"{context}.metrics must be a list")
    if not isinstance(record["logs"], list):
        raise ValueError(f"{context}.logs must be a list")
    if not isinstance(record["deployment_history"], list):
        raise ValueError(f"{context}.deployment_history must be a list")
    previous_version = record["previous_version"]

    return IncidentScenario(
        scenario_id=_text(record["scenario_id"], f"{context}.scenario_id"),
        scenario_type=_enum_value(
            ScenarioType, record["scenario_type"], f"{context}.scenario_type"
        ),
        title=_text(record["title"], f"{context}.title"),
        incident_summary=_text(
            record["incident_summary"], f"{context}.incident_summary"
        ),
        affected_services=_text_tuple(
            record["affected_services"], f"{context}.affected_services"
        ),
        time_window=_text(record["time_window"], f"{context}.time_window"),
        metrics=tuple(
            _parse_metric(item, f"{context}.metrics[{index}]")
            for index, item in enumerate(record["metrics"])
        ),
        logs=tuple(
            _parse_log(item, f"{context}.logs[{index}]")
            for index, item in enumerate(record["logs"])
        ),
        deployment_history=tuple(
            _parse_deployment(item, f"{context}.deployment_history[{index}]")
            for index, item in enumerate(record["deployment_history"])
        ),
        previous_version=(
            None
            if previous_version is None
            else _parse_previous_version(
                previous_version, f"{context}.previous_version"
            )
        ),
        missing_evidence=_text_tuple(
            record["missing_evidence"], f"{context}.missing_evidence"
        ),
        conflicting_evidence=_text_tuple(
            record["conflicting_evidence"], f"{context}.conflicting_evidence"
        ),
    )


def _parse_metric(value: Any, context: str) -> Metric:
    record = _expect_object(
        value, context, {"name", "value", "unit", "source", "observed_at"}
    )
    metric_value = record["value"]
    if metric_value is not None and (
        isinstance(metric_value, bool)
        or not isinstance(metric_value, (int, float, str))
    ):
        raise ValueError(f"{context}.value must be a number, string, or null")
    return Metric(
        name=_text(record["name"], f"{context}.name"),
        value=metric_value,
        unit=_text(record["unit"], f"{context}.unit"),
        source=_text(record["source"], f"{context}.source"),
        observed_at=_text(record["observed_at"], f"{context}.observed_at"),
    )


def _parse_log(value: Any, context: str) -> LogEntry:
    record = _expect_object(
        value,
        context,
        {"timestamp", "level", "service", "message", "source"},
    )
    return LogEntry(
        timestamp=_text(record["timestamp"], f"{context}.timestamp"),
        level=_text(record["level"], f"{context}.level"),
        service=_text(record["service"], f"{context}.service"),
        message=_text(record["message"], f"{context}.message"),
        source=_text(record["source"], f"{context}.source"),
    )


def _parse_deployment(value: Any, context: str) -> DeploymentEvent:
    record = _expect_object(
        value,
        context,
        {"timestamp", "version", "change_type", "summary", "source"},
    )
    return DeploymentEvent(
        timestamp=_text(record["timestamp"], f"{context}.timestamp"),
        version=_text(record["version"], f"{context}.version"),
        change_type=_text(record["change_type"], f"{context}.change_type"),
        summary=_text(record["summary"], f"{context}.summary"),
        source=_text(record["source"], f"{context}.source"),
    )


def _parse_previous_version(value: Any, context: str) -> PreviousVersion:
    record = _expect_object(
        value, context, {"status", "version", "source"}
    )
    version = record["version"]
    if version is not None:
        version = _text(version, f"{context}.version")
    return PreviousVersion(
        status=_enum_value(
            PreviousVersionStatus, record["status"], f"{context}.status"
        ),
        version=version,
        source=_text(record["source"], f"{context}.source"),
    )


def _expect_object(
    value: Any, context: str, expected_keys: set[str]
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be a JSON object")
    missing = expected_keys - value.keys()
    extra = value.keys() - expected_keys
    if missing:
        raise ValueError(f"{context} is missing fields: {sorted(missing)}")
    if extra:
        raise ValueError(f"{context} has unexpected fields: {sorted(extra)}")
    return value


def _text(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be a non-empty string")
    return value


def _text_tuple(value: Any, context: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{context} must be a list of strings")
    return tuple(
        _text(item, f"{context}[{index}]") for index, item in enumerate(value)
    )


def _enum_value(enum_type: type[EnumValue], value: Any, context: str) -> EnumValue:
    try:
        return enum_type(value)
    except ValueError as error:
        allowed = ", ".join(member.value for member in enum_type)
        raise ValueError(f"{context} must be one of: {allowed}") from error
