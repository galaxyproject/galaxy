"""This module is auto-generated, please do not modify."""

import re
import typing

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
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
        re.compile(typing.cast(str, v))
    except re.error:
        raise AssertionError(f"Invalid regular expression {v}")
    return v


def check_non_negative_if_set(v: typing.Any):
    if v is not None:
        try:
            assert v >= 0
        except TypeError:
            raise AssertionError(f"Invalid type found {v}")
    return v


def check_non_negative_if_int(v: typing.Any):
    if v is not None and isinstance(v, int):
        assert typing.cast(int, v) >= 0
    return v


has_line_line_description = """The full line of text to search for in the output."""

has_line_n_description = """Desired number, can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_line_delta_description = (
    """Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``"""
)

has_line_min_description = """Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_line_max_description = """Maximum number (default: infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_line_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class has_line_model(AssertionModel):
    r"""Asserts the specified output contains the line specified by the
    argument line. The exact number of occurrences can be optionally
    specified by the argument n"""

    that: Literal["has_line"] = "has_line"

    line: str = Field(
        ...,
        description=has_line_line_description,
    )

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_line_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        description=has_line_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_line_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_line_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        description=has_line_negate_description,
    )


has_line_matching_expression_description = """The regular expressions to attempt match in the output."""

has_line_matching_n_description = """Desired number, can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_line_matching_delta_description = (
    """Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``"""
)

has_line_matching_min_description = """Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_line_matching_max_description = """Maximum number (default: infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_line_matching_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class has_line_matching_model(AssertionModel):
    r"""Asserts the specified output contains a line matching the
    regular expression specified by the argument expression. If n is given
    the assertion checks for exactly n occurences."""

    that: Literal["has_line_matching"] = "has_line_matching"

    expression: str = Field(
        ...,
        description=has_line_matching_expression_description,
    )

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_line_matching_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        description=has_line_matching_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_line_matching_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_line_matching_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        description=has_line_matching_negate_description,
    )


has_n_lines_n_description = """Desired number, can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_n_lines_delta_description = (
    """Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``"""
)

has_n_lines_min_description = """Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_n_lines_max_description = """Maximum number (default: infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_n_lines_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class has_n_lines_model(AssertionModel):
    r"""Asserts the specified output contains ``n`` lines allowing
    for a difference in the number of lines (delta)
    or relative differebce in the number of lines"""

    that: Literal["has_n_lines"] = "has_n_lines"

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_n_lines_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        description=has_n_lines_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_n_lines_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_n_lines_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        description=has_n_lines_negate_description,
    )


has_text_text_description = """The text to search for in the output."""

has_text_n_description = """Desired number, can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_text_delta_description = (
    """Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``"""
)

has_text_min_description = """Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_text_max_description = """Maximum number (default: infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_text_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class has_text_model(AssertionModel):
    r"""Asserts specified output contains the substring specified by
    the argument text. The exact number of occurrences can be
    optionally specified by the argument n"""

    that: Literal["has_text"] = "has_text"

    text: str = Field(
        ...,
        description=has_text_text_description,
    )

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_text_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        description=has_text_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_text_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_text_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        description=has_text_negate_description,
    )


has_text_matching_expression_description = """The regular expressions to attempt match in the output."""

