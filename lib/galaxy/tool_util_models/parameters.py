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
    Sequence,
    Type,
    TypeVar,
    Union,
)

from pydantic import (
    AfterValidator,
    AnyUrl,
    BaseModel,
    ConfigDict,
    create_model,
    Discriminator,
    Field,
    field_validator,
    HttpUrl,
    model_validator,
    RootModel,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    Tag,
    TypeAdapter,
)
from pydantic.json_schema import SkipJsonSchema
from typing_extensions import (
    Annotated,
    Literal,
    Protocol,
)

from ._types import (
    cast_as_type,
    expand_annotation,
    is_optional,
    list_type,
    optional,
    optional_if_needed,
    union_type,
)
from .parameter_validators import (
    EmptyFieldParameterValidatorModel,
    ExpressionParameterValidatorModel,
    InRangeParameterValidatorModel,
    LengthParameterValidatorModel,
    NoOptionsParameterValidatorModel,
    RegexParameterValidatorModel,
    StaticValidatorModel,
)
from .tool_source import (
    DrillDownOptionsDict,
    JsonTestCollectionDefDict,
    JsonTestDatasetDefDict,
)

# TODO:
# - implement data_ref on rules and implement some cross model validation

# + request: Return info needed to build request pydantic model at runtime.
# + request_internal: This is a pydantic model to validate what Galaxy expects to find in the database,
# in particular dataset and collection references should be decoded integers.
StateRepresentationT = Literal[
    "request",
    "request_internal",
    "request_internal_dereferenced",
    "landing_request",
    "landing_request_internal",
    "job_runtime",
    "job_internal",
    "test_case_xml",
    "workflow_step",
    "workflow_step_linked",
]

DEFAULT_MODEL_NAME = "DynamicModelForTool"
RawStateDict = Dict[str, Any]


# could be made more specific - validators need to be classmethod
ValidatorDictT = Dict[str, Callable]


class DynamicModelInformation(NamedTuple):
    name: str
    definition: tuple
    validators: ValidatorDictT


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConnectedValue(BaseModel):
    discriminator: Literal["ConnectedValue"] = Field(alias="__class__")


def allow_connected_value(type: Type):
    return union_type([type, ConnectedValue])


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


def safe_field_name(name: str) -> str:
    if name.startswith("_"):
        return f"X{name}"
    return name


def dynamic_model_information_from_py_type(
    param_model: ParamModel, py_type: Type, requires_value: Optional[bool] = None, validators=None
):
    name = safe_field_name(param_model.name)
    if requires_value is None:
        requires_value = param_model.request_requires_value
    initialize = ... if requires_value else None
    py_type_is_optional = is_optional(py_type)
    validators = validators or {}
    if not py_type_is_optional and not requires_value:
        validators["not_null"] = field_validator(name)(Validators.validate_not_none)

    return DynamicModelInformation(
        name,
        (py_type, Field(initialize, alias=param_model.name if param_model.name != name else None)),
        validators,
    )


# We probably need incoming (parameter def) and outgoing (parameter value as transmitted) models,
# where value in the incoming model means "default value" and value in the outgoing model is the actual
# value a user has set. (incoming/outgoing from the client perspective).
class BaseToolParameterModelDefinition(BaseModel):
    name: Annotated[
        str,
        Field(description="Parameter name. Used when referencing parameter in workflows or inside command templating."),
    ]
    parameter_type: str

    @abstractmethod
    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        """Return info needed to build Pydantic model at runtime for validation."""


class BaseGalaxyToolParameterModelDefinition(BaseToolParameterModelDefinition):
    hidden: bool = False
    label: Optional[
        Annotated[str, Field(description="Will be displayed on the tool page as the label of the parameter.")]
    ] = None
    help: Optional[
        Annotated[
            str,
            Field(
                description="Short bit of text, rendered on the tool form just below the associated field to provide information about the field."
            ),
        ]
    ] = None
    argument: Optional[
        Annotated[
            str,
            Field(
                description="""If the parameter reflects just one command line argument of a certain tool, this tag should be set to that particular argument. It is rendered in parenthesis after the help section, and it will create the name attribute (if not given explicitly) from the argument attribute by stripping leading dashes and replacing all remaining dashes by underscores (e.g. if argument="--long-parameter" then name="long_parameter" is implicit)."""
            ),
        ]
    ] = None
    is_dynamic: bool = False
    optional: Annotated[bool, Field(description="If `false`, parameter must have a value.")] = False


class LabelValue(BaseModel):
    label: str
    value: str
    selected: bool


TextCompatiableValidators = Union[
    LengthParameterValidatorModel,
    RegexParameterValidatorModel,
    ExpressionParameterValidatorModel,
    EmptyFieldParameterValidatorModel,
]


def pydantic_to_galaxy_type(value: Any) -> Any:
    """We use advanced Pydantic types like URL but the Galaxy validators only expect strings for these."""
    if isinstance(value, AnyUrl):
        return str(value)

    return value


VT = TypeVar("VT", bound=StaticValidatorModel)


def decorate_type_with_validators_if_needed(py_type: Type, static_validator_models: Sequence[VT]) -> Type:
    pydantic_validator = pydantic_validator_for(static_validator_models)
    if pydantic_validator:
        return expand_annotation(py_type, [pydantic_validator])
    else:
        return py_type


# Looks like Annotated only work with one PlainValidator so condensing all static validators
# into a single PlainValidator for pydantic.
def pydantic_validator_for(static_validator_models: Sequence[VT]) -> Optional[AfterValidator]:

    if static_validator_models:

        def validator(v: Any) -> Any:
            gx_val = pydantic_to_galaxy_type(v)

            for static_validator_model in static_validator_models:
                static_validator_model.statically_validate(gx_val)
            return v

        return AfterValidator(validator)
    else:
        return None


class TextParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_text"] = "gx_text"
    type: Literal["text"]
    area: bool = False
    default_value: Optional[str] = Field(default=None, alias="value")
    default_options: List[LabelValue] = []
    validators: List[TextCompatiableValidators] = []

    @property
    def py_type(self) -> Type:
        return optional_if_needed(StrictStr, self.optional)

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        py_type = decorate_type_with_validators_if_needed(self.py_type, self.validators)
        if state_representation == "workflow_step_linked":
            py_type = allow_connected_value(py_type)
        requires_value = self.request_requires_value
        if state_representation in ("job_internal", "job_runtime"):
            requires_value = True
        return dynamic_model_information_from_py_type(self, py_type, requires_value=requires_value)

    @property
    def request_requires_value(self) -> bool:
        return False


NumberCompatiableValidators = Union[InRangeParameterValidatorModel,]


class IntegerParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_integer"] = "gx_integer"
    type: Literal["integer"]
    optional: bool
    value: Optional[int] = None
    min: Optional[int] = None
    max: Optional[int] = None
    validators: List[NumberCompatiableValidators] = []

    @property
    def py_type(self) -> Type:
        return optional_if_needed(StrictInt, self.optional)

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        py_type = self.py_type
        validators = self.validators[:]
        if self.min is not None or self.max is not None:
            validators.append(InRangeParameterValidatorModel(min=self.min, max=self.max, implicit=True))
        py_type = decorate_type_with_validators_if_needed(py_type, validators)
        if state_representation == "workflow_step_linked":
            py_type = allow_connected_value(py_type)
        requires_value = self.request_requires_value
        if state_representation in ("job_internal", "job_runtime"):
            requires_value = True
        elif _is_landing_request(state_representation):
            requires_value = False
        return dynamic_model_information_from_py_type(self, py_type, requires_value=requires_value)

    @property
    def request_requires_value(self) -> bool:
        return not self.optional and self.value is None


class FloatParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_float"] = "gx_float"
    type: Literal["float"]
    value: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    validators: List[NumberCompatiableValidators] = []

    @property
    def py_type(self) -> Type:
        return optional_if_needed(union_type([StrictInt, StrictFloat]), self.optional)

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        py_type = self.py_type
        if state_representation == "workflow_step_linked":
            py_type = allow_connected_value(py_type)
        requires_value = self.request_requires_value
        if state_representation in ("job_internal", "job_runtime"):
            requires_value = True
        elif _is_landing_request(state_representation):
            requires_value = False
        validators = self.validators[:]
        if self.min is not None or self.max is not None:
            validators.append(InRangeParameterValidatorModel(min=self.min, max=self.max, implicit=True))
        py_type = decorate_type_with_validators_if_needed(py_type, validators)
        return dynamic_model_information_from_py_type(self, py_type, requires_value=requires_value)

    @property
    def request_requires_value(self) -> bool:
        return False


DataSrcT = Literal["hda", "ldda"]
MultiDataSrcT = Literal["hda", "ldda", "hdca"]
# @jmchilton you meant CollectionSrcT - fix that at some point please.
CollectionStrT = Literal["hdca"]

TestCaseDataSrcT = Literal["File"]


class LegacyRequestModelAttributes(StrictModel):
    # Here for bioblend's sake, should be stripped
    map_over_type: SkipJsonSchema[Optional[str]] = Field(None, exclude=True)
    hid: SkipJsonSchema[Optional[int]] = Field(None, exclude=True)
    workflow_step_id: SkipJsonSchema[Optional[str]] = Field(None, exclude=True)
    label: SkipJsonSchema[Optional[str]] = Field(None, exclude=True)


class DataRequestHda(LegacyRequestModelAttributes):
    src: Literal["hda"] = "hda"
    id: StrictStr


class DataRequestLdda(LegacyRequestModelAttributes):
    src: Literal["ldda"] = "ldda"
    id: StrictStr


class DataRequestLd(LegacyRequestModelAttributes):
    src: Literal["ld"] = Field(deprecated=True)
    id: StrictStr


class DataRequestHdca(LegacyRequestModelAttributes):
    src: Literal["hdca"] = "hdca"
    id: StrictStr


class DatasetHash(StrictModel):
    hash_function: Literal["MD5", "SHA-1", "SHA-256", "SHA-512"]
    hash_value: StrictStr


class BaseDataRequest(StrictModel):
    url: StrictStr = Field(..., alias="location")
    name: Optional[StrictStr] = None
    ext: StrictStr
    dbkey: StrictStr = "?"
    deferred: StrictBool = False
    created_from_basename: Optional[StrictStr] = None
    info: Optional[StrictStr] = None
    hashes: Optional[List[DatasetHash]] = None
    space_to_tab: bool = False
    to_posix_lines: bool = False

    # to implement:
    # tags
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def allow_filetype_and_extension(cls, data: Any):
        if isinstance(data, dict):
            extension = data.get("filetype")
            if extension:
                data = data.copy()
                data.pop("filetype")
                data["ext"] = extension
            extension = data.get("extension")
            if extension:
                data = data.copy()
                data.pop("extension")
                data["ext"] = extension
        return data


class DataRequestUri(BaseDataRequest):
    # calling it url instead of uri to match data fetch schema...
    src: Literal["url"] = "url"


class FileRequestUri(BaseDataRequest):
    class_: Literal["File"] = Field(..., alias="class")
    src: None = Field(None, exclude=True)


