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

# TODO - add description to fields


class GetTargetHistoryPayload(Model):
    history: Optional[str] = Field(
        None,
        title="History",
        description="The history to import the workflow into.",
    )
    history_id: Optional[str] = Field(
        None,
        title="History ID",
        description="The history to import the workflow into.",
    )
    history_name: Optional[str] = Field(
        None,
        title="History Name",
        description="The name of the history to import the workflow into.",
    )
    new_history_name: Optional[str] = Field(
        None,
        title="New History Name",
        description="The name of the new history to import the workflow into.",
    )


class InvokeWorkflowPayload(GetTargetHistoryPayload):
    instance: Optional[bool] = Field(
        False,
        title="Is Instance",
        description="If true, the workflow is invoked as an instance.",
    )
    scheduler: Optional[str] = Field(
        None,
        title="Scheduler",
        description="Scheduler to use for workflow invocation.",
    )
    batch: Optional[bool] = Field(
        False,
        title="Batch",
        description="If true, the workflow is invoked as a batch.",
    )
    require_exact_tool_versions: Optional[bool] = Field(
        False,
        title="Require Exact Tool Versions",
        description="If true, exact tool versions are required for workflow invocation.",
    )
    allow_tool_state_corrections: Optional[bool] = False
    use_cached_job: Optional[bool] = False

    # input_step_parameters: Dict[str, InvocationInputParameter] = Field(
    #     default=..., title="Input step parameters", description="Input step parameters of the workflow invocation."
    # )
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

    parameters: Optional[Dict[str, Any]] = None
    inputs: Optional[Dict[str, Any]] = None
    ds_map: Optional[Dict[str, Dict[str, Any]]] = None
    resource_params: Optional[Dict[str, Any]] = None
    replacement_params: Optional[Dict[str, Any]] = None
    step_parameters: Optional[Dict[str, Any]] = None
    no_add_to_history: Optional[bool] = False
    legacy: Optional[bool] = False
    parameters_normalized: Optional[bool] = False
    inputs_by: Optional[str] = None
    effective_outputs: Optional[bool] = None
    preferred_object_store_id: Optional[str] = PreferredObjectStoreIdField
    preferred_intermediate_object_store_id: Optional[str] = None
    preferred_outputs_object_store_id: Optional[str] = None
