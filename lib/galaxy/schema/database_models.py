from datetime import datetime
from typing import (
    Optional,
    List,
)
from uuid import UUID

from pydantic import BaseModel

from galaxy import model
from galaxy.schema.fields import (
    DatabaseIdField,
    EncodedDatabaseIdField,
)


class WorkflowInvocationBase(BaseModel):
    update_time: Optional[datetime] = None
    create_time: Optional[datetime] = None
    uuid: Optional[UUID] = None
    state: Optional[model.WorkflowInvocation.states] = None

    class Config:
        orm_mode=True


class WorkflowInvocationInDb(WorkflowInvocationBase):
    id: DatabaseIdField
    history_id: DatabaseIdField
    workflow_id: DatabaseIdField


class WorkflowInvocation(WorkflowInvocationInDb):
    id: EncodedDatabaseIdField
    history_id: EncodedDatabaseIdField
    workflow_id: EncodedDatabaseIdField


class WorkflowInvocationStepBase(BaseModel):
    id: Optional[DatabaseIdField] = None
    update_time: Optional[datetime] = None
    job_id: Optional[DatabaseIdField] = None
    workflow_invocation_id: Optional[DatabaseIdField] = None
    workflow_step_id: Optional[DatabaseIdField] = None
    subworkflow_invocation_id: Optional[DatabaseIdField] = None
    state: Optional[model.WorkflowInvocationStep.states] = None

    class Config:
        orm_mode = True

class WorkflowInvocationElementInDb(WorkflowInvocationInDb):
    steps: List[WorkflowInvocationStepBase] = []

    class Config:
        orm_mode = True

