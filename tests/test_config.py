import os
from unittest.mock import patch

from paperseek.config import AgentConfig, default_api_type, default_model, default_base_url


def test_agent_config_from_env_defaults():
    # Test with empty environment
    with patch.dict(os.environ, {}, clear=True):
        config = AgentConfig.from_env()

        assert config.llm_provider == "openai"
        assert config.llm_api_type == default_api_type("openai")
        assert config.llm_model == default_model("openai")
        assert config.llm_base_url == default_base_url("openai", default_api_type("openai"))
        assert config.llm_max_tokens == 2048
        assert config.ranking_llm_timeout_seconds == 60
        assert config.wos_db == "WOS"
        assert config.fetch_abstracts is False
        assert config.expand_citations is True
        assert config.citation_seed_count == 30
        assert config.citation_per_seed == 4
        assert config.citation_max_records == 160
        assert config.citation_depth == 2
        assert config.ranking_batch_size == 8
        assert config.ranking_concurrency == 16
        assert config.ranking_candidate_limit == 256
        assert config.target_min == 5
        assert config.target_max == 50
        assert config.max_iterations == 5
        assert config.retrieval_pool_max == 3000
        assert config.retrieval_pool_min == 5
        assert config.retrieval_lane_limit == 1000
        assert config.retrieval_rrf_k == 60
        assert config.retrieval_embedding_provider == "local"
        assert config.retrieval_embedding_model == "qwen3-embedding:8b,bge-large-zh:latest"
        assert config.retrieval_reranker_provider == ""
        assert config.retrieval_reranker_model == "qwen3-reranker:8b"
        assert config.retrieval_crossref_enrichment is False
        assert config.llm_api_key == ""
        assert config.wos_api_key == ""


def test_agent_config_from_env_custom():
    custom_env = {
        "LLM_PROVIDER": "anthropic",
        "LLM_API_TYPE": "custom_anthropic",
        "LLM_MODEL": "claude-test",
        "LLM_BASE_URL": "http://custom-anthropic.local",
        "LLM_MAX_TOKENS": "4096",
        "RANKING_LLM_TIMEOUT_SECONDS": "120",
        "WOS_DB": "WOS_CUSTOM",
        "FETCH_ABSTRACTS": "1",
        "EXPAND_CITATIONS": "false",
        "CITATION_SEED_COUNT": "15",
        "CITATION_PER_SEED": "2",
        "CITATION_MAX_RECORDS": "80",
        "CITATION_DEPTH": "1",
        "RANKING_BATCH_SIZE": "4",
        "RANKING_CONCURRENCY": "8",
        "RANKING_CANDIDATE_LIMIT": "128",
        "TARGET_MIN": "10",
        "TARGET_MAX": "100",
        "MAX_ITERATIONS": "10",
        "RETRIEVAL_POOL_MAX": "5000",
        "RETRIEVAL_POOL_MIN": "10",
        "RETRIEVAL_LANE_LIMIT": "2000",
        "RETRIEVAL_RRF_K": "100",
        "RETRIEVAL_EMBEDDING_PROVIDER": "openai",
        "RETRIEVAL_EMBEDDING_MODEL": "text-embedding-3-small",
        "RETRIEVAL_RERANKER_PROVIDER": "cohere",
        "RETRIEVAL_RERANKER_MODEL": "rerank-english-v3.0",
        "RETRIEVAL_CROSSREF_ENRICHMENT": "yes",
        "LLM_API_KEY": "sk-123",
        "WOS_API_KEY": "wos-123",
    }
    with patch.dict(os.environ, custom_env, clear=True):
        config = AgentConfig.from_env()

        assert config.llm_provider == "anthropic"
        assert config.llm_api_type == "custom_anthropic"
        assert config.llm_model == "claude-test"
        assert config.llm_base_url == "http://custom-anthropic.local"
        assert config.llm_max_tokens == 4096
        assert config.ranking_llm_timeout_seconds == 120
        assert config.wos_db == "WOS_CUSTOM"
        assert config.fetch_abstracts is True
        assert config.expand_citations is False
        assert config.citation_seed_count == 15
        assert config.citation_per_seed == 2
        assert config.citation_max_records == 80
        assert config.citation_depth == 1
        assert config.ranking_batch_size == 4
        assert config.ranking_concurrency == 8
        assert config.ranking_candidate_limit == 128
        assert config.target_min == 10
        assert config.target_max == 100
        assert config.max_iterations == 10
        assert config.retrieval_pool_max == 5000
        assert config.retrieval_pool_min == 10
        assert config.retrieval_lane_limit == 2000
        assert config.retrieval_rrf_k == 100
        assert config.retrieval_embedding_provider == "openai"
        assert config.retrieval_embedding_model == "text-embedding-3-small"
        assert config.retrieval_reranker_provider == "cohere"
        assert config.retrieval_reranker_model == "rerank-english-v3.0"
        assert config.retrieval_crossref_enrichment is True
        assert config.llm_api_key == "sk-123"
        assert config.wos_api_key == "wos-123"


def test_agent_config_from_env_int_parsing_fallback():
    # Test fallback to default when invalid int is provided
    custom_env = {
        "LLM_MAX_TOKENS": "invalid_int",
        "RANKING_LLM_TIMEOUT_SECONDS": "",
    }
    with patch.dict(os.environ, custom_env, clear=True):
        config = AgentConfig.from_env()

        assert config.llm_max_tokens == 2048  # Default
        assert config.ranking_llm_timeout_seconds == 60  # Default


def test_agent_config_from_env_fallback_logic():
    # Test when LLM_API_TYPE is missing, it falls back based on LLM_PROVIDER
    custom_env = {
        "LLM_PROVIDER": "anthropic",
        "LLM_API_TYPE": "",
    }
    with patch.dict(os.environ, custom_env, clear=True):
        config = AgentConfig.from_env()

        assert config.llm_provider == "anthropic"
        assert config.llm_api_type == default_api_type("anthropic")
