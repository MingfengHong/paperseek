from pathlib import Path
import json
from queue import Queue
import re
from threading import Thread
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from paperseek.client import ApiException
from paperseek.config import AgentConfig, default_api_type, default_base_url, default_model
from paperseek.diagnostics import run_doctor, smoke_source
from paperseek.history import HistoryStore, result_payload_from_search_result, safe_search_params_from_config
from paperseek.llm_client import LLMError, create_llm_client
from paperseek.providers import ProviderError
from paperseek.search_agent import WosSearchAgent
from paperseek.source_metadata import list_source_metadata, supported_source_ids


STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="PaperSeek", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


FIELD_LABELS = {
    "question": "Research Question",
    "data_source": "Data Source",
    "wos_api_key": "WoS API Key",
    "openalex_api_key": "OpenAlex API Key",
    "openalex_email": "OpenAlex Email",
    "crossref_email": "Crossref Email",
    "llm_api_key": "LLM API Key",
    "llm_api_type": "LLM API Type",
    "expand_citations": "Expand Citations",
    "initial_query": "Initial Query",
    "search_accept_max_records": "Source Candidate Cap",
    "citation_max_depth": "Citation Max Depth",
    "citation_relevance_threshold": "Citation Relevance Threshold",
    "target_min": "Min Results",
    "target_max": "Max Results",
    "max_iterations": "Iterations",
}


class SearchRequest(BaseModel):
    question: str = Field(min_length=1)
    data_source: str = "openalex"
    wos_api_key: Optional[str] = ""
    openalex_api_key: Optional[str] = ""
    openalex_email: Optional[str] = ""
    crossref_email: Optional[str] = ""
    llm_api_key: Optional[str] = ""
    llm_provider: str = "openai"
    llm_api_type: str = ""
    llm_model: Optional[str] = None
    llm_base_url: Optional[str] = None
    wos_db: str = "WOS"
    search_field: Optional[str] = ""
    initial_query: Optional[str] = ""
    client_timezone: Optional[str] = ""
    fetch_abstracts: bool = False
    expand_citations: bool = True
    search_accept_max_records: int = Field(default=1000, ge=1, le=100000)
    citation_max_depth: int = Field(default=3, ge=1, le=8)
    citation_relevance_threshold: float = Field(default=7.0, ge=1.0, le=10.0)
    target_min: int = Field(default=5, ge=0, le=50)
    target_max: int = Field(default=50, ge=1, le=50)
    max_iterations: int = Field(default=5, ge=1, le=10)

    @field_validator("question")
    @classmethod
    def non_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("is required")
        return value

    @field_validator("llm_provider")
    @classmethod
    def clean_provider(cls, value: str) -> str:
        return (value or "openai").strip().lower()

    @field_validator("llm_api_type")
    @classmethod
    def clean_api_type(cls, value: str) -> str:
        return (value or "").strip().lower()

    @field_validator("data_source")
    @classmethod
    def supported_source(cls, value: str) -> str:
        value = (value or "openalex").strip().lower()
        if value not in supported_source_ids():
            raise ValueError(f"must be one of {', '.join(supported_source_ids())}")
        return value


class DiagnosticRequest(BaseModel):
    question: Optional[str] = "machine learning"
    data_source: str = "openalex"
    wos_api_key: Optional[str] = ""
    openalex_api_key: Optional[str] = ""
    openalex_email: Optional[str] = ""
    crossref_email: Optional[str] = ""
    llm_api_key: Optional[str] = ""
    llm_provider: str = "openai"
    llm_api_type: str = ""
    llm_model: Optional[str] = None
    llm_base_url: Optional[str] = None
    wos_db: str = "WOS"
    search_field: Optional[str] = ""
    initial_query: Optional[str] = ""
    client_timezone: Optional[str] = ""
    fetch_abstracts: bool = False
    expand_citations: bool = True
    search_accept_max_records: int = Field(default=1000, ge=1, le=100000)
    citation_max_depth: int = Field(default=3, ge=1, le=8)
    citation_relevance_threshold: float = Field(default=7.0, ge=1.0, le=10.0)
    target_min: int = Field(default=5, ge=0, le=50)
    target_max: int = Field(default=50, ge=1, le=50)
    max_iterations: int = Field(default=5, ge=1, le=10)

    @field_validator("llm_provider")
    @classmethod
    def clean_provider(cls, value: str) -> str:
        return (value or "openai").strip().lower()

    @field_validator("llm_api_type")
    @classmethod
    def clean_api_type(cls, value: str) -> str:
        return (value or "").strip().lower()

    @field_validator("data_source")
    @classmethod
    def supported_source(cls, value: str) -> str:
        value = (value or "openalex").strip().lower()
        if value not in supported_source_ids():
            raise ValueError(f"must be one of {', '.join(supported_source_ids())}")
        return value


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_, exc: RequestValidationError):
    messages = []
    for error in exc.errors():
        loc = error.get("loc", [])
        field = loc[-1] if loc else ""
        label = FIELD_LABELS.get(field, str(field))
        error_type = error.get("type", "")
        msg = str(error.get("msg", "invalid value")).replace("Value error, ", "")
        if error_type == "value_error":
            if "is required" in msg:
                messages.append(f"{label} is required.")
            else:
                messages.append(f"{label}: {msg}.")
        elif error_type == "string_too_short":
            messages.append(f"{label} is required.")
        elif "greater_than_equal" in error_type or "less_than_equal" in error_type:
            messages.append(f"{label} is outside the allowed range.")
        else:
            messages.append(f"{label}: {msg}.")
    return JSONResponse(status_code=422, content={"detail": " ".join(messages) or "Invalid request."})


