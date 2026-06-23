from collections.abc import (
    Callable,
    Iterable,
)
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import (
    cast,
    Optional,
    TYPE_CHECKING,
    Union,
)
from uuid import UUID

from sqlalchemy import (
    delete,
    exists,
    false,
    or_,
    select,
)
from sqlalchemy.sql.elements import ColumnElement

from galaxy import exceptions
from galaxy.config import GalaxyAppConfiguration
from galaxy.managers import datasets
from galaxy.model import (
    Dataset,
    DatasetStorageOperationRun,
    DatasetStorageOperationRunItem,
    DatasetStorageOperationSnapshot,
    HistoryDatasetAssociation,
    HistoryDatasetCollectionAssociation,
    User,
)
from galaxy.model.orm.now import now
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.objectstore import BaseObjectStore
from galaxy.quota import QuotaAgent
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.schema.storage_operations import (
    DatasetStorageOperationFailureReasonCode,
    StorageOperationEligibilityReasonSummary,
    StorageOperationEligibilitySummary,
    StorageOperationEstimateSummary,
    StorageOperationExecutionResult,
    StorageOperationMode,
    StorageOperationPreviewResponse,
    StorageOperationQuotaDeltaTransfer,
    StorageOperationQuotaProjectionSummary,
    StorageOperationRunItemState,
    StorageOperationRunItemStatus,
    StorageOperationRunState,
    StorageOperationRunSummary,
    StorageOperationSelectionCounts,
)
from galaxy.security import RBACAgent
from galaxy.util.custom_logging import get_logger
from galaxy.util.hash_util import (
    HashFunctionNameEnum,
    memory_bound_hexdigest,
)
from galaxy.util.search import parse_filters_structured

if TYPE_CHECKING:
    from galaxy.managers.hdcas import HDCAManager
    from galaxy.structured_app import MinimalManagerApp

log = get_logger(__name__)


DEFAULT_DATASET_MINIMUM_DAYS_TO_EXPIRATION = 7
DEFAULT_RUN_RETENTION_AFTER_COMPLETION_DAYS = 30
UNUSED_SNAPSHOT_EXPIRES_AFTER_DAYS = 1
TRANSFER_RETRY_ATTEMPTS = 3
PROGRESS_COMMIT_INTERVAL_SMALL_RUN = 1
PROGRESS_COMMIT_INTERVAL_MEDIUM_RUN = 5
PROGRESS_COMMIT_INTERVAL_LARGE_RUN = 25
PROGRESS_COMMIT_INTERVAL_XL_RUN = 50
NEAR_QUOTA_WARNING_THRESHOLD = 0.8
TERMINAL_RUN_ITEM_STATES = {
    StorageOperationRunItemState.succeeded.value,
    StorageOperationRunItemState.failed.value,
    StorageOperationRunItemState.skipped.value,
}
TERMINAL_RUN_STATES = {
    StorageOperationRunState.completed.value,
    StorageOperationRunState.failed.value,
}

StorageOperationContent = Union[HistoryDatasetAssociation, HistoryDatasetCollectionAssociation]


@dataclass(frozen=True)
class DatasetObjectStoreProxy:
    id: int
    uuid: UUID | str | None
    object_store_id: str


@dataclass(frozen=True)
class TargetQuotaProjection:
    projected_usage: int
    quota: int

    @property
    def exceeds_quota(self) -> bool:
        return self.projected_usage > self.quota


def _as_encoded_database_id(value: int) -> EncodedDatabaseIdField:
    return cast(EncodedDatabaseIdField, value)


@dataclass
class StorageOperationPreviewComputation:
    eligible_dataset_ids: list[int]
    eligibility_reasons: list[StorageOperationEligibilityReasonSummary]
    eligible_count: int
    ineligible_count: int
    bytes_to_transfer: int
    target_quota_delta: int
    quota_delta_transfers: list[StorageOperationQuotaDeltaTransfer]
    privacy_downgrade_count: int
    target_quota_projection: Optional[TargetQuotaProjection] = None


