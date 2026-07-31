# AI Coding Agent

A production-minded Python 3.11 AI Coding Agent that analyzes an existing local
repository and implements a product request with help from Google Gemini.

The included target repository is a Node.js notes application located at
`./target_repo`. The agent does not rewrite that application. It explores the
existing structure, plans a focused change, asks Gemini for complete-file edits,
applies those edits safely inside `target_repo`, verifies the result, and
produces an engineering summary.

## Architecture Diagram

```text
User Request
    |
    v
RepositoryExplorer
    |
    v
RepositorySummary
    |
    v
Planner
    |
    v
ExecutionPlan
    |
    v
GeminiClient
    |
    v
CodeEditor
    |
    v
Verifier
    |
    v
Summarizer
```

## Folder Structure

```text
AI-Coding-Agent/
|-- agent.py
|-- config.py
|-- editor.py
|-- explorer.py
|-- llm.py
|-- logger.py
|-- planner.py
|-- README.md
|-- requirements.txt
|-- summarizer.py
|-- verifier.py
|-- logs/
`-- target_repo/
```

## Workflow

1. The user request is accepted from the CLI or the default assignment prompt.
2. The repository explorer scans `target_repo`.
3. A structured repository summary is generated.
4. The planner selects a practical feature direction and likely files to edit.
5. Gemini receives the repository context and execution plan.
6. Gemini returns complete-file updates using a strict `BEGIN_FILE` format.
7. The editor validates paths and writes changes inside `target_repo`.
8. The verifier checks syntax and consistency.
9. The summarizer prints the final run report.

## Repository Exploration

`explorer.py` walks the entire target repository while ignoring noisy folders:

- `node_modules`
- `.git`
- `dist`
- `build`
- `coverage`
- `venv`
- `__pycache__`

It prioritizes files and directories commonly needed for product changes:

- `README` / `Readme.md`
- `package.json`
- routes
- controllers
- models
- services
- middlewares
- config

The output is a `RepositorySummary` dataclass that can be rendered into prompt
context for the LLM.

## Planning

`planner.py` converts the product request and repository summary into an
`ExecutionPlan`.

For the assignment request:

```text
Improve the application so users can better organise and search their notes.
```

the planner chooses a cohesive direction such as adding note organization
metadata plus search/filter support. The planner is intentionally reusable so
future requests like note priority, archive, favourites, reminders, sharing, or
recently edited notes can follow the same workflow.

## Code Generation

`llm.py` wraps the Google Gemini API through the supported `google-genai` SDK.

The prompt asks Gemini to return only complete-file changes:

````text
BEGIN_FILE: app/models/note.model.js
```language
complete file content
```
END_FILE
````

This keeps the LLM boundary predictable and lets the editor apply changes
without parsing free-form prose.

## Editing

`editor.py` parses each `BEGIN_FILE` block, normalizes the path, and ensures the
destination remains inside `target_repo`.

It supports:

- updating existing files
- creating new files
- skipping unchanged files
- rejecting unsafe paths

## Verification

`verifier.py` performs lightweight checks designed for fast interview-style
evaluation:

- Python syntax checks for the agent modules
- duplicate generated file detection
- `package.json` parsing
- JavaScript syntax checks with `node --check` when Node.js is available

These checks are not a replacement for a full test suite, but they catch common
LLM generation mistakes before the run is considered successful.

## How to Run

Create and activate a virtual environment, then install dependencies:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a `.env` file:

```text
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-3.6-flash
```

Run the default assignment request:

```powershell
python agent.py
```

Run a different request:

```powershell
python agent.py --request "Add note priority"
```

Enable verbose logs:

```powershell
python agent.py --verbose
```

## Environment Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `GEMINI_API_KEY` | Yes | None | Google Gemini API key loaded from `.env`. |
| `GEMINI_MODEL` | No | `gemini-3.6-flash` | Gemini model used for implementation generation. |
| `MAX_FILE_SIZE_BYTES` | No | `120000` | Largest file the explorer will read. |
| `MAX_PROMPT_CHARS` | No | `120000` | Maximum repository context passed into the prompt. |

## Logging

Console logs are intentionally clean and professional:

```text
AI Coding Agent Started
Loading Repository...
Repository Loaded
Scanning Files...
Found Controllers
Found Models
Found Routes
Generating Repository Summary...
Creating Execution Plan...
Connecting to Gemini...
Generating Implementation...
Applying Code Changes...
Running Verification...
Generating Summary...
Completed Successfully.
```

Detailed logs are written to:

```text
logs/agent.log
```

## Troubleshooting

If Gemini generation fails with a connection message such as `getaddrinfo
failed`, check your internet connection, DNS, VPN/proxy settings, and whether
Google AI Studio endpoints are reachable from the machine running the agent.

If Gemini reports that a model is unavailable, update `GEMINI_MODEL` in `.env`
to a currently supported Google AI Studio model.

## Assumptions

- The target repository is already downloaded at `./target_repo`.
- The agent may modify files only inside `target_repo`.
- Gemini returns complete file content in the requested format.
- The most valuable implementation is a small cohesive product improvement, not
  a rewrite.
- The target app should preserve its existing behavior unless the request
  clearly requires a change.

## Trade-offs

- Complete-file replacement is easier to validate than free-form edits, but it
  can produce larger diffs than unified patches.
- The planner uses deterministic heuristics before the LLM step; this improves
  reliability but does not replace deeper semantic code analysis.
- Verification is intentionally lightweight so the assignment remains scoped to
  a 2-3 hour implementation.
- The agent avoids adding dependencies unless the existing application clearly
  needs them.

## Future Improvements

- Add unit test generation when the target repository has a test framework.
- Add unified diff support for smaller patches.
- Add optional Git branch creation and commit generation.
- Add richer dependency and import graph analysis.
- Add retry and repair loops when verification fails.
"# AI-Coding-Agent" 
