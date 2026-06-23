# 部署指南

PaperSeek Web UI 常见部署方式有三种：

- **Docker / Docker Compose**：推荐用于完整 Web UI、长时间搜索、流式日志、引用扩展和自托管场景。
- **Vercel**：适合快速演示和轻量使用。Vercel 可以运行 FastAPI Web UI，但它是 serverless function 运行时，长搜索可能触发函数时长限制。
- **ModelScope Studio**：适合在魔搭创空间中发布可访问的 Docker 版 Web UI。PaperSeek 已包含 `Dockerfile` 和 `ms_deploy.json`，可按创空间 Git 流程推送部署。

如果只是试用 PaperSeek，可以直接访问在线体验版：

```text
https://www.paperseek.xyz/
```

在线体验版的 Quick Start、ModelScope Service、Use your own API、登录权限、ModelScope 额度和历史记录说明见 [在线体验版用户手册](online-demo.md)。

## Docker

Docker 是 PaperSeek 推荐的生产式部署方式。容器中使用 Uvicorn 运行 FastAPI 应用，默认监听 `7860`；下面的本地示例把它映射到宿主机 `8765`。

### 构建并运行

```bash
docker build -t paperseek .
docker run --rm -p 8765:7860 \
  -e LLM_PROVIDER=deepseek \
  -e LLM_API_TYPE=openai_chat \
  -e LLM_MODEL=deepseek-v4-flash \
  -e LLM_BASE_URL=https://api.deepseek.com \
  -e LLM_API_KEY=your-llm-api-key \
  paperseek
```

打开：

```text
http://127.0.0.1:8765/
```

### Docker Compose

复制示例环境文件：

```bash
cp .env.example .env
```

编辑 `.env`，填入模型服务商和数据源配置。然后运行：

```bash
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

停止服务：

```bash
docker compose down
```

### 环境变量

Docker 镜像接受与 CLI 和 Web UI 后端相同的环境变量：

| 变量 | 示例 |
| --- | --- |
| `PORT` | `7860` |
| `DATA_SOURCE` | `openalex` |
| `LLM_PROVIDER` | `deepseek` |
| `LLM_API_TYPE` | `openai_chat` |
| `LLM_MODEL` | `deepseek-v4-flash` |
| `LLM_BASE_URL` | `https://api.deepseek.com` |
| `LLM_API_KEY` | `your-llm-api-key` |
| `OPENALEX_API_KEY` | `your-openalex-key` |
| `CROSSREF_EMAIL` | `you@example.org` |
| `WOS_API_KEY` | `your-wos-key` |
| `DISCIPLINE_FIELDS` | `17;14` |
| `RANKING_BATCH_SIZE` | `8` |
| `RANKING_CONCURRENCY` | `4` |
| `LLM_TIMEOUT_SECONDS` | `180` |

如果你不想在服务器端配置密钥，用户也可以在 Web UI 中为当前浏览器会话填写 LLM Key 和数据源 Key。PaperSeek 不会保存这些本次会话密钥。

`DISCIPLINE_FIELDS` 用于设置服务器端默认选中的 Discipline Fields。多个 OpenAlex Field ID、标签或 URL 建议用分号分隔，例如 `17;14` 或 `Computer Science;Business, Management and Accounting`；用户仍可在 Web UI 中按本次会话修改选择。

`RANKING_BATCH_SIZE` 和 `RANKING_CONCURRENCY` 控制 LLM 相关性排序阶段的批大小与并发。候选池较大时，PaperSeek 会自适应放大批大小，使批次数接近并发数；单个排序批次失败时，只回退该批次为源顺序零分，不会使整次检索失败。`LLM_TIMEOUT_SECONDS` 控制单次 LLM 请求超时，默认 180 秒，最小 30 秒。

### 反向代理

如果通过 Nginx、Caddy、Traefik 或其他反向代理公开部署，把 HTTP 流量代理到：

