# PaperSeek CLI Contract

This reference records the stable CLI surface the PaperSeek Skill may rely on. If it conflicts with the live CLI, trust `paperseek --help`.

## Entrypoints

```bash
paperseek --help
paperseek search "QUESTION" [options]
paperseek "QUESTION" [options]
paperseek doctor [--source SOURCE] [--json]
paperseek smoke [--source SOURCE] [--query QUERY] [--limit N] [--json]
paperseek sources [--json]
paperseek config <path|keys|list|set|unset|import-env>
paperseek-web
python skills/paperseek/scripts/paperseek.py --help
```

`paperseek "QUESTION"` is legacy-compatible and equivalent to `paperseek search "QUESTION"` for search tasks.

The bundled Skill script is a package launcher. It delegates to the full `paperseek` Python package and must not be treated as a separate implementation.

## Search Command

```bash
paperseek search "QUESTION" \
  --source openalex \
  --min 5 \
  --max 50 \
  --iterations 5 \
  --output json
```

Common flags:

| Flag | Meaning |
| --- | --- |
| `--source openalex|crossref|wos` | Literature source. Default is OpenAlex. |
| `--field FIELD` | Optional discipline or field hint. |
| `--min N` / `--max N` | Target result range. |
| `--iterations N` | Maximum query broaden/narrow cycles. |
| `--no-expand-citations` | Disable OpenAlex citation expansion. |
| `--fetch-abstracts` | Try DOI-based external abstract enrichment for WoS. |
| `--output json` or `--json` | Machine-readable output. |

LLM flags:

```bash
--llm-provider deepseek
--llm-api-type openai_chat
--llm-model deepseek-v4-flash
--llm-base-url https://api.deepseek.com
--llm-key YOUR_KEY
```

Source flags:

```bash
--openalex-key YOUR_KEY
--openalex-email you@example.org
--crossref-email you@example.org
--wos-key YOUR_KEY
--db WOS
```

## JSON Output

Top-level fields:

- `question`
- `source`
- `query`
- `database`
- `field`
- `total_results`
- `iterations`
- `history`
- `ranked`

Each `ranked` item keeps legacy UI fields and stable normalized fields.

Stable fields:

- `rank`
- `id`
- `source`
- `title`
- `authors`
- `authors_text`
- `year`
- `venue`
- `publication_type`
- `doi`
- `url`
- `pdf_url`
- `abstract`
- `keywords`
- `keywords_text`
- `citation_count`
- `relevance_score`
- `relevance_reason`
- `source_raw_id`

Legacy-compatible fields:

- `score`
- `provider`
- `uid`
- `publish_year`
- `document_types`
- `citations`
- `reasoning`
- `links`

Prefer stable fields for new agent logic.

## Environment Variables

Common variables:

- `DATA_SOURCE`
- `LLM_PROVIDER`
- `LLM_API_TYPE`
- `LLM_MODEL`
- `LLM_BASE_URL`
- `LLM_API_KEY`
- `OPENALEX_API_KEY`
- `OPENALEX_EMAIL`
- `CROSSREF_EMAIL`
- `WOS_API_KEY`
- `WOS_DB`
- `TARGET_MIN`
- `TARGET_MAX`
- `MAX_ITERATIONS`
- `EXPAND_CITATIONS`

Do not echo real secret values. Use `paperseek config list` for masked status.

## Diagnostics Contract

`paperseek doctor --json` returns:

- `ok`
- `status`
- `checks`
- `sources`
- `summary`

`paperseek smoke --source SOURCE --query QUERY --json` returns:

- `ok`
- `source`
- `status`
- `query`
- `total`
- `returned`
- `elapsed_ms`
- `sample_titles`
- `message` and `body` on failure

Use `doctor` before consuming live quota. Use `smoke` when a real source/network check is needed.