class CollectionElementDataRequestUri(FileRequestUri):
    class_: Literal["File"] = Field(..., alias="class")
    identifier: StrictStr


class CollectionElementCollectionRequestUri(StrictModel):
    class_: Literal["Collection"] = Field(..., alias="class")
    identifier: StrictStr
    collection_type: StrictStr
    elements: List[
        Annotated[
            Union["CollectionElementCollectionRequestUri", CollectionElementDataRequestUri],
            Field(discriminator="class_"),
        ]
    ]

    @model_validator(mode="before")
    @classmethod
    def allow_collection_type_by_type(cls, data: Any):
        if isinstance(data, dict):
            collection_type = data.get("type")
            if collection_type:
                data = data.copy()
                data.pop("type")
                data["collection_type"] = collection_type
        return data


class DataRequestCollectionUri(StrictModel):
    class_: Literal["Collection"] = Field(..., alias="class")
    collection_type: str
    elements: List[
        Annotated[
            Union[CollectionElementCollectionRequestUri, CollectionElementDataRequestUri], Field(discriminator="class_")
        ]
    ]
    deferred: StrictBool = False
    name: Optional[StrictStr] = None
    src: None = Field(None, exclude=True)


_DataRequest = Annotated[
    Union[DataRequestHda, DataRequestLdda, DataRequestLd, DataRequestUri], Field(discriminator="src")
]
DataRequest: Type = cast(Type, _DataRequest)

DataOrCollectionRequest = Union[_DataRequest, FileRequestUri, DataRequestCollectionUri, DataRequestHdca]

DataRequestHda.model_rebuild()
DataRequestLd.model_rebuild()
DataRequestLdda.model_rebuild()
DataRequestUri.model_rebuild()
DataRequestHdca.model_rebuild()
DataRequestCollectionUri.model_rebuild()

DataOrCollectionRequestAdapter: TypeAdapter[DataOrCollectionRequest] = TypeAdapter(DataOrCollectionRequest)


class BatchDataInstance(StrictModel):
    src: MultiDataSrcT
    id: StrictStr


MultiDataInstance: Type = cast(
    Type,
    Annotated[
        union_type([DataRequestHda, DataRequestLdda, DataRequestHdca, DataRequestUri]), Field(discriminator="src")
    ],
)
MultiDataRequest: Type = union_type([MultiDataInstance, list_type(MultiDataInstance)])


class DataRequestInternalHda(StrictModel):
    src: Literal["hda"]
    id: StrictInt


class DataRequestInternalLdda(StrictModel):
    src: Literal["ldda"]
    id: StrictInt


class DataRequestInternalHdca(StrictModel):
    src: Literal["hdca"]
    id: StrictInt


class DataInternalJson(StrictModel):
    class_: Annotated[Literal["File"], Field(alias="class")]
    basename: Annotated[
        str,
        Field(
            description="The base name of the file, that is, the name of the file without any leading directory path"
        ),
    ]
    location: str
    path: Annotated[str, Field(description="The absolute path to the file on disk.")]
    listing: Optional[List[str]]  # Should be recursive
    nameroot: Annotated[Optional[str], Field(description="The basename root such that nameroot + nameext == basename")]
    nameext: Annotated[
        Optional[str], Field(description="The basename extension such that nameroot + nameext == basename")
    ]
    # "secondaryFiles": List[Any],
    checksum: Optional[str]
    size: int


class DataCollectionInternalJson(RootModel):
    root: Dict[str, DataInternalJson]


class RecursiveDataCollectionInternalJson(RootModel):
    root: Dict[str, Union[DataInternalJson, "RecursiveDataCollectionInternalJson"]]


RecursiveDataCollectionInternalJson.model_rebuild()


class DataCollectionPaired(StrictModel):
    forward: DataInternalJson
    reverse: DataInternalJson


DataRequestInternal: Type = cast(
    Type, Annotated[Union[DataRequestInternalHda, DataRequestInternalLdda, DataRequestUri], Field(discriminator="src")]
)
DataRequestInternalDereferenced: Type = cast(
    Type,
    Annotated[Union[DataRequestInternalHda, DataRequestInternalLdda], Field(discriminator="src")],
)
DataJobInternal = DataRequestInternalDereferenced


class BatchDataInstanceInternal(StrictModel):
    src: MultiDataSrcT
    id: StrictInt


MultiDataInstanceInternal: Type = cast(
    Type,
    Annotated[
        Union[DataRequestInternalHda, DataRequestInternalLdda, DataRequestInternalHdca, DataRequestUri],
        Field(discriminator="src"),
    ],
)
MultiDataInstanceInternalDereferenced: Type = cast(
    Type,
    Annotated[
        Union[DataRequestInternalHda, DataRequestInternalLdda, DataRequestInternalHdca], Field(discriminator="src")
    ],
)

MultiDataRequestInternal: Type = union_type([MultiDataInstanceInternal, list_type(MultiDataInstanceInternal)])
MultiDataRequestInternalDereferenced: Type = union_type(
    [MultiDataInstanceInternalDereferenced, list_type(MultiDataInstanceInternalDereferenced)]
)


class DataParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_data"] = "gx_data"
    type: Literal["data"]
    extensions: Annotated[
        List[str],
        Field(
            description="Limit inputs to datasets with these extensions. Use 'data' to allow all input datasets.",
            examples=["txt", "tabular", "tiff"],
        ),
    ] = ["data"]
    multiple: Annotated[bool, Field(description="Allow multiple values to be selected.")] = False
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
    def py_type_internal_json(self) -> Type:
        base_model: Type
        if self.multiple:
            base_model = list_type(DataInternalJson)
        else:
            base_model = DataInternalJson
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
    def py_type_internal_dereferenced(self) -> Type:
        base_model: Type
        if self.multiple:
            base_model = MultiDataRequestInternalDereferenced
        else:
            base_model = DataRequestInternalDereferenced
        return optional_if_needed(base_model, self.optional)

    @property
    def py_type_test_case(self) -> Type:
        base_model: Type
        if self.multiple:
            base_model = list_type(JsonTestDatasetDefDict)
        else:
            base_model = JsonTestDatasetDefDict
        return optional_if_needed(base_model, self.optional)

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        if state_representation == "request":
            return allow_batching(dynamic_model_information_from_py_type(self, self.py_type), BatchDataInstance)
        if state_representation == "landing_request":
            return allow_batching(
                dynamic_model_information_from_py_type(self, self.py_type, requires_value=False), BatchDataInstance
            )
        elif state_representation == "request_internal":
            return allow_batching(
                dynamic_model_information_from_py_type(self, self.py_type_internal), BatchDataInstanceInternal
            )
        elif state_representation == "landing_request_internal":
            return allow_batching(
                dynamic_model_information_from_py_type(self, self.py_type_internal, requires_value=False),
                BatchDataInstanceInternal,
            )
        elif state_representation == "request_internal_dereferenced":
            return allow_batching(
                dynamic_model_information_from_py_type(self, self.py_type_internal_dereferenced),
                BatchDataInstanceInternal,
            )
        elif state_representation == "job_internal":
            return dynamic_model_information_from_py_type(self, self.py_type_internal_dereferenced, requires_value=True)
        elif state_representation == "job_runtime":
            return dynamic_model_information_from_py_type(self, self.py_type_internal_json, requires_value=True)
        elif state_representation == "test_case_xml":
            return dynamic_model_information_from_py_type(self, self.py_type_test_case)
        elif state_representation == "workflow_step":
            return dynamic_model_information_from_py_type(self, type(None), requires_value=False)
        elif state_representation == "workflow_step_linked":
            return dynamic_model_information_from_py_type(self, ConnectedValue)

    @property
    def request_requires_value(self) -> bool:
        return not self.optional


class DataCollectionRequest(StrictModel):
    src: CollectionStrT
    id: StrictStr


class DataCollectionRequestInternal(StrictModel):
    src: CollectionStrT
    id: StrictInt


CollectionAdapterSrcT = Literal["CollectionAdapter"]


class AdaptedDataCollectionRequestBase(StrictModel):
    src: CollectionAdapterSrcT


class AdaptedDataCollectionPromoteDatasetToCollectionRequest(AdaptedDataCollectionRequestBase):
    adapter_type: Literal["PromoteDatasetToCollection"]
    collection_type: Literal["list", "paired_or_unpaired"]
    adapting: DataRequestHda


# calling this name and element_identifier to align with fetch API, etc...
class AdapterElementRequest(DataRequestHda):
    name: str  # element_identifier


class AdaptedDataCollectionPromoteDatasetsToCollectionRequest(AdaptedDataCollectionRequestBase):
    adapter_type: Literal["PromoteDatasetsToCollection"]
    # could allow list in here without changing much else I think but I'm trying to keep these tight in scope
    collection_type: Literal["paired", "paired_or_unpaired"]
    adapting: List[AdapterElementRequest]


AdaptedDataCollectionRequest = Annotated[
    Union[
        AdaptedDataCollectionPromoteDatasetToCollectionRequest, AdaptedDataCollectionPromoteDatasetsToCollectionRequest
    ],
    Field(discriminator="adapter_type"),
]
AdaptedDataCollectionRequestTypeAdapter = TypeAdapter(AdaptedDataCollectionRequest)  # type:ignore[var-annotated]


class DatasetCollectionElementReference(StrictModel):
    src: Literal["dce"]
    id: StrictInt


class AdaptedDataCollectionPromoteCollectionElementToCollectionRequestInternal(AdaptedDataCollectionRequestBase):
    adapter_type: Literal["PromoteCollectionElementToCollection"]
    adapting: DatasetCollectionElementReference


class AdaptedDataCollectionPromoteDatasetToCollectionRequestInternal(AdaptedDataCollectionRequestBase):
    adapter_type: Literal["PromoteDatasetToCollection"]
    collection_type: Literal["list", "paired_or_unpaired"]
    adapting: DataRequestInternalHda


class AdapterElementRequestInternal(DataRequestInternalHda):
    name: str  # element_identifier


class AdaptedDataCollectionPromoteDatasetsToCollectionRequestInternal(AdaptedDataCollectionRequestBase):
    adapter_type: Literal["PromoteDatasetsToCollection"]
    # could allow list in here without changing much else I think but I'm trying to keep these tight in scope
    collection_type: Literal["paired", "paired_or_unpaired"]
    adapting: List[AdapterElementRequestInternal]


AdaptedDataCollectionRequestInternal = Annotated[
    Union[
        AdaptedDataCollectionPromoteCollectionElementToCollectionRequestInternal,
        AdaptedDataCollectionPromoteDatasetToCollectionRequestInternal,
        AdaptedDataCollectionPromoteDatasetsToCollectionRequestInternal,
    ],
    Field(discriminator="adapter_type"),
]
AdaptedDataCollectionRequestInternalTypeAdapter = TypeAdapter(
    AdaptedDataCollectionRequestInternal
)  # type:ignore[var-annotated]


class DataCollectionParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_data_collection"] = "gx_data_collection"
    type: Literal["data_collection"]
    collection_type: Optional[str] = None
    extensions: List[str] = ["data"]
    value: Optional[Dict[str, Any]]

    @property
    def py_type(self) -> Type:
        return optional_if_needed(DataCollectionRequest, self.optional)

    @property
    def py_type_internal(self) -> Type:
        return optional_if_needed(DataCollectionRequestInternal, self.optional)

    @property
    def py_type_internal_json(self) -> Type:
        if self.collection_type == "list":
            return optional_if_needed(list_type(DataInternalJson), self.optional)
        elif self.collection_type:
            base_type: Optional[Type] = None
            for subtype in reversed(self.collection_type.split(":")):
                if subtype == "paired":
                    base_type = DataCollectionPaired
                elif subtype == "list":
                    if base_type is None:
                        base_type = Dict[str, DataInternalJson]
                    else:
                        base_type = Dict[str, base_type]  # type: ignore[valid-type]  # we use this at runtime to build pydantic model
                else:
                    raise Exception(f"unkown subtype '{subtype}' in collection_type '{self.collection_type}'")
        else:
            base_type = union_type(
                [list_type(DataInternalJson), DataCollectionPaired, RecursiveDataCollectionInternalJson]
            )
        assert base_type
        return optional_if_needed(base_type, self.optional)

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        if state_representation == "request":
            return allow_batching(dynamic_model_information_from_py_type(self, self.py_type))
        elif state_representation == "landing_request":
            return allow_batching(dynamic_model_information_from_py_type(self, self.py_type, requires_value=False))
        elif state_representation == "landing_request_internal":
            return allow_batching(
                dynamic_model_information_from_py_type(self, self.py_type_internal, requires_value=False)
            )
        elif state_representation in ["request_internal", "request_internal_dereferenced"]:
            return allow_batching(dynamic_model_information_from_py_type(self, self.py_type_internal))
        elif state_representation == "job_internal":
            return dynamic_model_information_from_py_type(self, self.py_type_internal, requires_value=True)
        elif state_representation == "job_runtime":
            return dynamic_model_information_from_py_type(self, self.py_type_internal_json, requires_value=True)
        elif state_representation == "workflow_step":
            return dynamic_model_information_from_py_type(self, type(None), requires_value=False)
        elif state_representation == "workflow_step_linked":
            return dynamic_model_information_from_py_type(self, ConnectedValue)
        elif state_representation == "test_case_xml":
            return dynamic_model_information_from_py_type(self, JsonTestCollectionDefDict)
        else:
            raise NotImplementedError(
                f"Have not implemented data collection parameter models for state representation {state_representation}"
            )

    @property
    def request_requires_value(self) -> bool:
        return not self.optional and self.value is None


class HiddenParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_hidden"] = "gx_hidden"
    type: Literal["hidden"]
    value: Optional[str]
    validators: List[TextCompatiableValidators] = []

    @property
    def py_type(self) -> Type:
        return optional_if_needed(StrictStr, self.optional)

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        py_type = self.py_type
        requires_value = not self.optional and self.value is None
        py_type = decorate_type_with_validators_if_needed(py_type, self.validators)
        if state_representation == "workflow_step_linked":
            py_type = allow_connected_value(py_type)
        elif state_representation == "workflow_step" and not self.optional:
            # allow it to be linked in so force allow optional...
            py_type = optional(py_type)
            requires_value = False
        if state_representation in ("job_internal", "job_runtime"):
            requires_value = True
        return dynamic_model_information_from_py_type(self, py_type, requires_value=requires_value)

    @property
    def request_requires_value(self) -> bool:
        return not self.optional and self.value is None


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
    type: Literal["color"]
    value: Optional[str] = None

    @property
    def py_type(self) -> Type:
        return optional_if_needed(StrictStr, self.optional)

    @staticmethod
    def validate_color_str(value) -> str:
        ensure_color_valid(value)
        return value

    @staticmethod
    def validate_color_str_if_value(value) -> str:
        if value:
            ensure_color_valid(value)
        return value

    @staticmethod
    def validate_color_str_or_connected_value(value) -> str:
        if not isinstance(value, ConnectedValue):
            ensure_color_valid(value)
        return value

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        py_type = self.py_type
        initialize: Any = ...
        if state_representation == "workflow_step_linked":
            py_type = allow_connected_value(py_type)
            validators = {
                "color_format": field_validator(self.name)(ColorParameterModel.validate_color_str_or_connected_value)
            }
        elif state_representation == "workflow_step":
            initialize = None
            validators = {"color_format": field_validator(self.name)(ColorParameterModel.validate_color_str_if_value)}
        else:
            validators = {"color_format": field_validator(self.name)(ColorParameterModel.validate_color_str)}
        return DynamicModelInformation(
            self.name,
            (py_type, initialize),
            validators,
        )

    @property
    def request_requires_value(self) -> bool:
        return False


class BooleanParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_boolean"] = "gx_boolean"
    type: Literal["boolean"]
    value: Optional[bool] = False
    truevalue: Optional[str] = None
    falsevalue: Optional[str] = None

    @property
    def py_type(self) -> Type:
        return optional_if_needed(StrictBool, self.optional)

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        py_type = self.py_type
        if state_representation == "workflow_step_linked":
            py_type = allow_connected_value(py_type)
        requires_value = self.request_requires_value
        if state_representation in ("job_internal", "job_runtime"):
            requires_value = True
        return dynamic_model_information_from_py_type(self, py_type, requires_value=requires_value)

    @property
    def request_requires_value(self) -> bool:
        # these parameters always have an implicit default - either None if
        # if it is optional or 'checked' if not (itself defaulting to False).
        return False


class DirectoryUriParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_directory_uri"] = "gx_directory_uri"
    type: Literal["directory"]
    validators: List[TextCompatiableValidators] = []

    @property
    def py_type(self) -> Type:
        return AnyUrl

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        py_type = self.py_type
        py_type = decorate_type_with_validators_if_needed(py_type, self.validators)
        if state_representation == "workflow_step_linked":
            py_type = allow_connected_value(py_type)
        requires_value = self.request_requires_value
        if _is_landing_request(state_representation):
            requires_value = False
        return dynamic_model_information_from_py_type(self, py_type, requires_value=requires_value)

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
    type: Literal["rules"]

    @property
    def py_type(self) -> Type:
        return RulesModel

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        return dynamic_model_information_from_py_type(self, self.py_type)

    @property
    def request_requires_value(self) -> bool:
        return True


SelectCompatiableValidators = Union[NoOptionsParameterValidatorModel,]


class SelectParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_select"] = "gx_select"
    type: Literal["select"]
    options: Optional[List[LabelValue]] = None
    multiple: bool = False
    validators: List[SelectCompatiableValidators] = []

    @staticmethod
    def split_str(cls, data: Any) -> Any:
        if isinstance(data, str):
            return [x.strip() for x in data.split(",")]

        return data

    def py_type_if_required(self, allow_connections: bool = False) -> Type:
        if self.options is not None:
            if len(self.options) > 0:
                literal_options: List[Type] = [cast_as_type(Literal[o.value]) for o in self.options]
                py_type = union_type(literal_options)
            else:
                py_type = type(None)
        else:
            py_type = StrictStr
        if self.multiple:
            if allow_connections:
                py_type = list_type(allow_connected_value(py_type))
            else:
                py_type = list_type(py_type)
        elif allow_connections:
            py_type = allow_connected_value(py_type)
        return py_type

    @property
    def py_type(self) -> Type:
        return optional_if_needed(self.py_type_if_required(), self.optional or self.multiple)

    @property
    def py_type_workflow_step(self) -> Type:
        # this is always optional in this context
        return optional(self.py_type_if_required())

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        validators = {}
        requires_value = self.request_requires_value
        py_type = None
        if state_representation == "workflow_step":
            py_type = self.py_type_workflow_step
        elif state_representation == "workflow_step_linked":
            py_type = self.py_type_if_required(allow_connections=True)
            py_type = optional_if_needed(py_type, self.optional or self.multiple)
        elif state_representation == "test_case_xml":
            # in a YAML test case representation this can be string, in XML we are still expecting a comma separated string
            py_type = self.py_type_if_required(allow_connections=False)
            if self.multiple:
                validators = {"from_string": field_validator(self.name, mode="before")(SelectParameterModel.split_str)}
            py_type = optional_if_needed(py_type, self.optional)
        elif state_representation in ("job_internal", "job_runtime"):
            requires_value = True
            py_type = self.py_type
        else:
            py_type = self.py_type

        py_type = decorate_type_with_validators_if_needed(py_type, self.validators)
        return dynamic_model_information_from_py_type(
            self, py_type, validators=validators, requires_value=requires_value
        )

    @property
    def has_selected_static_option(self):
        return self.options is not None and any(o.selected for o in self.options)

    @property
    def default_value(self) -> Optional[str]:
        if self.options:
            for option in self.options:
                if option.selected:
                    return option.value
            # single value pick up first value
            if not self.optional:
                return self.options[0].value

        return None

    @property
    def request_requires_value(self) -> bool:
        # API will allow an empty value and just grab the first static option
        # see API Tests -> test_tools.py -> test_select_first_by_default
        # If it is multiple - it will also always just allow null regardless of
        # optional - see test_select_multiple_null_handling
        return False

    @property
    def dynamic_options(self) -> bool:
        return self.options is None


class GenomeBuildParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_genomebuild"] = "gx_genomebuild"
    type: Literal["genomebuild"]
    multiple: bool

    @property
    def py_type(self) -> Type:
        py_type: Type = StrictStr
        if self.multiple:
            py_type = list_type(py_type)
        return optional_if_needed(py_type, self.optional)

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        requires_value = self.request_requires_value
        if state_representation in ("job_internal", "job_runtime"):
            requires_value = True
        return dynamic_model_information_from_py_type(self, self.py_type, requires_value=requires_value)

    @property
    def request_requires_value(self) -> bool:
        # it seems to always just pick values currently - an empty multiple or optional comes through as null
        # and empty single non-optional input comes through as "?"". See gx_genomebuild*.xml tools.
        return False


DrillDownHierarchyT = Literal["recurse", "exact"]


def drill_down_possible_values(
    options: List[DrillDownOptionsDict], multiple: bool, hierarchy: DrillDownHierarchyT
) -> List[str]:
    possible_values = []

    def add_value(option: str, is_leaf: bool):
        if not multiple and not is_leaf and hierarchy == "recurse":
            return
        possible_values.append(option)

    def walk_selection(option: DrillDownOptionsDict):
        child_options = option["options"]
        is_leaf = not child_options
        add_value(option["value"], is_leaf)
        if not is_leaf:
            for child_option in child_options:
                walk_selection(child_option)

    for option in options:
        walk_selection(option)

    return possible_values


class DrillDownParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_drill_down"] = "gx_drill_down"
    type: Literal["drill_down"]
    options: Optional[List[DrillDownOptionsDict]] = None
    multiple: bool
    hierarchy: DrillDownHierarchyT

    @property
    def py_type(self) -> Type:
        if self.options is not None:
            literal_options: List[Type] = [
                cast_as_type(Literal[o])
                for o in drill_down_possible_values(self.options, self.multiple, self.hierarchy)
            ]
            py_type = union_type(literal_options)
        else:
            py_type = StrictStr

        if self.multiple:
            py_type = list_type(py_type)

        return py_type

    @property
    def py_type_test_case_xml(self) -> Type:
        base_model = str
        return optional_if_needed(base_model, not self.request_requires_value)

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        py_type = self.py_type_test_case_xml if state_representation == "test_case_xml" else self.py_type
        requires_value = self.request_requires_value
        if state_representation in ("job_internal", "job_runtime"):
            requires_value = True

        return dynamic_model_information_from_py_type(self, py_type, requires_value=requires_value)

    @property
    def request_requires_value(self) -> bool:
        options = self.options
        if options:
            # if any of these are selected, they seem to serve as defaults - check out test_tools -> test_drill_down_first_by_default
            return not any_drill_down_options_selected(options)
        else:
            # I'm not sure how to handle dynamic options... they might or might not be required?
            # do we need to default to assuming they're not required?
            return False

    @property
    def default_option(self) -> Optional[str]:
        options = self.options
        if options:
            selected_options = selected_drill_down_options(options)
            if len(selected_options) > 0:
                return selected_options[0]
        return None

    @property
    def default_options(self) -> Optional[List[str]]:
        options = self.options
        if options:
            selected_options = selected_drill_down_options(options)
            return selected_options

        return None


def any_drill_down_options_selected(options: List[DrillDownOptionsDict]) -> bool:
    for option in options:
        selected = option.get("selected")
        if selected:
            return True
        child_options = option.get("options", [])
        if any_drill_down_options_selected(child_options):
            return True

    return False


def selected_drill_down_options(options: List[DrillDownOptionsDict]) -> List[str]:
    selected_options: List[str] = []
    for option in options:
        selected = option.get("selected")
        value = option.get("value")
        if selected and value:
            selected_options.append(value)
        child_options = option.get("options", [])
        selected_options.extend(selected_drill_down_options(child_options))

    return selected_options


class DataColumnParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_data_column"] = "gx_data_column"
    type: Literal["data_column"]
    multiple: bool
    value: Optional[Union[int, List[int]]] = None

    @staticmethod
    def split_str(cls, data: Any) -> Any:
        if isinstance(data, str):
            return [int(x.strip()) for x in data.split(",")]
        elif isinstance(data, int):
            return [data]

        return data

    @property
    def py_type(self) -> Type:
        py_type: Type = StrictInt
        if self.multiple:
            py_type = list_type(py_type)
        return optional_if_needed(py_type, self.optional)

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        if state_representation == "test_case_xml":
            if self.multiple:
                validators = {
                    "from_string": field_validator(self.name, mode="before")(DataColumnParameterModel.split_str)
                }
            else:
                validators = {}
            requires_value = self.request_requires_value
            return dynamic_model_information_from_py_type(
                self, self.py_type, validators=validators, requires_value=requires_value
            )
        else:
            requires_value = self.request_requires_value
            if state_representation in ("job_internal", "job_runtime"):
                requires_value = True
            return dynamic_model_information_from_py_type(self, self.py_type, requires_value=requires_value)

    @property
    def request_requires_value(self) -> bool:
        return self.multiple and not (self.optional or self.value)


class GroupTagParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_group_tag"] = "gx_group_tag"
    type: Literal["group_tag"]
    multiple: bool

    @property
    def py_type(self) -> Type:
        py_type: Type = StrictStr
        if self.multiple:
            py_type = list_type(py_type)
        return optional_if_needed(py_type, self.optional)

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        requires_value = self.request_requires_value
        if state_representation in ("job_internal", "job_runtime"):
            requires_value = True
        return dynamic_model_information_from_py_type(self, self.py_type, requires_value=requires_value)

    @property
    def request_requires_value(self) -> bool:
        return not self.optional


class BaseUrlParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_baseurl"] = "gx_baseurl"
    type: Literal["baseurl"]

    @property
    def py_type(self) -> Type:
        return HttpUrl

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        return dynamic_model_information_from_py_type(self, self.py_type)

    @property
    def request_requires_value(self) -> bool:
        return True


DiscriminatorType = Union[bool, str]


def cond_test_parameter_default_value(
    test_parameter: Union["BooleanParameterModel", "SelectParameterModel"],
) -> Optional[DiscriminatorType]:
    default_value: Optional[DiscriminatorType] = None
    if isinstance(test_parameter, BooleanParameterModel):
        default_value = test_parameter.value
    elif isinstance(test_parameter, SelectParameterModel):
        select_default_value = test_parameter.default_value
        if select_default_value is not None:
            default_value = select_default_value
    return default_value


class ConditionalWhen(StrictModel):
    discriminator: DiscriminatorType
    parameters: List["ToolParameterT"]
    is_default_when: bool


class ConditionalParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_conditional"] = "gx_conditional"
    type: Literal["conditional"]
    test_parameter: Union[BooleanParameterModel, SelectParameterModel]
    whens: List[ConditionalWhen]

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        is_boolean = isinstance(self.test_parameter, BooleanParameterModel)
        test_param_name = self.test_parameter.name
        test_info = self.test_parameter.pydantic_template(state_representation)
        extra_validators = test_info.validators
        if state_representation in ("job_internal", "job_runtime"):
            test_parameter_requires_value = True
        else:
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
            tag = str(discriminator) if not is_boolean else str(discriminator).lower()
            extra_kwd = {test_param_name: (Literal[when.discriminator], initialize_test)}
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
                        Tag(tag),
                    ],
                )
            )
            # job_internal requires parameters are filled in - so don't allow the absent branch
            # here that most other state representations allow
            if state_representation not in ("job_internal", "job_runtime"):
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

        def model_x_discriminator(v: Any) -> Optional[str]:
            # returning None causes a validation error, this is what we would want if
            # if the conditional state is not a dictionary.
            if not isinstance(v, dict):
                return None
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

        py_type: Type

        if len(when_types) > 1:
            cond_type = union_type(when_types)

            class ConditionalType(RootModel):
                root: cond_type = Field(..., discriminator=Discriminator(model_x_discriminator))  # type: ignore[valid-type]

            if default_type is not None:
                initialize_cond = None
            else:
                initialize_cond = ...

            py_type = ConditionalType

        else:
            py_type = when_types[0]
            # a better check here would be if any of the parameters below this have a required value,
            # in the case of job_internal though this is correct
            if state_representation in ("job_internal", "job_runtime"):
                initialize_cond = ...
            else:
                initialize_cond = None

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
    type: Literal["repeat"]
    parameters: List["ToolParameterT"]
    min: Optional[int] = None
    max: Optional[int] = None

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        # Maybe validators for min and max...
        instance_class: Type[BaseModel] = create_field_model(
            self.parameters, f"Repeat_{self.name}", state_representation
        )
        min_length = self.min
        max_length = self.max
        requires_value = self.request_requires_value
        if state_representation in ("job_internal", "job_runtime"):
            requires_value = True
        elif _is_landing_request(state_representation):
            requires_value = False
            min_length = 0  # in a landing request - parameters can be partially filled

        initialize_repeat: Any
        if requires_value:
            initialize_repeat = ...
        else:
            initialize_repeat = None

        class RepeatType(RootModel):
            root: List[instance_class] = Field(initialize_repeat, min_length=min_length, max_length=max_length)  # type: ignore[valid-type]

        return DynamicModelInformation(
            self.name,
            (RepeatType, initialize_repeat),
            {},
        )

    @property
    def request_requires_value(self) -> bool:
        if self.min is None or self.min == 0:
            return False
        # so we know we need at least one value, but maybe none of the parameters in the list
        # are required
        for parameter in self.parameters:
            if parameter.request_requires_value:
                return True
        return False


class SectionParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_section"] = "gx_section"
    type: Literal["section"]
    parameters: List["ToolParameterT"]

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        instance_class: Type[BaseModel] = create_field_model(
            self.parameters, f"Section_{self.name}", state_representation
        )
        requires_value = self.request_requires_value
        if state_representation in ("job_internal", "job_runtime"):
            requires_value = True
        if requires_value:
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
    DataColumnParameterModel,
    DirectoryUriParameterModel,
    RulesParameterModel,
    DrillDownParameterModel,
    GroupTagParameterModel,
    BaseUrlParameterModel,
    GenomeBuildParameterModel,
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


class GalaxyToolParameterModel(RootModel):
    root: GalaxyParameterT = Field(..., discriminator="type")


ConditionalWhen.model_rebuild()
ConditionalParameterModel.model_rebuild()
RepeatParameterModel.model_rebuild()
CwlUnionParameterModel.model_rebuild()


class ToolParameterBundle(Protocol):
    """An object having a dictionary of input models (i.e. a 'Tool')"""

    parameters: List[ToolParameterT]


class ToolParameterBundleModel(BaseModel):
    parameters: List[ToolParameterT]


def to_simple_model(input_parameter: Union[ToolParameterModel, ToolParameterT]) -> ToolParameterT:
    if input_parameter.__class__ == ToolParameterModel:
        assert isinstance(input_parameter, ToolParameterModel)
        return input_parameter.root
    else:
        return cast(ToolParameterT, input_parameter)


def simple_input_models(parameters: Union[List[ToolParameterModel], List[ToolParameterT]]) -> Iterable[ToolParameterT]:
    return [to_simple_model(m) for m in parameters]


def create_model_strict(*args, **kwd) -> Type[BaseModel]:
    # proteted_namespaces here prevents tool with model_ parameter names from issueing warnings
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    return create_model(*args, __config__=model_config, **kwd)


def create_model_factory(state_representation: StateRepresentationT):

    def create_method(tool: ToolParameterBundle, name: Optional[str] = None) -> Type[BaseModel]:
        return create_field_model(tool.parameters, name or DEFAULT_MODEL_NAME, state_representation)

    return create_method


create_request_model = create_model_factory("request")
create_request_internal_model = create_model_factory("request_internal")
create_request_internal_dereferenced_model = create_model_factory("request_internal_dereferenced")
create_landing_request_model = create_model_factory("landing_request")
create_landing_request_internal_model = create_model_factory("landing_request_internal")
create_job_internal_model = create_model_factory("job_internal")
create_job_runtime_model = create_model_factory("job_runtime")
create_test_case_model = create_model_factory("test_case_xml")
create_workflow_step_model = create_model_factory("workflow_step")
create_workflow_step_linked_model = create_model_factory("workflow_step_linked")


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
        pydantic_request_template = input_model.pydantic_template(state_representation)
        input_name = pydantic_request_template.name
        kwd[input_name] = pydantic_request_template.definition
        input_validators = pydantic_request_template.validators
        for validator_name, validator_callable in input_validators.items():
            model_validators[f"{input_name}_{validator_name}"] = validator_callable

    pydantic_model = create_model_strict(name, __validators__=model_validators, **kwd)
    return pydantic_model


def _is_landing_request(state_representation: StateRepresentationT):
    return state_representation in ["landing_request", "landing_request_internal"]
