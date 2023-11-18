from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    TypeVar,
    Union,
)

from pydantic import (
    BaseModel,
    Field,
    Required,
)
from pydantic.generics import GenericModel
from pydantic.utils import GetterDict
from typing_extensions import (
    Annotated,
    Literal,
)

from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.schema.schema import (
    CreateTimeField,
    EntityIdField,
    UpdateTimeField,
    WorkflowIdField,
)


class WarningReason(str, Enum):
    workflow_output_not_found = "workflow_output_not_found"


class FailureReason(str, Enum):
    dataset_failed = "dataset_failed"
    collection_failed = "collection_failed"
    job_failed = "job_failed"
    output_not_found = "output_not_found"
    expression_evaluation_failed = "expression_evaluation_failed"
    when_not_boolean = "when_not_boolean"
    unexpected_failure = "unexpected_failure"


class CancelReason(str, Enum):
    """Possible reasons for a cancelled workflow."""

    history_deleted = "history_deleted"
    user_request = "user_request"
    cancelled_on_review = "cancelled_on_review"


DatabaseIdT = TypeVar("DatabaseIdT")


class StepOrderIndexGetter(GetterDict):
    def get(self, key: Any, default: Any = None) -> Any:
        # Fetch the order_index when serializing for the API,
        # which makes much more sense when pointing to steps.
        if key == "workflow_step_id":
            if self._obj.workflow_step:
                return self._obj.workflow_step.order_index
            else:
                return default
        elif key == "dependent_workflow_step_id":
            if self._obj.dependent_workflow_step_id:
                return self._obj.dependent_workflow_step.order_index
            else:
                return default

        return super().get(key, default)


class InvocationMessageBase(GenericModel):
    reason: Union[CancelReason, FailureReason, WarningReason]

    class Config:
        orm_mode = True
        getter_dict = StepOrderIndexGetter


class GenericInvocationCancellationReviewFailed(InvocationMessageBase, Generic[DatabaseIdT]):
    reason: Literal[CancelReason.cancelled_on_review]
    workflow_step_id: int = Field(..., description="Workflow step id of paused step that did not pass review.")


class GenericInvocationCancellationHistoryDeleted(InvocationMessageBase, Generic[DatabaseIdT]):
    reason: Literal[CancelReason.history_deleted]
    history_id: DatabaseIdT = Field(..., title="History ID", description="History ID of history that was deleted.")


class GenericInvocationCancellationUserRequest(InvocationMessageBase, Generic[DatabaseIdT]):
    reason: Literal[CancelReason.user_request]


class InvocationFailureMessageBase(InvocationMessageBase, Generic[DatabaseIdT]):
    workflow_step_id: int = Field(..., description="Workflow step id of step that failed.")


class GenericInvocationFailureDatasetFailed(InvocationFailureMessageBase[DatabaseIdT], Generic[DatabaseIdT]):
    reason: Literal[FailureReason.dataset_failed]
    hda_id: DatabaseIdT = Field(
        ..., title="HistoryDatasetAssociation ID", description="HistoryDatasetAssociation ID that relates to failure."
    )
    dependent_workflow_step_id: Optional[int] = Field(None, description="Workflow step id of step that caused failure.")


class GenericInvocationFailureCollectionFailed(InvocationFailureMessageBase[DatabaseIdT], Generic[DatabaseIdT]):
    reason: Literal[FailureReason.collection_failed]
    hdca_id: DatabaseIdT = Field(
        ...,
        title="HistoryDatasetCollectionAssociation ID",
        description="HistoryDatasetCollectionAssociation ID that relates to failure.",
    )
    dependent_workflow_step_id: int = Field(..., description="Workflow step id of step that caused failure.")


class GenericInvocationFailureJobFailed(InvocationFailureMessageBase[DatabaseIdT], Generic[DatabaseIdT]):
    reason: Literal[FailureReason.job_failed]
    job_id: DatabaseIdT = Field(..., title="Job ID", description="Job ID that relates to failure.")
    dependent_workflow_step_id: int = Field(..., description="Workflow step id of step that caused failure.")


