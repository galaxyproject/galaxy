"""Define the ParsedTool model representing metadata extracted from a tool's source.

This is abstraction exported by newer tool shed APIS (circa 2024) and should be sufficient
for reasoning about tool state externally from Galaxy.
"""

import re
from typing import (
    Annotated,
    Any,
    ClassVar,
    Literal,
    Union,
)

from pydantic import (
    AnyUrl,
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    field_validator,
    model_serializer,
    model_validator,
    RootModel,
    SerializerFunctionWrapHandler,
    Tag,
    ValidationError,
)
from pydantic_core import PydanticCustomError
from typing_extensions import (
    NotRequired,
    TypedDict,
)

from ._base import (
    CollectionType,
    StrictModel,
    ToolSourceBaseModel,
)
from .assertions import assertions
from .parameters import ToolParameterT
from .test_job import Job
from .tool_outputs import (
    IncomingToolOutput,
    IncomingToolOutputCollection,
    IncomingToolOutputDataset,
    ToolOutput,
)
from .tool_source import (
    Citation,
    Container,
    ContainerRequirement,
    HelpContent,
    JavascriptRequirement,
    OutputCompareType,
    PackageRequirement,
    ResourceRequirement,
    SetEnvironmentRequirement,
    Stdio,
    XrefDict,
    YamlTemplateConfigFile,
)
from .yaml_parameters import YamlGalaxyToolParameter


def normalize_dict(values, keys: list[str]):
    for key in keys:
        items = values.get(key)
        if isinstance(items, dict):  # dict-of-dicts format
            # Transform dict-of-dicts to list-of-dicts
            values[key] = [{"name": k, **v} for k, v in items.items()]


# Tool ID: lowercase, leading letter, letters/digits/'_'/'-'.
_TOOL_ID_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
TOOL_ID_PATTERN = r"^[a-z][a-z0-9_-]*$"

# Templated ecmascript inside `shell_command` / `configfiles[*].content`.
# Pull every $(<expr>) and extract the *leading* 'inputs.<name>' identifier.
# Only the top-level name is checked, so nested references like
# 'inputs.cond.test_parameter' or 'inputs.repeat[0].x' resolve against
# the conditional / repeat / section's own top-level name -- no false
# positives for nested structures. Computed/aliased references (e.g.
# 'var x = inputs; x.foo') are intentionally not parsed; the goal is
# catching obvious typos cheaply, not modelling ecmascript scope.
_TEMPLATE_BLOCK_RE = re.compile(r"\$\((.*?)\)", re.DOTALL)
_INPUTS_REF_RE = re.compile(r"\binputs\.([A-Za-z_][A-Za-z0-9_]*)")


def _command_input_refs(text: str | None) -> set[str]:
    refs: set[str] = set()
    if not text:
        return refs
    for block in _TEMPLATE_BLOCK_RE.findall(text):
        for match in _INPUTS_REF_RE.findall(block):
            refs.add(match)
    return refs


def format_validation_errors(exc: ValidationError) -> list[str]:
    """Distill a pydantic ValidationError into a human-readable list.

    Each entry is `<dotted.location>: <message>`, or just `<message>` for
    model-level errors with no location. Suitable for surfacing directly to
    a user (in the agent's bullet list, or as an API 4xx body).
    """
    lines: list[str] = []
    for err in exc.errors():
        loc_parts = [str(p) for p in err.get("loc", ()) if p not in ("__root__",)]
        loc = ".".join(loc_parts)
        msg = err.get("msg", "validation error")
        lines.append(f"{loc}: {msg}" if loc else msg)
    return lines


