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

    name: Annotated[
        str,
        Field(description="Identifier used to read this input from `shell_command` and other expressions."),
    ]
    label: Annotated[
        Optional[str],
        Field(description="Human-readable prompt shown beside the input on the tool form."),
    ] = None
    help: Annotated[
        Optional[str],
        Field(description="Additional guidance shown on the tool form to help users choose a value."),
    ] = None
    optional: Annotated[
        bool,
        Field(description="Set true when the command can run without the user supplying this input."),
    ] = False


def _common_internal_kwargs(yaml_param: "_YamlParamBase") -> dict:
    kwargs: dict = {"name": yaml_param.name, "optional": yaml_param.optional}
    if yaml_param.label is not None:
        kwargs["label"] = yaml_param.label
    if yaml_param.help is not None:
        kwargs["help"] = yaml_param.help
    return kwargs


class YamlBooleanParameter(_YamlParamBase):
    """A true-or-false input."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "include_header",
                    "type": "boolean",
                    "label": "Include a header line",
                    "value": True,
                }
            ],
            "x-shell-command": 'include_header="$(inputs.include_header)"',
        }
    )

    type: Annotated[
        Literal["boolean"],
        Field(description="Presents a true-or-false choice and supplies the selected Boolean value to expressions."),
    ]
    value: Annotated[
        Optional[bool],
        Field(description="Initial choice shown when the user first opens the tool form."),
    ] = False

    def to_internal(self) -> BooleanParameterModel:
        return BooleanParameterModel(type="boolean", value=self.value, **_common_internal_kwargs(self))


class YamlIntegerParameter(_YamlParamBase):
    """A whole-number input with optional bounds and validators."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "num_lines",
                    "type": "integer",
                    "label": "Number of lines",
                    "value": 10,
                    "min": 1,
                    "max": 1000,
                }
            ],
            "x-shell-command": 'num_lines="$(inputs.num_lines)"',
        }
    )

    type: Annotated[
        Literal["integer"],
        Field(description="Accepts a whole number and supplies it as a numeric value to expressions."),
    ]
    value: Annotated[
        Optional[int],
        Field(description="Number prefilled when the user first opens the tool form."),
    ] = None
    min: Annotated[
        Optional[int],
        Field(description="Rejects submitted values smaller than this inclusive lower bound."),
    ] = None
    max: Annotated[
        Optional[int],
        Field(description="Rejects submitted values larger than this inclusive upper bound."),
    ] = None
    validators: Annotated[
        List[YamlNumberValidators],
        Field(description="Additional validation rules; supports `in_range`."),
    ] = []

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
    """A numeric input with optional bounds and validators."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "threshold",
                    "type": "float",
                    "label": "Score threshold",
                    "value": 0.5,
                    "min": 0.0,
                    "max": 1.0,
                }
            ],
            "x-shell-command": 'threshold="$(inputs.threshold)"',
        }
    )

    type: Annotated[
        Literal["float"],
        Field(description="Accepts a number, including decimal values, and supplies it to expressions."),
    ]
    value: Annotated[
        Optional[float],
        Field(description="Number prefilled when the user first opens the tool form."),
    ] = None
    min: Annotated[
        Optional[float],
        Field(description="Rejects submitted values smaller than this inclusive lower bound."),
    ] = None
    max: Annotated[
        Optional[float],
        Field(description="Rejects submitted values larger than this inclusive upper bound."),
    ] = None
    validators: Annotated[
        List[YamlNumberValidators],
        Field(description="Additional validation rules; supports `in_range`."),
    ] = []

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
    """A single-line or multiline text input."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "motif",
                    "type": "text",
                    "label": "Sequence motif",
                    "value": "ACGT",
                    "area": False,
                }
            ],
            "x-shell-command": 'motif="$(inputs.motif)"',
        }
    )

    type: Annotated[
        Literal["text"],
        Field(description="Accepts user-entered text and supplies the resulting string to expressions."),
    ]
    value: Optional[str] = Field(
        default=None,
        alias="value",
        description="Text prefilled when the user first opens the tool form.",
    )
    area: Annotated[
        bool,
        Field(description="Set true to use a multiline editor instead of a single-line text box."),
    ] = False
    validators: Annotated[
        List[YamlTextValidators],
        Field(description="Additional validation rules; supports `length`, `regex`, and `empty_field`."),
    ] = []

    def to_internal(self) -> TextParameterModel:
        return TextParameterModel(
            type="text",
            default_value=self.value,
            area=self.area,
            validators=list(self.validators),
            **_common_internal_kwargs(self),
        )


