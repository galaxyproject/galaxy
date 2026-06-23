"""This module is auto-generated, please do not modify."""

import re
import typing

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    model_validator,
    RootModel,
    StrictFloat,
    StrictInt,
)
from typing_extensions import (
    Annotated,
    Literal,
)

BYTES_PATTERN = re.compile(r"^(0|[1-9][0-9]*)([kKMGTPE]i?)?$")


class AssertionModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )


def check_bytes(v: typing.Any) -> typing.Any:
    if isinstance(v, str):
        assert BYTES_PATTERN.match(v), "Not valid bytes string"
    return v


def check_center_of_mass(v: typing.Any):
    assert isinstance(v, str)
    split_parts = v.split(",")
    assert len(split_parts) == 2
    for part in split_parts:
        assert float(part.strip())
    return v


def check_regex(v: typing.Any):
    assert isinstance(v, str)
    try:
        re.compile(v)
    except re.error:
        raise AssertionError(f"Invalid regular expression {v}")
    return v


def check_non_negative_if_set(v: typing.Any):
    if v is not None:
        try:
            assert float(v) >= 0
        except TypeError:
            raise AssertionError(f"Invalid type found {v}")
    return v


def check_non_negative_if_int(v: typing.Any):
    if v is not None and isinstance(v, int):
        assert v >= 0
    return v


has_line_line_description = """The full line of text to search for in the output."""

has_line_n_description = """Desired number, can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_line_delta_description = (
    """Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``"""
)

has_line_min_description = """Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_line_max_description = """Maximum number (default: infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_line_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class base_has_line_model(AssertionModel):
    """base model for has_line describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_line_model")

    line: str = Field(
        ...,
        title="Line",
        description=has_line_line_description,
    )

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="N",
        description=has_line_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        title="Delta",
        description=has_line_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Min",
        description=has_line_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Max",
        description=has_line_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_line_negate_description,
    )


class base_has_line_model_relaxed(AssertionModel):
    """base model for has_line describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_line_model_relaxed")

    line: str = Field(
        ...,
        title="Line",
        description=has_line_line_description,
    )

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="N",
        description=has_line_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        title="Delta",
        description=has_line_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Min",
        description=has_line_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Max",
        description=has_line_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_line_negate_description,
    )


class has_line_model(base_has_line_model):
    r"""Asserts the specified output contains the line specified by the
    argument line. The exact number of occurrences can be optionally
    specified by the argument n"""

    model_config = ConfigDict(extra="forbid", title="Assert Has Line")
    that: Literal["has_line"] = Field("has_line", title="That")


class has_line_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Line (Nested)")
    has_line: base_has_line_model = Field(..., title="Assert Has Line")


class has_line_model_relaxed(base_has_line_model_relaxed):
    r"""Asserts the specified output contains the line specified by the
    argument line. The exact number of occurrences can be optionally
    specified by the argument n"""

    model_config = ConfigDict(extra="forbid", title="Assert Has Line (Relaxed)")
    that: Literal["has_line"] = Field("has_line", title="That")


has_line_matching_expression_description = """The regular expressions to attempt match in the output."""

has_line_matching_n_description = """Desired number, can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_line_matching_delta_description = (
    """Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``"""
)

has_line_matching_min_description = """Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_line_matching_max_description = """Maximum number (default: infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_line_matching_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class base_has_line_matching_model(AssertionModel):
    """base model for has_line_matching describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_line_matching_model")

    expression: str = Field(
        ...,
        title="Expression",
        description=has_line_matching_expression_description,
    )

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="N",
        description=has_line_matching_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        title="Delta",
        description=has_line_matching_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Min",
        description=has_line_matching_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Max",
        description=has_line_matching_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_line_matching_negate_description,
    )


class base_has_line_matching_model_relaxed(AssertionModel):
    """base model for has_line_matching describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_line_matching_model_relaxed")

    expression: str = Field(
        ...,
        title="Expression",
        description=has_line_matching_expression_description,
    )

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="N",
        description=has_line_matching_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        title="Delta",
        description=has_line_matching_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Min",
        description=has_line_matching_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Max",
        description=has_line_matching_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_line_matching_negate_description,
    )


class has_line_matching_model(base_has_line_matching_model):
    r"""Asserts the specified output contains a line matching the
    regular expression specified by the argument expression. If n is given
    the assertion checks for exactly n occurrences."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Line Matching")
    that: Literal["has_line_matching"] = Field("has_line_matching", title="That")


class has_line_matching_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Line Matching (Nested)")
    has_line_matching: base_has_line_matching_model = Field(..., title="Assert Has Line Matching")


class has_line_matching_model_relaxed(base_has_line_matching_model_relaxed):
    r"""Asserts the specified output contains a line matching the
    regular expression specified by the argument expression. If n is given
    the assertion checks for exactly n occurrences."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Line Matching (Relaxed)")
    that: Literal["has_line_matching"] = Field("has_line_matching", title="That")


has_n_lines_n_description = """Desired number, can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_n_lines_delta_description = (
    """Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``"""
)

has_n_lines_min_description = """Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_n_lines_max_description = """Maximum number (default: infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_n_lines_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class base_has_n_lines_model(AssertionModel):
    """base model for has_n_lines describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_n_lines_model")

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="N",
        description=has_n_lines_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        title="Delta",
        description=has_n_lines_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Min",
        description=has_n_lines_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Max",
        description=has_n_lines_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_n_lines_negate_description,
    )


class base_has_n_lines_model_relaxed(AssertionModel):
    """base model for has_n_lines describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_n_lines_model_relaxed")

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="N",
        description=has_n_lines_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        title="Delta",
        description=has_n_lines_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Min",
        description=has_n_lines_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Max",
        description=has_n_lines_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_n_lines_negate_description,
    )


class has_n_lines_model(base_has_n_lines_model):
    r"""Asserts the specified output contains ``n`` lines allowing
    for a difference in the number of lines (delta)
    or relative differebce in the number of lines"""

    model_config = ConfigDict(extra="forbid", title="Assert Has N Lines")
    that: Literal["has_n_lines"] = Field("has_n_lines", title="That")


class has_n_lines_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Has N Lines (Nested)")
    has_n_lines: base_has_n_lines_model = Field(..., title="Assert Has N Lines")


class has_n_lines_model_relaxed(base_has_n_lines_model_relaxed):
    r"""Asserts the specified output contains ``n`` lines allowing
    for a difference in the number of lines (delta)
    or relative differebce in the number of lines"""

    model_config = ConfigDict(extra="forbid", title="Assert Has N Lines (Relaxed)")
    that: Literal["has_n_lines"] = Field("has_n_lines", title="That")


has_text_text_description = """The text to search for in the output."""

has_text_n_description = """Desired number, can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_text_delta_description = (
    """Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``"""
)

has_text_min_description = """Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_text_max_description = """Maximum number (default: infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_text_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class base_has_text_model(AssertionModel):
    """base model for has_text describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_text_model")

    text: str = Field(
        ...,
        title="Text",
        description=has_text_text_description,
    )

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="N",
        description=has_text_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        title="Delta",
        description=has_text_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Min",
        description=has_text_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Max",
        description=has_text_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_text_negate_description,
    )


class base_has_text_model_relaxed(AssertionModel):
    """base model for has_text describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_text_model_relaxed")

    text: str = Field(
        ...,
        title="Text",
        description=has_text_text_description,
    )

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="N",
        description=has_text_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        title="Delta",
        description=has_text_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Min",
        description=has_text_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Max",
        description=has_text_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_text_negate_description,
    )


class has_text_model(base_has_text_model):
    r"""Asserts specified output contains the substring specified by
    the argument text. The exact number of occurrences can be
    optionally specified by the argument n"""

    model_config = ConfigDict(extra="forbid", title="Assert Has Text")
    that: Literal["has_text"] = Field("has_text", title="That")


class has_text_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Text (Nested)")
    has_text: base_has_text_model = Field(..., title="Assert Has Text")


class has_text_model_relaxed(base_has_text_model_relaxed):
    r"""Asserts specified output contains the substring specified by
    the argument text. The exact number of occurrences can be
    optionally specified by the argument n"""

    model_config = ConfigDict(extra="forbid", title="Assert Has Text (Relaxed)")
    that: Literal["has_text"] = Field("has_text", title="That")


has_text_matching_expression_description = """The regular expressions to attempt match in the output."""

has_text_matching_n_description = """Desired number, can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_text_matching_delta_description = (
    """Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``"""
)

has_text_matching_min_description = """Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_text_matching_max_description = """Maximum number (default: infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_text_matching_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class base_has_text_matching_model(AssertionModel):
    """base model for has_text_matching describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_text_matching_model")

    expression: str = Field(
        ...,
        title="Expression",
        description=has_text_matching_expression_description,
    )

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="N",
        description=has_text_matching_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        title="Delta",
        description=has_text_matching_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Min",
        description=has_text_matching_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Max",
        description=has_text_matching_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_text_matching_negate_description,
    )


class base_has_text_matching_model_relaxed(AssertionModel):
    """base model for has_text_matching describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_text_matching_model_relaxed")

    expression: str = Field(
        ...,
        title="Expression",
        description=has_text_matching_expression_description,
    )

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="N",
        description=has_text_matching_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        title="Delta",
        description=has_text_matching_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Min",
        description=has_text_matching_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Max",
        description=has_text_matching_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_text_matching_negate_description,
    )


class has_text_matching_model(base_has_text_matching_model):
    r"""Asserts the specified output contains text matching the
    regular expression specified by the argument expression.
    If n is given the assertion checks for exactly n (nonoverlapping)
    occurrences."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Text Matching")
    that: Literal["has_text_matching"] = Field("has_text_matching", title="That")


class has_text_matching_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Text Matching (Nested)")
    has_text_matching: base_has_text_matching_model = Field(..., title="Assert Has Text Matching")


class has_text_matching_model_relaxed(base_has_text_matching_model_relaxed):
    r"""Asserts the specified output contains text matching the
    regular expression specified by the argument expression.
    If n is given the assertion checks for exactly n (nonoverlapping)
    occurrences."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Text Matching (Relaxed)")
    that: Literal["has_text_matching"] = Field("has_text_matching", title="That")


not_has_text_text_description = """The text to search for in the output."""


class base_not_has_text_model(AssertionModel):
    """base model for not_has_text describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_not_has_text_model")

    text: str = Field(
        ...,
        title="Text",
        description=not_has_text_text_description,
    )


class base_not_has_text_model_relaxed(AssertionModel):
    """base model for not_has_text describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_not_has_text_model_relaxed")

    text: str = Field(
        ...,
        title="Text",
        description=not_has_text_text_description,
    )


class not_has_text_model(base_not_has_text_model):
    r"""Asserts specified output does not contain the substring
    specified by the argument text"""

    model_config = ConfigDict(extra="forbid", title="Assert Not Has Text")
    that: Literal["not_has_text"] = Field("not_has_text", title="That")


class not_has_text_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Not Has Text (Nested)")
    not_has_text: base_not_has_text_model = Field(..., title="Assert Not Has Text")


class not_has_text_model_relaxed(base_not_has_text_model_relaxed):
    r"""Asserts specified output does not contain the substring
    specified by the argument text"""

    model_config = ConfigDict(extra="forbid", title="Assert Not Has Text (Relaxed)")
    that: Literal["not_has_text"] = Field("not_has_text", title="That")


has_n_columns_n_description = """Desired number, can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_n_columns_delta_description = (
    """Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``"""
)

