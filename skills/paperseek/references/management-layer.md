# Management Layer Reference

Use this reference when checking whether PaperSeek is installed, configured, healthy, or ready for a live literature search. These commands support readiness and troubleshooting; they do not perform a full literature task by themselves.

## Skill Script Launcher

The Skill includes:

```bash
python skills/paperseek/scripts/paperseek.py
```

This script is a package-aware launcher with a self-contained fallback runtime. It first tries the full PaperSeek Python package. If the package is not importable, it falls back to `scripts/paperseek_skill_runtime.py`, which can run core `search`, `smoke`, `sources`, `doctor`, `config`, and `history path` commands without third-party dependencies.

Use the launcher when a standalone Skill distribution needs a stable script entrypoint:

```bash
python skills/paperseek/scripts/paperseek.py --help
python skills/paperseek/scripts/paperseek.py search "platform governance and user innovation" --source openalex --json
python skills/paperseek/scripts/paperseek.py doctor
python skills/paperseek/scripts/paperseek.py smoke --source openalex --query "machine learning" --json
```

If the full package is not importable:

```bash
python skills/paperseek/scripts/paperseek.py --install-help
```

When the Skill is distributed separately from the repository, the bundled runtime can still search OpenAlex/Crossref/WoS directly. Install the full PaperSeek package only when the user needs the Web UI, citation maps, full history commands, or exact package parity. If the package source exists locally but is not importable, set:

```bash
PAPERSEEK_PROJECT_ROOT=/path/to/paperseek
```

## Health Commands

```bash
python skills/paperseek/scripts/paperseek.py --help
python skills/paperseek/scripts/paperseek.py doctor
python skills/paperseek/scripts/paperseek.py doctor --json
python skills/paperseek/scripts/paperseek.py sources
python skills/paperseek/scripts/paperseek.py sources --json
python skills/paperseek/scripts/paperseek.py smoke --source openalex --query "machine learning" --json
paperseek history list
paperseek config list
```

| Command | Purpose | Use when |
| --- | --- | --- |
| `paperseek doctor` | Static configuration diagnostics without live source requests | First use, uncertain setup, or before a real search |
| `paperseek doctor --json` | Machine-readable diagnostics | Agent needs to decide next action |
| `paperseek smoke --source SOURCE --query QUERY --json` | Minimal live request to one literature source | Network, source availability, or key validity is uncertain |
| `paperseek sources --json` | Source capability registry | Need to know supported fields and source limits |
| `paperseek history list` | Local saved-run index | User asks to recall prior searches on this self-hosted instance |
| `paperseek config list` | Masked user-level config view | Need to check whether values are configured |

## Configuration Sources

Priority:

1. Shell environment variables.
2. User-level PaperSeek config under `~/.config/paperseek/config.json` unless `PAPERSEEK_CONFIG_FILE` or `PAPERSEEK_CONFIG_DIR` overrides it.
3. CLI flags.
4. Built-in defaults.

The Web UI uses request/session values only. It does not save API keys or endpoint settings.

Local search history is separate from user-level config. It is stored in SQLite under `~/.paperseek/paperseek.db` by default and can be disabled with `PAPERSEEK_HISTORY_ENABLED=false`.

## User-Level Config

Use these only when the user wants CLI configuration saved locally:

```bash
paperseek config path
paperseek config keys
paperseek config set LLM_PROVIDER deepseek
paperseek config set LLM_API_TYPE openai_chat
paperseek config set LLM_BASE_URL https://api.deepseek.com
paperseek config set LLM_API_KEY YOUR_KEY
paperseek config list
paperseek config unset LLM_API_KEY
```

Never write real keys into Skill files, README, tests, logs, or chat. `paperseek config list` masks secret values; still avoid copying secret-like output unless necessary.

## Web UI

Start the UI:

```bash
paperseek-web
```

The Web UI requires the full PaperSeek package. The standalone Skill runtime is CLI-only.

Fallback:

```bash
python -m paperseek.web_app
```

Default URL:

```text
http://127.0.0.1:8765/
```

If the port is busy, run uvicorn manually with another port:

```bash
python -m uvicorn paperseek.web_app:app --host 127.0.0.1 --port 8766
```

The Web UI provides `Check Config`, which calls `/api/diagnostics` and does not perform a live literature source request.

## Interpreting Doctor

Statuses:

- `pass`: usable.
- `warning`: usable but degraded or recommended config is missing.
- `fail`: required config or command contract is broken.

Common findings:

- Missing `LLM_API_KEY`: required unless provider is `ollama`.
- Missing `OPENALEX_API_KEY`: warning; live test may still work, but stable use should configure it.
- Missing `CROSSREF_EMAIL`: warning; Crossref polite-pool email is recommended.
- WoS marked temporarily unavailable: prefer OpenAlex while Clarivate access is being verified.
