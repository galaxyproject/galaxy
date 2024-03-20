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
)
from typing_extensions import Annotated

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
    ToolStep,
    WorkflowInput,
)

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


class GetTargetHistoryPayload(Model):
    # TODO - Are the descriptions correct?
    history: Optional[str] = Field(
        None,
        title="History",
        # description="The encoded history id - passed exactly like this 'hist_id=...' -  to import the workflow into. Or the name of the new history to import the workflow into.",
        description="The encoded history id - passed exactly like this 'hist_id=...' -  into which to import. Or the name of the new history into which to import.",
    )
    history_id: Optional[str] = Field(
        None,
        title="History ID",
        # description="The history to import the workflow into.",
        description="The encoded history id into which to import.",
    )
    new_history_name: Optional[str] = Field(
        None,
        title="New History Name",
        # description="The name of the new history to import the workflow into.",
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
        # description="TODO",
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
        description="TODO",
    )
    ds_map: Optional[Dict[str, Dict[str, Any]]] = Field(
        {},
        title="Dataset Map",
        description="TODO",
    )
    resource_params: Optional[Dict[str, Any]] = Field(
        {},
        title="Resource Parameters",
        description="TODO",
    )
    replacement_params: Optional[Dict[str, Any]] = Field(
        {},
        title="Replacement Parameters",
        description="TODO",
    )
    step_parameters: Optional[Dict[str, Any]] = Field(
        None,
        title="Step Parameters",
        description="TODO",
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
        description="TODO",
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


class WorkflowDictStepsBase(Model):
    when: Optional[str] = Field(
        None,
        title="When",
        description="The when expression for the step.",
    )
    # TODO - could be modeled further see manager
    post_job_actions: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = Field(
        None,
        title="Post Job Actions",
        description="A dictionary of post-job actions for the step.",
    )
    tool_version: Optional[str] = Field(
        None,
        title="Tool Version",
        description="The version of the tool associated with the step.",
    )
    errors: Optional[Union[List[str], str, Dict[str, Any]]] = Field(
        None,
        title="Errors",
        description="Any errors associated with the step.",
    )
    tool_id: Optional[str] = Field(
        None,
        title="Tool ID",
        description="The tool ID associated with the step.",
    )
    position: Optional[Any] = Field(
        None,
        title="Position",
        description="The position of the step.",
    )
    # TODO - can be modeled further see manager
    outputs: Optional[List[Dict[str, Any]]] = Field(
        None,
        title="Outputs",
        description="The outputs of the step.",
    )
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
    # TODO - could be modeled further see manager
    workflow_outputs: Optional[List[Dict[str, Any]]] = Field(
        None,
        title="Workflow Outputs",
        description="A list of workflow outputs for the step.",
    )


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


# TODO - This is potentially missing some fields, when step type is tool - see manager line 1006 - TODO
class WorkflowDictRunSteps(WorkflowDictStepsBase):
    inputs: List[Dict[str, Any]] = Field(
        ...,
        title="Inputs",
        description="The inputs of the step.",
    )
    replacement_parameters: Optional[List[Dict[str, Any]]] = Field(
        None,
        title="Replacement Parameters",
        description="Informal replacement parameters for the step.",
    )
    step_name: str = Field(
        ...,
        title="Step Name",
        description="The name of the step's module.",
    )
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
    output_connections: List[Dict[str, Any]] = Field(
        ...,
        title="Output Connections",
        description="A list of dictionaries representing the output connections of the step.",
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


class WorkflowDictPreviewSteps(WorkflowDictStepsExtendedBase):
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


class WorkflowDictEditorSteps(WorkflowDictStepsExtendedBase):
    id: int = Field(
        ...,
        title="ID",
        description="The order index of the step.",
    )
    name: Optional[str] = Field(
        None,
        title="Name",
        description="The name of the step.",
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
    uuid: Optional[str] = Field(
        None,
        title="UUID",
        description="The UUID of the step.",
    )
    tooltip: Optional[str] = Field(
        None,
        title="Tooltip",
        description="The tooltip for the step.",
    )
    input_connections: Optional[Dict[str, Any]] = Field(
        None,
        title="Input Connections",
        description="A dictionary representing the input connections for the step.",
    )


class WorkflowDictExportSteps(WorkflowDictStepsExtendedBase):
    id: int = Field(
        ...,
        title="ID",
        description="The order index of the step.",
    )
    name: str = Field(
        ...,
        title="Name",
        description="The name of the step.",
    )
    uuid: str = Field(
        ...,
        title="UUID",
        description="The UUID (Universally Unique Identifier) of the step.",
    )
    annotation: WorkflowAnnotationField = None
    # TODO - can be modeled see manager line 1483 or below
    tool_shed_repository: Optional[Dict[str, Any]] = Field(
        None,
        title="Tool Shed Repository",
        description="Information about the tool shed repository associated with the tool.",
    )
    # "name" (type: str): The name of the tool shed repository.
    # "owner" (type: str): The owner of the tool shed repository.
    # "changeset_revision" (type: str): The changeset revision of the tool shed repository.
    # "tool_shed" (type: str): The tool shed URL.
    tool_representation: Optional[Dict[str, Any]] = Field(
        None,
        title="Tool Representation",
        description="The representation of the tool associated with the step.",
    )
    # TODO - can also be WorkflowDictExportSummary see manager line 1512
    subworkflow: Optional[Dict[str, Any]] = Field(
        None,
        title="Sub Workflow",
        description="The sub-workflow associated with the step.",
    )
    # TODO - can be modeled see manager line 1516 -1532
    inputs: Optional[List[Dict[str, Any]]] = Field(
        None,
        title="Inputs",
        description="The inputs of the step.",
    )
    # TODO - can be modeled see manager line 1551
    in_parameter: Optional[Dict[str, Any]] = Field(
        None, title="In", description="The input connections of the step.", alias="in"
    )
    input_connections: Optional[Dict[str, Union[Dict[str, Any], List[Dict[str, Any]]]]] = Field(
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
    version: int = Field(
        ...,
        title="Version",
        description="The version of the workflow.",
    )


class WorkflowDictPreviewSummary(WorkflowDictBaseModel):
    steps: List[WorkflowDictPreviewSteps] = Field(
        ...,
        title="Steps",
        description="A dictionary with information about all the steps of the workflow.",
    )


class WorkflowDictEditorSummary(WorkflowDictBaseModel):
    upgrade_messages: Dict[int, str] = Field(
        ...,
        title="Upgrade Messages",
        description="Upgrade messages for each step in the workflow.",
    )
    report: Dict[str, Any] = Field(
        ...,
        title="Report",
        description="The reports configuration for the workflow.",
    )
    comments: List[Dict[str, Any]] = Field(
        ...,
        title="Comments",
        description="Comments on the workflow.",
    )
    annotation: WorkflowAnnotationField
    license: Optional[str] = Field(
        None,
        title="License",
        description="The license information for the workflow.",
    )
    creator: WorkflowCreator
    source_metadata: Optional[Dict[str, Any]] = Field(
        None,
        title="Source Metadata",
        description="Metadata about the source of the workflow",
    )
    steps: Dict[int, WorkflowDictEditorSteps] = Field(
        ...,
        title="Steps",
        description="A dictionary with information about all the steps of the workflow.",
    )


class WorkflowDictRunSummary(WorkflowDictBaseModel):
    id: Optional[str] = Field(
        None,
        title="ID",
        description="The encoded ID of the stored workflow.",
    )
    history_id: Optional[str] = Field(
        None,
        title="History ID",
        description="The encoded ID of the history associated with the workflow (or None if not applicable).",
    )
    step_version_changes: Optional[List[Dict[str, Any]]] = Field(
        None,
        title="Step Version Changes",
        description="A list of version changes for the workflow steps.",
    )
    has_upgrade_messages: Optional[bool] = Field(
        None,
        title="Has Upgrade Messages",
        description="A boolean indicating whether the workflow has upgrade messages.",
    )
    workflow_resource_parameters: Optional[Dict[str, Any]] = Field(
        None,
        title="Workflow Resource Parameters",
        description="The resource parameters of the workflow.",
    )
    steps: List[WorkflowDictRunSteps] = Field(
        ...,
        title="Steps",
        description="A dictionary with information about all the steps of the workflow.",
    )


class WorkflowDictExportSummary(WorkflowDictBaseModel):
    a_galaxy_workflow: Optional[str] = Field(
        None,
        title="A Galaxy Workflow",
        description="Is a Galaxy workflow.",
    )
    format_version: Optional[str] = Field(
        None,
        alias="format-version",
        title="Format Version",
        description="The version of the workflow format being used.",
    )
    annotation: WorkflowAnnotationField
    tags: Optional[List[str]] = Field(
        None,
        title="Tags",
        description="The tags associated with the workflow.",
    )
    uuid: Optional[str] = Field(
        None,
        title="UUID",
        description="The UUID (Universally Unique Identifier) of the workflow, represented as a string.",
    )
    comments: Optional[List[Dict[str, Any]]] = Field(
        None,
        title="Comments",
        description="A list of dictionaries representing comments associated with the workflow.",
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
        description="The license information for the workflow.",
    )
    source_metadata: Optional[Dict[str, Any]] = Field(
        None,
        title="Source Metadata",
        description="Metadata about the source of the workflow.",
    )
    steps: Dict[int, WorkflowDictExportSteps] = Field(
        ...,
        title="Steps",
        description="A dictionary with information about all the steps of the workflow.",
    )


class WorkflowDictFormat2Summary(Model):
    workflow_class: str = Field(
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
        description="The license information for the workflow.",
    )
    release: Optional[str] = Field(
        None,
        title="Release",
        description="The release information for the workflow.",
    )
    tags: Optional[List[str]] = Field(
        None,
        title="Tags",
        description="The tags associated with the workflow.",
    )
    uuid: Optional[str] = Field(
        None,
        title="UUID",
        description="The UUID (Universally Unique Identifier) of the workflow, represented as a string.",
    )
    report: Optional[Dict[str, Any]] = Field(
        None,
        title="Report",
        description="The configuration for generating a report for the workflow.",
    )
    inputs: Optional[Dict[str, Any]] = Field(
        None,
        title="Inputs",
        description="A dictionary representing the inputs of the workflow.",
    )
    outputs: Optional[Dict[str, Any]] = Field(
        None,
        title="Outputs",
        description="A dictionary representing the outputs of the workflow.",
    )
    # TODO - step into line 888 in manager
    steps: Dict[str, Any] = Field(
        ...,
        title="Steps",
        description="A dictionary representing the steps of the workflow.",
    )
    doc: WorkflowAnnotationField = None


class WorkflowDictFormat2WrappedYamlSummary(Model):
    yaml_content: Any = Field(
        ...,
        title="YAML Content",
        description="The content of the workflow in YAML format.",
    )
