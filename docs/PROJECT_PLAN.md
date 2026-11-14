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

## Milestones

| Milestone | Work | Completion evidence |
|---|---|---|
| 1. Repository and setup | Create the GitHub repository, Python environment, documentation, and project skeleton. | Repository contains setup and architecture docs. |
| 2. Scenarios and shared data | Define typed incident inputs and normal, traffic/CPU, deployment-failure, and ambiguous fixtures. | Tests confirm each agent receives the same selected scenario. |
| 3. Classical agents | Implement each decision mechanism separately with explicit reasoning and recommended actions. | Focused unit tests for each agent and its decision rule. |
| 4. Learning agent | Load experience counts, select an action using the recorded outcomes, and update counts from feedback. | Tests show experience changes the decision or its explanation and persists as designed. |
| 5. LLM tools and agent | Implement fixture-backed evidence tools and a LangChain/Ollama agent that calls at least two tools. | Tests or recorded demo evidence show tool results are used in the response. |
| 6. Streamlit comparison UI | Add scenario selection, run all agents on shared input, and display individual results and comparison. | Demonstration screenshots for required scenarios. |
| 7. Validation and submission | Run tests, capture results/screenshots, finish documentation, and check repository contents. | Reproducible setup, test output, screenshots, and submission checklist. |

## Two-contributor effort and schedule

The estimates below are planning estimates, not guarantees. They distinguish **person-hours** (sum of contributors' work) from **calendar time** (elapsed time, with independent tasks done in parallel).

| Workstream | Estimated person-hours | Primary owner |
|---|---:|---|
| Repository setup and architecture | 1.5 | Joint |
| Five classical agents | 4 | Contributor 1 |
| Ollama/LangChain agent and four evidence tools | 7 | Contributor 2 |
| Learning Agent and experience store | 2 | Contributor 1 |
| Shared scenarios, common contract, and orchestrator | 2 | Joint, led by Contributor 1 |
| Streamlit comparison UI | 3 | Contributor 2, using the agreed contract |
| Testing and evaluation | 3 | Joint |
| Integration and debugging buffer | 4 | Joint |
| Documentation and screenshots | 2 | Joint |
| **Estimated total** | **28.5 person-hours** | |

These estimates follow the task-level breakdown above and sum to about 28.5 person-hours. They assume the local model is available and tool-calling compatible; model troubleshooting can add time. Two contributors do not halve the work because interface agreement, integration, and end-to-end testing are shared or sequential tasks.

### Suggested ownership

- **Contributor 1 — classical agents and shared contracts:** define scenario/result types with Contributor 2; implement the five classical agents, Learning Agent experience updates, and focused tests.
- **Contributor 2 — LLM and UI:** use the agreed contracts; implement the fixture-backed evidence tools, LangChain/Ollama agent, and Streamlit comparison UI.
- **Joint — integration and submission:** agree on the contract before parallel work, integrate via small changes, verify identical scenario inputs and tool evidence, run tests, and capture screenshots.

This is a true two-member team plan for Group 2. Both members contribute equally, and the work is split by domain expertise while keeping a common interface for all six agents. A single owner is listed only for task tracking and progress visibility, not for exclusive ownership of the final result.

### Deadline-driven calendar plan

| Date (2026) | Focus | End-of-day checkpoint |
|---|---|---|
| **Nov 14** | Freeze shared scenario/result contract; create A-D fixtures. In parallel, scaffold classical-agent interfaces and verify Ollama model/tool-call feasibility. | Both workstreams can integrate without changing the common contract. |
| **Nov 15** | Implement and unit-test the five classical agents and Learning Agent; implement the four evidence tools and LLM tool-calling path. | Classical decisions work on fixtures; LLM demonstrates at least two tool calls. |
| **Nov 16** | Integrate the orchestrator and Streamlit UI; compare all six agents on each shared scenario. | End-to-end A-D runs work with visible evidence and errors. |
| **Nov 17** | Run tests, fix integration issues, capture scenario screenshots, complete README/setup and comparison explanation. | Submission checklist is substantially complete; test results are recorded. |
| **Nov 18 (due 11:59 PM)** | Final clean-environment run, verify files/screenshots and repository state; reserve this day for blockers. | Submit before the deadline; avoid starting optional features. |

The plan targets roughly four focused implementation days with two contributors and a final-day buffer. It is an aggressive schedule, especially if Ollama downloads or tool calling require troubleshooting; prioritize the acceptance criteria and defer optional polish.

## Acceptance criteria

- Five distinct classical agents use their intended decision mechanisms; they are not aliases of one common rule.
- The LLM agent calls at least two relevant tools and cites or summarizes evidence returned by those tools.
- All six agents analyze the same selected scenario data on each comparison run.
- Scenarios cover the required database-pool incident, high-CPU traffic spike, and configuration-induced startup failure; an ambiguous/incomplete evidence scenario is also included.
- Each result includes an incident summary, evidence, likely cause, recommended action, verification steps, and limitations (or clearly marks any unavailable field).
- The Learning Agent uses and updates experience counts, and explains how those counts influence its recommendation.
- The Streamlit UI presents each agent's decision and reasoning and makes differences visible.
- Tests and screenshots are included in the submission.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Selected local model does not reliably support tool calling. | Test tool calls early; choose a compatible Ollama model and expose a clear error if investigation tools are not called. |
| Stochastic LLM output makes comparisons hard to reproduce. | Use fixed scenario fixtures, low temperature where supported, and display exact tool evidence alongside the response. |
| Agents receive subtly different inputs. | Construct one immutable scenario object per run and pass it to every agent; test scenario identity/content. |
| Learning results depend on prior runs. | Make experience data visible, document reset/seed behavior, and test with known counts. |
| Suggestions could be unsafe if applied automatically. | Recommendations are advisory only; require a human operator and include verification/rollback steps. |

## Submission checklist

- [ ] Source for five classical agents and the Ollama/LangChain agent
- [ ] `requirements.txt`
- [ ] Streamlit UI and setup/run documentation
- [ ] At least three scenario results, including normal, critical/failure, and ambiguous/edge behavior
- [ ] Evidence that the LLM called at least two tools
- [ ] Learning experience data and explanation of its effect
- [ ] Comparison table and explanation of differing decisions
- [ ] Screenshots and test results
