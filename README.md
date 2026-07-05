<p align="center">
  <img src="docs/assets/paperseek_logo_with_text.png" alt="PaperSeek" width="560">
</p>

<p align="center">
  <strong>AI-powered literature search and discovery at research speed.</strong>
</p>

<p align="center">
  输入一句研究问题，PaperSeek 自动生成检索式、迭代命中范围、扩展引用网络、排序候选论文，并导出可复核结果。
  <br>
  面向开题、综述、跨学科选题和日常文献追踪的开源检索工作流。
</p>

<p align="center">
  <a href="https://www.paperseek.xyz/">在线版</a>
  ·
  <a href="https://docs.paperseek.xyz/">文档站</a>
  ·
  <a href="https://modelscope.cn/studios/HongMingfeng/PaperSeek">创空间</a>
  ·
  <a href="https://modelscope.cn/learn/434408">社区文章</a>
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
  <a href="#项目状态"><img alt="Status" src="https://img.shields.io/badge/status-alpha-orange"></a>
  <a href="https://modelscope.cn/studios/HongMingfeng/PaperSeek"><img alt="ModelScope visits" src="https://img.shields.io/badge/ModelScope%20visits-2.6k-624AFF?logo=modelscope&logoColor=white"></a>
</p>

<p align="center">
  <img src="docs/assets/paperseek-banner.png" alt="PaperSeek banner">
</p>

<p align="center">
  <strong>语言：</strong>
  简体中文
  ·
  <a href="README.en.md">English</a>
</p>

## 更新说明

### v0.2.1 - 在线服务与模型路由更新

- 在线版 PaperSeek Service 开放 Semantic Scholar、PubMed 和 Crossref 数据源；Crossref 不需要 API Key。
- 在线版更新模型服务：PaperSeek Service 支持 Auto / Custom 模式，Auto 会自动选择当前可用模型，Custom 可手动选择请求模型、Embedding 模型和预重排方式。
- 补充在线版 PaperSeek Service、Third-party Service 与 Bring your own Key / BYOK 使用边界说明。

### v0.2.0 - 多源检索与多路召回

- 新增 arXiv、Semantic Scholar、PubMed、计算机顶会和 Crossref 数据源。
- 检索流程升级为按数据源生成检索式、意图识别、多轮结果反馈和轻量多路召回预重排。
- 新增轻量多路召回预重排：在 LLM 打分前，按数据源能力综合相关性、高影响力/引用、时效性和本地质量信号，并用 RRF、BM25/词项覆盖和本地 hashing embedding 融合；可选接入 OpenAI-compatible embedding/reranker。
- 更新了在线版的用户注册与登录系统。现在 PaperSeek 默认使用邮箱注册与登录，支持 GitHub、ModelScope、Hugging Face 等站点的 OAuth，并为登录用户提供高达每日 20 次成功检索的免费额度。

### v0.1.1 - 界面语言、历史与学科筛选

