# production-incident-agent

Intelligent Production Incident Management System (Assignment 1-set-1 - Group-2).

A Group 2 team project with two equal contributors comparing five classical AI agents and one local-LLM agent on the same production-incident scenario. The application will show their recommendations and supporting evidence in a Streamlit interface.

## Project status

This repository is at the planning and documentation stage. The implementation and screenshots will be added in later milestones.

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
3. Create and activate a virtual environment:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

4. Install project dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. Start Ollama and download a model that supports tool calling (for example, a compatible Qwen3 model). Set the exact model name in the app configuration.
6. Add the source directory to `PYTHONPATH`, then start the UI:

   ```powershell
   $env:PYTHONPATH = "$PWD\src"
   streamlit run src\incident_agent\app\streamlit_app.py
   ```

The final setup instructions, model name, and run command will be confirmed against the implemented code before submission.

## Submission evidence

The final submission will include source code, `requirements.txt`, test results, and screenshots of the three required scenarios (plus the ambiguous case if implemented).
