from collections.abc import Sequence
from typing import (
    Any,
    cast,
    Literal,
    Union,
)

from fastapi._compat.v2 import (
    _has_computed_fields,
    get_flat_models_from_fields,
    ModelField,
)
from fastapi.openapi.constants import REF_TEMPLATE
from fastapi.types import ModelNameMap
from pydantic.fields import FieldInfo as FieldInfo
from pydantic.json_schema import (
    GenerateJsonSchema as GenerateJsonSchema,
    JsonSchemaValue as JsonSchemaValue,
)


def get_definitions(
    *,
    fields: Sequence[ModelField],
    model_name_map: ModelNameMap,
    separate_input_output_schemas: bool = True,
    schema_generator: Union[GenerateJsonSchema, None] = None,
) -> tuple[
    dict[tuple[ModelField, Literal["validation", "serialization"]], JsonSchemaValue],
    dict[str, dict[str, Any]],
]:
    schema_generator = schema_generator or GenerateJsonSchema(ref_template=REF_TEMPLATE)
    validation_fields = [field for field in fields if field.mode == "validation"]
    serialization_fields = [field for field in fields if field.mode == "serialization"]
    flat_validation_models = get_flat_models_from_fields(validation_fields, known_models=set())
    flat_serialization_models = get_flat_models_from_fields(serialization_fields, known_models=set())
    flat_validation_model_fields = [
        ModelField(
            field_info=FieldInfo(annotation=model),
            name=model.__name__,
            mode="validation",
        )
        for model in flat_validation_models
    ]
    flat_serialization_model_fields = [
        ModelField(
            field_info=FieldInfo(annotation=model),
            name=model.__name__,
            mode="serialization",
        )
        for model in flat_serialization_models
    ]
    flat_model_fields = flat_validation_model_fields + flat_serialization_model_fields
    input_types = {f.field_info.annotation for f in fields}
    unique_flat_model_fields = {f for f in flat_model_fields if f.field_info.annotation not in input_types}
    inputs = [
        (
            field,
            (field.mode if (separate_input_output_schemas or _has_computed_fields(field)) else "validation"),
            field._type_adapter.core_schema,
        )
        for field in list(fields) + list(unique_flat_model_fields)
    ]
    field_mapping, definitions = schema_generator.generate_definitions(inputs=inputs)
    for item_def in cast(dict[str, dict[str, Any]], definitions).values():
        if "description" in item_def:
            item_description = cast(str, item_def["description"]).split("\f")[0]
            item_def["description"] = item_description
    # definitions: dict[DefsRef, dict[str, Any]]
    # but mypy complains about general str in other places that are not declared as
    # DefsRef, although DefsRef is just str:
    # DefsRef = NewType('DefsRef', str)
    # So, a cast to simplify the types here
    return field_mapping, cast(dict[str, dict[str, Any]], definitions)
