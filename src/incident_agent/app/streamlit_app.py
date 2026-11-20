"""Streamlit interface for comparing production incident agents."""

from typing import cast

import streamlit as st

from incident_agent.domain.models import AgentResult, IncidentScenario, Metric
from incident_agent.domain.scenarios import ScenarioCatalog, load_scenarios
from incident_agent.orchestration import IncidentOrchestrator, IncidentRun
from incident_agent.orchestration.decision_comparison import (
    explain_decision_differences,
)

_AGENT_LABELS = {
    "simple_reflex": "Simple Reflex",
    "model_based_reflex": "Model-Based Reflex",
    "goal_based": "Goal-Based",
    "utility_based": "Utility-Based",
    "learning": "Learning",
    "llm_ollama": "Local Ollama LLM",
}
_SNAPSHOT_METRICS = (
    ("CPU utilization", "cpu_utilization"),
    ("Request rate", "request_rate"),
    ("API latency (p95)", "api_latency_p95"),
)


def _get_orchestrator() -> IncidentOrchestrator:
    if "incident_orchestrator" not in st.session_state:
        st.session_state["incident_orchestrator"] = IncidentOrchestrator()
    return cast(IncidentOrchestrator, st.session_state["incident_orchestrator"])


def _render_scenario_summary(scenario_catalog: ScenarioCatalog, scenario_id: str) -> None:
    scenario = scenario_catalog[scenario_id]
    st.subheader(f"Scenario {scenario.scenario_id}: {scenario.title}")
    st.write(scenario.incident_summary)
    st.caption(
        f"Type: {scenario.scenario_type.value.replace('_', ' ').title()} · "
        f"Services: {', '.join(scenario.affected_services)} · "
        f"Window: {scenario.time_window}"
    )
    if scenario.missing_evidence:
        st.info("Missing evidence: " + "; ".join(scenario.missing_evidence))
    if scenario.conflicting_evidence:
        st.warning("Conflicting evidence: " + "; ".join(scenario.conflicting_evidence))


def _render_metric_snapshot(scenario: IncidentScenario) -> None:
    st.subheader("Metric snapshot")
    st.caption(
        "Synthetic fixture observations, not live telemetry. Each value is a "
        "snapshot; the fixture does not contain a time series for trend charts."
    )
    metrics_by_name = {metric.name: metric for metric in scenario.metrics}
    columns = st.columns(4)
    for column, (label, metric_name) in zip(
        columns[:3],
        _SNAPSHOT_METRICS,
        strict=True,
    ):
        metric = metrics_by_name.get(metric_name)
        with column:
            st.metric(
                label,
                _format_snapshot_metric(metric),
                help=_metric_provenance(metric),
            )

    active = metrics_by_name.get("db_pool_active")
    maximum = metrics_by_name.get("db_pool_max")
    pool_value, pool_help = _format_pool_usage(active, maximum)
    with columns[3]:
        st.metric("Database pool usage", pool_value, help=pool_help)

    if not scenario.metrics:
        st.info("No metric observations were supplied for this scenario.")
        return

    with st.expander("All supplied metric observations and sources"):
        for metric in scenario.metrics:
            observed_value = (
                "Not supplied"
                if metric.value is None
                else f"{metric.value} {metric.unit}"
            )
            st.markdown(
                f"- **{_markdown_cell(metric.name)}:** "
                f"{_markdown_cell(observed_value)} "
                f"({_markdown_cell(metric.observed_at)}; "
                f"source: {_markdown_cell(metric.source)})"
            )


def _format_snapshot_metric(metric: Metric | None) -> str:
    if metric is None or metric.value is None:
        return "Not supplied"
    formatted_value = _format_metric_value(metric.value)
    unit_suffix = {
        "percent": "%",
        "ms": " ms",
        "requests_per_second": " req/s",
    }.get(metric.unit, f" {metric.unit}")
    return f"{formatted_value}{unit_suffix}"


def _format_metric_value(value: int | float | str | None) -> str:
    if value is None:
        return "Not supplied"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return f"{value:,.2f}".rstrip("0").rstrip(".")
    return value