```text
http://127.0.0.1:8765
```

公开访问时应使用 HTTPS。Web UI 表单允许用户输入 API Key，如果实例不是面向所有人开放，建议同时加访问控制。

## ModelScope Studio

ModelScope 创空间支持 Docker 应用，适合把 PaperSeek 发布成国内可访问的在线 Web UI。它和 Vercel 的按钮部署不同：ModelScope 当前流程通常需要先创建创空间，再把代码推送到该创空间分配的 Git 仓库。PaperSeek 已经把 Docker 部署所需文件放在根目录，因此用户只需要完成创空间创建、环境变量配置和 Git 推送。

<a href="https://modelscope.cn/docs/studios/create"><img src="./assets/deploy-modelscope.svg" alt="Deploy to ModelScope" height="32"></a>

### 适用场景

- 需要把 PaperSeek 放在 ModelScope 创空间中公开演示。
- 需要使用 Docker 运行 FastAPI Web UI。
- 希望用户通过浏览器访问，而不要求他们本地安装 Python。
- 可以接受创空间构建、休眠、并发和平台资源策略带来的限制。

长时间检索、稳定并发、私有数据或生产级服务仍建议使用自己的 Docker / VPS 部署。

### 创空间部署步骤

1. 登录 ModelScope，进入 [创空间创建与搭建](https://modelscope.cn/docs/studios/create)。
2. 创建一个新的创空间。部署类型选择 Docker；如果页面先创建空白创空间，也可以创建后通过 Git 推送代码。
3. 在创空间的“空间文件”或“空间内容”页面复制 Git 地址。通常形如：

   ```text
   https://www.modelscope.cn/studios/<namespace>/<studio-name>.git
   ```

4. 在本地准备 PaperSeek 代码并添加创空间远程：

   ```bash
   git clone https://github.com/MingfengHong/paperseek.git
   cd paperseek
   git remote add modelscope https://oauth2:<MODELSCOPE_TOKEN>@www.modelscope.cn/studios/<namespace>/<studio-name>.git
   ```

   将 `<MODELSCOPE_TOKEN>`、`<namespace>` 和 `<studio-name>` 替换为你自己的访问令牌和创空间路径。不要把带 token 的远程地址提交到仓库。

5. 推送到创空间仓库。很多创空间默认分支是 `master`，可以显式把 GitHub 的 `main` 推到创空间 `master`：

   ```bash
   git push modelscope main:master
   ```

6. 在创空间设置中添加环境变量。至少需要配置一个 LLM：

   - `LLM_PROVIDER`
   - `LLM_API_TYPE`
   - `LLM_MODEL`
   - `LLM_BASE_URL`
   - `LLM_API_KEY`

   推荐同时配置：

   - `OPENALEX_API_KEY`
   - `CROSSREF_EMAIL`
   - `WOS_API_KEY`（如果使用 Web of Science Starter）
   - `DISCIPLINE_FIELDS`（如果希望设置默认学科字段）

7. 在创空间页面点击发布、上线或深度重启。构建完成后访问创空间页面测试 Web UI。

### ModelScope 相关文件

| 文件 | 用途 |
| --- | --- |
| `Dockerfile` | 构建 PaperSeek Docker 镜像并启动 `paperseek-web`。 |
| `ms_deploy.json` | 告诉 ModelScope 使用 Docker SDK、监听 `7860` 端口并选择 CPU 资源规格。 |
| `.env.example` | 本地参考环境变量，不应直接提交真实密钥。 |

如果构建失败，先在创空间设置页查看构建日志。常见问题包括没有正确识别 `Dockerfile`、环境变量缺失、依赖安装超时或端口与 `ms_deploy.json` 不一致。

## ModelScope API-Inference

PaperSeek 支持把 ModelScope API-Inference 作为 OpenAI Chat Completions 兼容模型服务商：

```bash
export LLM_PROVIDER=modelscope
export LLM_API_TYPE=openai_chat
export LLM_MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507
export LLM_BASE_URL=https://api-inference.modelscope.cn/v1
export LLM_API_KEY=your-modelscope-token
```

默认 Base URL 和模型可以在 Web UI 中修改，也可以通过 CLI 参数覆盖。

## Vercel

Vercel 可以通过 Python runtime 部署 PaperSeek FastAPI 应用，适合演示、快速测试和轻量 Web UI 访问。

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FMingfengHong%2Fpaperseek)

