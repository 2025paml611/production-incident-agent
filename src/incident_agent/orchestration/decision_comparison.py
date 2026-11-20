"""Explain why agents on one shared scenario recommended what they did."""

from incident_agent.orchestration.incident_orchestrator import IncidentRun

AGENT_LABELS = {
    "simple_reflex": "Simple Reflex",
    "model_based_reflex": "Model-Based Reflex",
    "goal_based": "Goal-Based",
    "utility_based": "Utility-Based",
    "learning": "Learning",
    "llm_ollama": "Local Ollama LLM",
}

_MECHANISM = {
    "simple_reflex": "by matching the current observations to a condition-action rule",
    "model_based_reflex": "by applying rules to incident state retained from observations",
    "goal_based": "by choosing a plan toward safe restoration and verification",
    "utility_based": "by selecting the candidate with the highest weighted utility",
    "learning": "by ranking candidates with recorded success and failure counts",
    "llm_ollama": "by grounding the action in evidence returned from its tools",
}


def explain_decision_differences(run: IncidentRun) -> str:
    """Describe each agent's action and the mechanism that produced it."""

    distinct_actions = distinct_recommendation_count(run)
    if distinct_actions == 0:
        opening = "No agent returned a recommendation for this scenario."
    elif distinct_actions == 1:
        opening = (
            "Every agent that returned a result used the same recommended-action text. "
            "The mechanism behind that action is still different for each agent."
        )
    else:
        opening = (
            f"This run produced {distinct_actions} different recommended-action texts "
            "from the same scenario. Some of those texts describe the same recovery "
            "in different words. A different recovery means the mechanism used "
            "different evidence, a different objective, or the Learning Agent's "
            "recorded outcomes."
        )
    paragraphs = [opening]
    for execution in run.executions:
        label = AGENT_LABELS[execution.agent_id]
        if execution.result is None:
            paragraphs.append(
                f"{label} did not return a recommendation: {execution.error}"
            )
            continue
        action = " ".join(execution.result.recommended_action.split())
        paragraphs.append(
            f"{label} recommended \"{action}\" {_MECHANISM[execution.agent_id]}."
        )
    return "\n\n".join(paragraphs)


def distinct_recommendation_count(run: IncidentRun) -> int:
    """Count distinct recommended-action texts among agents that returned a result."""

    actions = {
        " ".join(execution.result.recommended_action.split())
        for execution in run.executions
        if execution.result is not None
    }
    return len(actions)
