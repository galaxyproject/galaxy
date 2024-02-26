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
    creator: Optional[List[Union[Person, Organization]]] = Field(
        None,
        title="Creator",
        description=("Additional information about the creator (or multiple creators) of this workflow."),
    )
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
