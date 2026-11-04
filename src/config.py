import os
from typing import Literal, Mapping, Optional

import yaml
from pydantic import BaseModel


class Source(BaseModel):
    name: str
    type: str
    url: str
    adapter: Literal["feed", "html"] = "feed"
    enabled: bool = True


class Settings(BaseModel):
    provider: Literal["azure", "openai"]
    agent_model: str
    evaluator_model: str
    items_per_source: int
    demo_mode: bool
    fake_llm: bool
    db_path: str


def load_settings(env: Optional[Mapping[str, str]] = None) -> Settings:
    env = os.environ if env is None else env
    azure = bool(env.get("AZURE_OPENAI_ENDPOINT") and env.get("AZURE_OPENAI_API_KEY"))
    agent_model = env.get("AGENT_MODEL", "gpt-4o-mini")
    return Settings(
        provider="azure" if azure else "openai",
        agent_model=agent_model,
        evaluator_model=env.get("EVALUATOR_MODEL") or agent_model,
        items_per_source=int(env.get("ITEMS_PER_SOURCE", "3")),
        demo_mode=env.get("DEMO_MODE") == "1",
        fake_llm=env.get("FAKE_LLM") == "1",
        db_path=env.get("DB_PATH", "data/signalwire.db"),
    )


def load_sources(path: str = "config/sources.yaml") -> list[Source]:
    with open(path) as f:
        data = yaml.safe_load(f)
    return [s for s in (Source(**row) for row in data["sources"]) if s.enabled]
