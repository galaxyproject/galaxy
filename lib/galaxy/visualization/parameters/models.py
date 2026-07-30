"""Typed parameter models for visualization plugins.

Analogous to ``galaxy.tool_util_models.parameters`` but deliberately smaller:
visualizations declare a flat set of ``settings`` inputs plus at most one
top-level ``tracks`` repeat, and there is a single state representation (the
embed config authored in a Page/Report). Dataset-id decoding happens outside
this model, in the binding layer.

Naming mirrors the tool parameter models so anyone familiar with those feels at
home here. As in ``tool_util_models._types``, the typing system is used to build
runtime pydantic models rather than to statically type-check this module, so a
few dynamic type constructions are funnelled through the helpers below.
"""

from typing import (
    Annotated,
    Any,
    cast,
    List,
    Literal,
    Optional,
    Union,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    create_model,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
)

VISUALIZATION_REQUEST_MODEL_NAME = "VisualizationRequest"
ExtraT = Literal["allow", "forbid", "ignore"]

# (annotation, default) pair consumed by pydantic.create_model.
FieldDefinition = tuple


def _optional(type_: Any) -> Any:
    return cast(type, Optional[type_])


def _union(types: List[Any]) -> Any:
    result = types[0]
    for type_ in types[1:]:
        result = cast(type, Union[result, type_])
    return result


def _list(type_: Any) -> Any:
    return cast(type, List[type_])


def _literal(values: List[Any]) -> Any:
    return cast(type, Literal[tuple(values)])


class LabelValue(BaseModel):
    label: str
    value: str


class BaseVisualizationParameterModel(BaseModel):
    """Shared declaration fields for every visualization input."""

    name: str
    label: Optional[str] = None
    help: Optional[str] = None
    optional: bool = False

    @property
    def requires_value(self) -> bool:
        """Declaration intent: an input has no default and is not optional.

        Retained as metadata for a future strict mode / JSON-Schema ``required``
        export. The runtime request model does not enforce presence: an embed
        config is a partial override where the client form fills defaults and
        dataset binding is validated in a separate layer.
        """
        return not self.optional and getattr(self, "value", None) is None

    def _finalize(self, base_type: Any) -> FieldDefinition:
        # Presence is not enforced (see requires_value); validate type and choices
        # of whatever the author provided.
        return (_optional(base_type), getattr(self, "value", None))

    def field_definition(self) -> FieldDefinition:
        raise NotImplementedError


class BooleanParameterModel(BaseVisualizationParameterModel):
    parameter_type: Literal["gx_boolean"] = "gx_boolean"
    value: Optional[bool] = None

    def field_definition(self) -> FieldDefinition:
        return self._finalize(StrictBool)


class ColorParameterModel(BaseVisualizationParameterModel):
    parameter_type: Literal["gx_color"] = "gx_color"
    value: Optional[str] = None

    def field_definition(self) -> FieldDefinition:
        return self._finalize(StrictStr)


class IntegerParameterModel(BaseVisualizationParameterModel):
    parameter_type: Literal["gx_integer"] = "gx_integer"
    value: Optional[int] = None
    min: Optional[int] = None
    max: Optional[int] = None

    def field_definition(self) -> FieldDefinition:
        base: Any = StrictInt
        if self.min is not None or self.max is not None:
            base = Annotated[StrictInt, Field(ge=self.min, le=self.max)]
        return self._finalize(base)


class FloatParameterModel(BaseVisualizationParameterModel):
    parameter_type: Literal["gx_float"] = "gx_float"
    value: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None

    def field_definition(self) -> FieldDefinition:
        base: Any = _union([StrictFloat, StrictInt])
        if self.min is not None or self.max is not None:
            base = Annotated[base, Field(ge=self.min, le=self.max)]
        return self._finalize(base)


class TextParameterModel(BaseVisualizationParameterModel):
    parameter_type: Literal["gx_text"] = "gx_text"
    value: Optional[str] = None
    area: bool = False

    def field_definition(self) -> FieldDefinition:
        return self._finalize(StrictStr)


class SelectParameterModel(BaseVisualizationParameterModel):
    parameter_type: Literal["gx_select"] = "gx_select"
    value: Optional[str] = None
    options: List[LabelValue] = []
    multiple: bool = False

    def field_definition(self) -> FieldDefinition:
        base: Any = _literal([o.value for o in self.options]) if self.options else StrictStr
        if self.multiple:
            base = _list(base)
        return self._finalize(base)


class DataParameterModel(BaseVisualizationParameterModel):
    parameter_type: Literal["gx_data"] = "gx_data"
    extension: Optional[str] = None
    value: Optional[str] = None

    def field_definition(self) -> FieldDefinition:
        return self._finalize(StrictStr)