has_n_columns_min_description = """Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_n_columns_max_description = """Maximum number (default: infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_n_columns_sep_description = """Separator defining columns, default: tab"""

has_n_columns_comment_description = (
    """Comment character(s) used to skip comment lines (which should not be used for counting columns)"""
)

has_n_columns_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class base_has_n_columns_model(AssertionModel):
    """base model for has_n_columns describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_n_columns_model")

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="N",
        description=has_n_columns_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        title="Delta",
        description=has_n_columns_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Min",
        description=has_n_columns_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Max",
        description=has_n_columns_max_description,
    )

    sep: str = Field(
        "	",
        title="Sep",
        description=has_n_columns_sep_description,
    )

    comment: str = Field(
        "",
        title="Comment",
        description=has_n_columns_comment_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_n_columns_negate_description,
    )


class base_has_n_columns_model_relaxed(AssertionModel):
    """base model for has_n_columns describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_n_columns_model_relaxed")

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="N",
        description=has_n_columns_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        title="Delta",
        description=has_n_columns_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Min",
        description=has_n_columns_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Max",
        description=has_n_columns_max_description,
    )

    sep: str = Field(
        "	",
        title="Sep",
        description=has_n_columns_sep_description,
    )

    comment: str = Field(
        "",
        title="Comment",
        description=has_n_columns_comment_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_n_columns_negate_description,
    )


class has_n_columns_model(base_has_n_columns_model):
    r"""Asserts tabular output  contains the specified
    number (``n``) of columns.

    For instance, ``<has_n_columns n="3"/>``. The assertion tests only the first line.
    Number of columns can optionally also be specified with ``delta``. Alternatively the
    range of expected occurrences can be specified by ``min`` and/or ``max``.

    Optionally a column separator (``sep``, default is ``       ``) `and comment character(s)
    can be specified (``comment``, default is empty string). The first non-comment
    line is used for determining the number of columns."""

    model_config = ConfigDict(extra="forbid", title="Assert Has N Columns")
    that: Literal["has_n_columns"] = Field("has_n_columns", title="That")


class has_n_columns_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Has N Columns (Nested)")
    has_n_columns: base_has_n_columns_model = Field(..., title="Assert Has N Columns")


class has_n_columns_model_relaxed(base_has_n_columns_model_relaxed):
    r"""Asserts tabular output  contains the specified
    number (``n``) of columns.

    For instance, ``<has_n_columns n="3"/>``. The assertion tests only the first line.
    Number of columns can optionally also be specified with ``delta``. Alternatively the
    range of expected occurrences can be specified by ``min`` and/or ``max``.

    Optionally a column separator (``sep``, default is ``       ``) `and comment character(s)
    can be specified (``comment``, default is empty string). The first non-comment
    line is used for determining the number of columns."""

    model_config = ConfigDict(extra="forbid", title="Assert Has N Columns (Relaxed)")
    that: Literal["has_n_columns"] = Field("has_n_columns", title="That")


attribute_is_path_description = """The Python xpath-like expression to find the target element."""

attribute_is_attribute_description = """The XML attribute name to test against from the target XML element."""

attribute_is_text_description = """The expected attribute value to test against on the target XML element"""

attribute_is_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class base_attribute_is_model(AssertionModel):
    """base model for attribute_is describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_attribute_is_model")

    path: str = Field(
        ...,
        title="Path",
        description=attribute_is_path_description,
    )

    attribute: str = Field(
        ...,
        title="Attribute",
        description=attribute_is_attribute_description,
    )

    text: str = Field(
        ...,
        title="Text",
        description=attribute_is_text_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=attribute_is_negate_description,
    )


class base_attribute_is_model_relaxed(AssertionModel):
    """base model for attribute_is describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_attribute_is_model_relaxed")

    path: str = Field(
        ...,
        title="Path",
        description=attribute_is_path_description,
    )

    attribute: str = Field(
        ...,
        title="Attribute",
        description=attribute_is_attribute_description,
    )

    text: str = Field(
        ...,
        title="Text",
        description=attribute_is_text_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=attribute_is_negate_description,
    )


class attribute_is_model(base_attribute_is_model):
    r"""Asserts the XML ``attribute`` for the element (or tag) with the specified
    XPath-like ``path`` is the specified ``text``.

    For example:

    ```xml
    <attribute_is path="outerElement/innerElement1" attribute="foo" text="bar" />
    ```

    The assertion implicitly also asserts that an element matching ``path`` exists.
    With ``negate`` the result of the assertion (on the equality) can be inverted (the
    implicit assertion on the existence of the path is not affected)."""

    model_config = ConfigDict(extra="forbid", title="Assert Attribute Is")
    that: Literal["attribute_is"] = Field("attribute_is", title="That")


class attribute_is_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Attribute Is (Nested)")
    attribute_is: base_attribute_is_model = Field(..., title="Assert Attribute Is")


class attribute_is_model_relaxed(base_attribute_is_model_relaxed):
    r"""Asserts the XML ``attribute`` for the element (or tag) with the specified
    XPath-like ``path`` is the specified ``text``.

    For example:

    ```xml
    <attribute_is path="outerElement/innerElement1" attribute="foo" text="bar" />
    ```

    The assertion implicitly also asserts that an element matching ``path`` exists.
    With ``negate`` the result of the assertion (on the equality) can be inverted (the
    implicit assertion on the existence of the path is not affected)."""

    model_config = ConfigDict(extra="forbid", title="Assert Attribute Is (Relaxed)")
    that: Literal["attribute_is"] = Field("attribute_is", title="That")


attribute_matches_path_description = """The Python xpath-like expression to find the target element."""

attribute_matches_attribute_description = """The XML attribute name to test against from the target XML element."""

attribute_matches_expression_description = (
    """The regular expressions to apply against the named attribute on the target XML element."""
)

attribute_matches_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class base_attribute_matches_model(AssertionModel):
    """base model for attribute_matches describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_attribute_matches_model")

    path: str = Field(
        ...,
        title="Path",
        description=attribute_matches_path_description,
    )

    attribute: str = Field(
        ...,
        title="Attribute",
        description=attribute_matches_attribute_description,
    )

    expression: Annotated[str, BeforeValidator(check_regex)] = Field(
        ...,
        title="Expression",
        description=attribute_matches_expression_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=attribute_matches_negate_description,
    )


class base_attribute_matches_model_relaxed(AssertionModel):
    """base model for attribute_matches describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_attribute_matches_model_relaxed")

    path: str = Field(
        ...,
        title="Path",
        description=attribute_matches_path_description,
    )

    attribute: str = Field(
        ...,
        title="Attribute",
        description=attribute_matches_attribute_description,
    )

    expression: Annotated[str, BeforeValidator(check_regex)] = Field(
        ...,
        title="Expression",
        description=attribute_matches_expression_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=attribute_matches_negate_description,
    )


class attribute_matches_model(base_attribute_matches_model):
    r"""Asserts the XML ``attribute`` for the element (or tag) with the specified
    XPath-like ``path`` matches the regular expression specified by ``expression``.

    For example:

    ```xml
    <attribute_matches path="outerElement/innerElement2" attribute="foo2" expression="bar\d+" />
    ```

    The assertion implicitly also asserts that an element matching ``path`` exists.
    With ``negate`` the result of the assertion (on the matching) can be inverted (the
    implicit assertion on the existence of the path is not affected)."""

    model_config = ConfigDict(extra="forbid", title="Assert Attribute Matches")
    that: Literal["attribute_matches"] = Field("attribute_matches", title="That")


class attribute_matches_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Attribute Matches (Nested)")
    attribute_matches: base_attribute_matches_model = Field(..., title="Assert Attribute Matches")


class attribute_matches_model_relaxed(base_attribute_matches_model_relaxed):
    r"""Asserts the XML ``attribute`` for the element (or tag) with the specified
    XPath-like ``path`` matches the regular expression specified by ``expression``.

    For example:

    ```xml
    <attribute_matches path="outerElement/innerElement2" attribute="foo2" expression="bar\d+" />
    ```

    The assertion implicitly also asserts that an element matching ``path`` exists.
    With ``negate`` the result of the assertion (on the matching) can be inverted (the
    implicit assertion on the existence of the path is not affected)."""

    model_config = ConfigDict(extra="forbid", title="Assert Attribute Matches (Relaxed)")
    that: Literal["attribute_matches"] = Field("attribute_matches", title="That")


element_text_path_description = """The Python xpath-like expression to find the target element."""

element_text_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class base_element_text_model(AssertionModel):
    """base model for element_text describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_element_text_model")

    path: str = Field(
        ...,
        title="Path",
        description=element_text_path_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=element_text_negate_description,
    )

    children: typing.Optional["assertion_list"] = Field(None, title="Children")
    asserts: typing.Optional["assertion_list"] = Field(None, title="Asserts")

    @model_validator(mode="before")
    @classmethod
    def validate_children(self, data: typing.Any):
        if isinstance(data, dict) and "children" not in data and "asserts" not in data:
            raise ValueError("At least one of 'children' or 'asserts' must be specified for this assertion type.")
        return data


class base_element_text_model_relaxed(AssertionModel):
    """base model for element_text describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_element_text_model_relaxed")

    path: str = Field(
        ...,
        title="Path",
        description=element_text_path_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=element_text_negate_description,
    )

    children: typing.Optional["assertion_list"] = Field(None, title="Children")
    asserts: typing.Optional["assertion_list"] = Field(None, title="Asserts")

    @model_validator(mode="before")
    @classmethod
    def validate_children(self, data: typing.Any):
        if isinstance(data, dict) and "children" not in data and "asserts" not in data:
            raise ValueError("At least one of 'children' or 'asserts' must be specified for this assertion type.")
        return data


class element_text_model(base_element_text_model):
    r"""This tag allows the developer to recurisively specify additional assertions as
    child elements about just the text contained in the element specified by the
    XPath-like ``path``, e.g.

    ```xml
    <element_text path="BlastOutput_iterations/Iteration/Iteration_hits/Hit/Hit_def">
      <not_has_text text="EDK72998.1" />
    </element_text>
    ```

    The assertion implicitly also asserts that an element matching ``path`` exists.
    With ``negate`` the result of the implicit assertions can be inverted.
    The sub-assertions, which have their own ``negate`` attribute, are not affected
    by ``negate``."""

    model_config = ConfigDict(extra="forbid", title="Assert Element Text")
    that: Literal["element_text"] = Field("element_text", title="That")


class element_text_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Element Text (Nested)")
    element_text: base_element_text_model = Field(..., title="Assert Element Text")


class element_text_model_relaxed(base_element_text_model_relaxed):
    r"""This tag allows the developer to recurisively specify additional assertions as
    child elements about just the text contained in the element specified by the
    XPath-like ``path``, e.g.

    ```xml
    <element_text path="BlastOutput_iterations/Iteration/Iteration_hits/Hit/Hit_def">
      <not_has_text text="EDK72998.1" />
    </element_text>
    ```

    The assertion implicitly also asserts that an element matching ``path`` exists.
    With ``negate`` the result of the implicit assertions can be inverted.
    The sub-assertions, which have their own ``negate`` attribute, are not affected
    by ``negate``."""

    model_config = ConfigDict(extra="forbid", title="Assert Element Text (Relaxed)")
    that: Literal["element_text"] = Field("element_text", title="That")


element_text_is_path_description = """The Python xpath-like expression to find the target element."""

element_text_is_text_description = (
    """The expected element text (body of the XML tag) to test against on the target XML element"""
)

element_text_is_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class base_element_text_is_model(AssertionModel):
    """base model for element_text_is describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_element_text_is_model")

    path: str = Field(
        ...,
        title="Path",
        description=element_text_is_path_description,
    )

    text: str = Field(
        ...,
        title="Text",
        description=element_text_is_text_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=element_text_is_negate_description,
    )


class base_element_text_is_model_relaxed(AssertionModel):
    """base model for element_text_is describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_element_text_is_model_relaxed")

    path: str = Field(
        ...,
        title="Path",
        description=element_text_is_path_description,
    )

    text: str = Field(
        ...,
        title="Text",
        description=element_text_is_text_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=element_text_is_negate_description,
    )


