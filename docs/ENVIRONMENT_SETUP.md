# Environment Setup

This guide describes the planned development setup for the Intelligent Production Incident Management System. Commands are for Windows PowerShell.

## Prerequisites

- Windows 10/11 (or another OS with equivalent Python, Git, and Ollama support).
- Python 3.11 or newer.
- Git and a GitHub account.
- Ollama installed and running locally.
- Internet access for the initial package and model downloads.

Use a local model compatible with LangChain tool calling. Qwen3 is a candidate; confirm the selected Ollama model and its tool-call behavior during implementation. The model should be configurable rather than hard-coded.

## Create the GitHub repository

1. Create a new, empty GitHub repository under your account.
2. Choose a descriptive name such as `production-incident-agent`.
3. Do not initialize it with files if you plan to push an existing local project.
4. Clone it and open its folder in VS Code:

   ```powershell
   git clone https://github.com/<your-username>/production-incident-agent.git
   Set-Location production-incident-agent
   code .
   ```

Replace `<your-username>` with your GitHub username. Keep repository visibility and any course-specific sharing requirements in mind.

## Python environment

Create a project-local virtual environment and activate it:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

If PowerShell prevents activation, use the Python executable directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

After `requirements.txt` is created, install dependencies:

```powershell
pip install -r requirements.txt
```

The dependency list is expected to include Streamlit, LangChain's Ollama integration, and the project's test dependencies. Exact package names and compatible versions must be pinned or bounded based on the implemented APIs.

## Ollama and model

1. Install Ollama using its official installer and start the Ollama service.
2. Pull the chosen model using the model name documented by the project. For example, after selecting a suitable Qwen3 tag:

   ```powershell
   ollama pull <model-tag>
   ollama list
   ```

3. Configure the application to use that exact installed model and the local Ollama endpoint.
4. Verify the model can call the registered incident tools before relying on its recommendation.

Do not put credentials or machine-specific secrets in source control. The local demo should use fixture-backed incident evidence and should not require production credentials.

## Run and test

Once implementation is complete, the intended commands are:

```powershell
$env:PYTHONPATH = "$PWD\src"
streamlit run src\incident_agent\app\streamlit_app.py
python -m unittest discover -s tests -v
```

Use the final README and `--help` output, if provided, as the source of truth if the entry point or test command changes.

## Troubleshooting checklist

- Confirm the virtual environment is active and `python --version` reports the expected version.
- Confirm Ollama is running and `ollama list` includes the configured model.
- Check that the configured model tag exactly matches the installed tag.
- If tool calls fail, verify the model's tool-calling support and inspect the app's displayed error rather than treating an ungrounded response as a successful investigation.
- Run the classical agents and tests without Ollama when diagnosing local-model availability issues.
