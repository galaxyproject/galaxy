import sys
from typing import (
    Any,
    Generic,
    Tuple,
    Type,
    TypeVar,
)

from pydantic import BaseModel
from pydantic.json_schema import GenerateJsonSchema
from typing_extensions import override

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


class PatchGenericPickle:
    """A mixin that allows generic pydantic models to be serialized and deserialized with pickle.

    Notes
    ----
    In general, pickle shouldn't be encouraged as a means of serialization since there are better,
    safer options. In some cases e.g. Streamlit's `@st.cache_data there's no getting around
    needing to use pickle.

    As of Pydantic 2.7, generics don't properly work with pickle. The core issue is the following
    1. For each specialized generic, pydantic creates a new subclass at runtime. This class
       has a `__qualname__` that contains the type var argument e.g. `"MyGeneric[str]"` for a
       `class MyGeneric(BaseModel, Generic[T])`.
    2. Pickle attempts to find a symbol with the value of `__qualname__` in the module where the
       class was defined, which fails since Pydantic defines that class dynamically at runtime.
       Pydantic does attempt to register these dynamic classes but currently only for classes
       defined at the top-level of the interpreter.

    See Also
    --------
    - https://github.com/pydantic/pydantic/issues/9390
    """

    @classmethod
    @override
    def __init_subclass__(cls, **kwargs):
        # Note: we're still in __init_subclass__, not yet in __pydantic_init_subclass__
        #  not all model_fields are available at this point.
        super().__init_subclass__(**kwargs)

        if not issubclass(cls, BaseModel):
            raise TypeError("PatchGenericPickle can only be used with subclasses of pydantic.BaseModel")
        if not issubclass(cls, Generic):  # type: ignore [arg-type]
            raise TypeError("PatchGenericPickle can only be used with Generic models")

        qualname = cls.__qualname__
        declaring_module = sys.modules[cls.__module__]
        if qualname not in declaring_module.__dict__:
            # This should work in all cases, but we might need to make this check and update more
            # involved e.g. see pydantic._internal._generics.create_generic_submodel
            declaring_module.__dict__[qualname] = cls