class element_text_is_model(base_element_text_is_model):
    r"""Asserts the text of the XML element with the specified XPath-like ``path`` is
    the specified ``text``.

    For example:

    ```xml
    <element_text_is path="BlastOutput_program" text="blastp" />
    ```

    The assertion implicitly also asserts that an element matching ``path`` exists.
    With ``negate`` the result of the assertion (on the equality) can be inverted (the
    implicit assertion on the existence of the path is not affected)."""

    model_config = ConfigDict(extra="forbid", title="Assert Element Text Is")
    that: Literal["element_text_is"] = Field("element_text_is", title="That")


class element_text_is_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Element Text Is (Nested)")
    element_text_is: base_element_text_is_model = Field(..., title="Assert Element Text Is")


class element_text_is_model_relaxed(base_element_text_is_model_relaxed):
    r"""Asserts the text of the XML element with the specified XPath-like ``path`` is
    the specified ``text``.

    For example:

    ```xml
    <element_text_is path="BlastOutput_program" text="blastp" />
    ```

    The assertion implicitly also asserts that an element matching ``path`` exists.
    With ``negate`` the result of the assertion (on the equality) can be inverted (the
    implicit assertion on the existence of the path is not affected)."""

    model_config = ConfigDict(extra="forbid", title="Assert Element Text Is (Relaxed)")
    that: Literal["element_text_is"] = Field("element_text_is", title="That")


element_text_matches_path_description = """The Python xpath-like expression to find the target element."""

element_text_matches_expression_description = """The regular expressions to apply against the target element."""

element_text_matches_negate_description = (
    """A boolean that can be set to true to negate the outcome of the assertion."""
)


class base_element_text_matches_model(AssertionModel):
    """base model for element_text_matches describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_element_text_matches_model")

    path: str = Field(
        ...,
        title="Path",
        description=element_text_matches_path_description,
    )

    expression: Annotated[str, BeforeValidator(check_regex)] = Field(
        ...,
        title="Expression",
        description=element_text_matches_expression_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=element_text_matches_negate_description,
    )


class base_element_text_matches_model_relaxed(AssertionModel):
    """base model for element_text_matches describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_element_text_matches_model_relaxed")

    path: str = Field(
        ...,
        title="Path",
        description=element_text_matches_path_description,
    )

    expression: Annotated[str, BeforeValidator(check_regex)] = Field(
        ...,
        title="Expression",
        description=element_text_matches_expression_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=element_text_matches_negate_description,
    )


class element_text_matches_model(base_element_text_matches_model):
    r"""Asserts the text of the XML element with the specified XPath-like ``path``
    matches the regular expression defined by ``expression``.

    For example:

    ```xml
    <element_text_matches path="BlastOutput_version" expression="BLASTP\s+2\.2.*"/>
    ```

    The assertion implicitly also asserts that an element matching ``path`` exists.
    With ``negate`` the result of the assertion (on the matching) can be inverted (the
    implicit assertion on the existence of the path is not affected)."""

    model_config = ConfigDict(extra="forbid", title="Assert Element Text Matches")
    that: Literal["element_text_matches"] = Field("element_text_matches", title="That")


class element_text_matches_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Element Text Matches (Nested)")
    element_text_matches: base_element_text_matches_model = Field(..., title="Assert Element Text Matches")


class element_text_matches_model_relaxed(base_element_text_matches_model_relaxed):
    r"""Asserts the text of the XML element with the specified XPath-like ``path``
    matches the regular expression defined by ``expression``.

    For example:

    ```xml
    <element_text_matches path="BlastOutput_version" expression="BLASTP\s+2\.2.*"/>
    ```

    The assertion implicitly also asserts that an element matching ``path`` exists.
    With ``negate`` the result of the assertion (on the matching) can be inverted (the
    implicit assertion on the existence of the path is not affected)."""

    model_config = ConfigDict(extra="forbid", title="Assert Element Text Matches (Relaxed)")
    that: Literal["element_text_matches"] = Field("element_text_matches", title="That")


has_element_with_path_path_description = """The Python xpath-like expression to find the target element."""

has_element_with_path_negate_description = (
    """A boolean that can be set to true to negate the outcome of the assertion."""
)


class base_has_element_with_path_model(AssertionModel):
    """base model for has_element_with_path describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_element_with_path_model")

    path: str = Field(
        ...,
        title="Path",
        description=has_element_with_path_path_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_element_with_path_negate_description,
    )


class base_has_element_with_path_model_relaxed(AssertionModel):
    """base model for has_element_with_path describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_element_with_path_model_relaxed")

    path: str = Field(
        ...,
        title="Path",
        description=has_element_with_path_path_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_element_with_path_negate_description,
    )


class has_element_with_path_model(base_has_element_with_path_model):
    r"""Asserts the XML output contains at least one element (or tag) with the specified
    XPath-like ``path``, e.g.

    ```xml
    <has_element_with_path path="BlastOutput_param/Parameters/Parameters_matrix" />
    ```

    With ``negate`` the result of the assertion can be inverted."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Element With Path")
    that: Literal["has_element_with_path"] = Field("has_element_with_path", title="That")


class has_element_with_path_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Element With Path (Nested)")
    has_element_with_path: base_has_element_with_path_model = Field(..., title="Assert Has Element With Path")


class has_element_with_path_model_relaxed(base_has_element_with_path_model_relaxed):
    r"""Asserts the XML output contains at least one element (or tag) with the specified
    XPath-like ``path``, e.g.

    ```xml
    <has_element_with_path path="BlastOutput_param/Parameters/Parameters_matrix" />
    ```

    With ``negate`` the result of the assertion can be inverted."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Element With Path (Relaxed)")
    that: Literal["has_element_with_path"] = Field("has_element_with_path", title="That")


has_n_elements_with_path_path_description = """The Python xpath-like expression to find the target element."""

has_n_elements_with_path_n_description = """Desired number, can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_n_elements_with_path_delta_description = (
    """Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``"""
)

has_n_elements_with_path_min_description = (
    """Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""
)

has_n_elements_with_path_max_description = (
    """Maximum number (default: infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""
)

has_n_elements_with_path_negate_description = (
    """A boolean that can be set to true to negate the outcome of the assertion."""
)


class base_has_n_elements_with_path_model(AssertionModel):
    """base model for has_n_elements_with_path describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_n_elements_with_path_model")

    path: str = Field(
        ...,
        title="Path",
        description=has_n_elements_with_path_path_description,
    )

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="N",
        description=has_n_elements_with_path_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        title="Delta",
        description=has_n_elements_with_path_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Min",
        description=has_n_elements_with_path_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Max",
        description=has_n_elements_with_path_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_n_elements_with_path_negate_description,
    )


class base_has_n_elements_with_path_model_relaxed(AssertionModel):
    """base model for has_n_elements_with_path describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_n_elements_with_path_model_relaxed")

    path: str = Field(
        ...,
        title="Path",
        description=has_n_elements_with_path_path_description,
    )

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="N",
        description=has_n_elements_with_path_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        title="Delta",
        description=has_n_elements_with_path_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Min",
        description=has_n_elements_with_path_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Max",
        description=has_n_elements_with_path_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_n_elements_with_path_negate_description,
    )


class has_n_elements_with_path_model(base_has_n_elements_with_path_model):
    r"""Asserts the XML output contains the specified number (``n``, optionally with ``delta``) of elements (or
    tags) with the specified XPath-like ``path``.

    For example:

    ```xml
    <has_n_elements_with_path n="9" path="BlastOutput_iterations/Iteration/Iteration_hits/Hit/Hit_num" />
    ```

    Alternatively to ``n`` and ``delta`` also the ``min`` and ``max`` attributes
    can be used to specify the range of the expected number of occurrences.
    With ``negate`` the result of the assertion can be inverted."""

    model_config = ConfigDict(extra="forbid", title="Assert Has N Elements With Path")
    that: Literal["has_n_elements_with_path"] = Field("has_n_elements_with_path", title="That")


class has_n_elements_with_path_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Has N Elements With Path (Nested)")
    has_n_elements_with_path: base_has_n_elements_with_path_model = Field(..., title="Assert Has N Elements With Path")


class has_n_elements_with_path_model_relaxed(base_has_n_elements_with_path_model_relaxed):
    r"""Asserts the XML output contains the specified number (``n``, optionally with ``delta``) of elements (or
    tags) with the specified XPath-like ``path``.

    For example:

    ```xml
    <has_n_elements_with_path n="9" path="BlastOutput_iterations/Iteration/Iteration_hits/Hit/Hit_num" />
    ```

    Alternatively to ``n`` and ``delta`` also the ``min`` and ``max`` attributes
    can be used to specify the range of the expected number of occurrences.
    With ``negate`` the result of the assertion can be inverted."""

    model_config = ConfigDict(extra="forbid", title="Assert Has N Elements With Path (Relaxed)")
    that: Literal["has_n_elements_with_path"] = Field("has_n_elements_with_path", title="That")


class base_is_valid_xml_model(AssertionModel):
    """base model for is_valid_xml describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_is_valid_xml_model")


class base_is_valid_xml_model_relaxed(AssertionModel):
    """base model for is_valid_xml describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_is_valid_xml_model_relaxed")


class is_valid_xml_model(base_is_valid_xml_model):
    r"""Asserts the output is a valid XML file (e.g. ``<is_valid_xml />``)."""

    model_config = ConfigDict(extra="forbid", title="Assert Is Valid Xml")
    that: Literal["is_valid_xml"] = Field("is_valid_xml", title="That")


class is_valid_xml_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Is Valid Xml (Nested)")
    is_valid_xml: base_is_valid_xml_model = Field(..., title="Assert Is Valid Xml")


class is_valid_xml_model_relaxed(base_is_valid_xml_model_relaxed):
    r"""Asserts the output is a valid XML file (e.g. ``<is_valid_xml />``)."""

    model_config = ConfigDict(extra="forbid", title="Assert Is Valid Xml (Relaxed)")
    that: Literal["is_valid_xml"] = Field("is_valid_xml", title="That")


xml_element_path_description = """The Python xpath-like expression to find the target element."""

xml_element_attribute_description = """The XML attribute name to test against from the target XML element."""

xml_element_all_description = (
    """Check the sub-assertions for all paths matching the path. Default: false, i.e. only the first """
)

xml_element_n_description = """Desired number, can be suffixed by ``(k|M|G|T|P|E)i?``"""

xml_element_delta_description = (
    """Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``"""
)

xml_element_min_description = """Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

xml_element_max_description = """Maximum number (default: infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

xml_element_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class base_xml_element_model(AssertionModel):
    """base model for xml_element describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_xml_element_model")

    path: str = Field(
        ...,
        title="Path",
        description=xml_element_path_description,
    )

    attribute: typing.Optional[typing.Union[str]] = Field(
        None,
        title="Attribute",
        description=xml_element_attribute_description,
    )

    all: typing.Union[bool, str] = Field(
        False,
        title="All",
        description=xml_element_all_description,
    )

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="N",
        description=xml_element_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        title="Delta",
        description=xml_element_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Min",
        description=xml_element_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Max",
        description=xml_element_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=xml_element_negate_description,
    )

    children: typing.Optional["assertion_list"] = Field(None, title="Children")
    asserts: typing.Optional["assertion_list"] = Field(None, title="Asserts")


