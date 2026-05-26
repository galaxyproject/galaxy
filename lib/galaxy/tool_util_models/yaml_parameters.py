"""Narrow YAML-facing tool parameter models.

`UserToolSource` and `YamlToolSource` use these for their `inputs` field instead
of the full internal Galaxy XML metamodel union. The YAML layer is purely an
authoring/publication surface: it validates what users may write in YAML tools and
rejects XML-only fields and unsupported parameter types via ``extra="forbid"``.

Every model exposes ``to_internal()`` returning the matching internal
``GalaxyParameterT`` instance so callers that need the internal metamodel (e.g.
round-trip tests) can construct it directly without re-parsing through
``YamlToolSource``. The primary production path still builds internal models via
``input_models_for_tool_source`` from the raw validated dict, so ``to_internal()``
is not load-bearing for execution today.
"""

from typing import (
    List,
    Optional,
    Union,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    RootModel,
)
from typing_extensions import (
    Annotated,
    Literal,
)

from .parameter_validators import (
    EmptyFieldParameterValidatorModel,
    InRangeParameterValidatorModel,
    LengthParameterValidatorModel,
    NoOptionsParameterValidatorModel,
    RegexParameterValidatorModel,
)
from .parameters import (
    BooleanParameterModel,
    ColorParameterModel,
    cond_test_parameter_default_value,
    ConditionalParameterModel,
    ConditionalWhen,
    DataCollectionParameterModel,
    DataParameterModel,
    FloatParameterModel,
    GalaxyParameterT,
    IntegerParameterModel,
    LabelValue,
    RepeatParameterModel,
    SectionParameterModel,
    SelectParameterModel,
    TextParameterModel,
)


class YamlLabelValue(BaseModel):
    """YAML-friendly option model — ``selected`` defaults to ``False``."""

    label: str
    value: str
    selected: bool = False

    def to_internal(self) -> LabelValue:
        return LabelValue(label=self.label, value=self.value, selected=self.selected)


# Narrow validator unions — drops XML-only validators like Expression.
YamlTextValidators = Union[
    LengthParameterValidatorModel,
    RegexParameterValidatorModel,
    EmptyFieldParameterValidatorModel,
]
YamlNumberValidators = Union[InRangeParameterValidatorModel,]
YamlSelectValidators = Union[NoOptionsParameterValidatorModel,]


