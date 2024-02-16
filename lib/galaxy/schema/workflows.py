import json
from typing import (
    Any,
    Dict,
    Optional,
)

from pydantic import (
    Field,
    field_validator,
)

from galaxy.schema.schema import (
    Model,
    PreferredObjectStoreIdField,
)

# class WorkflowExtractionParams(Model):
#     from_history_id: str = Field(..., title="From History ID", description="Id of history to extract a workflow from.")
#     job_ids: Optional[str] = Field(
#         None,
#         title="Job IDs",
#         description="List of jobs to include when extracting a workflow from history",
#     )

#     @field_validator("dataset_ids", mode="before", check_fields=False)
#     @classmethod
#     def inputs_string_to_json(cls, v):
#         if isinstance(v, str):
#             return json.loads(v)
#         return v

#     dataset_ids: Optional[str] = Field(
#         None,
#         title="Dataset IDs",
#         description="List of HDA 'hid's corresponding to workflow inputs when extracting a workflow from history",
#         alias="ds_map",
#     )
#     dataset_collection_ids: Optional[str] = Field(
#         None,
#         title="Dataset Collection IDs",
#         description="List of HDCA 'hid's corresponding to workflow inputs when extracting a workflow from history",
#     )
#     workflow_name: Optional[str] = Field(
#         None,
#         title="Workflow Name",
#         description="Name of the workflow to create when extracting a workflow from history",
#     )


class GetTargetHistoryPayload(Model):
    # TODO - add description to fields
    history: Optional[str] = Field(
        None,
        title="History",
        # description="The history to import the workflow into.",
        description="TODO",
    )
    history_id: Optional[str] = Field(
        None,
        title="History ID",
        # description="The history to import the workflow into.",
        description="TODO",
    )
    history_name: Optional[str] = Field(
        None,
        title="History Name",
        # description="The name of the history to import the workflow into.",
        description="TODO",
    )
    new_history_name: Optional[str] = Field(
        None,
        title="New History Name",
        # description="The name of the new history to import the workflow into.",
        description="TODO",
    )


class InvokeWorkflowPayload(GetTargetHistoryPayload):
    # TODO - add description to fields
    instance: Optional[bool] = Field(
        False,
        title="Is instance",
        description="TODO",
    )
    scheduler: Optional[str] = Field(
        None,
        title="Scheduler",
        # description="Scheduler to use for workflow invocation.",
        description="TODO",
    )
    batch: Optional[bool] = Field(
        False,
        title="Batch",
        # description="If true, the workflow is invoked as a batch.",
        description="TODO",
    )
    require_exact_tool_versions: Optional[bool] = Field(
        True,
        title="Require Exact Tool Versions",
        # description="If true, exact tool versions are required for workflow invocation.",
        description="TODO",
    )
    allow_tool_state_corrections: Optional[bool] = Field(
        False,
        title="Allow tool state corrections",
        description="TODO",
    )
    use_cached_job: Optional[bool] = Field(
        False,
        title="Use cached job",
        description="TODO",
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
        description="TODO",
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
        description="TODO",
    )
    legacy: Optional[bool] = Field(
        False,
        title="Legacy",
        description="TODO",
    )
    parameters_normalized: Optional[bool] = Field(
        False,
        title="Parameters Normalized",
        description="TODO",
    )
    inputs_by: Optional[str] = Field(
        None,
        title="Inputs By",
        description="TODO",
    )
    effective_outputs: Optional[bool] = Field(
        None,
        title="Effective Outputs",
        description="TODO",
    )
    preferred_intermediate_object_store_id: Optional[str] = Field(
        None,
        title="Preferred Intermediate Object Store ID",
        description="TODO",
    )
    preferred_outputs_object_store_id: Optional[str] = Field(
        None,
        title="Preferred Outputs Object Store ID",
        description="TODO",
    )
    preferred_object_store_id: Optional[str] = PreferredObjectStoreIdField
