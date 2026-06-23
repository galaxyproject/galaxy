"""Factory for building a pydantic-ai model usable as an LLMJudge.

Reuses the same proxy/key resolution as the agents under test, but produces
a pydantic_ai Model instance that pydantic-evals' LLMJudge can call.
"""

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider


def build_judge_model(
    model_name: str,
    base_url: str,
    api_key: str,
) -> OpenAIChatModel:
    """Build an OpenAI-compatible pydantic-ai model for use as an LLMJudge."""
    provider = OpenAIProvider(base_url=base_url, api_key=api_key)
    return OpenAIChatModel(model_name, provider=provider)
