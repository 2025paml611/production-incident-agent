# production-incident-agent

Intelligent Production Incident Management System (Assignment 1-set-1 - Group-2).

A Group 2 team project with two equal contributors comparing five classical AI agents and one local-LLM agent on the same production-incident scenario. The application will show their recommendations and supporting evidence in a Streamlit interface.

## Project status

Phases 1-3 are complete: shared scenario/result models, four synthetic fixtures, five classical agents, Learning Agent experience tracking, fixture-bound LangChain tools, and the Ollama agent are implemented and tested. The Ollama agent requires evidence from at least two tools and validates exact evidence quotes before returning a recommendation. Six-agent orchestration and the Streamlit UI are planned for later phases.

## Implemented capabilities

- Simple Reflex, Model-Based Reflex, Goal-Based, Utility-Based, and Learning agents.
- An Ollama-backed LangChain agent that investigates incidents through four fixture-bound evidence tools.
- Exact evidence citations from at least two tools, with malformed or unsupported recommendations rejected.
- Unit tests for classical agents, tool behavior, and LLM grounding; an opt-in live Qwen3 integration test.

## Planned capabilities

- Orchestrate all six agents against the same selected scenario.
- Streamlit scenario selection, per-agent reasoning, and a comparison view.

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
6. Add the source directory to `PYTHONPATH` to run the unit tests or the opt-in Ollama test:

   ```powershell
   $env:PYTHONPATH = "$PWD\src"
   .\.venv\Scripts\python.exe -m unittest discover -s tests -v
   $env:RUN_OLLAMA_INTEGRATION = "1"
   .\.venv\Scripts\python.exe -m unittest tests.integration.test_ollama_tool_calling -v
   ```

The live integration test contacts the local Ollama model and can take longer than the unit tests. The UI and run command will be added in a later phase.

## Submission evidence

The final submission will include source code, `requirements.txt`, test results, and screenshots of the three required scenarios (plus the ambiguous case if implemented).