- Web UI 支持 `EN` / `中文` 语言切换，语言选择会保存在当前浏览器中，见 [#10](https://github.com/MingfengHong/paperseek/issues/10)。
- 新增本地历史记录保存，记录检索运行、日志事件、检索式和结果，便于回看和恢复结果视图，并为后续阶段断点重跑能力打基础，见 [#2](https://github.com/MingfengHong/paperseek/issues/2)。
- 优化 CSV 与日志导出文件名，使用研究问题主题和本地时间生成更容易辨认的文件名，见 [#3](https://github.com/MingfengHong/paperseek/issues/3)。
- 支持 OpenAlex Field 学科分类筛选，并将所选学科传递给引用扩展，减少结果池偏离所选领域的情况。

## 为什么需要 PaperSeek

文献检索的难点在于判断检索是否完整、准确，尤其是在同义词、跨学科术语和不同数据库检索规则并存时。PaperSeek 把自然语言研究意图转成可执行、可观察、可回看的检索流程，让每一步生成、调整和排序都有迹可循。

PaperSeek 专注于第一轮候选文献发现和元数据整理，帮助研究者把检索过程、候选集和排序依据整理成可复查的数据。

## PaperSeek 会做什么

- **理解研究问题**：从中文或英文研究问题生成适配 OpenAlex、arXiv、Semantic Scholar、PubMed、计算机顶会、Crossref 或 WoS Starter 的检索查询。
- **自动校准检索式**：根据目标结果数量放宽或收窄查询。默认从 5 轮调整开始；如果候选池仍为空、过小或明显超过预重排安全范围，会继续进行有限的自适应调整。
- **结构化候选集**：整理题名、作者、期刊、年份、DOI、摘要、引用数、关键词和链接等元数据。
- **排序并解释相关性**：用 LLM 对候选论文打分，并给出简短评分理由。
- **扩展引用网络**：通过 OpenAlex 扩展高匹配论文的参考文献和被引论文，并展示 Citation Map。
- **按数据源限定领域**：在研究问题下方选择数据源，再使用 OpenAlex Field、WoS Category 或 arXiv Category 等可靠原生过滤；无可靠硬过滤的数据源使用领域文本提示辅助生成检索式。
- **保留可复核过程**：在 Web UI 中查看工作流、结果表、引用图和本地历史记录，并导出 CSV。

## 选择使用方式

- **在线版**：直接访问 [paperseek.xyz](https://www.paperseek.xyz/)。支持 PaperSeek Service、Third-party Service（ModelScope、OpenRouter、Hugging Face）和 Bring your own Key 三种模式；Bring your own Key 即 bring your own provider keys (BYOK)，适合快速试用或自带服务商 Key；详情见 [在线体验版使用说明](docs/online-demo.md)。
- **开源自托管版**：通过 PyPI、源码安装、Docker 或 VPS 运行，适合长期检索、引用扩展和大量请求。
- **ModelScope 创空间**：可在 [PaperSeek 创空间](https://modelscope.cn/studios/HongMingfeng/PaperSeek) 直接使用，也可参考部署指南创建自己的 Docker 创空间。
- **Agent Skill**：可复制 `skills/paperseek/` 到支持 Skill 的 agent 平台；Skill 自带轻量 runtime，可在未安装完整包时执行核心检索。
- **MCP Server**：安装 `paperseek[mcp]` 后运行 `paperseek-mcp`，将文献检索、诊断和历史记录暴露为 MCP 工具，供支持 MCP 的 AI agent 直接调用。

完整使用说明见 [PaperSeek 用户手册](docs/user-manual.md)；部署说明见 [Docker、Vercel 与 ModelScope 部署指南](docs/deployment.md)。

## 快速开始

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

也可以 clone 仓库从源码安装，适合想查看或修改代码的用户：

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

ModelScope 创空间也可通过 Docker 方式部署。点击下方按钮 fork 社区版创空间并创建自己的副本：

<a href="https://modelscope.cn/studios/fork?target=HongMingfeng/PaperSeek"><img src="docs/assets/deploy-modelscope.svg" alt="Deploy to ModelScope" height="32"></a>

长时间搜索、引用扩展和大量请求建议使用 Docker 或 VPS。完整说明见 [部署指南](docs/deployment.md)。

## 最小配置

PaperSeek 至少需要一个 LLM。默认数据源是 OpenAlex；OpenAlex 可匿名测试，但建议申请免费 API Key 以获得更稳定的访问体验。

使用默认 OpenAI provider 时，只需要提供 LLM Key：

```bash
export LLM_API_KEY=your-llm-api-key
paperseek-web
```

切换到 DeepSeek：

```bash
export LLM_PROVIDER=deepseek
export LLM_API_TYPE=openai_chat
export LLM_MODEL=deepseek-v4-flash
export LLM_BASE_URL=https://api.deepseek.com
export LLM_API_KEY=your-llm-api-key
paperseek-web
```

以中国科技云为例：

```bash
export LLM_PROVIDER=cstcloud
export LLM_API_TYPE=openai_chat
export LLM_MODEL=deepseek-v4-flash
export LLM_BASE_URL=https://uni-api.cstcloud.cn/v1
export LLM_API_KEY=your-cstcloud-api-key
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

项目提供 `.env.example`。复制为 `.env` 后先填 `LLM_API_KEY` 即可开始使用；高级参数默认保持注释。不要提交真实 API Key。CLI 和 Web 后端会自动读取当前目录或项目根目录下的 `.env`；已经存在的系统环境变量优先于 `.env`。

## Web UI

PaperSeek 的网页界面分为四个工作区：

| 页面 | 用途 |
| --- | --- |
| Search | 输入研究问题，选择 Discipline Fields，配置数据源、LLM、迭代次数和目标结果数；实时查看工作流与系统日志。 |
| Results | 查看最终排序结果，搜索、过滤、排序、勾选，并导出论文 CSV。 |
| Citation Map | 查看 OpenAlex 引用扩展形成的关系图，按箭头方向探索论文之间的引用关系。 |
| History | 查看本地保存的搜索运行、最终检索式、结果列表和运行事件。 |

![PaperSeek web interface](docs/assets/paperseek-web.png)

如果后端已经通过系统环境变量或 `.env` 配置了 API Key，Web UI 会显示环境中已配置的状态，不会把密钥内容发送到浏览器。Web UI 中填写的 API Key、Base URL 和参数只用于当前浏览器会话，不写入本地配置文件。历史记录会保存运行参数摘要、检索式、日志事件和结果，但不会保存任何 API Key。

Results 导出的 CSV 文件名使用研究问题主题和本地日期，便于区分多次运行。

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

查看本地历史记录：

```bash
paperseek history list
paperseek history show <RUN_ID> --json
paperseek history path
```

保存 CLI 用户级配置：

```bash
paperseek config path
paperseek config set LLM_API_KEY your-llm-api-key
paperseek config list
paperseek config unset LLM_API_KEY
```

环境变量优先于用户级配置。`paperseek config list` 会遮蔽密钥。

Source Filter 支持当前数据源可用的原生过滤值。OpenAlex 可使用 Field ID、字段标签或 `https://openalex.org/fields/<id>` URL；WoS 使用 Web of Science Category；arXiv 使用 `cs.IR`、`cs.LG` 等 category。多个值可以重复传入 `--discipline` / `--discipline-field`，也可以在环境变量中用分号分隔，例如：

```bash
export DISCIPLINE_FIELDS="17;14"
paperseek search "open innovation and digital platforms" --source openalex
```

`--field` / `SEARCH_FIELD` 是自由文本领域提示，主要影响 LLM 生成的检索式；`--discipline` / `DISCIPLINE_FIELDS` 只用于有可靠原生过滤的数据源。OpenAlex 会应用 `primary_topic.field.id`，arXiv 会追加 `cat:`；WoS Starter 目前不支持 `WC=`，所选 Web of Science Category 只作为 LLM 构建 `TS` / `TI` / `SO` 检索式的上下文；Semantic Scholar、PubMed、Crossref 和计算机顶会检索也使用领域文本提示，不做硬过滤。

## 数据源

| 数据源 | 默认状态 | API Key | 适合场景 | 说明 |
| --- | --- | --- | --- | --- |
| OpenAlex | 默认 | 推荐 | 精确检索、摘要、引用数、引用扩展、引用图 | 开放学术元数据库，适合通用文献发现与引用关系探索。 |
| arXiv | 支持 | 不需要 | 预印本、计算机科学、物理、数学、统计等领域 | 使用 arXiv 公共 API Atom feed，返回摘要、分类和 PDF 链接。 |
| Semantic Scholar | 支持 | 可选 | 跨学科学术图谱、引用数、开放 PDF 线索 | 匿名访问适合轻量测试；配置 API Key 可获得更稳定的限额。 |
| PubMed | 支持 | 可选 | 医学、生物医学与生命科学文献 | 使用 NCBI E-utilities；建议配置邮箱和 tool 标识以符合负责任使用要求。 |
| 计算机顶会 | 支持 | 不需要 | ICLR、ICML、NeurIPS、AAAI、NDSS 等计算机顶会论文 | 面向计算机顶会论文发现，不需要数据源 Key。 |
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
| 中国科技云 CSTCloud | `openai_chat` | `deepseek-v4-flash` |
| 阿里云百炼 DashScope | `openai_chat` | `qwen3.6-plus` |
| Kimi Moonshot | `openai_chat` | `kimi-k2.6` |
| 智谱 AI GLM | `openai_chat` | `glm-5.1` |
| 硅基流动 SiliconFlow | `openai_chat` | `deepseek-ai/DeepSeek-V4-Flash` |
| OpenRouter | `openai_chat` | `openai/gpt-5.4-mini` |
| NVIDIA NIM | `openai_chat` | `nvidia/llama-3.3-nemotron-super-49b-v1.5` |
| 火山方舟 | `openai_chat` | `doubao-seed-2-0-mini-260428` |
| 腾讯混元 | `openai_chat` | `hunyuan-turbos-latest` |
| 百度千帆 | `openai_chat` | `ernie-5.0` |
| ModelScope 魔搭 | `openai_chat` | `Qwen/Qwen3-235B-A22B-Instruct-2507` |
| Ollama | `openai_chat` | `qwen3:8b` |
| Custom | `openai_chat` | 空，用户自行填写 |

默认模型用于初始化表单和命令参数示例。实际可用模型以各服务商控制台、账号权限和兼容层为准。

## Embedding 服务商

Embedding 用于 LLM 打分前的轻量多路召回预重排。社区版默认使用 `local`，即纯 Python hashing / BM25 / RRF，不需要外部服务。需要外部 embedding 时，可以在 Web UI 高级设置或环境变量中选择 OpenAI-compatible 服务。

| Provider | 默认模型 | 默认 Base URL |
| --- | --- | --- |
| Local Python | 空 | 空 |
| 中国科技云 CSTCloud | `qwen3-embedding:8b,bge-large-zh:latest` | `https://uni-api.cstcloud.cn/v1` |
| OpenAI | `text-embedding-3-large` | `https://api.openai.com/v1` |
| 阿里云百炼 DashScope | `text-embedding-v4` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| 硅基流动 SiliconFlow | `BAAI/bge-large-zh-v1.5` | `https://api.siliconflow.cn/v1` |
| OpenRouter | `openai/text-embedding-3-small` | `https://openrouter.ai/api/v1` |
| NVIDIA NIM | `nvidia/nv-embedqa-e5-v5` | `https://integrate.api.nvidia.com/v1` |
| 智谱 AI GLM | `embedding-3` | `https://open.bigmodel.cn/api/paas/v4` |
| 火山方舟 | 空 | `https://ark.cn-beijing.volces.com/api/v3` |
| ModelScope API-Inference | `Qwen/Qwen3-Embedding-8B,Qwen/Qwen3-Embedding-4B` | `https://api-inference.modelscope.cn/v1` |
| Custom | 空 | 空 |

如果 `RETRIEVAL_EMBEDDING_API_KEY` 留空，PaperSeek 会复用 `LLM_API_KEY`。未配置外部 embedding 或外部调用失败时，会回退到本地预重排。

## Rerank 服务商

Rerank 是 RRF 后的可选外部重排步骤，默认关闭。社区版默认不需要外部 reranker；只有在你明确配置 provider、model 和可用 API Key 时才会调用。

| Provider | 默认模型 | 默认 Base URL |
| --- | --- | --- |
| Off | 空 | 空 |
| 中国科技云 CSTCloud | `qwen3-reranker:8b` | `https://uni-api.cstcloud.cn/v1` |
| OpenRouter | `jinaai/jina-reranker-v2-base-multilingual` | `https://openrouter.ai/api/v1` |
| NVIDIA NIM | `nv-rerank-qa-mistral-4b:1` | `https://ai.api.nvidia.com/v1/retrieval/nvidia/reranking` |
| 硅基流动 SiliconFlow | `BAAI/bge-reranker-v2-m3` | `https://api.siliconflow.cn/v1` |
| Custom | 空 | 空 |

如果 `RETRIEVAL_RERANKER_API_KEY` 留空，PaperSeek 会复用 `LLM_API_KEY`。外部 reranker 不可用时，系统会保留本地 RRF 顺序继续运行。
ModelScope API-Inference 可用于 LLM 和 Qwen embedding，不作为 Rerank 服务商。NVIDIA NIM 的 embedding 和 rerank 使用不同端点，PaperSeek 会自动按 provider 选择对应请求格式。

> 中国科技云 CSTCloud 的 LLM、Embedding 和 Rerank 均按 OpenAI-compatible 方式接入，Base URL 统一为 `https://uni-api.cstcloud.cn/v1`。获取 Key 可打开 [中国科技云 API Keys](https://uni-api.cstcloud.cn/api_keys)，登录中国科技云统一认证后按页面要求提交申请信息；中国科学院院内用户可使用中国科技云通行证登录，通行证通常为院邮箱账号及密码。接口说明见 [中国科技云大模型 API 接口使用手册](https://uni-api.cstcloud.cn/doc/llm/)，其中包含 Chats、Embeddings 和 Rerank 文档。

## 工作流

一次搜索通常包含四步：

1. **Query Generation**：LLM 根据研究问题、可选领域文本提示和源特定过滤生成初始查询。
2. **Source Search**：请求所选数据源（OpenAlex、arXiv、Semantic Scholar、PubMed、计算机顶会、Crossref 或 WoS Starter），并记录 HTTP 状态和命中数量。
3. **Query Refinement**：若命中数过少或过多，LLM 调整查询并继续下一轮。
4. **Ranking & Results**：将候选池交给 LLM 统一评分，输出前若干条结果。

如果启用 OpenAlex 引用扩展，PaperSeek 会从相关性、高被引和最新性三类 seed 中默认选择最多 30 篇：高相关 seed 同时扩展参考文献和被引论文，高被引 seed 重点扩展参考文献，最新 seed 重点扩展被引论文。扩展记录会合并进同一个候选池，再统一预重排和 LLM 打分。

在进入 LLM 打分前，PaperSeek 会先进行轻量多路召回预重排：按数据源能力综合相关性、高引用/影响力、时效性和本地质量等信号，去重后用 RRF 融合召回排名，并叠加纯 Python hashing embedding cosine、BM25 和词项覆盖分数。默认 LLM 前融合候选池上限为 `3000`。社区版默认不依赖外部 embedding 服务；如需外部增强，可在 Web UI 高级设置中从 Local Python、中国科技云、OpenAI、阿里云百炼、硅基流动、OpenRouter、NVIDIA NIM、智谱、火山方舟、ModelScope 或自定义端点中选择 embedding 服务，其中 ModelScope API-Inference 仅使用 `Qwen/Qwen3-Embedding-8B` 和 `Qwen/Qwen3-Embedding-4B`。如果用户自行配置外部 embedding/reranker，也可使用中国科技云的 `qwen3-embedding:8b`、`bge-large-zh:latest`、OpenRouter 的 embedding/rerank 模型或 NVIDIA NIM 的 `nvidia/nv-embedqa-e5-v5`、`nv-rerank-qa-mistral-4b:1` 等模型，配置多个模型时会按顺序 fallback，失败时会回退到本地 RRF 顺序。

候选池较大时，LLM 排序会自动分批并发执行。默认批大小为 `8`、并发为 `16`；超过 16 篇候选论文时会自适应放大批大小。若一个或多个批次失败，系统会按 `16 -> 8 -> 4` 降低并发重试；如果并发 `4` 仍失败，只回退失败批次，不会使整次检索失败。ranking 批次默认使用 `RANKING_LLM_TIMEOUT_SECONDS=60`，超时后回退本地预排序，避免长时间端点等待拖断整次检索。高级用户仍可手动把 `RANKING_CONCURRENCY` 设为 `32`，此时会按 `32 -> 16 -> 8 -> 4` 降级。

`TARGET_MAX` 用于指导检索式收窄或放宽，不是最终展示的硬上限。LLM 打分前最多保留 `RANKING_CANDIDATE_LIMIT` 条候选，默认 `256`。最终结果少于 50 条时全部展示；结果较多时至少展示前 50 条，如果 5 分及以上候选超过 50 条，则展示全部高分候选。

## 引用图

Citation Map 使用箭头表示引用方向：

```text
A -> B  表示 A 引用了 B
```

图中节点来自最终结果和 OpenAlex 引用扩展记录。你可以拖动节点、缩放和平移画布，并查看节点详情。引用图适合发现关键词检索遗漏的经典文献、相邻主题和近期延伸研究。

## 环境变量

大多数参数已有代码默认值，复制 `.env.example` 后通常只需要填写模型服务 Key。高级参数保持注释即可，除非你明确要覆盖默认行为。

### 必须配置

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `LLM_API_KEY` | 空 | LLM API Key。使用 Ollama 时可留空。 |
| `WOS_API_KEY` | 空 | 仅当 `DATA_SOURCE=wos` 时需要。 |

### 常用可选配置

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `LLM_PROVIDER` | `openai` | LLM 服务商，例如 `openai`、`deepseek`、`cstcloud`、`anthropic`、`openrouter`、`nvidia`、`modelscope` 或 `ollama`。 |
| `LLM_API_TYPE` | 由 provider 决定 | `openai_responses`、`openai_chat` 或 `anthropic_messages`。 |
| `LLM_MODEL` | 由 provider 决定 | 模型名称。 |
| `LLM_BASE_URL` | 由 provider 决定 | API Base URL。 |
| `DATA_SOURCE` | `openalex` | `openalex`、`arxiv`、`semanticscholar`、`pubmed`、`paperhub`、`crossref` 或 `wos`。 |
| `OPENALEX_API_KEY` | 空 | OpenAlex API Key，推荐填写以获得更稳定的请求体验。 |
| `OPENALEX_EMAIL` | 空 | OpenAlex 联系邮箱。 |
| `SEMANTIC_SCHOLAR_API_KEY` | 空 | Semantic Scholar API Key，可选；匿名访问适合轻量测试。 |
| `PUBMED_EMAIL` / `PUBMED_TOOL` | 空 / `paperseek` | PubMed / NCBI 责任使用标识。 |
| `PUBMED_API_KEY` | 空 | NCBI API Key，可选；提高 PubMed E-utilities 请求限额。 |
| `CROSSREF_EMAIL` | 空 | Crossref polite pool 邮箱。 |

### 高级配置

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `SEARCH_FIELD` | 空 | 自由文本学科或领域提示。 |
| `DISCIPLINE_FIELDS` | 空 | OpenAlex Field、WoS Category 或 arXiv Category 等原生过滤值；多个值建议用分号分隔。其它数据源使用 `SEARCH_FIELD` 文本提示。 |
| `TARGET_MIN` / `TARGET_MAX` | `5` / `50` | 目标结果数量范围。 |
| `MAX_ITERATIONS` | `5` | 最大查询调整轮数。 |
| `EXPAND_CITATIONS` | `true` | 是否启用 OpenAlex 引用扩展。 |
| `FETCH_ABSTRACTS` | `false` | 是否尝试从外部 DOI 元数据补摘要。 |
| `CITATION_SEED_COUNT` / `CITATION_PER_SEED` / `CITATION_MAX_RECORDS` | `30` / `4` / `160` | 引用扩展规模控制。 |
| `CITATION_DEPTH` | `2` | OpenAlex 引用扩展遍历层数。 |
| `RANKING_BATCH_SIZE` / `RANKING_CONCURRENCY` | `8` / `16` | LLM 排序批大小和并发数。 |
| `LLM_MAX_TOKENS` / `LLM_TIMEOUT_SECONDS` | `2048` / `180` | LLM 输出长度和常规单次请求超时。 |
| `RANKING_LLM_TIMEOUT_SECONDS` | `60` | 仅用于 LLM 排序批次的超时；超时后回退本地预排序。 |
| `RETRIEVAL_POOL_MAX` / `RETRIEVAL_POOL_MIN` | `3000` / `5` | LLM 打分前的融合候选池范围。 |
| `RETRIEVAL_LANE_LIMIT` / `RETRIEVAL_RRF_K` | `1000` / `60` | 每路召回上限和 RRF 融合常数。 |
| `RETRIEVAL_EMBEDDING_PROVIDER` | `local` | 社区版默认使用本地纯 Python 预重排；可改为 OpenAI-compatible embedding 服务。 |
| `RETRIEVAL_EMBEDDING_MODEL` | `qwen3-embedding:8b,bge-large-zh:latest` | 外部 embedding 模型列表。 |
| `RETRIEVAL_RERANKER_PROVIDER` / `RETRIEVAL_RERANKER_MODEL` | 空 / `qwen3-reranker:8b` | RRF 后的可选外部 reranker。 |
| `RETRIEVAL_CROSSREF_ENRICHMENT` | `false` | 可选 Crossref DOI 元数据补全。 |
| `PAPERSEEK_HISTORY_ENABLED` | `true` | 是否启用本地历史记录。 |
| `PAPERSEEK_TIMEZONE` | `Asia/Shanghai` | CLI 和后端 fallback 时间戳时区；Web UI 优先使用浏览器时区。 |
| `PAPERSEEK_DATA_DIR` / `PAPERSEEK_HISTORY_DB` | `~/.paperseek` / `~/.paperseek/paperseek.db` | 本地数据目录和历史数据库路径。 |

## API 获取方式

### OpenAlex

OpenAlex 可匿名访问，但推荐配置免费 API Key：

1. 打开 [OpenAlex](https://openalex.org/) 并注册账号。
2. 进入 [OpenAlex API settings](https://openalex.org/settings/api)。
3. 复制 API Key。
4. 在 Web UI 填写 `OpenAlex API Key`，或设置 `OPENALEX_API_KEY`。

### Semantic Scholar

Semantic Scholar 可匿名访问；长期使用或请求量较高时建议申请 API Key：

1. 打开 [Semantic Scholar API](https://www.semanticscholar.org/product/api) 页面。
2. 进入 API Key 申请入口，按页面要求填写姓名、邮箱、用途等信息。
3. 提交申请后等待 Semantic Scholar 发送或启用 API Key。
4. 在 Web UI 填写 `Semantic Scholar API Key`，或设置 `SEMANTIC_SCHOLAR_API_KEY`。

### PubMed / NCBI

PubMed 使用 NCBI E-utilities。建议始终配置联系邮箱和 tool 名称；如果需要更高请求限额，可在 NCBI 账号中生成 API Key：

1. 打开 [NCBI](https://www.ncbi.nlm.nih.gov/) 并注册或登录账号。
2. 进入账号设置页面，找到 API Key 管理区域。
3. 点击创建 API Key 并复制生成的 key。
4. 在 Web UI 填写 `PubMed API Key`，或设置 `PUBMED_API_KEY`。
5. 同时设置 `PUBMED_EMAIL` 和 `PUBMED_TOOL`，例如 `paperseek`。

### Crossref

Crossref REST API 通常不需要 API Key。建议设置邮箱进入 polite pool：

```bash
export CROSSREF_EMAIL=you@example.org
```

如果需要更高限额、优先支持或生产级 SLA，可以了解 Crossref Metadata Plus。PaperSeek 使用 Crossref 公共/Polite REST API 路径。

### arXiv 与计算机顶会

- arXiv 不需要 API Key，适合预印本和 arXiv 覆盖学科的快速发现。
- 计算机顶会检索不需要 API Key。

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

## Python API 与 core

社区版安装包已经内置可复用核心模块 `paperseek_core`，不需要额外安装单独的 `paperseek-core` 仓库依赖。常规用户和下游代码建议从 `paperseek` 导入稳定入口：

```python
from paperseek import PaperSeekAgent
```

`LiteratureSearchAgent` 和 `WosSearchAgent` 仍保留为兼容旧代码的别名，新代码请使用 `PaperSeekAgent`。

## Agent Skill

仓库包含一个可选的 PaperSeek Skill：

```text
skills/paperseek/
```

它用于指导支持 Skill 的 AI agent 正确调用 PaperSeek，包括数据源选择、配置诊断、JSON 结果解析和引用图边界。Skill 使用 progressive disclosure：`SKILL.md` 保持简短，详细命令契约放在 `references/`。

这个 Skill **不会随 Python 包自动安装**。如果需要在 agent 平台中使用，可以手动复制或链接 `skills/paperseek/` 到对应平台的 Skill 目录。

Skill 中的 launcher 与自包含 runtime：

```text
skills/paperseek/scripts/paperseek.py
skills/paperseek/scripts/paperseek_skill_runtime.py
```

单独发布 Skill 时，复制 `skills/paperseek/` 即可。`paperseek.py` 会优先调用完整 PaperSeek 包；如果未安装包，会回退到 `paperseek_skill_runtime.py`，使用 Python 标准库直接完成 OpenAlex、arXiv、Semantic Scholar、PubMed、计算机顶会、Crossref 和带 key 的 WoS Starter 核心文献检索。Web UI、引用图和完整历史管理仍需要安装完整包。

## MCP Server

PaperSeek 提供可选的 MCP（Model Context Protocol）服务器，将文献检索、配置诊断、数据源测试和历史记录暴露为 MCP 工具，供支持 MCP 的 AI agent 直接调用。

安装 MCP 可选依赖（需要 Python 3.10+）：

```bash
python -m pip install "paperseek[mcp]"
```

启动 MCP 服务器（stdio 传输）：

```bash
paperseek-mcp
```

配置方式与 CLI 和 Web UI 完全一致，通过环境变量或 `.env` 设置 LLM 和数据源参数。API Key 不会暴露给 LLM，仅由 MCP 服务器进程持有。

可用的 MCP 工具：

| 工具 | 用途 |
| --- | --- |
| `search_papers` | 输入研究问题，执行完整的 LLM 检索工作流并返回排序结果 |
| `check_config` | 检查 PaperSeek 配置（数据源、LLM、API Key）是否就绪 |
| `smoke_test` | 对数据源发起最小真实请求，测试连通性 |
| `list_sources` | 列出所有支持的数据源及其能力 |
| `list_history` | 列出本地保存的搜索运行记录 |
| `get_history_run` | 查看某次搜索运行的完整详情 |

在 Claude Desktop 等支持 MCP 的客户端中配置：

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

也可以使用 `python -m paperseek.mcp_server` 启动。MCP 服务器复用与 CLI 相同的 `PaperSeekAgent` 核心逻辑，搜索结果会自动保存到本地历史记录。

## 项目状态

PaperSeek 当前处于 alpha 阶段。CLI、Web UI、OpenAlex、arXiv、Semantic Scholar、PubMed、计算机顶会、Crossref、引用扩展、CSV 导出、Skill 和 MCP Server 已可用于日常文献检索与候选集整理。

欢迎贡献：

- 新数据源适配器。
- 更稳健的查询生成与排序提示词。
- 更好的引用图交互。
- Web API、CLI、provider parsing 和导出行为测试。
- 文档、示例和错误诊断改进。

贡献前可阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。安全问题请参考 [SECURITY.md](SECURITY.md)。

## 致谢

PaperSeek 的设计和实现参考了以下开源项目：

- [dr-dumpling/paper-search-cli](https://github.com/dr-dumpling/paper-search-cli/)：参考 CLI 使用方式与文献检索工作流设计。
- [666ghj/MiroFish](https://github.com/666ghj/MiroFish)：参考 Web 前端界面的左右分栏和工作流展示风格。
- [clarivate/wosstarter_python_client](https://github.com/clarivate/wosstarter_python_client)：参考 Web of Science Starter API 的客户端调用方式。
- [Yupu-Wang/paper-hub](https://github.com/Yupu-Wang/paper-hub)：经作者同意后集成，用于提供计算机顶会检索支持。
- [Lloyd-Jahn/openclaw-paper-search](https://github.com/Lloyd-Jahn/openclaw-paper-search)：参考文献搜索工具的组织方式。

## 开源协议

PaperSeek 使用 [Apache License 2.0](LICENSE) 开源。
