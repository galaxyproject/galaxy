import json
from typing import (
    Any,
    Callable,
    cast,
)

from ._types import (
    Annotated,
    AssertionParameter,
    Output,
)

PropertyVisitor = Callable[[str, Any], Any]

Property = Annotated[str, AssertionParameter("The property name to search the JSON document for.")]
Text = Annotated[str, AssertionParameter("The expected text value of the target JSON attribute.")]
Value = Annotated[
    str, AssertionParameter("The expected JSON value of the target JSON attribute (as a JSON encoded string).")
]


def any_in_tree(f: PropertyVisitor, json_tree: Any):
    if isinstance(json_tree, list):
        for element in json_tree:
            if any_in_tree(f, element):
                return True

    elif isinstance(json_tree, dict):
        for key, value in json_tree.items():
            if f(cast(str, key), value):
                return True
            elif any_in_tree(f, value):
                return True

    return False


def assert_has_json_property_with_value(
    output: Output,
    property: Property,
    value: Value,
):
    """Asserts the JSON document contains a property or key with the specified JSON value.

    ```xml
    <has_json_property_with_value property="skipped_columns" value="[1, 3, 5]" />
    ```
    """
    output_json = _assert_json_and_load(output)
    expected_value = _assert_json_and_load(value)

    def is_property(key, value):
        return key == property and value == expected_value

    assert any_in_tree(is_property, output_json), f"Failed to find property [{property}] with JSON value [{value}]"


def assert_has_json_property_with_text(
    output: Output,
    property: Property,
    text: Text,
):
    """Asserts the JSON document contains a property or key with the specified text (i.e. string) value.

    ```xml
    <has_json_property_with_text property="color" text="red" />
    ```
    """
    output_json = _assert_json_and_load(output)

    def is_property(key, value):
        return key == property and value == text

    assert any_in_tree(is_property, output_json), f"Failed to find property [{property}] with text [{text}]"


def _assert_json_and_load(json_str: str):
    try:
        return json.loads(json_str)
    except Exception:
        raise AssertionError(f"Failed to parse JSON from {json_str[0:1024]}.")
