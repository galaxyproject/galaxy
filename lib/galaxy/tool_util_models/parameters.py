# attempt to model requires_value...
# conditional can descend...
import builtins
from abc import abstractmethod
from collections.abc import (
    Callable,
    Iterable,
    Iterator,
    Mapping,
    Sequence,
)
from functools import lru_cache
from typing import (
    Annotated,
    Any,
    cast,
    get_args,
    Literal,
    NamedTuple,
    TypeAlias,
    TypeVar,
    Union,
)

import annotated_types
from pydantic import (
    AfterValidator,
    AliasChoices,
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
from pydantic_extra_types.color import Color
from typing_extensions import (
    Protocol,
)

from ._base import ToolSourceBaseModel
from ._types import (
    dict_type,
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
from .sample_sheet import (
    SampleSheetColumnDefinitions,
    SampleSheetRow,
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
    "relaxed_request",
    "request",
    "request_internal",
    "request_internal_dereferenced",
    "landing_request",
    "landing_request_internal",
    "job_runtime",
    "job_internal",
    "test_case_xml",
    "test_case_json",
    "workflow_step",
    "workflow_step_linked",
]

DEFAULT_MODEL_NAME = "DynamicModelForTool"
RawStateDict = dict[str, Any]


# could be made more specific - validators need to be classmethod
ValidatorDictT = dict[str, Callable]


class DynamicModelInformation(NamedTuple):
    name: str
    definition: tuple
    validators: ValidatorDictT


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConnectedValue(BaseModel):
    discriminator: Literal["ConnectedValue"] = Field(alias="__class__")


def allow_connected_value(type_: type) -> type:
    return union_type([type_, ConnectedValue])


def allow_batching(job_template: DynamicModelInformation, batch_type: type | None = None) -> DynamicModelInformation:
    job_py_type = job_template.definition[0]
    default_value = job_template.definition[1]
    batch_type = batch_type or job_py_type

    class BatchRequest(StrictModel):
        meta_class: Literal["Batch"] = Field(..., alias="__class__")
        values: list[batch_type]  # type: ignore[valid-type]
        linked: bool | None = None  # maybe True instead?

    request_type = job_py_type | BatchRequest

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

    def field_kwargs(self) -> dict[str, Any]:
        """Return kwargs for pydantic Field() including json_schema_extra metadata."""
        ...


def safe_field_name(name: str) -> str:
    if name.startswith("_"):
        return f"X{name}"
    return name


def _label_value_dicts(options: list[Any]) -> list[dict[str, Any]]:
    return [{"label": o.label, "value": o.value, "selected": o.selected} for o in options]


_UNSET: Any = object()


def dynamic_model_information_from_py_type(
    param_model: ParamModel,
    py_type: type,
    requires_value: bool | None = None,
    validators: dict[str, Any] | None = None,
    extra_json_schema: dict[str, Any] | None = None,
    default: Any = _UNSET,
) -> DynamicModelInformation:
    name = safe_field_name(param_model.name)
    if default is not _UNSET:
        initialize = default
        requires_value = False
    else:
        if requires_value is None:
            requires_value = param_model.request_requires_value
        initialize = ... if requires_value else None
    py_type_is_optional = is_optional(py_type)
    validators = validators or {}
    if not py_type_is_optional and not requires_value:
        validators["not_null"] = field_validator(name)(Validators.validate_not_none)

    field_kwargs = param_model.field_kwargs()
    if extra_json_schema:
        field_kwargs.setdefault("json_schema_extra", {}).update(extra_json_schema)
    return DynamicModelInformation(
        name,
        (py_type, Field(initialize, alias=param_model.name if param_model.name != name else None, **field_kwargs)),
        validators,
    )


# We probably need incoming (parameter def) and outgoing (parameter value as transmitted) models,
# where value in the incoming model means "default value" and value in the outgoing model is the actual
# value a user has set. (incoming/outgoing from the client perspective).
class BaseToolParameterModelDefinition(ToolSourceBaseModel):
    name: Annotated[
        str,
        Field(description="Parameter name. Used when referencing parameter in workflows or inside command templating."),
    ]
    parameter_type: str

    @abstractmethod
    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        """Return info needed to build Pydantic model at runtime for validation."""

    def field_kwargs(self) -> dict[str, Any]:
        """Return kwargs for pydantic Field() including json_schema_extra metadata."""
        return {"json_schema_extra": {"gx_type": self.parameter_type}}


class BaseGalaxyToolParameterModelDefinition(BaseToolParameterModelDefinition):
    hidden: bool = False
    label: Annotated[
        str | None, Field(description="Will be displayed on the tool page as the label of the parameter.")
    ] = None
    help: Annotated[
        str | None,
        Field(
            description="Short bit of text, rendered on the tool form just below the associated field to provide information about the field."
        ),
    ] = None
    argument: Annotated[
        str | None,
        Field(
            description="""If the parameter reflects just one command line argument of a certain tool, this tag should be set to that particular argument. It is rendered in parenthesis after the help section, and it will create the name attribute (if not given explicitly) from the argument attribute by stripping leading dashes and replacing all remaining dashes by underscores (e.g. if argument="--long-parameter" then name="long_parameter" is implicit)."""
        ),
    ] = None
    is_dynamic: bool = False
    optional: Annotated[bool, Field(description="If `false`, parameter must have a value.")] = False

    def field_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        if self.label:
            kwargs["title"] = self.label
        description_parts = []
        if self.help:
            description_parts.append(self.help)
        if self.argument:
            description_parts.append(f"({self.argument})")
        if description_parts:
            kwargs["description"] = " ".join(description_parts)
        kwargs["json_schema_extra"] = {"gx_type": self.parameter_type}
        return kwargs


class LabelValue(BaseModel):
    label: str
    value: str
    selected: bool


TextCompatiableValidators: TypeAlias = (
    LengthParameterValidatorModel
    | RegexParameterValidatorModel
    | ExpressionParameterValidatorModel
    | EmptyFieldParameterValidatorModel
)


def pydantic_to_galaxy_type(value: Any) -> Any:
    """We use advanced Pydantic types like URL but the Galaxy validators only expect strings for these."""
    if isinstance(value, AnyUrl):
        return str(value)

    return value


VT = TypeVar("VT", bound=StaticValidatorModel)


def _json_schema_annotations_for(static_validator_models: Sequence[VT]) -> list[Any]:
    """Extract JSON Schema-representable constraint annotations from validators.

    Non-negated in_range and length validators have direct annotated_types
    equivalents that Pydantic emits as JSON Schema keywords. Regex is handled
    separately via json_schema_extra since StringConstraints is incompatible
    with non-string types (e.g. AnyUrl).
    """
    annotations: list[Any] = []
    for v in static_validator_models:
        if isinstance(v, InRangeParameterValidatorModel) and not v.negate:
            if v.min is not None:
                annotations.append(annotated_types.Gt(v.min) if v.exclude_min else annotated_types.Ge(v.min))
            if v.max is not None:
                annotations.append(annotated_types.Lt(v.max) if v.exclude_max else annotated_types.Le(v.max))
        elif isinstance(v, LengthParameterValidatorModel) and not v.negate:
            if v.min is not None:
                annotations.append(annotated_types.MinLen(v.min))
            if v.max is not None:
                annotations.append(annotated_types.MaxLen(v.max))
    return annotations


def _json_schema_extra_for_validators(validators: Sequence[VT]) -> dict[str, Any]:
    """Extract JSON Schema keywords for validators best handled via json_schema_extra.

    Regex pattern is emitted here rather than as a type annotation because
    StringConstraints is incompatible with non-string types like AnyUrl.
    Negated length uses ``not: {minLength, maxLength}`` since the non-negated
    form is handled by annotated_types.
    """
    extra: dict[str, Any] = {}
    for v in validators:
        if isinstance(v, RegexParameterValidatorModel) and not v.negate:
            pattern = v.expression
            # Python re.match anchors at start; JSON Schema pattern does not
            if not pattern.startswith("^"):
                pattern = "^" + pattern
            extra["pattern"] = pattern
            break
    for v in validators:
        if isinstance(v, LengthParameterValidatorModel) and v.negate:
            not_constraint: dict[str, Any] = {}
            if v.min is not None:
                not_constraint["minLength"] = v.min
            if v.max is not None:
                not_constraint["maxLength"] = v.max
            if not_constraint:
                extra["not"] = not_constraint
            break
    return extra


def decorate_type_with_validators_if_needed(
    py_type: type, static_validator_models: Sequence[VT], optional: bool = False
) -> type:
    pydantic_validator = pydantic_validator_for(static_validator_models, optional=optional)
    json_schema_annotations = _json_schema_annotations_for(static_validator_models)
    all_annotations = json_schema_annotations[:]
    if pydantic_validator:
        all_annotations.append(pydantic_validator)
    if all_annotations:
        return expand_annotation(py_type, all_annotations)
    return py_type


# Looks like Annotated only work with one PlainValidator so condensing all static validators
# into a single PlainValidator for pydantic.
def pydantic_validator_for(static_validator_models: Sequence[VT], optional: bool = False) -> AfterValidator | None:

    if static_validator_models:

        def validator(v: Any) -> Any:
            if optional and (v is None or v == ""):
                return v

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
    default_value: str | None = Field(default=None, alias="value")
    default_options: list[LabelValue] = []
    validators: list[TextCompatiableValidators] = []

    def field_kwargs(self) -> dict[str, Any]:
        kwargs = super().field_kwargs()
        extra = kwargs["json_schema_extra"]
        extra["gx_area"] = self.area
        if self.default_options:
            extra["gx_default_options"] = _label_value_dicts(self.default_options)
        return kwargs

    @property
    def py_type(self) -> builtins.type:
        return optional_if_needed(StrictStr, self.optional)

    @property
    def py_type_relaxed_request(self) -> builtins.type:
        # such a hack but explicit nulls are always allowed in the API even for non-optional
        # parameters - it becomes "" in the internal state.
        return optional(StrictStr)

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        py_type = self.py_type
        if state_representation == "relaxed_request":
            py_type = self.py_type_relaxed_request
        py_type = decorate_type_with_validators_if_needed(py_type, self.validators, optional=self.optional)
        if state_representation == "workflow_step_linked":
            py_type = allow_connected_value(py_type)
        requires_value = self.request_requires_value
        if state_representation in ("job_internal", "job_runtime"):
            requires_value = True
        return dynamic_model_information_from_py_type(
            self,
            py_type,
            requires_value=requires_value,
            extra_json_schema=_json_schema_extra_for_validators(self.validators),
        )

    @property
    def request_requires_value(self) -> bool:
        return False


NumberCompatiableValidators: TypeAlias = InRangeParameterValidatorModel


class IntegerParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_integer"] = "gx_integer"
    type: Literal["integer"]
    optional: bool = False
    value: int | None = None
    min: int | None = None
    max: int | None = None
    validators: list[NumberCompatiableValidators] = []

    def field_kwargs(self) -> dict[str, Any]:
        kwargs = super().field_kwargs()
        extra = kwargs["json_schema_extra"]
        if self.min is not None:
            extra["gx_min"] = self.min
        if self.max is not None:
            extra["gx_max"] = self.max
        return kwargs

    @property
    def py_type(self) -> builtins.type:
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


_INFINITY_SENTINEL = "__Infinity__"
_NEG_INFINITY_SENTINEL = "__-Infinity__"


def _convert_infinity_sentinel(v: Any) -> Any:
    """Convert Galaxy JSON sentinel strings for infinity back to Python floats.

    Galaxy's custom JSON encoder (galaxy.util.json.safe_dumps) serializes
    float('inf') as '__Infinity__' and float('-inf') as '__-Infinity__' to
    produce valid JSON.  When these sentinel values appear in deserialized
    parameter dicts (e.g. from GET /api/tools/{id}/test_data) Pydantic must
    accept them as valid float input.
    """
    if v == _INFINITY_SENTINEL:
        return float("inf")
    elif v == _NEG_INFINITY_SENTINEL:
        return float("-inf")
    return v


class FloatParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_float"] = "gx_float"
    type: Literal["float"]
    value: float | None = None
    min: float | None = None
    max: float | None = None
    validators: list[NumberCompatiableValidators] = []

    @field_validator("value", "min", "max", mode="before")
    @classmethod
    def convert_infinity_sentinels(cls, v: Any) -> Any:
        return _convert_infinity_sentinel(v)

    def field_kwargs(self) -> dict[str, Any]:
        kwargs = super().field_kwargs()
        extra = kwargs["json_schema_extra"]
        if self.min is not None:
            extra["gx_min"] = self.min
        if self.max is not None:
            extra["gx_max"] = self.max
        return kwargs

    @property
    def py_type(self) -> builtins.type:
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
        # Convert Galaxy JSON sentinel strings ("__Infinity__", "__-Infinity__") to Python floats
        # before Pydantic validates the field. These sentinels appear when float('inf') values are
        # round-tripped through Galaxy's safe_dumps/json.loads path (e.g. GET /api/tools/{id}/test_data).
        dynamic_validators: dict[str, Any] = {
            "infinity_sentinel": field_validator(safe_field_name(self.name), mode="before")(_convert_infinity_sentinel)
        }
        return dynamic_model_information_from_py_type(
            self, py_type, requires_value=requires_value, validators=dynamic_validators
        )

    @property
    def request_requires_value(self) -> bool:
        return False


# External collection source type. ``dce`` is accepted because a job that maps
# over a nested collection (e.g. subcollection mapping over a ``list:paired``)
# records its input as a ``DatasetCollectionElement``; rerunning such a job
# resubmits that ``dce`` reference through the request model.
CollectionSrcT = Literal["hdca", "dce"]
# Internal collection source type - includes dce for subcollection mapping
CollectionInternalSrcT = Literal["hdca", "dce"]


class LegacyRequestModelAttributes(StrictModel):
    # Here for bioblend's sake, should be stripped
    map_over_type: SkipJsonSchema[str | None] = Field(None, exclude=True)
    hid: SkipJsonSchema[int | None] = Field(None, exclude=True)
    workflow_step_id: SkipJsonSchema[str | None] = Field(None, exclude=True)
    label: SkipJsonSchema[str | None] = Field(None, exclude=True)


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


class DataRequestDce(LegacyRequestModelAttributes):
    src: Literal["dce"] = "dce"
    id: StrictStr


class FileHash(StrictModel):
    hash_function: Literal["MD5", "SHA-1", "SHA-256", "SHA-512"]
    hash_value: StrictStr


class BaseDataRequest(StrictModel):
    url: StrictStr = Field(..., alias="location", validation_alias=AliasChoices("url", "location"))
    name: StrictStr | None = None
    ext: StrictStr
    dbkey: StrictStr = "?"
    deferred: StrictBool = False
    created_from_basename: StrictStr | None = None
    info: StrictStr | None = None
    tags: list[str] | None = None
    hashes: list[FileHash] | None = None
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
    identifier: StrictStr = Field(
        ...,
        description="A unique identifier for this element within the collection.",
        validation_alias=AliasChoices("identifier", "name"),
    )


class CollectionElementCollectionRequestUri(StrictModel):
    class_: Literal["Collection"] = Field(..., alias="class")
    identifier: StrictStr = Field(
        ...,
        description="A unique identifier for this element within the collection.",
        validation_alias=AliasChoices("identifier", "name"),
    )
    collection_type: StrictStr
    elements: list["CollectionRequestUriElement"]

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


def _collection_element_discriminator(value: Any) -> str | None:
    if isinstance(value, dict):
        return value.get("class") or value.get("class_")
    return getattr(value, "class_", None)


# A callable Discriminator avoids the PydanticJsonSchemaWarning emitted for
# the recursive Field(discriminator="class_") on this self-referential union;
# json_schema_extra restores the OpenAPI discriminator metadata.
CollectionRequestUriElement = Annotated[
    Annotated[CollectionElementCollectionRequestUri, Tag("Collection")]
    | Annotated[CollectionElementDataRequestUri, Tag("File")],
    Discriminator(_collection_element_discriminator),
    Field(
        json_schema_extra={
            "discriminator": {
                "propertyName": "class",
                "mapping": {
                    "Collection": "#/components/schemas/CollectionElementCollectionRequestUri",
                    "File": "#/components/schemas/CollectionElementDataRequestUri",
                },
            }
        }
    ),
]


class DataRequestCollectionUri(StrictModel):
    class_: Literal["Collection"] = Field(..., alias="class")
    collection_type: str
    elements: list[CollectionRequestUriElement]
    deferred: StrictBool = False
    name: StrictStr | None = None
    src: None = Field(None, exclude=True)
    # Sample sheet metadata
    column_definitions: SampleSheetColumnDefinitions | None = None
    rows: dict[str, SampleSheetRow] | None = None


_DataRequest = Annotated[
    DataRequestHda | DataRequestLdda | DataRequestLd | DataRequestDce | DataRequestUri, Field(discriminator="src")
]
DataRequest: type = cast(type, _DataRequest)

DataOrCollectionRequest = _DataRequest | FileRequestUri | DataRequestCollectionUri | DataRequestHdca
FileOrCollectionRequest = Annotated[FileRequestUri | DataRequestCollectionUri, Field(discriminator="class_")]

DataRequestHda.model_rebuild()
DataRequestLd.model_rebuild()
DataRequestLdda.model_rebuild()
DataRequestDce.model_rebuild()
DataRequestUri.model_rebuild()
DataRequestHdca.model_rebuild()
CollectionElementCollectionRequestUri.model_rebuild()
DataRequestCollectionUri.model_rebuild()

DataOrCollectionRequestAdapter: TypeAdapter[DataOrCollectionRequest] = TypeAdapter(DataOrCollectionRequest)


class BatchDataHdcaInstance(StrictModel):
    src: Literal["hdca"]
    id: StrictStr
    map_over_type: str | None = None


class BatchDataDceInstance(StrictModel):
    src: Literal["dce"]
    id: StrictStr
    map_over_type: str | None = None


class BatchDataNonCollectionInstance(StrictModel):
    src: Literal["hda", "ldda"]
    id: StrictStr


BatchDataInstance: type = cast(
    type,
    Annotated[
        BatchDataHdcaInstance | BatchDataDceInstance | BatchDataNonCollectionInstance, Field(discriminator="src")
    ],
)


def multi_data_discriminator(v: Any) -> str:
    if isinstance(v, dict):
        src = v.get("src", None)
        clazz = v.get("class", None)
        if clazz == "Collection":
            return "data_request_collection_uri"
        elif src == "hda":
            return "data_request_hda"
        elif src == "ldda":
            return "data_request_ldda"
        elif src == "hdca":
            return "data_request_hdca"
        elif src == "dce":
            return "data_request_dce"
        elif src == "url":
            return "data_request_uri"
    return ""


def tag(field: type, tag: str) -> type:
    return Annotated[field, Tag(tag)]  # type: ignore[return-value]


MultiDataInstanceDiscriminator = Discriminator(multi_data_discriminator)
MultiDataInstance = cast(
    type,
    Annotated[
        tag(DataRequestHda, "data_request_hda")
        | tag(DataRequestLdda, "data_request_ldda")
        | tag(DataRequestHdca, "data_request_hdca")
        | tag(DataRequestDce, "data_request_dce")
        | tag(DataRequestUri, "data_request_uri")
        | tag(DataRequestCollectionUri, "data_request_collection_uri"),
        Field(discriminator=MultiDataInstanceDiscriminator),
    ],
)
MultiDataRequest = union_type([MultiDataInstance, list_type(MultiDataInstance)])


class DataRequestInternalHda(StrictModel):
    src: Literal["hda"]
    id: StrictInt


class DataRequestInternalLdda(StrictModel):
    src: Literal["ldda"]
    id: StrictInt


class DataRequestInternalHdca(StrictModel):
    src: Literal["hdca"]
    id: StrictInt


class DataRequestInternalDce(StrictModel):
    src: Literal["dce"]
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
    listing: list[str] | None = None  # Should be recursive
    nameroot: Annotated[str | None, Field(description="The basename root such that nameroot + nameext == basename")]
    nameext: Annotated[str | None, Field(description="The basename extension such that nameroot + nameext == basename")]
    format: Annotated[str, Field(description="The datatype extension of the file, e.g. 'txt', 'bam', 'fastq.gz'.")]
    # "secondaryFiles": List[Any],
    checksum: str | None = None
    size: int
    # When a gx_data param receives a DCE (subcollection mapping), preserve element_identifier
    # for output naming and collection traceability
    element_identifier: str | None = None


class DataCollectionElementInternalJson(DataInternalJson):
    """A file within a collection element - adds collection-specific metadata."""

    element_identifier: str
    columns: list[Any] | None = None  # for sample_sheet elements


# Collection runtime models with metadata
class DataCollectionInternalJsonBase(StrictModel):
    """Base model for collection runtime representations with metadata."""

    class_: Annotated[Literal["Collection"], Field(alias="class")]
    name: str | None  # None for raw DatasetCollection inputs
    collection_type: str
    elements: Any
    tags: list[str] = []
    # Special metadata fields (optional, type-dependent)
    column_definitions: list[dict[str, Any]] | None = None  # for sample_sheet
    fields: list[dict[str, Any]] | None = None  # for record
    has_single_item: bool | None = None  # for paired_or_unpaired
    columns: list[Any] | None = None  # for sample_sheet elements

    model_config = ConfigDict(populate_by_name=True)


class DataCollectionPairedElements(StrictModel):
    forward: DataCollectionElementInternalJson
    reverse: DataCollectionElementInternalJson


class DataCollectionPairedRuntime(DataCollectionInternalJsonBase):
    """Paired collection runtime representation."""

    collection_type: Literal["paired"]
    elements: DataCollectionPairedElements


class DataCollectionListRuntime(DataCollectionInternalJsonBase):
    """List collection runtime representation."""

    collection_type: Literal["list"]
    elements: list[DataCollectionElementInternalJson]


class DataCollectionSampleSheetRuntime(DataCollectionInternalJsonBase):
    """Sample sheet collection runtime representation."""

    collection_type: Literal["sample_sheet"]
    elements: list[DataCollectionElementInternalJson]


class DataCollectionRecordRuntime(DataCollectionInternalJsonBase):
    """Record collection runtime representation."""

    collection_type: Literal["record"]
    elements: dict[
        str,
        Union[
            DataCollectionElementInternalJson, "DataCollectionNestedListRuntime", "DataCollectionNestedRecordRuntime"
        ],
    ]


class DataCollectionPairedOrUnpairedRuntime(DataCollectionInternalJsonBase):
    """Paired or Unpaired collection runtime representation."""

    collection_type: Literal["paired_or_unpaired"]
    elements: dict[str, DataCollectionElementInternalJson]


class DataCollectionNestedListRuntime(DataCollectionInternalJsonBase):
    """Nested collection with list-like outer structure (list:*, sample_sheet:*)."""

    @field_validator("collection_type")
    @classmethod
    def must_be_nested_list_like(cls, v: str) -> str:
        if ":" not in v:
            raise ValueError(f'Nested collection_type must contain ":", got "{v}"')
        first_segment = v.split(":")[0]
        if first_segment not in ("list", "sample_sheet"):
            raise ValueError(f'Outer type must be list-like (list, sample_sheet), got "{first_segment}"')
        return v

    elements: list[
        Union[
            "DataCollectionListRuntime",
            "DataCollectionSampleSheetRuntime",
            "DataCollectionPairedRuntime",
            "DataCollectionRecordRuntime",
            "DataCollectionPairedOrUnpairedRuntime",
            "DataCollectionNestedListRuntime",
            "DataCollectionNestedRecordRuntime",
        ]
    ]


class DataCollectionNestedRecordRuntime(DataCollectionInternalJsonBase):
    """Nested collection with record-like outer structure (paired:*, record:*)."""

    @field_validator("collection_type")
    @classmethod
    def must_be_nested_record_like(cls, v: str) -> str:
        if ":" not in v:
            raise ValueError(f'Nested collection_type must contain ":", got "{v}"')
        first_segment = v.split(":")[0]
        if first_segment in ("list", "sample_sheet"):
            raise ValueError(f'Outer type must be record-like, got list-like "{first_segment}"')
        return v

    elements: dict[
        str,
        Union[
            DataCollectionElementInternalJson,
            "DataCollectionListRuntime",
            "DataCollectionSampleSheetRuntime",
            "DataCollectionPairedRuntime",
            "DataCollectionRecordRuntime",
            "DataCollectionPairedOrUnpairedRuntime",
            "DataCollectionNestedListRuntime",
            "DataCollectionNestedRecordRuntime",
        ],
    ]


DataCollectionNestedListRuntime.model_rebuild()
DataCollectionNestedRecordRuntime.model_rebuild()


_LEAF_COLLECTION_MODELS: dict[str, type[Any]] = {
    "list": DataCollectionListRuntime,
    "paired": DataCollectionPairedRuntime,
    "record": DataCollectionRecordRuntime,
    "paired_or_unpaired": DataCollectionPairedOrUnpairedRuntime,
    "sample_sheet": DataCollectionSampleSheetRuntime,
}


@lru_cache(maxsize=128)
def build_collection_model_for_type(collection_type: str) -> type[DataCollectionInternalJsonBase] | None:
    """Dynamically generate a Pydantic model for a specific collection_type.

    Simple types -> existing static model.
    Nested types -> model with Literal[collection_type] and
    elements narrowed to exact inner model.
    Unknown single-segment types -> None (caller decides fallback).
    """
    if collection_type in _LEAF_COLLECTION_MODELS:
        return _LEAF_COLLECTION_MODELS[collection_type]

    if ":" not in collection_type:
        return None

    outer_segment, inner_type = collection_type.split(":", 1)
    inner_model = build_collection_model_for_type(inner_type)

    if inner_model is None:
        return None

    is_list_like = outer_segment in ("list", "sample_sheet")

    if is_list_like:
        elements_type = list_type(inner_model)
    else:
        elements_type = dict_type(str, inner_model)

    safe_name = f"DynamicCollection_{'_'.join(collection_type.split(':'))}"

    model = create_model(
        safe_name,
        __base__=DataCollectionInternalJsonBase,
        collection_type=(Literal[collection_type], ...),
        elements=(elements_type, ...),
    )

    return model


def _collection_type_discriminator(v: Any) -> str:
    """Return the full collection_type string for discriminated union routing.

    Used for subset unions (comma-separated types) where tags may be dynamic
    model collection_type strings like "list:paired".
    """
    if isinstance(v, dict):
        return v.get("collection_type", "")
    return getattr(v, "collection_type", "")


def collection_runtime_discriminator(v: Any) -> str:
    """Discriminator function for collection runtime unions.

    Routes validation to the correct model based on collection_type pattern.
    """
    if isinstance(v, dict):
        ct = v.get("collection_type", "")
    else:
        ct = getattr(v, "collection_type", "")

    # Simple types - exact match
    if ct == "list":
        return "list"
    elif ct == "paired":
        return "paired"
    elif ct == "record":
        return "record"
    elif ct == "paired_or_unpaired":
        return "paired_or_unpaired"
    elif ct == "sample_sheet":
        return "sample_sheet"
    elif ":" in ct:
        # Nested types - route by outer structure
        first_segment = ct.split(":")[0]
        if first_segment in ("list", "sample_sheet"):
            return "nested_list"
        else:
            return "nested_record"
    elif not ct:
        # Missing collection_type — data isn't a runtime collection dict.
        # Route to list so Pydantic fails validation with a clear schema error
        # rather than a discriminator error.
        return "list"
    else:
        raise ValueError(f"Unknown collection_type for runtime discrimination: '{ct}'")


CollectionRuntimeDiscriminated: type = cast(
    type,
    Annotated[
        Annotated[DataCollectionListRuntime, Tag("list")]
        | Annotated[DataCollectionSampleSheetRuntime, Tag("sample_sheet")]
        | Annotated[DataCollectionPairedRuntime, Tag("paired")]
        | Annotated[DataCollectionRecordRuntime, Tag("record")]
        | Annotated[DataCollectionPairedOrUnpairedRuntime, Tag("paired_or_unpaired")]
        | Annotated[DataCollectionNestedListRuntime, Tag("nested_list")]
        | Annotated[DataCollectionNestedRecordRuntime, Tag("nested_record")],
        Discriminator(collection_runtime_discriminator),
    ],
)


DataRequestInternal = cast(
    type,
    Annotated[
        tag(DataRequestInternalHda, "data_request_hda")
        | tag(DataRequestInternalLdda, "data_request_ldda")
        | tag(DataRequestInternalHdca, "data_request_hdca")
        | tag(DataRequestInternalDce, "data_request_dce")
        | tag(DataRequestUri, "data_request_uri")
        | tag(DataRequestCollectionUri, "data_request_collection_uri"),
        Field(discriminator=MultiDataInstanceDiscriminator),
    ],
)


class DatasetCollectionElementReference(StrictModel):
    src: Literal["dce"]
    id: StrictInt
    map_over_type: str | None = None


DataRequestInternalDereferencedT = DataRequestInternalHda | DataRequestInternalLdda | DatasetCollectionElementReference
DataRequestInternalDereferenced: type = cast(
    type,
    Annotated[DataRequestInternalDereferencedT, Field(discriminator="src")],
)

DataJobInternalT = DataRequestInternalHda | DataRequestInternalLdda | DatasetCollectionElementReference
DataJobInternal: type = cast(
    type,
    Annotated[DataJobInternalT, Field(discriminator="src")],
)


class BatchDataHdcaInstanceInternal(StrictModel):
    src: Literal["hdca"]
    id: StrictInt
    map_over_type: str | None = None


class BatchDataDceInstanceInternal(StrictModel):
    src: Literal["dce"]
    id: StrictInt
    map_over_type: str | None = None


class BatchDataNonCollectionInstanceInternal(StrictModel):
    src: Literal["hda", "ldda"]
    id: StrictInt


BatchDataInstanceInternal: type = cast(
    type,
    Annotated[
        BatchDataHdcaInstanceInternal | BatchDataDceInstanceInternal | BatchDataNonCollectionInstanceInternal,
        Field(discriminator="src"),
    ],
)


MultiDataInstanceInternal = cast(
    type,
    Annotated[
        DataRequestInternalHda
        | DataRequestInternalLdda
        | DataRequestInternalHdca
        | DataRequestInternalDce
        | DataRequestUri,
        Field(discriminator="src"),
    ],
)
MultiDataInstanceInternalDereferenced: type = cast(
    type,
    Annotated[
        DataRequestInternalHda | DataRequestInternalLdda | DataRequestInternalHdca | DataRequestInternalDce,
        Field(discriminator="src"),
    ],
)

MultiDataRequestInternal = union_type([MultiDataInstanceInternal, list_type(MultiDataInstanceInternal)])
MultiDataRequestInternalDereferenced = union_type(
    [MultiDataInstanceInternalDereferenced, list_type(MultiDataInstanceInternalDereferenced)]
)


class DataParameterModel(BaseGalaxyToolParameterModelDefinition):
    model_config = ConfigDict(populate_by_name=True)

    parameter_type: Literal["gx_data"] = "gx_data"
    type: Literal["data"]
    extensions: Annotated[
        list[str],
        Field(
            validation_alias=AliasChoices("extensions", "format"),
            description="Limit inputs to datasets with these extensions. Use 'data' to allow all input datasets.",
            examples=["txt", "tabular", "tiff"],
        ),
    ] = ["data"]
    multiple: Annotated[bool, Field(description="Allow multiple values to be selected.")] = False
    min: int | None = None
    max: int | None = None
    url_default: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _reject_extensions_and_format(cls, data):
        if isinstance(data, dict) and "extensions" in data and "format" in data:
            raise ValueError("Specify either 'extensions' or 'format', not both")
        return data

    def field_kwargs(self) -> dict[str, Any]:
        kwargs = super().field_kwargs()
        extra = kwargs["json_schema_extra"]
        extra["gx_extensions"] = self.extensions
        extra["gx_multiple"] = self.multiple
        if self.min is not None:
            extra["gx_min"] = self.min
        if self.max is not None:
            extra["gx_max"] = self.max
        return kwargs

    @property
    def py_type(self) -> builtins.type:
        base_model: type
        if self.multiple:
            base_model = MultiDataRequest
        else:
            base_model = DataRequest
        return optional_if_needed(base_model, self.optional)

    @property
    def py_type_internal_json(self) -> builtins.type:
        base_model: type
        if self.multiple:
            base_model = list_type(DataInternalJson)
        else:
            base_model = DataInternalJson
        return optional_if_needed(base_model, self.optional)

    @property
    def py_type_internal(self) -> builtins.type:
        base_model: type
        if self.multiple:
            base_model = MultiDataRequestInternal
        else:
            base_model = DataRequestInternal
        return optional_if_needed(base_model, self.optional)

    @property
    def py_type_internal_dereferenced(self) -> builtins.type:
        base_model: type
        if self.multiple:
            base_model = MultiDataRequestInternalDereferenced
        else:
            base_model = DataRequestInternalDereferenced
        return optional_if_needed(base_model, self.optional)

    @property
    def py_type_job_internal(self) -> builtins.type:
        base_model: type
        if self.multiple:
            base_model = MultiDataRequestInternalDereferenced
        else:
            base_model = DataJobInternal
        return optional_if_needed(base_model, self.optional)

    @property
    def py_type_test_case(self) -> builtins.type:
        base_model: type
        if self.multiple:
            base_model = list_type(JsonTestDatasetDefDict)
        else:
            base_model = JsonTestDatasetDefDict
        return optional_if_needed(base_model, self.optional)

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        if state_representation in ["request", "relaxed_request"]:
            requires_value = None if not self.url_default else False
            return allow_batching(
                dynamic_model_information_from_py_type(self, self.py_type, requires_value=requires_value),
                BatchDataInstance,
            )
        elif state_representation == "landing_request":
            return allow_batching(
                dynamic_model_information_from_py_type(self, self.py_type, requires_value=False), BatchDataInstance
            )
        elif state_representation == "request_internal":
            requires_value = None if not self.url_default else False
            return allow_batching(
                dynamic_model_information_from_py_type(self, self.py_type_internal, requires_value=requires_value),
                BatchDataInstanceInternal,
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
            return dynamic_model_information_from_py_type(self, self.py_type_job_internal, requires_value=True)
        elif state_representation == "job_runtime":
            return dynamic_model_information_from_py_type(self, self.py_type_internal_json, requires_value=True)
        elif state_representation in ("test_case_xml", "test_case_json"):
            if self.url_default:
                return dynamic_model_information_from_py_type(
                    self,
                    self.py_type_test_case,
                    default={"class": "File", "location": self.url_default},
                )
            return dynamic_model_information_from_py_type(self, self.py_type_test_case)
        elif state_representation == "workflow_step":
            return dynamic_model_information_from_py_type(self, type(None), requires_value=False)
        elif state_representation == "workflow_step_linked":
            return dynamic_model_information_from_py_type(self, ConnectedValue)
        else:
            raise NotImplementedError(
                f"Have not implemented data collection parameter models for state representation {state_representation}"
            )

    @property
    def request_requires_value(self) -> bool:
        return not self.optional and self.url_default is None


class DataCollectionRequest(StrictModel):
    src: CollectionSrcT
    id: StrictStr


class BatchCollectionInstance(StrictModel):
    src: CollectionSrcT
    id: StrictStr
    map_over_type: str | None = None


class BatchCollectionInstanceInternal(StrictModel):
    src: CollectionInternalSrcT
    id: StrictInt
    map_over_type: str | None = None


DataCollectionRequestOrCollectionUri: type = union_type([DataCollectionRequest, DataRequestCollectionUri])


class DataCollectionRequestInternal(StrictModel):
    """Internal request for a collection - tracks source type.

    src can be:
    - "hdca": Direct collection input (HistoryDatasetCollectionAssociation)
    - "dce": Subcollection mapping (DatasetCollectionElement)
    """

    src: CollectionInternalSrcT
    id: StrictInt


DataCollectionRequestInternalOrCollectionUri: type = union_type(
    [DataCollectionRequestInternal, DataRequestCollectionUri]
)
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
    adapting: list[AdapterElementRequest]


AdaptedDataCollectionRequest = Annotated[
    AdaptedDataCollectionPromoteDatasetToCollectionRequest | AdaptedDataCollectionPromoteDatasetsToCollectionRequest,
    Field(discriminator="adapter_type"),
]
AdaptedDataCollectionRequestTypeAdapter = TypeAdapter(AdaptedDataCollectionRequest)  # type: ignore[var-annotated]


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
    adapting: list[AdapterElementRequestInternal]


AdaptedDataCollectionRequestInternal = Annotated[
    AdaptedDataCollectionPromoteCollectionElementToCollectionRequestInternal
    | AdaptedDataCollectionPromoteDatasetToCollectionRequestInternal
    | AdaptedDataCollectionPromoteDatasetsToCollectionRequestInternal,
    Field(discriminator="adapter_type"),
]
AdaptedDataCollectionRequestInternalTypeAdapter = TypeAdapter(AdaptedDataCollectionRequestInternal)  # type: ignore[var-annotated]

DataCollectionJobInternal = cast(type, DataCollectionRequestInternal | AdaptedDataCollectionRequestInternal)


class DataCollectionParameterModel(BaseGalaxyToolParameterModelDefinition):
    model_config = ConfigDict(populate_by_name=True)

    parameter_type: Literal["gx_data_collection"] = "gx_data_collection"
    type: Literal["data_collection"]
    collection_type: str | None = None
    extensions: Annotated[
        list[str],
        Field(validation_alias=AliasChoices("extensions", "format")),
    ] = ["data"]
    value: dict[str, Any] | None

    @model_validator(mode="before")
    @classmethod
    def _reject_extensions_and_format(cls, data):
        if isinstance(data, dict) and "extensions" in data and "format" in data:
            raise ValueError("Specify either 'extensions' or 'format', not both")
        return data

    def field_kwargs(self) -> dict[str, Any]:
        kwargs = super().field_kwargs()
        kwargs["json_schema_extra"]["gx_extensions"] = self.extensions
        return kwargs

    @property
    def py_type(self) -> builtins.type:
        return optional_if_needed(DataCollectionRequestOrCollectionUri, self.optional)

    @property
    def py_type_internal(self) -> builtins.type:
        return optional_if_needed(DataCollectionRequestInternalOrCollectionUri, self.optional)

    @property
    def py_type_internal_dereferenced(self) -> builtins.type:
        return optional_if_needed(DataCollectionRequestInternal, self.optional)

    def _runtime_model_for_collection_type(self, ct: str) -> tuple:
        """Map a single collection type to its runtime model and tag.

        Returns tuple of (model, tag) for use in discriminated unions.
        Uses build_collection_model_for_type which handles both leaf and nested types
        via _LEAF_COLLECTION_MODELS lookup + recursive dynamic model generation.
        """
        if (model := build_collection_model_for_type(ct)) is not None:
            return (model, ct)
        return (None, None)

    @property
    def py_type_internal_json(self) -> builtins.type:
        # Return normalized collection runtime models with metadata
        if not self.collection_type:
            # Unknown collection_type - use full discriminated union
            return optional_if_needed(CollectionRuntimeDiscriminated, self.optional)

        # Handle comma-separated collection types (e.g., "list,paired")
        if "," in self.collection_type:
            types = [t.strip() for t in self.collection_type.split(",")]
            tagged_types: list[type] = []
            tags_seen: set = set()

            for t in types:
                model, tag_str = self._runtime_model_for_collection_type(t)
                if model and tag_str not in tags_seen:
                    tags_seen.add(tag_str)
                    tagged_types.append(cast(type, Annotated[model, Tag(tag_str)]))

            if tagged_types:
                if len(tagged_types) == 1:
                    # Single type - no union needed, unwrap Annotated to get base model
                    base_type: type = get_args(tagged_types[0])[0]
                else:
                    # Multiple types - build discriminated union
                    # Use _collection_type_discriminator which returns full collection_type,
                    # matching both simple tags ("list") and dynamic tags ("list:paired")
                    tagged_union = union_type(tagged_types)
                    base_type = cast(type, Annotated[tagged_union, Discriminator(_collection_type_discriminator)])
                return optional_if_needed(base_type, self.optional)
            # Fall through to full union if no models matched

        # Single collection type
        model, _tag = self._runtime_model_for_collection_type(self.collection_type)
        if model:
            return optional_if_needed(model, self.optional)

        raise ValueError(f"Unknown collection_type for runtime model: '{self.collection_type}'")

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        if state_representation in ["request", "relaxed_request"]:
            return allow_batching(dynamic_model_information_from_py_type(self, self.py_type), BatchCollectionInstance)
        elif state_representation == "landing_request":
            return allow_batching(
                dynamic_model_information_from_py_type(self, self.py_type, requires_value=False),
                BatchCollectionInstance,
            )
        elif state_representation == "landing_request_internal":
            return allow_batching(
                dynamic_model_information_from_py_type(self, self.py_type_internal, requires_value=False),
                BatchCollectionInstanceInternal,
            )
        elif state_representation == "request_internal":
            return allow_batching(
                dynamic_model_information_from_py_type(self, self.py_type_internal),
                BatchCollectionInstanceInternal,
            )
        elif state_representation == "request_internal_dereferenced":
            return allow_batching(
                dynamic_model_information_from_py_type(self, self.py_type_internal_dereferenced),
                BatchCollectionInstanceInternal,
            )
        elif state_representation == "job_internal":
            return dynamic_model_information_from_py_type(
                self, optional_if_needed(DataCollectionJobInternal, self.optional), requires_value=True
            )
        elif state_representation == "job_runtime":
            return dynamic_model_information_from_py_type(self, self.py_type_internal_json, requires_value=True)
        elif state_representation == "workflow_step":
            return dynamic_model_information_from_py_type(self, type(None), requires_value=False)
        elif state_representation == "workflow_step_linked":
            return dynamic_model_information_from_py_type(self, ConnectedValue)
        elif state_representation == "test_case_xml":
            return dynamic_model_information_from_py_type(self, JsonTestCollectionDefDict)
        elif state_representation == "test_case_json":
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
    value: str | None
    validators: list[TextCompatiableValidators] = []

    @property
    def py_type(self) -> builtins.type:
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


def ensure_color_valid(value: Any | None):
    if value is None:
        return
    if not isinstance(value, str):
        raise ValueError(f"Invalid color value type {value.__class__} encountered.")
    try:
        Color(value)
    except Exception as e:
        raise ValueError(f"Invalid color value {value!r}: {e}")


class ColorParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_color"] = "gx_color"
    type: Literal["color"]
    value: str | None = None

    def field_kwargs(self) -> dict[str, Any]:
        kwargs = super().field_kwargs()
        kwargs["json_schema_extra"]["format"] = "color"
        return kwargs

    @property
    def py_type(self) -> builtins.type:
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
        requires_value = self.request_requires_value
        initialize = ... if requires_value else None
        if state_representation == "workflow_step_linked":
            py_type = allow_connected_value(py_type)
            validators = {
                "color_format": field_validator(self.name)(ColorParameterModel.validate_color_str_or_connected_value)
            }
        elif state_representation == "workflow_step":
            validators = {"color_format": field_validator(self.name)(ColorParameterModel.validate_color_str_if_value)}
        else:
            validators = {"color_format": field_validator(self.name)(ColorParameterModel.validate_color_str)}
        field_kwargs = self.field_kwargs()
        return DynamicModelInformation(
            self.name,
            (py_type, Field(initialize, **field_kwargs)),
            validators,
        )

    @property
    def request_requires_value(self) -> bool:
        return False


class BooleanParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_boolean"] = "gx_boolean"
    type: Literal["boolean"]
    value: bool | None = False
    truevalue: str | None = None
    falsevalue: str | None = None

    @property
    def py_type(self) -> builtins.type:
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
    validators: list[TextCompatiableValidators] = []

    @property
    def py_type(self) -> builtins.type:
        return AnyUrl

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        py_type = self.py_type
        py_type = decorate_type_with_validators_if_needed(py_type, self.validators)
        if state_representation == "workflow_step_linked":
            py_type = allow_connected_value(py_type)
        requires_value = self.request_requires_value
        if _is_landing_request(state_representation):
            requires_value = False
        return dynamic_model_information_from_py_type(
            self,
            py_type,
            requires_value=requires_value,
            extra_json_schema=_json_schema_extra_for_validators(self.validators),
        )

    @property
    def request_requires_value(self) -> bool:
        return True


class RulesMapping(StrictModel):
    type: str
    columns: list[StrictInt]


class RulesModel(StrictModel):
    rules: list[dict[str, Any]]
    mapping: list[RulesMapping]


class RulesParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_rules"] = "gx_rules"
    type: Literal["rules"]

    @property
    def py_type(self) -> builtins.type:
        return RulesModel

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        return dynamic_model_information_from_py_type(self, self.py_type)

    @property
    def request_requires_value(self) -> bool:
        return True


SelectCompatiableValidators: TypeAlias = NoOptionsParameterValidatorModel


class SelectParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_select"] = "gx_select"
    type: Literal["select"]
    options: list[LabelValue] | None = None
    multiple: bool = False
    validators: list[SelectCompatiableValidators] = []

    def field_kwargs(self) -> dict[str, Any]:
        kwargs = super().field_kwargs()
        extra = kwargs["json_schema_extra"]
        if self.options is not None and self.options:
            extra["gx_options"] = _label_value_dicts(self.options)
        extra["gx_multiple"] = self.multiple
        return kwargs

    @staticmethod
    def split_str(cls, data: Any) -> Any:
        if isinstance(data, str):
            return [x.strip() for x in data.split(",")]

        return data

    def py_type_if_required(self, allow_connections: bool = False) -> builtins.type:
        if self.options is not None:
            if len(self.options) > 0:
                literal_options = [cast(type, Literal[o.value]) for o in self.options]
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
    def py_type(self) -> builtins.type:
        return optional_if_needed(self.py_type_if_required(), self.optional or self.multiple)

    @property
    def py_type_workflow_step(self) -> builtins.type:
        # this is always optional in this context
        return optional(self.py_type_if_required())

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        validators = {}
        requires_value = self.request_requires_value
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
                py_type = union_type([StrictStr, py_type])
            py_type = optional_if_needed(py_type, self.optional)
        elif state_representation == "test_case_json":
            # in JSON test case representation, lists are already validated as lists (no string splitting)
            py_type = self.py_type_if_required(allow_connections=False)
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
    def default_value(self) -> str | None:
        assert not self.multiple
        if self.options:
            for option in self.options:
                if option.selected:
                    return option.value
            # single value pick up first value
            if not self.optional:
                return self.options[0].value

        return None

    @property
    def default_values(self) -> list[str] | None:
        assert self.multiple
        if self.options:
            return [option.value for option in self.options if option.selected]
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

    def field_kwargs(self) -> dict[str, Any]:
        kwargs = super().field_kwargs()
        kwargs["json_schema_extra"]["gx_multiple"] = self.multiple
        return kwargs

    @property
    def py_type(self) -> builtins.type:
        py_type: type = StrictStr
        if self.multiple:
            py_type = list_type(py_type)
        return optional_if_needed(py_type, self.optional or self.multiple)

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
    options: list[DrillDownOptionsDict], multiple: bool, hierarchy: DrillDownHierarchyT
) -> list[str]:
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
    options: list[DrillDownOptionsDict] | None = None
    multiple: bool
    hierarchy: DrillDownHierarchyT

    def field_kwargs(self) -> dict[str, Any]:
        kwargs = super().field_kwargs()
        kwargs["json_schema_extra"]["gx_multiple"] = self.multiple
        return kwargs

    @property
    def py_type(self) -> builtins.type:
        if self.options is not None:
            literal_options = [
                cast(type, Literal[o]) for o in drill_down_possible_values(self.options, self.multiple, self.hierarchy)
            ]
            py_type = union_type(literal_options)
        else:
            py_type = StrictStr

        if self.multiple:
            py_type = list_type(py_type)

        return py_type

    @property
    def py_type_test_case_xml(self) -> builtins.type:
        base_model = str
        return optional_if_needed(base_model, not self.request_requires_value)

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        py_type = self.py_type_test_case_xml if state_representation == "test_case_xml" else self.py_type
        if state_representation == "test_case_json":
            # JSON test cases use the normal type (not string-based)
            py_type = self.py_type
        requires_value = self.request_requires_value
        if state_representation in ("job_internal", "job_runtime"):
            requires_value = True

        return dynamic_model_information_from_py_type(self, py_type, requires_value=requires_value)

    @property
    def request_requires_value(self) -> bool:
        if options := self.options:
            # if any of these are selected, they seem to serve as defaults - check out test_tools -> test_drill_down_first_by_default
            return not any_drill_down_options_selected(options)
        else:
            # I'm not sure how to handle dynamic options... they might or might not be required?
            # do we need to default to assuming they're not required?
            return False

    @property
    def default_option(self) -> str | None:
        if options := self.options:
            selected_options = selected_drill_down_options(options)
            if len(selected_options) > 0:
                return selected_options[0]
        return None

    @property
    def default_options(self) -> list[str] | None:
        if options := self.options:
            selected_options = selected_drill_down_options(options)
            return selected_options

        return None


def any_drill_down_options_selected(options: list[DrillDownOptionsDict]) -> bool:
    for option in options:
        selected = option.get("selected")
        if selected:
            return True
        child_options = option.get("options", [])
        if any_drill_down_options_selected(child_options):
            return True

    return False


def selected_drill_down_options(options: list[DrillDownOptionsDict]) -> list[str]:
    selected_options: list[str] = []
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
    value: int | list[int] | None = None

    def field_kwargs(self) -> dict[str, Any]:
        kwargs = super().field_kwargs()
        kwargs["json_schema_extra"]["gx_multiple"] = self.multiple
        return kwargs

    @staticmethod
    def split_str(cls, data: Any) -> Any:
        if isinstance(data, str):
            return [int(x.strip()) for x in data.split(",")]
        elif isinstance(data, int):
            return [data]

        return data

    @property
    def py_type(self) -> builtins.type:
        py_type = list_type(StrictInt) if self.multiple else StrictInt
        return optional_if_needed(py_type, self.optional)

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        if state_representation == "test_case_xml":
            if self.multiple:
                validators = {
                    "from_string": field_validator(self.name, mode="before")(DataColumnParameterModel.split_str)
                }
                py_type = union_type([StrictStr, self.py_type])
            else:
                validators = {}
                py_type = self.py_type
            requires_value = self.request_requires_value
            return dynamic_model_information_from_py_type(
                self, py_type, validators=validators, requires_value=requires_value
            )
        elif state_representation == "test_case_json":
            # JSON test cases accept lists directly (no string splitting)
            requires_value = self.request_requires_value
            return dynamic_model_information_from_py_type(
                self, self.py_type, validators={}, requires_value=requires_value
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

    def field_kwargs(self) -> dict[str, Any]:
        kwargs = super().field_kwargs()
        kwargs["json_schema_extra"]["gx_multiple"] = self.multiple
        return kwargs

    @property
    def py_type(self) -> builtins.type:
        py_type = list_type(StrictStr) if self.multiple else StrictStr
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
    def py_type(self) -> builtins.type:
        return HttpUrl

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        return dynamic_model_information_from_py_type(self, self.py_type)

    @property
    def request_requires_value(self) -> bool:
        return True


DiscriminatorType = bool | str


def cond_test_parameter_default_value(
    test_parameter: Union[BooleanParameterModel, "SelectParameterModel"],
) -> DiscriminatorType | None:
    default_value: DiscriminatorType | None = None
    if isinstance(test_parameter, BooleanParameterModel):
        default_value = test_parameter.value
    elif isinstance(test_parameter, SelectParameterModel):
        select_default_value = test_parameter.default_value
        if select_default_value is not None:
            default_value = select_default_value
    return default_value


class ConditionalWhen(StrictModel):
    discriminator: DiscriminatorType
    parameters: list["ToolParameterT"]
    is_default_when: bool


class ConditionalParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_conditional"] = "gx_conditional"
    type: Literal["conditional"]
    test_parameter: BooleanParameterModel | SelectParameterModel
    whens: list[ConditionalWhen]

    def field_kwargs(self) -> dict[str, Any]:
        kwargs = super().field_kwargs()
        extra = kwargs["json_schema_extra"]
        test_param = self.test_parameter
        if isinstance(test_param, SelectParameterModel) and test_param.options:
            extra["gx_options"] = _label_value_dicts(test_param.options)
        if test_param.label:
            extra["gx_test_label"] = test_param.label
        if test_param.help:
            extra["gx_test_help"] = test_param.help
        return kwargs

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        is_boolean = isinstance(self.test_parameter, BooleanParameterModel)
        test_param_name = self.test_parameter.name
        test_info = self.test_parameter.pydantic_template(state_representation)
        extra_validators = test_info.validators
        if state_representation in ("job_internal", "job_runtime"):
            test_parameter_requires_value = True
        else:
            test_parameter_requires_value = self.test_parameter.request_requires_value
        when_types: list[type[BaseModel]] = []
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
                    type[BaseModel],
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
                    when_types.append(cast(type[BaseModel], Annotated[default_type, Tag("__absent__")]))

        def model_x_discriminator(v: Any) -> str | None:
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

        py_type: type

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

        field_kwargs = self.field_kwargs()
        return DynamicModelInformation(
            self.name,
            (py_type, Field(initialize_cond, **field_kwargs)),
            {},
        )

    @property
    def request_requires_value(self) -> bool:
        return False  # TODO


class RepeatParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["gx_repeat"] = "gx_repeat"
    type: Literal["repeat"]
    parameters: list["ToolParameterT"]
    min: int | None = None
    max: int | None = None

    def field_kwargs(self) -> dict[str, Any]:
        kwargs = super().field_kwargs()
        extra = kwargs["json_schema_extra"]
        if self.min is not None:
            extra["gx_min"] = self.min
        if self.max is not None:
            extra["gx_max"] = self.max
        return kwargs

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        # Maybe validators for min and max...
        instance_class: type[BaseModel] = create_field_model(
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
            root: list[instance_class] = Field(initialize_repeat, min_length=min_length, max_length=max_length)  # type: ignore[valid-type]

        field_kwargs = self.field_kwargs()
        return DynamicModelInformation(
            self.name,
            (RepeatType, Field(initialize_repeat, **field_kwargs)),
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
    parameters: list["ToolParameterT"]

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        instance_class: type[BaseModel] = create_field_model(
            self.parameters, f"Section_{self.name}", state_representation
        )
        requires_value = self.request_requires_value
        if state_representation in ("job_internal", "job_runtime"):
            requires_value = True
        if requires_value:
            initialize_section = ...
        else:
            initialize_section = None
        field_kwargs = self.field_kwargs()
        return DynamicModelInformation(
            self.name,
            (instance_class, Field(initialize_section, **field_kwargs)),
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


LiteralNone: TypeAlias = Literal[None]


class CwlNullParameterModel(BaseToolParameterModelDefinition):
    parameter_type: Literal["cwl_null"] = "cwl_null"

    @property
    def py_type(self) -> type:
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
    def py_type(self) -> type:
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
    def py_type(self) -> type:
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
    def py_type(self) -> type:
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
    def py_type(self) -> type:
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
    parameters: list["CwlParameterT"]

    @property
    def py_type(self) -> builtins.type:
        cwl_types = [parameter.py_type for parameter in self.parameters]
        return union_type(cwl_types)

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
    def py_type(self) -> type:
        return DataRequest

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        return dynamic_model_information_from_py_type(self, self.py_type)

    @property
    def request_requires_value(self) -> bool:
        return True


class CwlDirectoryParameterModel(BaseGalaxyToolParameterModelDefinition):
    parameter_type: Literal["cwl_directory"] = "cwl_directory"

    @property
    def py_type(self) -> type:
        return DataRequest

    def pydantic_template(self, state_representation: StateRepresentationT) -> DynamicModelInformation:
        return dynamic_model_information_from_py_type(self, self.py_type)

    @property
    def request_requires_value(self) -> bool:
        return True


CwlParameterT = (
    CwlIntegerParameterModel
    | CwlFloatParameterModel
    | CwlStringParameterModel
    | CwlBooleanParameterModel
    | CwlNullParameterModel
    | CwlFileParameterModel
    | CwlDirectoryParameterModel
    | CwlUnionParameterModel
)

GalaxyParameterT = (
    TextParameterModel
    | IntegerParameterModel
    | FloatParameterModel
    | BooleanParameterModel
    | HiddenParameterModel
    | SelectParameterModel
    | DataParameterModel
    | DataCollectionParameterModel
    | DataColumnParameterModel
    | DirectoryUriParameterModel
    | RulesParameterModel
    | DrillDownParameterModel
    | GroupTagParameterModel
    | BaseUrlParameterModel
    | GenomeBuildParameterModel
    | ColorParameterModel
    | ConditionalParameterModel
    | RepeatParameterModel
    | SectionParameterModel
)

ToolParameterT = CwlParameterT | GalaxyParameterT


class ToolParameterModel(RootModel):
    root: ToolParameterT = Field(..., discriminator="parameter_type")


class GalaxyToolParameterModel(RootModel):
    root: GalaxyParameterT = Field(..., discriminator="type")


ConditionalWhen.model_rebuild()
ConditionalParameterModel.model_rebuild()
RepeatParameterModel.model_rebuild()
CwlUnionParameterModel.model_rebuild()


class MaybeToolParameterBundle(Protocol):
    """An object that may or may not be a ToolParameterModel, but if it is a model, it has a root that is a ToolParameterT"""

    parameters: list[ToolParameterT] | None


class ToolParameterBundle(Protocol):
    """An object having a dictionary of input models (i.e. a 'Tool')"""

    parameters: list[ToolParameterT]


class ToolParameterBundleModel(BaseModel):
    parameters: list[ToolParameterT]


def to_simple_model(input_parameter: ToolParameterModel | ToolParameterT) -> ToolParameterT:
    if input_parameter.__class__ == ToolParameterModel:
        assert isinstance(input_parameter, ToolParameterModel)
        return input_parameter.root
    else:
        return cast(ToolParameterT, input_parameter)


def simple_input_models(
    parameters: list[ToolParameterModel] | list[ToolParameterT],
) -> Iterable[ToolParameterT]:
    return [to_simple_model(m) for m in parameters]


def iter_parameter_models(parameters: Iterable[ToolParameterT]) -> Iterator[ToolParameterT]:
    """Yield every parameter in a parameter tree, depth-first.

    Descends into repeats, sections and *all* branches of every conditional - the purely
    structural view of the tree, independent of any state. A conditional yields the
    conditional itself, then its discriminator ``test_parameter``, then every parameter
    across all of its whens; a repeat/section yields the group node then its children.

    Use this for structure-only queries (collecting names, validating types). When the walk
    needs to follow values - and so only the active when of each conditional - use
    ``visit_input_values`` instead.
    """
    for parameter in parameters:
        yield parameter
        if isinstance(parameter, ConditionalParameterModel):
            yield parameter.test_parameter
            for when in parameter.whens:
                yield from iter_parameter_models(when.parameters)
        elif isinstance(parameter, (RepeatParameterModel, SectionParameterModel)):
            yield from iter_parameter_models(parameter.parameters)


def create_model_strict(*args, **kwd) -> type[BaseModel]:
    # protected_namespaces here prevents tool with model_ parameter names from issuing warnings
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    return create_model(*args, __config__=model_config, **kwd)


def create_model_factory(state_representation: StateRepresentationT):

    def create_method(tool: ToolParameterBundle, name: str | None = None) -> type[BaseModel]:
        return create_field_model(tool.parameters, name or DEFAULT_MODEL_NAME, state_representation)

    return create_method


create_relaxed_request_model = create_model_factory("relaxed_request")
create_request_model = create_model_factory("request")
create_request_internal_model = create_model_factory("request_internal")
create_request_internal_dereferenced_model = create_model_factory("request_internal_dereferenced")
create_landing_request_model = create_model_factory("landing_request")
create_landing_request_internal_model = create_model_factory("landing_request_internal")
create_job_internal_model = create_model_factory("job_internal")
create_job_runtime_model = create_model_factory("job_runtime")
create_test_case_model = create_model_factory("test_case_xml")
create_test_case_json_model = create_model_factory("test_case_json")
create_workflow_step_model = create_model_factory("workflow_step")
create_workflow_step_linked_model = create_model_factory("workflow_step_linked")


def create_field_model(
    tool_parameter_models: list[ToolParameterModel] | list[ToolParameterT],
    name: str,
    state_representation: StateRepresentationT,
    extra_kwd: Mapping[str, tuple] | None = None,
    extra_validators: ValidatorDictT | None = None,
) -> type[BaseModel]:
    kwd: dict[str, tuple] = {}
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
