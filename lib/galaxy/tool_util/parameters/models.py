# attempt to model requires_value...
# conditional can descend...
from abc import abstractmethod
from typing import (
    Any,
    Callable,
    cast,
    Dict,
    Iterable,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Type,
    Union,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    create_model,
    Discriminator,
    Field,
    field_validator,
    RootModel,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    Tag,
    ValidationError,
)
from typing_extensions import (
    Annotated,
    Literal,
    Protocol,
)

from galaxy.exceptions import RequestParameterInvalidException
from ._types import (
    cast_as_type,
    is_optional,
    list_type,
    optional_if_needed,
    union_type,
)

# TODO:
# - implement job vs request...
# - drill down
# - implement data_ref on rules and implement some cross model validation
# - Optional conditionals... work through that?
# - Sections - fight that battle again...

# + request: Return info needed to build request pydantic model at runtime.
# + request_internal: This is a pydantic model to validate what Galaxy expects to find in the database,
# in particular dataset and collection references should be decoded integers.
StateRepresentationT = Literal["request", "request_internal", "job_internal", "test_case"]


# could be made more specific - validators need to be classmethod
ValidatorDictT = Dict[str, Callable]


class DynamicModelInformation(NamedTuple):
    name: str
    definition: tuple
    validators: ValidatorDictT


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def allow_batching(job_template: DynamicModelInformation, batch_type: Optional[Type] = None) -> DynamicModelInformation:
    job_py_type: Type = job_template.definition[0]
    default_value = job_template.definition[1]
    batch_type = batch_type or job_py_type

    class BatchRequest(StrictModel):
        meta_class: Literal["Batch"] = Field(..., alias="__class__")
        values: List[batch_type]  # type: ignore[valid-type]

    request_type = union_type([job_py_type, BatchRequest])

    return DynamicModelInformation(
        job_template.name,
        (request_type, default_value),
        {},  # should we modify these somehow?
    )


class Validators:
    def validate_not_none(cls, v):
        assert v is not None, "null is an invalid value for attribute"
        return v


