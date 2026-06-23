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

## Package Release

PaperSeek is published on PyPI as `paperseek`. Do not reuse a released version number; PyPI versions are immutable, so fixes must bump `pyproject.toml` to the next version such as `0.1.1`.

Before uploading:

```bash
python -m pip install --upgrade build twine packaging pkginfo
rm -rf dist build paperseek.egg-info
python -m build
python -m twine check dist/*
```

Install the built wheel in a fresh virtual environment and verify the CLI and Web app:

```bash
python -m venv .venv-pkg-test
source .venv-pkg-test/bin/activate
python -m pip install --upgrade pip
python -m pip install dist/paperseek-*.whl
paperseek --help
python -c "import paperseek, paperseek_core"
```

Publish to TestPyPI first:

```bash
TWINE_USERNAME=__token__ TWINE_PASSWORD=$TESTPYPI_TOKEN \
python -m twine upload --disable-progress-bar --repository-url https://test.pypi.org/legacy/ dist/*
```

When testing TestPyPI, avoid dependency confusion from test packages with the same dependency names. Install PaperSeek from TestPyPI without dependencies, then install dependencies from PyPI:

```bash
python -m pip install --index-url https://test.pypi.org/simple/ --no-deps paperseek==<version>
python -m pip install --index-url https://pypi.org/simple/ \
  "requests>=2.25" "pydantic>=2" "python-dateutil>=2.5" \
  "urllib3>=1.25.3,<3" "typing-extensions>=4.7" "fastapi>=0.100" "uvicorn>=0.23"
```

After TestPyPI install and smoke tests pass, publish to PyPI:

```bash
TWINE_USERNAME=__token__ TWINE_PASSWORD=$PYPI_TOKEN \
python -m twine upload --disable-progress-bar --repository-url https://upload.pypi.org/legacy/ dist/*
```

Then verify the public package:

```bash
python -m venv .venv-pypi-test
source .venv-pypi-test/bin/activate
python -m pip install --upgrade pip
python -m pip install paperseek==<version>
paperseek --help
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