### Vercel 上可用的功能

- PaperSeek Web UI。
- `/api/*` 下的 FastAPI 路由。
- FastAPI 应用托管的静态前端文件。
- Web UI 中按会话填写 API Key。
- 函数时长允许范围内的流式搜索日志。

### Vercel 限制

Vercel 使用 serverless function 模型。PaperSeek 搜索可能包含多次 LLM 调用、数据源请求和引用扩展。长时间或高负载搜索更适合 Docker 或 VPS。

常见限制包括：

- 搜索请求受函数最大执行时长限制。
- 冷启动会增加延迟。
- 很长的引用扩展可能超时。
- Serverless function 不适合持久后台任务。
- Vercel 部署日志和函数日志与 PaperSeek 页面中的 System Dashboard 是两套日志。

PaperSeek 通过根目录 `app.py` 让 Vercel 自动识别 FastAPI 应用。启用 Fluid Compute 时，Hobby 项目的默认和最大函数时长通常是 300 秒；实际限制取决于你的 Vercel 计划和项目设置。

### 从 GitHub 部署到 Vercel

1. 把仓库推送到 GitHub。
2. 点击上方 Deploy 按钮，或在 Vercel 中导入仓库。
3. 保持默认项目设置。
4. 如果希望服务器端提供默认配置，添加环境变量：
   - `LLM_PROVIDER`
   - `LLM_API_TYPE`
   - `LLM_MODEL`
   - `LLM_BASE_URL`
   - `LLM_API_KEY`
   - `OPENALEX_API_KEY`
   - `CROSSREF_EMAIL`
   - `WOS_API_KEY`
   - `DISCIPLINE_FIELDS`
5. 点击部署。

如果不配置服务器端密钥，用户仍可以在 Web UI 中按会话填写 API Key。

### 使用 Vercel CLI

安装 Vercel CLI 后运行：

```bash
vercel
```

生产部署：

```bash
vercel --prod
```

本地 Vercel 开发：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
vercel dev
```

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
vercel dev
```

### Vercel 相关文件

PaperSeek 包含：

| 文件 | 用途 |
| --- | --- |
| `app.py` | Vercel FastAPI 自动识别入口，暴露 `paperseek.web_app.app` 为 `app`。 |
| `api/index.py` | 兼容 Python 入口，同样暴露 FastAPI `app`。 |
| `vercel.json` | 最小项目配置，故意不使用 `functions` pattern，避免 Vercel 函数匹配失败。 |
| `requirements.txt` | Vercel Python 依赖。 |

## Docker、ModelScope 还是 Vercel

| 场景 | 推荐方式 |
| --- | --- |
| 重复研究使用的完整 Web UI | Docker |
| 长时间搜索和引用扩展 | Docker |
| 私有实验室或服务器部署 | Docker + HTTPS 反向代理 |
| 国内公开演示和创空间分发 | ModelScope Studio |
| 快速演示链接 | Vercel |
| 用户只在浏览器会话中输入 Key | Docker、ModelScope Studio 或 Vercel |
| 需要稳定长任务行为 | Docker |

## 健康检查

部署后测试：

```bash
curl http://127.0.0.1:8765/api/sources
```

Vercel 部署请替换域名：

```bash
curl https://your-project.vercel.app/api/sources
```

应返回包含 `openalex`、`crossref` 和 `wos` 的 JSON 数据源列表。

