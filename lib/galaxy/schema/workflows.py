import json
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)

from pydantic import (
    Field,
    field_validator,
    UUID4,
)
from typing_extensions import (
    Annotated,
    Literal,
)

from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
    AnnotationField,
    InputDataCollectionStep,
    InputDataStep,
    InputParameterStep,
    Model,
    Organization,
    PauseStep,
    Person,
    PreferredObjectStoreIdField,
    StoredWorkflowSummary,
    SubworkflowStep,
    TagCollection,
    ToolStep,
)
from galaxy.schema.workflow.comments import WorkflowCommentModel

WorkflowAnnotationField = Annotated[
    Optional[str],
    Field(
        title="Annotation",
        description="An annotation to provide details or to help understand the purpose and usage of this item.",
    ),
]

WorkflowCreator = Annotated[
    Optional[List[Union[Person, Organization]]],
    Field(
        None,
        title="Creator",
        description=("Additional information about the creator (or multiple creators) of this workflow."),
    ),
]


class WorkflowDictExportStepInput(Model):
    name: str = Field(..., title="Name", description="The name of the input.")
    description: str = Field(..., title="Description", description="The annotation or description of the input.")


class InputConnectionBase(Model):
    id: int = Field(..., title="ID", description="The order index of the step.")
    output_name: str = Field(
        ...,
        title="Output Name",
        description="The output name of the input step that serves as the source for this connection.",
    )


class InputConnectionExport(InputConnectionBase):
    input_subworkflow_step_id: Optional[int] = Field(
        None,
        title="Input Subworkflow Step ID",
    )


class InputConnectionEditor(InputConnectionBase):
    input_type: str = Field(
        ...,
        title="Input Type",
        description="The input type of the workflow step.",
    )


class WorkflowStepLayoutPosition(Model):
    """Position and dimensions of the workflow step represented by a box on the graph."""

    bottom: Optional[Union[int, float]] = Field(
        None,
        title="Bottom",
        description="Position of the bottom of the box.",
    )
    top: Union[int, float] = Field(
        ...,
        title="Top",
        description="Position of the top of the box.",
    )
    left: Union[int, float] = Field(
        ...,
        title="Left",
        description="Left margin or left-most position of the box.",
    )
    right: Optional[Union[int, float]] = Field(
        None,
        title="Right",
        description="Right margin or right-most position of the box.",
    )
    x: Optional[int] = Field(
        None,
        title="X",
        description="Horizontal coordinate of the top right corner of the box.",
    )
    y: Optional[int] = Field(
        None,
        title="Y",
        description="Vertical coordinate of the top right corner of the box.",
    )
    height: Optional[Union[int, float]] = Field(
        None,
        title="Height",
        description="Height of the box.",
    )
    width: Optional[Union[int, float]] = Field(
        None,
        title="Width",
        description="Width of the box.",
    )


class WorkflowInput(Model):
    label: Optional[str] = Field(
        ...,
        title="Label",
        description="Label of the input.",
    )
    value: Optional[Any] = Field(
        ...,
        title="Value",
    )
    uuid: Optional[UUID4] = Field(
        ...,
        title="UUID",
        description="Universal unique identifier of the input.",
    )


class WorkflowOutput(Model):
    label: Optional[str] = Field(
        None,
        title="Label",
        description="Label of the output.",
    )
    output_name: str = Field(
        ...,
        title="Output Name",
        description="The name of the step output.",
    )
    uuid: Optional[UUID4] = Field(
        None,
        title="UUID",
        description="Universal unique identifier of the output.",
    )


class ToolShedRepositorySummary(Model):
    name: str = Field(
        ...,
        title="Name",
        description="The name of the repository.",
    )
    owner: str = Field(
        ...,
        title="Owner",
        description="The owner of the repository.",
    )
    changeset_revision: str = Field(
        ...,
        title="Changeset Revision",
    )
    tool_shed: str = Field(
        ...,
        title="Tool Shed",
        description="The Tool Shed base URL.",
    )


class PostJobAction(Model):
    action_type: str = Field(
        ...,
        title="Action Type",
        description="The type of action to run.",
    )
    output_name: str = Field(
        ...,
        title="Output Name",
        description="The name of the output that will be affected by the action.",
    )
    action_arguments: Dict[str, Any] = Field(
        ...,
        title="Action Arguments",
        description="Any additional arguments needed by the action.",
    )
    short_str: Optional[str] = Field(
        None,
        title="Short String",
        description="A short string representation of the action.",
    )


