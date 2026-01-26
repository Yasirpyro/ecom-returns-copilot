from __future__ import annotations

import os
from typing import Literal, Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

LLMProfile = Literal["draft", "finalize", "repair"]


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    raise RuntimeError(f"Missing required environment variable: {name}")


def get_llm(
    profile: LLMProfile,
    *,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> ChatOpenAI:
    api_key = _require_env("OPENROUTER_API_KEY")
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    model = os.getenv("OPENROUTER_MODEL", "x-ai/grok-4.1-fast")

    app_url = os.getenv("OPENROUTER_APP_URL", "http://localhost:8000")
    app_name = os.getenv("OPENROUTER_APP_NAME", "ecom-returns-copilot")

    defaults = {
        "draft": {"temperature": 0.2, "max_tokens": 200},
        "finalize": {"temperature": 0.2, "max_tokens": 260},
        "repair": {"temperature": 0.0, "max_tokens": 260},
    }[profile]

    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=defaults["temperature"] if temperature is None else temperature,
        max_tokens=defaults["max_tokens"] if max_tokens is None else max_tokens,
        default_headers={
            "HTTP-Referer": app_url,
            "X-Title": app_name,
        },
    )
