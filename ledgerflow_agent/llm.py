from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq
from langchain_groq import ChatGroq

from ledgerflow_agent.guardrails import require_env

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

DEFAULT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_TEMPERATURE = 0.0
DEFAULT_MAX_TOKENS = 2048


@lru_cache(maxsize=1)
def get_groq_client() -> Groq:
    return Groq(api_key=require_env("GROQ_API_KEY"))


@lru_cache(maxsize=16)
def get_chat_llm(
    model_name: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> ChatGroq:
    return ChatGroq(
        groq_api_key=require_env("GROQ_API_KEY"),
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
    )