class base_xml_element_model_relaxed(AssertionModel):
    """base model for xml_element describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_xml_element_model_relaxed")

    path: str = Field(
        ...,
        title="Path",
        description=xml_element_path_description,
    )

    attribute: typing.Optional[typing.Union[str]] = Field(
        None,
        title="Attribute",
        description=xml_element_attribute_description,
    )

    all: typing.Union[bool, str] = Field(
        False,
        title="All",
        description=xml_element_all_description,
    )

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="N",
        description=xml_element_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        title="Delta",
        description=xml_element_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Min",
        description=xml_element_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Max",
        description=xml_element_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=xml_element_negate_description,
    )

    children: typing.Optional["assertion_list"] = Field(None, title="Children")
    asserts: typing.Optional["assertion_list"] = Field(None, title="Asserts")


class xml_element_model(base_xml_element_model):
    r"""Assert if the XML file contains element(s) or tag(s) with the specified
    [XPath-like ``path``](https://lxml.de/xpathxslt.html).  If ``n`` and ``delta``
    or ``min`` and ``max`` are given also the number of occurrences is checked.

    ```xml
    <assert_contents>
      <xml_element path="./elem"/>
      <xml_element path="./elem/more[2]"/>
      <xml_element path=".//more" n="3" delta="1"/>
    </assert_contents>
    ```

    With ``negate="true"`` the outcome of the assertions wrt the presence and number
    of ``path`` can be negated. If there are any sub assertions then check them against

    - the content of the attribute ``attribute``
    - the element's text if no attribute is given

    ```xml
    <assert_contents>
      <xml_element path="./elem/more[2]" attribute="name">
        <has_text_matching expression="foo$"/>
      </xml_element>
    </assert_contents>
    ```

    Sub-assertions are not subject to the ``negate`` attribute of ``xml_element``.
    If ``all`` is ``true`` then the sub assertions are checked for all occurrences.

    Note that all other XML assertions can be expressed by this assertion (Galaxy
    also implements the other assertions by calling this one)."""

    model_config = ConfigDict(extra="forbid", title="Assert Xml Element")
    that: Literal["xml_element"] = Field("xml_element", title="That")


class xml_element_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Xml Element (Nested)")
    xml_element: base_xml_element_model = Field(..., title="Assert Xml Element")


class xml_element_model_relaxed(base_xml_element_model_relaxed):
    r"""Assert if the XML file contains element(s) or tag(s) with the specified
    [XPath-like ``path``](https://lxml.de/xpathxslt.html).  If ``n`` and ``delta``
    or ``min`` and ``max`` are given also the number of occurrences is checked.

    ```xml
    <assert_contents>
      <xml_element path="./elem"/>
      <xml_element path="./elem/more[2]"/>
      <xml_element path=".//more" n="3" delta="1"/>
    </assert_contents>
    ```

    With ``negate="true"`` the outcome of the assertions wrt the presence and number
    of ``path`` can be negated. If there are any sub assertions then check them against

    - the content of the attribute ``attribute``
    - the element's text if no attribute is given

    ```xml
    <assert_contents>
      <xml_element path="./elem/more[2]" attribute="name">
        <has_text_matching expression="foo$"/>
      </xml_element>
    </assert_contents>
    ```

    Sub-assertions are not subject to the ``negate`` attribute of ``xml_element``.
    If ``all`` is ``true`` then the sub assertions are checked for all occurrences.

    Note that all other XML assertions can be expressed by this assertion (Galaxy
    also implements the other assertions by calling this one)."""

    model_config = ConfigDict(extra="forbid", title="Assert Xml Element (Relaxed)")
    that: Literal["xml_element"] = Field("xml_element", title="That")


has_json_property_with_text_property_description = """The property name to search the JSON document for."""

has_json_property_with_text_text_description = """The expected text value of the target JSON attribute."""


class base_has_json_property_with_text_model(AssertionModel):
    """base model for has_json_property_with_text describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_json_property_with_text_model")

    property: str = Field(
        ...,
        title="Property",
        description=has_json_property_with_text_property_description,
    )

    text: str = Field(
        ...,
        title="Text",
        description=has_json_property_with_text_text_description,
    )


class base_has_json_property_with_text_model_relaxed(AssertionModel):
    """base model for has_json_property_with_text describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_json_property_with_text_model_relaxed")

    property: str = Field(
        ...,
        title="Property",
        description=has_json_property_with_text_property_description,
    )

    text: str = Field(
        ...,
        title="Text",
        description=has_json_property_with_text_text_description,
    )


class has_json_property_with_text_model(base_has_json_property_with_text_model):
    r"""Asserts the JSON document contains a property or key with the specified text (i.e. string) value.

    ```xml
    <has_json_property_with_text property="color" text="red" />
    ```"""

    model_config = ConfigDict(extra="forbid", title="Assert Has Json Property With Text")
    that: Literal["has_json_property_with_text"] = Field("has_json_property_with_text", title="That")


class has_json_property_with_text_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Json Property With Text (Nested)")
    has_json_property_with_text: base_has_json_property_with_text_model = Field(
        ..., title="Assert Has Json Property With Text"
    )


class has_json_property_with_text_model_relaxed(base_has_json_property_with_text_model_relaxed):
    r"""Asserts the JSON document contains a property or key with the specified text (i.e. string) value.

    ```xml
    <has_json_property_with_text property="color" text="red" />
    ```"""

    model_config = ConfigDict(extra="forbid", title="Assert Has Json Property With Text (Relaxed)")
    that: Literal["has_json_property_with_text"] = Field("has_json_property_with_text", title="That")


has_json_property_with_value_property_description = """The property name to search the JSON document for."""

has_json_property_with_value_value_description = (
    """The expected JSON value of the target JSON attribute (as a JSON encoded string)."""
)


class base_has_json_property_with_value_model(AssertionModel):
    """base model for has_json_property_with_value describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_json_property_with_value_model")

    property: str = Field(
        ...,
        title="Property",
        description=has_json_property_with_value_property_description,
    )

    value: str = Field(
        ...,
        title="Value",
        description=has_json_property_with_value_value_description,
    )


class base_has_json_property_with_value_model_relaxed(AssertionModel):
    """base model for has_json_property_with_value describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_json_property_with_value_model_relaxed")

    property: str = Field(
        ...,
        title="Property",
        description=has_json_property_with_value_property_description,
    )

    value: str = Field(
        ...,
        title="Value",
        description=has_json_property_with_value_value_description,
    )


class has_json_property_with_value_model(base_has_json_property_with_value_model):
    r"""Asserts the JSON document contains a property or key with the specified JSON value.

    ```xml
    <has_json_property_with_value property="skipped_columns" value="[1, 3, 5]" />
    ```"""

    model_config = ConfigDict(extra="forbid", title="Assert Has Json Property With Value")
    that: Literal["has_json_property_with_value"] = Field("has_json_property_with_value", title="That")


class has_json_property_with_value_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Json Property With Value (Nested)")
    has_json_property_with_value: base_has_json_property_with_value_model = Field(
        ..., title="Assert Has Json Property With Value"
    )


class has_json_property_with_value_model_relaxed(base_has_json_property_with_value_model_relaxed):
    r"""Asserts the JSON document contains a property or key with the specified JSON value.

    ```xml
    <has_json_property_with_value property="skipped_columns" value="[1, 3, 5]" />
    ```"""

    model_config = ConfigDict(extra="forbid", title="Assert Has Json Property With Value (Relaxed)")
    that: Literal["has_json_property_with_value"] = Field("has_json_property_with_value", title="That")


has_h5_attribute_key_description = """HDF5 attribute to check value of."""

has_h5_attribute_value_description = """Expected value of HDF5 attribute to check."""


class base_has_h5_attribute_model(AssertionModel):
    """base model for has_h5_attribute describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_h5_attribute_model")

    key: str = Field(
        ...,
        title="Key",
        description=has_h5_attribute_key_description,
    )

    value: str = Field(
        ...,
        title="Value",
        description=has_h5_attribute_value_description,
    )


class base_has_h5_attribute_model_relaxed(AssertionModel):
    """base model for has_h5_attribute describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_h5_attribute_model_relaxed")

    key: str = Field(
        ...,
        title="Key",
        description=has_h5_attribute_key_description,
    )

    value: str = Field(
        ...,
        title="Value",
        description=has_h5_attribute_value_description,
    )


class has_h5_attribute_model(base_has_h5_attribute_model):
    r"""Asserts HDF5 output contains the specified ``value`` for an attribute (``key``), e.g.

    ```xml
    <has_h5_attribute key="nchroms" value="15" />
    ```"""

    model_config = ConfigDict(extra="forbid", title="Assert Has H5 Attribute")
    that: Literal["has_h5_attribute"] = Field("has_h5_attribute", title="That")


class has_h5_attribute_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Has H5 Attribute (Nested)")
    has_h5_attribute: base_has_h5_attribute_model = Field(..., title="Assert Has H5 Attribute")


class has_h5_attribute_model_relaxed(base_has_h5_attribute_model_relaxed):
    r"""Asserts HDF5 output contains the specified ``value`` for an attribute (``key``), e.g.

    ```xml
    <has_h5_attribute key="nchroms" value="15" />
    ```"""

    model_config = ConfigDict(extra="forbid", title="Assert Has H5 Attribute (Relaxed)")
    that: Literal["has_h5_attribute"] = Field("has_h5_attribute", title="That")


has_h5_keys_keys_description = """HDF5 attributes to check value of as a comma-separated string."""


class base_has_h5_keys_model(AssertionModel):
    """base model for has_h5_keys describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_h5_keys_model")

    keys: str = Field(
        ...,
        title="Keys",
        description=has_h5_keys_keys_description,
    )


class base_has_h5_keys_model_relaxed(AssertionModel):
    """base model for has_h5_keys describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_h5_keys_model_relaxed")

    keys: str = Field(
        ...,
        title="Keys",
        description=has_h5_keys_keys_description,
    )


class has_h5_keys_model(base_has_h5_keys_model):
    r"""Asserts the specified HDF5 output has the given keys."""

    model_config = ConfigDict(extra="forbid", title="Assert Has H5 Keys")
    that: Literal["has_h5_keys"] = Field("has_h5_keys", title="That")


class has_h5_keys_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Has H5 Keys (Nested)")
    has_h5_keys: base_has_h5_keys_model = Field(..., title="Assert Has H5 Keys")


class has_h5_keys_model_relaxed(base_has_h5_keys_model_relaxed):
    r"""Asserts the specified HDF5 output has the given keys."""

    model_config = ConfigDict(extra="forbid", title="Assert Has H5 Keys (Relaxed)")
    that: Literal["has_h5_keys"] = Field("has_h5_keys", title="That")


has_archive_member_path_description = """The regular expression specifying the archive member."""

has_archive_member_all_description = (
    """Check the sub-assertions for all paths matching the path. Default: false, i.e. only the first"""
)

has_archive_member_n_description = """Desired number, can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_archive_member_delta_description = (
    """Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``"""
)

has_archive_member_min_description = """Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_archive_member_max_description = """Maximum number (default: infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_archive_member_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class base_has_archive_member_model(AssertionModel):
    """base model for has_archive_member describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_archive_member_model")

    path: str = Field(
        ...,
        title="Path",
        description=has_archive_member_path_description,
    )

    all: typing.Union[bool, str] = Field(
        False,
        title="All",
        description=has_archive_member_all_description,
    )

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="N",
        description=has_archive_member_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        title="Delta",
        description=has_archive_member_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Min",
        description=has_archive_member_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Max",
        description=has_archive_member_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_archive_member_negate_description,
    )

    children: typing.Optional["assertion_list"] = Field(None, title="Children")
    asserts: typing.Optional["assertion_list"] = Field(None, title="Asserts")


class base_has_archive_member_model_relaxed(AssertionModel):
    """base model for has_archive_member describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_archive_member_model_relaxed")

    path: str = Field(
        ...,
        title="Path",
        description=has_archive_member_path_description,
    )

    all: typing.Union[bool, str] = Field(
        False,
        title="All",
        description=has_archive_member_all_description,
    )

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="N",
        description=has_archive_member_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        title="Delta",
        description=has_archive_member_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Min",
        description=has_archive_member_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Max",
        description=has_archive_member_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_archive_member_negate_description,
    )

    children: typing.Optional["assertion_list"] = Field(None, title="Children")
    asserts: typing.Optional["assertion_list"] = Field(None, title="Asserts")


class has_archive_member_model(base_has_archive_member_model):
    r"""This tag allows to check if ``path`` is contained in a compressed file.

    The path is a regular expression that is matched against the full paths of the objects in
    the compressed file (remember that "matching" means it is checked if a prefix of
    the full path of an archive member is described by the regular expression).
    Valid archive formats include ``.zip``, ``.tar``, and ``.tar.gz``. Note that
    depending on the archive creation method:

    - full paths of the members may be prefixed with ``./``
    - directories may be treated as empty files

    ```xml
    <has_archive_member path="./path/to/my-file.txt"/>
    ```

    With ``n`` and ``delta`` (or ``min`` and ``max``) assertions on the number of
    archive members matching ``path`` can be expressed. The following could be used,
    e.g., to assert an archive containing n&plusmn;1 elements out of which at least
    4 need to have a ``txt`` extension.

    ```xml
    <has_archive_member path=".*" n="10" delta="1"/>
    <has_archive_member path=".*\.txt" min="4"/>
    ```

    In addition the tag can contain additional assertions as child elements about
    the first member in the archive matching the regular expression ``path``. For
    instance

    ```xml
    <has_archive_member path=".*/my-file.txt">
      <not_has_text text="EDK72998.1"/>
    </has_archive_member>
    ```

    If the ``all`` attribute is set to ``true`` then all archive members are subject
    to the assertions. Note that, archive members matching the ``path`` are sorted
    alphabetically.

    The ``negate`` attribute of the ``has_archive_member`` assertion only affects
    the asserts on the presence and number of matching archive members, but not any
    sub-assertions (which can offer the ``negate`` attribute on their own).  The
    check if the file is an archive at all, which is also done by the function, is
    not affected."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Archive Member")
    that: Literal["has_archive_member"] = Field("has_archive_member", title="That")


class has_archive_member_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Archive Member (Nested)")
    has_archive_member: base_has_archive_member_model = Field(..., title="Assert Has Archive Member")


class has_archive_member_model_relaxed(base_has_archive_member_model_relaxed):
    r"""This tag allows to check if ``path`` is contained in a compressed file.

    The path is a regular expression that is matched against the full paths of the objects in
    the compressed file (remember that "matching" means it is checked if a prefix of
    the full path of an archive member is described by the regular expression).
    Valid archive formats include ``.zip``, ``.tar``, and ``.tar.gz``. Note that
    depending on the archive creation method:

    - full paths of the members may be prefixed with ``./``
    - directories may be treated as empty files

    ```xml
    <has_archive_member path="./path/to/my-file.txt"/>
    ```

    With ``n`` and ``delta`` (or ``min`` and ``max``) assertions on the number of
    archive members matching ``path`` can be expressed. The following could be used,
    e.g., to assert an archive containing n&plusmn;1 elements out of which at least
    4 need to have a ``txt`` extension.

    ```xml
    <has_archive_member path=".*" n="10" delta="1"/>
    <has_archive_member path=".*\.txt" min="4"/>
    ```

    In addition the tag can contain additional assertions as child elements about
    the first member in the archive matching the regular expression ``path``. For
    instance

    ```xml
    <has_archive_member path=".*/my-file.txt">
      <not_has_text text="EDK72998.1"/>
    </has_archive_member>
    ```

    If the ``all`` attribute is set to ``true`` then all archive members are subject
    to the assertions. Note that, archive members matching the ``path`` are sorted
    alphabetically.

    The ``negate`` attribute of the ``has_archive_member`` assertion only affects
    the asserts on the presence and number of matching archive members, but not any
    sub-assertions (which can offer the ``negate`` attribute on their own).  The
    check if the file is an archive at all, which is also done by the function, is
    not affected."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Archive Member (Relaxed)")
    that: Literal["has_archive_member"] = Field("has_archive_member", title="That")


has_size_value_description = """Deprecated alias for `size`"""

has_size_size_description = """Desired size of the output (in bytes), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_size_delta_description = (
    """Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``"""
)

has_size_min_description = """Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_size_max_description = """Maximum number (default: infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_size_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class base_has_size_model(AssertionModel):
    """base model for has_size describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_size_model")

    value: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Value",
        description=has_size_value_description,
    )

    size: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Size",
        description=has_size_size_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        title="Delta",
        description=has_size_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Min",
        description=has_size_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Max",
        description=has_size_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_size_negate_description,
    )


