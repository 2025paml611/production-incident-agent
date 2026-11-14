"""Goal-based agent that plans to restore service safely and verify recovery."""

from incident_agent.agents.classical.common import (
    build_result,
    scenario_signals,
)
from incident_agent.domain.models import AgentResult, IncidentScenario


class GoalBasedAgent:
    """Choose a plan that advances explicit incident-management goals."""

    agent_id = "goal_based"
    goals = (
        "restore service",
        "prefer reversible, low-risk recovery",
        "verify service health before declaring recovery",
    )

    def analyze(self, scenario: IncidentScenario) -> AgentResult:
        signals = scenario_signals(scenario)
        if signals.ambiguous_evidence:
            cause = "Conflicting or incomplete observations prevent a safe root-cause decision."
            action = (
                "First reduce uncertainty: collect independent CPU, pool-waiter, and "
                "deployment evidence; avoid high-impact remediation until the signals agree."
            )
            confidence = 0.3
            steps = (
                "Align metric and log timestamps for the same observation window.",
                "Collect independent CPU and database-pool measurements.",
                "Review complete deployment history before planning a recovery.",
            )
            plan = "evidence-first plan; diagnosis is a prerequisite to safe restoration"
        elif signals.startup_failure_after_deploy:
            cause = "The recent configuration change is a plausible cause of failed startup."
            action = (
                "Compare the configuration with the last-known-good version and have an "
                "operator approve a rollback or corrected configuration."
            )
            confidence = 0.88
            steps = (
                "Validate required configuration keys and secret injection.",
                "Confirm the approved version starts and passes readiness checks.",
                "Restore traffic gradually and watch health and error-rate signals.",
            )
            plan = "recover availability using a reversible configuration/version change"
        elif signals.database_pool_exhaustion:
            cause = "Connection-pool pressure is the strongest supplied explanation for API delays."
            action = (
                "Reduce connection demand by investigating slow or blocked queries; adjust "
                "pool capacity only if database capacity and connection limits permit."
            )
            confidence = 0.86
            steps = (
                "Check slow queries, lock waits, pool waiters, and database headroom.",
                "Apply one approved, reversible mitigation at a time.",
                "Verify pool waiters, API latency, and error rate return toward baseline.",
            )
            plan = "restore the API while protecting database capacity"
        elif signals.traffic_cpu_pressure:
            cause = "High request volume and CPU pressure with available DB connections point to the application tier."
            action = (
                "Protect the service objective with controlled load-shedding or bounded "
                "application scaling, then profile the CPU-bound work."
            )
            confidence = 0.78
            steps = (
                "Check per-instance CPU, worker queue depth, and request mix.",
                "Confirm database connection usage remains normal.",
                "Verify latency and errors improve without creating a database bottleneck.",
            )
            plan = "protect availability and latency at the application tier"
        else:
            cause = "The supplied scenario does not satisfy a specific recovery plan."
            action = (
                "Collect current service, database, and deployment evidence before selecting "
                "a recovery action."
            )
            confidence = 0.35
            steps = (
                "Refresh service metrics and relevant logs.",
                "Confirm current and previous deployment health.",
                "Reassess the goals after evidence is available.",
            )
            plan = "gather evidence before committing to a recovery plan"

        return build_result(
            agent_id=self.agent_id,
            scenario=scenario,
            likely_cause=cause,
            recommended_action=action,
            rationale=(
                f"Selected {plan} to satisfy these goals in order: "
                f"{'; '.join(self.goals)}."
            ),
            confidence=confidence,
            verification_steps=steps,
        )
