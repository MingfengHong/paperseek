# Deployment

PaperSeek Web UI can be deployed in two common ways:

- **Docker / Docker Compose**: recommended for the full Web UI experience, including long searches, streaming logs, citation expansion, and self-hosted control.
- **Vercel**: convenient one-click deployment for demos and lightweight use. It can run the FastAPI Web UI, but it uses a serverless function runtime, so long-running searches may hit function duration limits.

## Docker

Docker is the recommended production-style deployment path for PaperSeek. It runs the FastAPI app with Uvicorn in a container. The container listens on `7860` by default; local examples map it to host port `8765`.

### Build and run

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

### Docker Compose

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your model provider settings. Then run:

```bash
docker compose up --build
```

Open:

```text
http://127.0.0.1:8765/
```

Run in the background:

```bash
docker compose up -d --build
```

View logs:

```bash
docker compose logs -f
```

Stop:

```bash
docker compose down
```

### Environment variables

The Docker image accepts the same environment variables as the CLI and Web UI backend:

| Variable | Example |
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

If you prefer not to set secrets on the server, users can still enter LLM and data-source keys in the Web UI for the current browser session. Those values are not saved by PaperSeek.

### Reverse proxy

For public deployment behind Nginx, Caddy, Traefik, or another reverse proxy, proxy HTTP traffic to:

```text
http://127.0.0.1:8765
```

Keep the service behind HTTPS when exposed publicly. The Web UI accepts API keys in browser form fields, so public deployments should use TLS and an access-control layer if the instance is not intended for everyone.

## ModelScope API-Inference

PaperSeek supports ModelScope API-Inference as an OpenAI Chat Completions-compatible provider:

```bash
export LLM_PROVIDER=modelscope
export LLM_API_TYPE=openai_chat
export LLM_MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507
export LLM_BASE_URL=https://api-inference.modelscope.cn/v1
export LLM_API_KEY=your-modelscope-token
```

The default base URL and model can be edited in the Web UI or overridden through CLI flags.

## Vercel

Vercel can deploy the PaperSeek FastAPI app through the Python runtime. This is convenient for demos, quick tests, and one-click Web UI access.

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2FMingfengHong%2Fpaperseek)

### What works on Vercel

- The PaperSeek Web UI.
- FastAPI routes under `/api/*`.
- Static frontend files served by the FastAPI app.
- Session-only API key entry through the Web UI.
- Streaming search logs when the function remains within platform limits.

### Limitations

Vercel runs the app as a serverless function. PaperSeek searches can involve multiple LLM calls, data-source requests, and citation expansion. For long or heavy searches, Docker or a VPS deployment is more reliable.

Typical Vercel caveats:

- Function max duration applies to search requests.
- Cold starts may add latency.
- Very long citation expansion can time out.
- Serverless functions are not designed for persistent background workers.
- Vercel deployment logs and function logs are separate from PaperSeek's in-app System Dashboard.

PaperSeek uses Vercel's FastAPI framework preset through the root `app.py` entrypoint. With Fluid Compute enabled by default, Hobby deployments have a 300-second default and maximum function duration. Your actual limit depends on your Vercel plan and project settings.

### Deploy from GitHub

1. Push this repository to GitHub.
2. Click the deploy button above, or open Vercel and import the repository.
3. Keep the default project settings.
4. Add environment variables if you want server-side defaults:
   - `LLM_PROVIDER`
   - `LLM_API_TYPE`
   - `LLM_MODEL`
   - `LLM_BASE_URL`
   - `LLM_API_KEY`
   - `OPENALEX_API_KEY`
   - `CROSSREF_EMAIL`
   - `WOS_API_KEY`
5. Deploy.

The app can also be used without server-side keys if users fill API keys in the Web UI per session.

### Deploy with Vercel CLI

Install Vercel CLI, then run:

```bash
vercel
```

For production:

```bash
vercel --prod
```

Local Vercel development:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
vercel dev
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
vercel dev
```

### Vercel files

PaperSeek includes:

| File | Purpose |
| --- | --- |
| `app.py` | Root FastAPI entrypoint for Vercel framework auto-detection; it exposes `paperseek.web_app.app` as `app`. |
| `api/index.py` | Compatibility Python entrypoint that also exposes `paperseek.web_app.app`. |
| `vercel.json` | Minimal project configuration. It intentionally avoids `functions` patterns because Vercel auto-detects the FastAPI app. |
| `requirements.txt` | Vercel Python dependencies. |

## Choosing Docker or Vercel

| Scenario | Recommended deployment |
| --- | --- |
| Full Web UI for repeated research use | Docker |
| Long searches with citation expansion | Docker |
| Private lab or server deployment | Docker behind HTTPS |
| Quick demo link | Vercel |
| Users enter keys only in browser session | Docker or Vercel |
| Need predictable long-running behavior | Docker |

## Health check

After deployment, test:

```bash
curl http://127.0.0.1:8765/api/sources
```

For Vercel, replace the host:

```bash
curl https://your-project.vercel.app/api/sources
```

You should receive JSON listing `openalex`, `crossref`, and `wos`.
