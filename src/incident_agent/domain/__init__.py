"""Shared incident and agent-result domain contracts."""

from incident_agent.domain.models import (
    AgentResult,
    DeploymentEvent,
    EvidenceItem,
    IncidentScenario,
    LogEntry,
    Metric,
    PreviousVersion,
    PreviousVersionStatus,
    ScenarioType,
    ToolCallEvidence,
)
from incident_agent.domain.scenarios import ScenarioCatalog, load_scenarios

__all__ = [
    "AgentResult",
    "DeploymentEvent",
    "EvidenceItem",
    "IncidentScenario",
    "LogEntry",
    "Metric",
    "PreviousVersion",
    "PreviousVersionStatus",
    "ScenarioCatalog",
    "ScenarioType",
    "ToolCallEvidence",
    "load_scenarios",
]