---

# Deployment Guide (English)

PaperSeek Web UI is commonly deployed in three ways:

- **Docker / Docker Compose**: recommended for the full Web UI experience, long searches, streaming logs, citation expansion, and self-hosted control.
- **Vercel**: convenient for demos and lightweight use. It can run the FastAPI Web UI, but long searches may hit serverless function duration limits.
- **ModelScope Studio**: useful for publishing a Docker-based PaperSeek Web UI on ModelScope. PaperSeek includes both `Dockerfile` and `ms_deploy.json`.

## Docker

Build and run:

```bash
docker build -t paperseek .
docker run --rm -p 8765:7860 \
  -e LLM_PROVIDER=deepseek \
  -e LLM_API_TYPE=openai_chat \
  -e LLM_MODEL=deepseek-v4-flash \
  -e LLM_BASE_URL=https://api.deepseek.com \
  -e LLM_API_KEY=your-llm-api-key \
  paperseek
```

Open:

```text
http://127.0.0.1:8765/
```

Docker Compose:

```bash
cp .env.example .env
docker compose up --build
```

The Docker image accepts the same environment variables as the CLI and Web UI backend, including `DISCIPLINE_FIELDS` for default Discipline Field selections such as `17;14`. If you do not want server-side secrets, users can enter LLM and data-source keys in the Web UI for the current browser session.

## ModelScope Studio

ModelScope Studio deployment is supported through Docker. It is not the same as Vercel's prefilled one-click clone flow: users normally create a Studio first, then push code to the Git remote assigned by ModelScope. PaperSeek is ready for that flow because the root directory already contains `Dockerfile` and `ms_deploy.json`.

<a href="https://modelscope.cn/docs/studios/create"><img src="./assets/deploy-modelscope.svg" alt="Deploy to ModelScope" height="32"></a>

Basic flow:

1. Create a ModelScope Studio and choose Docker deployment.
2. Copy the Studio Git remote, usually:

   ```text
   https://www.modelscope.cn/studios/<namespace>/<studio-name>.git
   ```

3. Push PaperSeek to that remote:

   ```bash
   git clone https://github.com/MingfengHong/paperseek.git
   cd paperseek
   git remote add modelscope https://oauth2:<MODELSCOPE_TOKEN>@www.modelscope.cn/studios/<namespace>/<studio-name>.git
   git push modelscope main:master
   ```

4. Set environment variables in the Studio settings, including at least `LLM_PROVIDER`, `LLM_API_TYPE`, `LLM_MODEL`, `LLM_BASE_URL`, and `LLM_API_KEY`. Add `OPENALEX_API_KEY`, `CROSSREF_EMAIL`, `WOS_API_KEY`, or `DISCIPLINE_FIELDS` as needed.
5. Publish or restart the Studio and test the Web UI.

Do not commit `.env` files or token-bearing Git remotes. If the build fails, check the Studio build logs first and confirm that the Docker port matches `ms_deploy.json`.

## Vercel

Vercel can deploy the FastAPI app through the Python runtime:

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FMingfengHong%2Fpaperseek)

Useful files:

| File | Purpose |
| --- | --- |
| `app.py` | Root FastAPI entrypoint for Vercel auto-detection. |
| `api/index.py` | Compatibility Python entrypoint. |
| `vercel.json` | Minimal Vercel configuration without fragile `functions` patterns. |
| `requirements.txt` | Python dependencies for Vercel. |

Vercel is good for demos and lightweight use. For repeated research work, long searches, or citation expansion, use Docker or a VPS.

You can set server-side environment defaults on Vercel as well, including `DISCIPLINE_FIELDS` for default Discipline Field selections. Users can still override those selections in the Web UI for a single browser session.

## Health check

```bash
curl http://127.0.0.1:8765/api/sources
```

For Vercel:

```bash
curl https://your-project.vercel.app/api/sources
```
