# Project Plan

## Objective

Build an incident assistant that investigates software-service incidents and compares six decision-making approaches: five classical agents and one local LLM agent. Every agent receives the same selected scenario to make the comparison fair.

## Scope and assumptions

- Individual Group 2 project with one contributor.
- Local demonstration using fixed, synthetic scenario data; no connection to a real production system.
- The LLM uses a local Ollama model through LangChain and must call at least two relevant evidence tools.
- The Learning Agent reads and updates explicit success/failure experience data.
- The UI displays decisions, reasoning, evidence, and a side-by-side comparison.
- Do not claim that a recommendation is verified beyond the supplied scenario evidence.

## Phase-wise implementation plan

Implement phases in order. A later phase may start only when its listed contract or prerequisite is agreed. Keep every Python module inside its relevant nested package under `src/incident_agent/`; do not create modules directly in `src/`.

### Phase 0 — Agree contracts and verify the local model

**Tasks**

- Confirm Python version, virtual environment, dependency strategy, Ollama installation, and a small tool-calling model.
- Define the shared `IncidentScenario` input and `AgentResult` output fields before implementing agents.
- Confirm scenario IDs A-D and define how missing/conflicting evidence is represented.

**Files**

- Review/update `docs/ARCHITECTURE.md`, `docs/ENVIRONMENT_SETUP.md`, and `docs/TEST_PLAN.md`.
- Add dependency pins to root `requirements.txt` when the selected package APIs are known.

**Exit checklist**

- [x] The contributor's development setup is ready.
- [x] The chosen model is present and a minimal LangChain tool-call smoke test succeeds on the primary laptop.
- [x] The common input/output contract and scenario IDs are documented.

### Phase 1 — Domain models and shared scenario fixtures

**Tasks**

- Define typed, preferably immutable scenario and agent-result models.
- Create A-D fixture data with metrics, logs, deployment history, and prior-version status as applicable.
- Ensure every fixture contains enough source-labelled evidence for tests and recommendations; explicitly mark unavailable evidence.

**Files**

- `src/incident_agent/domain/models.py`
- `src/incident_agent/domain/scenarios.py`
- `data/scenarios/scenarios.json`
- `tests/unit/test_scenarios.py`

**Exit checklist**

- [x] Scenario A covers latency/errors and exhausted DB pool.
- [x] Scenario B covers high traffic/CPU with normal DB connections.
- [x] Scenario C covers startup failure after a config change and a healthy previous version.
- [x] Scenario D covers missing or conflicting evidence.
- [x] Unit tests confirm catalog loading, scenario content, duplicate-ID rejection, and immutability.

### Phase 2 — Five classical agents and their unit tests

**Tasks**

- Implement five distinct decision mechanisms, all accepting the shared scenario contract and returning the common result contract.
- Keep each mechanism explicit in code and reasoning; shared validation/result helpers must not collapse their decision logic into one rule.
- Implement the Learning Agent with seeded experience counts and an explicit outcome-feedback update path. A recommendation by itself must not count as a success or failure.

**Files**

- `src/incident_agent/agents/classical/common.py` (shared evidence/signal extraction only)
- `src/incident_agent/agents/__init__.py`
- `src/incident_agent/agents/classical/__init__.py`
- `src/incident_agent/agents/classical/simple_reflex.py`
- `src/incident_agent/agents/classical/model_based_reflex.py`
- `src/incident_agent/agents/classical/goal_based.py`
- `src/incident_agent/agents/classical/utility_based.py`
- `src/incident_agent/agents/classical/learning.py`
- `src/incident_agent/storage/__init__.py`
- `src/incident_agent/storage/experience_store.py`
- `data/learning/experience.json`
- `tests/unit/test_classical_agents.py`
- `tests/unit/test_learning_agent.py`

**Exit checklist**

