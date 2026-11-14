# Project Plan

## Objective

Build an incident assistant that investigates software-service incidents and compares six decision-making approaches: five classical agents and one local LLM agent. Every agent receives the same selected scenario to make the comparison fair.

## Scope and assumptions

- Group 2 team project with two contributors working equally.
- Local demonstration using fixed, synthetic scenario data; no connection to a real production system.
- The LLM uses a local Ollama model through LangChain and must call at least two relevant evidence tools.
- The Learning Agent reads and updates explicit success/failure experience data.
- The UI displays decisions, reasoning, evidence, and a side-by-side comparison.
- Do not claim that a recommendation is verified beyond the supplied scenario evidence.

## Phase-wise implementation plan

Implement phases in order. A later phase may start only when its listed contract or prerequisite is agreed. Keep every Python module inside its relevant nested package under `src/incident_agent/`; do not create modules directly in `src/`. The two members contribute equally: each phase has a shared review/integration responsibility, and domain leads coordinate rather than work in isolation.

### Phase 0 — Agree contracts and verify the local model

**Tasks**

- Confirm Python version, virtual environment, dependency strategy, Ollama installation, and a small tool-calling model.
- Agree on the shared `IncidentScenario` input and `AgentResult` output fields before implementing agents.
- Confirm scenario IDs A-D and define how missing/conflicting evidence is represented.

**Files**

- Review/update `docs/ARCHITECTURE.md`, `docs/ENVIRONMENT_SETUP.md`, and `docs/TEST_PLAN.md`.
- Add dependency pins to root `requirements.txt` when the selected package APIs are known.

**Exit checklist**

- [ ] Both contributors can run Python and Ollama locally.
- [ ] The chosen model is present and a minimal LangChain tool-call smoke test succeeds.
- [ ] Both contributors approve the common input/output contract and scenario IDs.

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

**Joint exit checklist**

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

**Joint exit checklist**

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
- `tests/integration/test_llm_tool_calling.py`

**Joint exit checklist**

- [ ] Each tool returns the expected evidence for its scenario and identifies its source.
- [ ] A test or recorded run proves at least two relevant tools were called for a scenario.
- [ ] The LLM recommendation refers to returned evidence rather than unsupported claims.
- [ ] Missing evidence, unavailable Ollama, or failed tool calls are surfaced as errors/limitations, not success-shaped output.

### Phase 4 — Orchestration and shared-input validation

**Tasks**

- Implement the application controller that loads one selected scenario, invokes all six agents, collects results, and surfaces individual failures.
- Keep the scenario input identical for all agents; do not silently skip an agent.
- Keep learning feedback separate from the comparison run and require an explicit outcome event.

**Files**

- `src/incident_agent/orchestration/incident_orchestrator.py`
- `tests/integration/test_shared_scenario_run.py`

**Joint exit checklist**

- [ ] Orchestrator returns results for all six agents on the same scenario ID and contents.
- [ ] Integration test confirms every agent receives the same selected scenario object/content.
- [ ] An error in one agent is visible and does not invalidate or hide other agent results.
- [ ] No experience counts are updated just because agents generated recommendations.

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

**Joint exit checklist**

- [ ] User can run each of the four scenarios through all six agents.
- [ ] Results and differences are visible without implying equal certainty.
- [ ] UI displays tool evidence and exposes model/tool errors.
- [ ] Learning history and any outcome update are visible and attributable.

### Phase 6 — Test, evaluate, document, and submit

**Tasks**

- Run unit and integration suites; fix failures and record exact commands/results.
- Run all scenarios end-to-end and capture screenshots with no credentials or unrelated private data.
- Finish README setup/run instructions, project architecture, comparison explanation, and test evidence.
- Confirm the repository contains all required source, fixture, dependency, documentation, and screenshot files; push final changes to GitHub.

**Files**

- Update `README.md`, `docs/ENVIRONMENT_SETUP.md`, `docs/ARCHITECTURE.md`, and `docs/TEST_PLAN.md`.
- Save demo images under `screenshots/`.
- Keep final test output in the submission evidence (document results; do not claim tests that were not run).

