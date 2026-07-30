import json
from enum import Enum
from typing import (
    Annotated,
    Any,
    Literal,
)

from pydantic import (
    AfterValidator,
    Field,
    field_validator,
    model_validator,
    UUID4,
)

from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    EncodedDatabaseIdField,
)
from galaxy.schema.schema import (
    AnnotationField,
    CreatorOrganization,
    DatasetState,
    HistoryContentType,
    InputDataCollectionStep,
    InputDataStep,
    InputParameterStep,
    Model,
    PauseStep,
    Person,
    StoredWorkflowSummary,
    SubworkflowStep,
    ToolStep,
    WorkflowInput,
)

TargetHistoryIdField = Field(
    None,
    title="History ID",
    # description="The history to import the workflow into.",
    description="The encoded history id into which to import.",
)
INPUTS_BY_DESCRIPTION = (
    "How the 'inputs' field maps its inputs (datasets/collections/step parameters) to workflows steps."
)
STEP_PARAMETERS_NORMALIZED_TITLE = "Legacy Step Parameters Normalized"
STEP_PARAMETERS_NORMALIZED_DESCRIPTION = "Indicates if legacy parameters are already normalized to be indexed by the order_index and are specified as a dictionary per step. Legacy-style parameters could previously be specified as one parameter per step or by tool ID."
STEP_PARAMETERS_TITLE = "Legacy Step Parameters"
STEP_PARAMETERS_DESCRIPTION = "Parameters specified per-step for the workflow invocation, this is legacy and you should generally use inputs and only specify the formal parameters of a workflow instead."
ReplacementParametersField = Field(
    None,
    title="Replacement Parameters",
    description="Class of parameters mostly used for string replacement in PJAs. In best practice workflows, these should be replaced with input parameters",
)
UseCachedJobField = Field(
    False,
    title="Use cached job",
    description="Indicated whether to use a cached job for workflow invocation.",
)
PreferredObjectStoreIdField = Field(
    default=None,
    title="Preferred Object Store ID",
    description="The ID of the object store that should be used to store all datasets (can instead specify object store IDs for intermediate and outputs datasts separately) -  - Galaxy's job configuration may override this in some cases but this workflow preference will override tool and user preferences",
)
PreferredIntermediateObjectStoreIdField = Field(
    None,
    title="Preferred Intermediate Object Store ID",
    description="The ID of the object store that should be used to store the intermediate datasets of this workflow -  - Galaxy's job configuration may override this in some cases but this workflow preference will override tool and user preferences",
)
PreferredOutputsObjectStoreIdField = Field(
    None,
    title="Preferred Outputs Object Store ID",
    description="The ID of the object store that should be used to store the marked output datasets of this workflow - Galaxy's job configuration may override this in some cases but this workflow preference will override tool and user preferences.",
)
ResourceParametersField = Field(
    None,
    title="Resource Parameters",
    description="If a workflow_resource_params_file file is defined and the target workflow is configured to consumer resource parameters, they can be specified with this parameter. See https://github.com/galaxyproject/galaxy/pull/4830 for more information.",
)

VALID_INPUTS_BY_ITEMS = ["step_id", "step_index", "step_uuid", "name"]


def validateInputsBy(inputsBy: str | None) -> str | None:
    if inputsBy is not None:
        if not isinstance(inputsBy, str):
            raise ValueError(f"Invalid type for inputsBy {inputsBy}")
        inputsByArray: list[str] = inputsBy.split("|")
        for inputsByItem in inputsByArray:
            if inputsByItem not in VALID_INPUTS_BY_ITEMS:
                raise ValueError(f"Invalid inputsBy delineation {inputsByItem}")
    return inputsBy


InputsByValidator = AfterValidator(validateInputsBy)


class GetTargetHistoryPayload(Model):
    # TODO - Are the descriptions correct?
    history: str | None = Field(
        None,
        title="History",
        # description="The encoded history id - passed exactly like this 'hist_id=...' -  to import the workflow into. Or the name of the new history to import the workflow into.",
        description="The encoded history id - passed exactly like this 'hist_id=...' -  into which to import. Or the name of the new history into which to import.",
    )
    history_id: str | None = TargetHistoryIdField
    new_history_name: str | None = Field(
        None,
        title="New History Name",
        # description="The name of the new history to import the workflow into.",
        description="The name of the new history into which to import.",
    )