has_text_matching_n_description = """Desired number, can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_text_matching_delta_description = (
    """Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``"""
)

has_text_matching_min_description = """Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_text_matching_max_description = """Maximum number (default: infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_text_matching_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class has_text_matching_model(AssertionModel):
    r"""Asserts the specified output contains text matching the
    regular expression specified by the argument expression.
    If n is given the assertion checks for exacly n (nonoverlapping)
    occurences."""

    that: Literal["has_text_matching"] = "has_text_matching"

    expression: str = Field(
        ...,
        description=has_text_matching_expression_description,
    )

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_text_matching_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        description=has_text_matching_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_text_matching_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_text_matching_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        description=has_text_matching_negate_description,
    )


not_has_text_text_description = """The text to search for in the output."""


class not_has_text_model(AssertionModel):
    r"""Asserts specified output does not contain the substring
    specified by the argument text"""

    that: Literal["not_has_text"] = "not_has_text"

    text: str = Field(
        ...,
        description=not_has_text_text_description,
    )


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


class has_n_columns_model(AssertionModel):
    r"""Asserts tabular output  contains the specified
    number (``n``) of columns.

    For instance, ``<has_n_columns n="3"/>``. The assertion tests only the first line.
    Number of columns can optionally also be specified with ``delta``. Alternatively the
    range of expected occurences can be specified by ``min`` and/or ``max``.

    Optionally a column separator (``sep``, default is ``       ``) `and comment character(s)
    can be specified (``comment``, default is empty string). The first non-comment
    line is used for determining the number of columns."""

    that: Literal["has_n_columns"] = "has_n_columns"

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_n_columns_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        description=has_n_columns_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_n_columns_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_n_columns_max_description,
    )

    sep: str = Field(
        "	",
        description=has_n_columns_sep_description,
    )

    comment: str = Field(
        "",
        description=has_n_columns_comment_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        description=has_n_columns_negate_description,
    )


attribute_is_path_description = """The Python xpath-like expression to find the target element."""

attribute_is_attribute_description = """The XML attribute name to test against from the target XML element."""

attribute_is_text_description = """The expected attribute value to test against on the target XML element"""

attribute_is_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class attribute_is_model(AssertionModel):
    r"""Asserts the XML ``attribute`` for the element (or tag) with the specified
    XPath-like ``path`` is the specified ``text``.

    For example:

    ```xml
    <attribute_is path="outerElement/innerElement1" attribute="foo" text="bar" />
    ```

    The assertion implicitly also asserts that an element matching ``path`` exists.
    With ``negate`` the result of the assertion (on the equality) can be inverted (the
    implicit assertion on the existence of the path is not affected)."""

    that: Literal["attribute_is"] = "attribute_is"

    path: str = Field(
        ...,
        description=attribute_is_path_description,
    )

    attribute: str = Field(
        ...,
        description=attribute_is_attribute_description,
    )

    text: str = Field(
        ...,
        description=attribute_is_text_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        description=attribute_is_negate_description,
    )


attribute_matches_path_description = """The Python xpath-like expression to find the target element."""

attribute_matches_attribute_description = """The XML attribute name to test against from the target XML element."""

attribute_matches_expression_description = (
    """The regular expressions to apply against the named attribute on the target XML element."""
)

attribute_matches_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class attribute_matches_model(AssertionModel):
    r"""Asserts the XML ``attribute`` for the element (or tag) with the specified
    XPath-like ``path`` matches the regular expression specified by ``expression``.

    For example:

    ```xml
    <attribute_matches path="outerElement/innerElement2" attribute="foo2" expression="bar\d+" />
    ```

    The assertion implicitly also asserts that an element matching ``path`` exists.
    With ``negate`` the result of the assertion (on the matching) can be inverted (the
    implicit assertion on the existence of the path is not affected)."""

    that: Literal["attribute_matches"] = "attribute_matches"

    path: str = Field(
        ...,
        description=attribute_matches_path_description,
    )

    attribute: str = Field(
        ...,
        description=attribute_matches_attribute_description,
    )

    expression: Annotated[str, BeforeValidator(check_regex)] = Field(
        ...,
        description=attribute_matches_expression_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        description=attribute_matches_negate_description,
    )


element_text_path_description = """The Python xpath-like expression to find the target element."""

element_text_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class element_text_model(AssertionModel):
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

    that: Literal["element_text"] = "element_text"

    path: str = Field(
        ...,
        description=element_text_path_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        description=element_text_negate_description,
    )

    children: "assertion_list"


element_text_is_path_description = """The Python xpath-like expression to find the target element."""

element_text_is_text_description = (
    """The expected element text (body of the XML tag) to test against on the target XML element"""
)

element_text_is_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class element_text_is_model(AssertionModel):
    r"""Asserts the text of the XML element with the specified XPath-like ``path`` is
    the specified ``text``.

    For example:

    ```xml
    <element_text_is path="BlastOutput_program" text="blastp" />
    ```

    The assertion implicitly also asserts that an element matching ``path`` exists.
    With ``negate`` the result of the assertion (on the equality) can be inverted (the
    implicit assertion on the existence of the path is not affected)."""

    that: Literal["element_text_is"] = "element_text_is"

    path: str = Field(
        ...,
        description=element_text_is_path_description,
    )

    text: str = Field(
        ...,
        description=element_text_is_text_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        description=element_text_is_negate_description,
    )


element_text_matches_path_description = """The Python xpath-like expression to find the target element."""

element_text_matches_expression_description = """The regular expressions to apply against the target element."""

element_text_matches_negate_description = (
    """A boolean that can be set to true to negate the outcome of the assertion."""
)


class element_text_matches_model(AssertionModel):
    r"""Asserts the text of the XML element with the specified XPath-like ``path``
    matches the regular expression defined by ``expression``.

    For example:

    ```xml
    <element_text_matches path="BlastOutput_version" expression="BLASTP\s+2\.2.*"/>
    ```

    The assertion implicitly also asserts that an element matching ``path`` exists.
    With ``negate`` the result of the assertion (on the matching) can be inverted (the
    implicit assertion on the existence of the path is not affected)."""

    that: Literal["element_text_matches"] = "element_text_matches"

    path: str = Field(
        ...,
        description=element_text_matches_path_description,
    )

    expression: Annotated[str, BeforeValidator(check_regex)] = Field(
        ...,
        description=element_text_matches_expression_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        description=element_text_matches_negate_description,
    )


has_element_with_path_path_description = """The Python xpath-like expression to find the target element."""

has_element_with_path_negate_description = (
    """A boolean that can be set to true to negate the outcome of the assertion."""
)


class has_element_with_path_model(AssertionModel):
    r"""Asserts the XML output contains at least one element (or tag) with the specified
    XPath-like ``path``, e.g.

    ```xml
    <has_element_with_path path="BlastOutput_param/Parameters/Parameters_matrix" />
    ```

    With ``negate`` the result of the assertion can be inverted."""

    that: Literal["has_element_with_path"] = "has_element_with_path"

    path: str = Field(
        ...,
        description=has_element_with_path_path_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        description=has_element_with_path_negate_description,
    )


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


class has_n_elements_with_path_model(AssertionModel):
    r"""Asserts the XML output contains the specified number (``n``, optionally with ``delta``) of elements (or
    tags) with the specified XPath-like ``path``.

    For example:

    ```xml
    <has_n_elements_with_path n="9" path="BlastOutput_iterations/Iteration/Iteration_hits/Hit/Hit_num" />
    ```

    Alternatively to ``n`` and ``delta`` also the ``min`` and ``max`` attributes
    can be used to specify the range of the expected number of occurences.
    With ``negate`` the result of the assertion can be inverted."""

    that: Literal["has_n_elements_with_path"] = "has_n_elements_with_path"

    path: str = Field(
        ...,
        description=has_n_elements_with_path_path_description,
    )

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_n_elements_with_path_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        description=has_n_elements_with_path_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_n_elements_with_path_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_n_elements_with_path_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        description=has_n_elements_with_path_negate_description,
    )


class is_valid_xml_model(AssertionModel):
    r"""Asserts the output is a valid XML file (e.g. ``<is_valid_xml />``)."""

    that: Literal["is_valid_xml"] = "is_valid_xml"


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


class xml_element_model(AssertionModel):
    r"""Assert if the XML file contains element(s) or tag(s) with the specified
    [XPath-like ``path``](https://lxml.de/xpathxslt.html).  If ``n`` and ``delta``
    or ``min`` and ``max`` are given also the number of occurences is checked.

    ```xml
    <assert_contents>
      <xml_element path="./elem"/>
      <xml_element path="./elem/more[2]"/>
      <xml_element path=".//more" n="3" delta="1"/>
    </assert_contents>
    ```

    With ``negate="true"`` the outcome of the assertions wrt the precence and number
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
    If ``all`` is ``true`` then the sub assertions are checked for all occurences.

    Note that all other XML assertions can be expressed by this assertion (Galaxy
    also implements the other assertions by calling this one)."""

    that: Literal["xml_element"] = "xml_element"

    path: str = Field(
        ...,
        description=xml_element_path_description,
    )

    attribute: typing.Optional[typing.Union[str]] = Field(
        None,
        description=xml_element_attribute_description,
    )

    all: typing.Union[bool, str] = Field(
        False,
        description=xml_element_all_description,
    )

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=xml_element_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        description=xml_element_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=xml_element_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=xml_element_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        description=xml_element_negate_description,
    )

    children: typing.Optional["assertion_list"] = None


has_json_property_with_text_property_description = """The property name to search the JSON document for."""

has_json_property_with_text_text_description = """The expected text value of the target JSON attribute."""


class has_json_property_with_text_model(AssertionModel):
    r"""Asserts the JSON document contains a property or key with the specified text (i.e. string) value.

    ```xml
    <has_json_property_with_text property="color" text="red" />
    ```"""

    that: Literal["has_json_property_with_text"] = "has_json_property_with_text"

    property: str = Field(
        ...,
        description=has_json_property_with_text_property_description,
    )

    text: str = Field(
        ...,
        description=has_json_property_with_text_text_description,
    )


has_json_property_with_value_property_description = """The property name to search the JSON document for."""

has_json_property_with_value_value_description = (
    """The expected JSON value of the target JSON attribute (as a JSON encoded string)."""
)


class has_json_property_with_value_model(AssertionModel):
    r"""Asserts the JSON document contains a property or key with the specified JSON value.

    ```xml
    <has_json_property_with_value property="skipped_columns" value="[1, 3, 5]" />
    ```"""

    that: Literal["has_json_property_with_value"] = "has_json_property_with_value"

    property: str = Field(
        ...,
        description=has_json_property_with_value_property_description,
    )

    value: str = Field(
        ...,
        description=has_json_property_with_value_value_description,
    )


has_h5_attribute_key_description = """HDF5 attribute to check value of."""

has_h5_attribute_value_description = """Expected value of HDF5 attribute to check."""


class has_h5_attribute_model(AssertionModel):
    r"""Asserts HDF5 output contains the specified ``value`` for an attribute (``key``), e.g.

    ```xml
    <has_h5_attribute key="nchroms" value="15" />
    ```"""

    that: Literal["has_h5_attribute"] = "has_h5_attribute"

    key: str = Field(
        ...,
        description=has_h5_attribute_key_description,
    )

    value: str = Field(
        ...,
        description=has_h5_attribute_value_description,
    )


has_h5_keys_keys_description = """HDF5 attributes to check value of as a comma-separated string."""


class has_h5_keys_model(AssertionModel):
    r"""Asserts the specified HDF5 output has the given keys."""

    that: Literal["has_h5_keys"] = "has_h5_keys"

    keys: str = Field(
        ...,
        description=has_h5_keys_keys_description,
    )


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


class has_archive_member_model(AssertionModel):
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

    that: Literal["has_archive_member"] = "has_archive_member"

    path: str = Field(
        ...,
        description=has_archive_member_path_description,
    )

    all: typing.Union[bool, str] = Field(
        False,
        description=has_archive_member_all_description,
    )

    n: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_archive_member_n_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        description=has_archive_member_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_archive_member_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_archive_member_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        description=has_archive_member_negate_description,
    )

    children: typing.Optional["assertion_list"] = None


has_size_value_description = """Deprecated alias for `size`"""

has_size_size_description = """Desired size of the output (in bytes), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_size_delta_description = (
    """Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``"""
)

has_size_min_description = """Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_size_max_description = """Maximum number (default: infinity), can be suffixed by ``(k|M|G|T|P|E)i?``"""

has_size_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class has_size_model(AssertionModel):
    r"""Asserts the specified output has a size of the specified value

    Attributes size and value or synonyms though value is considered deprecated.
    The size optionally allows for absolute (``delta``) difference."""

    that: Literal["has_size"] = "has_size"

    size: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_size_size_description,
    )

    delta: Annotated[
        typing.Union[int, str], BeforeValidator(check_bytes), BeforeValidator(check_non_negative_if_int)
    ] = Field(
        0,
        description=has_size_delta_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_size_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[str, int]],
        BeforeValidator(check_bytes),
        BeforeValidator(check_non_negative_if_int),
    ] = Field(
        None,
        description=has_size_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        description=has_size_negate_description,
    )


has_image_center_of_mass_center_of_mass_description = """The required center of mass of the image intensities (horizontal and vertical coordinate, separated by a comma)."""

has_image_center_of_mass_channel_description = """Restricts the assertion to a specific channel of the image (where ``0`` corresponds to the first image channel)."""

has_image_center_of_mass_slice_description = (
    """Restricts the assertion to a specific slice of the image (where ``0`` corresponds to the first image slice)."""
)

has_image_center_of_mass_frame_description = """Restricts the assertion to a specific frame of the image sequeqnce (where ``0`` corresponds to the first image frame)."""

has_image_center_of_mass_eps_description = (
    """The maximum allowed Euclidean distance to the required center of mass (defaults to ``0.01``)."""
)


class has_image_center_of_mass_model(AssertionModel):
    r"""Asserts the specified output is an image and has the specified center of mass.

    Asserts the output is an image and has a specific center of mass,
    or has an Euclidean distance of ``eps`` or less to that point (e.g.,
    ``<has_image_center_of_mass center_of_mass="511.07, 223.34" />``)."""

    that: Literal["has_image_center_of_mass"] = "has_image_center_of_mass"

    center_of_mass: Annotated[str, BeforeValidator(check_center_of_mass)] = Field(
        ...,
        description=has_image_center_of_mass_center_of_mass_description,
    )

    channel: typing.Optional[StrictInt] = Field(
        None,
        description=has_image_center_of_mass_channel_description,
    )

    slice: typing.Optional[StrictInt] = Field(
        None,
        description=has_image_center_of_mass_slice_description,
    )

    frame: typing.Optional[StrictInt] = Field(
        None,
        description=has_image_center_of_mass_frame_description,
    )

    eps: Annotated[typing.Union[StrictInt, StrictFloat], BeforeValidator(check_non_negative_if_set)] = Field(
        0.01,
        description=has_image_center_of_mass_eps_description,
    )


has_image_channels_channels_description = """Expected number of channels of the image."""

has_image_channels_delta_description = """Maximum allowed difference of the number of channels (default is 0). The observed number of channels has to be in the range ``value +- delta``."""

has_image_channels_min_description = """Minimum allowed number of channels."""

has_image_channels_max_description = """Maximum allowed number of channels."""

has_image_channels_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class has_image_channels_model(AssertionModel):
    r"""Asserts the output is an image and has a specific number of channels.

    The number of channels is plus/minus ``delta`` (e.g., ``<has_image_channels channels="3" />``).

    Alternatively the range of the expected number of channels can be specified by ``min`` and/or ``max``."""

    that: Literal["has_image_channels"] = "has_image_channels"

    channels: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        description=has_image_channels_channels_description,
    )

    delta: Annotated[StrictInt, BeforeValidator(check_non_negative_if_set)] = Field(
        0,
        description=has_image_channels_delta_description,
    )

    min: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        description=has_image_channels_min_description,
    )

    max: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        description=has_image_channels_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        description=has_image_channels_negate_description,
    )


has_image_depth_depth_description = """Expected depth of the image (number of slices)."""

has_image_depth_delta_description = """Maximum allowed difference of the image depth (number of slices, default is 0). The observed depth has to be in the range ``value +- delta``."""

has_image_depth_min_description = """Minimum allowed depth of the image (number of slices)."""

has_image_depth_max_description = """Maximum allowed depth of the image (number of slices)."""

has_image_depth_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class has_image_depth_model(AssertionModel):
    r"""Asserts the output is an image and has a specific depth (number of slices).

    The depth is plus/minus ``delta`` (e.g., ``<has_image_depth depth="512" delta="2" />``).
    Alternatively the range of the expected depth can be specified by ``min`` and/or ``max``."""

    that: Literal["has_image_depth"] = "has_image_depth"

    depth: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        description=has_image_depth_depth_description,
    )

    delta: Annotated[StrictInt, BeforeValidator(check_non_negative_if_set)] = Field(
        0,
        description=has_image_depth_delta_description,
    )

    min: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        description=has_image_depth_min_description,
    )

    max: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        description=has_image_depth_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        description=has_image_depth_negate_description,
    )


has_image_frames_frames_description = """Expected number of frames in the image sequence (number of time steps)."""

has_image_frames_delta_description = """Maximum allowed difference of the number of frames in the image sequence (number of time steps, default is 0). The observed number of frames has to be in the range ``value +- delta``."""

has_image_frames_min_description = """Minimum allowed number of frames in the image sequence (number of time steps)."""

has_image_frames_max_description = """Maximum allowed number of frames in the image sequence (number of time steps)."""

has_image_frames_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class has_image_frames_model(AssertionModel):
    r"""Asserts the output is an image and has a specific number of frames (number of time steps).

    The number of frames is plus/minus ``delta`` (e.g., ``<has_image_frames depth="512" delta="2" />``).
    Alternatively the range of the expected number of frames can be specified by ``min`` and/or ``max``."""

    that: Literal["has_image_frames"] = "has_image_frames"

    frames: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        description=has_image_frames_frames_description,
    )

    delta: Annotated[StrictInt, BeforeValidator(check_non_negative_if_set)] = Field(
        0,
        description=has_image_frames_delta_description,
    )

    min: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        description=has_image_frames_min_description,
    )

    max: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        description=has_image_frames_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        description=has_image_frames_negate_description,
    )


has_image_height_height_description = """Expected height of the image (in pixels)."""

has_image_height_delta_description = """Maximum allowed difference of the image height (in pixels, default is 0). The observed height has to be in the range ``value +- delta``."""

has_image_height_min_description = """Minimum allowed height of the image (in pixels)."""

has_image_height_max_description = """Maximum allowed height of the image (in pixels)."""

has_image_height_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class has_image_height_model(AssertionModel):
    r"""Asserts the output is an image and has a specific height (in pixels).

    The height is plus/minus ``delta`` (e.g., ``<has_image_height height="512" delta="2" />``).
    Alternatively the range of the expected height can be specified by ``min`` and/or ``max``."""

    that: Literal["has_image_height"] = "has_image_height"

    height: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        description=has_image_height_height_description,
    )

    delta: Annotated[StrictInt, BeforeValidator(check_non_negative_if_set)] = Field(
        0,
        description=has_image_height_delta_description,
    )

    min: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        description=has_image_height_min_description,
    )

    max: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        description=has_image_height_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        description=has_image_height_negate_description,
    )


has_image_mean_intensity_channel_description = """Restricts the assertion to a specific channel of the image (where ``0`` corresponds to the first image channel)."""

has_image_mean_intensity_slice_description = (
    """Restricts the assertion to a specific slice of the image (where ``0`` corresponds to the first image slice)."""
)

has_image_mean_intensity_frame_description = """Restricts the assertion to a specific frame of the image sequeqnce (where ``0`` corresponds to the first image frame)."""

has_image_mean_intensity_mean_intensity_description = """The required mean value of the image intensities."""

has_image_mean_intensity_eps_description = """The absolute tolerance to be used for ``value`` (defaults to ``0.01``). The observed mean value of the image intensities has to be in the range ``value +- eps``."""

has_image_mean_intensity_min_description = """A lower bound of the required mean value of the image intensities."""

has_image_mean_intensity_max_description = """An upper bound of the required mean value of the image intensities."""


class has_image_mean_intensity_model(AssertionModel):
    r"""Asserts the output is an image and has a specific mean intensity value.

    The mean intensity value is plus/minus ``eps`` (e.g., ``<has_image_mean_intensity mean_intensity="0.83" />``).
    Alternatively the range of the expected mean intensity value can be specified by ``min`` and/or ``max``."""

    that: Literal["has_image_mean_intensity"] = "has_image_mean_intensity"

    channel: typing.Optional[StrictInt] = Field(
        None,
        description=has_image_mean_intensity_channel_description,
    )

    slice: typing.Optional[StrictInt] = Field(
        None,
        description=has_image_mean_intensity_slice_description,
    )

    frame: typing.Optional[StrictInt] = Field(
        None,
        description=has_image_mean_intensity_frame_description,
    )

    mean_intensity: typing.Optional[typing.Union[StrictInt, StrictFloat]] = Field(
        None,
        description=has_image_mean_intensity_mean_intensity_description,
    )

    eps: Annotated[typing.Union[StrictInt, StrictFloat], BeforeValidator(check_non_negative_if_set)] = Field(
        0.01,
        description=has_image_mean_intensity_eps_description,
    )

    min: typing.Optional[typing.Union[StrictInt, StrictFloat]] = Field(
        None,
        description=has_image_mean_intensity_min_description,
    )

    max: typing.Optional[typing.Union[StrictInt, StrictFloat]] = Field(
        None,
        description=has_image_mean_intensity_max_description,
    )


has_image_mean_object_size_channel_description = """Restricts the assertion to a specific channel of the image (where ``0`` corresponds to the first image channel)."""

has_image_mean_object_size_slice_description = (
    """Restricts the assertion to a specific slice of the image (where ``0`` corresponds to the first image slice)."""
)

has_image_mean_object_size_frame_description = """Restricts the assertion to a specific frame of the image sequeqnce (where ``0`` corresponds to the first image frame)."""

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


class has_image_mean_object_size_model(AssertionModel):
    r"""Asserts the output is an image with labeled objects which have the specified mean size (number of pixels),

    The mean size is plus/minus ``eps`` (e.g., ``<has_image_mean_object_size mean_object_size="111.87" exclude_labels="0" />``).

    The labels must be unique."""

    that: Literal["has_image_mean_object_size"] = "has_image_mean_object_size"

    channel: typing.Optional[StrictInt] = Field(
        None,
        description=has_image_mean_object_size_channel_description,
    )

    slice: typing.Optional[StrictInt] = Field(
        None,
        description=has_image_mean_object_size_slice_description,
    )

    frame: typing.Optional[StrictInt] = Field(
        None,
        description=has_image_mean_object_size_frame_description,
    )

    labels: typing.Optional[typing.List[int]] = Field(
        None,
        description=has_image_mean_object_size_labels_description,
    )

    exclude_labels: typing.Optional[typing.List[int]] = Field(
        None,
        description=has_image_mean_object_size_exclude_labels_description,
    )

    mean_object_size: Annotated[
        typing.Optional[typing.Union[StrictInt, StrictFloat]], BeforeValidator(check_non_negative_if_set)
    ] = Field(
        None,
        description=has_image_mean_object_size_mean_object_size_description,
    )

    eps: Annotated[typing.Union[StrictInt, StrictFloat], BeforeValidator(check_non_negative_if_set)] = Field(
        0.01,
        description=has_image_mean_object_size_eps_description,
    )

    min: Annotated[
        typing.Optional[typing.Union[StrictInt, StrictFloat]], BeforeValidator(check_non_negative_if_set)
    ] = Field(
        None,
        description=has_image_mean_object_size_min_description,
    )

    max: Annotated[
        typing.Optional[typing.Union[StrictInt, StrictFloat]], BeforeValidator(check_non_negative_if_set)
    ] = Field(
        None,
        description=has_image_mean_object_size_max_description,
    )


has_image_n_labels_channel_description = """Restricts the assertion to a specific channel of the image (where ``0`` corresponds to the first image channel)."""

has_image_n_labels_slice_description = (
    """Restricts the assertion to a specific slice of the image (where ``0`` corresponds to the first image slice)."""
)

has_image_n_labels_frame_description = """Restricts the assertion to a specific frame of the image sequeqnce (where ``0`` corresponds to the first image frame)."""

has_image_n_labels_labels_description = """List of labels, separated by a comma. Labels *not* on this list will be excluded from consideration. Cannot be used in combination with ``exclude_labels``."""

has_image_n_labels_exclude_labels_description = """List of labels to be excluded from consideration, separated by a comma. The primary usage of this attribute is to exclude the background of a label image. Cannot be used in combination with ``labels``."""

has_image_n_labels_n_description = """Expected number of labels."""

has_image_n_labels_delta_description = """Maximum allowed difference of the number of labels (default is 0). The observed number of labels has to be in the range ``value +- delta``."""

has_image_n_labels_min_description = """Minimum allowed number of labels."""

has_image_n_labels_max_description = """Maximum allowed number of labels."""

has_image_n_labels_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class has_image_n_labels_model(AssertionModel):
    r"""Asserts the output is an image and has the specified labels.

    Labels can be a number of labels or unique values (e.g.,
    ``<has_image_n_labels n="187" exclude_labels="0" />``).

    The primary usage of this assertion is to verify the number of objects in images with uniquely labeled objects."""

    that: Literal["has_image_n_labels"] = "has_image_n_labels"

    channel: typing.Optional[StrictInt] = Field(
        None,
        description=has_image_n_labels_channel_description,
    )

    slice: typing.Optional[StrictInt] = Field(
        None,
        description=has_image_n_labels_slice_description,
    )

    frame: typing.Optional[StrictInt] = Field(
        None,
        description=has_image_n_labels_frame_description,
    )

    labels: typing.Optional[typing.List[int]] = Field(
        None,
        description=has_image_n_labels_labels_description,
    )

    exclude_labels: typing.Optional[typing.List[int]] = Field(
        None,
        description=has_image_n_labels_exclude_labels_description,
    )

    n: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        description=has_image_n_labels_n_description,
    )

    delta: Annotated[StrictInt, BeforeValidator(check_non_negative_if_set)] = Field(
        0,
        description=has_image_n_labels_delta_description,
    )

    min: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        description=has_image_n_labels_min_description,
    )

    max: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        description=has_image_n_labels_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        description=has_image_n_labels_negate_description,
    )


has_image_width_width_description = """Expected width of the image (in pixels)."""

has_image_width_delta_description = """Maximum allowed difference of the image width (in pixels, default is 0). The observed width has to be in the range ``value +- delta``."""

has_image_width_min_description = """Minimum allowed width of the image (in pixels)."""

has_image_width_max_description = """Maximum allowed width of the image (in pixels)."""

has_image_width_negate_description = """A boolean that can be set to true to negate the outcome of the assertion."""


class has_image_width_model(AssertionModel):
    r"""Asserts the output is an image and has a specific width (in pixels).

    The width is plus/minus ``delta`` (e.g., ``<has_image_width width="512" delta="2" />``).
    Alternatively the range of the expected width can be specified by ``min`` and/or ``max``."""

    that: Literal["has_image_width"] = "has_image_width"

    width: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        description=has_image_width_width_description,
    )

    delta: Annotated[StrictInt, BeforeValidator(check_non_negative_if_set)] = Field(
        0,
        description=has_image_width_delta_description,
    )

    min: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        description=has_image_width_min_description,
    )

    max: Annotated[typing.Optional[StrictInt], BeforeValidator(check_non_negative_if_set)] = Field(
        None,
        description=has_image_width_max_description,
    )

    negate: typing.Union[bool, str] = Field(
        False,
        description=has_image_width_negate_description,
    )


any_assertion_model = Annotated[
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

assertion_list = RootModel[typing.List[any_assertion_model]]
