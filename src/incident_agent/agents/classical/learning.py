"""Learning agent that ranks safe candidate actions using recorded outcomes."""

from dataclasses import dataclass

from incident_agent.agents.classical.common import build_result, scenario_signals
from incident_agent.domain.models import (
    AgentResult,
    EvidenceItem,
    IncidentScenario,
)
from incident_agent.storage.experience_store import (
    ExperienceRecord,
    ExperienceStore,
)


@dataclass(frozen=True, slots=True)
class LearningAction:
    """Scenario-appropriate action candidate with an experience key."""

    action_id: str
    description: str
    likely_cause: str
    verification_steps: tuple[str, ...]


class LearningAgent:
    """Prefer the candidate with the strongest smoothed observed outcome history."""

    agent_id = "learning"

    def __init__(self, experience_store: ExperienceStore | None = None) -> None:
        self.experience_store = experience_store or ExperienceStore()

    def analyze(self, scenario: IncidentScenario) -> AgentResult:
        candidates = self._candidates(scenario)
        ranked = sorted(
            (
                (self.experience_store.get(candidate.action_id), candidate)
                for candidate in candidates
            ),
            key=lambda item: (
                item[0].smoothed_success_rate,
                item[0].total,
            ),
            reverse=True,
        )
        selected_record, selected = ranked[0]
        history = "; ".join(
            f"{candidate.action_id}: {record.successes} successes, "
            f"{record.failures} failures, smoothed rate "
            f"{record.smoothed_success_rate:.2f}"
            for record, candidate in ranked
        )
        history_status = (
            "The selected action has no recorded outcomes; its score is the neutral prior."
            if selected_record.total == 0
            else (
                f"The selected action has {selected_record.successes} successes and "
                f"{selected_record.failures} failures."
            )
        )
        return build_result(
            agent_id=self.agent_id,
            scenario=scenario,
            likely_cause=selected.likely_cause,
            recommended_action=selected.description,
            rationale=(
                f"Ranked scenario-appropriate actions using a Beta(1, 1) smoothed "
                f"success rate. {history}. {history_status} "
                "The rate is an experience-based preference, not a calibrated probability "
                "for the current incident."
            ),
            confidence=None,
            verification_steps=selected.verification_steps,
            limitations=(
                "Experience counts are synthetic demonstration data and may be sparse.",
                "Update counts only after an operator or controlled test records an outcome.",
            )
            + tuple(f"Missing evidence: {item}" for item in scenario.missing_evidence)
            + tuple(
                f"Conflicting evidence: {item}"
                for item in scenario.conflicting_evidence
            ),
            recommended_action_id=selected.action_id,
            additional_evidence=(
                EvidenceItem(
                    source="synthetic seeded experience store",
                    detail=(
                        f"{selected.action_id}: {selected_record.successes} successes, "
                        f"{selected_record.failures} failures; smoothed success rate "
                        f"{selected_record.smoothed_success_rate:.2f}."
                    ),
                ),
            ),
        )

    def record_outcome(self, action_id: str, succeeded: bool) -> ExperienceRecord:
        """Record explicit external feedback; analysis never updates history."""

        return self.experience_store.record_outcome(action_id, succeeded)

    def _candidates(self, scenario: IncidentScenario) -> tuple[LearningAction, ...]:
        signals = scenario_signals(scenario)
        if signals.ambiguous_evidence:
            return (
                LearningAction(
                    "collect_independent_evidence",
                    "Collect independent CPU, DB pool, and deployment evidence before choosing remediation.",
                    "The evidence is incomplete or conflicting.",
                    (
                        "Reconcile metric and log timestamps.",
                        "Collect independent CPU and pool-waiter measurements.",
                        "Review complete deployment history before remediation.",
                    ),
                ),
                LearningAction(
                    "revert_recent_change",
                    "Review a recent change and revert it only if the evidence supports it and an operator approves.",
                    "A recent change is only a hypothesis until deployment history is complete.",
                    (
                        "Confirm the change and its time window.",
                        "Validate service health after any approved rollback.",
                    ),
                ),
                LearningAction(
                    "increase_pool_with_conflicting_metrics",
                    "Do not increase the database pool until the conflicting metrics are reconciled.",
                    "Database pool pressure is not established by the current evidence.",
                    (
                        "Collect pool waiters and database headroom.",
                        "Reassess the diagnosis when metrics agree.",
                    ),
                ),
            )
        if signals.startup_failure_after_deploy:
            return (
                LearningAction(
                    "review_config_rollback",
                    "Review the configuration diff and, if approved, roll back to the last-known-good version.",
                    "The configuration change is associated with application startup failure.",
                    (
                        "Validate configuration keys and secret injection.",
                        "Verify startup and readiness on the approved version.",
                        "Monitor health checks before restoring traffic.",
                    ),
                ),
                LearningAction(
                    "patch_config_forward",
                    "Correct the invalid configuration and deploy a validated fix.",
                    "A missing configuration key is preventing startup.",
                    (
                        "Validate the required configuration in a safe environment.",
                        "Verify readiness and error rate after deployment.",
                    ),
                ),
                LearningAction(
                    "restart_without_config_check",
                    "Avoid repeated restarts without validating the configuration change.",
                    "A restart alone does not address the observed configuration error.",
                    (
                        "Inspect the configuration diff before another startup attempt.",
                        "Verify readiness after an approved correction.",
                    ),
                ),
            )
        if signals.database_pool_exhaustion:
            return (
                LearningAction(
                    "reduce_db_pressure",
                    "Inspect slow queries and reduce connection demand; adjust the pool only after a database-capacity check.",
                    "Database pool saturation is delaying API requests.",
                    (
                        "Check slow queries, locks, pool waiters, and database headroom.",
                        "Verify pool waiters, API latency, and errors after mitigation.",
                    ),
                ),
                LearningAction(
                    "increase_pool_capacity",
                    "Consider a cautious pool-limit change only after verifying database capacity.",
                    "Pool capacity is exhausted, but increasing it without checking DB headroom may shift the bottleneck.",
                    (
                        "Check database connection limits and resource headroom.",
                        "Monitor database health and API latency after an approved change.",
                    ),
                ),
                LearningAction(
                    "restart_database",
                    "Do not restart the database solely to clear connection-pool pressure.",
                    "Pool pressure is observed; a database restart has substantial service risk.",
                    (
                        "Review connection waiters and database health.",
                        "Use a scoped, approved mitigation and verify service recovery.",
                    ),
                ),
            )
        if signals.traffic_cpu_pressure:
            return (
                LearningAction(
                    "bounded_load_shedding",
                    "Apply controlled load-shedding or bounded scaling while profiling CPU.",
                    "High request volume and CPU indicate application-tier pressure; DB usage is normal.",
                    (
                        "Check worker queue depth and per-instance CPU.",
                        "Verify DB connections remain within capacity.",
                        "Monitor latency and errors after an approved change.",
                    ),
                ),
                LearningAction(
                    "bounded_app_scaling",
                    "Increase application capacity within a bounded limit and observe CPU response.",
                    "Application CPU is high during elevated traffic.",
                    (
                        "Confirm available capacity and per-instance CPU.",
                        "Verify latency improves without exhausting database connections.",
                    ),
                ),
                LearningAction(
                    "collect_cpu_profile",
                    "Capture a short CPU profile and inspect the worker queue before changing capacity.",
                    "CPU pressure is observed, but its dominant application workload is unknown.",
                    (
                        "Collect a representative CPU profile.",
                        "Reassess capacity after identifying the CPU-heavy work.",
                    ),
                ),
            )
        return (
            LearningAction(
                "collect_general_evidence",
                "Collect current service metrics, logs, and deployment history before remediation.",
                "No specific cause is supported by the current observations.",
                (
                    "Collect a consistent service and dependency time window.",
                    "Review the evidence and reassess the incident.",
                ),
            ),
            LearningAction(
                "restart_without_diagnosis",
                "Avoid restarting services until a cause and recovery objective are established.",
                "The incident cause is not established.",
                (
                    "Gather relevant metrics and logs.",
                    "Select a scoped action after evidence review.",
                ),
            ),
        )