class ParamModel(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def request_requires_value(self) -> bool:
        # if this is a non-optional type and no default is defined - an
        # input value MUST be specified.
        ...


def dynamic_model_information_from_py_type(param_model: ParamModel, py_type: Type):
    name = param_model.name
    initialize = ... if param_model.request_requires_value else None
    py_type_is_optional = is_optional(py_type)
    if not py_type_is_optional and not param_model.request_requires_value:
        validators = {"not_null": field_validator(name)(Validators.validate_not_none)}
    else:
        validators = {}

    return DynamicModelInformation(
        name,
        (py_type, initialize),
        validators,
    )


# We probably need incoming (parameter def) and outgoing (parameter value as transmitted) models,
# where value in the incoming model means "default value" and value in the outgoing model is the actual
# value a user has set. (incoming/outgoing from the client perspective).
class BaseToolParameterModelDefinition(BaseModel):
    name: str
    parameter_type: str

    @abstractmethod
    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        """Return info needed to build Pydantic model at runtime for validation."""


class BaseGalaxyToolParameterModelDefinition(BaseToolParameterModelDefinition):
    hidden: bool = False
    label: Optional[str] = None
    help: Optional[str] = None
    argument: Optional[str] = None
    is_dynamic: bool = False
    optional: bool = False


class LabelValue(BaseModel):
    label: str
    value: str
    selected: bool


class TextParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_text"] = "gx_text"
    area: bool = False
    default_value: Optional[str] = Field(default=None, alias="value")
    default_options: List[LabelValue] = []

    @property
    def py_type(self) -> Type:
        return optional_if_needed(StrictStr, self.optional)

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        return dynamic_model_information_from_py_type(self, self.py_type)

    @property
    def request_requires_value(self) -> bool:
        return False


class IntegerParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_integer"] = "gx_integer"
    optional: bool
    value: Optional[int] = None
    min: Optional[int] = None
    max: Optional[int] = None

    @property
    def py_type(self) -> Type:
        return optional_if_needed(StrictInt, self.optional)

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        return dynamic_model_information_from_py_type(self, self.py_type)

    @property
    def request_requires_value(self) -> bool:
        return False


class FloatParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_float"] = "gx_float"
    value: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None

    @property
    def py_type(self) -> Type:
        return optional_if_needed(union_type([StrictInt, StrictFloat]), self.optional)

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        return dynamic_model_information_from_py_type(self, self.py_type)

    @property
    def request_requires_value(self) -> bool:
        return False


DataSrcT = Literal["hda", "ldda"]
MultiDataSrcT = Literal["hda", "ldda", "hdca"]
CollectionStrT = Literal["hdca"]

TestCaseDataSrcT = Literal["File"]


class DataRequest(StrictModel):
    src: DataSrcT
    id: StrictStr


class BatchDataInstance(StrictModel):
    src: MultiDataSrcT
    id: StrictStr


class MultiDataInstance(StrictModel):
    src: MultiDataSrcT
    id: StrictStr


MultiDataRequest: Type = union_type([MultiDataInstance, List[MultiDataInstance]])


class DataRequestInternal(StrictModel):
    src: DataSrcT
    id: StrictInt


class BatchDataInstanceInternal(StrictModel):
    src: MultiDataSrcT
    id: StrictInt


class MultiDataInstanceInternal(StrictModel):
    src: MultiDataSrcT
    id: StrictInt


class DataTestCaseValue(StrictModel):
    src: TestCaseDataSrcT
    path: str


class MultipleDataTestCaseValue(RootModel):
    root: List[DataTestCaseValue]


MultiDataRequestInternal: Type = union_type([MultiDataInstanceInternal, List[MultiDataInstanceInternal]])


class DataParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_data"] = "gx_data"
    extensions: List[str] = ["data"]
    multiple: bool = False
    min: Optional[int] = None
    max: Optional[int] = None

    @property
    def py_type(self) -> Type:
        base_model: Type
        if self.multiple:
            base_model = MultiDataRequest
        else:
            base_model = DataRequest
        return optional_if_needed(base_model, self.optional)

    @property
    def py_type_internal(self) -> Type:
        base_model: Type
        if self.multiple:
            base_model = MultiDataRequestInternal
        else:
            base_model = DataRequestInternal
        return optional_if_needed(base_model, self.optional)

    @property
    def py_type_test_case(self) -> Type:
        base_model: Type
        if self.multiple:
            base_model = MultiDataRequestInternal
        else:
            base_model = DataTestCaseValue
        return optional_if_needed(base_model, self.optional)

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        if state_representation == "request":
            return allow_batching(dynamic_model_information_from_py_type(self, self.py_type), BatchDataInstance)
        elif state_representation == "request_internal":
            return allow_batching(
                dynamic_model_information_from_py_type(self, self.py_type_internal), BatchDataInstanceInternal
            )
        elif state_representation == "job_internal":
            return dynamic_model_information_from_py_type(self, self.py_type_internal)
        elif state_representation == "test_case":
            return dynamic_model_information_from_py_type(self, self.py_type_test_case)

    @property
    def request_requires_value(self) -> bool:
        return not self.optional


class DataCollectionRequest(StrictModel):
    src: CollectionStrT
    id: StrictStr


class DataCollectionRequestInternal(StrictModel):
    src: CollectionStrT
    id: StrictInt


class DataCollectionParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_data_collection"] = "gx_data_collection"
    collection_type: Optional[str] = None
    extensions: List[str] = ["data"]

    @property
    def py_type(self) -> Type:
        return optional_if_needed(DataCollectionRequest, self.optional)

    @property
    def py_type_internal(self) -> Type:
        return optional_if_needed(DataCollectionRequestInternal, self.optional)

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        if state_representation == "request":
            return allow_batching(dynamic_model_information_from_py_type(self, self.py_type))
        elif state_representation == "request_internal":
            return allow_batching(dynamic_model_information_from_py_type(self, self.py_type_internal))
        else:
            raise NotImplementedError("...")

    @property
    def request_requires_value(self) -> bool:
        return not self.optional


class HiddenParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_hidden"] = "gx_hidden"

    @property
    def py_type(self) -> Type:
        return optional_if_needed(StrictStr, self.optional)

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        return dynamic_model_information_from_py_type(self, self.py_type)

    @property
    def request_requires_value(self) -> bool:
        return not self.optional


def ensure_color_valid(value: Optional[Any]):
    if value is None:
        return
    if not isinstance(value, str):
        raise ValueError(f"Invalid color value type {value.__class__} encountered.")
    value_str: str = value
    message = f"Invalid color value string format {value_str} encountered."
    if len(value_str) != 7:
        raise ValueError(message + "0")
    if value_str[0] != "#":
        raise ValueError(message + "1")
    for byte_str in value_str[1:]:
        if byte_str not in "0123456789abcdef":
            raise ValueError(message + "2")


class ColorParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_color"] = "gx_color"
    value: Optional[str] = None

    @property
    def py_type(self) -> Type:
        return optional_if_needed(StrictStr, self.optional)

    @staticmethod
    def validate_color_str(value) -> str:
        ensure_color_valid(value)
        return value

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        validators = {"color_format": field_validator(self.name)(ColorParameterModel.validate_color_str)}
        return DynamicModelInformation(
            self.name,
            (self.py_type, ...),
            validators,
        )

    @property
    def request_requires_value(self) -> bool:
        return False


class BooleanParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_boolean"] = "gx_boolean"
    value: Optional[bool] = False
    truevalue: Optional[str] = None
    falsevalue: Optional[str] = None

    @property
    def py_type(self) -> Type:
        return optional_if_needed(StrictBool, self.optional)

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        return dynamic_model_information_from_py_type(self, self.py_type)

    @property
    def request_requires_value(self) -> bool:
        # these parameters always have an implicit default - either None if
        # if it is optional or 'checked' if not (itself defaulting to False).
        return False


class DirectoryUriParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_directory_uri"]
    value: Optional[str]

    @property
    def request_requires_value(self) -> bool:
        return True


class RulesMapping(StrictModel):
    type: str
    columns: List[StrictInt]


class RulesModel(StrictModel):
    rules: List[Dict[str, Any]]
    mappings: List[RulesMapping]


class RulesParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_rules"] = "gx_rules"

    @property
    def py_type(self) -> Type:
        return RulesModel

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        return dynamic_model_information_from_py_type(self, self.py_type)

    @property
    def request_requires_value(self) -> bool:
        return True


class SelectParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_select"] = "gx_select"
    options: Optional[List[LabelValue]] = None
    multiple: bool

    @property
    def py_type(self) -> Type:
        if self.options is not None:
            literal_options: List[Type] = [cast_as_type(Literal[o.value]) for o in self.options]
            py_type = union_type(literal_options)
        else:
            py_type = StrictStr
        if self.multiple:
            py_type = list_type(py_type)
        return optional_if_needed(py_type, self.optional)

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        return dynamic_model_information_from_py_type(self, self.py_type)

    @property
    def has_selected_static_option(self):
        return self.options is not None and any(o.selected for o in self.options)

    @property
    def request_requires_value(self) -> bool:
        return not self.optional and not self.has_selected_static_option


DiscriminatorType = Union[bool, str]


class ConditionalWhen(StrictModel):
    discriminator: DiscriminatorType
    parameters: List["ToolParameterT"]
    is_default_when: bool


class ConditionalParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_conditional"] = "gx_conditional"
    test_parameter: Union[BooleanParameterModel, SelectParameterModel]
    whens: List[ConditionalWhen]

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        test_param_name = self.test_parameter.name
        test_info = self.test_parameter.pydantic_template(state_representation)
        extra_validators = test_info.validators
        test_parameter_requires_value = self.test_parameter.request_requires_value
        when_types: List[Type[BaseModel]] = []
        default_type = None
        for when in self.whens:
            discriminator = when.discriminator
            parameters = when.parameters
            if test_parameter_requires_value:
                initialize_test = ...
            else:
                initialize_test = None

            extra_kwd = {test_param_name: (Union[str, bool], initialize_test)}
            when_types.append(
                cast(
                    Type[BaseModel],
                    Annotated[
                        create_field_model(
                            parameters,
                            f"When_{test_param_name}_{discriminator}",
                            state_representation,
                            extra_kwd=extra_kwd,
                            extra_validators=extra_validators,
                        ),
                        Tag(str(discriminator)),
                    ],
                )
            )
            if when.is_default_when:
                extra_kwd = {}
                default_type = create_field_model(
                    parameters,
                    f"When_{test_param_name}___absent",
                    state_representation,
                    extra_kwd=extra_kwd,
                    extra_validators={},
                )
                when_types.append(cast(Type[BaseModel], Annotated[default_type, Tag("__absent__")]))

        def model_x_discriminator(v: Any) -> str:
            if test_param_name not in v:
                return "__absent__"
            else:
                test_param_val = v[test_param_name]
                if test_param_val is True:
                    return "true"
                elif test_param_val is False:
                    return "false"
                else:
                    return str(test_param_val)

        cond_type = union_type(when_types)

        class ConditionalType(RootModel):
            root: cond_type = Field(..., discriminator=Discriminator(model_x_discriminator))  # type: ignore[valid-type]

        if default_type is not None:
            initialize_cond = None
        else:
            initialize_cond = ...

        py_type = ConditionalType

        return DynamicModelInformation(
            self.name,
            (py_type, initialize_cond),
            {},
        )

    @property
    def request_requires_value(self) -> bool:
        return False  # TODO


class RepeatParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_repeat"] = "gx_repeat"
    parameters: List["ToolParameterT"]
    min: Optional[int] = None
    max: Optional[int] = None

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        # Maybe validators for min and max...
        instance_class: Type[BaseModel] = create_field_model(
            self.parameters, f"Repeat_{self.name}", state_representation
        )

        class RepeatType(RootModel):
            root: List[instance_class] = Field(..., min_length=self.min, max_length=self.max)  # type: ignore[valid-type]

        return DynamicModelInformation(
            self.name,
            (RepeatType, ...),
            {},
        )

    @property
    def request_requires_value(self) -> bool:
        return True  # TODO:


class SectionParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_section"] = "gx_section"
    parameters: List["ToolParameterT"]

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        instance_class: Type[BaseModel] = create_field_model(
            self.parameters, f"Section_{self.name}", state_representation
        )
        if self.request_requires_value:
            initialize_section = ...
        else:
            initialize_section = None
        return DynamicModelInformation(
            self.name,
            (instance_class, initialize_section),
            {},
        )

    @property
    def request_requires_value(self) -> bool:
        any_request_parameters_required = False
        for parameter in self.parameters:
            if parameter.request_requires_value:
                any_request_parameters_required = True
                break
        return any_request_parameters_required


LiteralNone: Type = Literal[None]  # type: ignore[assignment]


class CwlNullParameterModel(BaseToolParameterModelDefinition):
    parameter_type: Literal["cwl_null"] = "cwl_null"

    @property
    def py_type(self) -> Type:
        return LiteralNone

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        return DynamicModelInformation(
            self.name,
            (self.py_type, ...),
            {},
        )

    @property
    def request_requires_value(self) -> bool:
        return False


class CwlStringParameterModel(BaseToolParameterModelDefinition):
    parameter_type: Literal["cwl_string"] = "cwl_string"

    @property
    def py_type(self) -> Type:
        return StrictStr

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        return DynamicModelInformation(
            self.name,
            (self.py_type, ...),
            {},
        )

    @property
    def request_requires_value(self) -> bool:
        return True


class CwlIntegerParameterModel(BaseToolParameterModelDefinition):
    parameter_type: Literal["cwl_integer"] = "cwl_integer"

    @property
    def py_type(self) -> Type:
        return StrictInt

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        return DynamicModelInformation(
            self.name,
            (self.py_type, ...),
            {},
        )

    @property
    def request_requires_value(self) -> bool:
        return True


class CwlFloatParameterModel(BaseToolParameterModelDefinition):
    parameter_type: Literal["cwl_float"] = "cwl_float"

    @property
    def py_type(self) -> Type:
        return union_type([StrictFloat, StrictInt])

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        return DynamicModelInformation(
            self.name,
            (self.py_type, ...),
            {},
        )

    @property
    def request_requires_value(self) -> bool:
        return True


class CwlBooleanParameterModel(BaseToolParameterModelDefinition):
    parameter_type: Literal["cwl_boolean"] = "cwl_boolean"

    @property
    def py_type(self) -> Type:
        return StrictBool

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        return DynamicModelInformation(
            self.name,
            (self.py_type, ...),
            {},
        )

    @property
    def request_requires_value(self) -> bool:
        return True


class CwlUnionParameterModel(BaseToolParameterModelDefinition):
    parameter_type: Literal["cwl_union"] = "cwl_union"
    parameters: List["CwlParameterT"]

    @property
    def py_type(self) -> Type:
        union_of_cwl_types: List[Type] = []
        for parameter in self.parameters:
            union_of_cwl_types.append(parameter.py_type)
        return union_type(union_of_cwl_types)

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        return DynamicModelInformation(
            self.name,
            (self.py_type, ...),
            {},
        )

    @property
    def request_requires_value(self) -> bool:
        return False  # TODO:


class CwlFileParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["cwl_file"] = "cwl_file"

    @property
    def py_type(self) -> Type:
        return DataRequest

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        return dynamic_model_information_from_py_type(self, self.py_type)

    @property
    def request_requires_value(self) -> bool:
        return True


class CwlDirectoryParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["cwl_directory"] = "cwl_directory"

    @property
    def py_type(self) -> Type:
        return DataRequest

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        return dynamic_model_information_from_py_type(self, self.py_type)

    @property
    def request_requires_value(self) -> bool:
        return True


CwlParameterT = Union[
    CwlIntegerParameterModel,
    CwlFloatParameterModel,
    CwlStringParameterModel,
    CwlBooleanParameterModel,
    CwlNullParameterModel,
    CwlFileParameterModel,
    CwlDirectoryParameterModel,
    CwlUnionParameterModel,
]

GalaxyParameterT = Union[
    TextParameterModel,
    IntegerParameterModel,
    FloatParameterModel,
    BooleanParameterModel,
    HiddenParameterModel,
    SelectParameterModel,
    DataParameterModel,
    DataCollectionParameterModel,
    DirectoryUriParameterModel,
    RulesParameterModel,
    ColorParameterModel,
    ConditionalParameterModel,
    RepeatParameterModel,
    SectionParameterModel,
]

ToolParameterT = Union[
    CwlParameterT,
    GalaxyParameterT,
]


class ToolParameterModel(RootModel):
    root: ToolParameterT = Field(..., discriminator="parameter_type")


ConditionalWhen.model_rebuild()
ConditionalParameterModel.model_rebuild()
RepeatParameterModel.model_rebuild()
CwlUnionParameterModel.model_rebuild()


class ToolParameterBundle(Protocol):
    """An object having a dictionary of input models (i.e. a 'Tool')"""

    # TODO: rename to parameters to align with ConditionalWhen and Repeat.
    input_models: List[ToolParameterT]


class ToolParameterBundleModel(BaseModel):
    input_models: List[ToolParameterT]


def parameters_by_name(tool_parameter_bundle: ToolParameterBundle) -> Dict[str, ToolParameterT]:
    as_dict = {}
    for input_model in simple_input_models(tool_parameter_bundle.input_models):
        as_dict[input_model.name] = input_model
    return as_dict


def to_simple_model(input_parameter: Union[ToolParameterModel, ToolParameterT]) -> ToolParameterT:
    if input_parameter.__class__ == ToolParameterModel:
        assert isinstance(input_parameter, ToolParameterModel)
        return cast(ToolParameterT, input_parameter.root)
    else:
        return cast(ToolParameterT, input_parameter)


def simple_input_models(
    input_models: Union[List[ToolParameterModel], List[ToolParameterT]]
) -> Iterable[ToolParameterT]:
    return [to_simple_model(m) for m in input_models]


def create_model_strict(*args, **kwd) -> Type[BaseModel]:
    model_config = ConfigDict(extra="forbid")

    return create_model(*args, __config__=model_config, **kwd)


def create_request_model(tool: ToolParameterBundle, name: str = "DynamicModelForTool") -> Type[BaseModel]:
    return create_field_model(tool.input_models, name, "request")


def create_request_internal_model(tool: ToolParameterBundle, name: str = "DynamicModelForTool") -> Type[BaseModel]:
    return create_field_model(tool.input_models, name, "request_internal")


def create_job_internal_model(tool: ToolParameterBundle, name: str = "DynamicModelForTool") -> Type[BaseModel]:
    return create_field_model(tool.input_models, name, "job_internal")


def create_test_case_model(tool: ToolParameterBundle, name: str = "DynamicModelForTool") -> Type[BaseModel]:
    return create_field_model(tool.input_models, name, "test_case")


def create_field_model(
    tool_parameter_models: Union[List[ToolParameterModel], List[ToolParameterT]],
    name: str,
    state_representation: StateRepresentationT,
    extra_kwd: Optional[Mapping[str, tuple]] = None,
    extra_validators: Optional[ValidatorDictT] = None,
) -> Type[BaseModel]:
    kwd: Dict[str, tuple] = {}
    if extra_kwd:
        kwd.update(extra_kwd)
    model_validators = (extra_validators or {}).copy()

    for input_model in tool_parameter_models:
        input_model = to_simple_model(input_model)
        input_name = input_model.name
        pydantic_request_template = input_model.pydantic_template(state_representation)
        kwd[input_name] = pydantic_request_template.definition
        input_validators = pydantic_request_template.validators
        for validator_name, validator_callable in input_validators.items():
            model_validators[f"{input_name}_{validator_name}"] = validator_callable

    pydantic_model = create_model_strict(name, __validators__=model_validators, **kwd)
    return pydantic_model


def validate_against_model(pydantic_model: Type[BaseModel], parameter_state: Dict[str, Any]) -> None:
    try:
        pydantic_model(**parameter_state)
    except ValidationError as e:
        # TODO: Improve this or maybe add a handler for this in the FastAPI exception
        # handler.
        raise RequestParameterInvalidException(str(e))


def validate_request(tool: ToolParameterBundle, request: Dict[str, Any]) -> None:
    pydantic_model = create_request_model(tool)
    validate_against_model(pydantic_model, request)


def validate_internal_request(tool: ToolParameterBundle, request: Dict[str, Any]) -> None:
    pydantic_model = create_request_internal_model(tool)
    validate_against_model(pydantic_model, request)


def validate_internal_job(tool: ToolParameterBundle, request: Dict[str, Any]) -> None:
    pydantic_model = create_job_internal_model(tool)
    validate_against_model(pydantic_model, request)


def validate_test_case(tool: ToolParameterBundle, request: Dict[str, Any]) -> None:
    pydantic_model = create_test_case_model(tool)
    validate_against_model(pydantic_model, request)
