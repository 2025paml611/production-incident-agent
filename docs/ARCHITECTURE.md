# Project Architecture

## Overview

The application separates scenario data, agent implementations, evidence tools, orchestration, and presentation. The orchestrator loads one selected scenario and passes the same immutable object to all six agents. Individual agent failures are retained beside successful results. Learning feedback is recorded only through a separate explicit outcome call. The LLM can additionally query fixture-backed tools for evidence about that same scenario and must cite exact returned evidence from at least two different tools.

## Architecture diagram

![Production Incident Agent system architecture](<Production Incident Agent Architecture.png>)

The diagram shows the shared scenario path, agent responsibilities, evidence tools, and result flow. Its data-flow notes clarify that the LLM tools read the same selected fixture as the other agents, the Model-Based Reflex Agent retains observations as incident state, and Learning Agent counts change only after a recorded outcome—not merely after generating a recommendation.

```text
Streamlit UI
    |
    +-- IncidentOrchestrator --> scenario catalog --> selected shared IncidentScenario
    |                                                      |
    |                                                      +--> Simple Reflex Agent
    |                                                      +--> Model-Based Reflex Agent
    |                                                      +--> Goal-Based Agent
    |                                                      +--> Utility-Based Agent
    |                                                      +--> Learning Agent <--> experience store
    |                                                      +--> LangChain/Ollama Agent
    |                                                             +--> evidence tools
    |
    +-- Per-agent result or error --> comparison table, evidence, reasoning, limitations
    |
    +-- Explicit outcome feedback --> Learning Agent experience store
```

## Project folder layout

```text
.
|-- requirements.txt
|-- README.md
|-- data/
|   |-- scenarios/
|   |   `-- scenarios.json
|   `-- learning/
|       `-- experience.json
|-- src/
|   `-- incident_agent/
|       |-- app/
|       |   `-- streamlit_app.py
|       |-- agents/
|       |   |-- classical/
|       |   |   |-- simple_reflex.py
|       |   |   |-- model_based_reflex.py
|       |   |   |-- goal_based.py
|       |   |   |-- utility_based.py
|       |   |   `-- learning.py
|       |   `-- llm/
|       |       `-- ollama_agent.py
|       |-- domain/
|       |   |-- models.py
|       |   `-- scenarios.py
|       |-- orchestration/
|       |   `-- incident_orchestrator.py
|       |-- storage/
|       |   `-- experience_store.py
|       `-- tools/
|           `-- evidence_tools.py
|-- tests/
|   |-- unit/
|   `-- integration/
|-- docs/
`-- screenshots/
```

All application Python files belong under `src/incident_agent/` in their relevant package. Do not place Python modules directly in `src/`. The folder order reflects the implementation flow: define domain contracts and scenarios, implement agents and tools, connect them through orchestration, then build the UI. Add each file in its owning folder as that phase begins; avoid creating empty placeholder modules ahead of implementation.

`data/scenarios/` holds the shared scenario fixtures, while `data/learning/` holds the Learning Agent's explicit experience data. `tests/unit/` and `tests/integration/` separate focused logic checks from full-flow checks. `screenshots/` contains final demonstration evidence.

## Shared data and result contracts

The first implementation uses a small, curated **synthetic fixture set**, not a trained-on or externally collected dataset. `data/scenarios/scenarios.json` is the canonical fixture file. Scenario A covers latency/errors with database-pool exhaustion; B covers a traffic/CPU spike with normal database connections; C covers a configuration change followed by startup failure and a healthy previous version; D has conflicting or missing evidence. The fixtures are explicitly synthetic and are suitable for deterministic demonstrations, not operational decisions.

`src/incident_agent/domain/models.py` defines frozen, typed models. One `IncidentScenario` instance is loaded for a run and later passed to all agents. Its fields include:

- scenario ID, category, title, incident summary, affected services, and time window
- source-labelled metric observations and log entries
- deployment history and optional previous-version health
- explicit missing-evidence and conflicting-evidence notes

The shared `AgentResult` model requires:

- agent name and incident summary
- scenario ID, observed evidence (with source), and likely cause
- optional numeric confidence to allow explicit uncertainty
- recommended action and rationale
- verification steps and limitations
- optional recommended action ID for associating later outcome feedback

LLM tool-call summaries are retained as structured result data. Expected causes/actions used to evaluate a demo must remain separate from the scenario passed to agents, to avoid answer leakage. Missing evidence is represented explicitly rather than invented.

## Agent responsibilities

1. **Simple Reflex:** Select an action from current observed symptoms using condition-action rules; no persistent internal state.
2. **Model-Based Reflex:** Retain observations and detected conditions by scenario ID, update incident state, then apply rules to that state. Reset the model before reusing an ID for an unrelated incident.
3. **Goal-Based:** Choose a plan to restore service safely, reduce uncertainty when evidence conflicts, and verify recovery.
4. **Utility-Based:** Score candidate actions from 1-5 on recovery impact, safety, reversibility, and evidence fit; use weights 0.35, 0.25, 0.25, and 0.15 respectively.
5. **Learning:** Rank scenario-appropriate actions using recorded success/failure counts with a Beta(1, 1) smoothed success rate. The synthetic seed data is illustrative; only an explicit operator or controlled-test outcome updates counts. Results return the selected action ID, counts, and explanation.
6. **LLM-based:** Use LangChain with a local Ollama chat model, call relevant evidence tools, and ground its recommendation in returned tool results. The model must not be allowed to silently substitute unsupported facts for missing evidence.

The classical agents should remain independently understandable and testable. Shared data structures and safe-action constraints may be reused, but the decision mechanism of each agent must remain distinct.

## Evidence tools

Implement deterministic, local tools over the selected scenario fixture:

- `get_metrics`: return relevant metric values and time window.
- `search_logs`: return matching log evidence for the incident.
- `get_deployment_history`: return recent deployment/configuration events.
- `check_previous_version`: report previous-version health or availability.

Tool arguments should identify the selected scenario and any search criteria. Tool results should preserve source/context so the LLM's evidence can be checked. These are demo tools, not production observability integrations.

## Scenario catalog

- **A — Database pool exhaustion:** API latency and errors rise while the database connection pool is exhausted.
- **B — Traffic spike / CPU pressure:** Request traffic and CPU are high while database connections remain normal.
- **C — Startup failure after configuration change:** The service fails to start after a config change; the prior version was healthy.
- **D — Ambiguous evidence:** Symptoms conflict or critical telemetry is missing; agents should communicate uncertainty and avoid overconfident or risky actions.

The three specified assignment scenarios A-C must be included. D provides explicit edge/ambiguous-case coverage.

## Safety and failure handling

- Recommendations are advisory; the application does not execute operational changes.
- Prefer reversible, scoped actions and include verification and rollback considerations.
- The LLM recommendation is not considered tool-grounded unless at least two relevant tools return evidence.
- Surface Ollama/model/tool errors in the UI. Do not present an error or missing tool evidence as a successful investigation.
- Display uncertainty and limitations, especially for scenario D.

## UI flow

1. User selects a scenario and starts a comparison.
2. The orchestrator loads one scenario input and provides the same object to every agent.
3. Agents produce structured results; an individual failure is reported without hiding other agents' results. The LLM gathers evidence through tools.
4. UI shows the shared scenario, per-agent result/error cards, tool evidence, and a comparison table.
5. An explicit operator feedback or controlled test outcome can update Learning Agent experience data; generating recommendations alone does not update the counts.
