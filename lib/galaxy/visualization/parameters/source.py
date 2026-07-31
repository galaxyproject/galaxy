"""Low-level readers over the visualization plugin XML input elements.

Visualization inputs use a child-element dialect (``<name>``, ``<type>``,
``<min>``, ...) and a plural-wrapper convention where a list is a wrapper element
whose children repeat the wrapper's own tag: ``<data><data>...</data></data>``
for select options, ``<cases><cases>...</cases></cases>`` for conditional cases,
``<inputs><inputs>...</inputs></inputs>`` for a case's inputs, and
``<tables><tables>...</tables></tables>`` for data-table names.

The generic ``ListParser``/``DictParser`` in ``plugins/config_parser.py`` cannot
distinguish these from ordinary nesting, so this module walks the ElementTree
directly with type awareness.
"""

from xml.etree.ElementTree import Element


def text(elem: Element | None, tag: str) -> str | None:
    """Return the stripped text of ``elem``'s ``tag`` child, or None."""
    if elem is None:
        return None
    child = elem.find(tag)
    if child is None or child.text is None:
        return None
    return child.text.strip()


def value_of(elem: Element) -> str | None:
    """Return an input's default from its ``<value>`` child.

    A present-but-empty ``<value></value>`` is a real default (empty string), so
    it returns ``""``; only an absent element returns None. This distinction
    decides whether the input is required.
    """
    child = elem.find("value")
    if child is None:
        return None
    return (child.text or "").strip()


def asbool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("true", "yes", "on", "1")


def flag(elem: Element, tag: str, default: bool = False) -> bool:
    return asbool(text(elem, tag), default)


def as_int(elem: Element, tag: str) -> int | None:
    value = text(elem, tag)
    return int(value) if value not in (None, "") else None


def as_float(elem: Element, tag: str) -> float | None:
    value = text(elem, tag)
    return float(value) if value not in (None, "") else None


def wrapped_children(elem: Element, tag: str) -> list[Element]:
    """Return the repeated children of a plural wrapper ``<tag><tag>...``."""
    wrapper = elem.find(tag)
    if wrapper is None:
        return []
    return wrapper.findall(tag)


def input_elements(section: Element | None) -> list[Element]:
    """Return the ``<input>`` children of a ``<settings>``/``<tracks>`` section."""
    if section is None:
        return []
    return section.findall("input")