class base_has_size_model_relaxed(AssertionModel):
    """base model for has_size describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_size_model_relaxed")

    value: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Value",
        description=has_size_value_description,
    )

    size: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Size",
        description=has_size_size_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        title="Delta",
        description=has_size_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Min",
        description=has_size_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        title="Max",
        description=has_size_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_size_negate_description,
    )


class has_size_model(base_has_size_model):
    r"""Asserts the specified output has a size of the specified value

    Attributes size and value or synonyms though value is considered deprecated.
    The size optionally allows for absolute (``delta``) difference."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Size")
    that: Literal["has_size"] = Field("has_size", title="That")


class has_size_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Size (Nested)")
    has_size: base_has_size_model = Field(..., title="Assert Has Size")


class has_size_model_relaxed(base_has_size_model_relaxed):
    r"""Asserts the specified output has a size of the specified value

    Attributes size and value or synonyms though value is considered deprecated.
    The size optionally allows for absolute (``delta``) difference."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Size (Relaxed)")
    that: Literal["has_size"] = Field("has_size", title="That")


has_image_center_of_mass_center_of_mass_description = """The required center of mass of the image intensities (horizontal and vertical coordinate, separated by a comma)."""

has_image_center_of_mass_channel_description = """Restricts the assertion to a specific channel of the image (where ``0`` corresponds to the first image channel)."""

has_image_center_of_mass_slice_description = (
    """Restricts the assertion to a specific slice of the image (where ``0`` corresponds to the first image slice)."""
)

has_image_center_of_mass_frame_description = """Restricts the assertion to a specific frame of the image sequence (where ``0`` corresponds to the first image frame)."""

has_image_center_of_mass_eps_description = (
    """The maximum allowed Euclidean distance to the required center of mass (defaults to ``0.01``)."""
)


class base_has_image_center_of_mass_model(AssertionModel):
    """base model for has_image_center_of_mass describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_image_center_of_mass_model")

    center_of_mass: Annotated[str, BeforeValidator(check_center_of_mass)] = Field(
        ...,
        title="Center Of Mass",
        description=has_image_center_of_mass_center_of_mass_description,
    )

    channel: typing.Optional[StrictInt] = Field(
        None,
        title="Channel",
        description=has_image_center_of_mass_channel_description,
    )

    slice: typing.Optional[StrictInt] = Field(
        None,
        title="Slice",
        description=has_image_center_of_mass_slice_description,
    )

    frame: typing.Optional[StrictInt] = Field(
        None,
        title="Frame",
        description=has_image_center_of_mass_frame_description,
    )

    eps: Annotated[typing.Union[StrictInt, StrictFloat], BeforeValidator(check_non_negative_if_set)] = Field(
        0.01,
        title="Eps",
        description=has_image_center_of_mass_eps_description,
    )


class base_has_image_center_of_mass_model_relaxed(AssertionModel):
    """base model for has_image_center_of_mass describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_image_center_of_mass_model_relaxed")

    center_of_mass: Annotated[str, BeforeValidator(check_center_of_mass)] = Field(
        ...,
        title="Center Of Mass",
        description=has_image_center_of_mass_center_of_mass_description,
    )

    channel: typing.Optional[typing.Union[str, int]] = Field(
        None,
        title="Channel",
        description=has_image_center_of_mass_channel_description,
    )

    slice: typing.Optional[typing.Union[str, int]] = Field(
        None,
        title="Slice",
        description=has_image_center_of_mass_slice_description,
    )

    frame: typing.Optional[typing.Union[str, int]] = Field(
        None,
        title="Frame",
        description=has_image_center_of_mass_frame_description,
    )

    eps: Annotated[typing.Union[float, str], BeforeValidator(check_non_negative_if_set)] = Field(
        0.01,
        title="Eps",
        description=has_image_center_of_mass_eps_description,
    )


class has_image_center_of_mass_model(base_has_image_center_of_mass_model):
    r"""Asserts the specified output is an image and has the specified center of mass.

    Asserts the output is an image and has a specific center of mass,
    or has an Euclidean distance of ``eps`` or less to that point (e.g.,
    ``<has_image_center_of_mass center_of_mass="511.07, 223.34" />``)."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image Center Of Mass")
    that: Literal["has_image_center_of_mass"] = Field("has_image_center_of_mass", title="That")


class has_image_center_of_mass_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image Center Of Mass (Nested)")
    has_image_center_of_mass: base_has_image_center_of_mass_model = Field(..., title="Assert Has Image Center Of Mass")


class has_image_center_of_mass_model_relaxed(base_has_image_center_of_mass_model_relaxed):
    r"""Asserts the specified output is an image and has the specified center of mass.

    Asserts the output is an image and has a specific center of mass,
    or has an Euclidean distance of ``eps`` or less to that point (e.g.,
    ``<has_image_center_of_mass center_of_mass="511.07, 223.34" />``)."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image Center Of Mass (Relaxed)")
    that: Literal["has_image_center_of_mass"] = Field("has_image_center_of_mass", title="That")


has_image_channels_channels_description = """Expected number of channels of the image."""

has_image_channels_delta_description = """Maximum allowed difference of the number of channels (default is 0). The observed number of channels has to be in the range ``value +- delta``."""

has_image_channels_min_description = """Minimum allowed number of channels."""

has_image_channels_max_description = """Maximum allowed number of channels."""

has_image_channels_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class base_has_image_channels_model(AssertionModel):
    """base model for has_image_channels describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_image_channels_model")

    channels: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Channels",
        description=has_image_channels_channels_description,
    )

    delta: Annotated[StrictInt, BeforeValidator(check_non_negative_if_set)] = Field(
        0,
        title="Delta",
        description=has_image_channels_delta_description,
    )

    min: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Min",
        description=has_image_channels_min_description,
    )

    max: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Max",
        description=has_image_channels_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_image_channels_negate_description,
    )


class base_has_image_channels_model_relaxed(AssertionModel):
    """base model for has_image_channels describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_image_channels_model_relaxed")

    channels: Annotated[typing.Optional[typing.Union[str, int]], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Channels",
        description=has_image_channels_channels_description,
    )

    delta: Annotated[typing.Union[int, str], BeforeValidator(check_non_negative_if_set)] = Field(
        0,
        title="Delta",
        description=has_image_channels_delta_description,
    )

    min: Annotated[typing.Optional[typing.Union[str, int]], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Min",
        description=has_image_channels_min_description,
    )

    max: Annotated[typing.Optional[typing.Union[str, int]], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Max",
        description=has_image_channels_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_image_channels_negate_description,
    )


class has_image_channels_model(base_has_image_channels_model):
    r"""Asserts the output is an image and has a specific number of channels.

    The number of channels is plus/minus ``delta`` (e.g., ``<has_image_channels channels="3" />``).

    Alternatively the range of the expected number of channels can be specified by ``min`` and/or ``max``."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image Channels")
    that: Literal["has_image_channels"] = Field("has_image_channels", title="That")