class YamlSelectParameter(_YamlParamBase):
    """A choice from a fixed list of options."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "mode",
                    "type": "select",
                    "label": "Search mode",
                    "options": [
                        {"label": "Fast", "value": "fast", "selected": True},
                        {"label": "Sensitive", "value": "sensitive", "selected": False},
                    ],
                }
            ],
            "x-shell-command": 'mode="$(inputs.mode)"',
        }
    )

    type: Annotated[
        Literal["select"],
        Field(description="Lets the user choose from the declared `options` and supplies the selected value."),
    ]
    options: Annotated[
        List[YamlLabelValue],
        Field(min_length=1, description="Choices presented on the tool form, each with a display label and value."),
    ]
    multiple: Annotated[
        bool,
        Field(description="Set true to let the user select and supply several option values instead of one."),
    ] = False
    validators: Annotated[
        List[YamlSelectValidators],
        Field(description="Additional validation rules; supports `no_options`."),
    ] = []

    def to_internal(self) -> SelectParameterModel:
        return SelectParameterModel(
            type="select",
            options=[o.to_internal() for o in self.options],
            multiple=self.multiple,
            validators=list(self.validators),
            **_common_internal_kwargs(self),
        )


class YamlColorParameter(_YamlParamBase):
    """A color-picker input."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "plot_color",
                    "type": "color",
                    "label": "Plot color",
                    "value": "#3366cc",
                }
            ],
            "x-shell-command": 'plot_color="$(inputs.plot_color)"',
        }
    )

    type: Annotated[
        Literal["color"],
        Field(description="Presents a color picker and supplies the selected hexadecimal color string."),
    ]
    value: Annotated[
        Optional[str],
        Field(description="Color initially selected in the picker, written in hexadecimal notation."),
    ] = None

    def to_internal(self) -> ColorParameterModel:
        return ColorParameterModel(type="color", value=self.value, **_common_internal_kwargs(self))


def _split_format(v):
    # Accept the XML-style comma-separated string form (`format: "txt,tabular"`)
    # as well as a list. Internal `DataParameterModel.extensions` is always a list.
    if isinstance(v, str):
        return [ext.strip().lower() for ext in v.split(",") if ext.strip()]
    return v


