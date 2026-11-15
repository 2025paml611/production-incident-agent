# production-incident-agent

Intelligent Production Incident Management System (Assignment 1-set-1 - Group-2).

A solo Group 2 project comparing five classical AI agents and one local-LLM agent on the same production-incident scenario. The application shows their recommendations and supporting evidence in a Streamlit interface.

## Project status

Phases 1-5 are complete: shared scenario/result models, four synthetic fixtures, five classical agents, Learning Agent experience tracking, fixture-bound LangChain tools, the Ollama agent, six-agent orchestration, and the Streamlit comparison UI are implemented and tested. Each comparison run supplies the same selected scenario to all agents, surfaces individual failures, and changes learning history only after explicit outcome feedback. The Ollama agent requires evidence from at least two tools and validates exact evidence quotes before returning a recommendation.

## Implemented capabilities

- Simple Reflex, Model-Based Reflex, Goal-Based, Utility-Based, and Learning agents.
- An Ollama-backed LangChain agent that investigates incidents through four fixture-bound evidence tools.
- Exact evidence citations from at least two tools, with malformed or unsupported recommendations rejected.
- Orchestration that runs all six agents against one shared scenario and reports partial failures.
- Explicit Learning Agent outcome recording, separate from comparison runs.
- Streamlit scenario selection, synthetic metric snapshot cards with source/time context,
  per-agent reasoning, and a readable comparison view.
- Unit tests for classical agents, orchestration, tool behavior, and LLM grounding; an opt-in live Qwen3 integration test.

## Remaining work

- Phase 6: final evaluation, screenshots, and submission checklist.

## Documentation

- [Environment setup](docs/ENVIRONMENT_SETUP.md)
- [Project plan and phase checklists](docs/PROJECT_PLAN.md)
- [Project architecture](docs/ARCHITECTURE.md)
- [Test plan](docs/TEST_PLAN.md)

## Quick start (Windows PowerShell)

1. Install Python 3.11 or newer, Git, and [Ollama](https://ollama.com/download).
2. Install and start the local model (default: `qwen3:4b`), then clone the repository and open a terminal in its root:

   ```powershell
   ollama pull qwen3:4b
   ```

3. Create a virtual environment:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install --upgrade pip
   ```

4. Install project dependencies:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

5. Confirm the model is available with `ollama list`. Set `INCIDENT_AGENT_OLLAMA_MODEL` to use another installed model.
6. Add the source directory to `PYTHONPATH` and run the deterministic tests:

   ```powershell
   $env:PYTHONPATH = "$PWD\src"
   .\.venv\Scripts\python.exe -m unittest discover -s tests -v
   ```

The UI runs all six agents against the same selected synthetic scenario. Its CPU,
request-rate, latency, and database-pool cards show fixture snapshots, not live
telemetry or a time series. The local Ollama model must be running for the LLM
recommendation; its errors are shown alongside other agents' results.

Start the app in a separate terminal:

   ```powershell
   $env:PYTHONPATH = "$PWD\src"
   .\.venv\Scripts\python.exe -m streamlit run src\incident_agent\app\streamlit_app.py
   ```

To run the slower live Ollama verification:

   ```powershell
   $env:RUN_OLLAMA_INTEGRATION = "1"
   .\.venv\Scripts\python.exe -m unittest tests.integration.test_ollama_tool_calling -v
   ```

The live integration test contacts the local Ollama model and can take longer than the unit tests.

## Submission evidence

The final submission will include source code, `requirements.txt`, test results, and screenshots of the three required scenarios (plus the ambiguous case if implemented).
