---
name: paperseek
description: LLM literature-search workflow router for PaperSeek CLI and local Web UI. Use when users ask to search papers, find literature, run natural-language academic search, diagnose PaperSeek configuration, inspect OpenAlex/Crossref/WoS results, export ranked paper lists, or explore citation maps. Guides agents to call paperseek commands, parse JSON output, choose data sources, and avoid storing secrets or downloading paywalled PDFs.
license: Apache-2.0
compatibility: Bundles a self-contained Python standard-library runtime for core OpenAlex/Crossref/WoS literature search. The full PaperSeek package is optional and used automatically when installed.
---

# PaperSeek

You are using PaperSeek as an LLM-based literature search agent. This Skill includes a self-contained runtime under `scripts/` and can run core literature search even when the PaperSeek Python package is not installed. When the package is installed, the launcher automatically delegates to the full CLI/Web/source implementation.

## Reference Rules

- For install, Skill script launching, `doctor`, `smoke`, `config`, health checks, and secrets handling, read `references/management-layer.md`.
- For choosing OpenAlex, Crossref, or WoS Starter and deciding whether citation expansion applies, read `references/source-routing.md`.
- For exact CLI commands, output fields, JSON expectations, and stable command contracts, read `references/cli-contract.md`.
- If a reference conflicts with `paperseek --help`, `paperseek sources --json`, or `paperseek doctor --json`, trust the live CLI and report that the Skill reference may need an update.

## Quick Self-Check

When the environment is uncertain, start with:

```bash
python skills/paperseek/scripts/paperseek.py doctor
python skills/paperseek/scripts/paperseek.py sources
```

For a minimal live source test:

```bash
python skills/paperseek/scripts/paperseek.py smoke --source openalex --query "machine learning" --json
```

For install guidance or full Web UI/citation-map features:

```bash
python skills/paperseek/scripts/paperseek.py --install-help
```

The launcher `skills/paperseek/scripts/paperseek.py` first tries the full PaperSeek package. If that package is unavailable, it falls back to `scripts/paperseek_skill_runtime.py`, which implements standalone `search`, `smoke`, `sources`, `doctor`, `config list/path/keys`, and `history path` using only the Python standard library.

Do not ask the user to paste API keys into chat. Ask them to configure keys locally with environment variables, `paperseek config set ...`, or the Web UI session fields.

## Core Workflows

| User intent | Workflow | First command |
| --- | --- | --- |
| Find papers from a research question | Natural-language literature search | `python skills/paperseek/scripts/paperseek.py search "QUESTION" --source openalex --json` |
| Inspect whether PaperSeek is usable | Diagnostics | `python skills/paperseek/scripts/paperseek.py doctor --json` |
| Test a source with a small real query | Smoke check | `python skills/paperseek/scripts/paperseek.py smoke --source openalex --query "machine learning" --json` |
| Choose source and parameters | Source capability lookup | `python skills/paperseek/scripts/paperseek.py sources --json` |
| Start interactive UI | Local Web UI | `paperseek-web` after installing the full package |

## Default Search Procedure

1. Use OpenAlex as the default source unless the user asks for Crossref or WoS, or the task clearly needs DOI registry metadata.
2. For uncertain environments, run `paperseek doctor --json` before searching.
3. Run search with JSON output for machine parsing:

```bash
python skills/paperseek/scripts/paperseek.py search "open innovation and digital platforms" --source openalex --json
```

4. Parse `ranked` results. Prefer stable fields such as `relevance_score`, `citation_count`, `venue`, `doi`, `url`, `abstract`, and `relevance_reason`.
5. Report search query, source, iteration count, result count, and the top ranked papers. Do not treat LLM relevance score as proof of quality.
6. If the result set is poor, broaden or narrow the natural-language question and rerun. Do not fabricate missing DOI, authors, abstracts, or citations.

## Output Boundaries

- PaperSeek returns metadata and ranked candidate lists. It does not download PDFs.
- It may return links to records, DOI pages, OpenAlex records, or available PDF URLs from metadata, but those are not guaranteed access rights.
- WoS Starter should be treated as key-backed and currently marked temporarily unavailable in the UI.
- Crossref is good for DOI and bibliographic metadata; it is not the best sole source for semantic recall.
- The standalone Skill runtime does not perform citation expansion. Install the full PaperSeek package for citation maps and the Web UI.

## Failure Handling

| Situation | Action |
| --- | --- |
| CLI missing | Use `python skills/paperseek/scripts/paperseek.py ...`; install the full package only for Web UI/citation maps/full workflow parity. |
| Missing LLM key | Standalone search still works with deterministic query/ranking heuristics; tell user to set `LLM_API_KEY` for LLM query refinement and ranking. |
| OpenAlex warning about key | Explain that OpenAlex can be tested without a key but stable usage should configure `OPENALEX_API_KEY`. |
| Crossref warning about email | Suggest `CROSSREF_EMAIL` for polite-pool requests. |
| WoS 401 or missing key | Check `WOS_API_KEY` and Starter API entitlement. |
| WoS 512 | Treat as Clarivate upstream or query compatibility issue; retry with simpler query or switch to OpenAlex while investigating. |
| Zero or weak results | Try shorter English keywords, remove narrow field hints, or switch data source. |

## Do Not Do

- Do not store API keys in Skill files, README files, tests, or chat.
- Do not use PaperSeek for paywall bypass, Sci-Hub fallback, or bulk PDF downloading.
- Do not invent paper metadata from model memory.
- Do not claim a systematic review is complete from PaperSeek output alone.
