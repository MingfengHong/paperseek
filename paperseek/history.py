from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional, Union

from paperseek.config import AgentConfig


DISABLED_VALUES = {"0", "false", "no", "off"}
SECRET_KEY_NAMES = {"api_key", "apikey", "authorization", "auth_token", "access_token", "secret", "password"}
SECRET_KEY_PARTS = ("authorization", "token", "secret", "password")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def history_enabled() -> bool:
    return os.environ.get("PAPERSEEK_HISTORY_ENABLED", "true").strip().lower() not in DISABLED_VALUES


def history_data_dir() -> Path:
    configured = os.environ.get("PAPERSEEK_DATA_DIR", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".paperseek"


def history_db_path() -> Path:
    configured = os.environ.get("PAPERSEEK_HISTORY_DB", "").strip()
    if configured:
        return Path(configured).expanduser()
    return history_data_dir() / "paperseek.db"


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _json_loads(value: Optional[str], default: Any = None) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _is_secret_key(key: str) -> bool:
    normalized = str(key or "").lower().replace("-", "_")
    return (
        normalized in SECRET_KEY_NAMES
        or normalized.endswith("_key")
        or normalized.endswith("_apikey")
        or any(part in normalized for part in SECRET_KEY_PARTS)
    )


def redact_secrets(value: Any) -> Any:
    """Return a JSON-safe copy with obvious credential fields removed."""
    if isinstance(value, dict):
        output = {}
        for key, item in value.items():
            output[key] = "[redacted]" if _is_secret_key(str(key)) else redact_secrets(item)
        return output
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, tuple):
        return [redact_secrets(item) for item in value]
    return value


def safe_search_params_from_config(config: AgentConfig) -> dict[str, Any]:
    """Persist only run-shaping settings, never raw user credentials."""
    return {
        "data_source": config.data_source,
        "llm_provider": config.llm_provider,
        "llm_api_type": config.llm_api_type,
        "llm_model": config.llm_model,
        "llm_base_url": config.llm_base_url,
        "wos_db": config.wos_db,
        "search_field": config.search_field,
        "fetch_abstracts": config.fetch_abstracts,
        "expand_citations": config.expand_citations,
        "citation_seed_count": config.citation_seed_count,
        "citation_per_seed": config.citation_per_seed,
        "citation_max_records": config.citation_max_records,
        "target_min": config.target_min,
        "target_max": config.target_max,
        "max_iterations": config.max_iterations,
        "has_wos_api_key": bool(config.wos_api_key),
        "has_openalex_api_key": bool(config.openalex_api_key),
        "has_openalex_email": bool(config.openalex_email),
        "has_crossref_email": bool(config.crossref_email),
        "has_llm_api_key": bool(config.llm_api_key),
    }


def result_payload_from_search_result(result: dict[str, Any], source: str) -> dict[str, Any]:
    from paperseek.formatter import ranked_items_to_dict

    return {
        "question": result["question"],
        "source": result.get("source", source),
        "final_query": result["final_query"],
        "db": result["db"],
        "field": result["field"],
        "total": result["total"],
        "iterations": result["iterations"],
        "history": result.get("history", []),
        "citation_map": result.get("citation_map", {}),
        "ranked": ranked_items_to_dict(result["ranked"]),
    }


def _as_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _authors_from_paper(paper: dict[str, Any]) -> list[str]:
    authors = paper.get("authors")
    if isinstance(authors, list):
        return [str(author) for author in authors if author]
    authors_text = paper.get("authors_text") or ""
    return [part.strip() for part in str(authors_text).split(";") if part.strip()]


