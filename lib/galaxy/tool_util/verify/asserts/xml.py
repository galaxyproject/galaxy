import re
from typing import Optional

from lxml.etree import XMLSyntaxError

from galaxy.tool_util.verify import asserts
from galaxy.util import (
    asbool,
    parse_xml_string,
    unicodify,
)
from ._types import (
    Annotated,
    AssertionParameter,
    ChildAssertions,
    Delta,
    Max,
    Min,
    N,
    Negate,
    NEGATE_DEFAULT,
    Output,
    VerifyAssertionsFunction,
    XmlBool,
    XmlRegex,
)

Path = Annotated[str, AssertionParameter("The Python xpath-like expression to find the target element.")]
ElementExpression = Annotated[
    XmlRegex,
    AssertionParameter("The regular expressions to apply against the target element.", validators=["check_regex"]),
]
AttributeExpression = Annotated[
    XmlRegex,
    AssertionParameter(
        "The regular expressions to apply against the named attribute on the target XML element.",
        validators=["check_regex"],
    ),
]
Attribute = Annotated[str, AssertionParameter("The XML attribute name to test against from the target XML element.")]
OptionalAttribute = Annotated[
    Optional[str], AssertionParameter("The XML attribute name to test against from the target XML element.")
]
ElementText = Annotated[
    str, AssertionParameter("The expected element text (body of the XML tag) to test against on the target XML element")
]
AttributeText = Annotated[
    str, AssertionParameter("The expected attribute value to test against on the target XML element")
]
All = Annotated[
    XmlBool,
    AssertionParameter(
        "Check the sub-assertions for all paths matching the path. Default: false, i.e. only the first ",
        xml_type="PermissiveBoolean",
    ),
]


def assert_is_valid_xml(output: Output) -> None:
    """Asserts the output is a valid XML file (e.g. ``<is_valid_xml />``)."""
    try:
        parse_xml_string(output)
    except XMLSyntaxError as e:
        raise AssertionError(f"Expected valid XML, but could not parse output. {unicodify(e)}")


def assert_has_element_with_path(output: Output, path: Path, negate: Negate = NEGATE_DEFAULT) -> None:
    """Asserts the XML output contains at least one element (or tag) with the specified
    XPath-like ``path``, e.g.

    ```xml
    <has_element_with_path path="BlastOutput_param/Parameters/Parameters_matrix" />
    ```

    With ``negate`` the result of the assertion can be inverted."""
    assert_xml_element(output, path, negate=negate)


def assert_has_n_elements_with_path(
    output: Output,
    path: Path,
    n: N = None,
    delta: Delta = 0,
    min: Min = None,
    max: Max = None,
    negate: Negate = NEGATE_DEFAULT,
) -> None:
    """Asserts the XML output contains the specified number (``n``, optionally with ``delta``) of elements (or
    tags) with the specified XPath-like ``path``.

    For example:

    ```xml
    <has_n_elements_with_path n="9" path="BlastOutput_iterations/Iteration/Iteration_hits/Hit/Hit_num" />
    ```

    Alternatively to ``n`` and ``delta`` also the ``min`` and ``max`` attributes
    can be used to specify the range of the expected number of occurences.
    With ``negate`` the result of the assertion can be inverted.
    """
    assert_xml_element(output, path, n=n, delta=delta, min=min, max=max, negate=negate)


def assert_element_text_matches(
    output: Output, path: Path, expression: ElementExpression, negate: Negate = NEGATE_DEFAULT
) -> None:
    """Asserts the text of the XML element with the specified XPath-like ``path``
    matches the regular expression defined by ``expression``.

    For example:

    ```xml
    <element_text_matches path="BlastOutput_version" expression="BLASTP\\s+2\\.2.*"/>
    ```

    The assertion implicitly also asserts that an element matching ``path`` exists.
    With ``negate`` the result of the assertion (on the matching) can be inverted (the
    implicit assertion on the existence of the path is not affected).
    """
    sub = {"tag": "has_text_matching", "attributes": {"expression": expression, "negate": negate}}
    assert_xml_element(output, path, asserts.verify_assertions, [sub])


