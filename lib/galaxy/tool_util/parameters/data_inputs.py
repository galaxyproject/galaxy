"""Summaries of a tool's dataset inputs, derived from its parameter models."""

from collections.abc import (
    Iterable,
    Iterator,
)

from pydantic import (
    BaseModel,
    Field,
)

from galaxy.tool_util_models.parameters import (
    ConditionalParameterModel,
    DataParameterModel,
    RepeatParameterModel,
    SectionParameterModel,
    ToolParameterT,
)


class ToolDataInput(BaseModel):
    name: str | None = Field(
        ...,
        description="The `|`-joined path of the data parameter, usable as a tool form URL parameter; inputs in a "
        "repeat use its first element (`queries_0|input`). Null when the tool form cannot prefill it (an input in a "
        "conditional case that is not the default one).",
    )
    extensions: list[str] = Field(
        ...,
        description="Datatype extensions the input accepts; `data` accepts any datatype.",
    )
    multiple: bool = Field(..., description="Whether the input accepts several datasets.")


def data_inputs_for_parameters(parameters: Iterable[ToolParameterT]) -> list[ToolDataInput]:
    """List every ``data`` parameter of a tool, in input order."""
    return list(_walk(parameters, ""))


def _walk(parameters: Iterable[ToolParameterT], prefix: str | None) -> Iterator[ToolDataInput]:
    for parameter in parameters:
        name = None if prefix is None else f"{prefix}{parameter.name}"
        if isinstance(parameter, DataParameterModel):
            yield ToolDataInput(name=name, extensions=list(parameter.extensions), multiple=parameter.multiple)
        elif isinstance(parameter, SectionParameterModel):
            yield from _walk(parameter.parameters, None if name is None else f"{name}|")
        elif isinstance(parameter, RepeatParameterModel):
            # The build API creates repeat element N for incoming ``<name>_N|...`` keys.
            yield from _walk(parameter.parameters, None if name is None else f"{name}_0|")
        elif isinstance(parameter, ConditionalParameterModel):
            # The build API only fills the default case when the test parameter is absent.
            for when in parameter.whens:
                case_prefix = f"{name}|" if name is not None and when.is_default_when else None
                yield from _walk(when.parameters, case_prefix)