class YamlDataParameter(_YamlParamBase):
    """One dataset, or a list of datasets when ``multiple`` is true."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "input_file",
                    "type": "data",
                    "label": "Input file",
                    "format": ["txt", "tabular"],
                }
            ],
            "x-shell-command": "input_file='$(inputs.input_file.path)'",
        }
    )

    type: Annotated[
        Literal["data"],
        Field(description="Lets the user select history datasets and exposes their paths and metadata to expressions."),
    ]
    format: Annotated[
        List[str],
        Field(description="Limits selectable datasets to these Galaxy datatype extensions."),
    ] = ["data"]
    multiple: Annotated[
        bool,
        Field(description="Set true to accept several datasets (a list) for this input instead of one."),
    ] = False
    # NOTE: `min`/`max` (the min/max number of selected datasets) are intentionally
    # NOT exposed here. They only have meaning for a `multiple` input and the runtime
    # rejects them on a single one; in practice authors (and LLMs) reach for `min: 1`
    # to mean "required" -- which a data input already is -- and then the tool fails
    # at build time. Omitting the fields means such a tool is rejected up front with a
    # clear `extra_forbidden` error instead. The internal model still supports them
    # for XML tools.

    @field_validator("format", mode="before")
    @classmethod
    def _coerce_format(cls, v):
        return _split_format(v)

    def to_internal(self) -> DataParameterModel:
        return DataParameterModel(
            type="data",
            extensions=list(self.format),
            multiple=self.multiple,
            **_common_internal_kwargs(self),
        )


class YamlDataCollectionParameter(_YamlParamBase):
    """A dataset collection input."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "reads",
                    "type": "data_collection",
                    "label": "Paired reads",
                    "collection_type": "paired",
                    "format": ["fastqsanger"],
                }
            ],
            "x-shell-command": """forward='$(inputs.reads.elements.forward.path)'
reverse='$(inputs.reads.elements.reverse.path)'""",
        }
    )

    type: Annotated[
        Literal["data_collection"],
        Field(description="Lets the user select a history collection and exposes its elements to expressions."),
    ]
    collection_type: Annotated[
        Optional[str],
        Field(description="Limits selectable collections to this structure, such as `list` or `paired`."),
    ] = None
    format: Annotated[
        List[str],
        Field(description="Requires every selectable collection element to use one of these datatype extensions."),
    ] = ["data"]

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
    """A control input that selects which nested inputs are displayed and supplied to the command."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "search_options",
                    "type": "conditional",
                    "test_parameter": {
                        "name": "mode",
                        "type": "select",
                        "label": "Search mode",
                        "options": [
                            {"label": "Fast", "value": "fast", "selected": True},
                            {
                                "label": "Sensitive",
                                "value": "sensitive",
                                "selected": False,
                            },
                        ],
                    },
                    "whens": [
                        {"discriminator": "fast", "parameters": []},
                        {
                            "discriminator": "sensitive",
                            "parameters": [{"name": "iterations", "type": "integer", "value": 3}],
                        },
                    ],
                }
            ],
            "x-shell-command": 'mode="$(inputs.search_options.mode)"\niterations="$(inputs.search_options.iterations)"',
        }
    )

    type: Annotated[
        Literal["conditional"],
        Field(description="Shows one set of nested inputs at a time according to a Boolean or select control."),
    ]
    test_parameter: Annotated[
        YamlConditionalTestParameter,
        Field(description="Boolean or select input whose submitted value chooses the active `whens` branch."),
    ]
    whens: Annotated[
        List[YamlConditionalWhen],
        Field(
            min_length=1,
            description="Maps each control value to the nested parameters shown and supplied for that branch.",
        ),
    ]

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
    """A group the user may add multiple times, with ``parameters`` defining one repeated entry."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "extra_files",
                    "type": "repeat",
                    "label": "Additional files",
                    "min": 0,
                    "max": 3,
                    "parameters": [{"name": "input_file", "type": "data", "format": ["txt"]}],
                }
            ],
            "x-shell-command": ("files='$(inputs.extra_files.map((item) => item.input_file.path).join(\" \"))'"),
        }
    )

    type: Annotated[
        Literal["repeat"],
        Field(description="Lets the user add multiple entries that all contain the same nested inputs."),
    ]
    parameters: Annotated[
        List["YamlGalaxyToolParameter"],
        Field(description="Nested inputs that make up one entry in the repeated group."),
    ] = []
    min: Annotated[
        Optional[int],
        Field(description="Keeps at least this many entries in the group and creates them when the form opens."),
    ] = None
    max: Annotated[
        Optional[int],
        Field(description="Prevents the user from adding more than this many entries."),
    ] = None

    def to_internal(self) -> RepeatParameterModel:
        return RepeatParameterModel(
            type="repeat",
            parameters=[p.root.to_internal() for p in self.parameters],
            min=self.min,
            max=self.max,
            **_common_internal_kwargs(self),
        )


class YamlSectionParameter(_YamlParamBase):
    """Related inputs that users can expand or collapse to reduce form complexity."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "advanced",
                    "type": "section",
                    "label": "Advanced options",
                    "parameters": [
                        {
                            "name": "threshold",
                            "type": "float",
                            "value": 0.5,
                            "min": 0.0,
                            "max": 1.0,
                        }
                    ],
                }
            ],
            "x-shell-command": 'threshold="$(inputs.advanced.threshold)"',
        }
    )

    type: Annotated[
        Literal["section"],
        Field(description="Places related inputs in a collapsible group to simplify the tool form."),
    ]
    parameters: Annotated[
        List["YamlGalaxyToolParameter"],
        Field(description="Nested inputs displayed together inside the section."),
    ] = []

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