def assert_element_text_is(output: Output, path: Path, text: ElementText, negate: Negate = NEGATE_DEFAULT) -> None:
    """Asserts the text of the XML element with the specified XPath-like ``path`` is
    the specified ``text``.

    For example:

    ```xml
    <element_text_is path="BlastOutput_program" text="blastp" />
    ```

    The assertion implicitly also asserts that an element matching ``path`` exists.
    With ``negate`` the result of the assertion (on the equality) can be inverted (the
    implicit assertion on the existence of the path is not affected).
    """
    assert_element_text_matches(output, path, re.escape(text) + "$", negate=negate)


def assert_attribute_matches(
    output: Output,
    path: Path,
    attribute: Attribute,
    expression: AttributeExpression,
    negate: Negate = NEGATE_DEFAULT,
) -> None:
    """Asserts the XML ``attribute`` for the element (or tag) with the specified
    XPath-like ``path`` matches the regular expression specified by ``expression``.

    For example:

    ```xml
    <attribute_matches path="outerElement/innerElement2" attribute="foo2" expression="bar\\d+" />
    ```

    The assertion implicitly also asserts that an element matching ``path`` exists.
    With ``negate`` the result of the assertion (on the matching) can be inverted (the
    implicit assertion on the existence of the path is not affected).
    """
    sub = {"tag": "has_text_matching", "attributes": {"expression": expression, "negate": negate}}
    assert_xml_element(output, path, asserts.verify_assertions, [sub], attribute=attribute)


def assert_attribute_is(
    output: Output, path: Path, attribute: Attribute, text: AttributeText, negate: Negate = NEGATE_DEFAULT
) -> None:
    """Asserts the XML ``attribute`` for the element (or tag) with the specified
    XPath-like ``path`` is the specified ``text``.

    For example:

    ```xml
    <attribute_is path="outerElement/innerElement1" attribute="foo" text="bar" />
    ```

    The assertion implicitly also asserts that an element matching ``path`` exists.
    With ``negate`` the result of the assertion (on the equality) can be inverted (the
    implicit assertion on the existence of the path is not affected).
    """
    assert_attribute_matches(output, path, attribute, re.escape(text) + "$", negate=negate)


def assert_element_text(
    output: Output,
    path: Path,
    verify_assertions_function: VerifyAssertionsFunction,
    children: ChildAssertions,
    negate: Negate = NEGATE_DEFAULT,
) -> None:
    """This tag allows the developer to recurisively specify additional assertions as
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
    by ``negate``.
    """
    assert_xml_element(output, path, verify_assertions_function, children, negate=negate)


def assert_xml_element(
    output: Output,
    path: Path,
    verify_assertions_function: Optional[VerifyAssertionsFunction] = None,
    children: ChildAssertions = None,
    attribute: OptionalAttribute = None,
    all: All = False,
    n: N = None,
    delta: Delta = 0,
    min: Min = None,
    max: Max = None,
    negate: Negate = NEGATE_DEFAULT,
) -> None:
    """Assert if the XML file contains element(s) or tag(s) with the specified
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
    also implements the other assertions by calling this one).
    """
    children = children or []
    all = asbool(all)
    # assert that path is in output (the specified number of times)

    xml = parse_xml_string(output)
    asserts._util._assert_presence_number(
        xml,
        path,
        n,
        delta,
        min,
        max,
        negate,
        lambda x, p: x.find(p) is not None,
        lambda x, p: len(x.findall(p)),
        "{expected} path '{text}' in xml",
        "{expected} {n}+-{delta} occurrences of path '{text}' in xml",
        "{expected} that the number of occurences of path '{text}' in xml is in [{min}:{max}]",
    )

    # check sub-assertions
    if len(children) == 0 or verify_assertions_function is None:
        return
    for occ in xml.findall(path):
        if attribute is None or attribute == "":
            content = occ.text
        else:
            content = occ.attrib[attribute]  # type: ignore[assignment] # https://github.com/lxml/lxml-stubs/pull/99
        try:
            if content is None:
                raise AssertionError("Failed to find expected XML content")
            verify_assertions_function(content.encode("utf-8"), children)
        except AssertionError as e:
            if attribute is not None and attribute != "":
                raise AssertionError(f"Attribute '{attribute}' on element with path '{path}': {str(e)}")
            else:
                raise AssertionError(f"Text of element with path '{path}': {str(e)}")
        if not all:
            break
