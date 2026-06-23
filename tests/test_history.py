import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from paperseek.config import AgentConfig
from paperseek.history import HistoryStore, safe_search_params_from_config
from paperseek.web_app import app
from tests.helpers import temporary_env


class HistoryStoreTest(unittest.TestCase):
    def test_store_saves_run_events_and_results_without_raw_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "paperseek.db"
            store = HistoryStore(db_path=db_path, enabled=True)
            config = AgentConfig(
                data_source="openalex",
                openalex_api_key="oa-secret",
                llm_api_key="llm-secret",
                llm_provider="openai",
                llm_api_type="openai_responses",
                llm_model="gpt-5.4-mini",
                llm_base_url="https://api.openai.com/v1",
                discipline_fields=("17", "14"),
            )
            run_id = store.create_run("open innovation", safe_search_params_from_config(config))
            store.record_event(run_id, {"type": "log", "message": "Started", "api_key": "event-secret"})
            store.complete_run(
                run_id,
                {
                    "question": "open innovation",
                    "source": "openalex",
                    "final_query": '"open innovation"',
                    "db": "OPENALEX",
                    "field": "",
                    "total": 1,
                    "iterations": 1,
                    "history": [{"iteration": 1, "query": '"open innovation"', "total": 1}],
                    "citation_map": {"enabled": True, "nodes": [], "edges": []},
                    "ranked": [
                        {
                            "rank": 1,
                            "uid": "W1",
                            "provider": "openalex",
                            "title": "Open Innovation",
                            "authors": ["Ada Lovelace"],
                            "publish_year": 2025,
                            "source": "Research Policy",
                            "doi": "10.1234/example",
                            "links": {"record": "https://example.org/record"},
                            "keywords": "open innovation; platforms",
                            "citations": "42",
                            "score": 9.1,
                            "reasoning": "Relevant",
                        }
                    ],
                },
            )

            runs = store.list_runs()
            self.assertEqual(len(runs), 1)
            self.assertEqual(runs[0]["result_count"], 1)

            detail = store.get_run(run_id)
            self.assertIsNotNone(detail)
            self.assertEqual(detail["status"], "success")
            self.assertEqual(detail["history"][0]["total"], 1)
            self.assertEqual(detail["ranked"][0]["title"], "Open Innovation")
            self.assertEqual(detail["ranked"][0]["keywords"], "open innovation; platforms")
            self.assertTrue(detail["params"]["has_llm_api_key"])
            self.assertEqual(detail["params"]["discipline_fields"], ["17", "14"])
            serialized = json.dumps(detail, ensure_ascii=False)
            self.assertNotIn("llm-secret", serialized)
            self.assertNotIn("oa-secret", serialized)
            self.assertNotIn("event-secret", serialized)

            self.assertTrue(store.delete_run(run_id))
            self.assertEqual(store.list_runs(), [])

    def test_store_defaults_to_shanghai_timezone_for_timestamps(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = HistoryStore(db_path=Path(tmp) / "paperseek.db", enabled=True)
            run_id = store.create_run("open innovation", {"data_source": "openalex"})

            detail = store.get_run(run_id)

            self.assertIsNotNone(detail)
            self.assertIn("+08:00", detail["created_at"])

    def test_store_uses_client_timezone_offset_when_zone_name_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = HistoryStore(
                db_path=Path(tmp) / "paperseek.db",
                enabled=True,
                timezone_name="Unsupported/Zone",
                utc_offset_minutes=-300,
            )
            run_id = store.create_run("open innovation", {"data_source": "openalex"})

            detail = store.get_run(run_id)

            self.assertIsNotNone(detail)
            self.assertIn("-05:00", detail["created_at"])


class HistoryApiTest(unittest.TestCase):
    def test_history_endpoint_reads_configured_local_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            with temporary_env({
                "PAPERSEEK_HISTORY_DB": str(Path(tmp) / "paperseek.db"),
                "PAPERSEEK_HISTORY_ENABLED": "true",
            }):
                store = HistoryStore()
                run_id = store.create_run("responsible AI", {"data_source": "openalex"})
                store.fail_run(run_id, "Missing LLM key")

                client = TestClient(app)
                response = client.get("/api/history")
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload["history"][0]["id"], run_id)
                self.assertEqual(payload["history"][0]["status"], "error")

                detail = client.get(f"/api/history/{run_id}").json()
                self.assertEqual(detail["error_message"], "Missing LLM key")

    def test_clear_history_requires_explicit_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            with temporary_env({
                "PAPERSEEK_HISTORY_DB": str(Path(tmp) / "paperseek.db"),
                "PAPERSEEK_HISTORY_ENABLED": "true",
            }):
                store = HistoryStore()
                run_id = store.create_run("platform governance", {"data_source": "openalex"})
                self.assertTrue(run_id)

                client = TestClient(app)
                response = client.delete("/api/history")
                self.assertEqual(response.status_code, 400)
                self.assertEqual(len(store.list_runs()), 1)

                confirmed = client.delete("/api/history?confirm=true")
                self.assertEqual(confirmed.status_code, 200)
                self.assertEqual(confirmed.json()["deleted"], 1)
                self.assertEqual(store.list_runs(), [])


if __name__ == "__main__":
    unittest.main()