class DatasetStorageOperationManager:
    """Shared policy checks used by storage operation preview and execution paths."""

    def __init__(
        self,
        object_store: BaseObjectStore,
        config: Optional[GalaxyAppConfiguration] = None,
        hdca_manager: Optional["HDCAManager"] = None,
    ):
        self.object_store = object_store
        self.dataset_minimum_days_to_expiration = (
            config.bulk_storage_operation_dataset_minimum_days_to_expiration
            if config is not None
            else DEFAULT_DATASET_MINIMUM_DAYS_TO_EXPIRATION
        )
        self.run_retention_after_completion_days = (
            config.bulk_storage_operation_completed_run_retention_days
            if config is not None
            else DEFAULT_RUN_RETENTION_AFTER_COMPLETION_DAYS
        )
        self._preview_builder = (
            DatasetStorageOperationPreviewBuilder(self, hdca_manager) if hdca_manager is not None else None
        )
        self._run_manager = DatasetStorageOperationRunManager(self)

    def validate_dataset_for_move(
        self,
        security_agent: RBACAgent,
        user: User,
        dataset: Dataset,
        target_object_store_id: str,
    ) -> Optional[DatasetStorageOperationFailureReasonCode]:
        target_device_id = self._device_id_for_store(target_object_store_id)
        if target_device_id is None:
            return DatasetStorageOperationFailureReasonCode.invalid_target_object_store

        source_object_store_id = dataset.object_store_id
        if source_object_store_id is None:
            return DatasetStorageOperationFailureReasonCode.missing_source_object_store
        if source_object_store_id == target_object_store_id:
            return DatasetStorageOperationFailureReasonCode.already_in_target

        if dataset.library_associations:
            return DatasetStorageOperationFailureReasonCode.insufficient_permissions

        can_change = security_agent.can_change_object_store_id(user, dataset)
        if not can_change:
            return DatasetStorageOperationFailureReasonCode.shared_dataset

        ok_to_edit_metadata = getattr(dataset, "ok_to_edit_metadata", None)
        if callable(ok_to_edit_metadata) and not ok_to_edit_metadata():
            return DatasetStorageOperationFailureReasonCode.dataset_in_use

        is_below_expiration_threshold = self.is_dataset_below_expiration_threshold(dataset, target_object_store_id)
        if is_below_expiration_threshold:
            return DatasetStorageOperationFailureReasonCode.target_expiration_imminent

        return None

    def target_quota_delta(
        self,
        dataset_size: int,
        source_quota_label: Optional[str],
        target_quota_label: Optional[str],
    ) -> int:
        if source_quota_label == target_quota_label:
            return 0
        return dataset_size

    def target_quota_projection(
        self,
        quota_agent: QuotaAgent,
        user: User,
        target_object_store_id: str,
        target_quota_delta: int,
        *,
        additional_target_usage: int = 0,
    ) -> Optional[TargetQuotaProjection]:
        if target_quota_delta <= 0:
            return None

        quota_source_label = self.object_store.get_quota_source_map().get_quota_source_label(target_object_store_id)
        quota = quota_agent.get_quota(user, quota_source_label=quota_source_label)
        if quota is None:
            return None

        if quota_source_label is None:
            usage = int(user.total_disk_usage or 0)
        else:
            quota_source_usage = user.quota_source_usage_for(quota_source_label)
            usage = int(quota_source_usage.disk_usage or 0) if quota_source_usage else 0

        projected_usage = usage + additional_target_usage + target_quota_delta
        return TargetQuotaProjection(projected_usage=projected_usage, quota=quota)

    def target_quota_exceeded_message(self, *, phase_label: str) -> str:
        return f"Operation would exceed the target quota {phase_label}."

    def requires_data_transfer(
        self,
        dataset: Dataset,
        target_object_store_id: str,
    ) -> bool:
        source_object_store_id = dataset.object_store_id
        if source_object_store_id is None:
            return True
        if source_object_store_id == target_object_store_id:
            return False
        if self.is_cross_device_move(dataset, target_object_store_id):
            return True

        source_proxy = DatasetObjectStoreProxy(
            id=dataset.id,
            uuid=dataset.uuid,
            object_store_id=source_object_store_id,
        )
        target_proxy = DatasetObjectStoreProxy(
            id=dataset.id,
            uuid=dataset.uuid,
            object_store_id=target_object_store_id,
        )
        try:
            source_path = self.object_store.construct_path(source_proxy)
            target_path = self.object_store.construct_path(target_proxy)
        except Exception:
            log.warning(
                "Falling back to data transfer for dataset %s when comparing object store paths %s -> %s",
                dataset.id,
                source_object_store_id,
                target_object_store_id,
                exc_info=True,
            )
            return True
        return source_path != target_path

    def is_privacy_downgrade_for_target(self, dataset: Dataset, target_object_store_id: str) -> bool:
        source_is_private = self._is_private_for_dataset(dataset)
        target_is_private = self._is_private_for_object_store_id(target_object_store_id)
        return source_is_private is True and target_is_private is False

    def is_target_store_expirable(self, target_object_store_id: str) -> bool:
        return self._target_store_expiration_days(target_object_store_id) is not None

    def is_dataset_below_expiration_threshold(self, dataset: Dataset, target_object_store_id: str) -> bool:
        remaining_lifetime = self._target_remaining_lifetime(dataset, target_object_store_id)
        if remaining_lifetime is None:
            return False
        return remaining_lifetime < timedelta(days=self.dataset_minimum_days_to_expiration)

    def is_cross_device_move(self, dataset: Dataset, target_object_store_id: str) -> bool:
        source_object_store_id = dataset.object_store_id
        if source_object_store_id is None:
            return True
        source_device_id = self._device_id_for_store(source_object_store_id)
        target_device_id = self._device_id_for_store(target_object_store_id)
        if source_device_id is None or target_device_id is None:
            return True
        return source_device_id != target_device_id

    def _device_id_for_store(self, object_store_id: Optional[str]) -> Optional[str]:
        if object_store_id is None:
            return None
        return self.object_store.get_device_source_map().get_device_id(object_store_id)

    def _is_private_for_dataset(self, dataset: Dataset) -> Optional[bool]:
        try:
            return self.object_store.is_private(dataset)
        except Exception:
            return None

    def _is_private_for_object_store_id(self, object_store_id: str) -> Optional[bool]:
        try:
            proxy = SimpleNamespace(object_store_id=object_store_id)
            return self.object_store.is_private(proxy)
        except Exception:
            return None

    def _target_remaining_lifetime(self, dataset: Dataset, target_object_store_id: str) -> Optional[timedelta]:
        expiration_days = self._target_store_expiration_days(target_object_store_id)
        if expiration_days is None or dataset.create_time is None:
            return None

        expiration_time = dataset.create_time + timedelta(days=expiration_days)
        return expiration_time - now()

    def _target_store_expiration_days(self, target_object_store_id: str) -> Optional[int]:
        concrete_store = self.object_store.get_concrete_store_by_object_store_id(target_object_store_id)
        if concrete_store is None:
            return None

        expiration_days = concrete_store.object_expires_after_days
        if expiration_days is None:
            return None

        return int(expiration_days)

    def create_operation_snapshot(
        self,
        sa_session: galaxy_scoped_session,
        history_id: int,
        user_id: int,
        target_object_store_id: str,
        resolved_dataset_ids: list[int],
        eligible_dataset_ids: list[int],
        snapshot_ttl: timedelta,
    ) -> DatasetStorageOperationSnapshot:
        expires_at = now() + snapshot_ttl
        snapshot = DatasetStorageOperationSnapshot(
            history_id=history_id,
            user_id=user_id,
            mode=StorageOperationMode.move,
            target_object_store_id=target_object_store_id,
            resolved_dataset_ids=resolved_dataset_ids,
            eligible_dataset_ids=eligible_dataset_ids,
            expires_at=expires_at,
        )
        sa_session.add(snapshot)
        sa_session.commit()
        return snapshot

    def create_operation_run(
        self,
        sa_session: galaxy_scoped_session,
        snapshot: DatasetStorageOperationSnapshot,
        skip_ineligible: bool,
        notify_on_completion: bool = True,
    ) -> DatasetStorageOperationRun:
        run = DatasetStorageOperationRun(
            snapshot_id=snapshot.id,
            history_id=snapshot.history_id,
            user_id=snapshot.user_id,
            mode=snapshot.mode,
            target_object_store_id=snapshot.target_object_store_id,
            state=StorageOperationRunState.pending.value,
            skip_ineligible=skip_ineligible,
            notify_on_completion=notify_on_completion,
        )
        run.total_count = len(snapshot.resolved_dataset_ids)
        sa_session.add(run)
        sa_session.commit()
        return run

    def prune_expired_snapshots(self, sa_session: galaxy_scoped_session) -> int:
        snapshot_run_exists = (
            select(DatasetStorageOperationRun.id)
            .where(
                DatasetStorageOperationRun.snapshot_id == DatasetStorageOperationSnapshot.id,
            )
            .correlate(DatasetStorageOperationSnapshot)
        )
        deleted_snapshot_ids = sa_session.scalars(
            delete(DatasetStorageOperationSnapshot)
            .where(
                DatasetStorageOperationSnapshot.expires_at <= now(),
                ~exists(snapshot_run_exists),
            )
            .returning(DatasetStorageOperationSnapshot.id)
        ).all()
        deleted_count = len(deleted_snapshot_ids)
        sa_session.commit()
        return deleted_count

    def prune_completed_runs(self, sa_session: galaxy_scoped_session) -> int:
        completion_cutoff = now() - timedelta(days=self.run_retention_after_completion_days)
        deleted_run_ids = sa_session.scalars(
            delete(DatasetStorageOperationRun)
            .where(
                DatasetStorageOperationRun.state.in_(TERMINAL_RUN_STATES),
                DatasetStorageOperationRun.update_time <= completion_cutoff,
            )
            .returning(DatasetStorageOperationRun.id)
        ).all()
        deleted_count = len(deleted_run_ids)
        sa_session.commit()
        return deleted_count

    def can_prune_expired_snapshot(self, sa_session: galaxy_scoped_session, snapshot_id: int) -> bool:
        snapshot_run_exists = sa_session.execute(
            select(DatasetStorageOperationRun.id).where(
                DatasetStorageOperationRun.snapshot_id == snapshot_id,
            )
        ).first()
        return snapshot_run_exists is None

    def build_preview_response(
        self,
        *,
        sa_session: galaxy_scoped_session,
        security_agent: RBACAgent,
        quota_agent: QuotaAgent,
        history_id: int,
        user: User,
        contents: list[StorageOperationContent],
        target_object_store_id: str,
        snapshot_ttl: timedelta = timedelta(days=UNUSED_SNAPSHOT_EXPIRES_AFTER_DAYS),
        query_based_selection: bool,
    ) -> StorageOperationPreviewResponse:
        preview_builder = self._require_preview_builder()
        return preview_builder.build_preview_response(
            sa_session=sa_session,
            security_agent=security_agent,
            quota_agent=quota_agent,
            history_id=history_id,
            user=user,
            contents=contents,
            target_object_store_id=target_object_store_id,
            snapshot_ttl=snapshot_ttl,
            query_based_selection=query_based_selection,
        )

    def get_snapshot(self, sa_session: galaxy_scoped_session, snapshot_id: int) -> DatasetStorageOperationSnapshot:
        return self._run_manager.get_snapshot(sa_session, snapshot_id)

    def validate_snapshot_for_history(
        self,
        snapshot: DatasetStorageOperationSnapshot,
        *,
        history_id: int,
        user_id: int,
    ) -> None:
        self._run_manager.validate_snapshot_for_history(snapshot, history_id=history_id, user_id=user_id)

    def create_run_and_summary(
        self,
        *,
        sa_session: galaxy_scoped_session,
        snapshot: DatasetStorageOperationSnapshot,
        skip_ineligible: bool,
        notify_on_completion: bool = True,
    ) -> tuple[DatasetStorageOperationRun, StorageOperationRunSummary]:
        return self._run_manager.create_run_and_summary(
            sa_session=sa_session,
            snapshot=snapshot,
            skip_ineligible=skip_ineligible,
            notify_on_completion=notify_on_completion,
        )

    def get_run(
        self,
        *,
        sa_session: galaxy_scoped_session,
        run_id: int,
        history_id: int,
        user_id: int,
    ) -> DatasetStorageOperationRun:
        return self._run_manager.get_run(
            sa_session=sa_session,
            run_id=run_id,
            history_id=history_id,
            user_id=user_id,
        )

    def to_run_summary(self, run: DatasetStorageOperationRun) -> StorageOperationRunSummary:
        return self._run_manager.to_run_summary(run)

    def get_run_items(
        self,
        *,
        sa_session: galaxy_scoped_session,
        run: DatasetStorageOperationRun,
        decode_id: Callable[[str], int],
        offset: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
    ) -> tuple[list[StorageOperationRunItemStatus], int]:
        return self._run_manager.get_run_items(
            sa_session=sa_session,
            run=run,
            decode_id=decode_id,
            offset=offset,
            limit=limit,
            search=search,
        )

    def create_run_executor(
        self,
        *,
        sa_session: galaxy_scoped_session,
        dataset_manager: datasets.DatasetManager,
        app: "MinimalManagerApp",
        run: DatasetStorageOperationRun,
        user: User,
        current_task_id: Optional[str] = None,
    ) -> "StorageOperationRunExecutor":
        return StorageOperationRunExecutor(
            sa_session=sa_session,
            dataset_manager=dataset_manager,
            app=app,
            run=run,
            user=user,
            current_task_id=current_task_id,
            storage_operation_manager=self,
        )

    def _require_preview_builder(self) -> "DatasetStorageOperationPreviewBuilder":
        if self._preview_builder is None:
            raise RuntimeError("Preview operations require an HDCA manager.")
        return self._preview_builder


