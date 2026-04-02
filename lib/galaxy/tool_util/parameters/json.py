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


def _absent_test_params(defs: Dict[str, Any]) -> Dict[str, str]:
    """Map test parameter names to their absent branch def names, longest name first."""
    result: Dict[str, str] = {}
    for def_name in defs:
        m = WHEN_ABSENT_RE.match(def_name)
        if m:
            result[m.group(1)] = def_name
    return dict(sorted(result.items(), key=lambda item: len(item[0]), reverse=True))


def _match_when_branch(def_name: str, absent_test_params: Dict[str, str]) -> Any:
    """Return (test_param_name, value_suffix) for an explicit When branch, or None."""
    if not def_name.startswith("When_") or "___absent" in def_name:
        return None
    for test_param_name in absent_test_params:
        prefix = f"When_{test_param_name}_"
        if def_name.startswith(prefix):
            return test_param_name, def_name[len(prefix) :]
    return None


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

    atp = _absent_test_params(defs)
    if not atp:
        return

    for def_name, def_schema in defs.items():
        match = _match_when_branch(def_name, atp)
        if match:
            _make_field_required(def_schema, match[0])


def _make_field_required(def_schema: Dict[str, Any], field_name: str) -> None:
    props = def_schema.get("properties", {})
    if field_name not in props:
        return
    required: List[str] = def_schema.get("required", [])
    if field_name not in required:
        required.append(field_name)
        def_schema["required"] = required
    props[field_name].pop("default", None)


def _discriminator_key(def_schema: Dict[str, Any], test_param_name: str, value_suffix: str) -> str:
    """Derive the discriminator mapping key from the branch's const value.

    Uses the actual ``const`` value from the schema property so boolean branches
    map to ``"true"``/``"false"`` (JSON style) rather than ``"True"``/``"False"``.
    """
    props = def_schema.get("properties", {})
    test_prop = props.get(test_param_name, {})
    const = test_prop.get("const")
    if const is not None:
        return json.dumps(const) if isinstance(const, bool) else str(const)
    return value_suffix


def _add_conditional_discriminators(schema: Dict[str, Any]) -> None:
    """Add OpenAPI 3.1 discriminator objects and human-readable titles to conditional oneOfs."""
    defs = schema.get("$defs", {})
    if not defs:
        return

    atp = _absent_test_params(defs)
    if not atp:
        return

    for def_name, def_schema in defs.items():
        if def_name in atp.values():
            for param_name, absent_name in atp.items():
                if def_name == absent_name:
                    def_schema["title"] = f"When {param_name} is absent"
                    break
        else:
            match = _match_when_branch(def_name, atp)
            if match:
                def_schema["title"] = f"When {match[0]} = {match[1]}"

    for def_schema in defs.values():
        one_of = def_schema.get("oneOf")
        if not isinstance(one_of, list):
            continue

        test_param_name = _conditional_test_param_for_oneof(one_of, atp)
        if test_param_name is None:
            continue

        mapping: Dict[str, str] = {}
        for branch in one_of:
            ref = branch.get("$ref", "")
            branch_def_name = ref.rsplit("/", 1)[-1] if "/" in ref else ""
            match = _match_when_branch(branch_def_name, atp)
            if match and match[0] == test_param_name:
                branch_def = defs.get(branch_def_name, {})
                key = _discriminator_key(branch_def, test_param_name, match[1])
                mapping[key] = ref

        if mapping:
            def_schema["discriminator"] = {
                "propertyName": test_param_name,
                "mapping": mapping,
            }


def _conditional_test_param_for_oneof(one_of: List[Any], absent_test_params: Dict[str, str]) -> Any:
    """Return the test parameter name if this oneOf is a conditional discriminated union."""
    for branch in one_of:
        ref = branch.get("$ref", "")
        branch_def_name = ref.rsplit("/", 1)[-1] if "/" in ref else ""
        for param_name, absent_name in absent_test_params.items():
            if branch_def_name == absent_name:
                return param_name
    return None


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


_ANNOTATED_TYPES_TO_JSON_SCHEMA = {
    "ge": "minimum",
    "gt": "exclusiveMinimum",
    "le": "maximum",
    "lt": "exclusiveMaximum",
}


def _normalize_annotated_types_keywords(schema: Dict[str, Any]) -> None:
    """Convert annotated_types constraint keys to standard JSON Schema keywords.

    When annotated_types constraints (Ge, Gt, Le, Lt) are applied to Union types,
    Pydantic emits them as raw keys (ge, gt, le, lt) instead of the standard
    JSON Schema keywords (minimum, exclusiveMinimum, etc.). Normalize these.
    """
    _walk_and_normalize(schema)


def _walk_and_normalize(node: Any) -> None:
    if not isinstance(node, dict):
        if isinstance(node, list):
            for item in node:
                _walk_and_normalize(item)
        return

    for at_key, js_key in _ANNOTATED_TYPES_TO_JSON_SCHEMA.items():
        if at_key in node and js_key not in node:
            node[js_key] = node.pop(at_key)

    for value in node.values():
        _walk_and_normalize(value)


def to_json_schema(model, mode: MODE = DEFAULT_JSON_SCHEMA_MODE) -> Dict[str, Any]:
    schema = model.model_json_schema(schema_generator=CustomGenerateJsonSchema, mode=mode)
    _fix_conditional_oneofs(schema)
    _add_conditional_discriminators(schema)
    _fix_collection_runtime_oneofs(schema)
    _normalize_annotated_types_keywords(schema)
    return schema


def to_json_schema_string(model, mode: MODE = DEFAULT_JSON_SCHEMA_MODE) -> str:
    return json.dumps(to_json_schema(model, mode=mode), indent=4)