class has_image_channels_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image Channels (Nested)")
    has_image_channels: base_has_image_channels_model = Field(..., title="Assert Has Image Channels")


class has_image_channels_model_relaxed(base_has_image_channels_model_relaxed):
    r"""Asserts the output is an image and has a specific number of channels.

    The number of channels is plus/minus ``delta`` (e.g., ``<has_image_channels channels="3" />``).

    Alternatively the range of the expected number of channels can be specified by ``min`` and/or ``max``."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image Channels (Relaxed)")
    that: Literal["has_image_channels"] = Field("has_image_channels", title="That")


has_image_depth_depth_description = """Expected depth of the image (number of slices)."""

has_image_depth_delta_description = """Maximum allowed difference of the image depth (number of slices, default is 0). The observed depth has to be in the range ``value +- delta``."""

has_image_depth_min_description = """Minimum allowed depth of the image (number of slices)."""

has_image_depth_max_description = """Maximum allowed depth of the image (number of slices)."""

has_image_depth_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class base_has_image_depth_model(AssertionModel):
    """base model for has_image_depth describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_image_depth_model")

    depth: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Depth",
        description=has_image_depth_depth_description,
    )

    delta: Annotated[StrictInt, BeforeValidator(check_non_negative_if_set)] = Field(
        0,
        title="Delta",
        description=has_image_depth_delta_description,
    )

    min: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Min",
        description=has_image_depth_min_description,
    )

    max: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Max",
        description=has_image_depth_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_image_depth_negate_description,
    )


class base_has_image_depth_model_relaxed(AssertionModel):
    """base model for has_image_depth describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_image_depth_model_relaxed")

    depth: Annotated[typing.Optional[typing.Union[str, int]], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Depth",
        description=has_image_depth_depth_description,
    )

    delta: Annotated[typing.Union[int, str], BeforeValidator(check_non_negative_if_set)] = Field(
        0,
        title="Delta",
        description=has_image_depth_delta_description,
    )

    min: Annotated[typing.Optional[typing.Union[str, int]], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Min",
        description=has_image_depth_min_description,
    )

    max: Annotated[typing.Optional[typing.Union[str, int]], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Max",
        description=has_image_depth_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_image_depth_negate_description,
    )


class has_image_depth_model(base_has_image_depth_model):
    r"""Asserts the output is an image and has a specific depth (number of slices).

    The depth is plus/minus ``delta`` (e.g., ``<has_image_depth depth="512" delta="2" />``).
    Alternatively the range of the expected depth can be specified by ``min`` and/or ``max``."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image Depth")
    that: Literal["has_image_depth"] = Field("has_image_depth", title="That")


class has_image_depth_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image Depth (Nested)")
    has_image_depth: base_has_image_depth_model = Field(..., title="Assert Has Image Depth")


class has_image_depth_model_relaxed(base_has_image_depth_model_relaxed):
    r"""Asserts the output is an image and has a specific depth (number of slices).

    The depth is plus/minus ``delta`` (e.g., ``<has_image_depth depth="512" delta="2" />``).
    Alternatively the range of the expected depth can be specified by ``min`` and/or ``max``."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image Depth (Relaxed)")
    that: Literal["has_image_depth"] = Field("has_image_depth", title="That")


has_image_frames_frames_description = """Expected number of frames in the image sequence (number of time steps)."""

has_image_frames_delta_description = """Maximum allowed difference of the number of frames in the image sequence (number of time steps, default is 0). The observed number of frames has to be in the range ``value +- delta``."""

has_image_frames_min_description = """Minimum allowed number of frames in the image sequence (number of time steps)."""

has_image_frames_max_description = """Maximum allowed number of frames in the image sequence (number of time steps)."""

has_image_frames_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class base_has_image_frames_model(AssertionModel):
    """base model for has_image_frames describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_image_frames_model")

    frames: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Frames",
        description=has_image_frames_frames_description,
    )

    delta: Annotated[StrictInt, BeforeValidator(check_non_negative_if_set)] = Field(
        0,
        title="Delta",
        description=has_image_frames_delta_description,
    )

    min: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Min",
        description=has_image_frames_min_description,
    )

    max: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Max",
        description=has_image_frames_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_image_frames_negate_description,
    )


class base_has_image_frames_model_relaxed(AssertionModel):
    """base model for has_image_frames describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_image_frames_model_relaxed")

    frames: Annotated[typing.Optional[typing.Union[str, int]], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Frames",
        description=has_image_frames_frames_description,
    )

    delta: Annotated[typing.Union[int, str], BeforeValidator(check_non_negative_if_set)] = Field(
        0,
        title="Delta",
        description=has_image_frames_delta_description,
    )

    min: Annotated[typing.Optional[typing.Union[str, int]], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Min",
        description=has_image_frames_min_description,
    )

    max: Annotated[typing.Optional[typing.Union[str, int]], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Max",
        description=has_image_frames_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_image_frames_negate_description,
    )


class has_image_frames_model(base_has_image_frames_model):
    r"""Asserts the output is an image and has a specific number of frames (number of time steps).

    The number of frames is plus/minus ``delta`` (e.g., ``<has_image_frames depth="512" delta="2" />``).
    Alternatively the range of the expected number of frames can be specified by ``min`` and/or ``max``."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image Frames")
    that: Literal["has_image_frames"] = Field("has_image_frames", title="That")


class has_image_frames_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image Frames (Nested)")
    has_image_frames: base_has_image_frames_model = Field(..., title="Assert Has Image Frames")


class has_image_frames_model_relaxed(base_has_image_frames_model_relaxed):
    r"""Asserts the output is an image and has a specific number of frames (number of time steps).

    The number of frames is plus/minus ``delta`` (e.g., ``<has_image_frames depth="512" delta="2" />``).
    Alternatively the range of the expected number of frames can be specified by ``min`` and/or ``max``."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image Frames (Relaxed)")
    that: Literal["has_image_frames"] = Field("has_image_frames", title="That")


has_image_height_height_description = """Expected height of the image (in pixels)."""

has_image_height_delta_description = """Maximum allowed difference of the image height (in pixels, default is 0). The observed height has to be in the range ``value +- delta``."""

has_image_height_min_description = """Minimum allowed height of the image (in pixels)."""

has_image_height_max_description = """Maximum allowed height of the image (in pixels)."""

has_image_height_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class base_has_image_height_model(AssertionModel):
    """base model for has_image_height describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_image_height_model")

    height: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Height",
        description=has_image_height_height_description,
    )

    delta: Annotated[StrictInt, BeforeValidator(check_non_negative_if_set)] = Field(
        0,
        title="Delta",
        description=has_image_height_delta_description,
    )

    min: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Min",
        description=has_image_height_min_description,
    )

    max: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Max",
        description=has_image_height_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_image_height_negate_description,
    )


class base_has_image_height_model_relaxed(AssertionModel):
    """base model for has_image_height describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_image_height_model_relaxed")

    height: Annotated[typing.Optional[typing.Union[str, int]], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Height",
        description=has_image_height_height_description,
    )

    delta: Annotated[typing.Union[int, str], BeforeValidator(check_non_negative_if_set)] = Field(
        0,
        title="Delta",
        description=has_image_height_delta_description,
    )

    min: Annotated[typing.Optional[typing.Union[str, int]], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Min",
        description=has_image_height_min_description,
    )

    max: Annotated[typing.Optional[typing.Union[str, int]], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Max",
        description=has_image_height_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_image_height_negate_description,
    )


class has_image_height_model(base_has_image_height_model):
    r"""Asserts the output is an image and has a specific height (in pixels).

    The height is plus/minus ``delta`` (e.g., ``<has_image_height height="512" delta="2" />``).
    Alternatively the range of the expected height can be specified by ``min`` and/or ``max``."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image Height")
    that: Literal["has_image_height"] = Field("has_image_height", title="That")


class has_image_height_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image Height (Nested)")
    has_image_height: base_has_image_height_model = Field(..., title="Assert Has Image Height")


class has_image_height_model_relaxed(base_has_image_height_model_relaxed):
    r"""Asserts the output is an image and has a specific height (in pixels).

    The height is plus/minus ``delta`` (e.g., ``<has_image_height height="512" delta="2" />``).
    Alternatively the range of the expected height can be specified by ``min`` and/or ``max``."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image Height (Relaxed)")
    that: Literal["has_image_height"] = Field("has_image_height", title="That")


has_image_mean_intensity_channel_description = """Restricts the assertion to a specific channel of the image (where ``0`` corresponds to the first image channel)."""

has_image_mean_intensity_slice_description = (
    """Restricts the assertion to a specific slice of the image (where ``0`` corresponds to the first image slice)."""
)

has_image_mean_intensity_frame_description = """Restricts the assertion to a specific frame of the image sequence (where ``0`` corresponds to the first image frame)."""

has_image_mean_intensity_mean_intensity_description = """The required mean value of the image intensities."""

has_image_mean_intensity_eps_description = """The absolute tolerance to be used for ``value`` (defaults to ``0.01``). The observed mean value of the image intensities has to be in the range ``value +- eps``."""

has_image_mean_intensity_min_description = """A lower bound of the required mean value of the image intensities."""

has_image_mean_intensity_max_description = """An upper bound of the required mean value of the image intensities."""


class base_has_image_mean_intensity_model(AssertionModel):
    """base model for has_image_mean_intensity describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_image_mean_intensity_model")

    channel: typing.Optional[StrictInt] = Field(
        None,
        title="Channel",
        description=has_image_mean_intensity_channel_description,
    )

    slice: typing.Optional[StrictInt] = Field(
        None,
        title="Slice",
        description=has_image_mean_intensity_slice_description,
    )

    frame: typing.Optional[StrictInt] = Field(
        None,
        title="Frame",
        description=has_image_mean_intensity_frame_description,
    )

    mean_intensity: typing.Optional[typing.Union[StrictInt, StrictFloat]] = Field(
        None,
        title="Mean Intensity",
        description=has_image_mean_intensity_mean_intensity_description,
    )

    eps: Annotated[typing.Union[StrictInt, StrictFloat], BeforeValidator(check_non_negative_if_set)] = Field(
        0.01,
        title="Eps",
        description=has_image_mean_intensity_eps_description,
    )

    min: typing.Optional[typing.Union[StrictInt, StrictFloat]] = Field(
        None,
        title="Min",
        description=has_image_mean_intensity_min_description,
    )

    max: typing.Optional[typing.Union[StrictInt, StrictFloat]] = Field(
        None,
        title="Max",
        description=has_image_mean_intensity_max_description,
    )


