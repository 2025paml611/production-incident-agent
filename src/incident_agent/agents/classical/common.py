"""Shared evidence extraction helpers; agent decision logic remains separate."""

from dataclasses import dataclass

from incident_agent.domain.models import (
    AgentResult,
    DeploymentEvent,
    EvidenceItem,
    IncidentScenario,
    LogEntry,
    Metric,
    ToolCallEvidence,
)


@dataclass(frozen=True, slots=True)
class ScenarioSignals:
    """Current observations derived from a scenario without choosing an action."""

    startup_failure_after_deploy: bool
    database_pool_exhaustion: bool
    traffic_cpu_pressure: bool
    ambiguous_evidence: bool


def numeric_metric(scenario: IncidentScenario, name: str) -> float | None:
    for metric in scenario.metrics:
        if metric.name == name and isinstance(metric.value, (int, float)):
            if not isinstance(metric.value, bool):
                return float(metric.value)
    return None


def scenario_signals(scenario: IncidentScenario) -> ScenarioSignals:
    active = numeric_metric(scenario, "db_pool_active")
    maximum = numeric_metric(scenario, "db_pool_max")
    waiters = numeric_metric(scenario, "db_pool_waiters")
    cpu = numeric_metric(scenario, "cpu_utilization")
    traffic = numeric_metric(scenario, "request_rate")
    ready = numeric_metric(scenario, "application_ready")
    startup_failures = numeric_metric(scenario, "startup_failures")

    log_text = " ".join(log.message.lower() for log in scenario.logs)
    configuration_deployed = any(
        event.change_type.lower() == "configuration"
        for event in scenario.deployment_history
    )
    startup_failure = (
        ready == 0
        or (startup_failures is not None and startup_failures > 0)
        or "startup" in log_text
    )
    pool_exhausted = (
        active is not None
        and maximum is not None
        and maximum > 0
        and active / maximum >= 0.95
        and (waiters is None or waiters > 0)
    ) or "timed out waiting to acquire a database connection" in log_text
    traffic_cpu_pressure = (
        cpu is not None
        and cpu >= 85
        and traffic is not None
        and traffic >= 4000
        and maximum is not None
        and maximum > 0
        and active is not None
        and active / maximum < 0.85
    )

    return ScenarioSignals(
        startup_failure_after_deploy=startup_failure and configuration_deployed,
        database_pool_exhaustion=pool_exhausted,
        traffic_cpu_pressure=traffic_cpu_pressure,
        ambiguous_evidence=bool(scenario.conflicting_evidence)
        or (
            bool(scenario.missing_evidence)
            and not (startup_failure and configuration_deployed)
            and not pool_exhausted
            and not traffic_cpu_pressure
        ),
    )


def scenario_evidence(scenario: IncidentScenario) -> tuple[EvidenceItem, ...]:
    evidence: list[EvidenceItem] = []
    for metric in scenario.metrics:
        evidence.append(_metric_evidence(metric))
    for log in scenario.logs:
        evidence.append(_log_evidence(log))
    for event in scenario.deployment_history:
        evidence.append(_deployment_evidence(event))
    if scenario.previous_version is not None:
        version = scenario.previous_version.version or "version not supplied"
        evidence.append(
            EvidenceItem(
                source=scenario.previous_version.source,
                detail=(
                    f"Previous version {version} health is "
                    f"{scenario.previous_version.status.value}."
                ),
            )
        )
    for item in scenario.missing_evidence:
        evidence.append(
            EvidenceItem(source="scenario evidence inventory", detail=f"Missing: {item}")
        )
    for item in scenario.conflicting_evidence:
        evidence.append(
            EvidenceItem(
                source="scenario evidence inventory", detail=f"Conflict: {item}"
            )
        )
    return tuple(evidence)


def build_result(
    *,
    agent_id: str,
    scenario: IncidentScenario,
    likely_cause: str,
    recommended_action: str,
    rationale: str,
    confidence: float | None,
    verification_steps: tuple[str, ...],
    limitations: tuple[str, ...] | None = None,
    recommended_action_id: str | None = None,
    additional_evidence: tuple[EvidenceItem, ...] = (),
    tool_calls: tuple[ToolCallEvidence, ...] = (),
) -> AgentResult:
    scenario_limitations = tuple(
        f"Missing evidence: {item}" for item in scenario.missing_evidence
    ) + tuple(f"Conflicting evidence: {item}" for item in scenario.conflicting_evidence)
    result_limitations = limitations or scenario_limitations or (
        "Scenario evidence is synthetic and does not represent live telemetry.",
    )
    return AgentResult(
        agent_id=agent_id,
        scenario_id=scenario.scenario_id,
        incident_summary=scenario.incident_summary,
        evidence=scenario_evidence(scenario) + additional_evidence,
        likely_cause=likely_cause,
        confidence=confidence,
        recommended_action=recommended_action,
        rationale=rationale,
        verification_steps=verification_steps,
        limitations=result_limitations,
        tool_calls=tool_calls,
        recommended_action_id=recommended_action_id,
    )


def _metric_evidence(metric: Metric) -> EvidenceItem:
    value = "not reported" if metric.value is None else str(metric.value)
    return EvidenceItem(
        source=metric.source,
        detail=f"{metric.name}={value} {metric.unit} at {metric.observed_at}.",
    )


def _log_evidence(log: LogEntry) -> EvidenceItem:
    return EvidenceItem(
        source=log.source,
        detail=f"{log.timestamp} {log.level} {log.service}: {log.message}",
    )


def _deployment_evidence(event: DeploymentEvent) -> EvidenceItem:
    return EvidenceItem(
        source=event.source,
        detail=(
            f"{event.timestamp}: {event.change_type} change in {event.version}: "
            f"{event.summary}"
        ),
    )
