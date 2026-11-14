"""Simple reflex agent using condition-action rules on current observations."""

from incident_agent.agents.classical.common import (
    build_result,
    scenario_signals,
)
from incident_agent.domain.models import AgentResult, IncidentScenario


class SimpleReflexAgent:
    """Choose an immediate response from the current scenario's signals."""

    agent_id = "simple_reflex"

    def analyze(self, scenario: IncidentScenario) -> AgentResult:
        signals = scenario_signals(scenario)
        if signals.startup_failure_after_deploy:
            return build_result(
                agent_id=self.agent_id,
                scenario=scenario,
                likely_cause="A configuration change is associated with the startup failure.",
                confidence=0.9,
                recommended_action=(
                    "Have an operator review the configuration change and, if approved, "
                    "roll back to the last-known-good version."
                ),
                rationale=(
                    "Reflex rule: startup failure after a configuration deployment "
                    "triggers a review of that change and a reversible recovery option."
                ),
                verification_steps=(
                    "Validate the required configuration keys.",
                    "Confirm the previous version starts and passes readiness checks.",
                    "Monitor error rate and health checks before restoring full traffic.",
                ),
            )
        if signals.database_pool_exhaustion:
            return build_result(
                agent_id=self.agent_id,
                scenario=scenario,
                likely_cause="Database connection-pool exhaustion is delaying API requests.",
                confidence=0.9,
                recommended_action=(
                    "Inspect slow or blocked queries and reduce connection demand; "
                    "consider a cautious pool adjustment only after checking database capacity."
                ),
                rationale=(
                    "Reflex rule: a saturated pool with waiters or connection-acquisition "
                    "timeouts maps directly to database-pool investigation."
                ),
                verification_steps=(
                    "Check pool waiters and acquisition timeouts.",
                    "Confirm database query latency and database health.",
                    "Verify API latency and error rate recover after the approved mitigation.",
                ),
            )
        if signals.traffic_cpu_pressure:
            return build_result(
                agent_id=self.agent_id,
                scenario=scenario,
                likely_cause=(
                    "High request volume is coinciding with application CPU pressure; "
                    "database connections are not saturated."
                ),
                confidence=0.82,
                recommended_action=(
                    "Use a bounded, reversible capacity increase or controlled load-shedding "
                    "while profiling CPU."
                ),
                rationale=(
                    "Reflex rule: high CPU and traffic with available database connections "
                    "selects an application-capacity response rather than a database action."
                ),
                verification_steps=(
                    "Check per-instance CPU and worker queue depth.",
                    "Confirm database pool usage remains within capacity.",
                    "Monitor latency, errors, and CPU after the approved change.",
                ),
            )
        return build_result(
            agent_id=self.agent_id,
            scenario=scenario,
            likely_cause="The supplied evidence does not establish a single cause.",
            confidence=0.35,
            recommended_action=(
                "Defer high-impact remediation and collect independent CPU, database-pool, "
                "and deployment-history evidence."
            ),
            rationale=(
                "Reflex fallback: no high-confidence condition-action rule matched; "
                "uncertain evidence calls for further observation."
            ),
            verification_steps=(
                "Reconcile metric and log time windows.",
                "Collect independent CPU and database-pool telemetry.",
                "Confirm deployment history before selecting a recovery action.",
            ),
        )
