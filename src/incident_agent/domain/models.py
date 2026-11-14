"""Immutable data contracts shared by incident scenarios and agents."""

from dataclasses import dataclass
from enum import Enum


class ScenarioType(str, Enum):
    """Broad test category for a scenario fixture."""

    NORMAL = "normal"
    CRITICAL_FAILURE = "critical_failure"
    EDGE_AMBIGUOUS = "edge_ambiguous"


class PreviousVersionStatus(str, Enum):
    """Known health state of the previously deployed application version."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Metric:
    """A synthetic metric observation with source and time context."""

    name: str
    value: int | float | str | None
    unit: str
    source: str
    observed_at: str


@dataclass(frozen=True, slots=True)
class LogEntry:
    """A single source-labelled log observation."""

    timestamp: str
    level: str
    service: str
    message: str
    source: str


@dataclass(frozen=True, slots=True)
class DeploymentEvent:
    """A deployment or configuration change related to an incident."""

    timestamp: str
    version: str
    change_type: str
    summary: str
    source: str


@dataclass(frozen=True, slots=True)
class PreviousVersion:
    """Evidence about the health of the version before the current one."""

    status: PreviousVersionStatus
    version: str | None
    source: str


@dataclass(frozen=True, slots=True)
class IncidentScenario:
    """Immutable shared input passed to every agent in a comparison run."""

    scenario_id: str
    scenario_type: ScenarioType
    title: str
    incident_summary: str
    affected_services: tuple[str, ...]
    time_window: str
    metrics: tuple[Metric, ...]
    logs: tuple[LogEntry, ...]
    deployment_history: tuple[DeploymentEvent, ...]
    previous_version: PreviousVersion | None
    missing_evidence: tuple[str, ...]
    conflicting_evidence: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.scenario_id.strip():
            raise ValueError("scenario_id must not be empty")
        for field_name in (
            "affected_services",
            "metrics",
            "logs",
            "deployment_history",
            "missing_evidence",
            "conflicting_evidence",
        ):
            if not isinstance(getattr(self, field_name), tuple):
                raise TypeError(f"{field_name} must be a tuple")


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    """Evidence cited by an agent, with its originating source."""

    source: str
    detail: str


@dataclass(frozen=True, slots=True)
class ToolCallEvidence:
    """Summary of a tool result used by an agent."""

    tool_name: str
    result_summary: str


@dataclass(frozen=True, slots=True)
class AgentResult:
    """Comparable structured response returned by any of the six agents."""

    agent_id: str
    scenario_id: str
    incident_summary: str
    evidence: tuple[EvidenceItem, ...]
    likely_cause: str
    confidence: float | None
    recommended_action: str
    rationale: str
    verification_steps: tuple[str, ...]
    limitations: tuple[str, ...]
    tool_calls: tuple[ToolCallEvidence, ...] = ()

    def __post_init__(self) -> None:
        if not self.agent_id.strip():
            raise ValueError("agent_id must not be empty")
        if not self.scenario_id.strip():
            raise ValueError("scenario_id must not be empty")
        for field_name in (
            "evidence",
            "verification_steps",
            "limitations",
            "tool_calls",
        ):
            if not isinstance(getattr(self, field_name), tuple):
                raise TypeError(f"{field_name} must be a tuple")
        if self.confidence is not None:
            if isinstance(self.confidence, bool) or not isinstance(
                self.confidence, (int, float)
            ):
                raise TypeError("confidence must be a number or None")
            if not 0.0 <= self.confidence <= 1.0:
                raise ValueError("confidence must be between 0.0 and 1.0")
