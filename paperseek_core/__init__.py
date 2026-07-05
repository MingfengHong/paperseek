from __future__ import annotations

from typing import Callable

from paperseek_core.agent import LiteratureSearchAgent, PaperSeekAgent, WosSearchAgent
from paperseek_core.config import LLMConfig, SearchConfig, SourceConfig, build_runtime_config
from paperseek_core.llm import create_llm_client

__version__ = "0.2.1"


def run_search(
    question: str,
    search_config: SearchConfig | None = None,
    source_config: SourceConfig | None = None,
    llm_config: LLMConfig | None = None,
    event_handler: Callable[[dict], None] | None = None,
) -> dict:
    config = build_runtime_config(search_config, source_config, llm_config)
    llm = create_llm_client(config)
    return PaperSeekAgent(config, llm).search(question, event_handler=event_handler)


__all__ = [
    "LLMConfig",
    "LiteratureSearchAgent",
    "PaperSeekAgent",
    "SearchConfig",
    "SourceConfig",
    "WosSearchAgent",
    "__version__",
    "run_search",
]
