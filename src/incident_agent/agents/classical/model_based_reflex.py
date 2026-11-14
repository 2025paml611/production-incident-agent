"""Model-based reflex agent that accumulates observations into incident state."""

from dataclasses import dataclass

from incident_agent.agents.classical.common import (
    build_result,
    scenario_evidence,
    scenario_signals,
)
from incident_agent.domain.models import AgentResult, IncidentScenario


@dataclass(frozen=True, slots=True)
class IncidentState:
    """Beliefs retained for a scenario across successive observations."""

    scenario_id: str
    time_window: str
    observations: tuple[str, ...]
    conditions: frozenset[str]


class ModelBasedReflexAgent:
    """Update an internal scenario model, then apply rules to the model state."""

    agent_id = "model_based_reflex"

    def __init__(self) -> None:
        self._states: dict[str, IncidentState] = {}

    def analyze(self, scenario: IncidentScenario) -> AgentResult:
        state = self._update_state(scenario)
        if "startup_failure_after_deploy" in state.conditions:
            cause = "The accumulated incident state links startup failure to a config deployment."
            action = (
                "Review the recorded configuration change and, with operator approval, "
                "restore the last-known-good version."
            )
            confidence = 0.91
            steps = (
                "Validate required configuration and secret injection.",
                "Confirm startup and readiness on the approved version.",
                "Check service health and error rate before restoring traffic.",
            )
        elif "database_pool_exhaustion" in state.conditions:
            cause = "Current or prior observations indicate database-pool exhaustion."
            action = (
                "Inspect query duration and connection waiters, then reduce connection "
                "demand or cautiously adjust the pool after capacity review."
            )
            confidence = 0.88
            steps = (
                "Compare current pool utilization with retained observations.",
                "Inspect database waiters, query latency, and database health.",
                "Verify API latency and errors after an approved mitigation.",
            )
        elif "traffic_cpu_pressure" in state.conditions:
            cause = "Accumulated observations indicate traffic-driven application CPU pressure."
            action = (
                "Review queue depth and per-instance CPU; apply bounded scaling or "
                "load-shedding if current telemetry confirms pressure."
            )
            confidence = 0.8
            steps = (
                "Refresh CPU and traffic measurements.",
                "Verify database connections remain within capacity.",
                "Monitor latency, errors, and queue depth after intervention.",
            )
        else:
            cause = "The internal model has insufficient or conflicting evidence for diagnosis."
            action = (
                "Gather independent measurements and deployment evidence before choosing "
                "a high-impact recovery action."
            )
            confidence = 0.3
            steps = (
                "Collect a new metrics sample for the affected time window.",
                "Reconcile logs with independent CPU and database-pool telemetry.",
                "Review deployment history and update the incident model.",
            )

        condition_text = ", ".join(sorted(state.conditions)) or "none detected"
        rationale = (
            f"Model-based rule used {len(state.observations)} retained observations "
            f"across the latest window {state.time_window}; modeled conditions: "
            f"{condition_text}. The model persists per scenario until reset."
        )
        return build_result(
            agent_id=self.agent_id,
            scenario=scenario,
            likely_cause=cause,
            recommended_action=action,
            rationale=rationale,
            confidence=confidence,
            verification_steps=steps,
            limitations=(
                "The internal state accumulates observations for this scenario ID; "
                "reset it when starting a separate incident.",
            )
            + tuple(f"Missing evidence: {item}" for item in scenario.missing_evidence)
            + tuple(
                f"Conflicting evidence: {item}"
                for item in scenario.conflicting_evidence
            ),
        )

    def state_for(self, scenario_id: str) -> IncidentState | None:
        """Return the retained model state for inspection or demonstration."""

        return self._states.get(scenario_id)

    def reset(self, scenario_id: str | None = None) -> None:
        """Clear one scenario's state or reset the complete internal model."""

        if scenario_id is None:
            self._states.clear()
        else:
            self._states.pop(scenario_id, None)

    def _update_state(self, scenario: IncidentScenario) -> IncidentState:
        previous = self._states.get(scenario.scenario_id)
        signals = scenario_signals(scenario)
        current_conditions = {
            name
            for name, matched in (
                ("startup_failure_after_deploy", signals.startup_failure_after_deploy),
                ("database_pool_exhaustion", signals.database_pool_exhaustion),
                ("traffic_cpu_pressure", signals.traffic_cpu_pressure),
                ("ambiguous_evidence", signals.ambiguous_evidence),
            )
            if matched
        }
        current_observations = tuple(
            item.detail for item in scenario_evidence(scenario)
        )
        prior_observations = previous.observations if previous is not None else ()
        observations = tuple(dict.fromkeys(prior_observations + current_observations))
        prior_conditions = previous.conditions if previous is not None else frozenset()
        state = IncidentState(
            scenario_id=scenario.scenario_id,
            time_window=scenario.time_window,
            observations=observations,
            conditions=frozenset(prior_conditions | current_conditions),
        )
        self._states[scenario.scenario_id] = state
        return state
