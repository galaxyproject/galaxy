import json
import re
from typing import (
    Any,
    Dict,
    List,
)

from pydantic.json_schema import GenerateJsonSchema
from typing_extensions import Literal

MODE = Literal["validation", "serialization"]
DEFAULT_JSON_SCHEMA_MODE: MODE = "validation"

WHEN_ABSENT_RE = re.compile(r"^When_(.+)___absent$")


class CustomGenerateJsonSchema(GenerateJsonSchema):

    def generate(self, schema, mode: MODE = DEFAULT_JSON_SCHEMA_MODE):
        json_schema = super().generate(schema, mode=mode)
        json_schema["$schema"] = self.schema_dialect
        return json_schema


def _fix_conditional_oneofs(schema: Dict[str, Any]) -> None:
    """Make conditional discriminated unions unambiguous for JSON Schema validators.

    Pydantic uses a custom callable discriminator for conditionals that doesn't
    translate to JSON Schema. The result is a bare oneOf where explicit When branches
    (When_<test>_<value>) overlap with the absent branch (When_<test>___absent) because
    the test parameter field has a default and is therefore not required.

    Fix: for each explicit When branch, add the test parameter to ``required`` and
    remove its ``default``. This makes ``oneOf`` branches mutually exclusive.
    """
    defs = schema.get("$defs", {})
    if not defs:
        return

    absent_test_params: Dict[str, str] = {}
    for def_name in defs:
        m = WHEN_ABSENT_RE.match(def_name)
        if m:
            absent_test_params[m.group(1)] = def_name

    if not absent_test_params:
        return

    for def_name, def_schema in defs.items():
        if def_name.startswith("When_") and "___absent" not in def_name:
            for test_param_name in absent_test_params:
                prefix = f"When_{test_param_name}_"
                if def_name.startswith(prefix):
                    _make_field_required(def_schema, test_param_name)
                    break


def _make_field_required(def_schema: Dict[str, Any], field_name: str) -> None:
    props = def_schema.get("properties", {})
    if field_name not in props:
        return
    required: List[str] = def_schema.get("required", [])
    if field_name not in required:
        required.append(field_name)
        def_schema["required"] = required
    props[field_name].pop("default", None)


COLLECTION_RUNTIME_NESTED_DEFS = frozenset(["DataCollectionNestedListRuntime", "DataCollectionNestedRecordRuntime"])


def _fix_collection_runtime_oneofs(schema: Dict[str, Any]) -> None:
    """Convert collection runtime oneOf to anyOf to avoid discriminator overlap.

    The Pydantic callable discriminator routes by collection_type pattern but
    JSON Schema can't represent that. The nested variants have collection_type
    as plain string which overlaps with the Literal const branches, causing
    oneOf to reject valid inputs that match multiple branches. anyOf accepts
    if at least one branch matches, which is the correct semantic here.
    """
    _walk_and_fix_collection_oneofs(schema)


def _walk_and_fix_collection_oneofs(node: Any) -> None:
    if not isinstance(node, dict):
        if isinstance(node, list):
            for item in node:
                _walk_and_fix_collection_oneofs(item)
        return

    if "oneOf" in node:
        one_of = node["oneOf"]
        if isinstance(one_of, list) and _is_collection_runtime_oneof(one_of):
            node["anyOf"] = node.pop("oneOf")

    for value in node.values():
        _walk_and_fix_collection_oneofs(value)


def _is_collection_runtime_oneof(branches: List[Any]) -> bool:
    for branch in branches:
        ref = branch.get("$ref", "")
        def_name = ref.rsplit("/", 1)[-1] if "/" in ref else ""
        if def_name in COLLECTION_RUNTIME_NESTED_DEFS:
            return True
    return False


def to_json_schema(model, mode: MODE = DEFAULT_JSON_SCHEMA_MODE) -> Dict[str, Any]:
    schema = model.model_json_schema(schema_generator=CustomGenerateJsonSchema, mode=mode)
    _fix_conditional_oneofs(schema)
    _fix_collection_runtime_oneofs(schema)
    return schema


def to_json_schema_string(model, mode: MODE = DEFAULT_JSON_SCHEMA_MODE) -> str:
    return json.dumps(to_json_schema(model, mode=mode), indent=4)