class InvokeWorkflowPayload(GetTargetHistoryPayload):
    # TODO - Are the descriptions correct?
    version: int | None = Field(
        None,
        title="Version",
        description="The version of the workflow to invoke.",
    )
    instance: bool | None = Field(
        False,
        title="Is instance",
        description="True when fetching by Workflow ID, False when fetching by StoredWorkflow ID",
    )
    scheduler: str | None = Field(
        None,
        title="Scheduler",
        description="Scheduler to use for workflow invocation.",
    )
    batch: bool | None = Field(
        False,
        title="Batch",
        description="Indicates if the workflow is invoked as a batch.",
    )
    require_exact_tool_versions: bool | None = Field(
        True,
        title="Require Exact Tool Versions",
        description="If true, exact tool versions are required for workflow invocation.",
        # description="TODO",
    )
    allow_tool_state_corrections: bool | None = Field(
        False,
        title="Allow tool state corrections",
        description="Indicates if tool state corrections are allowed for workflow invocation.",
    )
    landing_uuid: UUID4 | None = Field(
        None,
        title="Landing UUID",
        description="The UUID of the workflow landing request associated with this invocation.",
    )
    use_cached_job: bool | None = UseCachedJobField
    parameters_normalized: bool | None = Field(
        False,
        title=STEP_PARAMETERS_NORMALIZED_TITLE,
        description=STEP_PARAMETERS_NORMALIZED_DESCRIPTION,
    )
    on_complete: list[dict[str, Any]] | None = Field(
        None,
        title="On Complete Actions",
        description=(
            "List of actions to execute when the workflow invocation completes. "
            "Each action is an object with the action name as key and configuration as value. "
            "Available actions: 'send_notification' (notify user, no config required), "
            "'export_to_file_source' (export results, requires target_uri). "
            "Example: [{'send_notification': {}}, {'export_to_file_source': {"
            "'target_uri': 'gxfiles://my_storage/exports/', 'format': 'rocrate.zip'}}]"
        ),
    )

    @field_validator(
        "parameters",
        "inputs",
        "ds_map",
        "resource_params",
        "replacement_params",
        mode="before",
        check_fields=False,
    )
    @classmethod
    def inputs_string_to_json(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    parameters: dict[str, dict[str, Any]] | None = Field(
        {},
        title=STEP_PARAMETERS_TITLE,
        description=STEP_PARAMETERS_DESCRIPTION,
    )
    inputs: dict[str, Any] | None = Field(
        None,
        title="Inputs",
        description="Specify values for formal inputs to the workflow",
    )
    ds_map: dict[str, dict[str, Any]] | None = Field(
        {},
        title="Legacy Dataset Map",
        description="An older alternative to specifying inputs using database IDs, do not use this and use inputs instead",
        deprecated=True,
    )
    resource_params: dict[str, Any] | None = ResourceParametersField
    replacement_params: dict[str, Any] | None = ReplacementParametersField
    no_add_to_history: bool | None = Field(
        False,
        title="No Add to History",
        description="Indicates if the workflow invocation should not be added to the history.",
    )
    legacy: bool | None = Field(
        False,
        title="Legacy",
        description="Indicating if to use legacy workflow invocation.",
    )
    inputs_by: Annotated[str | None, InputsByValidator] = Field(
        None,
        title="Inputs By",
        # lib/galaxy/workflow/run_request.py - see line 60
        description=INPUTS_BY_DESCRIPTION,
    )
    effective_outputs: Any | None = Field(
        None,
        title="Effective Outputs",
        # lib/galaxy/workflow/run_request.py - see line 455
        description="TODO",
    )
    preferred_object_store_id: str | None = PreferredObjectStoreIdField
    preferred_intermediate_object_store_id: str | None = PreferredIntermediateObjectStoreIdField
    preferred_outputs_object_store_id: str | None = PreferredOutputsObjectStoreIdField


class StoredWorkflowDetailed(StoredWorkflowSummary):
    annotation: str | None = AnnotationField  # Inconsistency? See comment on StoredWorkflowSummary.annotations
    license: str | None = Field(
        None, title="License", description="SPDX Identifier of the license associated with this workflow."
    )
    version: int = Field(
        ..., title="Version", description="The version of the workflow represented by an incremental number."
    )
    inputs: dict[int, WorkflowInput] = Field(
        {}, title="Inputs", description="A dictionary containing information about all the inputs of the workflow."
    )
    creator: list[Person | CreatorOrganization] | None = Field(
        None,
        title="Creator",
        description=("Additional information about the creator (or multiple creators) of this workflow."),
    )
    creator_deleted: bool = Field(
        ...,
        title="Creator deleted",
        description="Whether the creator of this Workflow has been deleted.",
    )
    doi: list[str] | None = Field(
        None, title="DOI", description="A list of Digital Object Identifiers associated with this workflow."
    )
    steps: dict[
        int,
        Annotated[
            InputDataStep | InputDataCollectionStep | InputParameterStep | PauseStep | ToolStep | SubworkflowStep,
            Field(discriminator="type"),
        ],
    ] = Field(
        {},
        title="Steps",
        description="A dictionary with information about all the steps of the workflow.",
    )
    importable: bool | None = Field(
        ...,
        title="Importable",
        description="Indicates if the workflow is importable by the current user.",
    )
    email_hash: str | None = Field(
        ...,
        title="Email Hash",
        description="The hash of the email of the creator of this workflow",
    )
    readme: str | None = Field(
        ...,
        title="Readme",
        description="The detailed markdown readme of the workflow.",
    )
    help: str | None = Field(
        ...,
        title="Help",
        description="The detailed help text for how to use the workflow and debug problems with it.",
    )
    slug: str | None = Field(
        ...,
        title="Slug",
        description="The slug of the workflow.",
    )
    source_metadata: dict[str, Any] | None = Field(
        ...,
        title="Source Metadata",
        description="The source metadata of the workflow.",
    )


class WorkflowExtractionOutput(Model):
    id: EncodedDatabaseIdField = Field(
        ...,
        title="ID",
        description="Encoded ID of the history content item.",
    )
    hid: int = Field(
        ...,
        title="HID",
        description="The history item ID (position in history).",
    )
    name: str = Field(
        ...,
        title="Name",
        description="The name of the dataset or collection.",
    )
    state: DatasetState = Field(
        ...,
        title="State",
        description="The state of the dataset or collection.",
    )
    deleted: bool = Field(
        ...,
        title="Deleted",
        description="Whether this item has been deleted.",
    )
    history_content_type: HistoryContentType = Field(
        ...,
        title="History Content Type",
        description="Whether this is a dataset or dataset_collection.",
    )
    output_name: str | None = Field(
        None,
        title="Output Name",
        description="Workflow/tool output port name for this concrete output, when known.",
    )
    suggested_name: str | None = Field(
        None,
        title="Suggested Name",
        description="Suggested workflow output label for this concrete output.",
    )
    suggested_name_source: Literal["renamed", "rendered_label", "bare_label", "port_name"] | None = Field(
        None,
        title="Suggested Name Source",
        description="Source used to derive the suggested workflow output label.",
    )
    exposed: bool = Field(
        False,
        title="Exposed",
        description="Whether this output should be preselected for exposure as a workflow output.",
    )


class OutputLabelHint(Model):
    id: DecodedDatabaseIdField = Field(
        ...,
        title="ID",
        description="Decoded ID of the concrete HDA/HDCA output to expose.",
    )
    kind: Literal["hda", "hdca"] = Field(
        ...,
        title="Kind",
        description="Whether the output ID identifies an HDA or an HDCA.",
    )
    label: str = Field(
        ...,
        title="Label",
        description="Workflow output label to assign to the exposed output.",
    )


class InvalidWorkflowExtractionJobReason(str, Enum):
    """Reasons a workflow extraction job may be invalid and disabled for extraction."""

    TOOL_MISSING_OR_INACCESSIBLE = "tool_missing_or_inaccessible"
    CUSTOM_TOOL_INACCESSIBLE = "custom_tool_inaccessible"


class WorkflowExtractionJob(Model):
    id: EncodedDatabaseIdField | None = Field(
        ...,
        title="ID",
        description="Encoded job ID, or null for fake input dataset entries.",
    )
    step_type: Literal["tool", "input_dataset", "input_collection"] = Field(
        ...,
        title="Step Type",
        description="The role this job plays in the extracted workflow.",
    )
    tool_id: str | None = Field(
        None,
        title="Tool ID",
        description="The tool ID that created this job.",
    )
    tool_name: str | None = Field(
        None,
        title="Tool Name",
        description="Human-readable name of the tool.",
    )
    tool_version: str | None = Field(
        None,
        title="Tool Version",
        description="The tool version used by this job.",
    )
    checked: bool = Field(
        ...,
        title="Checked",
        description="Whether this job should be preselected for extraction (True if any outputs are not deleted).",
    )
    tool_version_warning: str | None = Field(
        None,
        title="Tool Version Warning",
        description="Warning when the current tool version differs from the version used by this job.",
    )
    outputs: list[WorkflowExtractionOutput] = Field(
        default_factory=list,
        title="Outputs",
        description="The history items produced by this job.",
    )
    invalid: InvalidWorkflowExtractionJobReason | None = Field(
        None,
        title="Invalid",
        description="Reason this job is invalid for extraction.",
    )
    implicit_collection_jobs_id: EncodedDatabaseIdField | None = Field(
        None,
        title="Implicit Collection Jobs ID",
        description=(
            "Encoded ID of the ImplicitCollectionJobs this job belongs to, "
            "or null if the job is not part of a mapped/implicit collection. "
            "Callers should submit mapped jobs via implicit_collection_jobs_ids "
            "rather than job_ids in the extract-by-ids payload."
        ),
    )
    implicit_collection_jobs_size: int | None = Field(
        None,
        title="Implicit Collection Jobs Size",
        description="Number of constituent jobs in the ICJ (only set when implicit_collection_jobs_id is non-null).",
    )


class WorkflowExtractionSummary(Model):
    history_id: EncodedDatabaseIdField = Field(
        ...,
        title="History ID",
        description="The encoded ID of the history being extracted from.",
    )
    warnings: list[str] = Field(
        default_factory=list,
        title="Warnings",
        description="Any warnings generated during summarization (e.g. datasets still running).",
    )
    jobs: list[WorkflowExtractionJob] = Field(
        default_factory=list,
        title="Jobs",
        description="Ordered list of jobs (and fake input entries) found in the history.",
    )


class WorkflowExtractionPayload(Model):
    workflow_name: str = Field(
        ...,
        title="Workflow Name",
        description="The name for the extracted workflow.",
    )
    job_ids: list[DecodedDatabaseIdField] = Field(
        default_factory=list,
        title="Job IDs",
        description="Encoded IDs of compatible tool jobs to include as workflow steps.",
    )
    dataset_hids: list[int] = Field(
        default_factory=list,
        title="Dataset HIDs",
        description="History item IDs (HIDs) of datasets to treat as workflow inputs.",
    )
    dataset_collection_hids: list[int] = Field(
        default_factory=list,
        title="Dataset Collection HIDs",
        description="History item IDs (HIDs) of dataset collections to treat as workflow inputs.",
    )
    dataset_names: list[str] = Field(
        default_factory=list,
        title="Dataset Names",
        description="Names for the input datasets, parallel to dataset_hids.",
    )
    dataset_collection_names: list[str] = Field(
        default_factory=list,
        title="Dataset Collection Names",
        description="Names for the input dataset collections, parallel to dataset_collection_hids.",
    )


class WorkflowExtractionByIdsPayload(Model):
    workflow_name: str = Field(
        ...,
        title="Workflow Name",
        description="The name for the extracted workflow.",
    )
    job_ids: list[DecodedDatabaseIdField] = Field(
        default_factory=list,
        title="Job IDs",
        description="Decoded IDs of compatible tool jobs to include as workflow steps.",
    )
    hda_ids: list[DecodedDatabaseIdField] = Field(
        default_factory=list,
        title="HDA IDs",
        description="Decoded IDs of HistoryDatasetAssociations to treat as workflow inputs.",
    )
    hdca_ids: list[DecodedDatabaseIdField] = Field(
        default_factory=list,
        title="HDCA IDs",
        description="Decoded IDs of HistoryDatasetCollectionAssociations to treat as workflow inputs.",
    )
    implicit_collection_jobs_ids: list[DecodedDatabaseIdField] = Field(
        default_factory=list,
        title="Implicit Collection Jobs IDs",
        description=(
            "Decoded IDs of ImplicitCollectionJobs (map-over job groups) to include as mapped "
            "workflow steps. Use this for steps that ran with a map/over instead of passing a "
            "constituent job id in job_ids."
        ),
    )
    dataset_names: list[str] = Field(
        default_factory=list,
        title="Dataset Names",
        description="Names for the input datasets, parallel to hda_ids.",
    )
    dataset_collection_names: list[str] = Field(
        default_factory=list,
        title="Dataset Collection Names",
        description="Names for the input dataset collections, parallel to hdca_ids.",
    )
    output_labels: list[OutputLabelHint] = Field(
        default_factory=list,
        title="Output Labels",
        description="Concrete tool outputs to expose as workflow outputs, with labels.",
    )

    @model_validator(mode="after")
    def _at_least_one_input(self):
        if not (self.hda_ids or self.hdca_ids or self.job_ids or self.implicit_collection_jobs_ids):
            raise ValueError("At least one of hda_ids, hdca_ids, job_ids, implicit_collection_jobs_ids required")
        return self


class WorkflowExtractionResult(Model):
    id: EncodedDatabaseIdField = Field(
        ...,
        title="Workflow ID",
        description="The encoded ID of the newly created workflow.",
    )


class ToolShedRepositoryReference(Model):
    tool_shed: str = Field(..., title="Tool Shed", description="Base URL of the tool shed hosting the repository.")
    owner: str = Field(..., title="Owner", description="Owner of the repository in the tool shed.")
    name: str = Field(..., title="Name", description="Name of the repository in the tool shed.")
    changeset_revision: str | None = Field(
        None,
        title="Changeset Revision",
        description="Revision to install. When unset the newest installable revision is used.",
    )


class UnavailableWorkflowTool(Model):
    tool_id: str = Field(..., title="Tool ID", description="Id of the tool as recorded in the workflow.")
    tool_version: str | None = Field(None, title="Tool Version", description="Version recorded in the workflow.")
    tool_uuid: str | None = Field(None, title="Tool UUID", description="UUID of a dynamic tool, if any.")
    installed_versions: list[str] = Field(
        default_factory=list,
        title="Installed Versions",
        description="Versions of this tool that are installed. Empty if the tool is not installed at all.",
    )
    substitute_version: str | None = Field(
        None,
        title="Substitute Version",
        description=(
            "An installed version the workflow can be switched to without a known break in behaviour, "
            "as declared by Galaxy's safe tool version updates. Null when no installed version is known to be safe."
        ),
    )
    repository: ToolShedRepositoryReference | None = Field(
        None,
        title="Repository",
        description="Tool shed repository the tool came from, when the tool id identifies one.",
    )


class WorkflowToolAvailability(Model):
    unavailable_tools: list[UnavailableWorkflowTool] = Field(
        default_factory=list,
        title="Unavailable Tools",
        description="Tools the workflow refers to that are not installed in the version the workflow asks for.",
    )
    can_install: bool = Field(
        ...,
        title="Can Install",
        description="Whether the current user is allowed to install the missing tools from this Galaxy.",
    )
    cannot_install_reason: str | None = Field(
        None,
        title="Cannot Install Reason",
        description="Why installation is not offered to the current user.",
    )


class InstallWorkflowToolsPayload(Model):
    repositories: list[ToolShedRepositoryReference] | None = Field(
        None,
        title="Repositories",
        description="Repositories to install. When unset every repository the workflow is missing is installed.",
    )
    tool_panel_section_id: str | None = Field(
        None, title="Tool Panel Section ID", description="Existing tool panel section to install into."
    )
    new_tool_panel_section_label: str | None = Field(
        None, title="New Tool Panel Section Label", description="Label of a new tool panel section to create."
    )
    install_resolver_dependencies: bool = Field(True, title="Install Resolver Dependencies")
    install_repository_dependencies: bool = Field(True, title="Install Repository Dependencies")
    install_tool_dependencies: bool = Field(False, title="Install Tool Dependencies")


class InstalledWorkflowToolRepository(Model):
    repository: ToolShedRepositoryReference
    status: str | None = Field(None, title="Status", description="Installation status reported by the tool shed.")
    error: str | None = Field(None, title="Error", description="Why this repository could not be installed.")


class InstallWorkflowToolsResponse(Model):
    installed: list[InstalledWorkflowToolRepository] = Field(default_factory=list, title="Installed")
    failed: list[InstalledWorkflowToolRepository] = Field(default_factory=list, title="Failed")


class RequestToolInstallationResponse(Model):
    notified_admins: list[str] = Field(
        default_factory=list,
        title="Notified Admins",
        description="Email addresses of the administrators that were asked to install the missing tools.",
    )
    shared: bool = Field(..., title="Shared", description="Whether the workflow was shared with those administrators.")
    emailed: bool = Field(
        ..., title="Emailed", description="Whether an email could be sent. False when this Galaxy has no mail set up."
    )


class UpdateSubworkflowPayload(Model):
    workflow: dict[str, Any] = Field(
        ...,
        title="Workflow",
        description="The new contents of the subworkflow, in the same shape the editor loads it in.",
    )
    detach: bool = Field(
        False,
        title="Detach",
        description=(
            "Save into a copy embedded in the parent workflow instead of into the workflow the step "
            "points at, so a subworkflow that is a workflow in its own right is left unchanged."
        ),
    )


class UpdateSubworkflowResponse(Model):
    content_id: EncodedDatabaseIdField = Field(
        ..., title="Content ID", description="The subworkflow revision the step now points at."
    )
    detached: bool = Field(
        ..., title="Detached", description="Whether the edit went into a copy private to the parent workflow."
    )