- [x] Simple Reflex uses current-observation condition/action rules.
- [x] Model-Based Reflex maintains and uses incident state from observations.
- [x] Goal-Based selects actions to satisfy explicit restoration/verification goals.
- [x] Utility-Based scores candidate actions using declared factors.
- [x] Learning uses success/failure history, explains its effect, and updates only after recorded feedback/outcome.
- [x] Tests cover expected decisions, unknown/ambiguous inputs, and learning-store update behavior.

### Phase 3 — Evidence tools and local LLM agent

**Tasks**

- Implement deterministic fixture-backed `get_metrics`, `search_logs`, `get_deployment_history`, and `check_previous_version` tools.
- Scope every tool call to the currently selected scenario fixture.
- Implement the LangChain agent using the configured local Ollama model; require evidence from at least two relevant tools before treating the recommendation as grounded.
- Preserve tool names/results for display and testing; show model or tool failures explicitly.

**Files**

- `src/incident_agent/tools/evidence_tools.py`
- `src/incident_agent/agents/llm/ollama_agent.py`
- `tests/unit/test_evidence_tools.py`
- `tests/unit/test_ollama_agent.py`
- `tests/integration/test_ollama_tool_calling.py`

**Exit checklist**

- [x] Each tool returns the expected evidence for its scenario and identifies its source.
- [x] Tool instances are scoped to one selected scenario fixture; unit tests confirm scenario IDs and contents cannot be switched by tool arguments.
- [x] Unit tests prove at least two relevant tools were called; an opt-in live test exercises the local Ollama model.
- [x] The LLM recommendation cites exact returned evidence from at least two tools; unit tests reject unsupported citations.
- [x] Missing fixture evidence is explicit; unavailable Ollama, malformed responses, and failed tool calls surface as errors, not success-shaped output.

### Phase 4 — Orchestration and shared-input validation

**Tasks**

- Implement the application controller that loads one selected scenario, invokes all six agents, collects results, and surfaces individual failures.
- Keep the scenario input identical for all agents; do not silently skip an agent.
- Keep learning feedback separate from the comparison run and require an explicit outcome event.

**Files**

- `src/incident_agent/orchestration/__init__.py`
- `src/incident_agent/orchestration/incident_orchestrator.py`
- `tests/integration/test_shared_scenario_run.py`

**Exit checklist**

- [x] Orchestrator invokes all six registered agents using one selected catalog scenario and validates each returned scenario ID.
- [x] Integration tests confirm every agent receives the identical selected scenario object and contents.
- [x] An error in one agent is visible and does not invalidate or hide other agent results.
- [x] Experience counts remain unchanged during comparison and update only after explicit outcome feedback.

### Phase 5 — Streamlit interface and comparison

**Tasks**

- Build a scenario selector for A-D and a comparison action.
- Display each agent's incident summary, evidence, likely cause, recommendation, reasoning, verification steps, and limitations.
- Show LLM tool-call evidence and Learning Agent counts/update explanation.
- Add a readable side-by-side comparison table and explain why decisions can differ.
- Provide an explicit, controlled feedback interaction for Learning Agent outcomes if time permits.

**Files**

- `src/incident_agent/app/streamlit_app.py`
- `tests/integration/test_ui_flow.py` (or focused UI tests supported by the selected framework)
- `screenshots/` (final captured evidence)

**Exit checklist**

- [x] User can select each of the four scenarios and run the six-agent comparison.
- [x] Results and decision differences are visible without implying equal certainty.
- [x] CPU, request rate, latency, and database-pool snapshot cards show supplied values, identify missing observations, and disclose that the fixture is synthetic rather than live or time-series data.
- [x] UI displays LLM tool evidence and exposes individual model/tool errors.
- [x] Learning history is visible; outcome updates require explicit action and report updated counts.
- [x] Streamlit interaction tests cover scenario selection, comparison, feedback, and an individual-agent failure.

### Phase 6 — Test, evaluate, document, and submit

**Tasks**

