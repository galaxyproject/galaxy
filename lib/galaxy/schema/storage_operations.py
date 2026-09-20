from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import (
    Any,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    UUID4,
)

from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    EncodedDatabaseIdField,
)

CreateTimeField = Field(
    title="Create Time",
    description="The time and date this item was created.",
)

UpdateTimeField = Field(
    title="Update Time",
    description="The last time and date this item was updated.",
)


class Model(BaseModel):
    model_config = ConfigDict(populate_by_name=True, use_enum_values=True, protected_namespaces=())


class StorageOperationMode(str, Enum):
    move = "move"


class StorageOperationRunState(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class StorageOperationRunItemState(str, Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    skipped = "skipped"


class DatasetStorageOperationFailureReasonCode(str, Enum):
    dataset_not_found = "dataset_not_found"
    invalid_target_object_store = "invalid_target_object_store"
    missing_source_object_store = "missing_source_object_store"
    already_in_target = "already_in_target"
    target_quota_exceeded = "target_quota_exceeded"
    shared_dataset = "shared_dataset"
    insufficient_permissions = "insufficient_permissions"
    dataset_in_use = "dataset_in_use"
    target_expiration_imminent = "target_expiration_imminent"
    checksum_verification_failed = "checksum_verification_failed"
    execution_error = "execution_error"


class StorageOperationPreviewRequest(Model):
    mode: StorageOperationMode
    target_object_store_id: str
    items: list[dict[str, Any]] | None = None


class StorageOperationSelectionCounts(Model):
    selected_items_count: int
    expanded_leaf_count: int
    unique_dataset_count: int


class StorageOperationEligibilityReasonSummary(Model):
    reason_code: DatasetStorageOperationFailureReasonCode
    count: int


class StorageOperationEligibilitySummary(Model):
    eligible_count: int
    ineligible_count: int
    reasons: list[StorageOperationEligibilityReasonSummary] = Field(default_factory=list)


class StorageOperationQuotaDeltaTransfer(Model):
    source_object_store_id: str
    target_object_store_id: str
    bytes: int = 0


class StorageOperationQuotaProjectionSummary(Model):
    projected_usage: int
    quota_limit: int


class StorageOperationEstimateSummary(Model):
    bytes_to_transfer: int = 0
    quota_delta_transfers: list[StorageOperationQuotaDeltaTransfer] = Field(default_factory=list)
    quota_projection: StorageOperationQuotaProjectionSummary | None = None


class StorageOperationPreviewResponse(Model):
    snapshot_id: EncodedDatabaseIdField
    selection_counts: StorageOperationSelectionCounts
    eligibility: StorageOperationEligibilitySummary
    estimates: StorageOperationEstimateSummary
    warnings: list[str] = Field(default_factory=list)
    expires_at: datetime


class StorageOperationExecutePolicy(Model):
    skip_ineligible: bool = True
    max_retries: int | None = None


class StorageOperationExecuteRequest(Model):
    snapshot_id: DecodedDatabaseIdField
    execution_policy: StorageOperationExecutePolicy = Field(default_factory=StorageOperationExecutePolicy)
    notify_on_completion: bool = True


class StorageOperationRunSummary(Model):
    run_id: EncodedDatabaseIdField
    state: StorageOperationRunState
    mode: StorageOperationMode
    target_object_store_id: str
    create_time: datetime = CreateTimeField
    update_time: datetime = UpdateTimeField
    total_count: int
    succeeded_count: int
    failed_count: int
    skipped_count: int
    total_bytes_processed: int
    task_id: UUID4 | None = None


class StorageOperationRunItemStatus(Model):
    dataset_id: EncodedDatabaseIdField
    state: StorageOperationRunItemState
    reason_code: DatasetStorageOperationFailureReasonCode | None = None
    bytes_processed: int
    create_time: datetime = CreateTimeField
    update_time: datetime = UpdateTimeField


class StorageOperationExecuteResponse(Model):
    run: StorageOperationRunSummary


class StorageOperationRunResponse(Model):
    run: StorageOperationRunSummary
    items: list[StorageOperationRunItemStatus] = Field(default_factory=list)


@dataclass(frozen=True)
class StorageOperationExecutionResult:
    state: StorageOperationRunState
    message: str