def _format_pool_usage(
    active: Metric | None, maximum: Metric | None
) -> tuple[str, str]:
    if active is None or active.value is None:
        return "Not supplied", _metric_provenance(active)
    if maximum is None or maximum.value is None:
        return (
            f"{active.value} / limit not supplied",
            _metric_provenance(active),
        )
    active_value = active.value
    maximum_value = maximum.value
    if (
        isinstance(active_value, bool)
        or not isinstance(active_value, (int, float))
        or isinstance(maximum_value, bool)
        or not isinstance(maximum_value, (int, float))
    ):
        return (
            f"{active_value} / {maximum_value} connections",
            f"{_metric_provenance(active)} {_metric_provenance(maximum)}",
        )

    pool_value = (
        f"{_format_metric_value(active_value)} / "
        f"{_format_metric_value(maximum_value)} connections"
    )
    if maximum_value <= 0:
        return (
            pool_value,
            "Pool utilization is unavailable because the limit is not positive.",
        )
    utilization = active_value / maximum_value
    return (
        f"{pool_value} ({utilization:.0%})",
        f"Active connections divided by configured maximum. "
        f"{_metric_provenance(active)} {_metric_provenance(maximum)}",
    )


def _metric_provenance(metric: Metric | None) -> str:
    if metric is None:
        return "No observation was supplied in this scenario."
    return f"Source: {metric.source}. Observed at: {metric.observed_at}."


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _comparison_rows(run: IncidentRun) -> list[dict[str, str]]:
    rows = []
    for execution in run.executions:
        label = _AGENT_LABELS[execution.agent_id]
        if execution.result is None:
            rows.append(
                {
                    "Agent": label,
                    "Status": "Failed",
                    "Likely cause": "Unavailable",
                    "Recommended action": execution.error or "No error details provided.",
                    "Confidence": "Not available",
                }
            )
            continue
        result = execution.result
        rows.append(
            {
                "Agent": label,
                "Status": "Success",
                "Likely cause": result.likely_cause,
                "Recommended action": result.recommended_action,
                "Confidence": (
                    f"{result.confidence:.0%}"
                    if result.confidence is not None
                    else "Not calibrated"
                ),
            }
        )
    return rows


def _comparison_table(rows: list[dict[str, str]]) -> str:
    headers = ("Agent", "Status", "Likely cause", "Recommended action", "Confidence")
    separator = ("---",) * len(headers)

    def markdown_cell(value: str) -> str:
        return _markdown_cell(value)

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(markdown_cell(row[header]) for header in headers)
            + " |"
        )
    return "\n".join(lines)


def _render_agent_result(result: AgentResult) -> None:
    st.markdown("**Incident summary**")
    st.write(result.incident_summary)
    st.markdown("**Likely cause**")
    st.write(result.likely_cause)
    st.markdown("**Recommended action**")
    st.write(result.recommended_action)
    st.markdown("**Reasoning**")
    st.write(result.rationale)

    st.markdown("**Evidence**")
    if result.evidence:
        for item in result.evidence:
            st.markdown(f"- **{item.source}:** {item.detail}")
    else:
        st.write("No evidence items were returned.")

    st.markdown("**Verification steps**")
    for step in result.verification_steps:
        st.markdown(f"- {step}")

    st.markdown("**Limitations**")
    for limitation in result.limitations:
        st.markdown(f"- {limitation}")

    if result.tool_calls:
        st.markdown("**LLM tool calls**")
        for call in result.tool_calls:
            st.markdown(f"- **{call.tool_name}:** {call.result_summary}")


def _render_run(run: IncidentRun, orchestrator: IncidentOrchestrator) -> None:
    if run.failures:
        st.warning(
            f"{len(run.failures)} of 6 agents failed. Successful recommendations "
            "are shown below; failed agents are not treated as successful."
        )

    st.subheader("Agent comparison")
    st.markdown(_comparison_table(_comparison_rows(run)))
    st.caption(
        "Confidence values are agent-reported estimates, not calibrated or directly "
        "comparable probabilities. 'Not calibrated' means the agent does not provide "
        "a numeric confidence."
    )
    st.info(
        "Decisions can differ because each agent uses a different mechanism: current "
        "symptom rules, retained observations, explicit restoration goals, weighted "
        "utility, recorded action outcomes, or evidence gathered by the local LLM."
    )
    st.subheader("Why these decisions differ")
    st.markdown(explain_decision_differences(run))

    st.subheader("Individual agent results")
    for execution in run.executions:
        label = _AGENT_LABELS[execution.agent_id]
        status = "success" if execution.succeeded else "failed"
        with st.expander(f"{label} — {status}", expanded=not execution.succeeded):
            if execution.result is None:
                st.error(f"{label} failed: {execution.error}")
                continue
            _render_agent_result(execution.result)
            if execution.agent_id == "learning":
                _render_learning_feedback(
                    execution.result,
                    orchestrator,
                    run.scenario.scenario_id,
                )


