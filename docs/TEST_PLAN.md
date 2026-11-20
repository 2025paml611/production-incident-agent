# Test Plan

## Purpose

Verify that each agent uses its intended decision mechanism, all agents receive the same scenario, evidence-based requirements are met, and the UI presents comparable results.

## Scenario matrix

| ID | Class | Input evidence | Expected behavior |
|---|---|---|---|
| A | Normal / degraded service | API latency and errors elevated; database connection pool exhausted. | Identify pool pressure as a likely cause; recommend a cautious, relevant mitigation and verify recovery using metrics/logs. |
| B | Resource pressure | Traffic spike and CPU high; database connection levels normal. | Identify application/CPU or traffic pressure rather than blaming the database; recommend a safe capacity/load response and verification. |
| C | Critical / failure | Application fails to start following a configuration change; previous version healthy. | Prioritize safe recovery such as validating/reverting the change or rolling back; include startup and health verification. |
| D | Edge / ambiguous | Conflicting symptoms or missing key metrics/logs. | State uncertainty, identify missing evidence, request/collect relevant data, and avoid unsupported high-impact remediation. |

Each comparison run must pass one selected scenario object to all six agents. Tests should verify equivalent scenario ID and content at every agent boundary.

## Agent-level tests

- **Simple Reflex:** Known symptom patterns trigger expected rules; unknown patterns do not fabricate evidence.
- **Model-Based Reflex:** New observations update internal state and affect a later decision; reset behavior is testable.
- **Goal-Based:** Recommendations support the declared restoration and safe-verification goals.
- **Utility-Based:** Candidate scores and selected action are consistent with documented utility weights; risky actions do not win without an explicit rationale.
- **Learning:** Seeded success/failure counts affect action ranking or confidence as documented; feedback updates counts; malformed or missing experience data is handled explicitly.
- **LLM:** Tools return evidence for the selected scenario, at least two relevant tools are invoked, and the response reflects returned evidence. Include an error path for unavailable Ollama/model or failed tool calls.

Where possible, keep tests deterministic by testing tool adapters and prompt/response handling separately from an optional live Ollama integration test.

## UI and integration tests

- Scenario selection supplies the same input to all six agents.
- Metric snapshot cards format supplied CPU, request-rate, latency, and database-pool
  observations; unavailable values are labeled rather than inferred. The UI identifies
  fixtures as synthetic snapshots, not live telemetry or a time series.
- Results display decision, reasoning, evidence, verification steps, and limitations.
- The comparison includes all agents and makes differences readable.
- LLM/tool errors are visible and are not displayed as successful recommendations.
- Learning experience changes are visible and do not silently alter unrelated scenario data.

## Submission evidence

1. Scenario A comparison, including the LLM's tool evidence.
2. Scenario B comparison.
3. Scenario C critical-failure comparison.
4. Scenario D ambiguous case, to show how agents handle missing or conflicting evidence.
5. Learning Agent experience counts before/after a controlled feedback update.
6. Test command output and pass/fail summary.

Screenshots should avoid personal tokens, local credentials, and unrelated desktop information.

## Final report

Record the exact test command, date, Python version, selected Ollama model for any live test, passed/failed counts, and any skipped integration tests with reasons. Do not report unrun tests as passed.
