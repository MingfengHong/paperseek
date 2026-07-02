<p align="center">
  <img src="docs/assets/paperseek_logo_with_text.png" alt="PaperSeek" width="560">
</p>

<p align="center">
  <strong>AI-powered literature search and discovery at research speed.</strong>
</p>

<p align="center">
  Describe a research question once. PaperSeek generates database queries, calibrates result counts, expands citation links, ranks candidate papers, and exports a reviewable paper list.
  <br>
  An open-source literature-search workflow for topic exploration, reviews, interdisciplinary discovery, and daily paper tracking.
</p>

<p align="center">
  <a href="https://www.paperseek.xyz/">Online</a>
  ·
  <a href="https://docs.paperseek.xyz/">Docs</a>
  ·
  <a href="https://modelscope.cn/studios/HongMingfeng/PaperSeek">ModelScope Studio</a>
  ·
  <a href="https://modelscope.cn/learn/434408">Community Article</a>
  ·
  <a href="https://modelscope.cn/skills/HongMingfeng/paperseek">Skill</a>
  ·
  <a href="#mcp-server">MCP</a>
</p>

<p align="center">
  <a href="https://www.python.org/"><img alt="Python" src="https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white"></a>
  <a href="https://pypi.org/project/paperseek/"><img alt="PyPI" src="https://img.shields.io/pypi/v/paperseek?color=3775A9&label=PyPI"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/License-Apache%202.0-blue.svg"></a>
  <a href="https://github.com/MingfengHong/paperseek/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/MingfengHong/paperseek/actions/workflows/ci.yml/badge.svg"></a>
  <a href="#project-status"><img alt="Status" src="https://img.shields.io/badge/status-alpha-orange"></a>
  <a href="https://modelscope.cn/studios/HongMingfeng/PaperSeek"><img alt="ModelScope visits" src="https://img.shields.io/badge/ModelScope%20visits-2.6k-624AFF?logo=modelscope&logoColor=white"></a>
</p>

<p align="center">
  <img src="docs/assets/paperseek-banner.png" alt="PaperSeek banner">
</p>

<p align="center">
  <strong>Language:</strong>
  <a href="README.md">简体中文</a>
  ·
  English
</p>

## Release Notes

### v0.2.0 - More Sources and Multi-Lane Retrieval

- Added arXiv, Semantic Scholar, PubMed, computer science top-conference search, and Crossref.
- The search loop now uses source-aware query generation, intent analysis, iterative top-result feedback, and lightweight multi-lane pre-ranking.
- Added lightweight multi-lane pre-ranking: before LLM scoring, PaperSeek combines relevance, impact/citation, recency, and local-quality signals according to each source's capabilities, then fuses candidates with RRF, BM25/term coverage, and local hashing embeddings; OpenAI-compatible embedding/reranker endpoints remain optional.
- Updated the hosted online account system. PaperSeek now uses email registration and sign-in by default, supports GitHub and ModelScope OAuth, and provides signed-in users with up to 20 successful free searches per day.

### v0.1.1 - Language, History, and Discipline Filters

