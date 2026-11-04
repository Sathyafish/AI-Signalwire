from typing import Literal

from src.config import Settings


def get_llm(settings: Settings, role: Literal["agent", "evaluator"]):
    """Return the chat model for a role. Keys come from the environment, never from code."""
    if settings.fake_llm:
        from src.fake_llm import FakeLLM

        return FakeLLM()
    model = settings.evaluator_model if role == "evaluator" else settings.agent_model
    if settings.provider == "azure":
        from langchain_openai import AzureChatOpenAI

        return AzureChatOpenAI(azure_deployment=model, api_version="2024-08-01-preview", temperature=0)
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=model, temperature=0)
