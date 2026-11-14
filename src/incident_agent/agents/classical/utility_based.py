"""Utility-based agent that scores candidate actions against explicit factors."""

from dataclasses import dataclass

from incident_agent.agents.classical.common import build_result, scenario_signals
from incident_agent.domain.models import AgentResult, IncidentScenario

_WEIGHTS = {
    "recovery_impact": 0.35,
    "safety": 0.25,
    "reversibility": 0.25,
    "evidence_fit": 0.15,
}


@dataclass(frozen=True, slots=True)
class ActionCandidate:
    """Candidate response with factor scores on a one-to-five scale."""

    action_id: str
    description: str
    recovery_impact: int
    safety: int
    reversibility: int
    evidence_fit: int

    def __post_init__(self) -> None:
        if not self.action_id.strip() or not self.description.strip():
            raise ValueError("action candidates require an ID and description")
        for factor in _WEIGHTS:
            score = getattr(self, factor)
            if isinstance(score, bool) or not isinstance(score, int) or not 1 <= score <= 5:
                raise ValueError(f"{factor} must be an integer from 1 to 5")

    @property
    def utility(self) -> float:
        return sum(
            getattr(self, factor) * weight for factor, weight in _WEIGHTS.items()
        )


class UtilityBasedAgent:
    """Choose the action with the highest weighted expected utility."""

    agent_id = "utility_based"

    def analyze(self, scenario: IncidentScenario) -> AgentResult:
        signals = scenario_signals(scenario)
        if signals.ambiguous_evidence:
            likely_cause = "The available observations are conflicting or incomplete."
            candidates = (
                ActionCandidate(
                    "collect_evidence",
                    "Collect independent CPU, DB pool, and deployment evidence before remediation.",
                    2,
                    5,
                    5,
                    5,
                ),
                ActionCandidate(
                    "revert_change",
                    "Review and revert a recent change if confirmed and approved.",
                    3,
                    3,
                    4,
                    2,
                ),
                ActionCandidate(
                    "increase_pool",
                    "Increase the database connection pool immediately.",
                    2,
                    1,
                    1,
                    1,
                ),
            )
            verification = (
                "Reconcile independent telemetry and log timestamps.",
                "Confirm a root-cause hypothesis before high-impact changes.",
                "Re-score candidate actions when evidence is complete.",
            )
        elif signals.startup_failure_after_deploy:
            likely_cause = "A configuration deployment is associated with startup failure."
            candidates = (
                ActionCandidate(
                    "review_rollback",
                    "Review the config diff and, if approved, roll back to the last-known-good version.",
                    5,
                    5,
                    5,
                    5,
                ),
                ActionCandidate(
                    "forward_fix",
                    "Correct the configuration and deploy a validated fix.",
                    4,
                    4,
                    4,
                    4,
                ),
                ActionCandidate(
                    "restart_only",
                    "Repeatedly restart without validating the configuration.",
                    1,
                    1,
                    2,
                    1,
                ),
            )
            verification = (
                "Validate configuration keys and secret injection.",
                "Confirm startup and readiness after the approved change.",
                "Monitor health checks and errors before restoring traffic.",
            )
        elif signals.database_pool_exhaustion:
            likely_cause = "Pool saturation and connection waiters are consistent with database-pool exhaustion."
            candidates = (
                ActionCandidate(
                    "reduce_db_pressure",
                    "Inspect slow queries and reduce connection demand; adjust the pool only after a capacity check.",
                    5,
                    5,
                    5,
                    5,
                ),
                ActionCandidate(
                    "increase_pool",
                    "Increase the pool limit without checking database headroom.",
                    4,
                    2,
                    2,
                    3,
                ),
                ActionCandidate(
                    "restart_database",
                    "Restart the database to clear connection pressure.",
                    3,
                    1,
                    1,
                    2,
                ),
            )
            verification = (
                "Check query latency, database headroom, and pool waiters.",
                "Verify API latency and errors after one approved mitigation.",
                "Confirm the database remains healthy under recovered traffic.",
            )
        elif signals.traffic_cpu_pressure:
            likely_cause = "Traffic-driven application CPU pressure is more likely than DB connection saturation."
            candidates = (
                ActionCandidate(
                    "bounded_capacity",
                    "Apply bounded application scaling or controlled load-shedding while profiling CPU.",
                    5,
                    4,
                    5,
                    5,
                ),
                ActionCandidate(
                    "profile_first",
                    "Collect a short CPU profile and inspect the worker queue before changing capacity.",
                    3,
                    5,
                    5,
                    4,
                ),
                ActionCandidate(
                    "restart_database",
                    "Restart the database despite normal connection usage.",
                    1,
                    1,
                    1,
                    1,
                ),
            )
            verification = (
                "Compare per-instance CPU and worker queue depth.",
                "Confirm DB connection utilization remains within limits.",
                "Verify latency and error rate improve without a new bottleneck.",
            )
        else:
            likely_cause = "Evidence is insufficient to identify a specific failure mechanism."
            candidates = (
                ActionCandidate(
                    "collect_evidence",
                    "Collect current metrics, logs, and deployment history before remediation.",
                    2,
                    5,
                    5,
                    4,
                ),
                ActionCandidate(
                    "restart_service",
                    "Restart the service without a confirmed cause.",
                    2,
                    2,
                    2,
                    1,
                ),
            )
            verification = (
                "Collect a consistent observation window.",
                "Review evidence quality and source coverage.",
                "Re-score actions once the cause is better supported.",
            )

        selected = max(candidates, key=lambda candidate: candidate.utility)
        candidate_scores = "; ".join(
            f"{candidate.action_id}={candidate.utility:.2f}"
            for candidate in candidates
        )
        rationale = (
            "Candidates were scored from 1-5 for recovery impact, safety, "
            "reversibility, and evidence fit using weights "
            f"{_WEIGHTS}; scores: {candidate_scores}. "
            f"Selected {selected.action_id} with utility {selected.utility:.2f}. "
            "Scores are decision preferences, not calibrated probabilities."
        )
        return build_result(
            agent_id=self.agent_id,
            scenario=scenario,
            likely_cause=likely_cause,
            recommended_action=selected.description,
            rationale=rationale,
            confidence=None,
            verification_steps=verification,
            limitations=(
                "Utility weights are illustrative and have not been calibrated against production outcomes.",
            )
            + tuple(f"Missing evidence: {item}" for item in scenario.missing_evidence)
            + tuple(
                f"Conflicting evidence: {item}"
                for item in scenario.conflicting_evidence
            ),
        )
