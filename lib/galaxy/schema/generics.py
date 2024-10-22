from typing import (
    Any,
    Tuple,
    Type,
    TypeVar,
)

from pydantic import BaseModel
from pydantic.json_schema import GenerateJsonSchema

from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    EncodedDatabaseIdField,
)

DatabaseIdT = TypeVar("DatabaseIdT")

ref_to_name = {}


class GenericModel(BaseModel):
    @classmethod
    def model_parametrized_name(cls, params: Tuple[Type[Any], ...]) -> str:
        suffix = cls.__determine_suffix__(params)
        class_name = cls.__name__.split("Generic", 1)[-1]
        return f"{class_name}{suffix}"

    @classmethod
    def __get_pydantic_core_schema__(cls, *args, **kwargs):
        result = super().__get_pydantic_core_schema__(*args, **kwargs)
        ref_to_name[result["ref"]] = cls.__name__
        return result

    @classmethod
    def __determine_suffix__(cls, params: Tuple[Type[Any], ...]) -> str:
        suffix = "Incoming"
        if params[0] is EncodedDatabaseIdField:
            suffix = "Response"
        elif params[0] is DecodedDatabaseIdField:
            suffix = "Request"
        return suffix


class CustomJsonSchema(GenerateJsonSchema):
    def get_defs_ref(self, core_mode_ref):
        full_def = super().get_defs_ref(core_mode_ref)
        choices = self._prioritized_defsref_choices[full_def]
        ref, mode = core_mode_ref
        if ref in ref_to_name:
            for i, choice in enumerate(choices):
                choices[i] = choice.replace(choices[0], ref_to_name[ref])  # type: ignore[call-overload]
        return full_def
