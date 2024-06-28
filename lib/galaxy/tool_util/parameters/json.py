import json
from typing import (
    Any,
    Dict,
)

from pydantic.json_schema import GenerateJsonSchema
from typing_extensions import Literal

MODE = Literal["validation", "serialization"]
DEFAULT_JSON_SCHEMA_MODE: MODE = "validation"


class CustomGenerateJsonSchema(GenerateJsonSchema):

    def generate(self, schema, mode: MODE = DEFAULT_JSON_SCHEMA_MODE):
        json_schema = super().generate(schema, mode=mode)
        json_schema["$schema"] = self.schema_dialect
        return json_schema


def to_json_schema(model, mode: MODE = DEFAULT_JSON_SCHEMA_MODE) -> Dict[str, Any]:
    return model.model_json_schema(schema_generator=CustomGenerateJsonSchema, mode=mode)


def to_json_schema_string(model, mode: MODE = DEFAULT_JSON_SCHEMA_MODE) -> str:
    return json.dumps(to_json_schema(model, mode=mode), indent=4)