class DatasetStorageOperationPreviewBuilder:
    """Builds storage operation previews from resolved history contents."""

    def __init__(self, storage_operation_manager: DatasetStorageOperationManager, hdca_manager: "HDCAManager"):
        self.storage_operation_manager = storage_operation_manager
        self.hdca_manager = hdca_manager
        self.object_store = storage_operation_manager.object_store

    def build_preview_response(
        self,
        *,
        sa_session: galaxy_scoped_session,
        security_agent: RBACAgent,
        quota_agent: QuotaAgent,
        history_id: int,
        user: User,
        contents: list[StorageOperationContent],
        target_object_store_id: str,
        snapshot_ttl: timedelta,
        query_based_selection: bool,
    ) -> StorageOperationPreviewResponse:
        selected_items_count = len(contents)
        unique_datasets, expanded_leaf_count = self.resolve_unique_datasets_from_contents(contents)
        preview = self.compute_preview(
            security_agent=security_agent,
            quota_agent=quota_agent,
            user=user,
            unique_datasets=unique_datasets,
            target_object_store_id=target_object_store_id,
        )

        snapshot = self.storage_operation_manager.create_operation_snapshot(
            sa_session=sa_session,
            history_id=history_id,
            user_id=user.id,
            target_object_store_id=target_object_store_id,
            resolved_dataset_ids=list(unique_datasets.keys()),
            eligible_dataset_ids=preview.eligible_dataset_ids,
            snapshot_ttl=snapshot_ttl,
        )

        warnings: list[str] = []
        target_quota_exceeded = any(
            reason.reason_code == DatasetStorageOperationFailureReasonCode.target_quota_exceeded
            for reason in preview.eligibility_reasons
        )
        if target_quota_exceeded:
            warnings.append(
                self.storage_operation_manager.target_quota_exceeded_message(phase_label="before execution")
            )
        if (
            preview.target_quota_projection
            and not preview.target_quota_projection.exceeds_quota
            and preview.target_quota_projection.quota > 0
        ):
            target_quota_percentage = (
                preview.target_quota_projection.projected_usage / preview.target_quota_projection.quota
            ) * 100
            if target_quota_percentage >= NEAR_QUOTA_WARNING_THRESHOLD * 100:
                warnings.append(
                    f"After this operation, the target storage will be at {target_quota_percentage:.0f}% of its quota limit."
                )
        if preview.privacy_downgrade_count > 0:
            warnings.append(
                "Some selected datasets would move from private storage to shareable storage. "
                "After the operation, you will be able to share these datasets with other users."
            )
        if self.storage_operation_manager.is_target_store_expirable(target_object_store_id):
            warnings.append(
                "Datasets in the target storage expire based on their original creation date, so they may expire sooner than expected after moving. "
            )

        return StorageOperationPreviewResponse(
            snapshot_id=_as_encoded_database_id(snapshot.id),
            selection_counts=StorageOperationSelectionCounts(
                selected_items_count=selected_items_count,
                expanded_leaf_count=expanded_leaf_count,
                unique_dataset_count=len(unique_datasets),
            ),
            eligibility=StorageOperationEligibilitySummary(
                eligible_count=preview.eligible_count,
                ineligible_count=preview.ineligible_count,
                reasons=preview.eligibility_reasons,
            ),
            estimates=StorageOperationEstimateSummary(
                bytes_to_transfer=preview.bytes_to_transfer,
                quota_delta_transfers=preview.quota_delta_transfers,
                quota_projection=(
                    StorageOperationQuotaProjectionSummary(
                        projected_usage=preview.target_quota_projection.projected_usage,
                        quota_limit=preview.target_quota_projection.quota,
                    )
                    if preview.target_quota_projection
                    else None
                ),
            ),
            warnings=warnings,
            expires_at=snapshot.expires_at,
        )

    def compute_preview(
        self,
        *,
        security_agent: RBACAgent,
        quota_agent: QuotaAgent,
        user: User,
        unique_datasets: dict[int, Dataset],
        target_object_store_id: str,
    ) -> StorageOperationPreviewComputation:
        eligible_dataset_ids: list[int] = []
        eligibility_reason_counts: dict[DatasetStorageOperationFailureReasonCode, int] = {}
        eligible_count = 0
        ineligible_count = 0
        bytes_to_transfer = 0
        running_additional_target_usage = 0
        quota_delta_transfer_totals: dict[tuple[str, str], int] = {}
        privacy_downgrade_count = 0
        quota_source_map = self.object_store.get_quota_source_map()

        for dataset_id, dataset in unique_datasets.items():
            reason = self.storage_operation_manager.validate_dataset_for_move(
                security_agent,
                user,
                dataset,
                target_object_store_id,
            )

            if reason is None:
                dataset_size = int(dataset.get_total_size() or 0)
                source_quota_label = quota_source_map.get_quota_source_label(dataset.object_store_id)
                target_quota_label = quota_source_map.get_quota_source_label(target_object_store_id)
                dataset_target_quota_delta = self.storage_operation_manager.target_quota_delta(
                    dataset_size,
                    source_quota_label,
                    target_quota_label,
                )

                target_quota_projection = self.storage_operation_manager.target_quota_projection(
                    quota_agent,
                    user,
                    target_object_store_id,
                    dataset_target_quota_delta,
                    additional_target_usage=running_additional_target_usage,
                )
                if target_quota_projection and target_quota_projection.exceeds_quota:
                    ineligible_count += 1
                    self._increment_eligibility_reason(
                        eligibility_reason_counts,
                        DatasetStorageOperationFailureReasonCode.target_quota_exceeded,
                    )
                    continue

                eligible_count += 1
                eligible_dataset_ids.append(dataset_id)

                if self.storage_operation_manager.requires_data_transfer(dataset, target_object_store_id):
                    bytes_to_transfer += dataset_size

                old_label = quota_source_map.get_quota_source_label(dataset.object_store_id) or "default"
                new_label = quota_source_map.get_quota_source_label(target_object_store_id) or "default"
                if old_label != new_label:
                    source_object_store_id = dataset.object_store_id
                    if source_object_store_id:
                        key = (source_object_store_id, target_object_store_id)
                        quota_delta_transfer_totals[key] = quota_delta_transfer_totals.get(key, 0) + dataset_size

                running_additional_target_usage += dataset_target_quota_delta
                if self.storage_operation_manager.is_privacy_downgrade_for_target(dataset, target_object_store_id):
                    privacy_downgrade_count += 1
            else:
                ineligible_count += 1
                self._increment_eligibility_reason(eligibility_reason_counts, reason)

        quota_delta_transfers = [
            StorageOperationQuotaDeltaTransfer(
                source_object_store_id=source_object_store_id,
                target_object_store_id=target_object_store_id,
                bytes=bytes_delta,
            )
            for (source_object_store_id, target_object_store_id), bytes_delta in sorted(
                quota_delta_transfer_totals.items()
            )
        ]
        target_quota_projection = self.storage_operation_manager.target_quota_projection(
            quota_agent,
            user,
            target_object_store_id,
            running_additional_target_usage,
        )

        return StorageOperationPreviewComputation(
            eligible_dataset_ids=eligible_dataset_ids,
            eligibility_reasons=[
                StorageOperationEligibilityReasonSummary(
                    reason_code=reason_code,
                    count=count,
                )
                for reason_code, count in eligibility_reason_counts.items()
            ],
            eligible_count=eligible_count,
            ineligible_count=ineligible_count,
            bytes_to_transfer=bytes_to_transfer,
            target_quota_delta=running_additional_target_usage,
            quota_delta_transfers=quota_delta_transfers,
            privacy_downgrade_count=privacy_downgrade_count,
            target_quota_projection=target_quota_projection,
        )

    def _increment_eligibility_reason(
        self,
        eligibility_reason_counts: dict[DatasetStorageOperationFailureReasonCode, int],
        reason_code: DatasetStorageOperationFailureReasonCode,
        *,
        count: int = 1,
    ) -> None:
        if count <= 0:
            return
        eligibility_reason_counts[reason_code] = eligibility_reason_counts.get(reason_code, 0) + count

    def resolve_unique_datasets_from_contents(
        self, contents: list[StorageOperationContent]
    ) -> tuple[dict[int, Dataset], int]:
        unique_datasets: dict[int, Dataset] = {}
        expanded_leaf_count = 0

        for content in contents:
            if isinstance(content, HistoryDatasetAssociation):
                dataset = content.dataset
                if dataset is None:
                    continue
                expanded_leaf_count += 1
                unique_datasets[dataset.id] = dataset
            elif isinstance(content, HistoryDatasetCollectionAssociation):
                hdas = self.hdca_manager.map_datasets(content, fn=lambda item, *parents: item)
                for hda in hdas:
                    dataset = hda.dataset
                    if dataset is None:
                        continue
                    expanded_leaf_count += 1
                    unique_datasets[dataset.id] = dataset

        return unique_datasets, expanded_leaf_count


