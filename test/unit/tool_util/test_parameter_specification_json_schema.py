"""Validate parameter_specification.yml entries against JSON Schema generated from Pydantic models.

This mirrors test_parameter_specification.py but validates against JSON Schema (Draft 2020-12)
instead of Pydantic models directly. The goal is to prove the exported JSON Schemas are usable
from non-Python toolkits.

Many Galaxy validators now emit native JSON Schema keywords (pattern, minimum/maximum,
minLength/maxLength, exclusiveMinimum/exclusiveMaximum, and negated length via not:{}).
Remaining AfterValidator-only constraints (expression, empty_field) that cannot be represented
in JSON Schema are annotated with _json_schema_skip in parameter_specification.yml so the test
knows to tolerate those *_invalid entries passing validation.
"""

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
)

import jsonschema
import yaml

from galaxy.tool_util.parameters.json import to_json_schema
from galaxy.tool_util.unittest_utils.parameters import (
    parameter_bundle_for_file,
)
from galaxy.tool_util_models.parameters import (
    create_field_model,
    RawStateDict,
    StateRepresentationT,
    ToolParameterBundleModel,
)
from galaxy.util.resources import resource_string

REPRESENTATION_KEYS = [
    "relaxed_request",
    "request",
    "request_internal",
    "request_internal_dereferenced",
    "landing_request",
    "landing_request_internal",
    "job_internal",
    "job_runtime",
    "test_case_xml",
    "test_case_json",
    "workflow_step",
    "workflow_step_linked",
]

STATE_REPRESENTATION_FOR_KEY: Dict[str, StateRepresentationT] = {k: k for k in REPRESENTATION_KEYS}  # type: ignore[misc]


def specification_object():
    try:
        yaml_str = resource_string(__name__, "parameter_specification.yml")
    except AttributeError:
        yaml_str = open("test/unit/tool_util/parameter_specification.yml").read()
    return yaml.safe_load(yaml_str)


def _json_schema_for(bundle: ToolParameterBundleModel, state_representation: StateRepresentationT) -> Dict[str, Any]:
    model = create_field_model(bundle.parameters, name="TestModel", state_representation=state_representation)
    return to_json_schema(model)


def _json_schema_validates(schema: Dict[str, Any], state_dict: RawStateDict) -> bool:
    validator = jsonschema.Draft202012Validator(schema)
    errors = list(validator.iter_errors(state_dict))
    return len(errors) == 0


def _test_file_json_schema(
    file: str,
    specification=None,
    parameter_bundle: Optional[ToolParameterBundleModel] = None,
):
    spec = specification or specification_object()
    combos = spec[file]
    if parameter_bundle is None:
        parameter_bundle = parameter_bundle_for_file(file)
    assert parameter_bundle

    json_schema_skip: Dict[str, str] = combos.get("_json_schema_skip", {}) or {}
    json_schema_valid_skip: Dict[str, str] = combos.get("_json_schema_valid_skip", {}) or {}
    skipped_invalid_keys: Set[str] = set(json_schema_skip.keys())
    skipped_valid_keys: Set[str] = set(json_schema_valid_skip.keys())

    failures: List[str] = []

    for combo_key, test_cases in combos.items():
        if combo_key in ("_json_schema_skip", "_json_schema_valid_skip"):
            continue
        if not isinstance(test_cases, list):
            continue

        if combo_key.endswith("_valid"):
            is_valid = True
            rep_key = combo_key[: -len("_valid")]
        elif combo_key.endswith("_invalid"):
            is_valid = False
            rep_key = combo_key[: -len("_invalid")]
        else:
            continue

        state_representation = STATE_REPRESENTATION_FOR_KEY.get(rep_key)
        if state_representation is None:
            continue

        schema = _json_schema_for(parameter_bundle, state_representation)

        for i, test_case in enumerate(test_cases):
            passes = _json_schema_validates(schema, test_case)

            if is_valid and not passes and combo_key not in skipped_valid_keys:
                failures.append(f"{file}/{combo_key}[{i}]: valid entry REJECTED by JSON Schema: {test_case}")
            elif not is_valid and passes and combo_key not in skipped_invalid_keys:
                failures.append(
                    f"{file}/{combo_key}[{i}]: invalid entry ACCEPTED by JSON Schema (not skipped): {test_case}"
                )

    if failures:
        raise AssertionError(
            f"{len(failures)} JSON Schema validation divergence(s) for {file}:\n" + "\n".join(failures)
        )


def test_specification_json_schema():
    parameter_spec = specification_object()
    for file in parameter_spec.keys():
        _test_file_json_schema(file, parameter_spec)


def _conditional_type_def(file: str, state_representation: StateRepresentationT = "request") -> Dict[str, Any]:
    bundle = parameter_bundle_for_file(file)
    schema = _json_schema_for(bundle, state_representation)
    defs = schema.get("$defs", {})
    matches = {k: v for k, v in defs.items() if "oneOf" in v}
    assert len(matches) == 1, f"Expected exactly one oneOf def, got {list(matches.keys())}"
    return next(iter(matches.values())), defs


def test_boolean_conditional_discriminator():
    cond_def, defs = _conditional_type_def("gx_conditional_boolean")
    disc = cond_def.get("discriminator")
    assert disc is not None
    assert disc["propertyName"] == "test_parameter"
    mapping = disc["mapping"]
    assert "true" in mapping
    assert "false" in mapping
    assert len(mapping) == 2

    assert defs["When_test_parameter_True"]["title"] == "When test_parameter = True"
    assert defs["When_test_parameter_False"]["title"] == "When test_parameter = False"
    assert defs["When_test_parameter___absent"]["title"] == "When test_parameter is absent"


def test_select_conditional_discriminator():
    cond_def, defs = _conditional_type_def("gx_conditional_select")
    disc = cond_def.get("discriminator")
    assert disc is not None
    assert disc["propertyName"] == "test_parameter"
    mapping = disc["mapping"]
    assert set(mapping.keys()) == {"a", "b", "c"}

    assert defs["When_test_parameter_a"]["title"] == "When test_parameter = a"
    assert defs["When_test_parameter___absent"]["title"] == "When test_parameter is absent"


def test_job_internal_no_discriminator():
    bundle = parameter_bundle_for_file("gx_conditional_boolean")
    schema = _json_schema_for(bundle, "job_internal")
    defs = schema.get("$defs", {})
    for def_schema in defs.values():
        assert "discriminator" not in def_schema