class GenericInvocationFailureOutputNotFound(InvocationFailureMessageBase[DatabaseIdT], Generic[DatabaseIdT]):
    reason: Literal[FailureReason.output_not_found]
    output_name: str = Field(..., title="Tool or module output name that was referenced but not produced")
    dependent_workflow_step_id: int = Field(..., description="Workflow step id of step that caused failure.")


class GenericInvocationFailureExpressionEvaluationFailed(
    InvocationFailureMessageBase[DatabaseIdT], Generic[DatabaseIdT]
):
    reason: Literal[FailureReason.expression_evaluation_failed]
    details: Optional[str] = Field(None, description="May contain details to help troubleshoot this problem.")


class GenericInvocationFailureWhenNotBoolean(InvocationFailureMessageBase[DatabaseIdT], Generic[DatabaseIdT]):
    reason: Literal[FailureReason.when_not_boolean]
    details: str = Field(..., description="Contains details to help troubleshoot this problem.")


class GenericInvocationUnexpectedFailure(InvocationMessageBase, Generic[DatabaseIdT]):
    reason: Literal[FailureReason.unexpected_failure]
    details: Optional[str] = Field(None, description="May contains details to help troubleshoot this problem.")
    workflow_step_id: Optional[int] = Field(None, description="Workflow step id of step that failed.")


class GenericInvocationWarning(InvocationMessageBase, Generic[DatabaseIdT]):
    reason: WarningReason = Field(..., title="Failure Reason", description="Reason for warning")
    workflow_step_id: Optional[int] = Field(None, title="Workflow step id of step that caused a warning.")


class GenericInvocationEvaluationWarningWorkflowOutputNotFound(
    GenericInvocationWarning[DatabaseIdT], Generic[DatabaseIdT]
):
    reason: Literal[WarningReason.workflow_output_not_found]
    workflow_step_id: int = Field(..., title="Workflow step id of step that caused a warning.")
    output_name: str = Field(
        ..., description="Output that was designated as workflow output but that has not been found"
    )


# TODO - This already exists in the WorkflowInvocation(lib/galaxy/model/__init__.py).
# How can I access it to use it here?
class InvocationState(str, Enum):
    NEW = "new"  # Brand new workflow invocation... maybe this should be same as READY
    READY = "ready"  # Workflow ready for another iteration of scheduling.
    SCHEDULED = "scheduled"  # Workflow has been scheduled.
    CANCELLED = "cancelled"
    CANCELLING = "cancelling"  # invocation scheduler will cancel job in next iteration
    FAILED = "failed"


class EncodedInvocation(BaseModel):
    id: EncodedDatabaseIdField = EntityIdField
    create_time: datetime = CreateTimeField
    update_time: datetime = UpdateTimeField
    workflow_id: EncodedDatabaseIdField = WorkflowIdField
    # history_id: EncodedDatabaseIdField = HistoryIdField # TODO - fix HistoryIdField?
    history_id: EncodedDatabaseIdField = Field(
        default=Required, title="History ID", description="The encoded ID of the history associated with this item."
    )
    # TODO this fails weirdly ... try to understand and fix it
    # uuid: UUID4 = UuidField
    uuid: Any = Field(..., title="UUID", description="Universal unique identifier for this dataset.")
    state: InvocationState = Field(
        default=Required, title="Invocation state", description="State of workflow invocation."
    )
    # TODO - is there a class which classifies these models
    model_class: str = Field(default=Required, title="Model class", description="Model class name.")
    # TODO - Add proper models
    steps: Optional[List[Dict[str, Optional[str]]]] = None
    inputs: Optional[Dict[str, Dict[str, Optional[str]]]] = None
    input_step_parameters: Optional[Dict[str, Dict[str, Optional[str]]]] = None
    outputs: Optional[Dict[str, Dict[str, Optional[str]]]] = None
    output_collections: Optional[Dict[str, Dict[str, Optional[str]]]] = None
    output_values: Optional[Dict[str, Optional[str]]] = None
    # TODO understand where this comes from
    message: Optional[str] = Field(
        default=None, title="Message", description="Message associated with this invocation."
    )


