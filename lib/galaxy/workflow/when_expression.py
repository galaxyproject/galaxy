"""Static analysis helpers for workflow step ``when`` expressions.

The analyzer recognizes the property-access forms Galaxy documents for the
``inputs`` object without executing user JavaScript. Unsupported or computed
accesses are reported as dynamic so callers can handle them conservatively.
"""

import re
from dataclasses import dataclass
from typing import (
    Literal,
    TypeAlias,
)
from collections.abc import Sequence

InputPathSegment: TypeAlias = str | int | float
InputPath: TypeAlias = list[InputPathSegment]
TokenType: TypeAlias = Literal["identifier", "number", "string", "punct"]


@dataclass(frozen=True)
class ReferenceAnalysis:
    """The statically resolved and dynamic ``inputs`` accesses in an expression."""

    static_paths: list[InputPath]
    has_dynamic_inputs_access: bool


@dataclass(frozen=True)
class _Token:
    type: TokenType
    value: str


@dataclass(frozen=True)
class _AccessPath:
    segments: InputPath
    dynamic: bool


_PUNCTUATORS = ("===", "!==", "==", "!=", "&&", "||", "!", "(", ")", "[", "]", ".", ",", "?", ":")


def analyze_input_references(expression: str) -> ReferenceAnalysis:
    """Collect every statically resolvable access rooted at ``inputs``."""

    tokens = _tokenize(expression)
    if tokens is None:
        return ReferenceAnalysis([], True)

    static_paths: list[InputPath] = []
    has_dynamic_inputs_access = "`" in expression
    for position, token in enumerate(tokens):
        if token.type != "identifier" or token.value != "inputs":
            continue
        if position > 0 and tokens[position - 1].value == ".":
            continue
        path = _read_access_path(tokens, position + 1)
        if path.dynamic or not path.segments:
            has_dynamic_inputs_access = True
        if path.segments:
            static_paths.append(path.segments)

    return ReferenceAnalysis(static_paths, has_dynamic_inputs_access)


def expression_references_input(expression: str | None, input: str | Sequence[InputPathSegment]) -> bool:
    """Return whether an expression could read a named workflow connection."""

    if not expression:
        return False
    target_path: Sequence[InputPathSegment] = input.split("|") if isinstance(input, str) else input
    references = analyze_input_references(expression)
    if references.has_dynamic_inputs_access:
        return True
    return any(_input_path_is_prefix(target_path, referenced_path) for referenced_path in references.static_paths)


def _tokenize(expression: str) -> list[_Token] | None:
    tokens: list[_Token] = []
    index = 0

    while index < len(expression):
        char = expression[index]
        if char.isspace():
            index += 1
            continue

        if expression.startswith("//", index):
            newline = expression.find("\n", index)
            index = len(expression) if newline == -1 else newline
            continue

        if expression.startswith("/*", index):
            end = expression.find("*/", index + 2)
            if end == -1:
                return None
            index = end + 2
            continue

        if char == "/":
            if not _can_start_regex(tokens):
                return None
            next_index = _read_regex_literal(expression, index)
            if next_index is None:
                return None
            index = next_index
            continue

        if char in {'"', "'", "`"}:
            literal = _read_string_literal(expression, index)
            if literal is None:
                return None
            value, index = literal
            tokens.append(_Token("string", value))
            continue

        if char.isascii() and char.isdigit():
            match = re.match(r"[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", expression[index:])
            assert match
            value = match.group(0)
            tokens.append(_Token("number", value))
            index += len(value)
            continue

        if char.isascii() and (char.isalpha() or char in "_$"):
            match = re.match(r"[A-Za-z_$][A-Za-z0-9_$]*", expression[index:])
            assert match
            value = match.group(0)
            tokens.append(_Token("identifier", value))
            index += len(value)
            continue

        punctuator = next((candidate for candidate in _PUNCTUATORS if expression.startswith(candidate, index)), char)
        tokens.append(_Token("punct", punctuator))
        index += len(punctuator)

    return tokens


def _can_start_regex(tokens: list[_Token]) -> bool:
    if not tokens:
        return True
    previous = tokens[-1]
    return previous.type == "punct" and previous.value not in (")", "]", ".")


def _read_regex_literal(expression: str, start: int) -> int | None:
    index = start + 1
    in_character_class = False

    while index < len(expression):
        char = expression[index]
        if char == "\\":
            index += 2
            continue
        if char == "[":
            in_character_class = True
        elif char == "]":
            in_character_class = False
        elif char == "/" and not in_character_class:
            index += 1
            while index < len(expression) and expression[index].isascii() and expression[index].isalpha():
                index += 1
            return index
        elif char in "\n\r":
            return None
        index += 1

    return None


def _read_string_literal(expression: str, start: int) -> tuple[str, int] | None:
    quote = expression[start]
    value = ""
    index = start + 1

    while index < len(expression):
        char = expression[index]
        if char == "\\":
            value += expression[index + 1] if index + 1 < len(expression) else ""
            index += 2
            continue
        if char == quote:
            return value, index + 1
        value += char
        index += 1

    return None


def _read_access_path(tokens: list[_Token], start: int) -> _AccessPath:
    segments: InputPath = []
    index = start

    while True:
        if index + 1 < len(tokens) and tokens[index].value == "?" and tokens[index + 1].value in (".", "["):
            if tokens[index + 1].value == "." and index + 2 < len(tokens) and tokens[index + 2].value == "[":
                index += 2
            else:
                index += 1

        if index + 1 < len(tokens) and tokens[index].value == "." and tokens[index + 1].type == "identifier":
            segments.append(tokens[index + 1].value)
            index += 2
            continue

        if index < len(tokens) and tokens[index].value == "[":
            if index + 2 < len(tokens):
                inner = tokens[index + 1]
                if inner.type in ("string", "number") and tokens[index + 2].value == "]":
                    if inner.type == "number":
                        number = (
                            float(inner.value) if any(marker in inner.value for marker in ".eE") else int(inner.value)
                        )
                        segments.append(number)
                    else:
                        segments.append(inner.value)
                    index += 3
                    continue
            return _AccessPath(segments, True)

        return _AccessPath(segments, False)


def _input_path_is_prefix(target_path: Sequence[InputPathSegment], referenced_path: Sequence[InputPathSegment]) -> bool:
    if len(target_path) > len(referenced_path):
        return False
    return all(segment == referenced_path[position] for position, segment in enumerate(target_path))
