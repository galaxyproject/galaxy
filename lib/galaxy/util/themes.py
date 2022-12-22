from typing import (
    Dict,
    Union,
)

Theme = Dict[str, Union["Theme", str]]


def flatten_theme(theme: Theme, prefix: str = "-") -> Dict[str, str]:
    """Transforms a nested theme dictionary into a flat dictionary,
    containing keys compatible with css variables. e.g. '--masthead-background-color'"""
    flat_attributes: Dict[str, str] = {}

    for key, val in theme.items():
        if isinstance(val, str):
            flat_attributes[f"{prefix}-{key}"] = val
        elif isinstance(val, Dict):
            flat_attributes.update(flatten_theme(val, f"{prefix}-{key}"))

    return flat_attributes
