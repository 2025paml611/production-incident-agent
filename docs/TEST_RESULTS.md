# Test Results

## Environment

- Date: November 15, 2026
- Python: 3.14.4 (project virtual environment)
- Ollama: 0.40.16
- Model: `qwen3:4b`

## Deterministic suite

Command:

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Result: **46 tests passed; 1 opt-in live Ollama test skipped.** The skip is expected
unless `RUN_OLLAMA_INTEGRATION=1` is set.

## Live Ollama tool-calling test

Command:

```powershell
$env:PYTHONPATH = "$PWD\src"
$env:RUN_OLLAMA_INTEGRATION = "1"
.\.venv\Scripts\python.exe -m unittest tests.integration.test_ollama_tool_calling -v
$env:RUN_OLLAMA_INTEGRATION = $null
```

Result: **1 test passed** using local Ollama `0.40.16` and `qwen3:4b`. The
integration test verifies that the model calls at least two different fixture-bound
evidence tools and cites exact text from their returned results.

## Scope and limitations

The scenario inputs and tool data are synthetic fixtures. Passing tests demonstrate
the application behavior against those fixtures; they do not establish diagnosis
accuracy on live production telemetry. The Streamlit UI flow tests use deterministic
stub agents, while the Ollama integration test exercises the local model separately.

## End-to-end scenario runs

On November 15, 2026, the Streamlit application was run locally against scenarios A,
B, C, and D using Ollama `qwen3:4b`. All six agents returned results in each run,
including the LLM's fixture-grounded tool-call evidence. The scenarios are synthetic;
these runs verify the demo flow, not behavior against live service data.

The local Streamlit endpoint returned **HTTP 200** at `http://127.0.0.1:8765/`.
This was verified in the existing project environment; a separate clean-environment
installation was subsequently verified on November 20, 2026, as detailed below.

## Clean-environment re-verification

On November 20, 2026, the project dependencies were installed into a new temporary
virtual environment using Python 3.14.4. `pip check` reported no broken requirements.
The full deterministic suite passed: **46 tests passed; 1 opt-in live Ollama test
skipped**.

The opt-in Ollama tool-calling test was then run from that environment against local
Ollama 0.40.16 and `qwen3:4b`: **1 test passed** in 147.546 seconds. It verified
calls to at least two different fixture-bound tools and exact evidence citations.

The Streamlit app was started from the clean environment on port 8768, and a direct
local HTTP probe returned **200**. The first PowerShell `Invoke-WebRequest` probe
did not connect; retrying with `curl.exe --noproxy "*"` succeeded. No application
code changes were needed.

Commands used:

```powershell
$cleanEnv = Join-Path $env:TEMP 'production-incident-agent-clean-env-20261120'
py -3.14 -m venv $cleanEnv
$python = Join-Path $cleanEnv 'Scripts\python.exe'
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt
& $python -m pip check
$env:PYTHONPATH = "$PWD\src"
& $python -m unittest discover -s tests -v
$env:RUN_OLLAMA_INTEGRATION = "1"
& $python -m unittest tests.integration.test_ollama_tool_calling -v
$env:RUN_OLLAMA_INTEGRATION = $null
& $python -m streamlit run src\incident_agent\app\streamlit_app.py --server.headless=true --server.port=8768 --browser.gatherUsageStats=false
```

In a second terminal, the local app endpoint was checked with:

```powershell
curl.exe --noproxy "*" -sS -o NUL -w "HTTP %{http_code}`n" --max-time 5 http://127.0.0.1:8768/
```

The isolated environment was used only for verification and is not part of the repository.

## Scenario screenshots

Captured from the running Streamlit application with the local Ollama model:

- [Scenario A — database pool exhaustion](../screenshots/scenario-A-comparison.png)
- [Scenario B — traffic and CPU spike](../screenshots/scenario-B-comparison.png)
- [Scenario C — configuration startup failure](../screenshots/scenario-C-comparison.png)
- [Scenario D — ambiguous evidence](../screenshots/scenario-D-full-comparison.png)
- [Scenario A — expanded Learning Agent and LLM evidence](../screenshots/scenario-A-agent-details.png)

Each comparison image is a full-page capture showing the scenario snapshot and all
six agent rows; individual agent details can be expanded in the running app. The
supplementary Scenario A image also expands the Learning Agent's experience counts
and explicit feedback controls, and the LLM's tool evidence and tool-call summaries.