class DatasetStorageOperationRunManager:
    """Handles snapshot/run validation, summaries, and run-item queries."""

    def __init__(self, storage_operation_manager: DatasetStorageOperationManager):
        self.storage_operation_manager = storage_operation_manager

    def get_snapshot(self, sa_session: galaxy_scoped_session, snapshot_id: int) -> DatasetStorageOperationSnapshot:
        snapshot = sa_session.get(DatasetStorageOperationSnapshot, snapshot_id)
        if snapshot is None:
            raise exceptions.ObjectNotFound("Storage operation snapshot not found.")
        if snapshot.expires_at <= now():
            if self.storage_operation_manager.can_prune_expired_snapshot(sa_session, snapshot.id):
                sa_session.delete(snapshot)
                sa_session.commit()
            raise exceptions.RequestParameterInvalidException("Storage operation snapshot has expired.")
        return snapshot

    def validate_snapshot_for_history(
        self,
        snapshot: DatasetStorageOperationSnapshot,
        *,
        history_id: int,
        user_id: int,
    ) -> None:
        if snapshot.history_id != history_id:
            raise exceptions.RequestParameterInvalidException("Snapshot does not belong to the requested history.")
        if snapshot.user_id != user_id:
            raise exceptions.RequestParameterInvalidException("Snapshot does not belong to the current user.")

    def create_run_and_summary(
        self,
        *,
        sa_session: galaxy_scoped_session,
        snapshot: DatasetStorageOperationSnapshot,
        skip_ineligible: bool,
        notify_on_completion: bool = True,
    ) -> tuple[DatasetStorageOperationRun, StorageOperationRunSummary]:
        run = self.storage_operation_manager.create_operation_run(
            sa_session=sa_session,
            snapshot=snapshot,
            skip_ineligible=skip_ineligible,
            notify_on_completion=notify_on_completion,
        )
        return run, self.to_run_summary(run)

    def get_run(
        self,
        *,
        sa_session: galaxy_scoped_session,
        run_id: int,
        history_id: int,
        user_id: int,
    ) -> DatasetStorageOperationRun:
        run = sa_session.get(DatasetStorageOperationRun, run_id)
        if run is None:
            raise exceptions.ObjectNotFound("Storage operation run not found.")
        if run.history_id != history_id:
            raise exceptions.RequestParameterInvalidException("Run does not belong to the requested history.")
        if run.user_id != user_id:
            raise exceptions.RequestParameterInvalidException("Run does not belong to the current user.")
        return run

    def to_run_summary(self, run: DatasetStorageOperationRun) -> StorageOperationRunSummary:
        return StorageOperationRunSummary(
            run_id=_as_encoded_database_id(run.id),
            state=StorageOperationRunState(run.state),
            mode=StorageOperationMode(run.mode),
            target_object_store_id=run.target_object_store_id,
            create_time=run.create_time,
            update_time=run.update_time,
            total_count=run.total_count,
            succeeded_count=run.succeeded_count,
            failed_count=run.failed_count,
            skipped_count=run.skipped_count,
            total_bytes_processed=run.total_bytes_processed,
            task_id=UUID(str(run.task_id)) if run.task_id is not None else None,
        )

    def get_run_items(
        self,
        *,
        sa_session: galaxy_scoped_session,
        run: DatasetStorageOperationRun,
        decode_id: Callable[[str], int],
        offset: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
    ) -> tuple[list[StorageOperationRunItemStatus], int]:
        run_items_query = sa_session.query(DatasetStorageOperationRunItem).filter(
            DatasetStorageOperationRunItem.run_id == run.id
        )

        if search and search.strip():
            parsed_search = parse_filters_structured(
                search.strip(),
                {
                    "state": "state",
                    "reason": "reason_code",
                    "reason_code": "reason_code",
                    "dataset": "dataset_id",
                    "dataset_id": "dataset_id",
                },
            )

            for filter_name in ("state", "reason_code", "dataset_id"):
                filter_terms = [term for term in parsed_search.filter_terms if term.filter == filter_name]
                if not filter_terms:
                    continue

                if filter_name == "dataset_id":
                    dataset_ids = self._decode_storage_run_item_dataset_ids(
                        [term.text for term in filter_terms], decode_id=decode_id
                    )
                    if not dataset_ids:
                        run_items_query = run_items_query.filter(false())
                        break
                    run_items_query = run_items_query.filter(DatasetStorageOperationRunItem.dataset_id.in_(dataset_ids))
                    continue

                column = getattr(DatasetStorageOperationRunItem, filter_name)
                filter_conditions = []
                for term in filter_terms:
                    if term.quoted:
                        filter_conditions.append(column == term.text)
                    else:
                        filter_conditions.append(column.ilike(f"%{term.text}%"))
                run_items_query = run_items_query.filter(or_(*filter_conditions))

            for text_term in parsed_search.text_terms:
                text = text_term.text
                if not text:
                    continue

                if text_term.quoted:
                    free_text_conditions: list[ColumnElement[bool]] = [
                        DatasetStorageOperationRunItem.state == text,
                        DatasetStorageOperationRunItem.reason_code == text,
                    ]
                else:
                    free_text_conditions = [
                        DatasetStorageOperationRunItem.state.ilike(f"%{text}%"),
                        DatasetStorageOperationRunItem.reason_code.ilike(f"%{text}%"),
                    ]

                dataset_ids = self._decode_storage_run_item_dataset_ids([text], decode_id=decode_id)
                if dataset_ids:
                    free_text_conditions.append(DatasetStorageOperationRunItem.dataset_id.in_(dataset_ids))

                run_items_query = run_items_query.filter(or_(*free_text_conditions))

        total_matches = run_items_query.count()
        run_items = run_items_query.order_by(DatasetStorageOperationRunItem.id.asc()).offset(offset).limit(limit).all()
        items = [
            StorageOperationRunItemStatus(
                dataset_id=_as_encoded_database_id(run_item.dataset_id),
                state=StorageOperationRunItemState(run_item.state),
                reason_code=(
                    DatasetStorageOperationFailureReasonCode(run_item.reason_code) if run_item.reason_code else None
                ),
                bytes_processed=run_item.bytes_processed,
                create_time=run_item.create_time,
                update_time=run_item.update_time,
            )
            for run_item in run_items
        ]
        return items, total_matches

    def _decode_storage_run_item_dataset_ids(
        self,
        encoded_or_raw_ids: list[str],
        *,
        decode_id: Callable[[str], int],
    ) -> list[int]:
        dataset_ids: list[int] = []
        for value in encoded_or_raw_ids:
            if not value:
                continue
            if value.isdigit():
                dataset_ids.append(int(value))
                continue
            try:
                dataset_ids.append(decode_id(value))
            except Exception:
                continue
        return dataset_ids