- Run unit and integration suites; fix failures and record exact commands/results in `docs/TEST_RESULTS.md`.
- Run all scenarios end-to-end and capture screenshots with no credentials or unrelated private data.
- Finish README setup/run instructions, project architecture, comparison explanation, and test evidence.
- Confirm the repository contains all required source, fixture, dependency, documentation, and screenshot files; push final changes to GitHub.

**Files**

- Update `README.md`, `docs/ENVIRONMENT_SETUP.md`, `docs/ARCHITECTURE.md`, and `docs/TEST_PLAN.md`.
- Save demo images under `screenshots/`.
- Keep final test output in the submission evidence (document results; do not claim tests that were not run).

**Exit checklist**

- [ ] All submission checklist items below are complete.
- [ ] Clean-environment setup and application launch have been verified.
- [x] Deterministic test results, selected Ollama model, and skipped/live test outcomes are documented.
- [x] Scenarios A-D were run through the Streamlit app and screenshots saved under `screenshots/`.
- [ ] Final commit is pushed and visible in the Group 2 GitHub repository.

## Estimated effort and schedule

The estimates below are planning estimates, not guarantees. They represent the approximate total effort for one contributor; actual time depends on local model setup and debugging.

| Workstream | Estimated person-hours |
|---|---:|
| Repository setup and architecture | 1.5 |
| Five classical agents | 4 |
| Ollama/LangChain agent and four evidence tools | 7 |
| Learning Agent and experience store | 2 |
| Shared scenarios, common contract, and orchestrator | 2 |
| Streamlit comparison UI | 3 |
| Testing and evaluation | 3 |
| Integration and debugging buffer | 4 |
| Documentation and screenshots | 2 |
| **Estimated total** | **28.5 person-hours** |

The estimated work sums to about 28.5 person-hours. It assumes the local model is available and tool-calling compatible; model troubleshooting can add time. Integration and end-to-end testing are sequential tasks, so prioritizing the acceptance criteria is more important than optional polish.

### Single-contributor workflow

- Define and validate the shared scenario/result contracts and fixture data.
- Implement and test the five classical agents, experience store, evidence tools, and local Ollama agent.
- Integrate all six agents through the orchestrator and build the Streamlit comparison UI.
- Run end-to-end tests, capture scenario screenshots, and complete documentation and submission checks.

### Deadline-driven calendar plan

| Date (2026) | Focus | End-of-day checkpoint |
|---|---|---|
| **Nov 14** | Phase 0-1: define input/result contracts and A-D scenario schema; prepare shared fixtures; verify local Ollama tool calling. | Fixture and local-model smoke checks pass. |
| **Nov 15** | Phases 2-5: implement agents, evidence tools, orchestration, and the Streamlit comparison. | All six agents run on shared scenarios; tests pass and comparison UI is usable. |
| **Nov 16-17** | Phase 6: run regression/live-model tests, capture scenario screenshots, and finish submission documentation. | Submission checklist complete and results recorded. |
| **Nov 18 (due 11:59 PM)** | Final clean-environment run, verify files/screenshots and GitHub state; reserve for blockers. | Submit before 11:59 PM; avoid optional feature work. |

The plan targets roughly four focused implementation days and a final-day buffer. It is aggressive for one contributor, especially if Ollama downloads or tool calling require troubleshooting; prioritize the acceptance criteria and defer optional polish.

## Assignment requirement traceability

