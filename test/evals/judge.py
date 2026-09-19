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
    # Strip the `provider:` prefix (e.g. `openai:gpt-5-mini`) the same way the
    # agents under test do; the bare model name is what the API expects.
    bare_name = model_name.split(":", 1)[1] if ":" in model_name else model_name
    provider = OpenAIProvider(base_url=base_url, api_key=api_key)
    return OpenAIChatModel(bare_name, provider=provider)
