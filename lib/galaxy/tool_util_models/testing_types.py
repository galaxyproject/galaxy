"""Shared TypedDicts for tool test definitions and assertion structures.

These live in ``tool_util_models`` so both ``tool_util_models`` and
``tool_util.parser`` can depend on them without creating a circular import.
"""

from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from typing_extensions import TypedDict


class AssertionDict(TypedDict):
    tag: str
    attributes: Dict[str, Any]
    children: "AssertionList"


AssertionList = Optional[List[AssertionDict]]


class DirectCredentialValue(TypedDict):
    """Represents a credential value (variable or secret) provided directly."""

    name: str
    value: str


class _DirectCredentialRequired(TypedDict):
    name: str
    variables: List[DirectCredentialValue]
    secrets: List[DirectCredentialValue]


class DirectCredential(_DirectCredentialRequired, total=False):
    """Represents a credential group with variables and secrets provided directly."""

    version: str