class StepIn(Model):
    # TODO - add proper type and description - see _workflow_to_dict_export in manager for more details
    # or class WorkflowStepInput
    default: Any = Field(
        ...,
        title="Default",
    )


class GetTargetHistoryPayload(Model):
    # TODO - Are the descriptions correct?
    history: Optional[str] = Field(
        None,
        title="History",
        description="The encoded history id - passed exactly like this 'hist_id=...' -  into which to import. Or the name of the new history into which to import.",
    )
    history_id: Optional[str] = Field(
        None,
        title="History ID",
        description="The encoded history id into which to import.",
    )
    new_history_name: Optional[str] = Field(
        None,
        title="New History Name",
        description="The name of the new history into which to import.",
    )


class InvokeWorkflowPayload(GetTargetHistoryPayload):
    # TODO - Are the descriptions correct?
    version: Optional[int] = Field(
        None,
        title="Version",
        description="The version of the workflow to invoke.",
    )
    instance: Optional[bool] = Field(
        False,
        title="Is instance",
        description="True when fetching by Workflow ID, False when fetching by StoredWorkflow ID",
    )
    scheduler: Optional[str] = Field(
        None,
        title="Scheduler",
        description="Scheduler to use for workflow invocation.",
    )
    batch: Optional[bool] = Field(
        False,
        title="Batch",
        description="Indicates if the workflow is invoked as a batch.",
    )
    require_exact_tool_versions: Optional[bool] = Field(
        True,
        title="Require Exact Tool Versions",
        description="If true, exact tool versions are required for workflow invocation.",
    )
    allow_tool_state_corrections: Optional[bool] = Field(
        False,
        title="Allow tool state corrections",
        description="Indicates if tool state corrections are allowed for workflow invocation.",
    )
    use_cached_job: Optional[bool] = Field(
        False,
        title="Use cached job",
        description="Indicated whether to use a cached job for workflow invocation.",
    )
    parameters_normalized: Optional[bool] = Field(
        False,
        title="Parameters Normalized",
        description="Indicates if parameters are already normalized for workflow invocation.",
    )

    @field_validator(
        "parameters",
        "inputs",
        "ds_map",
        "resource_params",
        "replacement_params",
        "step_parameters",
        mode="before",
        check_fields=False,
    )
    @classmethod
    def inputs_string_to_json(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    parameters: Optional[Dict[str, Any]] = Field(
        {},
        title="Parameters",
        description="The raw parameters for the workflow invocation.",
    )
    inputs: Optional[Dict[str, Any]] = Field(
        None,
        title="Inputs",
    )
    ds_map: Optional[Dict[str, Dict[str, Any]]] = Field(
        {},
        title="Dataset Map",
    )
    resource_params: Optional[Dict[str, Any]] = Field(
        {},
        title="Resource Parameters",
    )
    replacement_params: Optional[Dict[str, Any]] = Field(
        {},
        title="Replacement Parameters",
    )
    step_parameters: Optional[Dict[str, Any]] = Field(
        None,
        title="Step Parameters",
    )
    no_add_to_history: Optional[bool] = Field(
        False,
        title="No Add to History",
        description="Indicates if the workflow invocation should not be added to the history.",
    )
    legacy: Optional[bool] = Field(
        False,
        title="Legacy",
        description="Indicating if to use legacy workflow invocation.",
    )
    inputs_by: Optional[str] = Field(
        None,
        title="Inputs By",
        # lib/galaxy/workflow/run_request.py - see line 60
        description="How inputs maps to inputs (datasets/collections) to workflows steps.",
    )
    effective_outputs: Optional[Any] = Field(
        None,
        title="Effective Outputs",
        # lib/galaxy/workflow/run_request.py - see line 455
    )
    preferred_intermediate_object_store_id: Optional[str] = Field(
        None,
        title="Preferred Intermediate Object Store ID",
        description="The ID of the ? object store that should be used to store ? datasets in this history.",
    )
    preferred_outputs_object_store_id: Optional[str] = Field(
        None,
        title="Preferred Outputs Object Store ID",
        description="The ID of the object store that should be used to store ? datasets in this history.",
    )
    preferred_object_store_id: Optional[str] = PreferredObjectStoreIdField


class StoredWorkflowDetailed(StoredWorkflowSummary):
    annotation: Optional[str] = AnnotationField  # Inconsistency? See comment on StoredWorkflowSummary.annotations
    license: Optional[str] = Field(
        None, title="License", description="SPDX Identifier of the license associated with this workflow."
    )
    version: int = Field(
        ..., title="Version", description="The version of the workflow represented by an incremental number."
    )
    inputs: Dict[int, WorkflowInput] = Field(
        {}, title="Inputs", description="A dictionary containing information about all the inputs of the workflow."
    )
    creator: WorkflowCreator
    steps: Dict[
        int,
        Annotated[
            Union[
                InputDataStep,
                InputDataCollectionStep,
                InputParameterStep,
                PauseStep,
                ToolStep,
                SubworkflowStep,
            ],
            Field(discriminator="type"),
        ],
    ] = Field(
        {},
        title="Steps",
        description="A dictionary with information about all the steps of the workflow.",
    )
    importable: Optional[bool] = Field(
        ...,
        title="Importable",
        description="Indicates if the workflow is importable by the current user.",
    )
    email_hash: Optional[str] = Field(
        ...,
        title="Email Hash",
        description="The hash of the email of the creator of this workflow",
    )
    slug: Optional[str] = Field(
        ...,
        title="Slug",
        description="The slug of the workflow.",
    )
    source_metadata: Optional[Dict[str, Any]] = Field(
        ...,
        title="Source Metadata",
        description="The source metadata of the workflow.",
    )


class SetWorkflowMenuPayload(Model):
    workflow_ids: Union[List[DecodedDatabaseIdField], DecodedDatabaseIdField] = Field(
        ...,
        title="Workflow IDs",
        description="The list of workflow IDs to set the menu entry for.",
    )


class SetWorkflowMenuSummary(Model):
    message: Optional[Any] = Field(
        ...,
        title="Message",
        description="The message of the operation.",
    )
    status: str = Field(
        ...,
        title="Status",
        description="The status of the operation.",
    )


# see lib/galaxy/tools/parameters/__init__.py - def populate_state
RunStepLiteralError = Literal[
    "The number of repeat elements is outside the range specified by the tool.",
    "The selected case is unavailable/invalid.",
]

# see lib/galaxy/tools/parameters/__init__.py - def check_param
RunStepValueError = Union[
    # ValueError,
    str,  # unicodify(ValueError)
]

# see lib/galaxy/tools/__init__.py - def to_json
RunStepError = Union[
    RunStepLiteralError,
    RunStepValueError,
]

# see lib/galaxy/workflow/modules.py - def get_errors
GeneralStepError = Union[
    Literal["Tool is not installed"],
    str,  # f"{self.tool_id} is not installed"
]

# see lib/galaxy/managers/workflows.py - _workflow_to_dict_*
StepError = Union[
    Dict[str, RunStepError],
    GeneralStepError,
    List[GeneralStepError],
]


# TODO control typing
# see lib/galaxy/managers/workflows.py - line 1555
class ExportDictStepToolOutput(Model):
    name: str = Field(
        ...,
        title="Export step output name",
    )
    type: str = Field(
        ...,
        title="Export step output type",
    )


# see lib/galaxy/tools/__init__.py - line 2404/2444
# lib/galaxy/tool_util/parser/output_objects.py - line 123
class RunStepToolOutput(Model):
    name: str = Field(
        ...,
    )
    format: str = Field(
        ...,
    )
    label: str = Field(
        ...,
    )
    hidden: bool = Field(
        ...,
    )
    output_type: str = Field(
        ...,
    )
    format_source: Optional[str] = Field(
        ...,
    )
    default_identifier_source: str = Field(
        ...,
    )
    metadata_source: str = Field(
        ...,
    )
    parent: Optional[str] = Field(
        ...,
    )
    count: int = Field(
        ...,
    )
    from_work_dir: Optional[bool] = Field(
        ...,
    )
    edam_format: str = Field(
        ...,
    )
    edam_data: str = Field(
        ...,
    )
    # see lib/galaxy/tool_util/parser/output_collection_def.py - line 78
    discover_datasets: List[Any] = Field(
        ...,
    )


# There is no need to model a class for the output of SubworkflowModule
# as it is equal to the output of one of the other modules


# see lib/galaxy/workflow/modules.py - line 1022
class InputDataModuleStepOutput(Model):
    name: Literal["output"] = Field(
        ...,
        title="Input data module step output name",
    )
    extensions: Union[str, List[str]] = Field(
        ...,
        title="Input data module step output extensions",
    )
    optional: bool = Field(
        ...,
        title="Is optional",
    )


# see lib/galaxy/workflow/modules.py - line 1136
class InputDataCollectionModuleStepOutput(Model):
    name: Literal["output"] = Field(
        ...,
        title="Input data collection module step output name",
    )
    extensions: Union[str, List[str]] = Field(
        ...,
        title="Input data collection module step output extensions",
    )
    collection: Literal[True] = Field(
        ...,
        title="Is collection",
    )
    collection_type: str = Field(
        ...,
        title="Input data collection module step output collection type",
    )
    optional: bool = Field(
        ...,
        title="Is optional",
    )


# see lib/galaxy/workflow/modules.py - line 1519
class InputParameterModuleStepOutput(Model):
    name: Literal["output"] = Field(
        ...,
        title="Input data module step output name",
    )
    label: str = Field(
        ...,
        title="Input data module step output label",
    )
    type: str = Field(
        ...,
        title="Input data module step output parameter type",
    )
    optional: bool = Field(
        ...,
        title="Is optional",
    )
    parameter: Literal[True] = Field(
        ...,
        title="Is parameter",
    )


# see lib/galaxy/workflow/modules.py - line 1673
class PauseModuleStepOutput(Model):
    name: Literal["output"] = Field(
        ...,
        title="Pause module step output name",
    )
    label: Literal["Reviewed Dataset"] = Field(
        ...,
        title="Pause module step output label",
    )
    extension: List[Literal["input"]] = Field(
        ...,
    )


# see lib/galaxy/workflow/modules.py - line 1932
class ToolModuleStepOutput(Model):
    name: str = Field(
        ...,
        title="Tool module step output name",
    )
    extensions: List[str] = Field(
        ...,
        title="Tool module step output extensions",
    )
    type: str = Field(
        ...,
        title="Tool module step output type",
    )
    optional: Literal[False] = Field(..., title="Is optional")
    parameter: Literal[True] = Field(
        ...,
        title="Is parameter",
    )
    collection: Literal[True] = Field(
        ...,
        title="Is collection",
    )
    collection_type: str = Field(
        ...,
        title="Tool module step output collection type",
    )
    collection_type_source: str = Field(
        ...,
    )
    label: Any = Field(
        ...,
        title="Tool module step output label",
    )


# used by: WorkflowDictEditorStep
ModulesStepOutput = Union[
    InputDataModuleStepOutput,
    InputDataCollectionModuleStepOutput,
    InputParameterModuleStepOutput,
    PauseModuleStepOutput,
    ToolModuleStepOutput,
]


class WorkflowDictStepsBase(Model):
    when: Optional[str] = Field(
        None,
        title="When",
        description="The when expression for the step.",
    )
    # We should eventually clean this up, `Dict[str, PostJobAction]]` is probably the better form.
    post_job_actions: Optional[Union[List[PostJobAction], Dict[str, PostJobAction]]] = Field(
        None,
        title="Post Job Actions",
        description="Set of actions that will be run when the job finishes.",
    )
    tool_version: Optional[str] = Field(
        None,
        title="Tool Version",
        description="The version of the tool associated with the step.",
    )
    errors: Optional[StepError] = Field(
        None,
        title="Errors",
        description="An message indicating possible errors in the step.",
    )
    position: Optional[WorkflowStepLayoutPosition] = Field(
        None,
        title="Position",
        description="Layout position of this step in the graph",
    )
    # TODO: model outputs
    # # outputs: Optional[List[Dict[str, Any]]] = Field(
    #     None,
    #     title="Outputs",
    #     description="The outputs of the step.",
    # )
    tool_state: Optional[Union[Dict[str, Any], str]] = Field(
        None,
        title="Tool State",
        description="The state of the tool associated with the step",
    )
    content_id: Optional[str] = Field(
        None,
        title="Content ID",
        description="The content ID of the step.",
    )
    workflow_outputs: Optional[List[WorkflowOutput]] = Field(
        None,
        title="Workflow Outputs",
        description="Workflow outputs associated with this step.",
    )

    # @field_validator(
    #     "tool_state",
    #     mode="before",
    #     check_fields=False,
    # )
    # @classmethod
    # def inputs_string_to_json(cls, v):
    #     if isinstance(v, str):
    #         return json.loads(v)
    #     return v


class WorkflowDictStepsExtendedBase(WorkflowDictStepsBase):
    type: str = Field(
        ...,
        title="Type",
        description="The type of the module that represents a step in the workflow.",
    )
    label: Optional[str] = Field(
        None,
        title="Label",
        description="The label of the step.",
    )


class WorkflowDictRunStep(WorkflowDictStepsBase):
    inputs: List[Dict[str, Any]] = Field(
        ...,
        title="Inputs",
        description="The inputs of the step.",
    )
    replacement_parameters: Optional[List[Union[str, Dict[str, Any]]]] = Field(
        None,
        title="Replacement Parameters",
        description="Informal replacement parameters for the step.",
    )
    step_name: str = Field(..., title="Step Name", description="The descriptive name of the module or step.")
    step_version: Optional[str] = Field(
        None,
        title="Step Version",
        description="The version of the step's module.",
    )
    step_index: int = Field(
        ...,
        title="Step Index",
        description="The order index of the step.",
    )
    tool_id: Optional[str] = Field(  # Duplicate of `content_id` or viceversa?
        None,
        title="Tool ID",
        description="The unique name of the tool associated with this step.",
    )
    output_connections: List[Dict[str, Any]] = Field(
        ...,
        title="Output Connections",
        description="The output connections of the step.",
    )
    annotation: WorkflowAnnotationField = None
    messages: Optional[List[str]] = Field(
        None,
        title="Messages",
        description="Upgrade messages for the step.",
    )
    step_type: str = Field(
        ...,
        title="Step Type",
        description="The type of the step.",
    )
    step_label: Optional[str] = Field(
        None,
        title="Step Label",
        description="The label of the step.",
    )


class WorkflowDictRunToolStep(WorkflowDictRunStep):
    # TODO: remove everything that can be gotten through the tool store
    outputs: List[RunStepToolOutput] = Field(
        ...,
        title="Outputs",
        description="The outputs of the step.",
    )
    model_class: Literal["tool"] = Field(
        ...,
        title="Model Class",
        description="The model class of the tool step.",
    )
    id: str = Field(
        ...,
        title="ID",
        description="The identifier of the tool step.",
    )
    name: str = Field(
        ...,
        title="Name",
        description="The name of the tool step.",
    )
    version: str = Field(
        ...,
        title="Version",
        description="The version of the tool step.",
    )
    description: str = Field(
        ...,
        title="Description",
        description="The description of the tool step.",
    )
    labels: List[str] = Field(
        ...,
        title="Labels",
        description="The labels of the tool step.",
    )
    edam_operations: List[str] = Field(
        ...,
        title="EDAM Operations",
        description="The EDAM operations of the tool step.",
    )
    edam_topics: List[str] = Field(
        ...,
        title="EDAM Topics",
        description="The EDAM topics of the tool step.",
    )
    hidden: str = Field(
        ...,
        title="Hidden",
        description="The hidden status of the tool step.",
    )
    is_workflow_compatible: bool = Field(
        ...,
        title="Is Workflow Compatible",
        description="Indicates if the tool step is compatible with workflows.",
    )
    xrefs: List[str] = Field(
        ...,
        title="XRefs",
        description="The cross-references of the tool step.",
    )
    panel_section_id: str = Field(
        ...,
        title="Panel Section ID",
        description="The panel section ID of the tool step.",
    )
    panel_section_name: str = Field(
        ...,
        title="Panel Section Name",
        description="The panel section name of the tool step.",
    )
    form_style: str = Field(
        ...,
        title="Form Style",
        description="The form style of the tool step.",
    )
    help: str = Field(
        ...,
        title="Help",
        description="The help of the tool step.",
    )
    citations: bool = Field(
        ...,
        title="Citations",
        description="The citations of the tool step.",
    )
    sharable_url: Optional[str] = Field(
        None,
        title="Sharable URL",
        description="The sharable URL of the tool step.",
    )
    message: str = Field(
        ...,
        title="Message",
        description="The message of the tool step.",
    )
    warnings: Optional[str] = Field(
        None,
        title="Warnings",
        description="The warnings of the tool step.",
    )
    versions: List[str] = Field(
        ...,
        title="Versions",
        description="The versions of the tool step.",
    )
    requirements: List[str] = Field(
        ...,
        title="Requirements",
        description="The requirements of the tool step.",
    )
    tool_errors: Optional[str] = Field(
        None,
        title="Tool Errors",
        description="An message indicating possible errors in the tool step.",
    )
    state_inputs: Dict[str, Any] = Field(
        ...,
        title="State Inputs",
        description="The state inputs of the tool step.",
    )
    job_id: Optional[str] = Field(
        None,
        title="Job ID",
        description="The ID of the job associated with the tool step.",
    )
    job_remap: Optional[str] = Field(
        None,
        title="Job Remap",
        description="The remap of the job associated with the tool step.",
    )
    history_id: str = Field(
        ...,
        title="History ID",
        description="The ID of the history associated with the tool step.",
    )
    display: bool = Field(
        ...,
        title="Display",
        description="Indicates if the tool step should be displayed.",
    )
    action: str = Field(
        ...,
        title="Action",
        description="The action of the tool step.",
    )
    license: Optional[str] = Field(
        None,
        title="License",
        description="The license of the tool step.",
    )
    creator: Optional[str] = Field(
        None,
        title="Creator",
        description="The creator of the tool step.",
    )
    method: str = Field(
        ...,
        title="Method",
        description="The method of the tool step.",
    )
    enctype: str = Field(
        ...,
        title="Enctype",
        description="The enctype of the tool step.",
    )
    tool_shed_repository: Optional[ToolShedRepositorySummary] = Field(
        None,
        title="Tool Shed Repository",
        description="Information about the tool shed repository associated with the tool.",
    )
    link: Optional[str] = Field(
        None,
        title="Link",
        description="The link of the tool step.",
    )
    # TODO - see lib/galaxy/tools/__init__.py - class Tool - to_dict for further typing
    min_width: Optional[Any] = Field(
        None,
        title="Min Width",
        description="The minimum width of the tool step.",
    )
    # TODO - see lib/galaxy/tools/__init__.py - class Tool - to_dict for further typing
    target: Optional[Any] = Field(
        None,
        title="Target",
        description="The target of the tool step.",
    )
    tool_id: str = Field(  # Duplicate of `content_id` or viceversa?
        ...,
        title="Tool ID",
        description="The unique name of the tool associated with this step.",
    )


class WorkflowDictPreviewStep(WorkflowDictStepsExtendedBase):
    order_index: int = Field(
        ...,
        title="Order Index",
        description="The order index of the step.",
    )
    annotation: WorkflowAnnotationField = None
    label: str = Field(
        ...,
        title="Label",
        description="The label of the step.",
    )
    inputs: List[Dict[str, Any]] = Field(
        ...,
        title="Inputs",
        description="The inputs of the step.",
    )
    tool_id: Optional[str] = Field(  # Duplicate of `content_id` or viceversa?
        None,
        title="Tool ID",
        description="The unique name of the tool associated with this step.",
    )


class WorkflowDictEditorStep(WorkflowDictStepsExtendedBase):
    id: int = Field(
        ...,
        title="ID",
        description="The identifier of the step. It matches the index order of the step inside the workflow.",
    )
    name: Optional[str] = Field(
        None,
        title="Name",
        description="The descriptive name of the module or step.",
    )
    inputs: Optional[List[Dict[str, Any]]] = Field(
        None,
        title="Inputs",
        description="The inputs of the step.",
    )
    config_form: Optional[Dict[str, Any]] = Field(
        None,
        title="Config Form",
        description="The configuration form for the step.",
    )
    annotation: WorkflowAnnotationField
    uuid: Optional[UUID4] = Field(
        None,
        title="UUID",
        description="Universal unique identifier of the workflow.",
    )
    tooltip: Optional[str] = Field(
        None,
        title="Tooltip",
        description="The tooltip for the step.",
    )
    input_connections: Optional[Dict[str, Union[InputConnectionEditor, List[InputConnectionEditor]]]] = Field(
        # input_connections: Optional[Dict[str, Any]] = Field(
        None,
        title="Input Connections",
        description="The input connections for the step.",
    )
    tool_id: Optional[str] = Field(  # Duplicate of `content_id` or viceversa?
        None,
        title="Tool ID",
        description="The unique name of the tool associated with this step.",
    )
    outputs: Optional[List[ModulesStepOutput]] = Field(
        None,
        title="Outputs",
        description="The outputs of the step.",
    )


class WorkflowDictExportStep(WorkflowDictStepsExtendedBase):
    id: int = Field(
        ...,
        title="ID",
        description="The identifier of the step. It matches the index order of the step inside the workflow.",
    )
    name: str = Field(
        ...,
        title="Name",
        description="The descriptive name of the module or step.",
    )
    uuid: UUID4 = Field(
        ...,
        title="UUID",
        description="Universal unique identifier of the workflow.",
    )
    annotation: WorkflowAnnotationField = None
    tool_shed_repository: Optional[ToolShedRepositorySummary] = Field(
        None,
        title="Tool Shed Repository",
        description="Information about the tool shed repository associated with the tool.",
    )
    tool_representation: Optional[Dict[str, Any]] = Field(
        None,
        title="Tool Representation",
        description="The representation of the tool associated with the step.",
    )
    subworkflow: Optional["WorkflowDictExportSummary"] = Field(
        None,
        title="Sub Workflow",
        description="Full information about the subworkflow associated with this step.",
    )
    tool_id: Optional[str] = Field(  # Duplicate of `content_id` or viceversa?
        None,
        title="Tool ID",
        description="The unique name of the tool associated with this step.",
    )
    inputs: Optional[List[WorkflowDictExportStepInput]] = Field(
        None,
        title="Inputs",
        description="The inputs of the step.",
    )
    outputs: Optional[List[ExportDictStepToolOutput]] = Field(
        None,
        title="Outputs",
        description="The outputs of the step.",
    )
    in_parameter: Optional[Dict[str, StepIn]] = Field(None, title="In", alias="in")
    input_connections: Optional[Dict[str, Union[InputConnectionExport, List[InputConnectionExport]]]] = Field(
        None,
        title="Input Connections",
        description="The input connections of the step.",
    )


class WorkflowDictBaseModel(Model):
    name: str = Field(
        ...,
        title="Name",
        description="The name of the workflow.",
    )


class WorkflowDictExtendedBaseModel(WorkflowDictBaseModel):
    version: int = Field(
        ...,
        title="Version",
        description="The version of the workflow represented by an incremental number.",
    )


class WorkflowDictPreviewSummary(WorkflowDictExtendedBaseModel):
    steps: List[WorkflowDictPreviewStep] = Field(
        ...,
        title="Steps",
        description="Information about all the steps of the workflow.",
    )


class WorkflowDictEditorSummary(WorkflowDictExtendedBaseModel):
    upgrade_messages: Dict[int, str] = Field(
        ...,
        title="Upgrade Messages",
        description="Upgrade messages for each step in the workflow.",
    )
    # TODO - can this be modeled further? see manager method _workflow_to_dict_editor
    report: Dict[str, Any] = Field(
        ...,
        title="Report",
        description="The reports configuration for the workflow.",
    )
    comments: List[WorkflowCommentModel] = Field(
        ...,
        title="Comments",
        description="Comments on the workflow.",
    )
    annotation: WorkflowAnnotationField
    license: Optional[str] = Field(
        ...,
        title="License",
        description="SPDX Identifier of the license associated with this workflow.",
    )
    creator: WorkflowCreator
    source_metadata: Optional[Dict[str, Any]] = Field(
        ...,
        title="Source Metadata",
        description="Metadata about the source of the workflow",
    )
    steps: Dict[int, WorkflowDictEditorStep] = Field(
        ...,
        title="Steps",
        description="Information about all the steps of the workflow.",
    )


class WorkflowDictRunSummary(WorkflowDictExtendedBaseModel):
    id: str = Field(
        ...,
        title="ID",
        description="The encoded ID of the stored workflow.",
    )
    history_id: Optional[str] = Field(
        None,
        title="History ID",
        description="The encoded ID of the history associated with the workflow.",
    )
    step_version_changes: List[Union[str, Dict[str, Any]]] = Field(
        ...,
        title="Step Version Changes",
        description="Version changes for the workflow steps.",
    )
    has_upgrade_messages: bool = Field(
        ...,
        title="Has Upgrade Messages",
        description="Whether the workflow has upgrade messages.",
    )
    workflow_resource_parameters: Optional[Dict[str, Any]] = Field(
        ...,
        title="Workflow Resource Parameters",
        description="The resource parameters of the workflow.",
    )
    steps: List[Union[WorkflowDictRunToolStep, WorkflowDictRunStep]] = Field(
        ...,
        title="Steps",
        description="Information about all the steps of the workflow.",
    )


class WorkflowDictExportSummary(WorkflowDictBaseModel):
    a_galaxy_workflow: Literal["true"] = Field(
        # a_galaxy_workflow: str = Field(
        ...,
        title="A Galaxy Workflow",
        description="Whether this workflow is a Galaxy Workflow.",
    )
    version: Optional[int] = Field(
        None,
        title="Version",
        description="The version of the workflow represented by an incremental number.",
    )
    format_version: Literal["0.1"] = Field(
        # format_version: str = Field(
        ...,
        alias="format-version",
        title="Format Version",
        description="The version of the workflow format being used.",
    )
    annotation: WorkflowAnnotationField
    tags: Union[TagCollection, List[Literal[""]]] = Field(
        ...,
        title="Tags",
        description="The tags associated with the workflow.",
    )
    uuid: Optional[UUID4] = Field(
        None,
        title="UUID",
        description="The UUID (Universally Unique Identifier) of the workflow.",
    )
    comments: List[WorkflowCommentModel] = Field(
        # comments: List[Dict[str, Any]] = Field(
        ...,
        title="Comments",
        description="Comments associated with the workflow.",
    )
    report: Optional[Dict[str, Any]] = Field(
        None,
        title="Report",
        description="The configuration for generating a report for the workflow.",
    )
    creator: WorkflowCreator
    license: Optional[str] = Field(
        None,
        title="License",
        description="SPDX Identifier of the license associated with this workflow.",
    )
    source_metadata: Optional[Dict[str, Any]] = Field(
        None,
        title="Source Metadata",
        description="Metadata about the source of the workflow.",
    )
    steps: Dict[int, WorkflowDictExportStep] = Field(
        ...,
        title="Steps",
        description="Information about all the steps of the workflow.",
    )


class WorkflowDictFormat2Summary(Model):
    workflow_class: Literal["GalaxyWorkflow"] = Field(
        ...,
        title="Class",
        description="The class of the workflow.",
        alias="class",
    )
    label: Optional[str] = Field(
        None,
        title="Label",
        description="The label or name of the workflow.",
    )
    creator: WorkflowCreator
    license: Optional[str] = Field(
        None,
        title="License",
        description="SPDX Identifier of the license associated with this workflow.",
    )
    release: Optional[str] = Field(
        None,
        title="Release",
        description="The release information for the workflow.",
    )
    tags: Optional[TagCollection] = Field(
        None,
        title="Tags",
        description="The tags associated with the workflow.",
    )
    uuid: Optional[UUID4] = Field(
        None,
        title="UUID",
        description="The UUID (Universally Unique Identifier) of the workflow.",
    )
    report: Optional[Dict[str, Any]] = Field(
        None,
        title="Report",
        description="The configuration for generating a report for the workflow.",
    )
    inputs: Dict[str, Any] = Field(
        ...,
        title="Inputs",
        description="The inputs of the workflow.",
    )
    outputs: Dict[str, Any] = Field(
        ...,
        title="Outputs",
        description="The outputs of the workflow.",
    )
    # TODO - can be modeled further see manager method workflow_to_dict
    steps: Dict[str, Any] = Field(
        ...,
        title="Steps",
        description="Information about all the steps of the workflow.",
    )
    doc: WorkflowAnnotationField = None


class WorkflowDictFormat2WrappedYamlSummary(Model):
    # TODO What type is this?
    yaml_content: Any = Field(
        ...,
        title="YAML Content",
        # description="Safe and ordered dump of YAML to stream",
        description="The content of the workflow in YAML .",
    )