def _compact_text(value, max_chars: int = 700) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(?i)(x-apikey|api[_-]?key|authorization)\s*[:=]\s*[^,\s}]+", r"\1: [redacted]", text)
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "..."
    return text


def _friendly_api_error(exc: ApiException) -> str:
    body = _compact_text(exc.body or exc.data)
    query = _compact_text(getattr(exc, "query", ""), max_chars=450)
    iteration = getattr(exc, "iteration", None)
    context = f" Iteration: {iteration}." if iteration else ""
    query_context = f" Query: {query}" if query else ""

    if "please use https" in body.lower():
        return "WoS Starter API now requires HTTPS. The client has been updated; restart the web server and try again."
    if exc.status == 401:
        return f"WoS API authorization failed. Check that the WoS API Key is valid and has Starter API access.{context}{query_context}"
    if exc.status == 403:
        return f"WoS API access was forbidden. Check whether this key is allowed to use Web of Science Starter API.{context}{query_context}"
    if exc.status == 400:
        suffix = f" Response: {body}" if body else ""
        return f"WoS rejected the generated query. Try a simpler question or increase the iteration count.{context}{query_context}{suffix}"
    if exc.status == 512:
        suffix = f" Response: {body}" if body else " No response body was returned."
        return (
            "Clarivate returned HTTP 512, a non-standard upstream/server error from the WoS API. "
            "This is usually not caused by the local web UI. Retry once; if it repeats, simplify the query or reduce special characters."
            f"{context}{query_context}{suffix}"
        )
    suffix = f" Response: {body}" if body else ""
    return f"WoS API request failed with status {exc.status or 'unknown'}.{context}{query_context}{suffix}"


def _friendly_provider_error(exc: ProviderError) -> str:
    body = _compact_text(exc.body)
    message = _compact_text(str(exc), max_chars=700)
    query = _compact_text(exc.query, max_chars=450)
    query_context = f" Query: {query}" if query else ""
    suffix = f" Response: {body}" if body else (f" Details: {message}" if message else "")
    status = exc.status or "unknown"
    return f"{exc.source.title()} API request failed with status {status}.{query_context}{suffix}"


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/sources")
def sources():
    return {"sources": list_source_metadata()}


def _validate_payload(payload: SearchRequest):
    if payload.target_min > payload.target_max:
        raise HTTPException(status_code=400, detail="Target minimum cannot exceed target maximum.")
    if payload.search_accept_max_records < payload.target_max:
        raise HTTPException(status_code=400, detail="Source candidate cap cannot be lower than Max Results.")
    if payload.data_source == "wos" and not (payload.wos_api_key or "").strip():
        raise HTTPException(status_code=400, detail="WoS API Key is required for WoS searches.")


def _config_from_payload(payload: SearchRequest) -> AgentConfig:
    config = AgentConfig.from_env()
    config.data_source = payload.data_source
    config.wos_api_key = payload.wos_api_key
    config.openalex_api_key = payload.openalex_api_key or ""
    config.openalex_email = payload.openalex_email or ""
    config.crossref_email = payload.crossref_email or ""
    config.llm_api_key = payload.llm_api_key or ""
    config.llm_provider = payload.llm_provider
    config.llm_api_type = payload.llm_api_type or default_api_type(payload.llm_provider)
    if payload.llm_model:
        config.llm_model = payload.llm_model
    else:
        config.llm_model = default_model(payload.llm_provider)
    config.llm_base_url = payload.llm_base_url or default_base_url(payload.llm_provider, config.llm_api_type)
    config.wos_db = payload.wos_db or "WOS"
    config.search_field = payload.search_field or ""
    config.fetch_abstracts = payload.fetch_abstracts
    config.expand_citations = payload.expand_citations
    config.search_accept_max_records = payload.search_accept_max_records
    config.citation_max_depth = payload.citation_max_depth
    config.citation_relevance_threshold = payload.citation_relevance_threshold
    config.target_min = payload.target_min
    config.target_max = payload.target_max
    config.max_iterations = payload.max_iterations
    return config


@app.post("/api/diagnostics")
def diagnostics(payload: DiagnosticRequest):
    config = _config_from_payload(payload)
    return run_doctor(config)


@app.post("/api/smoke")
def smoke(payload: DiagnosticRequest):
    config = _config_from_payload(payload)
    query = (payload.question or "machine learning").strip() or "machine learning"
    return smoke_source(config, query=query, limit=1)


def _response_payload(result: dict, source: str) -> dict:
    return result_payload_from_search_result(result, source)


