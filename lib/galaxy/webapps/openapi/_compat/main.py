import sys
from typing import (
    Any,
    Union,
)

from fastapi._compat import (
    may_v1,
    v2,
)
from fastapi._compat.model_field import ModelField
from fastapi._compat.shared import PYDANTIC_V2
from fastapi.types import ModelNameMap
from typing_extensions import Literal

from .v2 import (
    GenerateJsonSchema as GenerateJsonSchema,
    get_definitions as v2_get_definitions,
)


def get_definitions(
    *,
    fields: list[ModelField],
    model_name_map: ModelNameMap,
    separate_input_output_schemas: bool = True,
    schema_generator: Union[GenerateJsonSchema, None] = None,
) -> tuple[
    dict[tuple[ModelField, Literal["validation", "serialization"]], may_v1.JsonSchemaValue],
    dict[str, dict[str, Any]],
]:
    if sys.version_info < (3, 14):
        v1_fields = [field for field in fields if isinstance(field, may_v1.ModelField)]
        v1_field_maps, v1_definitions = may_v1.get_definitions(
            fields=v1_fields,
            model_name_map=model_name_map,
            separate_input_output_schemas=separate_input_output_schemas,
        )
        if not PYDANTIC_V2:
            return v1_field_maps, v1_definitions
        else:
            v2_fields = [field for field in fields if isinstance(field, v2.ModelField)]
            v2_field_maps, v2_definitions = v2_get_definitions(
                fields=v2_fields,
                model_name_map=model_name_map,
                separate_input_output_schemas=separate_input_output_schemas,
                schema_generator=schema_generator,
            )
            all_definitions = {**v1_definitions, **v2_definitions}
            all_field_maps = {**v1_field_maps, **v2_field_maps}
            return all_field_maps, all_definitions

    # Pydantic v1 is not supported since Python 3.14
    else:
        v2_fields = [field for field in fields if isinstance(field, v2.ModelField)]
        v2_field_maps, v2_definitions = v2_get_definitions(
            fields=v2_fields,
            model_name_map=model_name_map,
            separate_input_output_schemas=separate_input_output_schemas,
            schema_generator=schema_generator,
        )
        return v2_field_maps, v2_definitions
