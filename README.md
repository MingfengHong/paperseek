---
domain:
- nlp
tags:
- literature-search
- research-agent
- openalex
- fastapi
models:
- Qwen/Qwen3-235B-A22B-Instruct-2507
license: Apache-2.0
deployspec:
  entry_file: Dockerfile
---

# PaperSeek

[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/MingfengHong/paperseek/actions/workflows/ci.yml/badge.svg)](https://github.com/MingfengHong/paperseek/actions/workflows/ci.yml)
[![Status](https://img.shields.io/badge/status-alpha-orange)](#项目状态)

**LLM based Literature Search Agent.** PaperSeek 是一个面向研究者的文献发现工具，支持用自然语言发起检索、自动迭代查询、扩展候选论文、排序结果并导出可复核的文献列表。

![PaperSeek web interface](https://raw.githubusercontent.com/MingfengHong/paperseek/main/docs/assets/paperseek-web.png)

完整使用说明见 [PaperSeek 用户手册](docs/user-manual.md)。
部署说明见 [Docker、Vercel 与 ModelScope 部署指南](docs/deployment.md)。
在线体验见 [ModelScope Studio](https://www.modelscope.cn/studios/HongMingfeng/paperseek)。

## 概览

PaperSeek 将研究问题组织成一条可观察的检索工作流：

- 输入中文或英文研究问题。
- 由 LLM 生成适合数据源的检索查询。
- 根据命中数量自动放宽或收窄查询。
- 统一整理题名、作者、期刊、年份、DOI、摘要、引用数和链接等元数据。
- 对候选文献进行 LLM 相关性评分。
- 可选地通过 OpenAlex 引用关系扩展高匹配论文的前向引用和后向参考文献。
- 在网页中查看工作流、结果表和引用图，并导出 CSV。

PaperSeek 专注于第一轮候选文献发现和元数据整理。系统综述流程、全文获取、版权合规和最终研究判断仍需由研究者完成。

## 功能概览

| 功能 | 说明 |
| --- | --- |
| 自然语言检索 | 输入研究问题，自动生成数据源查询。 |
| 多轮迭代 | 根据目标结果数量自动调整查询，默认最多 5 轮。 |
| 相关性排序 | LLM 对候选论文打分并给出简短理由。 |
| OpenAlex 引用扩展 | 从高匹配论文扩展参考文献和被引论文。 |
| 结果导出 | 在 Results 页面勾选论文并导出 CSV。 |
| 引用图 | 使用箭头显示引用方向，支持拖拽、缩放和平移。 |
| CLI 与 Web UI | 既可命令行运行，也可打开本地网页交互使用。 |
| Docker / Vercel / ModelScope 部署 | 支持 Docker 完整部署、Vercel 一键体验部署和 ModelScope Studio 创空间部署。 |
| 配置诊断 | `doctor`、`smoke`、`sources` 帮助排查 API Key、数据源和协议问题。 |
| 可选 Agent Skill | `skills/paperseek/` 可单独复制到支持 Skill 的 agent 平台，不随 Python 包自动安装。 |

## 快速开始

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

启动网页界面：

```bash
paperseek-web
```

打开：

```text
http://127.0.0.1:8765/
```

也可以直接使用命令行：

```bash
paperseek "open innovation and digital platforms" --source openalex
```

## 部署

Docker 是完整 Web UI 的推荐部署方式：

```bash
docker compose up --build
```

打开：

```text
http://127.0.0.1:8765/
```

Vercel 可用于快速体验和轻量 Web UI 部署：

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FMingfengHong%2Fpaperseek)

ModelScope Studio 也可托管完整 Web UI，适合中文社区用户在线体验。长时间搜索、引用扩展和大量请求建议使用 Docker、ModelScope Studio 或 VPS。完整说明见 [部署指南](docs/deployment.md)。

## 最小配置

PaperSeek 至少需要一个 LLM。默认数据源是 OpenAlex；OpenAlex 可匿名测试，但建议申请免费 API Key 以获得更稳定的访问体验。

以 DeepSeek 为例：

```bash
export LLM_PROVIDER=deepseek
export LLM_API_TYPE=openai_chat
export LLM_MODEL=deepseek-v4-flash
export LLM_BASE_URL=https://api.deepseek.com
export LLM_API_KEY=your-llm-api-key
paperseek-web
```

以 ModelScope API-Inference 为例：

```bash
export LLM_PROVIDER=modelscope
export LLM_API_TYPE=openai_chat
export LLM_MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507
export LLM_BASE_URL=https://api-inference.modelscope.cn/v1
export LLM_API_KEY=your-modelscope-token
paperseek-web
```

Windows PowerShell：

```powershell
$env:LLM_PROVIDER = "deepseek"
$env:LLM_API_TYPE = "openai_chat"
$env:LLM_MODEL = "deepseek-v4-flash"
$env:LLM_BASE_URL = "https://api.deepseek.com"
$env:LLM_API_KEY = "your-llm-api-key"
paperseek-web
```

本地 Ollama 不需要 LLM API Key：

```bash
export LLM_PROVIDER=ollama
export LLM_API_TYPE=openai_chat
export LLM_MODEL=qwen3:8b
export LLM_BASE_URL=http://127.0.0.1:11434/v1
paperseek-web
```

项目提供 `.env.example`。你可以复制为 `.env` 作为本地配置参考，但不要提交真实 API Key。

## Web UI

PaperSeek 的网页界面分为三个工作区：

| 页面 | 用途 |
| --- | --- |
| Search | 输入研究问题，配置数据源、LLM、迭代次数和目标结果数；实时查看工作流与系统日志。 |
| Results | 查看最终排序结果，搜索、过滤、排序、勾选，并导出论文 CSV。 |
| Citation Map | 查看 OpenAlex 引用扩展形成的关系图，按箭头方向探索论文之间的引用关系。 |

Web UI 中填写的 API Key、Base URL 和参数只用于当前浏览器会话，不写入本地配置文件。

## CLI 用法

基本检索：

```bash
paperseek "responsible AI governance in public sector" --source openalex
```

显式子命令：

```bash
paperseek search "digital platforms and open innovation" --source openalex
```

JSON 输出：

```bash
paperseek search "open innovation" --source openalex --output json
```

常用参数：

```bash
paperseek search "your research question" \
  --source openalex \
  --field management \
  --min 5 \
  --max 50 \
  --iterations 5 \
  --llm-provider deepseek \
  --llm-api-type openai_chat \
  --llm-model deepseek-v4-flash \
  --llm-base-url https://api.deepseek.com \
  --llm-key your-llm-api-key
```

诊断配置：

```bash
paperseek doctor
paperseek doctor --source openalex --json
```

测试数据源最小真实请求：

```bash
paperseek smoke --source openalex --query "machine learning"
paperseek smoke --source crossref --query "open innovation" --json
```

查看数据源能力：

```bash
paperseek sources
paperseek sources --json
```

保存 CLI 用户级配置：

```bash
paperseek config path
paperseek config set LLM_API_KEY your-llm-api-key
paperseek config list
paperseek config unset LLM_API_KEY
```

环境变量优先于用户级配置。`paperseek config list` 会遮蔽密钥。

## 数据源

| 数据源 | 默认状态 | API Key | 适合场景 | 说明 |
| --- | --- | --- | --- | --- |
| OpenAlex | 默认 | 推荐 | 精确检索、摘要、引用数、引用扩展、引用图 | 开放学术元数据库，适合通用文献发现与引用关系探索。 |
| Crossref | 支持 | 通常不需要 | DOI、出版元数据、期刊和出版社信息校验 | DOI 与出版元数据注册库，适合题录校验和 DOI 补全。 |
| Web of Science Starter | 适配中 | 必需 | 已有 Clarivate API 权限的机构用户 | 商业数据库 API，返回字段和可用性取决于订阅计划与机构授权。 |

## LLM 服务商

PaperSeek 支持两类主流接口协议：OpenAI 风格接口和 Anthropic Messages API。Provider 表示模型服务商，API Type 表示请求协议。

| Provider | 默认 API Type | 默认模型 |
| --- | --- | --- |
| OpenAI | `openai_responses` | `gpt-5.4-mini` |
| Anthropic | `anthropic_messages` | `claude-sonnet-4-6` |
| Google Gemini | `openai_chat` | `gemini-3.5-flash` |
| DeepSeek | `openai_chat` | `deepseek-v4-flash` |
| 阿里云百炼 DashScope | `openai_chat` | `qwen3.6-plus` |
| Kimi Moonshot | `openai_chat` | `kimi-k2.6` |
| 智谱 AI GLM | `openai_chat` | `glm-5.1` |
| 硅基流动 SiliconFlow | `openai_chat` | `deepseek-ai/DeepSeek-V4-Flash` |
| OpenRouter | `openai_chat` | `openai/gpt-5.4-mini` |
| 火山方舟 | `openai_chat` | `doubao-seed-2-0-mini-260428` |
| 腾讯混元 | `openai_chat` | `hunyuan-turbos-latest` |
| 百度千帆 | `openai_chat` | `ernie-5.0` |
| ModelScope 魔搭 | `openai_chat` | `Qwen/Qwen3-235B-A22B-Instruct-2507` |
| Ollama | `openai_chat` | `qwen3:8b` |
| Custom | `openai_chat` | 空，用户自行填写 |

默认模型用于初始化表单和命令参数示例。实际可用模型以各服务商控制台、账号权限和兼容层为准。

## 工作流

一次搜索通常包含四步：

1. **Query Generation**：LLM 根据研究问题和可选学科提示生成初始查询。
2. **Source Search**：请求 OpenAlex、Crossref 或 WoS Starter，并记录 HTTP 状态和命中数量。
3. **Query Refinement**：若命中数过少或过多，LLM 调整查询并继续下一轮。
4. **Ranking & Results**：将候选池交给 LLM 统一评分，输出前若干条结果。

如果启用 OpenAlex 引用扩展，PaperSeek 会从高匹配论文中选择 seed paper，加入 seed 的参考文献和被引论文，再对完整候选池统一评分。默认最大输出 50 条。

## 引用图

Citation Map 使用箭头表示引用方向：

```text
A -> B  表示 A 引用了 B
```

图中节点来自最终结果和 OpenAlex 引用扩展记录。你可以拖动节点、缩放和平移画布，并查看节点详情。引用图适合发现关键词检索遗漏的经典文献、相邻主题和近期延伸研究。

## 环境变量

| 变量 | 说明 |
| --- | --- |
| `DATA_SOURCE` | `openalex`、`crossref` 或 `wos`，默认 `openalex`。 |
| `LLM_PROVIDER` | LLM 服务商，例如 `openai`、`deepseek`、`anthropic`、`ollama`。 |
| `LLM_API_TYPE` | `openai_responses`、`openai_chat` 或 `anthropic_messages`。 |
| `LLM_MODEL` | 模型名称。 |
| `LLM_BASE_URL` | API Base URL。 |
| `LLM_API_KEY` | LLM API Key；Ollama 可不填。 |
| `OPENALEX_API_KEY` | OpenAlex API Key，推荐填写。 |
| `OPENALEX_EMAIL` | OpenAlex 联系邮箱。 |
| `CROSSREF_EMAIL` | Crossref polite pool 邮箱。 |
| `WOS_API_KEY` | Clarivate Web of Science Starter API Key。 |
| `WOS_DB` | WoS 数据库代码，默认 `WOS`。 |
| `TARGET_MIN` / `TARGET_MAX` | 目标结果数量范围。 |
| `MAX_ITERATIONS` | 最大查询调整轮数。 |
| `EXPAND_CITATIONS` | 是否启用 OpenAlex 引用扩展，默认 `true`。 |
| `FETCH_ABSTRACTS` | 是否尝试从外部 DOI 元数据补摘要，默认 `false`。 |
| `CITATION_SEED_COUNT` | 引用扩展 seed 论文数量。 |
| `CITATION_PER_SEED` | 每个 seed 抓取的引用邻居数量。 |
| `CITATION_MAX_RECORDS` | 引用扩展候选上限。 |

## API 获取方式

### OpenAlex

OpenAlex 可匿名访问，但推荐配置免费 API Key：

1. 打开 [OpenAlex](https://openalex.org/) 并注册账号。
2. 进入 [OpenAlex API settings](https://openalex.org/settings/api)。
3. 复制 API Key。
4. 在 Web UI 填写 `OpenAlex API Key`，或设置 `OPENALEX_API_KEY`。

### Crossref

Crossref REST API 通常不需要 API Key。建议设置邮箱进入 polite pool：

```bash
export CROSSREF_EMAIL=you@example.org
```

如果需要更高限额、优先支持或生产级 SLA，可以了解 Crossref Metadata Plus。PaperSeek 使用 Crossref 公共/Polite REST API 路径。

### Web of Science Starter API

WoS Starter 需要在 Clarivate Developer Portal 申请，通常适合已有机构订阅权限的用户：

1. 打开 [Clarivate Developer Portal 注册页](https://developer.clarivate.com/signup)，点击 `Register`。
2. 建议使用机构邮箱注册，并尽量与 Web of Science 数据库账号一致。
3. 登录后进入 [Applications](https://developer.clarivate.com/applications)，点击 `Register Application`。
4. 填写应用信息：
   - `Application ID` 使用数字、小写字母、`-` 或 `_`。
   - `Application Name` 可写为机构或项目名称。
   - `Application Description` 可说明用于 Web of Science API 检索。
   - `Client Type` 保持默认 `Public: Single Page Application`。
   - 不勾选 OAuth2.0 Flows。
5. 打开 [Web of Science Starter API](https://developer.clarivate.com/apis/wos-starter) 页面。
6. 找到刚注册的 Application，点击 `Subscribe`。
7. 按身份和机构权限选择计划。机构成员通常选择 Institutional Member 相关计划。
8. 看到 `Subscription approval is pending` 后等待审批。机构申请通常需要数个工作日。
9. 获得 API Key 后，在 Web UI 填写 `WoS API Key`，或设置 `WOS_API_KEY`。

WoS Starter 的权限、每日请求量和返回字段取决于订阅计划与机构授权。若遇到 HTTP 401，先检查是否使用 `https://` 和正确 key；若遇到 Clarivate 返回的非标准 HTTP 512，应优先检查 Clarivate 服务状态、订阅审批和检索式兼容性。

## Agent Skill

仓库包含一个可选的 PaperSeek Skill：

```text
skills/paperseek/
```

它用于指导支持 Skill 的 AI agent 正确调用 `paperseek` CLI 和本地 Web UI，包括数据源选择、配置诊断、JSON 结果解析和引用图边界。Skill 使用 progressive disclosure：`SKILL.md` 保持简短，详细命令契约放在 `references/`。

这个 Skill **不会随 Python 包自动安装**。如果需要在 agent 平台中使用，可以手动复制或链接 `skills/paperseek/` 到对应平台的 Skill 目录。

Skill 中的 launcher：

```text
skills/paperseek/scripts/paperseek.py
```

只负责调用完整的 PaperSeek Python 包，不维护无依赖降级版检索实现。单独发布 Skill 时，应先安装 PaperSeek 包，或设置 `PAPERSEEK_PROJECT_ROOT` 指向本地源码。

## 项目状态

PaperSeek 当前处于 alpha 阶段。CLI、Web UI、OpenAlex、Crossref、引用扩展、CSV 导出和 Skill 基本可用，但仍建议对正式研究结论进行人工复核。

欢迎贡献：

- 新数据源适配器。
- 更稳健的查询生成与排序提示词。
- 更好的引用图交互。
- Web API、CLI、provider parsing 和导出行为测试。
- 文档、示例和错误诊断改进。

贡献前可阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。安全问题请参考 [SECURITY.md](SECURITY.md)。

## 开源协议

PaperSeek 使用 [Apache License 2.0](LICENSE) 开源。
