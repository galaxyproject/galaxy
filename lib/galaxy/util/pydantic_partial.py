"""Helpers for deriving Pydantic models whose fields are all optional.

These live in their own module rather than in galaxy.util.config_templates
because they are generic Pydantic utilities with no relation to configuration
templates, and are used from galaxy.schema.schema, which is imported by
galaxy.model. Keeping them here means that import does not drag in
config_templates' own dependencies (requests, yaml, boltons, tool_util_models).
"""

from collections.abc import (
    Callable,
    Iterable,
)
from typing import (
    Annotated,
    TypeVar,
)

from pydantic import (
    BaseModel,
    create_model,
)
from pydantic.fields import FieldInfo

M = TypeVar("M", bound=BaseModel)


# Implementation copied from https://github.com/pydantic/pydantic/issues/12329#issuecomment-3382159312
def _make_field_optional(field_info: FieldInfo):
    """Returns the field's definition to be used in a `create_model()` call to make the field optional."""
    annotation = field_info.annotation
    assert annotation is not None
    if field_info.is_required():
        return Annotated[annotation | None, field_info], None
    else:
        return Annotated[annotation, field_info]


def make_model_with_all_fields_optional(model: type[M], fields=None) -> type[M]:
    """Returns a new Pydantic model based on `model`, but with all fields optional."""
    if fields is None:
        fields = model.model_fields.items()
    return create_model(
        model.__name__,
        __doc__=model.__doc__,
        __base__=model,
        **{field_name: _make_field_optional(field_info) for field_name, field_info in fields},
    )


# TODO: This is a workaround to make all fields optional.
#       It should be removed when Python/pydantic supports this feature natively.
# https://github.com/pydantic/pydantic/issues/1673
def partial_model(include: list[str] | None = None, exclude: list[str] | None = None) -> Callable[[type[M]], type[M]]:
    """Decorator to make all model fields optional"""

    if exclude is None:
        exclude = []

    def decorator(model: type[M]) -> type[M]:
        if include is None:
            fields: Iterable[tuple[str, FieldInfo]] = model.model_fields.items()
        else:
            fields = ((k, v) for k, v in model.model_fields.items() if k in include)

        if exclude is not None:
            fields = ((k, v) for k, v in fields if k not in exclude)

        return make_model_with_all_fields_optional(model, fields)

    return decorator