class HistoryStore:
    def __init__(self, db_path: Optional[Union[Path, str]] = None, enabled: Optional[bool] = None):
        self.db_path = Path(db_path).expanduser() if db_path is not None else history_db_path()
        self._enabled = history_enabled() if enabled is None else enabled
        self._schema_ready = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "path": str(self.db_path),
        }

    def _connect(self) -> sqlite3.Connection:
        if not self.enabled:
            raise RuntimeError("PaperSeek history is disabled.")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        if not self._schema_ready:
            self._ensure_schema(conn)
            self._schema_ready = True
        return conn

    @contextmanager
    def _connection(self):
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS search_runs (
                id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                source TEXT,
                final_query TEXT,
                db TEXT,
                field TEXT,
                total INTEGER,
                iterations INTEGER,
                status TEXT NOT NULL,
                error_message TEXT,
                params_json TEXT,
                history_json TEXT,
                citation_map_json TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT
            );

            CREATE TABLE IF NOT EXISTS search_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                event_type TEXT,
                stage TEXT,
                status TEXT,
                message TEXT,
                payload_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES search_runs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS search_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                rank INTEGER,
                paper_uid TEXT,
                source TEXT,
                title TEXT,
                authors_json TEXT,
                year INTEGER,
                venue TEXT,
                doi TEXT,
                url TEXT,
                abstract TEXT,
                citation_count INTEGER,
                relevance_score REAL,
                relevance_reason TEXT,
                raw_json TEXT,
                FOREIGN KEY(run_id) REFERENCES search_runs(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_search_runs_created_at ON search_runs(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_search_events_run_id ON search_events(run_id);
            CREATE INDEX IF NOT EXISTS idx_search_results_run_id ON search_results(run_id);
            """
        )
        self._ensure_column(conn, "search_runs", "history_json", "TEXT")

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def create_run(self, question: str, params: Optional[dict[str, Any]] = None) -> str:
        if not self.enabled:
            return ""
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        now = utc_now()
        try:
            with self._connection() as conn:
                conn.execute(
                    """
                    INSERT INTO search_runs (
                        id, question, status, params_json, created_at, started_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (run_id, question, "running", _json_dumps(redact_secrets(params or {})), now, now),
                )
        except Exception:
            return ""
        return run_id

    def record_event(self, run_id: str, event: dict[str, Any]) -> None:
        if not self.enabled or not run_id:
            return
        safe_event = redact_secrets(event or {})
        try:
            with self._connection() as conn:
                conn.execute(
                    """
                    INSERT INTO search_events (
                        run_id, event_type, stage, status, message, payload_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        str(safe_event.get("type", "")),
                        str(safe_event.get("stage", "")),
                        str(safe_event.get("status", "")),
                        str(safe_event.get("message", "")),
                        _json_dumps(safe_event),
                        utc_now(),
                    ),
                )
        except Exception:
            return

    def complete_run(self, run_id: str, payload: dict[str, Any]) -> None:
        if not self.enabled or not run_id:
            return
        safe_payload = redact_secrets(payload or {})
        ranked = list(safe_payload.get("ranked") or [])
        try:
            with self._connection() as conn:
                conn.execute("DELETE FROM search_results WHERE run_id = ?", (run_id,))
                conn.execute(
                    """
                    UPDATE search_runs
                    SET source = ?, final_query = ?, db = ?, field = ?, total = ?, iterations = ?,
                        status = ?, error_message = NULL, history_json = ?, citation_map_json = ?, finished_at = ?
                    WHERE id = ?
                    """,
                    (
                        safe_payload.get("source", ""),
                        safe_payload.get("final_query", ""),
                        safe_payload.get("db", ""),
                        safe_payload.get("field", ""),
                        _as_int(safe_payload.get("total")),
                        _as_int(safe_payload.get("iterations")),
                        "success",
                        _json_dumps(safe_payload.get("history") or []),
                        _json_dumps(safe_payload.get("citation_map") or {}),
                        utc_now(),
                        run_id,
                    ),
                )
                self._insert_results(conn, run_id, ranked)
        except Exception:
            return

    def fail_run(self, run_id: str, error_message: str) -> None:
        if not self.enabled or not run_id:
            return
        try:
            with self._connection() as conn:
                conn.execute(
                    """
                    UPDATE search_runs
                    SET status = ?, error_message = ?, finished_at = ?
                    WHERE id = ?
                    """,
                    ("error", str(error_message or ""), utc_now(), run_id),
                )
        except Exception:
            return

    def list_runs(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        limit = max(1, min(int(limit or 50), 200))
        offset = max(0, int(offset or 0))
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT r.*,
                       (SELECT COUNT(*) FROM search_results sr WHERE sr.run_id = r.id) AS result_count,
                       (SELECT COUNT(*) FROM search_events se WHERE se.run_id = r.id) AS event_count
                FROM search_runs r
                ORDER BY r.created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [self._run_row_to_dict(row, include_payload=False) for row in rows]

    def get_run(self, run_id: str) -> Optional[dict[str, Any]]:
        if not self.enabled:
            return None
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT r.*,
                       (SELECT COUNT(*) FROM search_results sr WHERE sr.run_id = r.id) AS result_count,
                       (SELECT COUNT(*) FROM search_events se WHERE se.run_id = r.id) AS event_count
                FROM search_runs r
                WHERE r.id = ?
                """,
                (run_id,),
            ).fetchone()
            if row is None:
                return None
            events = conn.execute(
                "SELECT * FROM search_events WHERE run_id = ? ORDER BY id ASC",
                (run_id,),
            ).fetchall()
            results = conn.execute(
                "SELECT * FROM search_results WHERE run_id = ? ORDER BY rank ASC, id ASC",
                (run_id,),
            ).fetchall()
        data = self._run_row_to_dict(row, include_payload=True)
        data["events"] = [self._event_row_to_dict(event) for event in events]
        data["ranked"] = [self._result_row_to_dict(result) for result in results]
        return data

    def delete_run(self, run_id: str) -> bool:
        if not self.enabled:
            return False
        with self._connection() as conn:
            cursor = conn.execute("DELETE FROM search_runs WHERE id = ?", (run_id,))
            return cursor.rowcount > 0

    def clear(self) -> int:
        if not self.enabled:
            return 0
        with self._connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM search_runs").fetchone()[0]
            conn.execute("DELETE FROM search_runs")
        return int(count or 0)

    def _insert_results(self, conn: sqlite3.Connection, run_id: str, ranked: Iterable[dict[str, Any]]) -> None:
        for index, paper in enumerate(ranked, 1):
            if not isinstance(paper, dict):
                continue
            links = paper.get("links") if isinstance(paper.get("links"), dict) else {}
            doi = str(paper.get("doi") or "")
            url = paper.get("url") or links.get("record") or links.get("landing_page") or (f"https://doi.org/{doi}" if doi else "")
            conn.execute(
                """
                INSERT INTO search_results (
                    run_id, rank, paper_uid, source, title, authors_json, year, venue, doi,
                    url, abstract, citation_count, relevance_score, relevance_reason, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    _as_int(paper.get("rank")) or index,
                    str(paper.get("uid") or paper.get("id") or doi or paper.get("title") or ""),
                    str(paper.get("provider") or paper.get("source_provider") or paper.get("source") or ""),
                    str(paper.get("title") or ""),
                    _json_dumps(_authors_from_paper(paper)),
                    _as_int(paper.get("publish_year") or paper.get("year")),
                    str(paper.get("source") or paper.get("venue") or ""),
                    doi,
                    str(url or ""),
                    str(paper.get("abstract") or ""),
                    _as_int(paper.get("citation_count") or paper.get("citations")),
                    _as_float(paper.get("relevance_score") if paper.get("relevance_score") is not None else paper.get("score")),
                    str(paper.get("relevance_reason") or paper.get("reasoning") or ""),
                    _json_dumps(paper),
                ),
            )

    def _run_row_to_dict(self, row: sqlite3.Row, include_payload: bool) -> dict[str, Any]:
        data = {
            "id": row["id"],
            "question": row["question"],
            "source": row["source"] or "",
            "final_query": row["final_query"] or "",
            "db": row["db"] or "",
            "field": row["field"] or "",
            "total": row["total"],
            "iterations": row["iterations"],
            "status": row["status"],
            "error_message": row["error_message"] or "",
            "created_at": row["created_at"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"] or "",
            "result_count": row["result_count"],
            "event_count": row["event_count"],
        }
        if include_payload:
            data["params"] = _json_loads(row["params_json"], {})
            data["history"] = _json_loads(row["history_json"], [])
            data["citation_map"] = _json_loads(row["citation_map_json"], {})
        return data

    def _event_row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        payload = _json_loads(row["payload_json"], {})
        return {
            "id": row["id"],
            "type": row["event_type"] or "",
            "stage": row["stage"] or "",
            "status": row["status"] or "",
            "message": row["message"] or "",
            "created_at": row["created_at"],
            "payload": payload,
        }

    def _result_row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        raw = _json_loads(row["raw_json"], {})
        if isinstance(raw, dict) and raw:
            return raw
        return {
            "rank": row["rank"],
            "uid": row["paper_uid"] or "",
            "provider": row["source"] or "",
            "title": row["title"] or "",
            "authors": _json_loads(row["authors_json"], []),
            "publish_year": row["year"],
            "source": row["venue"] or "",
            "doi": row["doi"] or "",
            "url": row["url"] or "",
            "abstract": row["abstract"] or "",
            "citations": str(row["citation_count"] or ""),
            "citation_count": row["citation_count"] or 0,
            "score": row["relevance_score"],
            "reasoning": row["relevance_reason"] or "",
        }