def _record_failure(store: HistoryStore, run_id: str, message: str) -> None:
    store.fail_run(run_id, message)


@app.get("/api/history/status")
def history_status():
    return HistoryStore().status()


@app.get("/api/history")
def history_list(limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)):
    store = HistoryStore()
    return {
        **store.status(),
        "history": store.list_runs(limit=limit, offset=offset),
    }


@app.get("/api/history/{run_id}")
def history_detail(run_id: str):
    store = HistoryStore()
    run = store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="History run not found.")
    return run


@app.delete("/api/history/{run_id}")
def history_delete(run_id: str):
    store = HistoryStore()
    if not store.delete_run(run_id):
        raise HTTPException(status_code=404, detail="History run not found.")
    return {"deleted": run_id}


@app.delete("/api/history")
def history_clear(confirm: bool = Query(default=False)):
    if not confirm:
        raise HTTPException(status_code=400, detail="Pass confirm=true to clear all local history.")
    store = HistoryStore()
    return {"deleted": store.clear()}


@app.post("/api/search")
def search(payload: SearchRequest):
    _validate_payload(payload)
    config = _config_from_payload(payload)
    store = HistoryStore(timezone_name=payload.client_timezone)
    run_id = store.create_run(payload.question, safe_search_params_from_config(config))

    try:
        config.validate()
        llm = create_llm_client(config)
        agent = WosSearchAgent(config, llm)
        result = agent.search(payload.question, verbose=False, initial_query=payload.initial_query)
        response = _response_payload(result, payload.data_source)
        if run_id:
            response["run_id"] = run_id
        store.complete_run(run_id, response)
    except ValueError as exc:
        _record_failure(store, run_id, str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMError as exc:
        _record_failure(store, run_id, str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ApiException as exc:
        message = _friendly_api_error(exc)
        _record_failure(store, run_id, message)
        raise HTTPException(status_code=502, detail=message) from exc
    except ProviderError as exc:
        message = _friendly_provider_error(exc)
        _record_failure(store, run_id, message)
        raise HTTPException(status_code=502, detail=message) from exc
    except Exception as exc:
        message = "Search failed. Check the local server logs for details."
        _record_failure(store, run_id, message)
        raise HTTPException(status_code=500, detail=message) from exc

    return response


@app.post("/api/search/stream")
def search_stream(payload: SearchRequest):
    _validate_payload(payload)

    def line(event: dict) -> str:
        return json.dumps(event, ensure_ascii=False) + "\n"

    def generator():
        events: Queue = Queue()
        store = HistoryStore(timezone_name=payload.client_timezone)
        run_id = ""

        def send(event: dict):
            if event.get("type") != "result":
                store.record_event(run_id, event)
            events.put(event)

        def worker():
            nonlocal run_id
            try:
                config = _config_from_payload(payload)
                run_id = store.create_run(payload.question, safe_search_params_from_config(config))
                if run_id:
                    send({"type": "run", "run_id": run_id})
                send({"type": "log", "message": "Backend request accepted: POST /api/search/stream -> HTTP 200 OK."})
                send({
                    "type": "log",
                    "message": (
                        f"Runtime config: source={config.data_source}; llm_provider={config.llm_provider}; "
                        f"api_type={config.llm_api_type}; model={config.llm_model}; target={config.target_min}-{config.target_max}; "
                        f"source_cap={config.search_accept_max_records}; iterations={config.max_iterations}."
                    ),
                })
                config.validate()
                send({"type": "log", "message": "Initializing LLM client."})
                llm = create_llm_client(config)
                send({"type": "log", "message": "Initializing source adapter."})
                agent = WosSearchAgent(config, llm)
                result = agent.search(
                    payload.question,
                    verbose=False,
                    event_handler=send,
                    initial_query=payload.initial_query,
                )
                response = _response_payload(result, payload.data_source)
                if run_id:
                    response["run_id"] = run_id
                store.complete_run(run_id, response)
                send({"type": "result", "data": response})
                send({"type": "log", "message": "Run completed successfully."})
            except ValueError as exc:
                message = str(exc)
                _record_failure(store, run_id, message)
                send({"type": "error", "message": message})
            except LLMError as exc:
                message = str(exc)
                _record_failure(store, run_id, message)
                send({"type": "error", "message": message})
            except ApiException as exc:
                message = _friendly_api_error(exc)
                _record_failure(store, run_id, message)
                send({"type": "error", "message": message})
            except ProviderError as exc:
                message = _friendly_provider_error(exc)
                _record_failure(store, run_id, message)
                send({"type": "error", "message": message})
            except Exception:
                message = "Search failed. Check the local server logs for details."
                _record_failure(store, run_id, message)
                send({"type": "error", "message": message})
            finally:
                events.put(None)

        Thread(target=worker, daemon=True).start()

        while True:
            item = events.get()
            if item is None:
                break
            yield line(item)

    return StreamingResponse(generator(), media_type="application/x-ndjson")


def main():
    uvicorn.run("paperseek.web_app:app", host="127.0.0.1", port=8765, reload=False)


if __name__ == "__main__":
    main()