| Assignment requirement | Implementation location | Verification / submission evidence |
|---|---|---|
| Five separate classical agents with intended mechanisms | `src/incident_agent/agents/classical/` | Unit tests confirm separate rules/state/goals/utility/learning behavior. |
| Local Ollama LLM through LangChain | `src/incident_agent/agents/llm/ollama_agent.py`, `requirements.txt` | Setup documentation names the compatible model; run evidence records model/version. |
| LLM calls at least two relevant tools and grounds its recommendation in returned evidence | `src/incident_agent/tools/evidence_tools.py`, LLM integration test | Tool-call records/results and scenario screenshot demonstrate two or more calls and evidence use. |
| Same selected scenario data reaches all six agents | `src/incident_agent/domain/`, `src/incident_agent/orchestration/` | Integration test checks scenario identity/content for all six agents. |
| At least three required scenarios: normal, critical/failure, edge/ambiguous | `data/scenarios/scenarios.json` | A, B, C, and D end-to-end results; D covers ambiguity explicitly. |
| Streamlit scenario selection, decisions, reasoning, and comparison | `src/incident_agent/app/streamlit_app.py` | Screenshots for scenario runs and comparison table. |
| Learning Agent uses/updates success/failure experience and explains effect | `src/incident_agent/agents/classical/learning.py`, `src/incident_agent/storage/experience_store.py`, `data/learning/experience.json` | Learning test and before/after feedback evidence; recommendation alone does not update counts. |
| Expected output: summary, evidence, likely cause, action, verification, limitations | Shared `AgentResult` contract and UI | All six result cards expose these fields or mark unavailable evidence/uncertainty. |
| Comparison table and explanation for differing decisions | Streamlit UI and `README.md` or demonstration notes | Comparison screenshots and written explanation citing agent decision mechanisms. |
| Source, requirements, README, setup instructions, tests, results, screenshots | Root, `src/`, `tests/`, `docs/`, `screenshots/` | Final checklist below; test results report only commands actually run. |

## Acceptance criteria

- [ ] Five distinct classical agents use their intended decision mechanisms, not aliases of one common rule.
- [ ] The local Ollama/LangChain agent invokes at least two relevant tools and uses their returned evidence.
- [ ] All six agents receive the same selected scenario contents on a comparison run.
- [ ] Scenarios A-C meet the assignment descriptions; D demonstrates ambiguous/missing evidence behavior.
- [ ] Every result exposes an incident summary, evidence, likely cause, recommended action, verification steps, and limitations (or explicitly marks unavailable fields).
- [ ] Learning experience data is used, updated from a recorded outcome, and explained in its result.
- [ ] The Streamlit UI shows decisions, reasoning, and an understandable comparison.
- [ ] Tests, results, and scenario screenshots are included.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Selected local model does not reliably support tool calling. | Test tool calls early; choose a compatible Ollama model and expose a clear error if investigation tools are not called. |
| Stochastic LLM output makes comparisons hard to reproduce. | Use fixed scenario fixtures, low temperature where supported, and display exact tool evidence alongside the response. |
| Agents receive subtly different inputs. | Construct one immutable scenario object per run and pass it to every agent; test scenario identity/content. |
| Learning results depend on prior runs. | Make experience data visible, document reset/seed behavior, and test with known counts. |
| Suggestions could be unsafe if applied automatically. | Recommendations are advisory only; require a human operator and include verification/rollback steps. |

## Submission checklist

- [x] Five separate classical-agent implementations and tests
- [x] LangChain agent connected to a local Ollama model; configured model and run instructions documented
- [x] At least two relevant LLM tool calls recorded, with recommendations grounded in returned evidence
- [x] Shared scenario/result contract and integration test proving the same scenario reaches all six agents
- [x] Scenario fixtures and results for A (DB pool exhaustion), B (traffic/CPU spike), C (config startup failure), and D (ambiguous evidence)
- [x] Learning Agent experience store, controlled feedback update, test, and explanation of its effect
- [x] Streamlit scenario selector, six decision/reasoning views, and comparison table
- [x] Comparison explanation describing why the agents may reach different recommendations
- [x] `requirements.txt`, README, setup instructions, architecture diagram/reference, and test plan
- [x] Recorded test commands/results, including the skipped default Ollama test and successful opt-in live test
- [x] Screenshots for A, B, and C, plus D
- [ ] Final source and evidence pushed to the Group 2 GitHub repository
