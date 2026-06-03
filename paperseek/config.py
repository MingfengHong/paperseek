import os
from dataclasses import dataclass, field

from paperseek.source_metadata import supported_source_ids


@dataclass
class AgentConfig:
    data_source: str = "openalex"
    wos_api_key: str = ""
    openalex_api_key: str = ""
    openalex_email: str = ""
    crossref_email: str = ""
    llm_api_key: str = ""
    llm_provider: str = "openai"
    llm_api_type: str = ""
    llm_model: str = ""
    llm_base_url: str = ""
    wos_db: str = "WOS"
    search_field: str = ""
    fetch_abstracts: bool = False
    expand_citations: bool = True
    citation_seed_count: int = 3
    citation_per_seed: int = 4
    citation_max_records: int = 40
    target_min: int = 5
    target_max: int = 50
    max_iterations: int = 5

    @classmethod
    def from_env(cls) -> "AgentConfig":
        provider = os.environ.get("LLM_PROVIDER", "openai").lower()
        api_type = os.environ.get("LLM_API_TYPE", "") or default_api_type(provider)
        return cls(
            wos_api_key=os.environ.get("WOS_API_KEY", ""),
            data_source=os.environ.get("DATA_SOURCE", "openalex").lower(),
            openalex_api_key=os.environ.get("OPENALEX_API_KEY", ""),
            openalex_email=os.environ.get("OPENALEX_EMAIL", ""),
            crossref_email=os.environ.get("CROSSREF_EMAIL", ""),
            llm_api_key=os.environ.get("LLM_API_KEY", ""),
            llm_provider=provider,
            llm_api_type=api_type,
            llm_model=os.environ.get("LLM_MODEL", default_model(provider)),
            llm_base_url=os.environ.get("LLM_BASE_URL", default_base_url(provider, api_type)),
            wos_db=os.environ.get("WOS_DB", "WOS"),
            search_field=os.environ.get("SEARCH_FIELD", ""),
            fetch_abstracts=os.environ.get("FETCH_ABSTRACTS", "").lower() in ("1", "true", "yes"),
            expand_citations=os.environ.get("EXPAND_CITATIONS", "true").lower() not in ("0", "false", "no"),
            citation_seed_count=int(os.environ.get("CITATION_SEED_COUNT", "3")),
            citation_per_seed=int(os.environ.get("CITATION_PER_SEED", "4")),
            citation_max_records=int(os.environ.get("CITATION_MAX_RECORDS", "40")),
            target_min=int(os.environ.get("TARGET_MIN", "5")),
            target_max=int(os.environ.get("TARGET_MAX", "50")),
            max_iterations=int(os.environ.get("MAX_ITERATIONS", "5")),
        )

    def validate(self):
        missing = []
        self.data_source = (self.data_source or "openalex").lower()
        if self.data_source not in supported_source_ids():
            raise ValueError(f"DATA_SOURCE must be one of {', '.join(supported_source_ids())}, got '{self.data_source}'")
        if self.data_source == "wos" and not self.wos_api_key:
            missing.append("WOS_API_KEY")
        self.llm_provider = (self.llm_provider or "openai").lower()
        self.llm_api_type = (self.llm_api_type or default_api_type(self.llm_provider)).lower()
        if not self.llm_api_key and self.llm_provider != "ollama":
            missing.append("LLM_API_KEY")
        if self.llm_provider not in SUPPORTED_LLM_PROVIDERS:
            raise ValueError(f"LLM_PROVIDER must be one of {', '.join(SUPPORTED_LLM_PROVIDERS)}, got '{self.llm_provider}'")
        if self.llm_api_type not in SUPPORTED_LLM_API_TYPES:
            raise ValueError(f"LLM_API_TYPE must be one of {', '.join(SUPPORTED_LLM_API_TYPES)}, got '{self.llm_api_type}'")
        if missing:
            raise ValueError(
                f"Missing required configuration: {', '.join(missing)}. "
                f"Set them via environment variables or CLI flags."
            )


SUPPORTED_LLM_PROVIDERS = (
    "openai",
    "anthropic",
    "google",
    "deepseek",
    "cstcloud",
    "dashscope",
    "moonshot",
    "zhipu",
    "siliconflow",
    "openrouter",
    "volcengine",
    "hunyuan",
    "qianfan",
    "modelscope",
    "ollama",
    "custom",
)

SUPPORTED_LLM_API_TYPES = ("openai_chat", "openai_responses", "anthropic_messages")


def default_api_type(provider: str) -> str:
    provider = (provider or "openai").lower()
    if provider == "anthropic":
        return "anthropic_messages"
    if provider == "openai":
        return "openai_responses"
    return "openai_chat"


def default_model(provider: str) -> str:
    provider = (provider or "openai").lower()
    models = {
        "openai": "gpt-5.4-mini",
        "anthropic": "claude-sonnet-4-6",
        "google": "gemini-3.5-flash",
        "deepseek": "deepseek-v4-flash",
        "cstcloud": "DeepSeek-V4-Flash",
        "dashscope": "qwen3.6-plus",
        "moonshot": "kimi-k2.6",
        "zhipu": "glm-5.1",
        "siliconflow": "deepseek-ai/DeepSeek-V4-Flash",
        "openrouter": "openai/gpt-5.4-mini",
        "volcengine": "doubao-seed-2-0-mini-260428",
        "hunyuan": "hunyuan-turbos-latest",
        "qianfan": "ernie-5.0",
        "modelscope": "Qwen/Qwen3-235B-A22B-Instruct-2507",
        "ollama": "qwen3:8b",
        "custom": "",
    }
    return models.get(provider, "")


def default_base_url(provider: str, api_type: str = "") -> str:
    provider = (provider or "openai").lower()
    api_type = (api_type or default_api_type(provider)).lower()
    urls = {
        "openai": "https://api.openai.com/v1",
        "anthropic": "https://api.anthropic.com",
        "google": "https://generativelanguage.googleapis.com/v1beta/openai",
        "deepseek": "https://api.deepseek.com",
        "cstcloud": "https://uni-api.cstcloud.cn/v1",
        "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "moonshot": "https://api.moonshot.ai/v1",
        "zhipu": "https://open.bigmodel.cn/api/paas/v4",
        "siliconflow": "https://api.siliconflow.cn/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        "volcengine": "https://ark.cn-beijing.volces.com/api/v3",
        "hunyuan": "https://tokenhub.tencentmaas.com/v1",
        "qianfan": "https://qianfan.baidubce.com/v2",
        "modelscope": "https://api-inference.modelscope.cn/v1",
        "ollama": "http://127.0.0.1:11434/v1",
        "custom": "",
    }
    if api_type == "anthropic_messages" and provider == "anthropic":
        return "https://api.anthropic.com"
    return urls.get(provider, "")
