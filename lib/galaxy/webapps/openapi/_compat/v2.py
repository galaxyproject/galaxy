from typing import (
    Any,
    cast,
    Union,
)

from fastapi._compat import ModelField
from fastapi.types import ModelNameMap
from pydantic.json_schema import (
    GenerateJsonSchema as GenerateJsonSchema,
    JsonSchemaValue as JsonSchemaValue,
)
from typing_extensions import Literal


def get_definitions(
    *,
    fields: list[ModelField],
    schema_generator: GenerateJsonSchema,
    model_name_map: ModelNameMap,
    separate_input_output_schemas: bool = True,
) -> tuple[
    dict[tuple[ModelField, Literal["validation", "serialization"]], JsonSchemaValue],
    dict[str, dict[str, Any]],
]:
    override_mode: Union[Literal["validation"], None] = None if separate_input_output_schemas else "validation"
    inputs = [(field, override_mode or field.mode, field._type_adapter.core_schema) for field in fields]
    field_mapping, definitions = schema_generator.generate_definitions(inputs=inputs)
    for item_def in cast(dict[str, dict[str, Any]], definitions).values():
        if "description" in item_def:
            item_description = cast(str, item_def["description"]).split("\f")[0]
            item_def["description"] = item_description
    return field_mapping, definitions  # type: ignore[return-value]