class base_has_image_mean_intensity_model_relaxed(AssertionModel):
    """base model for has_image_mean_intensity describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_image_mean_intensity_model_relaxed")

    channel: typing.Optional[typing.Union[str, int]] = Field(
        None,
        title="Channel",
        description=has_image_mean_intensity_channel_description,
    )

    slice: typing.Optional[typing.Union[str, int]] = Field(
        None,
        title="Slice",
        description=has_image_mean_intensity_slice_description,
    )

    frame: typing.Optional[typing.Union[str, int]] = Field(
        None,
        title="Frame",
        description=has_image_mean_intensity_frame_description,
    )

    mean_intensity: typing.Optional[typing.Union[float, str]] = Field(
        None,
        title="Mean Intensity",
        description=has_image_mean_intensity_mean_intensity_description,
    )

    eps: Annotated[typing.Union[float, str], BeforeValidator(check_non_negative_if_set)] = Field(
        0.01,
        title="Eps",
        description=has_image_mean_intensity_eps_description,
    )

    min: typing.Optional[typing.Union[float, str]] = Field(
        None,
        title="Min",
        description=has_image_mean_intensity_min_description,
    )

    max: typing.Optional[typing.Union[float, str]] = Field(
        None,
        title="Max",
        description=has_image_mean_intensity_max_description,
    )


class has_image_mean_intensity_model(base_has_image_mean_intensity_model):
    r"""Asserts the output is an image and has a specific mean intensity value.

    The mean intensity value is plus/minus ``eps`` (e.g., ``<has_image_mean_intensity mean_intensity="0.83" />``).
    Alternatively the range of the expected mean intensity value can be specified by ``min`` and/or ``max``."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image Mean Intensity")
    that: Literal["has_image_mean_intensity"] = Field("has_image_mean_intensity", title="That")


class has_image_mean_intensity_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image Mean Intensity (Nested)")
    has_image_mean_intensity: base_has_image_mean_intensity_model = Field(..., title="Assert Has Image Mean Intensity")


class has_image_mean_intensity_model_relaxed(base_has_image_mean_intensity_model_relaxed):
    r"""Asserts the output is an image and has a specific mean intensity value.

    The mean intensity value is plus/minus ``eps`` (e.g., ``<has_image_mean_intensity mean_intensity="0.83" />``).
    Alternatively the range of the expected mean intensity value can be specified by ``min`` and/or ``max``."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image Mean Intensity (Relaxed)")
    that: Literal["has_image_mean_intensity"] = Field("has_image_mean_intensity", title="That")


has_image_mean_object_size_channel_description = """Restricts the assertion to a specific channel of the image (where ``0`` corresponds to the first image channel)."""

has_image_mean_object_size_slice_description = (
    """Restricts the assertion to a specific slice of the image (where ``0`` corresponds to the first image slice)."""
)

has_image_mean_object_size_frame_description = """Restricts the assertion to a specific frame of the image sequence (where ``0`` corresponds to the first image frame)."""

has_image_mean_object_size_labels_description = """List of labels, separated by a comma. Labels *not* on this list will be excluded from consideration. Cannot be used in combination with ``exclude_labels``."""

has_image_mean_object_size_exclude_labels_description = """List of labels to be excluded from consideration, separated by a comma. The primary usage of this attribute is to exclude the background of a label image. Cannot be used in combination with ``labels``."""

has_image_mean_object_size_mean_object_size_description = """The required mean size of the uniquely labeled objects."""

has_image_mean_object_size_eps_description = """The absolute tolerance to be used for ``value`` (defaults to ``0.01``). The observed mean size of the uniquely labeled objects has to be in the range ``value +- eps``."""

has_image_mean_object_size_min_description = (
    """A lower bound of the required mean size of the uniquely labeled objects."""
)

has_image_mean_object_size_max_description = (
    """An upper bound of the required mean size of the uniquely labeled objects."""
)


class base_has_image_mean_object_size_model(AssertionModel):
    """base model for has_image_mean_object_size describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_image_mean_object_size_model")

    channel: typing.Optional[StrictInt] = Field(
        None,
        title="Channel",
        description=has_image_mean_object_size_channel_description,
    )

    slice: typing.Optional[StrictInt] = Field(
        None,
        title="Slice",
        description=has_image_mean_object_size_slice_description,
    )

    frame: typing.Optional[StrictInt] = Field(
        None,
        title="Frame",
        description=has_image_mean_object_size_frame_description,
    )

    labels: typing.Optional[typing.List[typing.Union[StrictInt, StrictFloat]]] = Field(
        None,
        title="Labels",
        description=has_image_mean_object_size_labels_description,
    )

    exclude_labels: typing.Optional[typing.List[typing.Union[StrictInt, StrictFloat]]] = Field(
        None,
        title="Exclude Labels",
        description=has_image_mean_object_size_exclude_labels_description,
    )

    mean_object_size: Annotated[
        typing.Optional[typing.Union[StrictInt, StrictFloat]], BeforeValidator(check_non_negative_if_set)
    ] = Field(
        None,
        title="Mean Object Size",
        description=has_image_mean_object_size_mean_object_size_description,
    )

    eps: Annotated[typing.Union[StrictInt, StrictFloat], BeforeValidator(check_non_negative_if_set)] = Field(
        0.01,
        title="Eps",
        description=has_image_mean_object_size_eps_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[StrictInt, StrictFloat]], BeforeValidator(check_non_negative_if_set)
    ] = Field(
        None,
        title="Min",
        description=has_image_mean_object_size_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[StrictInt, StrictFloat]], BeforeValidator(check_non_negative_if_set)
    ] = Field(
        None,
        title="Max",
        description=has_image_mean_object_size_max_description,
    )


class base_has_image_mean_object_size_model_relaxed(AssertionModel):
    """base model for has_image_mean_object_size describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_image_mean_object_size_model_relaxed")

    channel: typing.Optional[typing.Union[str, int]] = Field(
        None,
        title="Channel",
        description=has_image_mean_object_size_channel_description,
    )

    slice: typing.Optional[typing.Union[str, int]] = Field(
        None,
        title="Slice",
        description=has_image_mean_object_size_slice_description,
    )

    frame: typing.Optional[typing.Union[str, int]] = Field(
        None,
        title="Frame",
        description=has_image_mean_object_size_frame_description,
    )

    labels: typing.Optional[typing.Union[str, typing.List[typing.Union[float, int]]]] = Field(
        None,
        title="Labels",
        description=has_image_mean_object_size_labels_description,
    )

    exclude_labels: typing.Optional[typing.Union[str, typing.List[typing.Union[float, int]]]] = Field(
        None,
        title="Exclude Labels",
        description=has_image_mean_object_size_exclude_labels_description,
    )

    mean_object_size: Annotated[
        typing.Optional[typing.Union[float, str]], BeforeValidator(check_non_negative_if_set)
    ] = Field(
        None,
        title="Mean Object Size",
        description=has_image_mean_object_size_mean_object_size_description,
    )

    eps: Annotated[typing.Union[float, str], BeforeValidator(check_non_negative_if_set)] = Field(
        0.01,
        title="Eps",
        description=has_image_mean_object_size_eps_description,
    )

    min: Annotated[typing.Optional[typing.Union[float, str]], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Min",
        description=has_image_mean_object_size_min_description,
    )

    max: Annotated[typing.Optional[typing.Union[float, str]], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Max",
        description=has_image_mean_object_size_max_description,
    )


class has_image_mean_object_size_model(base_has_image_mean_object_size_model):
    r"""Asserts the output is an image with labeled objects which have the specified mean size (number of pixels),

    The mean size is plus/minus ``eps`` (e.g., ``<has_image_mean_object_size mean_object_size="111.87" exclude_labels="0" />``).

    The labels must be unique."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image Mean Object Size")
    that: Literal["has_image_mean_object_size"] = Field("has_image_mean_object_size", title="That")


class has_image_mean_object_size_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image Mean Object Size (Nested)")
    has_image_mean_object_size: base_has_image_mean_object_size_model = Field(
        ..., title="Assert Has Image Mean Object Size"
    )


class has_image_mean_object_size_model_relaxed(base_has_image_mean_object_size_model_relaxed):
    r"""Asserts the output is an image with labeled objects which have the specified mean size (number of pixels),

    The mean size is plus/minus ``eps`` (e.g., ``<has_image_mean_object_size mean_object_size="111.87" exclude_labels="0" />``).

    The labels must be unique."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image Mean Object Size (Relaxed)")
    that: Literal["has_image_mean_object_size"] = Field("has_image_mean_object_size", title="That")


has_image_n_labels_channel_description = """Restricts the assertion to a specific channel of the image (where ``0`` corresponds to the first image channel)."""

has_image_n_labels_slice_description = (
    """Restricts the assertion to a specific slice of the image (where ``0`` corresponds to the first image slice)."""
)

has_image_n_labels_frame_description = """Restricts the assertion to a specific frame of the image sequence (where ``0`` corresponds to the first image frame)."""

has_image_n_labels_labels_description = """List of labels, separated by a comma. Labels *not* on this list will be excluded from consideration. Cannot be used in combination with ``exclude_labels``."""

has_image_n_labels_exclude_labels_description = """List of labels to be excluded from consideration, separated by a comma. The primary usage of this attribute is to exclude the background of a label image. Cannot be used in combination with ``labels``."""

has_image_n_labels_n_description = """Expected number of labels."""

has_image_n_labels_delta_description = """Maximum allowed difference of the number of labels (default is 0). The observed number of labels has to be in the range ``value +- delta``."""

has_image_n_labels_min_description = """Minimum allowed number of labels."""

has_image_n_labels_max_description = """Maximum allowed number of labels."""

has_image_n_labels_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class base_has_image_n_labels_model(AssertionModel):
    """base model for has_image_n_labels describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_image_n_labels_model")

    channel: typing.Optional[StrictInt] = Field(
        None,
        title="Channel",
        description=has_image_n_labels_channel_description,
    )

    slice: typing.Optional[StrictInt] = Field(
        None,
        title="Slice",
        description=has_image_n_labels_slice_description,
    )

    frame: typing.Optional[StrictInt] = Field(
        None,
        title="Frame",
        description=has_image_n_labels_frame_description,
    )

    labels: typing.Optional[typing.List[typing.Union[StrictInt, StrictFloat]]] = Field(
        None,
        title="Labels",
        description=has_image_n_labels_labels_description,
    )

    exclude_labels: typing.Optional[typing.List[typing.Union[StrictInt, StrictFloat]]] = Field(
        None,
        title="Exclude Labels",
        description=has_image_n_labels_exclude_labels_description,
    )

    n: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="N",
        description=has_image_n_labels_n_description,
    )

    delta: Annotated[StrictInt, BeforeValidator(check_non_negative_if_set)] = Field(
        0,
        title="Delta",
        description=has_image_n_labels_delta_description,
    )

    min: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Min",
        description=has_image_n_labels_min_description,
    )

    max: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Max",
        description=has_image_n_labels_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_image_n_labels_negate_description,
    )


class base_has_image_n_labels_model_relaxed(AssertionModel):
    """base model for has_image_n_labels describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_image_n_labels_model_relaxed")

    channel: typing.Optional[typing.Union[str, int]] = Field(
        None,
        title="Channel",
        description=has_image_n_labels_channel_description,
    )

    slice: typing.Optional[typing.Union[str, int]] = Field(
        None,
        title="Slice",
        description=has_image_n_labels_slice_description,
    )

    frame: typing.Optional[typing.Union[str, int]] = Field(
        None,
        title="Frame",
        description=has_image_n_labels_frame_description,
    )

    labels: typing.Optional[typing.Union[str, typing.List[typing.Union[float, int]]]] = Field(
        None,
        title="Labels",
        description=has_image_n_labels_labels_description,
    )

    exclude_labels: typing.Optional[typing.Union[str, typing.List[typing.Union[float, int]]]] = Field(
        None,
        title="Exclude Labels",
        description=has_image_n_labels_exclude_labels_description,
    )

    n: Annotated[typing.Optional[typing.Union[str, int]], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="N",
        description=has_image_n_labels_n_description,
    )

    delta: Annotated[typing.Union[int, str], BeforeValidator(check_non_negative_if_set)] = Field(
        0,
        title="Delta",
        description=has_image_n_labels_delta_description,
    )

    min: Annotated[typing.Optional[typing.Union[str, int]], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Min",
        description=has_image_n_labels_min_description,
    )

    max: Annotated[typing.Optional[typing.Union[str, int]], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Max",
        description=has_image_n_labels_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_image_n_labels_negate_description,
    )


class has_image_n_labels_model(base_has_image_n_labels_model):
    r"""Asserts the output is an image and has the specified labels.

    Labels can be a number of labels or unique values (e.g.,
    ``<has_image_n_labels n="187" exclude_labels="0" />``).

    The primary usage of this assertion is to verify the number of objects in images with uniquely labeled objects."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image N Labels")
    that: Literal["has_image_n_labels"] = Field("has_image_n_labels", title="That")


