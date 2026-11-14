# production-incident-agent

Intelligent Production Incident Management System (Assignment 1-set-1 - Group-2).

A Group 2 team project with two equal contributors comparing five classical AI agents and one local-LLM agent on the same production-incident scenario. The application will show their recommendations and supporting evidence in a Streamlit interface.

## Project status

Phases 1 and 2 are complete: shared scenario/result models, four synthetic fixtures, five classical agents, and Learning Agent experience tracking are implemented with unit tests. Ollama 0.40.16 and Qwen3:4b are installed on the primary laptop; the LangChain smoke test successfully called two tools. The full LLM evidence-grounding implementation is still planned for Phase 3.

## Planned capabilities

- Simple Reflex, Model-Based Reflex, Goal-Based, Utility-Based, and Learning agents.
- An Ollama-backed LangChain agent that investigates incidents through evidence tools.
- Shared scenario data so agent recommendations can be compared fairly.
- Streamlit scenario selection, per-agent reasoning, and a comparison view.
- Scenario and agent tests, including a critical failure and an ambiguous evidence case.

## Documentation

- [Environment setup](docs/ENVIRONMENT_SETUP.md)
- [Project plan and phase checklists](docs/PROJECT_PLAN.md)
- [Project architecture](docs/ARCHITECTURE.md)
- [Test plan](docs/TEST_PLAN.md)

## Planned quick start (Windows PowerShell)

The commands below are the intended workflow; run them after the application files and `requirements.txt` have been implemented.

1. Install Python 3.11 or newer, Git, and [Ollama](https://ollama.com/download).
2. Clone the GitHub repository, then open a terminal in its root.
3. Create a virtual environment:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install --upgrade pip
   ```

4. Install project dependencies:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

5. Start Ollama and confirm `qwen3:4b` is available with `ollama list`. Set `INCIDENT_AGENT_OLLAMA_MODEL` if using a different installed model.
6. Add the source directory to `PYTHONPATH`, then start the UI:

   ```powershell
   $env:PYTHONPATH = "$PWD\src"
   .\.venv\Scripts\python.exe -m streamlit run src\incident_agent\app\streamlit_app.py
   ```

The final setup instructions, model name, and run command will be confirmed against the implemented code before submission.

## Submission evidence

The final submission will include source code, `requirements.txt`, test results, and screenshots of the three required scenarios (plus the ambiguous case if implemented).