class _YamlParamBase(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str
    label: Optional[str] = None
    help: Optional[str] = None
    optional: bool = False


def _common_internal_kwargs(yaml_param: "_YamlParamBase") -> dict:
    kwargs: dict = {"name": yaml_param.name, "optional": yaml_param.optional}
    if yaml_param.label is not None:
        kwargs["label"] = yaml_param.label
    if yaml_param.help is not None:
        kwargs["help"] = yaml_param.help
    return kwargs


class YamlBooleanParameter(_YamlParamBase):
    type: Literal["boolean"]
    value: Optional[bool] = False

    def to_internal(self) -> BooleanParameterModel:
        return BooleanParameterModel(type="boolean", value=self.value, **_common_internal_kwargs(self))


class YamlIntegerParameter(_YamlParamBase):
    type: Literal["integer"]
    value: Optional[int] = None
    min: Optional[int] = None
    max: Optional[int] = None
    validators: List[YamlNumberValidators] = []

    def to_internal(self) -> IntegerParameterModel:
        return IntegerParameterModel(
            type="integer",
            value=self.value,
            min=self.min,
            max=self.max,
            validators=list(self.validators),
            **_common_internal_kwargs(self),
        )


class YamlFloatParameter(_YamlParamBase):
    type: Literal["float"]
    value: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    validators: List[YamlNumberValidators] = []

    def to_internal(self) -> FloatParameterModel:
        return FloatParameterModel(
            type="float",
            value=self.value,
            min=self.min,
            max=self.max,
            validators=list(self.validators),
            **_common_internal_kwargs(self),
        )


class YamlTextParameter(_YamlParamBase):
    type: Literal["text"]
    value: Optional[str] = Field(default=None, alias="value")
    area: bool = False
    validators: List[YamlTextValidators] = []

    def to_internal(self) -> TextParameterModel:
        return TextParameterModel(
            type="text",
            default_value=self.value,
            area=self.area,
            validators=list(self.validators),
            **_common_internal_kwargs(self),
        )


class YamlSelectParameter(_YamlParamBase):
    type: Literal["select"]
    options: Annotated[List[YamlLabelValue], Field(min_length=1)]
    multiple: bool = False
    validators: List[YamlSelectValidators] = []

    def to_internal(self) -> SelectParameterModel:
        return SelectParameterModel(
            type="select",
            options=[o.to_internal() for o in self.options],
            multiple=self.multiple,
            validators=list(self.validators),
            **_common_internal_kwargs(self),
        )


class YamlColorParameter(_YamlParamBase):
    type: Literal["color"]
    value: Optional[str] = None

    def to_internal(self) -> ColorParameterModel:
        return ColorParameterModel(type="color", value=self.value, **_common_internal_kwargs(self))


def _split_format(v):
    # Accept the XML-style comma-separated string form (`format: "txt,tabular"`)
    # as well as a list. Internal `DataParameterModel.extensions` is always a list.
    if isinstance(v, str):
        return [ext.strip().lower() for ext in v.split(",") if ext.strip()]
    return v


class YamlDataParameter(_YamlParamBase):
    type: Literal["data"]
    format: List[str] = ["data"]
    multiple: bool = False
    min: Optional[int] = None
    max: Optional[int] = None

    @field_validator("format", mode="before")
    @classmethod
    def _coerce_format(cls, v):
        return _split_format(v)

    def to_internal(self) -> DataParameterModel:
        return DataParameterModel(
            type="data",
            extensions=list(self.format),
            multiple=self.multiple,
            min=self.min,
            max=self.max,
            **_common_internal_kwargs(self),
        )


class YamlDataCollectionParameter(_YamlParamBase):
    type: Literal["data_collection"]
    collection_type: Optional[str] = None
    format: List[str] = ["data"]

    @field_validator("format", mode="before")
    @classmethod
    def _coerce_format(cls, v):
        return _split_format(v)

    def to_internal(self) -> DataCollectionParameterModel:
        return DataCollectionParameterModel(
            type="data_collection",
            collection_type=self.collection_type,
            extensions=list(self.format),
            value=None,
            **_common_internal_kwargs(self),
        )


YamlConditionalTestParameter = Annotated[Union[YamlBooleanParameter, YamlSelectParameter], Field(discriminator="type")]


class YamlConditionalWhen(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    discriminator: Union[bool, str]
    parameters: List["YamlGalaxyToolParameter"] = []


class YamlConditionalParameter(_YamlParamBase):
    type: Literal["conditional"]
    test_parameter: YamlConditionalTestParameter
    whens: Annotated[List[YamlConditionalWhen], Field(min_length=1)]

    def to_internal(self) -> ConditionalParameterModel:
        internal_test = self.test_parameter.to_internal()
        default_value = cond_test_parameter_default_value(internal_test)
        internal_whens: List[ConditionalWhen] = []
        for when in self.whens:
            internal_params = [p.root.to_internal() for p in when.parameters]
            internal_whens.append(
                ConditionalWhen(
                    discriminator=when.discriminator,
                    parameters=internal_params,
                    is_default_when=when.discriminator == default_value,
                )
            )
        return ConditionalParameterModel(
            type="conditional",
            test_parameter=internal_test,
            whens=internal_whens,
            **_common_internal_kwargs(self),
        )


class YamlRepeatParameter(_YamlParamBase):
    type: Literal["repeat"]
    parameters: List["YamlGalaxyToolParameter"] = []
    min: Optional[int] = None
    max: Optional[int] = None

    def to_internal(self) -> RepeatParameterModel:
        return RepeatParameterModel(
            type="repeat",
            parameters=[p.root.to_internal() for p in self.parameters],
            min=self.min,
            max=self.max,
            **_common_internal_kwargs(self),
        )


class YamlSectionParameter(_YamlParamBase):
    type: Literal["section"]
    parameters: List["YamlGalaxyToolParameter"] = []

    def to_internal(self) -> SectionParameterModel:
        return SectionParameterModel(
            type="section",
            parameters=[p.root.to_internal() for p in self.parameters],
            **_common_internal_kwargs(self),
        )


YamlGalaxyParameterT = Union[
    YamlBooleanParameter,
    YamlIntegerParameter,
    YamlFloatParameter,
    YamlTextParameter,
    YamlSelectParameter,
    YamlColorParameter,
    YamlDataParameter,
    YamlDataCollectionParameter,
    YamlConditionalParameter,
    YamlRepeatParameter,
    YamlSectionParameter,
]


class YamlGalaxyToolParameter(RootModel):
    root: Annotated[YamlGalaxyParameterT, Field(discriminator="type")]

    def to_internal(self) -> GalaxyParameterT:
        return self.root.to_internal()


YamlConditionalWhen.model_rebuild()
YamlConditionalParameter.model_rebuild()
YamlRepeatParameter.model_rebuild()
YamlSectionParameter.model_rebuild()
YamlGalaxyToolParameter.model_rebuild()