class DataColumnParameterModel(BaseVisualizationParameterModel):
    parameter_type: Literal["gx_data_column"] = "gx_data_column"
    is_number: bool = False
    value: Optional[Any] = None

    def field_definition(self) -> FieldDefinition:
        base: Any = StrictInt if self.is_number else StrictStr
        return self._finalize(base)


class DataJsonParameterModel(BaseVisualizationParameterModel):
    """Dynamic select whose options are fetched from a URL; values unchecked."""

    parameter_type: Literal["gx_data_json"] = "gx_data_json"
    url: Optional[str] = None
    value: Optional[str] = None

    def field_definition(self) -> FieldDefinition:
        return self._finalize(StrictStr)


class DataTableParameterModel(BaseVisualizationParameterModel):
    """Dynamic select whose options come from a Galaxy data table; values unchecked."""

    parameter_type: Literal["gx_data_table"] = "gx_data_table"
    tables: List[str] = []
    value: Optional[str] = None

    def field_definition(self) -> FieldDefinition:
        return self._finalize(StrictStr)


class VisualizationWhen(BaseModel):
    value: Any
    inputs: List["VisualizationParameterT"] = []


class ConditionalParameterModel(BaseVisualizationParameterModel):
    parameter_type: Literal["gx_conditional"] = "gx_conditional"
    test_parameter: Union[BooleanParameterModel, SelectParameterModel]
    whens: List[VisualizationWhen] = []

    def field_definition(self) -> FieldDefinition:
        test = self.test_parameter
        discriminate = isinstance(test, SelectParameterModel)
        case_models = []
        for when in self.whens:
            fields: dict = {test.name: (_literal([when.value]), ...)}
            for parameter in when.inputs:
                fields[parameter.name] = parameter.field_definition()
            case_models.append(create_model(f"{self.name}_{when.value}", **fields))
        if not case_models:
            return (_optional(dict), None)
        if len(case_models) == 1:
            return (_optional(case_models[0]), None)
        union = _union(case_models)
        if discriminate:
            union = Annotated[union, Field(discriminator=test.name)]
        return (_optional(union), None)


VisualizationParameterT = Annotated[
    Union[
        BooleanParameterModel,
        ColorParameterModel,
        IntegerParameterModel,
        FloatParameterModel,
        TextParameterModel,
        SelectParameterModel,
        DataParameterModel,
        DataColumnParameterModel,
        DataJsonParameterModel,
        DataTableParameterModel,
        ConditionalParameterModel,
    ],
    Field(discriminator="parameter_type"),
]


class VisualizationParameterBundleModel(BaseModel):
    """The parsed parameter tree: a flat ``settings`` list and the ``tracks`` repeat."""

    settings: List[VisualizationParameterT] = []
    tracks: List[VisualizationParameterT] = []


VisualizationWhen.model_rebuild()
ConditionalParameterModel.model_rebuild()
VisualizationParameterBundleModel.model_rebuild()


def _create_model(*args, **kwd) -> type[BaseModel]:
    # Loosely typed wrapper: dynamic field definitions do not match create_model's
    # typed overloads, so route them through here (mirrors create_model_strict in
    # tool_util_models.parameters).
    return create_model(*args, **kwd)


def _model_from_parameters(parameters: List[Any], name: str, extra: ExtraT) -> type[BaseModel]:
    fields: dict[str, tuple] = {parameter.name: parameter.field_definition() for parameter in parameters}
    return _create_model(name, __config__=ConfigDict(extra=extra), **fields)


def create_request_model(
    bundle: VisualizationParameterBundleModel,
    name: str = VISUALIZATION_REQUEST_MODEL_NAME,
) -> type[BaseModel]:
    """Build the dynamic pydantic model that validates an embed config.

    ``settings`` is a closed object (unknown keys are rejected); ``tracks`` is a
    list of track objects that carry binding metadata alongside declared inputs,
    so they stay open. Top-level meta and binding keys (``visualization_name``,
    ``dataset_id``, ``height``, ...) are allowed and validated elsewhere.
    """
    settings_model = _model_from_parameters(bundle.settings, f"{name}Settings", "forbid")
    track_model = _model_from_parameters(bundle.tracks, f"{name}Track", "allow")
    fields: dict[str, tuple] = {
        "settings": (_optional(settings_model), None),
        "tracks": (_list(track_model), []),
    }
    return _create_model(name, __config__=ConfigDict(extra="allow"), **fields)


def visualization_request_json_schema(
    bundle: VisualizationParameterBundleModel,
    name: str = VISUALIZATION_REQUEST_MODEL_NAME,
) -> dict:
    """Return a JSON Schema for an embed config, for client-side validation."""
    return create_request_model(bundle, name).model_json_schema()
