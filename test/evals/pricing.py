"""Per-million-token pricing for the models the harness commonly evaluates.

Adapted from tcollins2011/galaxy PR #64 ``test/integration/agent_evals/eval_utils.py``.
Unknown models cost $0 -- if you want a real number for one, add an entry.
Provider prefix and ``claude-`` are stripped before lookup so
``anthropic:claude-haiku-4-5`` and ``haiku-4-5`` both resolve.
"""

# (input $/M tokens, output $/M tokens)
_PRICING: dict[str, tuple[float, float]] = {
    # Anthropic
    "opus-4-7": (15.0, 75.0),
    "opus-4-6": (15.0, 75.0),
    "opus-4": (15.0, 75.0),
    "sonnet-4-6": (3.0, 15.0),
    "sonnet-4-5": (3.0, 15.0),
    "sonnet-4": (3.0, 15.0),
    "haiku-4-6": (0.80, 4.0),
    "haiku-4-5": (0.80, 4.0),
    "haiku-4": (0.80, 4.0),
    # OpenAI
    "gpt-4o": (2.50, 10.0),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.0, 30.0),
    "gpt-3.5-turbo": (0.50, 1.50),
    "gpt-5": (2.50, 15.0),
    "gpt-5.4": (2.50, 15.0),
    # Google
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-2.5-pro": (1.25, 10.0),
    "gemini-1.5-pro": (1.25, 5.00),
    "gemini-1.5-flash": (0.075, 0.30),
    # Local / open-weights -- effectively free, but priced as $0 explicitly so
    # cost totals don't silently look like budget for hosted models.
    "gpt-oss-120b": (0.0, 0.0),
    "gpt-oss-20b": (0.0, 0.0),
    "gemma-4-e4b": (0.0, 0.0),
    "gemma-4-26b-a4b": (0.0, 0.0),
    # SambaNova-hosted via Tejas -- public list pricing as of 2026-04.
    "llama-4-maverick-17b-128e-instruct": (0.39, 1.56),
    "meta-llama-3.3-70b-instruct": (0.60, 1.20),
}


def _normalize(model_name: str) -> str:
    if ":" in model_name:
        model_name = model_name.split(":", 1)[1]
    if "/" in model_name:
        model_name = model_name.split("/", 1)[1]
    return model_name.lower().replace("claude-", "")


def model_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Cost in dollars for one model call. $0 for unknown / local models."""
    in_price, out_price = _PRICING.get(_normalize(model), (0.0, 0.0))
    return round(input_tokens / 1_000_000 * in_price + output_tokens / 1_000_000 * out_price, 6)