class _DynamicToolSourceBase(ToolSourceBaseModel):
    # extra="forbid" rejects unknown top-level keys (e.g. a stray `argument:` at
    # the tool level), matching the strict-narrow stance on `inputs`.
    model_config = ConfigDict(
        extra="forbid",
        field_title_generator=lambda field_name, field_info: field_name.lower(),
    )

    id: Annotated[
        str | None,
        Field(
            description=(
                "Unique identifier for the tool. Lowercase, must start with a letter, "
                "may contain letters, digits, '_' and '-'."
            ),
            examples=["my-cool-tool"],
            min_length=3,
            max_length=255,
            pattern=TOOL_ID_PATTERN,
        ),
    ] = None
    version: Annotated[str | None, Field(description="Version for the tool.", examples=["0.1.0"])] = None
    name: Annotated[
        str,
        Field(
            description="The name of the tool, displayed in the tool menu. This is not the same as the tool id, which is a unique identifier for the tool.",
            min_length=5,
        ),
    ]
    description: Annotated[
        str | None,
        Field(
            description="The description is displayed in the tool menu immediately following the hyperlink for the tool."
        ),
    ] = None
    configfiles: Annotated[
        list[YamlTemplateConfigFile] | None, Field(description="A list of config files for this tool.")
    ] = None
    requirements: Annotated[
        list[JavascriptRequirement | ResourceRequirement | ContainerRequirement] | None,
        Field(
            description="A list of requirements needed to execute this tool. These can be javascript expressions, resource requirements or container images."
        ),
    ] = []
    shell_command: Annotated[
        str,
        Field(
            title="shell_command",
            description="A string that contains the command to be executed. Parameters can be referenced inside $().",
            examples=["head -n '$(inputs.num_lines)' '$(inputs.input_file.path)' > output.txt"],
        ),
    ]
    inputs: list[YamlGalaxyToolParameter] = []
    outputs: list[IncomingToolOutput] = []
    citations: list[Citation] | None = None
    license: Annotated[
        str | None,
        Field(
            description="A full URI or a a short [SPDX](https://spdx.org/licenses/) identifier for a license for this tool wrapper. The tool wrapper license can be independent of the underlying tool license. This license covers the tool yaml and associated scripts shipped with the tool.",
            examples=["MIT"],
        ),
    ] = None
    edam_operations: list[str] | None = None
    edam_topics: list[str] | None = None
    xrefs: list[XrefDict] | None = None
    profile: float | None = None
    help: Annotated[HelpContent | None, Field(description="Help text shown below the tool interface.")] = None
    # NOTE: `tests` is intentionally NOT declared here. It lives on the concrete
    # subclasses (`UserToolSource`, `YamlToolSource`) so that the slim
    # `UserToolSourceAuthoringView` can inherit everything *except* the test
    # field. The test-assertion DSL pulled in by `tests` is ~70% of the JSON
    # schema; keeping it off the authoring view is what shrinks the
    # structured-output schema handed to LLM tool-generation agents.

    @model_validator(mode="before")
    @classmethod
    def normalize_items(cls, values):
        if isinstance(values, dict):
            normalize_dict(values, ["inputs", "outputs"])
        return values

    @field_validator("name", "version", mode="after")
    @classmethod
    def _reject_blank_strings(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise PydanticCustomError(
                "dynamic_tool.blank_string",
                "must not be empty or whitespace",
            )
        return v

    @model_validator(mode="after")
    def _check_input_refs(self) -> "_DynamicToolSourceBase":
        declared_inputs: set[str] = {param.root.name for param in self.inputs}
        referenced: set[str] = _command_input_refs(self.shell_command)
        for configfile in self.configfiles or []:
            referenced |= _command_input_refs(configfile.content)
        if undeclared := sorted(referenced - declared_inputs):
            joined = "; ".join(
                f"references inputs.{name} but no input named '{name}' is declared" for name in undeclared
            )
            raise PydanticCustomError(
                "dynamic_tool.undeclared_input_ref",
                joined,
            )
        return self

    @model_validator(mode="after")
    def _check_output_claims(self) -> "_DynamicToolSourceBase":
        errors: list[str] = []
        for output in self.outputs:
            if isinstance(output, IncomingToolOutputDataset):
                if not output.from_work_dir and not output.discover_datasets:
                    errors.append(
                        f"output '{output.name}' must set 'from_work_dir' or 'discover_datasets' "
                        "(otherwise its bytes will never be claimed from the working directory)"
                    )
            elif isinstance(output, IncomingToolOutputCollection):
                if not output.discover_datasets:
                    errors.append(
                        f"output collection '{output.name}' must set 'discover_datasets' "
                        "(otherwise no elements will be claimed from the working directory)"
                    )
        if errors:
            raise PydanticCustomError(
                "dynamic_tool.output_unclaimed",
                "; ".join(errors),
            )
        return self


# Schema-narrowed view of ``UserToolSource`` for LLM tool authoring.
#
# This is the *parent* of ``UserToolSource`` and carries every field and
# validator except ``tests``. Authoring agents (see ``galaxy.agents.custom_tool``)
# point their structured-output ``output_type`` at this view so the JSON schema
# the model must satisfy omits the test-assertion DSL — ~70% of
# ``UserToolSource``'s ~150 KB schema and never written in the first generation
# pass. Shrinking the schema cuts per-call token cost and sidesteps the
# nested-``$defs`` grammar failures some local inference backends hit (see
# ``CustomToolAgent._handle_model_http_error``).
#
# A produced view is a strict subset of ``UserToolSource``; convert with
# ``UserToolSource.model_validate(view.model_dump(by_alias=True))`` before storing
# or linting so downstream types stay honest.
#
# NOTE: the class docstring below is published verbatim as the structured-output
# tool *description* sent to the model on every call — keep it model-facing and
# concise; put implementation rationale in comments like this one, not the
# docstring.
class UserToolSourceAuthoringView(_DynamicToolSourceBase):
    """A Galaxy user-defined tool: a containerized shell command wrapped with typed inputs and outputs.

    Provide the tool's identity (``id``, ``name``, ``version``), a ``container``
    image to run in, and a ``shell_command`` that references inputs as
    ``$(inputs.NAME)`` for scalar values or ``$(inputs.NAME.path)`` for files.
    Declare every referenced input under ``inputs`` and every produced file under
    ``outputs`` (each output must set ``from_work_dir`` or ``discover_datasets``).
    """

    class_: Annotated[Literal["GalaxyUserTool"], Field(alias="class")]
    container: Annotated[
        str, Field(description="Container image to use for this tool.", examples=["quay.io/biocontainers/python:3.13"])
    ]
    # Required here (it's optional on the base for stored/legacy rows). Galaxy's
    # linter rejects a versionless tool, so forcing it into the structured-output
    # ``required`` set stops the model dropping it -- notably on a retry, where the
    # model would otherwise regenerate without it and trip ``ToolVersionMissing``.
    version: Annotated[str, Field(description="Version for the tool.", examples=["0.1.0"])]

    # Field declaration order puts subclass fields (class_, container) after
    # parent ones, which serializes them at the end. Re-order on dump so the
    # YAML the tool editor renders leads with identity + runtime.
    _CANONICAL_FIELD_ORDER: ClassVar[tuple[str, ...]] = (
        "class_",
        "id",
        "name",
        "version",
        "description",
        "container",
        "requirements",
        "shell_command",
        "configfiles",
        "inputs",
        "outputs",
        "citations",
        "license",
        "profile",
        "edam_operations",
        "edam_topics",
        "xrefs",
        "help",
        "tests",
    )

    @field_validator("container", mode="after")
    @classmethod
    def _reject_blank_container(cls, value: str) -> str:
        if not value or not value.strip():
            raise PydanticCustomError(
                "dynamic_tool.blank_container",
                "container must not be empty",
            )
        return value

    @model_serializer(mode="wrap")
    def _canonical_order(self, handler: SerializerFunctionWrapHandler, info: Any):
        # Runs for both direct ``model_dump`` calls and nested serialization
        # (e.g. inside ``UnprivilegedToolResponse``), where pydantic_core
        # bypasses ``model_dump`` on the child.
        # No return annotation so pydantic derives the output JSON schema from
        # the model fields instead of treating the result as opaque dict.
        data = handler(self)
        if not isinstance(data, dict):
            return data
        by_alias = bool(getattr(info, "by_alias", False))
        fields = type(self).model_fields
        ordered: dict[str, Any] = {}
        for field_name in self._CANONICAL_FIELD_ORDER:
            field_info = fields.get(field_name)
            key = (field_info.alias or field_name) if by_alias and field_info and field_info.alias else field_name
            if key in data:
                ordered[key] = data.pop(key)
        # Preserve any unexpected keys (forward compat) at the end.
        ordered.update(data)
        return ordered


class UserToolSource(UserToolSourceAuthoringView):
    """Full unprivileged tool source, including the optional ``tests`` block.

    This is the model persisted and validated on the API surface
    (``DynamicUnprivilegedToolCreatePayload.representation``). LLM authoring
    uses the slimmer ``UserToolSourceAuthoringView`` parent; ``tests`` is added
    back here so direct authors and stored rows can still carry tests.
    """

    # ``version`` is required (inherited from UserToolSourceAuthoringView). A stored
    # row that predates the requirement won't validate; ``lift_user_tool_source``
    # returns it as the raw dict with status "invalid" so its author still sees it.
    tests: list["YamlToolTest"] | None = None


class YamlToolSource(_DynamicToolSourceBase):
    class_: Annotated[Literal["GalaxyTool"], Field(alias="class")]
    container: Annotated[
        str | None,
        Field(
            description="Container image to use for this tool.",
            examples=["quay.io/biocontainers/python:3.13"],
        ),
    ] = None
    tests: list["YamlToolTest"] | None = None


DynamicToolSources = Annotated[UserToolSource | YamlToolSource, Field(discriminator="class_")]


# ---------------------------------------------------------------------------
# Schema-drift "lift" for stored DynamicTool.value rows.
#
# The strict `UserToolSource` schema is the single source of truth for both
# input and output. Stored rows from older Galaxy versions may carry fields
# that the current schema rejects (e.g. legacy internal-model fields after the
# YAML narrowing) or values that fail tightened constraints (e.g. a future
# `container` regex). `lift_user_tool_source` validates against the strict
# schema and:
#   - on success: returns ("ok", parsed_model, []).
#   - on `extra_forbidden`-only failure: strips the offending paths and
#     re-validates. Returns ("lifted", parsed_model, dropped_paths).
#   - on any other failure: returns ("invalid", original_dict, error_summary).
#     The endpoint exposes this so legacy/broken rows don't crash the API -- e.g.
#     a stored row that predates the required `version` comes back as the raw dict
#     with status "invalid", so its author can still see and fix what they defined.
# ---------------------------------------------------------------------------

LiftStatus = Literal["ok", "lifted", "invalid"]


def _navigable_path(value: Any, loc: tuple) -> tuple[Any | None, list[Any]]:
    """Walk `loc` against the structure of `value`, skipping steps that don't
    correspond to a real key/index (pydantic inserts discriminator literals
    like `"data"` into the loc for tagged unions). Returns the parent
    container of the leaf and the cleaned path components, or (None, []) if
    the path can't be resolved."""
    cur: Any = value
    if not loc:
        return cur, []
    *prefix, leaf = loc
    cleaned: list[Any] = []
    for step in prefix:
        if isinstance(cur, list) and isinstance(step, int) and 0 <= step < len(cur):
            cur = cur[step]
            cleaned.append(step)
        elif isinstance(cur, dict) and step in cur:
            cur = cur[step]
            cleaned.append(step)
        # else: skip — discriminator tag or stale path
    cleaned.append(leaf)
    return cur, cleaned


def _format_loc(value: Any, loc: tuple) -> str:
    _parent, cleaned = _navigable_path(value, loc)
    return ".".join(str(p) for p in cleaned if p != "representation")


def _strip_path(value: dict, loc: tuple) -> bool:
    """Remove the field at the given pydantic error `loc` from `value`. Returns
    True if a key was actually removed."""
    parent, cleaned = _navigable_path(value, loc)
    if not cleaned or not isinstance(parent, dict):
        return False
    if (leaf := cleaned[-1]) in parent:
        del parent[leaf]
        return True
    return False


def lift_user_tool_source(
    value: dict,
) -> tuple[LiftStatus, Union["UserToolSource", dict[str, Any]], list[str]]:
    """Validate `value` against the strict UserToolSource, lifting drift where
    safe. See module docstring above for the contract.
    """
    import copy

    try:
        return ("ok", UserToolSource.model_validate(value), [])
    except ValidationError as e:
        errors = e.errors()

    extra_forbidden = [err for err in errors if err.get("type") == "extra_forbidden"]
    other = [err for err in errors if err.get("type") != "extra_forbidden"]
    if extra_forbidden and not other:
        stripped = copy.deepcopy(value)
        dropped: list[str] = []
        for err in extra_forbidden:
            loc = tuple(err["loc"])
            if _strip_path(stripped, loc):
                dropped.append(_format_loc(value, loc))
        try:
            return ("lifted", UserToolSource.model_validate(stripped), dropped)
        except ValidationError as e2:
            errors = e2.errors()

    summary = [f"{_format_loc(value, tuple(err['loc']))}: {err.get('msg', err.get('type', ''))}" for err in errors]
    return ("invalid", value, summary)


class ParsedTool(ToolSourceBaseModel):
    id: str
    version: str | None
    name: str
    description: str | None
    requirements: list[PackageRequirement | SetEnvironmentRequirement | ResourceRequirement | JavascriptRequirement] = (
        Field(default_factory=list)
    )
    containers: list[Container] = Field(default_factory=list)
    stdio: Stdio = Field(default_factory=Stdio)
    inputs: list[ToolParameterT]
    outputs: list[ToolOutput]
    citations: list[Citation]
    license: str | None
    profile: str | None
    edam_operations: list[str]
    edam_topics: list[str]
    xrefs: list[XrefDict]
    help: HelpContent | None


class BaseTestOutputModel(StrictModel):
    model_config = ConfigDict(extra="forbid", title="BaseTestOutputModel")
    file: Annotated[
        str | None,
        Field(
            title="File",
            description=(
                "Name of the output file stored in the target `test-data` directory that will be used to "
                "compare against the results of executing the tool via the functional test framework."
            ),
        ),
    ] = None
    path: Annotated[
        str | None,
        Field(title="Path", description="Filesystem path to a local output file used for comparison."),
    ] = None
    location: Annotated[
        AnyUrl | None,
        Field(
            title="Location",
            description=(
                "URL that points to a remote output file that will be downloaded and used for output "
                "comparison. Use only when the file cannot be included in the `test-data` folder. May be "
                "combined with `file` (downloads when missing on disk) or used alone (filename inferred "
                "from the URL). A `checksum` is also used to verify the download when provided."
            ),
        ),
    ] = None
    ftype: Annotated[
        str | None,
        Field(
            title="File Type",
            description=(
                "If specified, this value is checked against the corresponding output's data type. "
                "If these do not match, the test will fail."
            ),
        ),
    ] = None
    sort: Annotated[
        bool | None,
        Field(
            title="Sort",
            description=(
                "Applies only if `compare` is `diff`, `re_match` or `re_match_multiline`. Sorts the lines "
                "of the history data set before comparison; for `diff` and `re_match` the local file is "
                "also sorted. Useful for non-deterministic output."
            ),
        ),
    ] = None
    compare: Annotated[
        OutputCompareType | None,
        Field(
            title="Compare",
            description="Comparison mode used when matching the output against the reference file.",
        ),
    ] = None
    checksum: Annotated[
        str | None,
        Field(
            title="Checksum",
            description=(
                "The target output's checksum should match the value specified here, in the form "
                "`hash_type$hash_value` (e.g. `sha1$8156d7ca0f46ed7abac98f82e36cfaddb2aca041`). Useful "
                "for large static files where uploading the whole file is inconvenient."
            ),
        ),
    ] = None
    metadata: Annotated[
        dict[str, Any] | None,
        Field(
            title="Metadata",
            description="Mapping of metadata keys to expected values for this output.",
        ),
    ] = None
    asserts: Annotated[
        assertions | None,
        Field(title="Asserts", description="Assertions about the content of the output."),
    ] = None
    delta: Annotated[
        int | None,
        Field(
            title="Delta",
            description=(
                "If `compare` is set to `sim_size`, the maximum allowed absolute size difference (in "
                "bytes) between the generated data set and the reference file in `test-data/`. Default "
                "is 10000 bytes. Can be combined with `delta_frac`."
            ),
        ),
    ] = None
    delta_frac: Annotated[
        float | None,
        Field(
            title="Delta Frac",
            description=(
                "If `compare` is set to `sim_size`, the maximum allowed relative size difference between "
                "the generated data set and the reference file in `test-data/`. 0.1 means the generated "
                "file can differ by at most 10%. Default is not to check for relative size difference. "
                "Can be combined with `delta`."
            ),
        ),
    ] = None
    lines_diff: Annotated[
        int | None,
        Field(
            title="Lines Diff",
            description=(
                "Applies when `compare` is set to `diff`, `re_match`, or `contains`. For `diff`, the "
                "number of lines of difference to allow (a modified line counts as two: one added, one "
                "removed)."
            ),
        ),
    ] = None
    decompress: Annotated[
        bool | None,
        Field(
            title="Decompress",
            description=(
                "If true, decompress files before comparison. Applies to assertions expressed with "
                "`assert_contents` or `compare` set to anything but `sim_size`. Useful for testing "
                "compressed outputs that are non-deterministic despite having deterministic decompressed "
                "contents. By default, only files compressed with bz2, gzip and zip are automatically "
                "decompressed."
            ),
        ),
    ] = None


class TestDataOutputAssertions(BaseTestOutputModel):
    model_config = ConfigDict(extra="forbid", title="TestDataOutputAssertions")
    class_: Literal["File"] | None = Field("File", alias="class", title="Class")


class TestCollectionCollectionElementAssertions(StrictModel):
    model_config = ConfigDict(extra="forbid", title="TestCollectionCollectionElementAssertions")
    class_: Literal["Collection"] | None = Field("Collection", alias="class", title="Class")
    elements: Annotated[
        dict[str, "TestCollectionElementAssertion"] | None,
        Field(title="Elements"),
    ] = None
    element_tests: Annotated[
        dict[str, "TestCollectionElementAssertion"] | None,
        Field(title="Element Tests"),
    ] = None


class TestCollectionDatasetElementAssertions(BaseTestOutputModel):
    model_config = ConfigDict(extra="forbid", title="TestCollectionDatasetElementAssertions")
    class_: Literal["File"] | None = Field("File", alias="class", title="Class")


def _discriminate_collection_element(v):
    if isinstance(v, dict):
        if v.get("class") == "Collection":
            return "Collection"
        return "File"
    if isinstance(v, TestCollectionCollectionElementAssertions):
        return "Collection"
    if isinstance(v, TestCollectionDatasetElementAssertions):
        return "File"
    return None


TestCollectionElementAssertion = Annotated[
    Annotated[TestCollectionDatasetElementAssertions, Tag("File")]
    | Annotated[TestCollectionCollectionElementAssertions, Tag("Collection")],
    Discriminator(_discriminate_collection_element),
]
TestCollectionCollectionElementAssertions.model_rebuild()


class CollectionAttributes(StrictModel):
    model_config = ConfigDict(extra="forbid", title="CollectionAttributes")
    collection_type: Annotated[CollectionType, Field(title="Collection Type")] = None


class TestCollectionOutputAssertions(StrictModel):
    model_config = ConfigDict(extra="forbid", title="TestCollectionOutputAssertions")
    class_: Literal["Collection"] | None = Field("Collection", alias="class", title="Class")
    elements: Annotated[
        dict[str, TestCollectionElementAssertion] | None,
        Field(title="Elements"),
    ] = None
    element_tests: Annotated[
        dict[str, "TestCollectionElementAssertion"] | None,
        Field(title="Element Tests"),
    ] = None
    element_count: Annotated[int | None, Field(title="Element Count")] = None
    attributes: Annotated[CollectionAttributes | None, Field(title="Attributes")] = None
    collection_type: Annotated[CollectionType, Field(title="Collection Type")] = None


TestOutputLiteral = bool | int | float | str


def _discriminate_output(v):
    if isinstance(v, dict):
        if v.get("class") == "Collection":
            return "Collection"
        return "File"
    if isinstance(v, TestCollectionOutputAssertions):
        return "Collection"
    if isinstance(v, TestDataOutputAssertions):
        return "File"
    if isinstance(v, (bool, int, float, str)):
        return "scalar"
    return None


TestOutputAssertions = Annotated[
    Annotated[TestCollectionOutputAssertions, Tag("Collection")]
    | Annotated[TestDataOutputAssertions, Tag("File")]
    | Annotated[TestOutputLiteral, Tag("scalar")],
    Discriminator(_discriminate_output),
]


TestInputValue = bool | int | float | str | list[Any] | dict[str, Any]


class YamlTestCredentialValue(StrictModel):
    model_config = ConfigDict(extra="forbid", title="YamlTestCredentialValue")
    name: Annotated[str, Field(title="Name", description="Name of the credential variable or secret.")]
    value: Annotated[str, Field(title="Value", description="Value of the credential variable or secret.")]


class YamlTestCredential(StrictModel):
    model_config = ConfigDict(extra="forbid", title="YamlTestCredential")
    name: Annotated[str, Field(title="Name", description="Name of the credentials group.")]
    variables: Annotated[
        list[YamlTestCredentialValue],
        Field(title="Variables", description="Variables exposed to the tool environment."),
    ] = []
    secrets: Annotated[
        list[YamlTestCredentialValue],
        Field(title="Secrets", description="Secrets exposed to the tool environment."),
    ] = []
    version: Annotated[
        str | None,
        Field(title="Version", description="Version of the credential definition."),
    ] = None


class YamlToolTest(BaseModel):
    """In-tool test case as authored in YAML tool fixtures."""

    model_config = ConfigDict(extra="forbid")

    doc: Annotated[str | None, Field(description="Human-readable description of this test case.")] = None
    inputs: Annotated[
        dict[str, TestInputValue] | None,
        Field(description="Mapping of input parameter names to test values."),
    ] = None
    outputs: Annotated[
        dict[str, TestOutputAssertions],
        Field(description="Mapping of output names to expected values or assertions."),
    ] = {}
    assert_stdout: Annotated[
        assertions | None,
        Field(description="Assertions to apply against the tool's standard output."),
    ] = None
    assert_stderr: Annotated[
        assertions | None,
        Field(description="Assertions to apply against the tool's standard error."),
    ] = None
    command: Annotated[
        assertions | None,
        Field(description="Assertions to apply against the executed command line."),
    ] = None
    expect_exit_code: Annotated[
        int | None,
        Field(description="Expected process exit code."),
    ] = None
    expect_failure: Annotated[
        bool | None,
        Field(description="If true, the tool is expected to produce an error."),
    ] = None
    expect_test_failure: Annotated[
        bool | None,
        Field(description="If true, the test itself is expected to fail."),
    ] = None
    credentials: Annotated[
        list[YamlTestCredential] | None,
        Field(description="Credentials to inject for this test case."),
    ] = None


UserToolSource.model_rebuild()
YamlToolSource.model_rebuild()

# Loose alias retained for TestJobDict / TypedDict consumers where helpers
# still tolerate Dict[str, Any]. The strict, validated shape is `Job` (see
# galaxy.tool_util_models.test_job).
JobDict = dict[str, Any]


class TestJob(StrictModel):
    model_config = ConfigDict(extra="forbid", title="TestJob")
    doc: Annotated[
        str | None,
        Field(title="Doc", description="Describes the purpose of the test."),
    ] = None
    job: Annotated[
        Job,
        Field(
            title="Job",
            description=(
                "Defines the job to execute. Can be a path to a file or an inline dictionary describing the job inputs."
            ),
        ),
    ]
    outputs: Annotated[
        dict[str, TestOutputAssertions],
        Field(
            title="Outputs",
            description=(
                "Defines assertions about outputs (datasets, collections or parameters). Each key "
                "corresponds to a labeled output; values are dictionaries describing the expected output."
            ),
        ),
    ]
    expect_failure: Annotated[
        bool | None,
        Field(
            title="Expect Failure",
            description="If true, the workflow is expected to produce an error.",
        ),
    ] = False


class Tests(RootModel[list[TestJob]]):
    model_config = ConfigDict(
        title="GalaxyWorkflowTests",
        json_schema_extra={
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "description": (
                "Galaxy workflow tests file — a YAML list of test entries asserting the expected "
                "inputs and outputs of a workflow run."
            ),
        },
    )


# TODO: typed dict versions of all thee above for verify code - make this Dict[str, Any] here more
# specific.
OutputChecks = TestOutputLiteral | dict[str, Any]
OutputsDict = dict[str, OutputChecks]


class JobTestDict(TypedDict):
    doc: NotRequired[str]
    job: NotRequired[JobDict]
    expect_failure: NotRequired[bool]
    outputs: OutputsDict


TestDicts = list[JobTestDict]
