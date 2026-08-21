"""Dependency-free state types shared by Galaxy's ORM and API schemas.

Keeping these definitions in a lightweight schema leaf module lets the ORM use
the canonical API state types without constructing the Pydantic schema graph.
"""

from enum import Enum
from typing import Literal


class DatasetState(str, Enum):
    NEW = "new"
    UPLOAD = "upload"
    QUEUED = "queued"
    RUNNING = "running"
    OK = "ok"
    EMPTY = "empty"
    ERROR = "error"
    PAUSED = "paused"
    SETTING_METADATA = "setting_metadata"
    FAILED_METADATA = "failed_metadata"
    # Non-deleted, non-purged datasets that don't have physical files.
    # These shouldn't have objectstores attached -
    # 'deferred' can be materialized for jobs using
    # attached DatasetSource objects but 'discarded'
    # cannot (e.g. imported histories). These should still
    # be able to have history contents associated (normal HDAs?)
    DEFERRED = "deferred"
    DISCARDED = "discarded"

    @classmethod
    def values(self):
        return self.__members__.values()


class JobState(str, Enum):
    NEW = "new"
    RESUBMITTED = "resubmitted"
    UPLOAD = "upload"
    WAITING = "waiting"
    QUEUED = "queued"
    RUNNING = "running"
    FINISHING = "finishing"
    OK = "ok"
    ERROR = "error"
    FAILED = "failed"
    PAUSED = "paused"
    DELETING = "deleting"
    DELETED = "deleted"
    STOPPING = "stop"
    STOPPED = "stopped"
    SKIPPED = "skipped"


class DatasetCollectionPopulatedState(str, Enum):
    NEW = "new"  # New dataset collection, unpopulated elements
    OK = "ok"  # Collection elements populated (HDAs may or may not have errors)
    FAILED = "failed"  # some problem populating state, won't be populated


# We use TypedDicts in the model layer and cannot type the action field with
# the enum because TypedDict does not have Pydantic's enum value conversion.
DatasetSourceTransformActionTypeLiteral = Literal["to_posix_lines", "spaces_to_tabs", "datatype_groom"]


class DatasetSourceTransformActionType(str, Enum):
    TO_POSIX_LINES = "to_posix_lines"
    SPACES_TO_TABLES = "spaces_to_tabs"
    DATATYPE_GROOM = "datatype_groom"


class DatasetValidatedState(str, Enum):
    UNKNOWN = "unknown"
    INVALID = "invalid"
    OK = "ok"


class ToolRequestState(str, Enum):
    NEW = "new"
    SUBMITTED = "submitted"
    FAILED = "failed"


class InvocationState(str, Enum):
    NEW = "new"  # Brand new workflow invocation... maybe this should be same as READY
    REQUIRES_MATERIALIZATION = "requires_materialization"  # an otherwise NEW or READY workflow that requires inputs to be materialized (undeferred)
    READY = "ready"  # Workflow ready for another iteration of scheduling.
    SCHEDULED = "scheduled"  # Workflow has been scheduled.
    CANCELLED = "cancelled"
    CANCELLING = "cancelling"  # invocation scheduler will cancel job in next iteration.
    FAILED = "failed"
    COMPLETED = "completed"  # All jobs have reached terminal states (ok, error, deleted, skipped, paused, stopped)


class InvocationStepState(str, Enum):
    NEW = "new"  # Brand new workflow invocation step
    READY = "ready"  # Workflow invocation step ready for another iteration of scheduling.
    SCHEDULED = "scheduled"  # Workflow invocation step has been scheduled.
    # CANCELLED = 'cancelled',  TODO: implement and expose
    # FAILED = 'failed',  TODO: implement and expose
