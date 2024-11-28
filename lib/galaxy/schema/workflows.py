import json
from typing import (
    Any,
    cast,
    Dict,
    List,
    Optional,
    Union,
)

from pydantic import (
    AfterValidator,
    Field,
    field_validator,
)
from typing_extensions import Annotated

from galaxy.schema.schema import (
    AnnotationField,
    InputDataCollectionStep,
    InputDataStep,
    InputParameterStep,
    Model,
    Organization,
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
    {},
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
    {},
    title="Resource Parameters",
    description="If a workflow_resource_params_file file is defined and the target workflow is configured to consumer resource parameters, they can be specified with this parameter. See https://github.com/galaxyproject/galaxy/pull/4830 for more information.",
)

VALID_INPUTS_BY_ITEMS = ["step_id", "step_index", "step_uuid", "name"]


def validateInputsBy(inputsBy: Optional[str]) -> Optional[str]:
    if inputsBy is not None:
        if not isinstance(inputsBy, str):
            raise ValueError(f"Invalid type for inputsBy {inputsBy}")
        inputsByStr = cast(str, inputsBy)
        inputsByArray: List[str] = inputsByStr.split("|")
        for inputsByItem in inputsByArray:
            if inputsByItem not in VALID_INPUTS_BY_ITEMS:
                raise ValueError(f"Invalid inputsBy delineation {inputsByItem}")
    return inputsBy


InputsByValidator = AfterValidator(validateInputsBy)


class GetTargetHistoryPayload(Model):
    # TODO - Are the descriptions correct?
    history: Optional[str] = Field(
        None,
        title="History",
        # description="The encoded history id - passed exactly like this 'hist_id=...' -  to import the workflow into. Or the name of the new history to import the workflow into.",
        description="The encoded history id - passed exactly like this 'hist_id=...' -  into which to import. Or the name of the new history into which to import.",
    )
    history_id: Optional[str] = TargetHistoryIdField
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
    use_cached_job: Optional[bool] = UseCachedJobField
    parameters_normalized: Optional[bool] = Field(
        False,
        title=STEP_PARAMETERS_NORMALIZED_TITLE,
        description=STEP_PARAMETERS_NORMALIZED_DESCRIPTION,
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

    parameters: Optional[Dict[str, Any]] = Field(
        {},
        title=STEP_PARAMETERS_TITLE,
        description=STEP_PARAMETERS_DESCRIPTION,
    )
    inputs: Optional[Dict[str, Any]] = Field(
        None,
        title="Inputs",
        description="Specify values for formal inputs to the workflow",
    )
    ds_map: Optional[Dict[str, Dict[str, Any]]] = Field(
        {},
        title="Legacy Dataset Map",
        description="An older alternative to specifying inputs using database IDs, do not use this and use inputs instead",
        deprecated=True,
    )
    resource_params: Optional[Dict[str, Any]] = ResourceParametersField
    replacement_params: Optional[Dict[str, Any]] = ReplacementParametersField
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
    inputs_by: Annotated[Optional[str], InputsByValidator] = Field(
        None,
        title="Inputs By",
        # lib/galaxy/workflow/run_request.py - see line 60
        description=INPUTS_BY_DESCRIPTION,
    )
    effective_outputs: Optional[Any] = Field(
        None,
        title="Effective Outputs",
        # lib/galaxy/workflow/run_request.py - see line 455
        description="TODO",
    )
    preferred_object_store_id: Optional[str] = PreferredObjectStoreIdField
    preferred_intermediate_object_store_id: Optional[str] = PreferredIntermediateObjectStoreIdField
    preferred_outputs_object_store_id: Optional[str] = PreferredOutputsObjectStoreIdField


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