- The Web UI supports `EN` / `中文` language switching, with the selected language saved in the current browser. See [#10](https://github.com/MingfengHong/paperseek/issues/10).
- Added local history persistence for search runs, log events, generated queries, and results, making it easier to revisit runs and laying groundwork for future stage-level resume support. See [#2](https://github.com/MingfengHong/paperseek/issues/2).
- Improved CSV and log export filenames by using the research-question theme and local timestamp for easier identification. See [#3](https://github.com/MingfengHong/paperseek/issues/3).
- Added OpenAlex Field discipline filtering and passed the selected fields into citation expansion so the candidate pool stays closer to the selected domain.

## Why PaperSeek

Literature search depends on knowing whether a query is complete and accurate when synonyms, disciplinary boundaries, and database-specific query rules all collide. PaperSeek turns a research intent into an executable, observable, and revisitable search workflow.

PaperSeek focuses on first-pass paper discovery and metadata organization, helping researchers turn search steps, candidate pools, and ranking reasons into reviewable data.

## What PaperSeek Does

- **Understands research questions**: generate source-specific queries for OpenAlex, arXiv, Semantic Scholar, PubMed, computer science top conferences, Crossref, or WoS Starter from Chinese or English input.
- **Calibrates search strings**: broaden or narrow queries according to target result counts. The default starts with 5 refinement rounds, then uses a limited adaptive extension when the pool is still empty, too small, or far above the pre-ranking safety pool.
- **Builds structured candidate sets**: normalize title, authors, venue, year, DOI, abstract, citation count, keywords, and links.
- **Ranks with reasons**: ask an LLM to score candidates and explain each score briefly.
- **Expands citation networks**: add references and citing works from high-matching OpenAlex records, then inspect them in Citation Map.
- **Limits by source-native filters**: choose the data source under the research question, then use OpenAlex Fields, WoS Categories, or arXiv categories where native filtering is reliable; other sources use a field/context hint to guide query generation.
- **Keeps the process reviewable**: inspect workflow stages, ranked results, citation maps, local history, and CSV exports in the Web UI.

## Choose Your Path

- **Hosted online edition**: use [paperseek.xyz](https://www.paperseek.xyz/) with Quick Start, ModelScope Service, or Use your own API; see the [hosted demo guide](docs/online-demo.md).
- **Self-hosted open-source edition**: install from PyPI or source, or run with Docker/VPS for longer searches, citation expansion, and heavier request volume.
- **ModelScope Studio**: use the public [PaperSeek Studio](https://modelscope.cn/studios/HongMingfeng/PaperSeek) or deploy your own Docker Studio from the guide.
- **Agent Skill**: copy `skills/paperseek/` into a skill-aware agent platform; the Skill includes a lightweight runtime for core search without installing the full package.
- **MCP Server**: install `paperseek[mcp]` and run `paperseek-mcp` to expose literature search, diagnostics, and history as MCP tools for MCP-compatible AI agents.

Full Chinese user manual: [PaperSeek User Manual](docs/user-manual.md); deployment guide: [Docker, Vercel, and ModelScope deployment](docs/deployment.md).

## Quick Start

Install the stable release from PyPI:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install paperseek
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install paperseek
```

You can also clone the repository and install from source when you want to inspect or edit the code:

```bash
git clone https://github.com/MingfengHong/paperseek.git
cd paperseek
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Windows PowerShell:

```powershell
git clone https://github.com/MingfengHong/paperseek.git
cd paperseek
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Start the Web UI:

```bash
paperseek-web
```

Open:

```text
http://127.0.0.1:8765/
```

You can also run a search directly from the CLI:

```bash
paperseek "open innovation and digital platforms" --source openalex
```

## Deployment

Docker is the recommended path for the full Web UI:

```bash
docker compose up --build
```

Open:

```text
http://127.0.0.1:8765/
```

Vercel can host quick demos and lightweight Web UI deployments:

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FMingfengHong%2Fpaperseek)

ModelScope Studio can also deploy PaperSeek as a Docker Studio. Use this button to fork the community Studio and create your own copy:

<a href="https://modelscope.cn/studios/fork?target=HongMingfeng/PaperSeek"><img src="docs/assets/deploy-modelscope.svg" alt="Deploy to ModelScope" height="32"></a>

For long searches, citation expansion, and heavy repeated use, prefer Docker or a VPS. See the [deployment guide](docs/deployment.md) for details.

## Minimal Configuration

PaperSeek needs at least one LLM provider. OpenAlex is the default data source. Anonymous OpenAlex access is enough for quick tests, but a free API key is recommended for more stable use.

With the default OpenAI provider, only the LLM key is required:

```bash
export LLM_API_KEY=your-llm-api-key
paperseek-web
```

Switching to DeepSeek:

```bash
export LLM_PROVIDER=deepseek
export LLM_API_TYPE=openai_chat
export LLM_MODEL=deepseek-v4-flash
export LLM_BASE_URL=https://api.deepseek.com
export LLM_API_KEY=your-llm-api-key
paperseek-web
```

CSTCloud example:

```bash
export LLM_PROVIDER=cstcloud
export LLM_API_TYPE=openai_chat
export LLM_MODEL=deepseek-v4-flash
export LLM_BASE_URL=https://uni-api.cstcloud.cn/v1
export LLM_API_KEY=your-cstcloud-api-key
paperseek-web
```

ModelScope API-Inference example:

```bash
export LLM_PROVIDER=modelscope
export LLM_API_TYPE=openai_chat
export LLM_MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507
export LLM_BASE_URL=https://api-inference.modelscope.cn/v1
export LLM_API_KEY=your-modelscope-token
paperseek-web
```

Windows PowerShell:

```powershell
$env:LLM_API_KEY = "your-llm-api-key"
paperseek-web
```

Local Ollama does not require an LLM API key:

```bash
export LLM_PROVIDER=ollama
export LLM_API_TYPE=openai_chat
export LLM_MODEL=qwen3:8b
export LLM_BASE_URL=http://127.0.0.1:11434/v1
paperseek-web
```

The repository includes `.env.example`. Copy it to `.env`, fill `LLM_API_KEY` first, and leave advanced variables commented unless you need them. Never commit real API keys. The CLI and Web backend automatically load `.env` from the current directory or project root; existing system environment variables take precedence.

## Web UI

The Web UI has four main workspaces:

| View | Purpose |
| --- | --- |
| Search | Enter the research question, choose Discipline Fields, configure data source, LLM, iterations, and target result range; watch workflow stages and system logs. |
| Results | Review ranked papers, search, filter, sort, select, and export paper CSV. |
| Citation Map | Explore OpenAlex citation expansion as a directed graph. |
| History | Review locally saved runs, final queries, ranked records, and run events. |

![PaperSeek web interface](docs/assets/paperseek-web.png)

If API keys are already configured through system environment variables or `.env`, the Web UI shows that the environment is configured without sending secret values to the browser. API keys, base URLs, and run parameters entered in the Web UI are used only for the current browser session and are not written to local config files by PaperSeek. Local history saves run summaries, queries, events, and results, but never raw API keys.

CSV files exported from Results use the research-question theme and local date in the filename.

## CLI Usage

Basic search:

```bash
paperseek "responsible AI governance in public sector" --source openalex
```

Explicit subcommand:

```bash
paperseek search "digital platforms and open innovation" --source openalex
```

JSON output:

```bash
paperseek search "open innovation" --source openalex --output json
```

Common options:

```bash
paperseek search "your research question" \
  --source openalex \
  --field management \
  --discipline "Computer Science" \
  --min 5 \
  --max 50 \
  --iterations 5 \
  --llm-provider deepseek \
  --llm-api-type openai_chat \
  --llm-model deepseek-v4-flash \
  --llm-base-url https://api.deepseek.com \
  --llm-key your-llm-api-key
```

Run diagnostics:

```bash
paperseek doctor
paperseek doctor --source openalex --json
```

Run a minimal real data-source request:

```bash
paperseek smoke --source openalex --query "machine learning"
paperseek smoke --source crossref --query "open innovation" --json
```

List source capabilities:

```bash
paperseek sources
paperseek sources --json
```

Review local history:

```bash
paperseek history list
paperseek history show <RUN_ID> --json
paperseek history path
```

Manage user-level CLI config:

```bash
paperseek config path
paperseek config set LLM_API_KEY your-llm-api-key
paperseek config list
paperseek config unset LLM_API_KEY
```

Environment variables override user-level config. `paperseek config list` masks secret values.

Source filters accept values supported by the selected source. For OpenAlex, use Field IDs, labels, or `https://openalex.org/fields/<id>` URLs. For WoS, use Web of Science Categories. For arXiv, use arXiv categories such as `cs.IR` or `cs.LG`. Pass multiple filters by repeating `--discipline` / `--discipline-field`, or separate environment values with semicolons:

```bash
export DISCIPLINE_FIELDS="17;14"
paperseek search "open innovation and digital platforms" --source openalex
```

`--field` / `SEARCH_FIELD` is a free-text field/context hint that mainly guides LLM query generation. `--discipline` / `DISCIPLINE_FIELDS` is a structured source filter only for sources with reliable native filtering: OpenAlex applies `primary_topic.field.id`, and arXiv appends `cat:`. WoS Starter currently rejects `WC=`, so selected Web of Science Categories are used only as context for building `TS` / `TI` / `SO` queries. Semantic Scholar, PubMed, Crossref, and computer science top-conference search also use field/context hints instead of hard filtering.

## Data Sources

| Source | Default status | API key | Best for | Notes |
| --- | --- | --- | --- | --- |
| OpenAlex | Default | Recommended | Precise search, abstracts, citation counts, citation expansion, citation maps | Open scholarly metadata source for broad discovery and citation exploration. |
| arXiv | Supported | Not required | Preprints, computer science, physics, mathematics, statistics, and adjacent quantitative fields | Uses the public arXiv Atom API and returns abstracts, categories, and PDF links. |
| Semantic Scholar | Supported | Optional | Broad scholarly graph search, citation counts, and open PDF clues | Anonymous access is useful for light tests; an API key improves rate limits. |
| PubMed | Supported | Optional | Medicine, biomedical, and life-science literature | Uses NCBI E-utilities; set email/tool metadata for responsible usage. |
| Computer science top conferences | Supported | Not required | Top CS conference papers from ICLR, ICML, NeurIPS, AAAI, and NDSS | Searches computer science top-conference records and needs no source key. |
| Crossref | Supported | Usually not required | DOI checks, publication metadata, journal and publisher validation | DOI and metadata registry; useful for metadata verification and DOI completion. |
| Web of Science Starter | Adapter retained | Required | Users with approved Clarivate API access | Commercial database API; availability and returned fields depend on subscription and institutional entitlement. |

## LLM Providers

PaperSeek supports two mainstream API protocol families: OpenAI-style APIs and Anthropic Messages API. Provider selects service defaults; API Type selects request format.

| Provider | Default API Type | Default model |
| --- | --- | --- |
| OpenAI | `openai_responses` | `gpt-5.4-mini` |
| Anthropic | `anthropic_messages` | `claude-sonnet-4-6` |
| Google Gemini | `openai_chat` | `gemini-3.5-flash` |
| DeepSeek | `openai_chat` | `deepseek-v4-flash` |
| CSTCloud | `openai_chat` | `deepseek-v4-flash` |
| DashScope | `openai_chat` | `qwen3.6-plus` |
| Kimi Moonshot | `openai_chat` | `kimi-k2.6` |
| Zhipu AI GLM | `openai_chat` | `glm-5.1` |
| SiliconFlow | `openai_chat` | `deepseek-ai/DeepSeek-V4-Flash` |
| OpenRouter | `openai_chat` | `openai/gpt-5.4-mini` |
| Volcengine Ark | `openai_chat` | `doubao-seed-2-0-mini-260428` |
| Tencent Hunyuan | `openai_chat` | `hunyuan-turbos-latest` |
| Baidu Qianfan | `openai_chat` | `ernie-5.0` |
| ModelScope | `openai_chat` | `Qwen/Qwen3-235B-A22B-Instruct-2507` |
| Ollama | `openai_chat` | `qwen3:8b` |
| Custom | `openai_chat` | Empty; fill in your own model |

Default models initialize forms and examples. Actual availability depends on provider accounts, regions, billing, and compatibility layers.

## Embedding Providers

Embedding is used in the lightweight multi-lane pre-ranking step before LLM scoring. The community edition defaults to `local`, which means pure-Python hashing, BM25, and RRF with no external service. Choose an OpenAI-compatible embedding service only when you need external embedding.

| Provider | Default model | Default Base URL |
| --- | --- | --- |
| Local Python | Empty | Empty |
| CSTCloud | `qwen3-embedding:8b,bge-large-zh:latest` | `https://uni-api.cstcloud.cn/v1` |
| OpenAI | `text-embedding-3-large` | `https://api.openai.com/v1` |
| Alibaba Cloud Bailian / DashScope | `text-embedding-v4` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| SiliconFlow | `BAAI/bge-large-zh-v1.5` | `https://api.siliconflow.cn/v1` |
| Zhipu AI GLM | `embedding-3` | `https://open.bigmodel.cn/api/paas/v4` |
| Volcano Ark | Empty | `https://ark.cn-beijing.volces.com/api/v3` |
| ModelScope API-Inference | `Qwen/Qwen3-Embedding-8B,Qwen/Qwen3-Embedding-4B` | `https://api-inference.modelscope.cn/v1` |
| Custom | Empty | Empty |

If `RETRIEVAL_EMBEDDING_API_KEY` is empty, PaperSeek reuses `LLM_API_KEY`. If no external embedding is configured or the external call fails, PaperSeek falls back to local pre-ranking.

## Rerank Providers

Rerank is an optional external step after RRF fusion. It is off by default. The community edition does not need an external reranker unless you explicitly configure provider, model, and a usable API key.

| Provider | Default model | Default Base URL |
| --- | --- | --- |
| Off | Empty | Empty |
| CSTCloud | `qwen3-reranker:8b` | `https://uni-api.cstcloud.cn/v1` |
| SiliconFlow | `BAAI/bge-reranker-v2-m3` | `https://api.siliconflow.cn/v1` |
| Custom | Empty | Empty |

If `RETRIEVAL_RERANKER_API_KEY` is empty, PaperSeek reuses `LLM_API_KEY`. If the external reranker is unavailable, PaperSeek keeps the local RRF order and continues.
ModelScope API-Inference can be used for LLM and Qwen embedding, but it is not listed as a Rerank provider.

> CSTCloud LLM, Embedding, and Rerank endpoints are accessed through OpenAI-compatible APIs with the same Base URL: `https://uni-api.cstcloud.cn/v1`. To get a key, open [CSTCloud API Keys](https://uni-api.cstcloud.cn/api_keys), sign in with CSTCloud unified authentication, and submit the requested application information. Chinese Academy of Sciences intramural users can sign in with a CSTCloud Pass, usually their institutional email account and password. See the [CSTCloud LLM API manual](https://uni-api.cstcloud.cn/doc/llm/) for Chats, Embeddings, and Rerank endpoint details.

## Workflow

A search usually has four stages:

1. **Query Generation**: the LLM creates an initial query from the research question, optional field/context hint, and source-specific filters.
2. **Source Search**: PaperSeek requests the selected source (OpenAlex, arXiv, Semantic Scholar, PubMed, computer science top conferences, Crossref, or WoS Starter) and logs HTTP status and hit counts.
3. **Query Refinement**: if the hit count is too low or too high, the LLM adjusts the query and continues.
4. **Ranking & Results**: the candidate pool is scored by the LLM, and the top records are returned.

When OpenAlex citation expansion is enabled, PaperSeek selects up to 30 seed papers across relevance, impact, and recency lanes. High-relevance seeds expand both references and citing works; highly cited seeds focus on references; recent seeds focus on citing works. The expanded records are merged into the same candidate pool before pre-ranking and LLM scoring.

Large candidate pools are ranked in concurrent LLM batches. The default batch size is `8` and default concurrency is `32`; above 32 candidates, PaperSeek adapts the batch size to keep the total batch count near the concurrency level. If one or more ranking batches fail, PaperSeek retries those batches with lower concurrency in the `32 -> 16 -> 8 -> 4` sequence. If the endpoint still fails at concurrency `4`, only the failed batch falls back to zero-score source order instead of failing the whole search.

Before LLM scoring, PaperSeek now runs lightweight multi-lane pre-ranking across the selected source's supported signals: relevance, impact/citation when available, recency, and local quality for the computer science top-conference index. It deduplicates candidates, fuses retrieval ranks with RRF, and adds pure-Python hashing cosine plus BM25/term coverage. The default fused pool limit is `3000`; community installs use the local pure-Python embedding path unless you explicitly configure an OpenAI-compatible embedding endpoint. The Web UI advanced settings include embedding provider choices for Local Python, CSTCloud, OpenAI, Alibaba Cloud Bailian, SiliconFlow, Zhipu AI, Volcano Ark, ModelScope, and Custom endpoints. ModelScope API-Inference uses only `Qwen/Qwen3-Embedding-8B` and `Qwen/Qwen3-Embedding-4B` for embedding. Optional external embedding/reranking can use models such as `qwen3-embedding:8b`, `bge-large-zh:latest`, or `qwen3-reranker:8b`; comma-separated model lists are tried in order and failures fall back to the local RRF order.

`TARGET_MAX` guides query refinement; it is not a hard display cap. LLM scoring receives at most `RANKING_CANDIDATE_LIMIT` candidates, default `256`. Results show all candidates when the scored pool is under 50, otherwise at least the top 50; if more than 50 candidates score `5` or above, all of those high-scoring candidates are shown.

## Citation Map

Citation Map uses arrows for citation direction:

```text
A -> B means A cites B
```

Graph nodes come from final results and OpenAlex citation expansion records. You can drag nodes, zoom and pan the canvas, and inspect node details. The citation map is useful for finding classic works, adjacent topics, and recent follow-up papers that keyword search may miss.

## Environment Variables

Most parameters already have code defaults. After copying `.env.example`, a normal setup usually only needs a model API key. Keep advanced variables commented unless you intentionally want to override defaults.

### Required

| Variable | Default | Description |
| --- | --- | --- |
| `LLM_API_KEY` | empty | LLM API key. Leave empty when using Ollama. |
| `WOS_API_KEY` | empty | Required only when `DATA_SOURCE=wos`. |

### Common Optional Settings

| Variable | Default | Description |
| --- | --- | --- |
| `LLM_PROVIDER` | `openai` | LLM provider, such as `openai`, `deepseek`, `cstcloud`, `anthropic`, `modelscope`, or `ollama`. |
| `LLM_API_TYPE` | provider default | `openai_responses`, `openai_chat`, or `anthropic_messages`. |
| `LLM_MODEL` | provider default | Model name. |
| `LLM_BASE_URL` | provider default | API base URL. |
| `DATA_SOURCE` | `openalex` | `openalex`, `arxiv`, `semanticscholar`, `pubmed`, `paperhub`, `crossref`, or `wos`. |
| `OPENALEX_API_KEY` | empty | OpenAlex API key, recommended for steadier requests. |
| `OPENALEX_EMAIL` | empty | OpenAlex contact email. |
| `SEMANTIC_SCHOLAR_API_KEY` | empty | Semantic Scholar API key, optional; anonymous access is best for light tests. |
| `PUBMED_EMAIL` / `PUBMED_TOOL` | empty / `paperseek` | PubMed / NCBI responsible-use metadata. |
| `PUBMED_API_KEY` | empty | NCBI API key, optional; increases PubMed E-utilities request limits. |
| `CROSSREF_EMAIL` | empty | Crossref polite pool email. |

### Advanced Settings

| Variable | Default | Description |
| --- | --- | --- |
| `SEARCH_FIELD` | empty | Free-text discipline or field hint. |
| `DISCIPLINE_FIELDS` | empty | Source-native filter values for OpenAlex Fields, WoS Categories, or arXiv categories; use semicolons for multiple values. Other sources use `SEARCH_FIELD` as a text hint. |
| `TARGET_MIN` / `TARGET_MAX` | `5` / `50` | Target result count range. |
| `MAX_ITERATIONS` | `5` | Maximum query refinement iterations. |
| `EXPAND_CITATIONS` | `true` | Enable OpenAlex citation expansion. |
| `FETCH_ABSTRACTS` | `false` | Try external DOI metadata for abstracts. |
| `CITATION_SEED_COUNT` / `CITATION_PER_SEED` / `CITATION_MAX_RECORDS` | `30` / `4` / `160` | Citation expansion size controls. |
| `CITATION_DEPTH` | `2` | OpenAlex citation traversal depth. |
| `RANKING_BATCH_SIZE` / `RANKING_CONCURRENCY` | `8` / `32` | LLM ranking batch size and concurrency. |
| `LLM_MAX_TOKENS` / `LLM_TIMEOUT_SECONDS` | `2048` / `180` | LLM output length and per-request timeout. |
| `RETRIEVAL_POOL_MAX` / `RETRIEVAL_POOL_MIN` | `3000` / `5` | Fused candidate pool range before LLM ranking. |
| `RETRIEVAL_LANE_LIMIT` / `RETRIEVAL_RRF_K` | `1000` / `60` | Retrieval lane cap and RRF fusion constant. |
| `RETRIEVAL_EMBEDDING_PROVIDER` | `local` | Community edition uses local pure-Python pre-ranking by default; set an OpenAI-compatible embedding provider if needed. |
| `RETRIEVAL_EMBEDDING_MODEL` | `qwen3-embedding:8b,bge-large-zh:latest` | External embedding model list. |
| `RETRIEVAL_RERANKER_PROVIDER` / `RETRIEVAL_RERANKER_MODEL` | empty / `qwen3-reranker:8b` | Optional external reranker after RRF. |
| `RETRIEVAL_CROSSREF_ENRICHMENT` | `false` | Optional Crossref DOI metadata enrichment. |
| `PAPERSEEK_HISTORY_ENABLED` | `true` | Enable local history. |
| `PAPERSEEK_TIMEZONE` | `Asia/Shanghai` | CLI and backend fallback timezone; the Web UI prefers the browser timezone. |
| `PAPERSEEK_DATA_DIR` / `PAPERSEEK_HISTORY_DB` | `~/.paperseek` / `~/.paperseek/paperseek.db` | Local data directory and history database path. |

## Getting API Access

### OpenAlex

OpenAlex supports anonymous access, but a free API key is recommended:

1. Open [OpenAlex](https://openalex.org/) and create an account.
2. Visit [OpenAlex API settings](https://openalex.org/settings/api).
3. Copy the API key.
4. Fill `OpenAlex API Key` in the Web UI or set `OPENALEX_API_KEY`.

### Semantic Scholar

Semantic Scholar supports anonymous access. For sustained use or higher request volume, request an API key:

1. Open the [Semantic Scholar API](https://www.semanticscholar.org/product/api) page.
2. Follow the API key request flow and provide the requested name, email, and use-case information.
3. Wait for Semantic Scholar to send or enable the API key.
4. Fill `Semantic Scholar API Key` in the Web UI or set `SEMANTIC_SCHOLAR_API_KEY`.

### PubMed / NCBI

PubMed uses NCBI E-utilities. Set a contact email and tool name for responsible usage. If you need higher request limits, generate an API key from your NCBI account:

1. Open [NCBI](https://www.ncbi.nlm.nih.gov/) and create or sign in to your account.
2. Open account settings and find the API Key management area.
3. Create an API key and copy it.
4. Fill `PubMed API Key` in the Web UI or set `PUBMED_API_KEY`.
5. Also set `PUBMED_EMAIL` and `PUBMED_TOOL`, for example `paperseek`.

### Crossref

Crossref REST API usually does not require an API key. Set a contact email to enter the polite pool:

```bash
export CROSSREF_EMAIL=you@example.org
```

For higher quotas, priority support, or production SLA, consider Crossref Metadata Plus. PaperSeek uses the public or polite REST API path.

### arXiv and computer science top conferences

- arXiv does not require an API key and is best for preprints and arXiv-covered disciplines.
- Computer science top-conference search does not require an API key.

### Web of Science Starter API

WoS Starter requires approval in Clarivate Developer Portal and usually fits users with institutional Web of Science access:

1. Open the [Clarivate Developer Portal signup page](https://developer.clarivate.com/signup) and register.
2. Prefer an institutional email and, if possible, use the same identity as your Web of Science account.
3. Go to [Applications](https://developer.clarivate.com/applications) and click `Register Application`.
4. Fill application metadata:
   - `Application ID` should use digits, lowercase letters, `-`, or `_`.
   - `Application Name` can be your institution or project name.
   - `Application Description` can mention Web of Science API search.
   - Keep `Client Type` as `Public: Single Page Application`.
   - Do not enable OAuth2.0 flows.
5. Open [Web of Science Starter API](https://developer.clarivate.com/apis/wos-starter).
6. Select the registered application and click `Subscribe`.
7. Choose the plan that matches your identity and institutional entitlement.
8. Wait for approval after `Subscription approval is pending`.
9. After receiving the API key, fill `WoS API Key` in the Web UI or set `WOS_API_KEY`.

WoS Starter limits, fields, and availability depend on plan and institutional entitlement. For HTTP 401, check HTTPS and the key. For Clarivate's non-standard HTTP 512, check Clarivate service status, subscription approval, and query compatibility.

## Python API and Core

The community package includes the reusable `paperseek_core` module directly, so users do not need to install a separate `paperseek-core` repository dependency. Regular users and downstream code should import the stable public entry point from `paperseek`:

```python
from paperseek import PaperSeekAgent
```

`LiteratureSearchAgent` and `WosSearchAgent` remain as backward-compatible aliases. New code should use `PaperSeekAgent`.

## Agent Skill

The repository includes an optional PaperSeek Skill:

```text
skills/paperseek/
```

It teaches skill-aware AI agents how to call PaperSeek, choose data sources, run diagnostics, parse JSON results, and respect citation-map boundaries. The Skill uses progressive disclosure: `SKILL.md` stays short, while detailed command contracts live in `references/`.

This Skill is **not installed automatically** with the Python package. If you need it, copy or link `skills/paperseek/` into the target agent platform's skill directory.

The launcher and standalone runtime:

```text
skills/paperseek/scripts/paperseek.py
skills/paperseek/scripts/paperseek_skill_runtime.py
```

For standalone Skill distribution, copy `skills/paperseek/`. `paperseek.py` first tries the full PaperSeek package; if the package is unavailable, it falls back to `paperseek_skill_runtime.py`, a Python standard-library runtime that can run core OpenAlex, arXiv, Semantic Scholar, PubMed, computer science top-conference, Crossref, and key-backed WoS Starter literature search without installing the package. The full package is still required for the Web UI, citation maps, and complete history management.

## MCP Server

PaperSeek provides an optional MCP (Model Context Protocol) server that exposes literature search, configuration diagnostics, source connectivity tests, and search history as MCP tools for MCP-compatible AI agents.

Install the MCP optional dependency (requires Python 3.10+):

```bash
python -m pip install "paperseek[mcp]"
```

Start the MCP server (stdio transport):

```bash
paperseek-mcp
```

Configuration is identical to the CLI and Web UI — set LLM and data source parameters via environment variables or `.env`. API keys are never exposed to the LLM; they are held only by the MCP server process.

Available MCP tools:

| Tool | Purpose |
| --- | --- |
| `search_papers` | Search literature from a research question with the full LLM workflow |
| `check_config` | Check whether PaperSeek configuration (source, LLM, API keys) is ready |
| `smoke_test` | Send a minimal live request to test source connectivity |
| `list_sources` | List all supported data sources and their capabilities |
| `list_history` | List locally saved search runs |
| `get_history_run` | View full details of a specific search run |

Configure in MCP-compatible clients such as Claude Desktop:

```json
{
  "mcpServers": {
    "paperseek": {
      "command": "paperseek-mcp",
      "env": {
        "LLM_API_KEY": "your-llm-api-key"
      }
    }
  }
}
```

You can also start the server with `python -m paperseek.mcp_server`. The MCP server reuses the same `PaperSeekAgent` core logic as the CLI, and search results are automatically saved to local history.

## Project Status

PaperSeek is currently alpha software. CLI, Web UI, OpenAlex, arXiv, Semantic Scholar, PubMed, computer science top-conference search, Crossref, citation expansion, CSV export, the optional Skill, and MCP Server are ready for daily literature search and candidate-set organization.

Contributions are welcome:

- New data-source adapters.
- More robust query-generation and ranking prompts.
- Better citation graph interactions.
- Tests for Web API, CLI, provider parsing, and export behavior.
- Documentation, examples, and error diagnostics.

Read [CONTRIBUTING.md](CONTRIBUTING.md) before contributing. Report security issues according to [SECURITY.md](SECURITY.md).

## Acknowledgements

PaperSeek takes inspiration from the following open-source projects:

- [dr-dumpling/paper-search-cli](https://github.com/dr-dumpling/paper-search-cli/): CLI usage patterns and literature-search workflow design.
- [666ghj/MiroFish](https://github.com/666ghj/MiroFish): split-pane Web UI layout and workflow presentation style.
- [clarivate/wosstarter_python_client](https://github.com/clarivate/wosstarter_python_client): Web of Science Starter API client usage.
- [Yupu-Wang/paper-hub](https://github.com/Yupu-Wang/paper-hub): integrated with the author's permission to provide computer science top-conference search support.
- [Lloyd-Jahn/openclaw-paper-search](https://github.com/Lloyd-Jahn/openclaw-paper-search): organization of paper-search tooling.

## License

PaperSeek is licensed under the [Apache License 2.0](LICENSE).
