"""Validate an embed config against a generated visualization request model."""

from typing import Any

from pydantic import (
    BaseModel,
    ValidationError,
)

from galaxy.exceptions import RequestParameterInvalidException


def validate_against_model(pydantic_model: type[BaseModel], parameter_state: dict[str, Any]) -> None:
    try:
        pydantic_model(**parameter_state)
    except ValidationError as e:
        raise RequestParameterInvalidException(str(e))
