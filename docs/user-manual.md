# PaperSeek 用户手册

适用版本：PaperSeek `0.1.x`

PaperSeek 是一个 LLM based Literature Search Agent。它面向研究者、学生、综述写作者和需要把文献候选列表交给 AI 继续处理的用户，提供自然语言检索、自动迭代、Discipline Fields 学科限制、元数据整理、相关性排序、引用扩展、CSV 导出、CLI 和本地 Web UI。

本文档从零开始说明如何安装、配置和使用 PaperSeek。若你只想快速试运行，可以先阅读 [Get started](#get-started)；若要长期使用，建议完整阅读 [Configuration](#configuration)、[Models](#models)、[Data sources](#data-sources)、[Discipline Fields](#discipline-fields)、[CLI](#cli) 和 [Web UI](#web-ui)。

## 目录

- [Get started](#get-started)
- [Install](#install)
- [Core concepts](#core-concepts)
- [Configuration](#configuration)
- [Models](#models)
- [Data sources](#data-sources)
- [Discipline Fields](#discipline-fields)
- [CLI](#cli)
- [Web UI](#web-ui)
- [Deployment](#deployment)
- [Results and exports](#results-and-exports)
- [Citation expansion and map](#citation-expansion-and-map)
- [Python API and core](#python-api-and-core)
- [Agent Skill](#agent-skill)
- [MCP Server](#mcp-server)
- [Diagnostics and troubleshooting](#diagnostics-and-troubleshooting)
- [Security and privacy](#security-and-privacy)
- [Upgrade and maintenance](#upgrade-and-maintenance)
- [FAQ](#faq)

## Get started

### 你需要准备什么

最小运行条件：

- Python `3.8` 或更高版本。
- 可访问互联网，用于请求文献数据源和 LLM API。
- 一个 LLM 服务商的 API Key；如果使用本地 Ollama，可不需要云端 LLM Key。
- 推荐准备 OpenAlex API Key；OpenAlex 可匿名测试，但长期使用建议配置 Key。

默认推荐路径：

- 数据源：OpenAlex。
- LLM API Type：OpenAI Chat Completions 兼容接口，或 OpenAI Responses API / Anthropic Messages API。
- 交互方式：首次使用建议打开 Web UI；批量或 agent 调用建议使用 CLI JSON 输出。

### 5 分钟启动 Web UI

从 PyPI 安装稳定发布版：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install paperseek
```

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install paperseek
```

也可以 clone 仓库从源码安装：

```bash
git clone https://github.com/MingfengHong/paperseek.git
cd paperseek
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Windows PowerShell：

```powershell
git clone https://github.com/MingfengHong/paperseek.git
cd paperseek
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

设置一个 LLM。以 DeepSeek 的 OpenAI Chat Completions 兼容接口为例：

```bash
export LLM_PROVIDER=deepseek
export LLM_API_TYPE=openai_chat
export LLM_MODEL=deepseek-v4-flash
export LLM_BASE_URL=https://api.deepseek.com
export LLM_API_KEY=your-llm-api-key
```

Windows PowerShell：

```powershell
$env:LLM_PROVIDER = "deepseek"
$env:LLM_API_TYPE = "openai_chat"
$env:LLM_MODEL = "deepseek-v4-flash"
$env:LLM_BASE_URL = "https://api.deepseek.com"
$env:LLM_API_KEY = "your-llm-api-key"
```

ModelScope API-Inference 也使用 OpenAI Chat Completions 兼容接口：

```bash
export LLM_PROVIDER=modelscope
export LLM_API_TYPE=openai_chat
export LLM_MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507
export LLM_BASE_URL=https://api-inference.modelscope.cn/v1
export LLM_API_KEY=your-modelscope-token
```

中国科技云大模型 API 也使用 OpenAI Chat Completions 兼容接口：

```bash
export LLM_PROVIDER=cstcloud
export LLM_API_TYPE=openai_chat
export LLM_MODEL=DeepSeek-V4-Flash
export LLM_BASE_URL=https://uni-api.cstcloud.cn/v1
export LLM_API_KEY=your-cstcloud-api-key
```

启动：

```bash
paperseek-web
```

打开：

```text
http://127.0.0.1:8765/
```

在页面左侧填写 Research Question，例如：

```text
open innovation and digital platforms
```

点击 `Run Search`。运行完成后，进入 `Results` 页面查看排序论文，并可导出 CSV。

### 5 分钟启动 CLI

```bash
paperseek search "open innovation and digital platforms" --source openalex
```

输出 JSON，适合保存或交给其他程序处理：

```bash
paperseek search "open innovation and digital platforms" --source openalex --output json
```

运行前检查配置：

```bash
paperseek doctor
```

对数据源发起一个最小真实请求：

```bash
paperseek smoke --source openalex --query "machine learning"
```

## Install

### 系统要求

| 项目 | 要求 |
| --- | --- |
| Python | `>=3.8` |
| 操作系统 | Windows、macOS、Linux 均可运行 |
| 网络 | 需要访问 LLM API 和选定文献数据源 |
| 浏览器 | Web UI 使用本地浏览器打开 `127.0.0.1:8765` |
| Node.js | 仅开发者检查前端 JS 语法时需要；普通用户不需要 |

PaperSeek 的核心依赖包括：

- `requests`
- `pydantic`
- `fastapi`
- `uvicorn`
- `python-dateutil`

### 从 PyPI 安装（推荐）

PaperSeek 已发布到 PyPI，普通用户推荐直接安装稳定发布版：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install paperseek
```

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install paperseek
```

安装后可使用：

```bash
paperseek --help
paperseek-web
```

### 从源码安装

```bash
git clone https://github.com/MingfengHong/paperseek.git
cd paperseek
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Windows PowerShell：

```powershell
git clone https://github.com/MingfengHong/paperseek.git
cd paperseek
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

`-e` 是 editable install。它适合从源码目录运行，更新代码后不需要重新安装包。

### 从 GitHub 安装

如果你希望安装最新 GitHub 代码，但不需要编辑源码，可以直接从 GitHub 安装：

```bash
python -m pip install "git+https://github.com/MingfengHong/paperseek.git"
```

安装后可使用：

```bash
paperseek --help
paperseek-web
```

### 开发者安装

开发者可安装额外测试依赖：

```bash
python -m pip install -e ".[dev]"
```

当前 dev 依赖用于 Web API 测试等开发场景。普通用户不需要安装。

### 验证安装

```bash
paperseek --help
paperseek sources
paperseek doctor
```

如果 `paperseek` 命令不存在，可用 Python 模块方式检查：

```bash
python -m paperseek.cli --help
```

如果模块方式可用但命令不可用，通常是虚拟环境未激活，或 Python scripts 目录未加入 `PATH`。

### 启动 Web UI

默认启动命令：

```bash
paperseek-web
```

等价的模块方式：

```bash
python -m paperseek.web_app
```

默认监听：

```text
127.0.0.1:8765
```

如果端口被占用，当前命令不会自动换端口。你可以关闭占用进程，或在开发环境中直接调用 `uvicorn` 指定端口：

```bash
uvicorn paperseek.web_app:app --host 127.0.0.1 --port 8766
```

### 卸载

```bash
python -m pip uninstall paperseek
```

如果你使用 editable install，卸载只移除环境中的包链接，不删除源码目录。

## Deployment

PaperSeek 支持 Docker、Docker Compose、Vercel 和 ModelScope 创空间部署。完整步骤见 [部署指南](deployment.md)。

### Docker 部署

Docker 是完整 Web UI 的推荐部署方式。它适合：

- 长时间搜索。
- 流式日志。
- OpenAlex 引用扩展。
- 私有服务器或实验室部署。
- 需要稳定运行的团队使用场景。

快速启动：

```bash
cp .env.example .env
docker compose up --build
```

打开：

```text
http://127.0.0.1:8765/
```

后台运行：

```bash
docker compose up -d --build
```

查看日志：

```bash
docker compose logs -f
```

停止：

```bash
docker compose down
```

### Vercel 部署

Vercel 适合快速体验和轻量 Web UI 部署：

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FMingfengHong%2Fpaperseek)

Vercel 运行在 serverless function 模型下。PaperSeek 的 Web UI 可以打开，API 也能工作；但长搜索、引用扩展和多轮 LLM 请求可能触发函数时长限制。需要完整稳定体验时，优先使用 Docker。

Vercel 部署所需文件：

| 文件 | 说明 |
| --- | --- |
| `app.py` | Vercel FastAPI 自动识别入口，暴露 `paperseek.web_app.app`。 |
| `api/index.py` | 兼容 Python 入口，也暴露同一个 FastAPI `app`。 |
| `vercel.json` | 最小 Vercel 项目配置，避免使用 `functions` pattern 触发函数匹配失败。 |
| `requirements.txt` | Python 依赖。 |

部署后可以用：

```bash
curl https://your-project.vercel.app/api/sources
```

确认 API 是否返回数据源列表。

### ModelScope 创空间部署

PaperSeek 社区版支持以 Docker 创空间的方式部署到 ModelScope。你可以通过 fork 链接创建官方 PaperSeek 创空间的副本，也可以手动创建 Docker 创空间后把本仓库代码推送到创空间分配的 Git 仓库。

<a href="https://modelscope.cn/studios/fork?target=HongMingfeng/PaperSeek"><img src="./assets/deploy-modelscope.svg" alt="Deploy to ModelScope" height="32"></a>

社区版已经包含部署所需文件：

| 文件 | 说明 |
| --- | --- |
| `Dockerfile` | 构建并启动 PaperSeek Web UI。 |
| `ms_deploy.json` | 声明 Docker SDK、`7860` 端口和 CPU 资源规格。 |

基本流程是：

1. 点击 [Deploy to ModelScope](https://modelscope.cn/studios/fork?target=HongMingfeng/PaperSeek) fork 官方创空间，或手动创建 Docker 创空间。
2. 如果手动创建创空间，将 PaperSeek 仓库推送到创空间 Git 远程。
3. 在创空间设置中配置 `LLM_PROVIDER`、`LLM_API_TYPE`、`LLM_MODEL`、`LLM_BASE_URL`、`LLM_API_KEY` 等环境变量。
4. 发布或深度重启创空间。

如果没有在服务端配置密钥，用户仍可在 Web UI 里为当前浏览器会话填写自己的 LLM 和数据源 Key。完整命令和注意事项见 [部署指南](deployment.md#modelscope-studio)。

## Core concepts

### Research Question

Research Question 是用户输入的自然语言检索意图。它可以是：

- 一个简短主题：`open innovation and digital platforms`
- 一个中文问题：`查找开放式创新与数字平台治理相关文献`
- 一段研究缺口：`I want papers about how public agencies evaluate responsible AI governance tools`
- 一个更精确的检索目标：`empirical studies on platform ecosystems and complementor innovation`

写 Research Question 时建议：

- 包含核心概念，而不是只写单个宽泛词。
- 可加入研究对象、理论视角、方法或场景。
- 结果太少时，减少限定词。
- 结果太多时，加入领域、对象或方法限制。

### Data Source

Data Source 是论文元数据来源。当前支持：

- OpenAlex
- Crossref
- Web of Science Starter

不同数据源覆盖范围、返回字段和查询能力不同。OpenAlex 是默认源；Crossref 偏 DOI 与出版元数据；WoS Starter 需要 Clarivate API 权限。

### Field Hint and Discipline Fields

`Field Hint` 是自由文本领域提示，例如 `management` 或 `public health`，主要帮助 LLM 生成更贴近领域的检索式。

`Discipline Fields` 是结构化学科限制，基于 OpenAlex Field taxonomy。它可以选择一个或多个学科，并由不同数据源按各自能力处理：OpenAlex 使用原生 field filter，WoS Starter 映射到 `WC=` 类目，Crossref 作为查询上下文。

### LLM Provider, API Type, Model

PaperSeek 将 LLM 配置拆成三个部分：

- `LLM_PROVIDER`：服务商，例如 `openai`、`deepseek`、`cstcloud`、`anthropic`、`modelscope`、`ollama`。
- `LLM_API_TYPE`：接口协议，例如 `openai_chat`、`openai_responses`、`anthropic_messages`。
- `LLM_MODEL`：模型名称，例如 `deepseek-v4-flash`、`gpt-5.4-mini`。

Provider 决定默认模型和 Base URL。API Type 决定请求格式。Model 决定实际调用哪个模型。

### Target range

目标结果数量由两个参数控制：

- `TARGET_MIN` / `--min`
- `TARGET_MAX` / `--max`

默认是 `5-50`。PaperSeek 会根据数据源命中数尝试放宽或收窄查询。

### Iterations

`MAX_ITERATIONS` / `--iterations` 控制查询调整轮数。默认 `5`。每一轮可能包括：

- LLM 生成或调整查询。
- 数据源请求。
- 记录命中数量和 HTTP 状态。
- 判断是否继续调整。

迭代次数越高，越可能找到合适命中范围，但会增加 LLM 和数据源请求次数。

### Candidate pool

候选池由数据源返回的论文构成。如果启用 OpenAlex 引用扩展，候选池还会加入高匹配论文的引用邻居。最终排序面向候选池，而不是只展示某一次数据源返回的原始顺序。

### Ranking

PaperSeek 使用 LLM 对候选论文进行相关性评分。评分用于文献发现阶段的优先级排序，不是论文质量、学术影响或系统综述纳入标准。

排序阶段会按批次调用 LLM。默认批大小为 `8`，默认并发为 `4`；当候选论文超过 32 条时，PaperSeek 会自动放大批大小，让总批次数接近并发数。这样可以降低大候选池排序的等待时间。若某一个排序批次失败，PaperSeek 只会将该批次按数据源顺序以零分回退，不会让整次检索失败。可通过 `RANKING_BATCH_SIZE`、`RANKING_CONCURRENCY` 和 `LLM_TIMEOUT_SECONDS` 调整。

### Citation expansion

OpenAlex 模式支持引用扩展。PaperSeek 会从高匹配论文中选择若干 seed paper，扩展：

- seed paper 引用过的参考文献。
- 引用了 seed paper 的后续论文。

引用扩展有助于发现关键词检索遗漏的经典文献、相邻主题和近期延伸研究。

## Configuration

PaperSeek 支持三种配置方式：

- Web UI 表单配置。
- CLI 参数。
- 环境变量与用户级配置文件。

### 配置优先级

CLI 运行时的优先级：

1. 命令行参数，例如 `--llm-key`、`--source`、`--iterations`。
2. 环境变量，例如 `LLM_API_KEY`、`DATA_SOURCE`。
3. 用户级配置文件，由 `paperseek config set ...` 写入。
4. 内置默认值。

Web UI 运行时：

- 页面表单值优先。
- 表单未填写时，后端会使用环境变量或默认值。
- Web UI 中填写的 API Key、Base URL 和参数只用于本次浏览器会话，不写入用户级配置文件。

### 环境变量

常用环境变量：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DATA_SOURCE` | `openalex` | 数据源：`openalex`、`crossref`、`wos`。 |
| `LLM_PROVIDER` | `openai` | LLM 服务商。 |
| `LLM_API_TYPE` | 由 provider 决定 | `openai_chat`、`openai_responses`、`anthropic_messages`。 |
| `LLM_MODEL` | 由 provider 决定 | 模型名称。 |
| `LLM_BASE_URL` | 由 provider 决定 | LLM API Base URL。 |
| `LLM_API_KEY` | 空 | LLM API Key；Ollama 可不填。 |
| `OPENALEX_API_KEY` | 空 | OpenAlex API Key，推荐填写。 |
| `OPENALEX_EMAIL` | 空 | OpenAlex 联系邮箱。 |
| `CROSSREF_EMAIL` | 空 | Crossref polite pool 邮箱。 |
| `WOS_API_KEY` | 空 | Clarivate Web of Science Starter API Key。 |
| `WOS_DB` | `WOS` | WoS 数据库代码。 |
| `SEARCH_FIELD` | 空 | 学科或领域提示。 |
| `DISCIPLINE_FIELDS` | 空 | OpenAlex Field ID、标签或 URL；多个值建议用分号分隔，并会映射到 OpenAlex / WoS 学科限定。 |
| `TARGET_MIN` | `5` | 目标最少结果数。 |
| `TARGET_MAX` | `50` | 目标最多结果数。 |
| `MAX_ITERATIONS` | `5` | 最大查询调整轮数。 |
| `EXPAND_CITATIONS` | `true` | 是否启用 OpenAlex 引用扩展。 |
| `FETCH_ABSTRACTS` | `false` | 是否尝试 DOI 外部摘要补全。 |
| `CITATION_SEED_COUNT` | `3` | 引用扩展 seed 数量。 |
| `CITATION_PER_SEED` | `4` | 每个 seed 的引用邻居数量。 |
| `CITATION_MAX_RECORDS` | `40` | 引用扩展加入候选池的最大记录数。 |
| `RANKING_BATCH_SIZE` | `8` | LLM 排序批大小；候选数较多时会自适应放大以减少批次数。 |
| `RANKING_CONCURRENCY` | `4` | LLM 排序并发数；单个批次失败只影响该批次，不会使整次检索失败。 |
| `LLM_TIMEOUT_SECONDS` | `180` | 单次 LLM 请求超时秒数，最小 `30`。 |
| `PAPERSEEK_HISTORY_ENABLED` | `true` | 是否启用本地 SQLite 历史记录。 |
| `PAPERSEEK_TIMEZONE` | `Asia/Shanghai` | 本地历史记录时间戳时区；Web UI 会优先使用浏览器检测到的时区，检测失败时默认东八区。 |
| `PAPERSEEK_DATA_DIR` | `~/.paperseek` | 本地数据目录。 |
| `PAPERSEEK_HISTORY_DB` | `~/.paperseek/paperseek.db` | 本地历史数据库路径。 |

布尔变量接受：

- True：`1`、`true`、`yes`
- False：`0`、`false`、`no`

### 使用 `.env.example`

仓库提供 `.env.example`：

```bash
cp .env.example .env
```

`.env` 不会被 Git 跟踪。PaperSeek CLI 和 Web 后端会自动读取当前目录或项目根目录下的 `.env`；已经存在的系统环境变量优先于 `.env`。你还可以选择：

- 手动把 `.env` 中的变量导入 shell。
- 使用 `paperseek config import-env .env` 导入用户级配置，便于脱离源码目录运行。
- 在 Web UI 中手动填写本次会话字段。

### 用户级配置文件

PaperSeek CLI 支持用户级配置文件。默认路径：

```text
~/.config/paperseek/config.json
```

查看路径：

```bash
paperseek config path
```

保存配置：

```bash
paperseek config set LLM_PROVIDER deepseek
paperseek config set LLM_API_TYPE openai_chat
paperseek config set LLM_MODEL deepseek-v4-flash
paperseek config set LLM_BASE_URL https://api.deepseek.com
paperseek config set LLM_API_KEY your-llm-api-key
```

列出配置：

```bash
paperseek config list
```

列出全部支持的配置项：

```bash
paperseek config keys
```

移除配置：

```bash
paperseek config unset LLM_API_KEY
```

从 `.env` 导入：

```bash
paperseek config import-env .env
```

密钥显示会被遮蔽，例如：

```text
LLM_API_KEY: sk-t...1234 [user_config]
```

### 使用自定义配置路径

你可以指定配置文件路径：

```bash
export PAPERSEEK_CONFIG_FILE=/path/to/config.json
```

或指定配置目录：

```bash
export PAPERSEEK_CONFIG_DIR=/path/to/paperseek-config
```

这适合测试、多用户环境或隔离不同项目配置。

### 常见配置方案

DeepSeek：

```bash
export LLM_PROVIDER=deepseek
export LLM_API_TYPE=openai_chat
export LLM_MODEL=deepseek-v4-flash
export LLM_BASE_URL=https://api.deepseek.com
export LLM_API_KEY=your-key
```

中国科技云：

```bash
export LLM_PROVIDER=cstcloud
export LLM_API_TYPE=openai_chat
export LLM_MODEL=DeepSeek-V4-Flash
export LLM_BASE_URL=https://uni-api.cstcloud.cn/v1
export LLM_API_KEY=your-cstcloud-api-key
```

OpenAI Responses API：

```bash
export LLM_PROVIDER=openai
export LLM_API_TYPE=openai_responses
export LLM_MODEL=gpt-5.4-mini
export LLM_BASE_URL=https://api.openai.com/v1
export LLM_API_KEY=your-key
```

Anthropic Messages API：

```bash
export LLM_PROVIDER=anthropic
export LLM_API_TYPE=anthropic_messages
export LLM_MODEL=claude-sonnet-4-6
export LLM_BASE_URL=https://api.anthropic.com
export LLM_API_KEY=your-key
```

ModelScope API-Inference：

```bash
export LLM_PROVIDER=modelscope
export LLM_API_TYPE=openai_chat
export LLM_MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507
export LLM_BASE_URL=https://api-inference.modelscope.cn/v1
export LLM_API_KEY=your-modelscope-token
```

本地 Ollama：

```bash
export LLM_PROVIDER=ollama
export LLM_API_TYPE=openai_chat
export LLM_MODEL=qwen3:8b
export LLM_BASE_URL=http://127.0.0.1:11434/v1
```

OpenAlex：

```bash
export DATA_SOURCE=openalex
export OPENALEX_API_KEY=your-openalex-key
```

Crossref：

```bash
export DATA_SOURCE=crossref
export CROSSREF_EMAIL=you@example.org
```

WoS Starter：

```bash
export DATA_SOURCE=wos
export WOS_API_KEY=your-wos-key
export WOS_DB=WOS
```

## Models

### API Type

PaperSeek 当前支持三种 API Type：

| API Type | 用途 |
| --- | --- |
| `openai_chat` | OpenAI Chat Completions 兼容接口。DeepSeek、中国科技云、DashScope、Moonshot、OpenRouter、Ollama 等通常使用此模式。 |
| `openai_responses` | OpenAI Responses API。OpenAI 官方模型默认使用此模式。 |
| `anthropic_messages` | Anthropic Messages API。Anthropic 官方接口默认使用此模式。 |

### Provider 默认值

Provider 默认模型和 Base URL：

| Provider | 默认 API Type | 默认模型 | 默认 Base URL |
| --- | --- | --- | --- |
| `openai` | `openai_responses` | `gpt-5.4-mini` | `https://api.openai.com/v1` |
| `anthropic` | `anthropic_messages` | `claude-sonnet-4-6` | `https://api.anthropic.com` |
| `google` | `openai_chat` | `gemini-3.5-flash` | `https://generativelanguage.googleapis.com/v1beta/openai` |
| `deepseek` | `openai_chat` | `deepseek-v4-flash` | `https://api.deepseek.com` |
| `cstcloud` | `openai_chat` | `DeepSeek-V4-Flash` | `https://uni-api.cstcloud.cn/v1` |
| `dashscope` | `openai_chat` | `qwen3.6-plus` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `moonshot` | `openai_chat` | `kimi-k2.6` | `https://api.moonshot.ai/v1` |
| `zhipu` | `openai_chat` | `glm-5.1` | `https://open.bigmodel.cn/api/paas/v4` |
| `siliconflow` | `openai_chat` | `deepseek-ai/DeepSeek-V4-Flash` | `https://api.siliconflow.cn/v1` |
| `openrouter` | `openai_chat` | `openai/gpt-5.4-mini` | `https://openrouter.ai/api/v1` |
| `volcengine` | `openai_chat` | `doubao-seed-2-0-mini-260428` | `https://ark.cn-beijing.volces.com/api/v3` |
| `hunyuan` | `openai_chat` | `hunyuan-turbos-latest` | `https://tokenhub.tencentmaas.com/v1` |
| `qianfan` | `openai_chat` | `ernie-5.0` | `https://qianfan.baidubce.com/v2` |
| `modelscope` | `openai_chat` | `Qwen/Qwen3-235B-A22B-Instruct-2507` | `https://api-inference.modelscope.cn/v1` |
| `ollama` | `openai_chat` | `qwen3:8b` | `http://127.0.0.1:11434/v1` |
| `custom` | `openai_chat` | 空 | 空 |

默认值用于快速填写表单和命令参数。实际可用模型由服务商账号权限、地区、计费方式和兼容层决定。

### 中国科技云 CSTCloud

中国科技云大模型 API 使用 OpenAI API Compatible 协议，Base URL 是 `https://uni-api.cstcloud.cn/v1`。PaperSeek 内置的 provider 为 `cstcloud`，默认模型为 `DeepSeek-V4-Flash`。获取 Key：

1. 打开 [中国科技云 API Keys](https://uni-api.cstcloud.cn/api_keys)。
2. 登录中国科技云统一认证。
3. 登录后按页面要求输入申请信息并提交，即可获取 API Key。
4. 中国科学院院内用户可使用中国科技云通行证登录，通行证通常为院邮箱账号及密码。
5. 在 PaperSeek 中选择 `cstcloud`，填入获取到的 API Key。

接口文档见 [中国科技云大模型 API 接口使用手册](https://uni-api.cstcloud.cn/doc/llm/)。

### 选择模型的建议

检索任务对模型的要求：

- 能稳定生成结构化 JSON。
- 能理解学术题名、摘要和关键词。
- 能处理中文研究问题并转成英文检索查询。
- 能在候选论文之间进行相关性比较。

模型选择建议：

- 首次使用：选择成本低、响应快、支持 JSON 的模型。
- 复杂跨学科问题：选择推理能力更强的模型。
- 批量检索：优先考虑价格、速率限制和稳定性。
- 本地隐私场景：可使用 Ollama，但排序质量取决于本地模型能力。

### Custom provider

当服务商兼容 OpenAI Chat Completions，但不在 Provider 列表中，可以使用：

```bash
paperseek search "your question" \
  --llm-provider custom \
  --llm-api-type openai_chat \
  --llm-model your-model \
  --llm-base-url https://your-gateway.example.com/v1 \
  --llm-key your-key
```

如果你的网关需要额外 header 或非标准参数，当前版本可能无法直接支持。

## Data sources

### 数据源能力总览

```bash
paperseek sources
paperseek sources --json
```

当前数据源：

| Source | ID | API Key | 摘要 | 引用数 | 引用扩展 | PDF 链接 |
| --- | --- | --- | --- | --- | --- | --- |
| OpenAlex | `openalex` | 推荐 | 支持，取决于记录 | 支持 | 支持 | 支持，取决于记录 |
| Crossref | `crossref` | 通常不需要 | 取决于出版商元数据 | 支持，覆盖不稳定 | 不支持 | 不支持 |
| Web of Science Starter | `wos` | 必需 | 不作为稳定字段依赖 | 支持，取决于权限 | 不支持 | 不支持 |

### OpenAlex

OpenAlex 是默认数据源，适合：

- 通用文献发现。
- 获取引用数。
- 获取可用摘要。
- 构建引用图。
- 扩展参考文献和被引论文。

推荐配置：

```bash
export DATA_SOURCE=openalex
export OPENALEX_API_KEY=your-openalex-key
```

可选邮箱：

```bash
export OPENALEX_EMAIL=you@example.org
```

申请 OpenAlex API Key：

1. 打开 `https://openalex.org/`。
2. 注册或登录账号。
3. 进入 API settings。
4. 复制 API Key。
5. 填入 Web UI 或设置 `OPENALEX_API_KEY`。

### Crossref

Crossref 适合：

- DOI 查询与校验。
- 出版元数据补全。
- 期刊、出版社和出版年份确认。
- 与其他数据源结果交叉核对。

推荐配置邮箱：

```bash
export DATA_SOURCE=crossref
export CROSSREF_EMAIL=you@example.org
```

Crossref 公共 REST API 通常不需要 API Key。提供邮箱有助于进入 polite pool，并便于 Crossref 在异常请求时联系。

### Web of Science Starter

WoS Starter 适合已有 Clarivate API 权限的机构用户。需要：

```bash
export DATA_SOURCE=wos
export WOS_API_KEY=your-wos-key
export WOS_DB=WOS
```

申请流程概要：

1. 注册 Clarivate Developer Portal。
2. 创建 Application。
3. 在 Web of Science Starter API 页面为该 Application 订阅。
4. 等待机构或 Clarivate 审批。
5. 获得 API Key 后填入 PaperSeek。

WoS Starter 的字段、请求量和可用数据库取决于订阅计划与机构授权。遇到 `401` 时检查 key、HTTPS 和订阅权限。遇到 `512` 时，通常需要同时排查 Clarivate 服务状态和查询兼容性。

### 选择数据源

| 需求 | 推荐数据源 |
| --- | --- |
| 第一次使用 PaperSeek | OpenAlex |
| 需要引用扩展和 Citation Map | OpenAlex |
| 需要 DOI 与出版元数据校验 | Crossref |
| 机构要求使用 Web of Science | WoS Starter |
| 希望尽量少配置 API Key | OpenAlex 匿名测试或 Crossref |
| 需要较稳定的长期运行 | OpenAlex API Key + LLM Key |

## Discipline Fields

Discipline Fields 用于把检索限制到一个或多个结构化学科领域。当前字段目录基于 OpenAlex Field taxonomy，共 26 个字段，并在 Web UI 中按大类分组显示。

它和 `Field Hint` 的区别是：

| 项目 | 用途 | 示例 |
| --- | --- | --- |
| `Field Hint` / `SEARCH_FIELD` | 自由文本提示，帮助 LLM 生成更贴近领域的检索式 | `management` |
| `Discipline Fields` / `DISCIPLINE_FIELDS` | 结构化学科限制，按数据源能力过滤或映射 | `17`、`Computer Science` |

### 支持的输入

CLI 和环境变量接受：

- OpenAlex Field ID，例如 `17`。
- OpenAlex Field 标签，例如 `Computer Science`。
- OpenAlex Field URL，例如 `https://openalex.org/fields/17`。

多个字段可以重复传入：

```bash
paperseek search "open innovation and digital platforms" \
  --source openalex \
  --discipline "Computer Science" \
  --discipline "Business, Management and Accounting"
```

也可以用环境变量设置默认值。多个值建议用分号分隔，尤其是字段标签本身包含逗号时：

```bash
export DISCIPLINE_FIELDS="Computer Science;Business, Management and Accounting"
paperseek search "open innovation and digital platforms" --source openalex
```

只用纯 ID 时也可以写成：

```bash
export DISCIPLINE_FIELDS="17;14"
```

### 数据源行为

| 数据源 | 行为 |
| --- | --- |
| OpenAlex | 使用 `primary_topic.field.id` 原生过滤，例如 `primary_topic.field.id:17|14`；引用扩展也会把邻居限制在所选 field 中。 |
| Web of Science Starter | 把所选 OpenAlex Field 映射为 Web of Science Categories，并在查询中加入 `WC=(...)` 限制；如果用户查询已经包含 `WC=`，PaperSeek 不会重复追加。 |
| Crossref | Crossref 没有同一套共享学科 taxonomy，PaperSeek 会把所选学科作为 bibliographic query context，而不是 API 原生 filter。 |

### 使用建议

适合使用 Discipline Fields：

- 结果太多，需要按学科收窄候选池。
- 同一个主题在多个学科里含义不同。
- 需要让 OpenAlex 引用扩展也保持在指定领域内。

不建议过早使用过窄字段。首次探索可以保持 `Any field`，先观察结果范围；如果命中太宽，再加入一个或两个最相关字段。

## CLI

### 命令结构

```text
paperseek search <question> [options]
paperseek <question> [options]
paperseek doctor [--source openalex] [--discipline "Computer Science"] [--json]
paperseek smoke [--source openalex] [--query "machine learning"] [--discipline "Computer Science"] [--json]
paperseek sources [--json]
paperseek history <list|show|delete|clear|path>
paperseek config <path|list|keys|set|unset|import-env>
```

`paperseek <question>` 是简写形式，等价于 `paperseek search <question>`。

### 基本搜索

```bash
paperseek "open innovation and digital platforms"
```

指定数据源：

```bash
paperseek "open innovation and digital platforms" --source openalex
paperseek "open innovation and digital platforms" --source crossref
```

指定领域提示：

```bash
paperseek "open innovation and digital platforms" --field management
```

指定结构化学科限制：

```bash
paperseek "open innovation and digital platforms" \
  --source openalex \
  --discipline "Computer Science" \
  --discipline "Business, Management and Accounting"
```

设置目标结果数和迭代次数：

```bash
paperseek "open innovation and digital platforms" \
  --min 5 \
  --max 50 \
  --iterations 5
```

### 输出格式

文本输出：

```bash
paperseek search "responsible AI governance"
```

JSON 输出：

```bash
paperseek search "responsible AI governance" --output json
```

快捷写法：

```bash
paperseek search "responsible AI governance" --json
```

保存 JSON：

```bash
paperseek search "responsible AI governance" --source openalex --json > results.json
```

### 搜索参数

| 参数 | 说明 |
| --- | --- |
| `question` | 自然语言研究问题。 |
| `--source` | 数据源：`openalex`、`crossref`、`wos`。 |
| `--field`, `-f` | 学科或领域提示。 |
| `--discipline`, `--discipline-field` | OpenAlex Field ID、标签或 URL；可重复传入多个学科。 |
| `--db`, `-d` | WoS 数据库代码，例如 `WOS`。 |
| `--fetch-abstracts` | 尝试通过 DOI 从外部源补摘要。 |
| `--no-expand-citations` | 关闭 OpenAlex 引用扩展。 |
| `--min` | 目标最少结果数。 |
| `--max` | 目标最多结果数，当前 UI 和导出上限为 50。 |
| `--iterations` | 最大查询调整轮数。 |
| `--output`, `-o` | `text` 或 `json`。 |
| `--json` | `--output json` 快捷方式。 |
| `--verbose`, `-v` | 打印中间查询信息。 |

### LLM 参数

| 参数 | 说明 |
| --- | --- |
| `--llm-provider` | LLM 服务商。 |
| `--llm-api-type` | API 协议。 |
| `--llm-model` | 模型名称。 |
| `--llm-base-url` | API Base URL。 |
| `--llm-key` | LLM API Key。 |

示例：

```bash
paperseek search "platform governance and innovation" \
  --llm-provider deepseek \
  --llm-api-type openai_chat \
  --llm-model deepseek-v4-flash \
  --llm-base-url https://api.deepseek.com \
  --llm-key your-key
```

### 数据源参数

| 参数 | 说明 |
| --- | --- |
| `--wos-key` | WoS Starter API Key。 |
| `--openalex-key` | OpenAlex API Key。 |
| `--openalex-email` | OpenAlex 联系邮箱。 |
| `--crossref-email` | Crossref polite pool 邮箱。 |

示例：

```bash
paperseek search "responsible AI policy" \
  --source openalex \
  --openalex-key your-openalex-key
```

### 诊断命令

检查配置，不发起真实文献检索：

```bash
paperseek doctor
paperseek doctor --source openalex
paperseek doctor --source openalex --discipline "Computer Science"
paperseek doctor --source openalex --json
```

`doctor` 会检查：

- 数据源是否支持。
- 数据源所需 key 是否存在。
- LLM provider 是否支持。
- API Type 是否支持。
- LLM API Key 是否需要。
- Base URL 格式是否合理。
- 目标结果范围是否有效。
- Discipline Fields 是否已规范化为可识别的学科限制。

### Smoke 命令

`smoke` 会对数据源发起一个最小真实请求：

```bash
paperseek smoke --source openalex --query "machine learning"
paperseek smoke --source openalex --query "machine learning" --discipline "Computer Science"
paperseek smoke --source crossref --query "open innovation"
paperseek smoke --source wos --query "TS=(open innovation)"
```

JSON 输出：

```bash
paperseek smoke --source openalex --query "machine learning" --json
```

`smoke` 适合区分：

- 本地配置问题。
- 数据源网络问题。
- 数据源 API Key 或权限问题。
- 数据源服务端错误。

### Sources 命令

```bash
paperseek sources
paperseek sources --json
```

该命令显示数据源能力，例如是否支持摘要、引用数、引用扩展、PDF 链接、必填配置和可选配置。

### History 命令

PaperSeek 默认把 CLI 和 Web UI 的搜索运行保存到本地 SQLite。查看数据库路径：

```bash
paperseek history path
```

列出最近运行：

```bash
paperseek history list
paperseek history list --limit 20
paperseek history list --json
```

查看一次运行的详情：

```bash
paperseek history show <RUN_ID>
paperseek history show <RUN_ID> --json
```

删除记录：

```bash
paperseek history delete <RUN_ID>
paperseek history clear --yes
```

历史记录保存研究问题、数据源、最终检索式、运行状态、日志事件、引用图元数据和排序后的论文结果。PaperSeek 不会把 LLM API Key、WoS API Key、OpenAlex API Key 或其它原始密钥写入历史数据库。

### Config 命令

查看配置路径：

```bash
paperseek config path
```

列出支持的配置项：

```bash
paperseek config keys
```

保存配置：

```bash
paperseek config set DATA_SOURCE openalex
paperseek config set LLM_PROVIDER deepseek
paperseek config set LLM_API_KEY your-key
```

列出已配置项：

```bash
paperseek config list
```

列出全部项，包括未配置：

```bash
paperseek config list --all
```

JSON 输出：

```bash
paperseek config list --json
```

移除配置：

```bash
paperseek config unset LLM_API_KEY
```

导入 `.env`：

```bash
paperseek config import-env .env
```

## Web UI

### 启动和访问

```bash
paperseek-web
```

浏览器打开：

```text
http://127.0.0.1:8765/
```

Web UI 由四个页面组成：

- `Search`
- `Results`
- `Citation Map`
- `History`

顶部状态栏显示：

- `Export Results CSV`
- `EN` / `中文` 语言切换
- 当前步骤，例如 `Step 0/4`
- 当前状态，例如 `Ready` 或 `Processing`

点击 `EN` 或 `中文` 可以切换 Web UI 语言。选择会保存在当前浏览器，刷新页面后继续生效。语言切换只影响界面文本，不改变检索问题、模型、数据源或历史记录内容。

### Search 页面

Search 页面左侧是输入和配置，右侧是工作流和日志。

#### Research Question

输入研究问题。建议写成一到三句话，包含：

- 主题概念。
- 研究对象。
- 场景或领域。
- 方法、理论或时间范围。

示例：

```text
Find empirical studies on how digital platforms influence open innovation in firms.
```

中文也可以：

```text
查找数字平台如何影响企业开放式创新的实证研究。
```

#### Discipline Fields

`Discipline Fields` 位于 Search 页面研究问题附近，默认显示 `Any field`。打开后可以按学科大类勾选一个或多个 OpenAlex Field。点击 `Clear` 会清空选择。

Web UI 会从 `/api/disciplines` 加载字段目录，并把所选字段随本次请求提交给后端。环境变量 `DISCIPLINE_FIELDS` 设置的默认值会在页面加载时自动选中；浏览器会话中的选择不会写回 `.env` 或用户级配置文件。

如果只想给 LLM 一个宽松提示，可以使用高级设置中的 `Field Hint`；如果需要按结构化学科收窄结果，使用 `Discipline Fields`。

#### Data Source

选择：

- `OpenAlex (precise search)`
- `Crossref (metadata / DOI registry)`
- `Web of Science Starter`

不同数据源会显示不同字段：

| 数据源 | 显示字段 |
| --- | --- |
| OpenAlex | OpenAlex API Key、OpenAlex Email、Field Hint、Expand citations |
| Crossref | Crossref Email、Field Hint |
| WoS Starter | WoS API Key、WoS DB、Field Hint、Try external abstracts |

`Discipline Fields` 是 Search 页面通用选择器，不在上表中重复列出。它会随所选数据源按 [Discipline Fields](#discipline-fields) 中说明的规则应用。

#### LLM Settings

字段：

- Provider
- API Type
- Model
- Base URL
- API Key

选择 Provider 后，Web UI 会填入默认 Model、API Type 和 Base URL。你可以手动修改。

#### Run Parameters

字段：

- Min Results
- Max Results
- Iterations
- Try external abstracts
- Expand citations

建议：

- `Min Results` 默认 `5`。
- `Max Results` 默认 `50`。
- `Iterations` 默认 `5`。
- 首次使用 OpenAlex 时保留 `Expand citations` 开启。
- 如果想减少请求次数，可关闭 `Expand citations`。

#### Check Config

`Check Config` 用于静态诊断。它不会发起真实文献检索，适合检查：

- Research Question 是否填写。
- Data Source 是否支持。
- LLM API Key 是否缺失。
- API Type 是否支持。
- Base URL 是否有效。
- 目标结果范围是否有效。

#### Run Search

点击 `Run Search` 后：

- 页面进入 Processing。
- 右侧工作流逐步更新。
- System Dashboard 输出日志。
- 如果选择了 Discipline Fields，Source Request 日志会显示实际应用的 field filter、`WC=` 限制或 query context。
- 完成后 Results 页面可查看结果。

### Workflow 区域

工作流包含四步：

| 步骤 | 含义 |
| --- | --- |
| Query Generation | LLM 生成数据源查询。 |
| Source Request | 请求数据源并记录命中数量。 |
| Metadata Ranking | LLM 对候选论文评分排序。 |
| Literature Results | 展示结果摘要，并引导进入 Results。 |

运行中每一步会显示当前状态和阶段产物。

### System Dashboard

Search 页面右下角日志面板显示：

- Run ID。
- Provider、API Type、Model、数据源。
- 后端请求是否被接受。
- LLM 请求开始和返回状态。
- 数据源请求开始和返回状态。
- 查询内容、命中数量、迭代轮次。
- Discipline Fields 的源端应用方式。
- 错误信息和排错提示。

可点击 `Export Log` 导出日志文本。日志导出用于排查，不是论文结果导出。

### Results 页面

Results 页面用于阅读和筛选最终论文列表。常见字段包括：

- Rank
- Score
- Title
- Authors
- Year
- Source / Venue
- Provider
- Citation count
- DOI
- Abstract
- Keywords
- Relevance reason
- Record URL
- PDF URL，若数据源提供

支持：

- 搜索结果。
- 按分数、引用、年份或排名排序。
- 按 DOI、摘要、PDF 等可用性过滤。
- 勾选论文。
- 导出 CSV。

如果勾选了论文，CSV 只导出勾选项；如果没有勾选，则导出当前过滤后的结果。

### Citation Map 页面

Citation Map 展示 OpenAlex 引用扩展得到的关系图。

交互能力：

- 拖动节点。
- 缩放画布。
- 平移画布。
- 点击节点查看论文详情。

箭头含义：

```text
A -> B 表示 A 引用了 B
```

Citation Map 依赖 OpenAlex 引用关系。Crossref 和 WoS Starter 当前不支持 PaperSeek 的引用扩展图。

### History 页面

History 页面读取本机 SQLite 历史数据库，用于回看自托管实例上的搜索运行。

可查看内容：

- 研究问题。
- 运行状态和创建时间。
- 数据源、命中数量和结果数量。
- 最终检索式。
- 排序后的论文结果。
- 最近的运行日志事件。

可执行操作：

- `Refresh`：刷新本地历史列表。
- `Open Results`：把该历史运行恢复到 Results 页面继续筛选和导出。
- `Open Citation Map`：如果该运行包含引用图数据，恢复到 Citation Map 页面探索。
- `Delete`：删除该条本地历史记录。

History 页面不会显示搜索配置区和 System Dashboard，因为它查看的是已经完成或失败的历史运行，而不是新的搜索会话。

## Results and exports

### CLI text 输出

文本输出适合人工快速阅读，包含：

- Search question
- Field
- Database / source
- Final query
- Found total
- Ranked count
- 每篇论文的标题、作者、来源、DOI、引用数、摘要片段和评分理由

### CLI JSON 输出

JSON 顶层字段：

| 字段 | 说明 |
| --- | --- |
| `question` | 原始研究问题。 |
| `source` | 数据源。 |
| `query` | 最终查询。 |
| `database` | 数据库或数据源标识。 |
| `field` | 学科提示。 |
| `total_results` | 数据源命中总数。 |
| `iterations` | 实际迭代次数。 |
| `history` | 查询迭代历史。 |
| `ranked` | 排序后的论文列表。 |

`ranked` 中常用字段：

| 字段 | 说明 |
| --- | --- |
| `rank` | 最终排名。 |
| `source` / `provider` | 数据源。 |
| `id` / `uid` | 数据源记录 ID。 |
| `title` | 标题。 |
| `authors` / `authors_text` | 作者。 |
| `year` / `publish_year` | 出版年份。 |
| `venue` / `source` | 期刊、会议或来源。 |
| `publication_type` / `document_types` | 文献类型。 |
| `doi` | DOI。 |
| `url` | 记录链接、落地页或 DOI 链接。 |
| `pdf_url` | PDF 链接，若数据源提供。 |
| `abstract` | 摘要，若可用。 |
| `keywords` / `keywords_text` | 关键词。 |
| `citation_count` / `citations` | 引用数。 |
| `relevance_score` / `score` | LLM 相关性评分。 |
| `relevance_reason` / `reasoning` | 评分理由。 |
| `links` | 记录、PDF、引用、参考文献等链接集合。 |

### Web CSV 导出

Web UI 导出 CSV 时包含 UTF-8 BOM，便于 Excel 识别非英文字符。字段包括：

- rank
- score
- title
- authors
- publish_year
- source
- provider
- document_types
- citations
- doi
- keywords
- abstract
- reasoning
- record_url
- pdf_url

使用建议：

- 若要人工筛选，先在 Results 页面勾选，再导出。
- 若要交给 LLM 继续阅读，建议保留摘要、DOI、record_url 和 reasoning 字段。
- 导出文件名使用研究问题主题和当前日期，例如 `open-innovation-20260603-1530-papers.csv`。
- 如果 Excel 打开仍显示乱码，使用“数据 -> 从文本/CSV”并选择 UTF-8。

### 日志导出

`Export Log` 导出的是运行日志，不是论文结果。日志适合：

- 排查 LLM 调用失败。
- 排查数据源 HTTP 错误。
- 保存运行过程证据。
- 向维护者报告问题。

## Citation expansion and map

### 启用条件

引用扩展当前仅支持 OpenAlex。默认开启：

```bash
export EXPAND_CITATIONS=true
```

CLI 关闭：

```bash
paperseek search "your question" --source openalex --no-expand-citations
```

Web UI 关闭：

取消勾选 `Expand citations (OpenAlex)`。

如果同时选择了 Discipline Fields，OpenAlex 引用扩展会把前向引用和后向参考文献邻居限制在相同的 field 范围内，减少跨学科扩展带来的噪声。

### 参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `CITATION_SEED_COUNT` | `3` | 从高匹配结果中选择多少篇作为 seed。 |
| `CITATION_PER_SEED` | `4` | 每个 seed 抓取多少条引用邻居。 |
| `CITATION_MAX_RECORDS` | `40` | 最多加入多少条引用扩展记录。 |

### 何时开启

适合开启：

- 你希望发现经典文献。
- 关键词检索结果过窄。
- 你想探索某个主题的相邻论文。
- 你需要 Citation Map。

适合关闭：

- 你只想看直接检索命中的论文。
- 你想减少 API 请求次数。
- 数据源请求速度较慢。
- 你正在做严格可复现的关键词检索试验。

### 如何解读图

Citation Map 不是文献计量分析工具，而是探索界面。建议：

- 把大节点或高引用节点作为进一步阅读线索。
- 关注连接多个主题的论文。
- 不要仅凭图中位置判断论文重要性。
- 最终纳入文献仍需人工阅读摘要或全文。

## Python API and core

社区版安装包已经内置可复用核心模块 `paperseek_core`，不需要额外安装单独的 `paperseek-core` 仓库依赖。常规用户和下游代码建议从 `paperseek` 导入稳定入口：

```python
from paperseek import PaperSeekAgent
```

`PaperSeekAgent` 是当前推荐的 agent 类名。`LiteratureSearchAgent` 和 `WosSearchAgent` 仍保留为兼容旧代码的别名，新代码请不要再依赖旧命名。

## Agent Skill

PaperSeek 提供可选 Skill：

```text
skills/paperseek/
```

Skill 用于指导支持 Skill 的 AI agent 调用自包含 runtime 或完整 PaperSeek 包。它包括：

- `SKILL.md`
- `references/cli-contract.md`
- `references/management-layer.md`
- `references/source-routing.md`
- `scripts/paperseek.py`
- `scripts/paperseek_skill_runtime.py`

### Skill 的定位

Skill 不再只是一份操作说明。它包含一个自包含 runtime：

- 不安装 PaperSeek 包时，也能运行核心 `search`、`smoke`、`sources`、`doctor`。
- 优先调用完整 PaperSeek 包；包不可用时回退到 `scripts/paperseek_skill_runtime.py`。
- 告诉 agent 如何选择 OpenAlex、Crossref、WoS。
- 告诉 agent 如何解析 JSON 输出。
- 告诉 agent 不要保存 API Key、不要编造论文元数据、不要下载受限 PDF。

### Skill 不随 Python 包安装

`skills/` 目录不会被打进 PaperSeek wheel。这样普通 Python 用户不会被自动安装 agent 平台文件。

如果你需要 Skill，可手动复制：

```text
skills/paperseek/
```

到你的 agent 平台 Skill 目录。

### Skill launcher

launcher 路径：

```text
skills/paperseek/scripts/paperseek.py
```

查看安装帮助：

```bash
python skills/paperseek/scripts/paperseek.py --install-help
```

调用 PaperSeek Skill runtime：

```bash
python skills/paperseek/scripts/paperseek.py sources --json
python skills/paperseek/scripts/paperseek.py smoke --source openalex --query "machine learning" --json
python skills/paperseek/scripts/paperseek.py search "open innovation and digital platforms" --source openalex --json
```

如果 PaperSeek 包未安装，上述 `sources`、`smoke`、`search`、`doctor` 仍可通过自包含 runtime 运行。若你希望使用完整包的 Web UI、引用图或完整历史管理，可设置：

```bash
export PAPERSEEK_PROJECT_ROOT=/path/to/paperseek
```

Windows PowerShell：

```powershell
$env:PAPERSEEK_PROJECT_ROOT = "C:\path\to\paperseek"
```

launcher 会优先调用完整 PaperSeek 包；没有安装包时，会自动使用 Skill 自带 runtime 运行核心检索。

## MCP Server

PaperSeek 提供可选的 MCP（Model Context Protocol）服务器。它和 Skill 的定位不同：

- Skill 是一组可复制到 agent 平台的说明与自包含 runtime。
- MCP Server 是一个长期运行的 stdio 服务，供支持 MCP 的客户端通过工具调用 PaperSeek。

MCP Server 复用完整 PaperSeek 包和 `PaperSeekAgent` 核心逻辑，因此支持 LLM 检索、配置诊断、数据源 smoke test 和本地历史记录。它需要 Python 3.10+，但基础 PaperSeek 包仍保持 Python 3.8+。

### 安装 MCP 可选依赖

```bash
python -m pip install "paperseek[mcp]"
```

如果从源码安装：

```bash
python -m pip install -e ".[mcp]"
```

启动服务器：

```bash
paperseek-mcp
```

也可以使用模块方式启动：

```bash
python -m paperseek.mcp_server
```

### 配置方式

MCP Server 读取的配置与 CLI、Web UI 一致：

- 当前工作目录或包根目录下的 `.env`
- 操作系统环境变量
- 通过 `paperseek config set` 写入的用户级配置

常用最小配置：

```text
LLM_PROVIDER=deepseek
LLM_API_TYPE=openai_chat
LLM_MODEL=deepseek-v4-flash
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=your-llm-api-key
OPENALEX_API_KEY=your-openalex-api-key
```

API Key 由 MCP Server 进程持有，不作为 MCP tool 参数传入。MCP 响应会对常见凭据形字符串做脱敏处理；仍然不要把真实 API Key 写入 prompt、issue、README 或客户端配置截图。

### 可用工具

| 工具 | 用途 |
| --- | --- |
| `search_papers` | 输入研究问题，执行完整 LLM 检索工作流并返回排序结果 |
| `check_config` | 检查数据源、LLM、API Key 和运行参数是否就绪 |
| `smoke_test` | 对数据源发起一次最小真实请求，测试连通性 |
| `list_sources` | 列出 OpenAlex、Crossref、WoS Starter 及其能力 |
| `list_history` | 列出本地历史记录 |
| `get_history_run` | 查看某次历史检索的完整详情 |

`search_papers` 支持常用覆盖参数，包括 `source`、`field`、`discipline_fields`、`target_min`、`target_max`、`max_iterations`、`expand_citations` 和 `fetch_abstracts`。不传这些参数时，会沿用环境变量或用户配置中的默认值。

### Claude Desktop 配置示例

```json
{
  "mcpServers": {
    "paperseek": {
      "command": "paperseek-mcp",
      "env": {
        "LLM_PROVIDER": "deepseek",
        "LLM_API_TYPE": "openai_chat",
        "LLM_MODEL": "deepseek-v4-flash",
        "LLM_BASE_URL": "https://api.deepseek.com",
        "LLM_API_KEY": "your-llm-api-key",
        "OPENALEX_API_KEY": "your-openalex-api-key"
      }
    }
  }
}
```

如果你在项目目录运行客户端，也可以不在客户端配置里写 key，而是在项目 `.env` 中保存配置。共享电脑上使用后请退出客户端，并确认 `.env` 没有被提交到 Git。

### MCP 与 CLI 的差异

- MCP 返回 JSON 字符串，适合 agent 继续解析。
- `paperseek-mcp` 默认使用 stdio transport，由 MCP 客户端负责启动和通信。
- 搜索成功会写入 PaperSeek 本地历史；可用 `list_history` 和 `get_history_run` 查看。
- MCP Server 本身不提供 Web UI；需要浏览器界面时使用 `paperseek-web`。

## Diagnostics and troubleshooting

### 推荐排错顺序

1. 确认虚拟环境已激活。
2. 运行 `paperseek --help`。
3. 运行 `paperseek sources`。
4. 运行 `paperseek doctor --json`。
5. 运行 `paperseek smoke --source openalex --query "machine learning" --json`。
6. 若 Web UI 失败，导出 System Dashboard 日志。
7. 简化 Research Question 后重试。

### `paperseek` 命令不存在

可能原因：

- 虚拟环境未激活。
- 包未安装。
- Scripts/bin 目录未加入 PATH。

解决：

```bash
python -m pip install -e .
python -m paperseek.cli --help
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
python -m paperseek.cli --help
```

### 缺少 LLM API Key

错误示例：

```text
LLM_API_KEY is required unless provider is Ollama.
```

解决：

```bash
export LLM_API_KEY=your-key
```

或使用本地 Ollama：

```bash
export LLM_PROVIDER=ollama
export LLM_API_TYPE=openai_chat
export LLM_BASE_URL=http://127.0.0.1:11434/v1
```

### Base URL 错误

`LLM_BASE_URL` 必须以 `http://` 或 `https://` 开头。远程服务商应使用 HTTPS。本地 Ollama 可使用 HTTP：

```text
http://127.0.0.1:11434/v1
```

### OpenAlex 请求失败

排查：

```bash
paperseek smoke --source openalex --query "machine learning" --json
```

建议：

- 配置 `OPENALEX_API_KEY`。
- 简化查询。
- 降低迭代次数或关闭引用扩展。
- 稍后重试。

### Crossref 请求失败

建议：

```bash
export CROSSREF_EMAIL=you@example.org
paperseek smoke --source crossref --query "open innovation"
```

如果请求频繁，设置邮箱进入 polite pool。

### WoS 401

常见原因：

- `WOS_API_KEY` 错误。
- Starter API 订阅未审批。
- 使用了不支持的 API 权限。
- 请求未走 HTTPS。

处理：

```bash
paperseek doctor --source wos
paperseek smoke --source wos --query "TS=(open innovation)"
```

### WoS 512

HTTP 512 是 Clarivate 端非标准错误。建议：

- 稍后重试。
- 简化检索式。
- 减少特殊字符。
- 用 OpenAlex 继续检索。
- 联系 Clarivate Customer Care 并附带查询、时间和响应体。

### 结果太少

可尝试：

- 删除过窄的 Field Hint。
- 清空或减少 Discipline Fields。
- 减少限定词。
- 使用英文关键词。
- 增加 `--iterations`。
- 降低 `--min`。
- 开启 OpenAlex 引用扩展。

示例：

```bash
paperseek search "open innovation" --source openalex --iterations 8
```

### 结果太多

可尝试：

- 加入 Discipline Fields 学科领域限制。
- 加入研究对象。
- 加入方法或时间范围。
- 降低 `--max`。

示例：

```bash
paperseek search "open innovation in digital platform ecosystems" --field management --max 30
```

### LLM 返回格式异常

现象：

- 查询生成失败。
- 排序失败。
- JSON 解析失败。

建议：

- 换更稳定的模型。
- 使用官方 API 或稳定兼容网关。
- 缩短 Research Question。
- 减少候选结果数量。
- 查看 System Dashboard 日志。

### CSV 乱码

PaperSeek Web UI 导出的 CSV 带 UTF-8 BOM。若仍乱码：

- 用 Excel 的“数据 -> 从文本/CSV”导入。
- 选择 UTF-8 编码。
- 或使用 LibreOffice / Google Sheets 打开。

### Web UI 不刷新或样式异常

建议：

- 刷新浏览器。
- 清理浏览器缓存。
- 确认访问的是当前启动的端口。
- 重启 `paperseek-web`。

## Security and privacy

### API Key

建议：

- 不要把真实 API Key 写入 README、Skill、测试或 issue。
- 不要把 `.env` 提交到 Git。
- Web UI 表单中的 Key 只用于当前会话。
- CLI 用户级配置会保存到本地配置文件，`paperseek config list` 会遮蔽密钥。

### 本地历史数据库

开源自托管版默认启用本地历史记录，默认路径：

```text
~/.paperseek/paperseek.db
```

历史数据库会保存：

- 研究问题。
- 数据源、Provider、Model、目标结果数、Discipline Fields 等运行摘要。
- 是否提供了相关 API Key 的布尔值。
- 最终检索式、运行事件、错误信息。
- 排序后的论文元数据、引用图元数据。

历史数据库不会保存：

- LLM API Key。
- WoS API Key。
- OpenAlex API Key。
- 其它原始 token、authorization header 或密码字段。

关闭本地历史：

```bash
export PAPERSEEK_HISTORY_ENABLED=false
```

自定义历史路径：

```bash
export PAPERSEEK_HISTORY_DB=/path/to/paperseek.db
```

### Web UI 本地服务

默认监听：

```text
127.0.0.1:8765
```

这意味着服务只对本机开放。不要在不理解风险的情况下把它绑定到 `0.0.0.0` 或暴露到公网。

### 数据和版权边界

PaperSeek 返回元数据和链接。它不负责：

- 下载受版权限制的全文。
- 绕过出版社或数据库权限。
- 保存数据库登录态。
- 替代人工文献质量判断。

### Agent 使用

当通过 agent 使用 PaperSeek：

- 不要让 agent 把 API Key 写入 Skill 文件。
- 不要让 agent 编造缺失 DOI、作者、摘要或引用数。
- 不要把 LLM relevance score 当作系统综述纳入标准。
- 需要复现时保存 JSON 输出和日志。

## Upgrade and maintenance

### 更新 PyPI 安装

```bash
python -m pip install --upgrade paperseek
```

### 更新源码安装

```bash
git pull
python -m pip install -e .
```

### 更新 GitHub 安装

```bash
python -m pip install --upgrade "git+https://github.com/MingfengHong/paperseek.git"
```

### 检查版本

```bash
python -c "import paperseek; print(paperseek.__version__)"
```

### 运行本地测试

开发者可运行：

```bash
python -m compileall -q paperseek skills/paperseek/scripts
python -m unittest discover -s tests
node --check paperseek/static/app.js
python -m pip wheel . -w dist --no-deps
```

普通用户通常不需要运行测试。

## FAQ

### PaperSeek 能做系统综述吗？

PaperSeek 可以帮助生成候选文献列表，但不能单独完成系统综述。系统综述需要明确检索策略、纳入排除标准、人工复核、去重、质量评价和可复现记录。

### PaperSeek 会下载 PDF 吗？

不会。PaperSeek 只返回元数据和数据源提供的链接。即使某些记录包含 PDF URL，访问权限仍取决于出版商、开放获取状态或机构订阅。

### 为什么结果没有摘要？

不同数据源的摘要覆盖不同。OpenAlex 可能返回摘要；Crossref 摘要依赖出版商元数据；WoS Starter 当前不应依赖摘要字段。可尝试 OpenAlex 或启用外部摘要补全。

### 引用数一定准确吗？

不一定。引用数由数据源提供，不同数据源统计口径不同。引用数适合作为排序和探索线索，不应直接作为唯一评价指标。

### 为什么搜索结果和数据库网页检索不同？

原因可能包括：

- 数据源 API 与网页检索语法不同。
- LLM 生成查询与人工检索式不同。
- Discipline Fields 在 OpenAlex、WoS 和 Crossref 中的应用方式不同。
- API 返回字段和排序规则不同。
- 时间、权限、订阅范围不同。

建议保存最终查询和日志，用于复核。

### 能不能只用 Crossref？

可以，但 Crossref 更适合 DOI 和出版元数据，不一定适合作为唯一语义召回来源。若需要广泛发现文献，建议优先使用 OpenAlex。

### 能不能只用本地模型？

可以。使用 Ollama 时配置：

```bash
export LLM_PROVIDER=ollama
export LLM_API_TYPE=openai_chat
export LLM_BASE_URL=http://127.0.0.1:11434/v1
export LLM_MODEL=qwen3:8b
```

本地模型的查询生成和排序质量取决于模型能力。

### 如何把结果交给其他 AI？

推荐：

```bash
paperseek search "your question" --source openalex --json > papers.json
```

或在 Web UI 的 Results 页面导出 CSV。优先保留标题、作者、年份、DOI、摘要、引用数、链接和 relevance reason。

### Skill 是必须安装的吗？

不是。Skill 只用于支持 Skill 的 agent 平台。普通 CLI 和 Web UI 用户不需要安装 Skill。若只复制 `skills/paperseek/` 到 agent 平台，Skill 自带 runtime 也可以直接完成核心文献检索；但 Web UI、引用图和完整历史管理仍需要完整 PaperSeek 包。

### MCP Server 是必须安装的吗？

不是。普通 CLI、Web UI、Docker、Vercel 和 ModelScope 创空间部署都不需要 MCP。只有当你要让 Claude Desktop、Cursor 或其他 MCP-compatible agent 通过工具调用 PaperSeek 时，才需要安装 `paperseek[mcp]` 并运行 `paperseek-mcp`。由于当前 `mcp` 依赖本身要求 Python 3.10+，MCP 功能也要求 Python 3.10+；基础 PaperSeek 包仍支持 Python 3.8+。

### Web UI 会保存我的 Key 吗？

不会。Web UI 表单值只用于当前会话。CLI 的 `paperseek config set` 会保存到本地用户级配置文件，这是用户主动执行的行为。