**Joint exit checklist**

- [ ] All submission checklist items below are complete.
- [ ] Clean-environment setup and application launch have been verified.
- [ ] Test results, selected Ollama model, and any skipped live tests are documented.
- [ ] Final commit is pushed and visible in the Group 2 GitHub repository.

## Two-contributor effort and schedule

The estimates below are planning estimates, not guarantees. They distinguish **person-hours** (sum of contributors' work) from **calendar time** (elapsed time, with independent tasks done in parallel).

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

These estimates describe total team effort and sum to about 28.5 person-hours, or approximately 14.25 hours per member if split equally. They assume the local model is available and tool-calling compatible; model troubleshooting can add time. Two contributors do not halve the work because interface agreement, integration, and end-to-end testing are shared or sequential tasks. Rebalance task ownership during check-ins so the actual contributions remain equitable.

### Suggested ownership

- **Contributor 1 — classical decision systems:** co-design the shared contracts and scenario fixtures; implement the classical agents and Learning Agent; pair on end-to-end testing, comparison, and documentation.
- **Contributor 2 — LLM and experience integration:** co-design the shared contracts and scenario fixtures; implement the evidence tools and LangChain/Ollama agent; pair on Streamlit, end-to-end testing, comparison, and documentation.
- **Both contributors — shared ownership:** review each other's work, jointly integrate the six agents, validate the UI and tests, capture screenshots, and prepare the final submission. Rotate who drives integration and who reviews so both members understand the whole system.

This is a true two-member team plan for Group 2. The domain split avoids duplicate implementation while shared design, review, integration, and evaluation provide meaningful and approximately equal contributions. Rebalance implementation, testing, and documentation tasks if one member's workload diverges; task ownership is for coordination, not exclusive ownership of the final result.

### Deadline-driven calendar plan

| Date (2026) | Focus | End-of-day checkpoint |
|---|---|---|
| **Nov 14** | Phase 0-1: agree input/result contracts and A-D scenario schema; prepare shared fixtures; verify local Ollama tool calling. | Both members can independently explain the contract; fixture and model smoke checks pass. |
| **Nov 15** | Phases 2-3: build classical and Learning Agents alongside the LLM tools/agent; review each other's unit tests. | Five classical decisions pass focused tests; LLM proves two tool calls using scenario evidence. |
| **Nov 16** | Phases 4-5: integrate orchestrator, verify same-input behavior, build and run the Streamlit comparison. | All six agents run against A-D; results/errors and comparison are visible. |
| **Nov 17** | Phase 6: regression tests, scenario screenshots, README/setup and comparison explanation; resolve issues jointly. | Submission checklist complete and results recorded. |
| **Nov 18 (due 11:59 PM)** | Final clean-environment run, verify files/screenshots and GitHub state; reserve for blockers. | Submit before 11:59 PM; avoid optional feature work. |

The plan targets roughly four focused implementation days with two contributors and a final-day buffer. It is an aggressive schedule, especially if Ollama downloads or tool calling require troubleshooting; prioritize the acceptance criteria and defer optional polish.

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

- [ ] Five separate classical-agent implementations and tests
- [ ] LangChain agent connected to a local Ollama model; configured model and run instructions documented
- [ ] At least two relevant LLM tool calls recorded, with recommendations grounded in returned evidence
- [ ] Shared scenario/result contract and integration test proving the same scenario reaches all six agents
- [ ] Scenario fixtures and results for A (DB pool exhaustion), B (traffic/CPU spike), C (config startup failure), and D (ambiguous evidence)
- [ ] Learning Agent experience store, controlled feedback update, test, and explanation of its effect
- [ ] Streamlit scenario selector, six decision/reasoning views, and comparison table
- [ ] Comparison explanation describing why the agents may reach different recommendations
- [ ] `requirements.txt`, README, setup instructions, architecture diagram/reference, and test plan
- [ ] Recorded test commands/results, including any skipped Ollama integration tests and reasons
- [ ] Screenshots for A, B, and C; include D and Learning Agent before/after feedback when practical
- [ ] Final source and evidence pushed to the Group 2 GitHub repository