InvocationCancellationReviewFailed = GenericInvocationCancellationReviewFailed[int]
InvocationCancellationHistoryDeleted = GenericInvocationCancellationHistoryDeleted[int]
InvocationCancellationUserRequest = GenericInvocationCancellationUserRequest[int]
InvocationFailureDatasetFailed = GenericInvocationFailureDatasetFailed[int]
InvocationFailureCollectionFailed = GenericInvocationFailureCollectionFailed[int]
InvocationFailureJobFailed = GenericInvocationFailureJobFailed[int]
InvocationFailureOutputNotFound = GenericInvocationFailureOutputNotFound[int]
InvocationFailureExpressionEvaluationFailed = GenericInvocationFailureExpressionEvaluationFailed[int]
InvocationFailureWhenNotBoolean = GenericInvocationFailureWhenNotBoolean[int]
InvocationUnexpectedFailure = GenericInvocationUnexpectedFailure[int]
InvocationWarningWorkflowOutputNotFound = GenericInvocationEvaluationWarningWorkflowOutputNotFound[int]

InvocationMessageUnion = Union[
    InvocationCancellationReviewFailed,
    InvocationCancellationHistoryDeleted,
    InvocationCancellationUserRequest,
    InvocationFailureDatasetFailed,
    InvocationFailureCollectionFailed,
    InvocationFailureJobFailed,
    InvocationFailureOutputNotFound,
    InvocationFailureExpressionEvaluationFailed,
    InvocationFailureWhenNotBoolean,
    InvocationUnexpectedFailure,
    InvocationWarningWorkflowOutputNotFound,
]

InvocationCancellationReviewFailedResponseModel = GenericInvocationCancellationReviewFailed[EncodedDatabaseIdField]
InvocationCancellationHistoryDeletedResponseModel = GenericInvocationCancellationHistoryDeleted[EncodedDatabaseIdField]
InvocationCancellationUserRequestResponseModel = GenericInvocationCancellationUserRequest[EncodedDatabaseIdField]
InvocationFailureDatasetFailedResponseModel = GenericInvocationFailureDatasetFailed[EncodedDatabaseIdField]
InvocationFailureCollectionFailedResponseModel = GenericInvocationFailureCollectionFailed[EncodedDatabaseIdField]
InvocationFailureJobFailedResponseModel = GenericInvocationFailureJobFailed[EncodedDatabaseIdField]
InvocationFailureOutputNotFoundResponseModel = GenericInvocationFailureOutputNotFound[EncodedDatabaseIdField]
InvocationFailureExpressionEvaluationFailedResponseModel = GenericInvocationFailureExpressionEvaluationFailed[
    EncodedDatabaseIdField
]
InvocationFailureWhenNotBooleanResponseModel = GenericInvocationFailureWhenNotBoolean[EncodedDatabaseIdField]
InvocationUnexpectedFailureResponseModel = GenericInvocationUnexpectedFailure[EncodedDatabaseIdField]
InvocationWarningWorkflowOutputNotFoundResponseModel = GenericInvocationEvaluationWarningWorkflowOutputNotFound[
    EncodedDatabaseIdField
]

InvocationMessageResponseUnion = Annotated[
    Union[
        InvocationCancellationReviewFailedResponseModel,
        InvocationCancellationHistoryDeletedResponseModel,
        InvocationCancellationUserRequestResponseModel,
        InvocationFailureDatasetFailedResponseModel,
        InvocationFailureCollectionFailedResponseModel,
        InvocationFailureJobFailedResponseModel,
        InvocationFailureOutputNotFoundResponseModel,
        InvocationFailureExpressionEvaluationFailedResponseModel,
        InvocationFailureWhenNotBooleanResponseModel,
        InvocationUnexpectedFailureResponseModel,
        InvocationWarningWorkflowOutputNotFoundResponseModel,
    ],
    Field(discriminator="reason"),
]


class InvocationMessageResponseModel(BaseModel):
    __root__: InvocationMessageResponseUnion

    class Config:
        orm_mode = True
