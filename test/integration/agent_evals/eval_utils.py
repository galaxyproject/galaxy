"""Shared utilities for agent evaluation tests."""


def calculate_model_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate API cost for a given model and token usage.

    Pricing as of 2024:
    - claude-opus-4-6: $15/1M input, $75/1M output
    - claude-sonnet-4-5: $3/1M input, $15/1M output
    - claude-haiku-4-5: $0.80/1M input, $4/1M output

    Args:
        model_name: Model identifier (e.g., "claude-sonnet-4-5", "anthropic:claude-sonnet-4-5")
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Total cost in dollars
    """
    # Extract model name from full identifier if needed
    if ":" in model_name:
        model_name = model_name.split(":")[-1]

    # Normalize model name (remove "anthropic:" prefix, handle variations)
    model_name = model_name.lower().replace("anthropic:", "").replace("claude-", "")

    # Define pricing per million tokens (input, output)
    pricing = {
        "opus-4-6": (15.0, 75.0),
        "opus-4": (15.0, 75.0),  # Alias
        "sonnet-4-5": (3.0, 15.0),
        "sonnet-4": (3.0, 15.0),  # Alias
        "haiku-4-5": (0.80, 4.0),
        "haiku-4": (0.80, 4.0),  # Alias
    }

    # Get pricing or use default (Sonnet 4.5 as fallback)
    input_price, output_price = pricing.get(model_name, (3.0, 15.0))

    # Calculate cost
    input_cost = (input_tokens / 1_000_000) * input_price
    output_cost = (output_tokens / 1_000_000) * output_price

    return round(input_cost + output_cost, 4)