def _render_learning_feedback(
    result: AgentResult,
    orchestrator: IncidentOrchestrator,
    scenario_id: str,
) -> None:
    action_id = result.recommended_action_id
    if action_id is None:
        st.info("This Learning Agent result has no action ID eligible for feedback.")
        return

    st.markdown("**Learning history and explicit outcome feedback**")
    try:
        record = orchestrator.get_learning_record(action_id)
    except Exception as error:
        st.error(f"Could not read Learning Agent history: {type(error).__name__}: {error}")
        return
    st.write(
        f"`{action_id}` — {record.successes} successes, {record.failures} failures; "
        f"smoothed success rate {record.smoothed_success_rate:.2f}."
    )
    st.caption(
        "Submitting an outcome records one explicit result for this action. "
        "Generating a recommendation does not change these counts. The recommendation "
        "above reflects experience available when that comparison was run."
    )
    success_column, failure_column = st.columns(2)
    with success_column:
        if st.button(
            "Record success",
            key=f"learning-success-{scenario_id}-{action_id}",
            width="stretch",
        ):
            _record_outcome(orchestrator, action_id, True)
    with failure_column:
        if st.button(
            "Record failure",
            key=f"learning-failure-{scenario_id}-{action_id}",
            width="stretch",
        ):
            _record_outcome(orchestrator, action_id, False)

    feedback = st.session_state.get("learning_feedback")
    if (
        isinstance(feedback, dict)
        and feedback.get("scenario_id") == scenario_id
        and feedback.get("action_id") == action_id
    ):
        st.success(feedback["message"])


def _record_outcome(
    orchestrator: IncidentOrchestrator, action_id: str, succeeded: bool
) -> None:
    try:
        record = orchestrator.record_learning_outcome(action_id, succeeded)
    except Exception as error:
        st.error(f"Could not record Learning Agent outcome: {type(error).__name__}: {error}")
        return
    scenario_id = st.session_state["incident_run"].scenario.scenario_id
    outcome = "success" if succeeded else "failure"
    st.session_state["learning_feedback"] = {
        "scenario_id": scenario_id,
        "action_id": action_id,
        "message": (
            f"Recorded one {outcome} for `{action_id}`. Updated totals: "
            f"{record.successes} successes, {record.failures} failures."
        ),
    }


def render_app(orchestrator: IncidentOrchestrator | None = None) -> None:
    """Render the interactive scenario-selection and agent-comparison UI."""

    st.set_page_config(
        page_title="Production Incident Agent",
        layout="wide",
    )
    st.title("Production Incident Agent")
    st.write(
        "Compare five classical decision agents with a local Ollama agent using "
        "the same synthetic incident scenario."
    )
    st.warning(
        "Recommendations are for this synthetic demonstration only. The agents do "
        "not access or modify a live production system."
    )

    try:
        scenario_catalog = load_scenarios()
    except Exception as error:
        st.error(f"Could not load incident scenarios: {type(error).__name__}: {error}")
        return

    try:
        selected_orchestrator = orchestrator or _get_orchestrator()
    except Exception as error:
        st.error(f"Could not initialize incident agents: {type(error).__name__}: {error}")
        return
    scenario_ids = tuple(scenario_catalog)
    selected_scenario_id = st.selectbox(
        "Select incident scenario",
        options=scenario_ids,
        format_func=lambda scenario_id: (
            f"{scenario_id} — {scenario_catalog[scenario_id].title}"
        ),
        key="selected_scenario_id",
    )
    _render_scenario_summary(scenario_catalog, selected_scenario_id)
    _render_metric_snapshot(scenario_catalog[selected_scenario_id])

    if st.button("Compare all six agents", type="primary", key="run-comparison"):
        st.session_state.pop("incident_run", None)
        with st.spinner("Running all six agents against the same scenario..."):
            try:
                st.session_state["incident_run"] = selected_orchestrator.run(
                    selected_scenario_id
                )
                st.session_state.pop("learning_feedback", None)
            except Exception as error:
                st.error(f"Could not run agent comparison: {type(error).__name__}: {error}")

    run = st.session_state.get("incident_run")
    if not isinstance(run, IncidentRun):
        st.info("Select a scenario and run the comparison to see agent decisions.")
        return
    if run.scenario.scenario_id != selected_scenario_id:
        st.info("The displayed comparison belongs to another scenario. Run again to refresh it.")
        return
    _render_run(run, selected_orchestrator)


if __name__ == "__main__":
    render_app()
