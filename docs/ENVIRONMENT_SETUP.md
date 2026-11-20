# Environment Setup

This guide covers setup, testing, and running the Intelligent Production Incident Management System. Commands are for Windows PowerShell.

## Prerequisites

- Windows 10/11 (or another OS with equivalent Python, Git, and Ollama support).
- Python 3.11 or newer.
- Git and a GitHub account.
- Ollama installed and running locally.
- Internet access for the initial package and model downloads.

Use a local model compatible with LangChain tool calling. The initial local setup uses `qwen3:4b`, configurable through `INCIDENT_AGENT_OLLAMA_MODEL`. Ollama and its model weights are installed outside the Git repository; do not commit model files.

## Clone the repository

Clone the existing Group 2 repository and open its folder in VS Code:

```powershell
git clone https://github.com/2025paml611/production-incident-agent.git
Set-Location production-incident-agent
code .
```

## Python environment

Create a project-local virtual environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

PowerShell activation may be blocked by the machine's execution policy. You do not need to activate the environment; invoke its Python directly to ensure packages install into the project environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The LangChain versions are pinned together to avoid `uuid-utils`, whose native DLL was blocked by Windows Application Control on the development laptop. `langchain-ollama==0.3.10` supports `langchain-core==0.3.82`; `langsmith==0.4.52` satisfies Core without that native dependency. Keep these pins together unless an alternate dependency chain is verified on the target machine. Tests use Python's standard `unittest` library.

## Ollama and model

1. Install Ollama using its official Windows installer and start the Ollama service.
2. Pull the selected Qwen3 model:

   ```powershell
   ollama pull qwen3:4b
   ollama list
   ```

3. If using a different installed tag, set `INCIDENT_AGENT_OLLAMA_MODEL`. The default is `qwen3:4b`.
4. Verify the model can call the registered incident tools before relying on its recommendation.

Do not put credentials or machine-specific secrets in source control. The local demo should use fixture-backed incident evidence and should not require production credentials.

## Run and test

Run the deterministic unit tests with:

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The live Ollama integration test is opt-in because it loads the local model and can take longer than deterministic unit tests. Ollama 0.40.16 with `qwen3:4b` passed this test on November 14 and November 15, 2026. The test exercises the incident agent, requiring tool calls and validating that the returned recommendation cites evidence from the tool results. The latest run is recorded in [Test Results](TEST_RESULTS.md).

```powershell
$env:PYTHONPATH = "$PWD\src"
$env:RUN_OLLAMA_INTEGRATION = "1"
.\.venv\Scripts\python.exe -m unittest tests.integration.test_ollama_tool_calling -v
$env:RUN_OLLAMA_INTEGRATION = $null
```

It exercises the incident agent end-to-end, checking that the Ollama response uses exact evidence quotes returned by at least two tools.

Start the Streamlit app:

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m streamlit run src\incident_agent\app\streamlit_app.py
```

Select one of scenarios A-D and choose **Compare all six agents**. The Ollama model must be running for its result; other agents still report their results if it is unavailable. Learning history changes only when an explicit success/failure outcome is recorded in the UI.

## Troubleshooting checklist

- Confirm `.venv\Scripts\python.exe --version` reports the expected version.
- Confirm Ollama is running and `ollama list` includes the configured model.
- Check that the configured model tag exactly matches the installed tag.
- If tool calls fail, verify the model's tool-calling support and inspect the app's displayed error rather than treating an ungrounded response as a successful investigation.
- Run the classical agents and tests without Ollama when diagnosing local-model availability issues.
