# Contributing to PaperSeek

PaperSeek is an early-stage literature-search agent. Contributions are welcome, especially around data-source adapters, ranking prompts, diagnostics, tests, and documentation.

## Development Setup

```bash
git clone https://github.com/MingfengHong/paperseek.git
cd paperseek
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

On Windows PowerShell, activate the environment with:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Local Checks

Run these before opening a pull request:

```bash
python -m compileall -q paperseek skills/paperseek/scripts
python -m unittest discover -s tests
node --check paperseek/static/app.js
python -m pip wheel . -w dist --no-deps
```

The smoke commands below make live network requests and may be skipped in offline CI:

```bash
paperseek smoke --source openalex --query "machine learning"
paperseek smoke --source crossref --query "open innovation"
```

## Scope Guidelines

- Keep API keys, cookies, and private credentials out of commits.
- Keep `skills/paperseek/` optional. It should not be installed automatically with the Python package.
- Add tests for CLI contracts, result schema changes, provider parsing, and Web API behavior.
- Treat LLM relevance scores as triage signals, not evidence that a literature review is complete.
- Do not add PDF-downloading or paywall-bypass behavior.

## Pull Request Notes

Please include:

- What changed and why.
- Which checks were run.
- Whether the change affects CLI, Web UI, Skill behavior, data-source adapters, or result schema.
- Any known limitations or API-provider assumptions.