class ChecksumVerificationError(ValueError):
    """Raised when post-copy checksum verification detects a mismatch."""


class StorageOperationRunExecutor:
    """Executes a storage operation run and returns notification outcome details to the caller."""

    def __init__(
        self,
        *,
        sa_session: galaxy_scoped_session,
        dataset_manager: datasets.DatasetManager,
        app: "MinimalManagerApp",
        run: DatasetStorageOperationRun,
        user: User,
        current_task_id: Optional[str],
        storage_operation_manager: DatasetStorageOperationManager,
    ):
        self.sa_session = sa_session
        self.dataset_manager = dataset_manager
        self.app = app
        self.run = run
        self.user = user
        self.current_task_id = current_task_id
        self.trans = SimpleNamespace(user=user)
        self.storage_operation_manager = storage_operation_manager
        self.quota_source_map = app.object_store.get_quota_source_map()
        self.target_quota_usage_at_start = 0
        self.target_quota_source_label = self.quota_source_map.get_quota_source_label(run.target_object_store_id)
        self.target_quota_limit = app.quota_agent.get_quota(user, quota_source_label=self.target_quota_source_label)
        if self.target_quota_source_label is None:
            self.target_quota_usage_at_start = int(user.total_disk_usage or 0)
        else:
            quota_source_usage = user.quota_source_usage_for(self.target_quota_source_label)
            self.target_quota_usage_at_start = int(quota_source_usage.disk_usage or 0) if quota_source_usage else 0
        self.additional_target_usage = 0
        self.succeeded_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.total_bytes_processed = 0
        self.progress_commit_every = PROGRESS_COMMIT_INTERVAL_SMALL_RUN
        self.datasets_since_progress_commit = 0
        self.run_items_by_dataset_id_cache: dict[int, DatasetStorageOperationRunItem] = {}
        self._pending_dataset_update_ids: set[int] = set()
        # Cleanups queued during transfer; executed after batch DB commit to ensure durability.
        self._pending_cleanups: list[tuple[DatasetObjectStoreProxy, Optional[str]]] = []

    def execute_run(self, snapshot: Optional[DatasetStorageOperationSnapshot]) -> StorageOperationExecutionResult:
        """Validate snapshot, drive state transitions, execute all datasets, and return execution outcome."""
        if snapshot is None:
            return self._fail_run("Bulk storage run failed because its preview snapshot could not be found.")

        if snapshot.expires_at <= now():
            return self._fail_run("Bulk storage run failed because its preview snapshot expired before execution.")

        run_items_by_dataset_id = self._run_items_by_dataset_id()
        self.run_items_by_dataset_id_cache = run_items_by_dataset_id
        self._reconcile_interrupted_items(run_items_by_dataset_id)
        self._rebuild_run_progress(self.run_items_by_dataset_id_cache.values())

        remaining_dataset_ids = self._remaining_dataset_ids(
            snapshot.resolved_dataset_ids, self.run_items_by_dataset_id_cache
        )
        if not remaining_dataset_ids:
            return self._complete_run(snapshot.resolved_dataset_ids)

        self.progress_commit_every = self._progress_commit_interval(len(remaining_dataset_ids))
        self.datasets_since_progress_commit = 0

        if not self._owns_run():
            return StorageOperationExecutionResult(
                state=StorageOperationRunState.running,
                message="Bulk storage run ownership moved to another worker.",
            )

        self.run.state = "running"
        self.sa_session.add(self.run)
        self.sa_session.commit()

        if self._execute(remaining_dataset_ids) is None:
            return StorageOperationExecutionResult(
                state=StorageOperationRunState.running,
                message="Bulk storage run ownership moved to another worker.",
            )

        return self._complete_run(snapshot.resolved_dataset_ids)

    def _complete_run(self, resolved_dataset_ids: list[int]) -> StorageOperationExecutionResult:
        succeeded_count = self.succeeded_count
        failed_count = self.failed_count
        skipped_count = self.skipped_count

        self.run.state = "completed"
        self.run.total_count = len(resolved_dataset_ids)
        self.run.succeeded_count = succeeded_count
        self.run.failed_count = failed_count
        self.run.skipped_count = skipped_count
        self.run.total_bytes_processed = self.total_bytes_processed
        self.sa_session.add(self.run)
        self.sa_session.commit()

        if failed_count > 0 or skipped_count > 0:
            message = "Bulk storage run finished with partial success. Check the run details for more information."
        else:
            message = f"Bulk {self.run.mode} run completed successfully for {succeeded_count} dataset(s)."

        return StorageOperationExecutionResult(state=StorageOperationRunState.completed, message=message)

    def _fail_run(self, message: str) -> StorageOperationExecutionResult:
        self._flush_pending_dataset_updates()
        self.run.state = "failed"
        self.run.failed_count = self.run.total_count if self.run.total_count else 0
        self.sa_session.add(self.run)
        self.sa_session.commit()
        return StorageOperationExecutionResult(
            state=StorageOperationRunState.failed,
            message=message,
        )

    def _execute(self, resolved_dataset_ids: list[int]) -> Optional[tuple[int, int, int, int]]:
        for dataset_id in resolved_dataset_ids:
            if not self._owns_run():
                return None
            self._process_dataset(dataset_id)
            self.datasets_since_progress_commit += 1
            self._persist_run_progress()
        self._persist_run_progress(force=True)
        # Flush all queued source cleanups only after DB is durable.
        # This ensures that if the worker crashes, recovery will see completed state
        # and datasets won't point to deleted files.
        self._flush_pending_cleanups()
        return self.succeeded_count, self.failed_count, self.skipped_count, self.total_bytes_processed

    def _progress_commit_interval(self, remaining_count: int) -> int:
        if remaining_count <= 10:
            return PROGRESS_COMMIT_INTERVAL_SMALL_RUN
        if remaining_count <= 100:
            return PROGRESS_COMMIT_INTERVAL_MEDIUM_RUN
        if remaining_count <= 1000:
            return PROGRESS_COMMIT_INTERVAL_LARGE_RUN
        return PROGRESS_COMMIT_INTERVAL_XL_RUN

    def _run_items_by_dataset_id(self) -> dict[int, DatasetStorageOperationRunItem]:
        run_items = self.sa_session.execute(
            select(DatasetStorageOperationRunItem).where(DatasetStorageOperationRunItem.run_id == self.run.id)
        ).scalars()
        return {run_item.dataset_id: run_item for run_item in run_items}

    def _rebuild_run_progress(self, run_items: Iterable[DatasetStorageOperationRunItem]) -> None:
        self.succeeded_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.total_bytes_processed = 0

        for run_item in run_items:
            if run_item.state == StorageOperationRunItemState.succeeded.value:
                self.succeeded_count += 1
                self.total_bytes_processed += int(run_item.bytes_processed or 0)
            elif run_item.state == StorageOperationRunItemState.failed.value:
                self.failed_count += 1
            elif run_item.state == StorageOperationRunItemState.skipped.value:
                self.skipped_count += 1

    def _reconcile_interrupted_items(self, run_items_by_dataset_id: dict[int, DatasetStorageOperationRunItem]) -> None:
        running_dataset_ids = [
            dataset_id
            for dataset_id, run_item in run_items_by_dataset_id.items()
            if run_item.state == StorageOperationRunItemState.running.value
        ]
        if not running_dataset_ids:
            return

        datasets = self.sa_session.execute(select(Dataset).where(Dataset.id.in_(running_dataset_ids))).scalars().all()
        datasets_by_id = {dataset.id: dataset for dataset in datasets}

        reconciled = False
        for dataset_id in running_dataset_ids:
            run_item = run_items_by_dataset_id[dataset_id]
            dataset = datasets_by_id.get(dataset_id)
            if dataset is None or dataset.purged:
                self._add_run_item(
                    dataset_id=dataset_id,
                    state=StorageOperationRunItemState.failed.value,
                    reason_code=DatasetStorageOperationFailureReasonCode.dataset_not_found,
                )
            elif dataset.object_store_id == self.run.target_object_store_id:
                self._add_run_item(
                    dataset_id=dataset_id,
                    state=StorageOperationRunItemState.succeeded.value,
                    bytes_processed=run_item.bytes_processed or int(dataset.get_total_size() or 0),
                )
            elif self._reconcile_completed_cross_device_transfer(dataset, run_item):
                pass
            else:
                self._add_run_item(
                    dataset_id=dataset_id,
                    state=StorageOperationRunItemState.pending.value,
                    reason_code=None,
                    bytes_processed=0,
                )
            reconciled = True

        if reconciled:
            self._flush_pending_dataset_updates()
            self.sa_session.commit()

    def _reconcile_completed_cross_device_transfer(
        self,
        dataset: Dataset,
        run_item: DatasetStorageOperationRunItem,
    ) -> bool:
        if not self.storage_operation_manager.requires_data_transfer(dataset, self.run.target_object_store_id):
            return False

        source_object_store_id = dataset.object_store_id
        if source_object_store_id is None:
            return False

        source_proxy = self._dataset_proxy(dataset, str(source_object_store_id))
        target_proxy = self._dataset_proxy(dataset, self.run.target_object_store_id)
        source_exists = self._source_dataset_exists(source_proxy)
        target_exists = self._target_dataset_exists(target_proxy)

        if not source_exists and target_exists:
            self._finalize_cross_device_move(dataset, self.run.target_object_store_id)
            self._add_run_item(
                dataset_id=dataset.id,
                state=StorageOperationRunItemState.succeeded.value,
                bytes_processed=run_item.bytes_processed or int(dataset.get_total_size() or 0),
            )
            self._notify_dataset_update(dataset)
            return True

        if not source_exists and not target_exists:
            self._add_run_item(
                dataset_id=dataset.id,
                state=StorageOperationRunItemState.failed.value,
                reason_code=DatasetStorageOperationFailureReasonCode.execution_error,
            )
            return True

        return False

    def _remaining_dataset_ids(
        self, resolved_dataset_ids: list[int], run_items_by_dataset_id: dict[int, DatasetStorageOperationRunItem]
    ) -> list[int]:
        remaining_dataset_ids = []
        for dataset_id in resolved_dataset_ids:
            run_item = run_items_by_dataset_id.get(dataset_id)
            if run_item is None or run_item.state not in TERMINAL_RUN_ITEM_STATES:
                remaining_dataset_ids.append(dataset_id)
        return remaining_dataset_ids

    def _owns_run(self) -> bool:
        if self.current_task_id is None:
            return True
        self.sa_session.refresh(self.run)
        if self.run.state in TERMINAL_RUN_STATES:
            return False
        if self.run.task_id is None:
            return False
        return str(self.run.task_id) == str(self.current_task_id)

    def _process_dataset(self, dataset_id: int):
        dataset = self.sa_session.get(Dataset, dataset_id)
        if dataset is None or dataset.purged:
            self.failed_count += 1
            self._add_run_item(
                dataset_id=dataset_id,
                state="failed",
                reason_code=DatasetStorageOperationFailureReasonCode.dataset_not_found,
            )
            return

        source_quota_label = self.quota_source_map.get_quota_source_label(dataset.object_store_id)
        dataset_size = int(dataset.get_total_size() or 0)
        quota_delta = self.storage_operation_manager.target_quota_delta(
            dataset_size,
            source_quota_label,
            self.target_quota_source_label,
        )

        reason_code = self._validate_dataset(dataset, quota_delta)
        if reason_code is not None:
            self._record_ineligible(dataset_id, reason_code)
            return

        self._execute_dataset_transfer(dataset, dataset_id, quota_delta)

    def _validate_dataset(
        self,
        dataset: Dataset,
        quota_delta: int,
    ) -> Optional[DatasetStorageOperationFailureReasonCode]:
        reason = self.storage_operation_manager.validate_dataset_for_move(
            self.app.security_agent,
            self.user,
            dataset,
            self.run.target_object_store_id,
        )
        if reason is not None:
            return reason

        if self.target_quota_limit is not None and quota_delta > 0:
            projected_usage = self.target_quota_usage_at_start + self.additional_target_usage + quota_delta
            if projected_usage > self.target_quota_limit:
                return DatasetStorageOperationFailureReasonCode.target_quota_exceeded

        return None

    def _record_ineligible(
        self,
        dataset_id: int,
        reason_code: DatasetStorageOperationFailureReasonCode,
    ):
        state = "skipped" if self.run.skip_ineligible else "failed"
        if state == "skipped":
            self.skipped_count += 1
        else:
            self.failed_count += 1
        self._add_run_item(
            dataset_id=dataset_id,
            state=state,
            reason_code=reason_code,
        )

    def _execute_dataset_transfer(self, dataset: Dataset, dataset_id: int, quota_delta: int):
        run_item = self._mark_run_item_running(dataset_id)
        # Capture source store ID early to avoid issues with in-memory mutations during retries.
        source_store_id = dataset.object_store_id
        assert source_store_id is not None, "Dataset object_store_id cannot be None for transfer operations."
        source_proxy = self._dataset_proxy(dataset, str(source_store_id))
        target_proxy = self._dataset_proxy(dataset, self.run.target_object_store_id)
        extra_files_path_name = dataset.extra_files_path_name
        requires_data_transfer = self.storage_operation_manager.requires_data_transfer(
            dataset, self.run.target_object_store_id
        )
        if not self._source_dataset_exists(source_proxy):
            self._record_transfer_failure(
                dataset_id,
                DatasetStorageOperationFailureReasonCode.dataset_not_found,
                run_item=run_item,
            )
            return

        for attempt in range(1, TRANSFER_RETRY_ATTEMPTS + 1):
            target_proxy_for_cleanup: Optional[DatasetObjectStoreProxy] = None
            try:
                bytes_processed = 0
                if requires_data_transfer:
                    target_proxy_for_cleanup = target_proxy
                    bytes_processed = self._copy_dataset_to_target_store(
                        dataset, source_store_id, self.run.target_object_store_id
                    )
                    self._verify_copied_dataset_integrity(dataset, source_store_id, self.run.target_object_store_id)
                    self._finalize_cross_device_move(dataset, self.run.target_object_store_id)
                    # Queue cleanup for after DB commit to ensure crash safety.
                    self._pending_cleanups.append((source_proxy, extra_files_path_name))
                else:
                    self.dataset_manager.update_object_store_id(self.trans, dataset, self.run.target_object_store_id)

                self.additional_target_usage += quota_delta
                self.succeeded_count += 1
                self.total_bytes_processed += bytes_processed
                self._add_run_item(
                    dataset_id=dataset_id,
                    state=StorageOperationRunItemState.succeeded.value,
                    bytes_processed=bytes_processed,
                )
                self._notify_dataset_update(dataset)
                return
            except ChecksumVerificationError as exc:
                log.warning(
                    "Integrity verification failed for run %s dataset %s (attempt %s/%s): %s",
                    self.run.id,
                    dataset.id,
                    attempt,
                    TRANSFER_RETRY_ATTEMPTS,
                    exc,
                )
                if target_proxy_for_cleanup is not None:
                    self._cleanup_target_dataset_data(target_proxy_for_cleanup, extra_files_path_name)
                if attempt < TRANSFER_RETRY_ATTEMPTS and requires_data_transfer:
                    continue
                self._record_transfer_failure(
                    dataset_id,
                    DatasetStorageOperationFailureReasonCode.checksum_verification_failed,
                    run_item=run_item,
                )
                return
            except Exception:
                log.exception(
                    "Storage operation execution error for run %s dataset %s (attempt %s/%s)",
                    self.run.id,
                    dataset.id,
                    attempt,
                    TRANSFER_RETRY_ATTEMPTS,
                )
                if target_proxy_for_cleanup is not None:
                    self._cleanup_target_dataset_data(target_proxy_for_cleanup, extra_files_path_name)
                if attempt < TRANSFER_RETRY_ATTEMPTS and requires_data_transfer:
                    continue
                self._record_transfer_failure(
                    dataset_id,
                    DatasetStorageOperationFailureReasonCode.execution_error,
                    run_item=run_item,
                )
                return

    def _source_dataset_exists(self, source_proxy: DatasetObjectStoreProxy) -> bool:
        try:
            return bool(self.app.object_store.exists(source_proxy))
        except Exception:
            return False

    def _target_dataset_exists(self, target_proxy: DatasetObjectStoreProxy) -> bool:
        try:
            return bool(self.app.object_store.exists(target_proxy))
        except Exception:
            return False

    def _notify_dataset_update(self, dataset: Dataset):
        self._pending_dataset_update_ids.add(dataset.id)

    def _flush_pending_dataset_updates(self) -> None:
        if not self._pending_dataset_update_ids:
            return

        datasets = (
            self.sa_session.execute(select(Dataset).where(Dataset.id.in_(self._pending_dataset_update_ids)))
            .scalars()
            .all()
        )
        for dataset in datasets:
            # Touching dataset-linked collections drives history refreshes for clients.
            dataset.touch_collection_update_time()
        self._pending_dataset_update_ids.clear()

    def _record_transfer_failure(
        self,
        dataset_id: int,
        reason_code: DatasetStorageOperationFailureReasonCode,
        run_item: Optional[DatasetStorageOperationRunItem] = None,
    ) -> None:
        self.failed_count += 1
        self._add_run_item(
            dataset_id=dataset_id,
            state="failed",
            reason_code=reason_code,
            bytes_processed=run_item.bytes_processed if run_item is not None else 0,
        )

    def _persist_run_progress(self, force: bool = False) -> None:
        if not force and self.datasets_since_progress_commit < self.progress_commit_every:
            return
        self._flush_pending_dataset_updates()
        self.run.succeeded_count = self.succeeded_count
        self.run.failed_count = self.failed_count
        self.run.skipped_count = self.skipped_count
        self.run.total_bytes_processed = self.total_bytes_processed
        self.sa_session.add(self.run)
        self.sa_session.commit()
        self.datasets_since_progress_commit = 0

    def _flush_pending_cleanups(self) -> None:
        """Execute queued source file cleanups after DB is durable.

        This ensures crash safety: if the worker fails, the DB reflects success
        and recovery will find source files already gone (expected state).
        """
        for source_proxy, extra_files_path_name in self._pending_cleanups:
            self._cleanup_source_dataset_data(source_proxy, extra_files_path_name)
        self._pending_cleanups.clear()

    def _add_run_item(
        self,
        *,
        dataset_id: int,
        state: str,
        reason_code: Optional[DatasetStorageOperationFailureReasonCode] = None,
        bytes_processed: int = 0,
    ) -> DatasetStorageOperationRunItem:
        run_item = self.run_items_by_dataset_id_cache.get(dataset_id)
        if run_item is None:
            run_item = self.sa_session.execute(
                select(DatasetStorageOperationRunItem).where(
                    DatasetStorageOperationRunItem.run_id == self.run.id,
                    DatasetStorageOperationRunItem.dataset_id == dataset_id,
                )
            ).scalar_one_or_none()
        if run_item is None:
            run_item = DatasetStorageOperationRunItem(
                run_id=self.run.id,
                dataset_id=dataset_id,
                state=state,
                reason_code=reason_code,
                bytes_processed=bytes_processed,
            )
            self.run_items_by_dataset_id_cache[dataset_id] = run_item
        else:
            run_item.state = state
            run_item.reason_code = reason_code
            run_item.bytes_processed = bytes_processed
            self.run_items_by_dataset_id_cache[dataset_id] = run_item
        self.sa_session.add(run_item)
        return run_item

    def _mark_run_item_running(self, dataset_id: int) -> DatasetStorageOperationRunItem:
        return self._add_run_item(
            dataset_id=dataset_id,
            state=StorageOperationRunItemState.running.value,
            bytes_processed=0,
        )

    def _dataset_proxy(self, dataset: Dataset, object_store_id: str) -> DatasetObjectStoreProxy:
        return DatasetObjectStoreProxy(id=dataset.id, uuid=dataset.uuid, object_store_id=object_store_id)

    def _copy_dataset_to_target_store(self, dataset: Dataset, source_store_id: str, target_object_store_id: str) -> int:
        source_proxy = self._dataset_proxy(dataset, source_store_id)
        target_proxy = self._dataset_proxy(dataset, target_object_store_id)

        source_filename = self.app.object_store.get_filename(source_proxy)
        self.app.object_store.update_from_file(
            target_proxy,
            file_name=source_filename,
            create=True,
            preserve_symlinks=False,
        )

        extra_files_path_name = dataset.extra_files_path_name
        if extra_files_path_name:
            self._copy_extra_files(source_proxy, target_proxy, extra_files_path_name)

        return int(dataset.get_total_size() or 0)

    def _copy_extra_files(
        self,
        source_proxy: DatasetObjectStoreProxy,
        target_proxy: DatasetObjectStoreProxy,
        extra_files_path_name: str,
    ) -> None:
        if not self.app.object_store.exists(source_proxy, dir_only=True, extra_dir=extra_files_path_name):
            return

        src_extra_dir = Path(
            self.app.object_store.get_filename(source_proxy, dir_only=True, extra_dir=extra_files_path_name)
        )
        for file_path in src_extra_dir.rglob("*"):
            if not file_path.is_file():
                continue
            relative_parent = file_path.parent.relative_to(src_extra_dir)
            extra_dir = extra_files_path_name
            if str(relative_parent) != ".":
                extra_dir = f"{extra_files_path_name}/{relative_parent.as_posix()}"
            self.app.object_store.update_from_file(
                target_proxy,
                extra_dir=extra_dir,
                alt_name=file_path.name,
                file_name=str(file_path),
                create=True,
                preserve_symlinks=False,
            )

    def _verify_copied_dataset_integrity(self, dataset: Dataset, source_store_id: str, target_object_store_id: str):
        source_proxy = self._dataset_proxy(dataset, source_store_id)
        target_proxy = self._dataset_proxy(dataset, target_object_store_id)

        source_filename = self.app.object_store.get_filename(source_proxy)
        target_filename = self.app.object_store.get_filename(target_proxy)
        source_hash = self._sha256(source_filename)
        target_hash = self._sha256(target_filename)
        if source_hash != target_hash:
            raise ChecksumVerificationError("Primary file checksum mismatch between source and target.")

        extra_files_path_name = dataset.extra_files_path_name
        if not extra_files_path_name:
            return

        self._verify_extra_files_integrity(
            source_proxy=source_proxy,
            target_proxy=target_proxy,
            extra_files_path_name=extra_files_path_name,
        )

    def _verify_extra_files_integrity(
        self,
        *,
        source_proxy: DatasetObjectStoreProxy,
        target_proxy: DatasetObjectStoreProxy,
        extra_files_path_name: str,
    ) -> None:

        source_has_extra = self.app.object_store.exists(source_proxy, dir_only=True, extra_dir=extra_files_path_name)
        target_has_extra = self.app.object_store.exists(target_proxy, dir_only=True, extra_dir=extra_files_path_name)
        if source_has_extra != target_has_extra:
            raise ChecksumVerificationError("Extra files presence differs between source and target.")
        if not source_has_extra:
            return

        src_extra_dir = Path(
            self.app.object_store.get_filename(source_proxy, dir_only=True, extra_dir=extra_files_path_name)
        )
        tgt_extra_dir = Path(
            self.app.object_store.get_filename(target_proxy, dir_only=True, extra_dir=extra_files_path_name)
        )

        source_rel_paths = {
            file_path.relative_to(src_extra_dir).as_posix()
            for file_path in src_extra_dir.rglob("*")
            if file_path.is_file()
        }
        target_rel_paths = {
            file_path.relative_to(tgt_extra_dir).as_posix()
            for file_path in tgt_extra_dir.rglob("*")
            if file_path.is_file()
        }
        if source_rel_paths != target_rel_paths:
            raise ChecksumVerificationError("Extra files layout differs between source and target.")

        for relative_path in sorted(source_rel_paths):
            source_file = src_extra_dir / relative_path
            target_file = tgt_extra_dir / relative_path
            source_hash = self._sha256(str(source_file))
            target_hash = self._sha256(str(target_file))
            if source_hash != target_hash:
                raise ChecksumVerificationError("Extra file checksum mismatch between source and target.")

    def _sha256(self, path: str) -> str:
        return memory_bound_hexdigest(hash_func_name=HashFunctionNameEnum.sha256, path=path)

    def _cleanup_source_dataset_data(
        self,
        source_proxy: DatasetObjectStoreProxy,
        extra_files_path_name: Optional[str],
    ) -> None:
        try:
            self.app.object_store.delete(source_proxy)
        except Exception:
            log.warning(
                "Failed to delete source dataset file after storage move for run %s dataset %s",
                self.run.id,
                source_proxy.id,
                exc_info=True,
            )

        if not extra_files_path_name:
            return

        try:
            if self.app.object_store.exists(source_proxy, dir_only=True, extra_dir=extra_files_path_name):
                self.app.object_store.delete(
                    source_proxy,
                    entire_dir=True,
                    extra_dir=extra_files_path_name,
                    dir_only=True,
                )
        except Exception:
            log.warning(
                "Failed to delete source extra files after storage move for run %s dataset %s",
                self.run.id,
                source_proxy.id,
                exc_info=True,
            )

    def _cleanup_target_dataset_data(
        self,
        target_proxy: DatasetObjectStoreProxy,
        extra_files_path_name: Optional[str],
    ) -> None:
        try:
            self.app.object_store.delete(target_proxy)
        except Exception:
            log.warning(
                "Failed to delete target dataset file while rolling back failed storage move for run %s dataset %s",
                self.run.id,
                target_proxy.id,
                exc_info=True,
            )

        if not extra_files_path_name:
            return

        try:
            if self.app.object_store.exists(target_proxy, dir_only=True, extra_dir=extra_files_path_name):
                self.app.object_store.delete(
                    target_proxy,
                    entire_dir=True,
                    extra_dir=extra_files_path_name,
                    dir_only=True,
                )
        except Exception:
            log.warning(
                "Failed to delete target extra files while rolling back failed storage move for run %s dataset %s",
                self.run.id,
                target_proxy.id,
                exc_info=True,
            )

    def _finalize_cross_device_move(self, dataset: Dataset, target_object_store_id: str):
        old_object_store_id = dataset.object_store_id
        quota_source_map = self.app.object_store.get_quota_source_map()
        if quota_source_map:
            old_label = quota_source_map.get_quota_source_label(old_object_store_id)
            new_label = quota_source_map.get_quota_source_label(target_object_store_id)
            if old_label != new_label:
                self.app.quota_agent.relabel_quota_for_dataset(dataset, old_label, new_label)
        dataset.object_store_id = target_object_store_id
        self.sa_session.add(dataset)