class has_image_n_labels_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image N Labels (Nested)")
    has_image_n_labels: base_has_image_n_labels_model = Field(..., title="Assert Has Image N Labels")


class has_image_n_labels_model_relaxed(base_has_image_n_labels_model_relaxed):
    r"""Asserts the output is an image and has the specified labels.

    Labels can be a number of labels or unique values (e.g.,
    ``<has_image_n_labels n="187" exclude_labels="0" />``).

    The primary usage of this assertion is to verify the number of objects in images with uniquely labeled objects."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image N Labels (Relaxed)")
    that: Literal["has_image_n_labels"] = Field("has_image_n_labels", title="That")


has_image_width_width_description = """Expected width of the image (in pixels)."""

has_image_width_delta_description = """Maximum allowed difference of the image width (in pixels, default is 0). The observed width has to be in the range ``value +- delta``."""

has_image_width_min_description = """Minimum allowed width of the image (in pixels)."""

has_image_width_max_description = """Maximum allowed width of the image (in pixels)."""

has_image_width_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class base_has_image_width_model(AssertionModel):
    """base model for has_image_width describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_image_width_model")

    width: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Width",
        description=has_image_width_width_description,
    )

    delta: Annotated[StrictInt, BeforeValidator(check_non_negative_if_set)] = Field(
        0,
        title="Delta",
        description=has_image_width_delta_description,
    )

    min: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Min",
        description=has_image_width_min_description,
    )

    max: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Max",
        description=has_image_width_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_image_width_negate_description,
    )


class base_has_image_width_model_relaxed(AssertionModel):
    """base model for has_image_width describing attributes."""

    model_config = ConfigDict(extra="forbid", title="base_has_image_width_model_relaxed")

    width: Annotated[typing.Optional[typing.Union[str, int]], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Width",
        description=has_image_width_width_description,
    )

    delta: Annotated[typing.Union[int, str], BeforeValidator(check_non_negative_if_set)] = Field(
        0,
        title="Delta",
        description=has_image_width_delta_description,
    )

    min: Annotated[typing.Optional[typing.Union[str, int]], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Min",
        description=has_image_width_min_description,
    )

    max: Annotated[typing.Optional[typing.Union[str, int]], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        title="Max",
        description=has_image_width_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        title="Negate",
        description=has_image_width_negate_description,
    )


class has_image_width_model(base_has_image_width_model):
    r"""Asserts the output is an image and has a specific width (in pixels).

    The width is plus/minus ``delta`` (e.g., ``<has_image_width width="512" delta="2" />``).
    Alternatively the range of the expected width can be specified by ``min`` and/or ``max``."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image Width")
    that: Literal["has_image_width"] = Field("has_image_width", title="That")


class has_image_width_model_nested(AssertionModel):
    r"""Nested version of this assertion model."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image Width (Nested)")
    has_image_width: base_has_image_width_model = Field(..., title="Assert Has Image Width")


class has_image_width_model_relaxed(base_has_image_width_model_relaxed):
    r"""Asserts the output is an image and has a specific width (in pixels).

    The width is plus/minus ``delta`` (e.g., ``<has_image_width width="512" delta="2" />``).
    Alternatively the range of the expected width can be specified by ``min`` and/or ``max``."""

    model_config = ConfigDict(extra="forbid", title="Assert Has Image Width (Relaxed)")
    that: Literal["has_image_width"] = Field("has_image_width", title="That")


any_assertion_model_flat = Annotated[
    typing.Union[
        has_line_model,
        has_line_matching_model,
        has_n_lines_model,
        has_text_model,
        has_text_matching_model,
        not_has_text_model,
        has_n_columns_model,
        attribute_is_model,
        attribute_matches_model,
        element_text_model,
        element_text_is_model,
        element_text_matches_model,
        has_element_with_path_model,
        has_n_elements_with_path_model,
        is_valid_xml_model,
        xml_element_model,
        has_json_property_with_text_model,
        has_json_property_with_value_model,
        has_h5_attribute_model,
        has_h5_keys_model,
        has_archive_member_model,
        has_size_model,
        has_image_center_of_mass_model,
        has_image_channels_model,
        has_image_depth_model,
        has_image_frames_model,
        has_image_height_model,
        has_image_mean_intensity_model,
        has_image_mean_object_size_model,
        has_image_n_labels_model,
        has_image_width_model,
    ],
    Field(discriminator="that"),
]

any_assertion_model_nested = typing.Union[
    has_line_model_nested,
    has_line_matching_model_nested,
    has_n_lines_model_nested,
    has_text_model_nested,
    has_text_matching_model_nested,
    not_has_text_model_nested,
    has_n_columns_model_nested,
    attribute_is_model_nested,
    attribute_matches_model_nested,
    element_text_model_nested,
    element_text_is_model_nested,
    element_text_matches_model_nested,
    has_element_with_path_model_nested,
    has_n_elements_with_path_model_nested,
    is_valid_xml_model_nested,
    xml_element_model_nested,
    has_json_property_with_text_model_nested,
    has_json_property_with_value_model_nested,
    has_h5_attribute_model_nested,
    has_h5_keys_model_nested,
    has_archive_member_model_nested,
    has_size_model_nested,
    has_image_center_of_mass_model_nested,
    has_image_channels_model_nested,
    has_image_depth_model_nested,
    has_image_frames_model_nested,
    has_image_height_model_nested,
    has_image_mean_intensity_model_nested,
    has_image_mean_object_size_model_nested,
    has_image_n_labels_model_nested,
    has_image_width_model_nested,
]

any_assertion_model_flat_relaxed = Annotated[
    typing.Union[
        has_line_model_relaxed,
        has_line_matching_model_relaxed,
        has_n_lines_model_relaxed,
        has_text_model_relaxed,
        has_text_matching_model_relaxed,
        not_has_text_model_relaxed,
        has_n_columns_model_relaxed,
        attribute_is_model_relaxed,
        attribute_matches_model_relaxed,
        element_text_model_relaxed,
        element_text_is_model_relaxed,
        element_text_matches_model_relaxed,
        has_element_with_path_model_relaxed,
        has_n_elements_with_path_model_relaxed,
        is_valid_xml_model_relaxed,
        xml_element_model_relaxed,
        has_json_property_with_text_model_relaxed,
        has_json_property_with_value_model_relaxed,
        has_h5_attribute_model_relaxed,
        has_h5_keys_model_relaxed,
        has_archive_member_model_relaxed,
        has_size_model_relaxed,
        has_image_center_of_mass_model_relaxed,
        has_image_channels_model_relaxed,
        has_image_depth_model_relaxed,
        has_image_frames_model_relaxed,
        has_image_height_model_relaxed,
        has_image_mean_intensity_model_relaxed,
        has_image_mean_object_size_model_relaxed,
        has_image_n_labels_model_relaxed,
        has_image_width_model_relaxed,
    ],
    Field(discriminator="that"),
]


class assertion_list(RootModel[typing.List[typing.Union[any_assertion_model_flat, any_assertion_model_nested]]]):
    model_config = ConfigDict(title="assertion_list")


# used to model what the XML conversion should look like - not meant to be consumed outside of
# of Galaxy internals / linting.
class relaxed_assertion_list(RootModel[typing.List[any_assertion_model_flat_relaxed]]):
    model_config = ConfigDict(title="relaxed_assertion_list")


class assertion_dict(AssertionModel):
    model_config = ConfigDict(extra="forbid", title="assertion_dict")

    has_line: typing.Optional[base_has_line_model] = Field(None, title="Assert Has Line")

    has_line_matching: typing.Optional[base_has_line_matching_model] = Field(None, title="Assert Has Line Matching")

    has_n_lines: typing.Optional[base_has_n_lines_model] = Field(None, title="Assert Has N Lines")

    has_text: typing.Optional[base_has_text_model] = Field(None, title="Assert Has Text")

    has_text_matching: typing.Optional[base_has_text_matching_model] = Field(None, title="Assert Has Text Matching")

    not_has_text: typing.Optional[base_not_has_text_model] = Field(None, title="Assert Not Has Text")

    has_n_columns: typing.Optional[base_has_n_columns_model] = Field(None, title="Assert Has N Columns")

    attribute_is: typing.Optional[base_attribute_is_model] = Field(None, title="Assert Attribute Is")

    attribute_matches: typing.Optional[base_attribute_matches_model] = Field(None, title="Assert Attribute Matches")

    element_text: typing.Optional[base_element_text_model] = Field(None, title="Assert Element Text")

    element_text_is: typing.Optional[base_element_text_is_model] = Field(None, title="Assert Element Text Is")

    element_text_matches: typing.Optional[base_element_text_matches_model] = Field(
        None, title="Assert Element Text Matches"
    )

    has_element_with_path: typing.Optional[base_has_element_with_path_model] = Field(
        None, title="Assert Has Element With Path"
    )

    has_n_elements_with_path: typing.Optional[base_has_n_elements_with_path_model] = Field(
        None, title="Assert Has N Elements With Path"
    )

    is_valid_xml: typing.Optional[base_is_valid_xml_model] = Field(None, title="Assert Is Valid Xml")

    xml_element: typing.Optional[base_xml_element_model] = Field(None, title="Assert Xml Element")

    has_json_property_with_text: typing.Optional[base_has_json_property_with_text_model] = Field(
        None, title="Assert Has Json Property With Text"
    )

    has_json_property_with_value: typing.Optional[base_has_json_property_with_value_model] = Field(
        None, title="Assert Has Json Property With Value"
    )

    has_h5_attribute: typing.Optional[base_has_h5_attribute_model] = Field(None, title="Assert Has H5 Attribute")

    has_h5_keys: typing.Optional[base_has_h5_keys_model] = Field(None, title="Assert Has H5 Keys")

    has_archive_member: typing.Optional[base_has_archive_member_model] = Field(None, title="Assert Has Archive Member")

    has_size: typing.Optional[base_has_size_model] = Field(None, title="Assert Has Size")

    has_image_center_of_mass: typing.Optional[base_has_image_center_of_mass_model] = Field(
        None, title="Assert Has Image Center Of Mass"
    )

    has_image_channels: typing.Optional[base_has_image_channels_model] = Field(None, title="Assert Has Image Channels")

    has_image_depth: typing.Optional[base_has_image_depth_model] = Field(None, title="Assert Has Image Depth")

    has_image_frames: typing.Optional[base_has_image_frames_model] = Field(None, title="Assert Has Image Frames")

    has_image_height: typing.Optional[base_has_image_height_model] = Field(None, title="Assert Has Image Height")

    has_image_mean_intensity: typing.Optional[base_has_image_mean_intensity_model] = Field(
        None, title="Assert Has Image Mean Intensity"
    )

    has_image_mean_object_size: typing.Optional[base_has_image_mean_object_size_model] = Field(
        None, title="Assert Has Image Mean Object Size"
    )

    has_image_n_labels: typing.Optional[base_has_image_n_labels_model] = Field(None, title="Assert Has Image N Labels")

    has_image_width: typing.Optional[base_has_image_width_model] = Field(None, title="Assert Has Image Width")


assertions = typing.Union[assertion_list, assertion_dict]
