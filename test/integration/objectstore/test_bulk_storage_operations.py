"""Integration tests for bulk storage operations (preview / execute / run status).

These run against a real Galaxy instance with a distributed object store that has
five backends:

* ``default``         – main store, weight=1, device ``tmp_disk``
* ``other``           – secondary store, weight=0, same device ``tmp_disk``
* ``separate_device`` – weight=0, different device ``other_disk``
* ``expirable_store`` – disk store with object expiration enabled
* ``private_store``   – private disk store used for warning and quota coverage

Tests cover:
- Preview: eligibility classification and snapshot creation
- Reason codes: already_in_target, invalid_target_object_store
- Warnings: private-source to non-private target moves
- Execute: run is created and dispatched
- Run lifecycle: pending -> running -> completed
- skip_ineligible=True skips ineligible items; =False fails them
- Per-item state/reason_code details returned in the run response
- Run-items search filtering by state, reason_code, and dataset_id
- Error cases: missing snapshot (404), snapshot for wrong history (400)
- Collection (HDCA) preview: expansion, partial ineligibility
- Collection execution: all elements moved
- dataset_not_found: dataset purged between preview and execute
"""

import os
import string
from datetime import timedelta
from types import SimpleNamespace
from typing import (
    Any,
    cast,
    Optional,
)
from unittest.mock import patch
from uuid import uuid4

from galaxy.celery.tasks import (
    prune_expired_bulk_storage_operations,
    recover_stale_bulk_storage_operation_runs,
)
from galaxy.managers.dataset_storage_operations import (
    DatasetStorageOperationManager,
    StorageOperationRunExecutor,
)
from galaxy.managers.datasets import DatasetManager
from galaxy.model import (
    Dataset,
    DatasetStorageOperationRun,
    DatasetStorageOperationRunItem,
    DatasetStorageOperationSnapshot,
    HistoryDatasetAssociation,
    User,
)
from galaxy.model.orm.now import now
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.schema.storage_operations import StorageOperationRunState
from galaxy_test.base.decorators import requires_celery
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
)
from ._base import (
    BaseObjectStoreIntegrationTestCase,
    files_count,
)

DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE = string.Template("""
type: distributed
backends:
    - id: default
      type: disk
      weight: 1
      allow_selection: true
      device: tmp_disk
      files_dir: "${temp_directory}/files_default"
      extra_dirs:
      - type: temp
        path: "${temp_directory}/tmp_default"
      - type: job_work
        path: "${temp_directory}/job_working_directory_default"

    - id: other
      type: disk
      weight: 0
      allow_selection: true
      device: tmp_disk
      quota:
          source: other_quota
      files_dir: "${temp_directory}/files_default"
      extra_dirs:
      - type: temp
        path: "${temp_directory}/tmp_other"
      - type: job_work
        path: "${temp_directory}/job_working_directory_other"

    - id: separate_device
      type: disk
      weight: 0
      allow_selection: true
      device: other_disk
      files_dir: "${temp_directory}/files_separate"
      extra_dirs:
      - type: temp
        path: "${temp_directory}/tmp_separate"
      - type: job_work
        path: "${temp_directory}/job_working_directory_separate"

    - id: expirable_store
      type: disk
      weight: 0
      allow_selection: true
      device: tmp_disk
      object_expires_after_days: 30
      files_dir: "${temp_directory}/files_expirable"
      extra_dirs:
      - type: temp
        path: "${temp_directory}/tmp_expirable"
      - type: job_work
        path: "${temp_directory}/job_working_directory_expirable"

    - id: private_store
      type: disk
      weight: 0
      allow_selection: true
      private: true
      device: private_disk
      quota:
        source: private_quota
      files_dir: "${temp_directory}/files_private"
      extra_dirs:
      - type: temp
        path: "${temp_directory}/tmp_private"
      - type: job_work
        path: "${temp_directory}/job_working_directory_private"
""")

DEFAULT_OBJECT_STORE_ID = "default"
OTHER_OBJECT_STORE_ID = "other"
SEPARATE_DEVICE_OBJECT_STORE_ID = "separate_device"
EXPIRABLE_OBJECT_STORE_ID = "expirable_store"
PRIVATE_OBJECT_STORE_ID = "private_store"
FAILED_OR_SKIPPED_SEARCH = "state:failed state:skipped"
TARGET_EXPIRATION_IMMINENT_REASON_CODE = "target_expiration_imminent"
ALREADY_IN_TARGET_REASON_CODE = "already_in_target"
EXPIRABLE_TARGET_WARNING = "Datasets in the target storage expire based on their original creation date, so they may expire sooner than expected after moving. "
PRIVACY_DOWNGRADE_WARNING = (
    "Some selected datasets would move from private storage to shareable storage. "
    "After the operation, you will be able to share these datasets with other users."
)
NEAR_QUOTA_WARNING_PREFIX = "After this operation, the target storage will be at"


class TestBulkStorageOperationsIntegration(BaseObjectStoreIntegrationTestCase):
    dataset_populator: DatasetPopulator
    dataset_collection_populator: DatasetCollectionPopulator

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["new_user_dataset_access_role_default_private"] = True
        config["enable_quotas"] = True
        cls._configure_object_store(DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE, config, format="yml")

    def setUp(self):
        super().setUp()
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    # ------------------------------------------------------------------ helpers

    @property
    def _sa_session(self) -> galaxy_scoped_session:
        return cast(galaxy_scoped_session, self._app.model.session)

    def _decode_id(self, encoded_id: str) -> int:
        return self._app.security.decode_id(encoded_id)

    def _encode_id(self, decoded_id: int) -> str:
        return self._app.security.encode_id(decoded_id)

    def _get_required_user(self, user_id: int) -> User:
        user = self._sa_session.get(User, user_id)
        assert user is not None
        return user

    def _preview_move(
        self,
        history_id: str,
        target_object_store_id: str,
        items: list[dict[str, Any]],
        expected_status: int = 200,
    ) -> dict[str, Any]:
        return self.dataset_populator.bulk_storage_operation_preview(
            history_id,
            {
                "mode": "move",
                "target_object_store_id": target_object_store_id,
                "items": items,
            },
            expected_status=expected_status,
        )

    def _execute_snapshot(
        self,
        history_id: str,
        snapshot_id: str,
        skip_ineligible: bool = True,
        expected_status: int = 200,
    ) -> dict[str, Any]:
        return self.dataset_populator.bulk_storage_operation_execute(
            history_id,
            {
                "snapshot_id": snapshot_id,
                "execution_policy": {"skip_ineligible": skip_ineligible},
            },
            expected_status=expected_status,
        )

    def _run_move(
        self,
        history_id: str,
        target_object_store_id: str,
        items: list[dict[str, Any]],
        skip_ineligible: bool = True,
        include_items_on_terminal: bool = False,
        search: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        preview = self._preview_move(history_id, target_object_store_id, items)
        execute_result = self._execute_snapshot(
            history_id,
            preview["snapshot_id"],
            skip_ineligible=skip_ineligible,
        )
        run = execute_result["run"]
        final = self.dataset_populator.wait_for_bulk_storage_operation_run(
            history_id,
            run["run_id"],
            include_items_on_terminal=include_items_on_terminal,
            search=search,
        )
        return preview, run, final

    def _run_items(self, history_id: str, run_id: str, search: str | None = None) -> list[dict[str, Any]]:
        return self.dataset_populator.bulk_storage_operation_run_items(history_id, run_id, search=search)

    def _run_items_by_dataset_id(self, items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return {item["dataset_id"]: item for item in items}

    def _store_file_counts(self) -> tuple[int, int]:
        default_path = os.path.join(self.object_stores_parent, "files_default")
        separate_path = os.path.join(self.object_stores_parent, "files_separate")
        return files_count(default_path), files_count(separate_path)

    def _execute_snapshot_sync(
        self,
        sa_session: galaxy_scoped_session,
        snapshot: DatasetStorageOperationSnapshot,
        *,
        skip_ineligible: bool,
        force_checksum_mismatch: bool = False,
    ) -> str:
        storage_operation_manager = DatasetStorageOperationManager(self._app.object_store)
        dataset_manager = DatasetManager(self._app)
        user = self._get_required_user(snapshot.user_id)

        run, _ = storage_operation_manager.create_run_and_summary(
            sa_session=sa_session,
            snapshot=snapshot,
            skip_ineligible=skip_ineligible,
        )
        executor = storage_operation_manager.create_run_executor(
            sa_session=sa_session,
            dataset_manager=dataset_manager,
            app=self._app,
            run=run,
            user=user,
        )

        if force_checksum_mismatch:
            with patch.object(
                StorageOperationRunExecutor,
                "_sha256",
                autospec=True,
                side_effect=lambda _self, path: "source-hash" if "files_default" in path else "target-hash",
            ):
                executor.execute_run(snapshot)
        else:
            executor.execute_run(snapshot)

        return self._encode_id(run.id)

    def _item(self, hda_id: str) -> dict[str, Any]:
        return {"id": hda_id, "history_content_type": "dataset"}

    def _collection_item(self, hdca_id: str) -> dict[str, Any]:
        return {"id": hdca_id, "history_content_type": "dataset_collection"}

    def _new_list_collection(self, history_id: str, contents: list[str]) -> dict[str, Any]:
        fetch_response = self.dataset_collection_populator.create_list_in_history(
            history_id,
            contents=contents,
            wait=True,
        ).json()
        return self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)

    def _assert_eligibility(
        self,
        preview: dict[str, Any],
        *,
        eligible: int,
        ineligible: int,
    ) -> dict[str, Any]:
        """Assert eligibility counts and return the eligibility dict for further checks."""
        eligibility = preview["eligibility"]
        assert eligibility["eligible_count"] == eligible
        assert eligibility["ineligible_count"] == ineligible
        assert isinstance(eligibility["reasons"], list)
        return eligibility

    def _assert_eligibility_reason(
        self,
        eligibility: dict[str, Any],
        *,
        reason_code: str,
        count: int,
    ) -> None:
        """Assert that a specific reason code is present with the expected count."""
        for reason in eligibility["reasons"]:
            if reason["reason_code"] == reason_code:
                assert reason["count"] == count
                return
        raise AssertionError(f"Expected reason code '{reason_code}' not found in eligibility reasons.")

    def _assert_run_counts(
        self,
        run: dict[str, Any],
        *,
        succeeded: int,
        failed: int,
        skipped: int,
        total_bytes_processed: Optional[int] = None,
        state: str = "completed",
        mode: str = "move",
    ) -> None:
        assert run["state"] == state
        assert run["mode"] == mode
        assert run["succeeded_count"] == succeeded
        assert run["failed_count"] == failed
        assert run["skipped_count"] == skipped
        assert run["total_count"] == succeeded + failed + skipped
        if total_bytes_processed is not None:
            assert run["total_bytes_processed"] == total_bytes_processed

    def _assert_dataset_store_and_content(
        self,
        history_id: str,
        dataset_id: str,
        object_store_id: str,
        expected_content: str,
    ) -> None:
        dataset_details = self.dataset_populator.get_history_dataset_details(history_id, dataset_id=dataset_id)
        assert dataset_details["object_store_id"] == object_store_id
        assert self.dataset_populator.get_history_dataset_content(history_id, dataset_id=dataset_id) == expected_content

    def _new_dataset_in_store(self, history_id: str, content: str, object_store_id: str) -> dict[str, Any]:
        self.dataset_populator.update_history(history_id, {"preferred_object_store_id": object_store_id})
        dataset = self.dataset_populator.new_dataset(history_id, content=content, wait=True)
        dataset_details = self.dataset_populator.get_history_dataset_details(history_id, dataset_id=dataset["id"])
        assert dataset_details["object_store_id"] == object_store_id
        return dataset

    def _set_dataset_create_time_days_ago(self, hda_id: str, days_ago: int) -> None:
        """Simulate a dataset having been created many days ago (for expiration checks)."""
        hda = self._sa_session.get(HistoryDatasetAssociation, self._decode_id(hda_id))
        assert hda is not None
        dataset = hda.dataset
        assert dataset is not None
        dataset.create_time = now() - timedelta(days=days_ago)
        self._sa_session.add(dataset)
        self._sa_session.commit()

    def _dataset_total_size(self, hda_id: str) -> int:
        hda = self._sa_session.get(HistoryDatasetAssociation, self._decode_id(hda_id))
        assert hda is not None
        dataset = hda.dataset
        assert dataset is not None
        return int(dataset.get_total_size() or 0)

    def _quota_source_usage_for_current_user(self, quota_source_label: str) -> int:
        user_email = self.dataset_populator.user_email()
        user = self._sa_session.query(User).filter(User.email == user_email).one()
        usage = user.quota_source_usage_for(quota_source_label)
        return int(usage.disk_usage or 0) if usage else 0

    def _total_disk_usage_for_current_user(self) -> int:
        user_email = self.dataset_populator.user_email()
        user = self._sa_session.query(User).filter(User.email == user_email).one()
        return int(user.total_disk_usage or 0)

    def _expire_snapshot(self, snapshot_id: str) -> None:
        """Simulate snapshot expiration by setting expires_at to the past."""
        snapshot = self._sa_session.get(DatasetStorageOperationSnapshot, self._decode_id(snapshot_id))
        assert snapshot is not None
        snapshot.expires_at = now() - timedelta(minutes=1)
        self._sa_session.add(snapshot)
        self._sa_session.commit()

    def _age_run_past_retention(self, run_id: str, days: int = 31) -> None:
        """Simulate a run having aged past the retention window by setting update_time far in the past."""
        run = self._sa_session.get(DatasetStorageOperationRun, self._decode_id(run_id))
        assert run is not None
        run.update_time = now() - timedelta(days=days)
        self._sa_session.add(run)
        self._sa_session.commit()

    def _prune_expired_bulk_storage_operations(self) -> None:
        """Run the prune task against the real database."""
        prune_expired_bulk_storage_operations(self._sa_session, self._app.object_store)

    def _snapshot_has_been_pruned(self, snapshot_id: str) -> bool:
        """Check whether a snapshot has been pruned by attempting to retrieve it from the database."""
        snapshot = self._sa_session.get(DatasetStorageOperationSnapshot, self._decode_id(snapshot_id))
        return snapshot is None

    def _run_has_been_pruned(self, history_id: str, run_id: str) -> bool:
        """Check via the API whether a run has been pruned (returns 404 when gone)."""
        response = self.dataset_populator.bulk_storage_operation_run_status_raw(history_id, run_id, expected_status=404)
        return response.status_code == 404

    def _preview_and_execute_sync(
        self,
        history_id: str,
        target_object_store_id: str,
        items: list[dict[str, Any]],
        *,
        skip_ineligible: bool = True,
        force_checksum_mismatch: bool = False,
    ) -> tuple[dict[str, Any], str]:
        """Preview a move and execute the resulting snapshot synchronously.

        Returns (preview, encoded_run_id).
        """
        preview = self._preview_move(history_id, target_object_store_id, items)
        snapshot = self._sa_session.get(DatasetStorageOperationSnapshot, self._decode_id(preview["snapshot_id"]))
        assert snapshot is not None
        run_id = self._execute_snapshot_sync(
            self._sa_session,
            snapshot,
            skip_ineligible=skip_ineligible,
            force_checksum_mismatch=force_checksum_mismatch,
        )
        return preview, run_id

    def _unknown_encoded_id(self) -> str:
        return self._app.security.encode_id(999999999)

    # ------------------------------------------------------------------ preview tests

    def test_preview_eligible_dataset(self):
        """Preview classifies a dataset for a valid same-device move as eligible."""
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="test", wait=True)

            preview = self._preview_move(history_id, OTHER_OBJECT_STORE_ID, [self._item(hda["id"])])

            assert "snapshot_id" in preview
            assert "expires_at" in preview
            eligibility = self._assert_eligibility(preview, eligible=1, ineligible=0)
            assert eligibility["reasons"] == []
            assert preview["selection_counts"]["selected_items_count"] == 1
            assert preview["selection_counts"]["expanded_leaf_count"] == 1
            assert preview["selection_counts"]["unique_dataset_count"] == 1

    def test_preview_ineligible_already_in_target(self):
        """A dataset already in the target store is ineligible with reason already_in_target."""
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="test", wait=True)

            preview = self._preview_move(history_id, DEFAULT_OBJECT_STORE_ID, [self._item(hda["id"])])

            eligibility = self._assert_eligibility(preview, eligible=0, ineligible=1)
            self._assert_eligibility_reason(eligibility, reason_code=ALREADY_IN_TARGET_REASON_CODE, count=1)

    def test_preview_move_allows_cross_device(self):
        """Move mode should allow cross-device targets (copy-then-cutover strategy)."""
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="test", wait=True)

            preview = self._preview_move(history_id, SEPARATE_DEVICE_OBJECT_STORE_ID, [self._item(hda["id"])])

            self._assert_eligibility(preview, eligible=1, ineligible=0)
            assert preview["estimates"]["bytes_to_transfer"] > 0
            assert isinstance(preview["estimates"]["quota_delta_transfers"], list)
            assert preview["warnings"] == []

    def test_preview_reports_quota_delta_transfers_with_source_and_target_store_ids(self):
        with self.dataset_populator.test_history() as history_id:
            hda = self._new_dataset_in_store(history_id, "quota-transfer", PRIVATE_OBJECT_STORE_ID)

            preview = self._preview_move(history_id, OTHER_OBJECT_STORE_ID, [self._item(hda["id"])])

            transfers = preview["estimates"]["quota_delta_transfers"]
            assert isinstance(transfers, list)
            assert any(
                transfer["source_object_store_id"] == PRIVATE_OBJECT_STORE_ID
                and transfer["target_object_store_id"] == OTHER_OBJECT_STORE_ID
                and transfer["bytes"] > 0
                for transfer in transfers
            )

    def test_preview_marks_eligible_items_ineligible_when_target_quota_projection_fails(self):
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="quota-failure", wait=True)
            quota = self.dataset_populator.create_quota(
                {
                    "name": "bulk-storage-other-quota",
                    "description": "Small quota for bulk storage preview target quota coverage.",
                    "amount": "1 bytes",
                    "operation": "=",
                    "default": "no",
                    "in_users": [self.dataset_populator.user_email()],
                    "in_groups": [],
                    "quota_source_label": "other_quota",
                }
            )

            try:
                preview = self._preview_move(history_id, OTHER_OBJECT_STORE_ID, [self._item(hda["id"])])

                eligibility = self._assert_eligibility(preview, eligible=0, ineligible=1)
                self._assert_eligibility_reason(eligibility, reason_code="target_quota_exceeded", count=1)
            finally:
                self._delete(f"quotas/{quota['id']}", admin=True).raise_for_status()
                self._post(f"quotas/{quota['id']}/purge", data={"purge": "true"}, admin=True).raise_for_status()

    def test_preview_partial_quota_eligibility_greedy_allocation(self):
        with self.dataset_populator.test_history() as history_id:
            hdas = self.dataset_populator.fetch_hdas(
                history_id,
                [
                    {"src": "pasted", "paste_content": "quota-greedy", "ext": "txt", "name": "quota-greedy-1"},
                    {"src": "pasted", "paste_content": "quota-greedy", "ext": "txt", "name": "quota-greedy-2"},
                    {"src": "pasted", "paste_content": "quota-greedy", "ext": "txt", "name": "quota-greedy-3"},
                ],
                wait=True,
            )
            dataset_size = self._dataset_total_size(hdas[0]["id"])
            current_usage = self._quota_source_usage_for_current_user("other_quota")
            quota = self.dataset_populator.create_quota(
                {
                    "name": "bulk-storage-greedy-preview-quota",
                    "description": "Quota for greedy partial eligibility preview coverage.",
                    "amount": f"{current_usage + (dataset_size * 2) + 1} bytes",
                    "operation": "=",
                    "default": "no",
                    "in_users": [self.dataset_populator.user_email()],
                    "in_groups": [],
                    "quota_source_label": "other_quota",
                }
            )

            try:
                preview = self._preview_move(
                    history_id,
                    OTHER_OBJECT_STORE_ID,
                    [self._item(hda["id"]) for hda in hdas],
                )

                eligibility = self._assert_eligibility(preview, eligible=2, ineligible=1)
                self._assert_eligibility_reason(eligibility, reason_code="target_quota_exceeded", count=1)
            finally:
                self._delete(f"quotas/{quota['id']}", admin=True).raise_for_status()
                self._post(f"quotas/{quota['id']}/purge", data={"purge": "true"}, admin=True).raise_for_status()

    @requires_celery
    def test_execute_quota_enforcement_matches_preview(self):
        with self.dataset_populator.test_history() as history_id:
            hdas = self.dataset_populator.fetch_hdas(
                history_id,
                [
                    {"src": "pasted", "paste_content": "quota-execute", "ext": "txt", "name": "quota-execute-1"},
                    {"src": "pasted", "paste_content": "quota-execute", "ext": "txt", "name": "quota-execute-2"},
                    {"src": "pasted", "paste_content": "quota-execute", "ext": "txt", "name": "quota-execute-3"},
                ],
                wait=True,
            )
            dataset_size = self._dataset_total_size(hdas[0]["id"])
            current_usage = self._quota_source_usage_for_current_user("other_quota")
            quota = self.dataset_populator.create_quota(
                {
                    "name": "bulk-storage-greedy-execute-quota",
                    "description": "Quota for greedy execute consistency coverage.",
                    "amount": f"{current_usage + (dataset_size * 2) + 1} bytes",
                    "operation": "=",
                    "default": "no",
                    "in_users": [self.dataset_populator.user_email()],
                    "in_groups": [],
                    "quota_source_label": "other_quota",
                }
            )

            try:
                preview, _, final = self._run_move(
                    history_id,
                    OTHER_OBJECT_STORE_ID,
                    [self._item(hda["id"]) for hda in hdas],
                    skip_ineligible=True,
                )

                self._assert_eligibility(preview, eligible=2, ineligible=1)
                self._assert_run_counts(final["run"], succeeded=2, failed=0, skipped=1)
            finally:
                self._delete(f"quotas/{quota['id']}", admin=True).raise_for_status()
                self._post(f"quotas/{quota['id']}/purge", data={"purge": "true"}, admin=True).raise_for_status()

    def test_preview_near_quota_warning_when_approaching_limit(self):
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="near-quota", wait=True)
            dataset_size = self._dataset_total_size(hda["id"])
            current_usage = self._quota_source_usage_for_current_user("other_quota")
            quota = self.dataset_populator.create_quota(
                {
                    "name": "bulk-storage-near-quota-warning",
                    "description": "Quota for near-threshold warning coverage.",
                    "amount": f"{current_usage + dataset_size} bytes",
                    "operation": "=",
                    "default": "no",
                    "in_users": [self.dataset_populator.user_email()],
                    "in_groups": [],
                    "quota_source_label": "other_quota",
                }
            )

            try:
                preview = self._preview_move(history_id, OTHER_OBJECT_STORE_ID, [self._item(hda["id"])])

                assert any(NEAR_QUOTA_WARNING_PREFIX in warning for warning in preview["warnings"])
                assert preview["estimates"].get("quota_projection") is not None
            finally:
                self._delete(f"quotas/{quota['id']}", admin=True).raise_for_status()
                self._post(f"quotas/{quota['id']}/purge", data={"purge": "true"}, admin=True).raise_for_status()

    def test_preview_quota_projection_in_estimates(self):
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="projection-estimate", wait=True)
            dataset_size = self._dataset_total_size(hda["id"])
            current_usage = self._quota_source_usage_for_current_user("other_quota")
            quota_limit = current_usage + dataset_size + 123
            quota = self.dataset_populator.create_quota(
                {
                    "name": "bulk-storage-quota-projection-estimate",
                    "description": "Quota projection estimate coverage.",
                    "amount": f"{quota_limit} bytes",
                    "operation": "=",
                    "default": "no",
                    "in_users": [self.dataset_populator.user_email()],
                    "in_groups": [],
                    "quota_source_label": "other_quota",
                }
            )

            try:
                preview = self._preview_move(history_id, OTHER_OBJECT_STORE_ID, [self._item(hda["id"])])

                projection = preview["estimates"].get("quota_projection")
                assert projection is not None
                assert projection["projected_usage"] == current_usage + dataset_size
                assert projection["quota_limit"] == quota_limit
            finally:
                self._delete(f"quotas/{quota['id']}", admin=True).raise_for_status()
                self._post(f"quotas/{quota['id']}/purge", data={"purge": "true"}, admin=True).raise_for_status()

    def test_preview_marks_ineligible_when_target_default_quota_projection_fails(self):
        with self.dataset_populator.test_history() as history_id:
            hda = self._new_dataset_in_store(history_id, "default-target-quota", PRIVATE_OBJECT_STORE_ID)
            dataset_size = self._dataset_total_size(hda["id"])
            current_usage = self._total_disk_usage_for_current_user()
            quota = self.dataset_populator.create_quota(
                {
                    "name": "bulk-storage-default-target-quota",
                    "description": "Quota for default target source projection coverage.",
                    "amount": f"{current_usage + dataset_size - 1} bytes",
                    "operation": "=",
                    "default": "no",
                    "in_users": [self.dataset_populator.user_email()],
                    "in_groups": [],
                }
            )

            try:
                preview = self._preview_move(history_id, DEFAULT_OBJECT_STORE_ID, [self._item(hda["id"])])

                eligibility = self._assert_eligibility(preview, eligible=0, ineligible=1)
                self._assert_eligibility_reason(eligibility, reason_code="target_quota_exceeded", count=1)
            finally:
                self._delete(f"quotas/{quota['id']}", admin=True).raise_for_status()
                self._post(f"quotas/{quota['id']}/purge", data={"purge": "true"}, admin=True).raise_for_status()

    def test_preview_warns_on_private_to_shareable_move(self):
        with self.dataset_populator.test_history() as history_id:
            hda = self._new_dataset_in_store(history_id, "privacy-warning", PRIVATE_OBJECT_STORE_ID)

            preview = self._preview_move(history_id, OTHER_OBJECT_STORE_ID, [self._item(hda["id"])])

            self._assert_eligibility(preview, eligible=1, ineligible=0)
            assert PRIVACY_DOWNGRADE_WARNING in preview["warnings"]

    def test_preview_warns_when_target_store_is_expirable(self):
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="expirable-warning", wait=True)

            preview = self._preview_move(history_id, EXPIRABLE_OBJECT_STORE_ID, [self._item(hda["id"])])

            self._assert_eligibility(preview, eligible=1, ineligible=0)
            assert EXPIRABLE_TARGET_WARNING in preview["warnings"]

    def test_preview_ineligible_when_target_expiration_is_imminent(self):
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="expires-soon", wait=True)
            self._set_dataset_create_time_days_ago(hda["id"], days_ago=25)

            preview = self._preview_move(history_id, EXPIRABLE_OBJECT_STORE_ID, [self._item(hda["id"])])

            eligibility = self._assert_eligibility(preview, eligible=0, ineligible=1)
            self._assert_eligibility_reason(
                eligibility,
                reason_code=TARGET_EXPIRATION_IMMINENT_REASON_CODE,
                count=1,
            )

    def test_preview_eligible_when_target_expiration_threshold_not_crossed(self):
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="threshold-boundary", wait=True)
            self._set_dataset_create_time_days_ago(hda["id"], days_ago=19)

            preview = self._preview_move(history_id, EXPIRABLE_OBJECT_STORE_ID, [self._item(hda["id"])])

            eligibility = self._assert_eligibility(preview, eligible=1, ineligible=0)
            assert eligibility["reasons"] == []

    def test_preview_ineligible_invalid_target(self):
        """A non-existent target store returns invalid_target_object_store."""
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="test", wait=True)

            preview = self._preview_move(history_id, "does_not_exist", [self._item(hda["id"])])

            eligibility = self._assert_eligibility(preview, eligible=0, ineligible=1)
            self._assert_eligibility_reason(eligibility, reason_code="invalid_target_object_store", count=1)

    def test_preview_mixed_eligibility(self):
        """Preview handles a mix of eligible and ineligible items in one request."""
        with self.dataset_populator.test_history() as history_id:
            eligible_hda, ineligible_hda = self.dataset_populator.fetch_hdas(
                history_id,
                [
                    {"src": "pasted", "paste_content": "a", "ext": "txt", "name": "eligible-a"},
                    {"src": "pasted", "paste_content": "b", "ext": "txt", "name": "ineligible-b"},
                ],
                wait=True,
            )

            self._preview_move(
                history_id,
                OTHER_OBJECT_STORE_ID,
                [
                    self._item(eligible_hda["id"]),
                    self._item(ineligible_hda["id"]),
                ],
            )

            self.dataset_populator.update_object_store_id(ineligible_hda["id"], OTHER_OBJECT_STORE_ID)

            preview = self._preview_move(
                history_id,
                OTHER_OBJECT_STORE_ID,
                [
                    self._item(eligible_hda["id"]),
                    self._item(ineligible_hda["id"]),
                ],
            )

            eligibility = self._assert_eligibility(preview, eligible=1, ineligible=1)
            self._assert_eligibility_reason(eligibility, reason_code=ALREADY_IN_TARGET_REASON_CODE, count=1)

    # ------------------------------------------------------------------ execute / run lifecycle

    def test_execute_missing_snapshot_returns_404(self):
        """Execute with an unknown snapshot_id returns HTTP 404."""
        with self.dataset_populator.test_history() as history_id:
            self._execute_snapshot(history_id, self._unknown_encoded_id(), expected_status=404)

    def test_execute_snapshot_wrong_history_returns_400(self):
        """Execute with a snapshot belonging to a different history returns HTTP 400."""
        with self.dataset_populator.test_history() as h1_id:
            with self.dataset_populator.test_history() as h2_id:
                hda = self.dataset_populator.new_dataset(h1_id, content="test", wait=True)

                preview = self._preview_move(h1_id, OTHER_OBJECT_STORE_ID, [self._item(hda["id"])])

                self._execute_snapshot(h2_id, preview["snapshot_id"], expected_status=400)

    @requires_celery
    def test_run_lifecycle_pending_to_completed(self):
        """Full lifecycle: preview -> execute -> poll until completed with succeeded_count=1."""
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="data", wait=True)

            _, run, final = self._run_move(history_id, OTHER_OBJECT_STORE_ID, [self._item(hda["id"])])

            assert run["state"] in ("pending", "running", "completed")
            self._assert_run_counts(final["run"], succeeded=1, failed=0, skipped=0)
            self._assert_dataset_store_and_content(history_id, hda["id"], OTHER_OBJECT_STORE_ID, "data\n")

    @requires_celery
    def test_run_per_item_status_returned(self):
        """Run response includes per-item entries with state and reason_code."""
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="data", wait=True)

            _, _, final = self._run_move(
                history_id,
                OTHER_OBJECT_STORE_ID,
                [self._item(hda["id"])],
                include_items_on_terminal=True,
            )

            assert len(final["items"]) == 1
            item = final["items"][0]
            assert item["state"] == "succeeded"
            assert item["reason_code"] is None

    def test_sync_large_batch_uses_batched_progress_commits_and_notification_flushes(self):
        with self.dataset_populator.test_history() as history_id:
            # Keep this test fast while still exercising batched progress commits (>10 => interval 5).
            dataset_count = 15
            datasets = self.dataset_populator.fetch_hdas(
                history_id,
                [
                    {
                        "src": "pasted",
                        "paste_content": f"batch-{i}",
                        "ext": "txt",
                        "name": f"batch-{i}",
                    }
                    for i in range(dataset_count)
                ],
                wait=True,
            )
            items = [self._item(dataset["id"]) for dataset in datasets]

            preview = self._preview_move(history_id, OTHER_OBJECT_STORE_ID, items)
            snapshot = self._sa_session.get(DatasetStorageOperationSnapshot, self._decode_id(preview["snapshot_id"]))
            assert snapshot is not None

            storage_operation_manager = DatasetStorageOperationManager(self._app.object_store)
            dataset_manager = DatasetManager(self._app)
            user = self._get_required_user(snapshot.user_id)

            run, _ = storage_operation_manager.create_run_and_summary(
                sa_session=self._sa_session,
                snapshot=snapshot,
                skip_ineligible=False,
            )
            executor = storage_operation_manager.create_run_executor(
                sa_session=self._sa_session,
                dataset_manager=dataset_manager,
                app=self._app,
                run=run,
                user=user,
            )

            batch_sizes: list[int] = []
            original_flush = executor._flush_pending_dataset_updates

            def recording_flush():
                pending_count = len(executor._pending_dataset_update_ids)
                if pending_count:
                    batch_sizes.append(pending_count)
                return original_flush()

            with patch.object(executor, "_flush_pending_dataset_updates", side_effect=recording_flush):
                result = executor.execute_run(snapshot)

            assert result.state == StorageOperationRunState.completed
            assert run.succeeded_count == len(datasets)
            assert run.failed_count == 0
            assert run.skipped_count == 0
            assert batch_sizes
            assert max(batch_sizes) > 1
            assert len(batch_sizes) < len(datasets)
            assert sum(batch_sizes) == len(datasets)

    @requires_celery
    def test_move_mode_cross_device_completes_and_updates_source_store(self):
        """Move mode to a different device uses copy-then-cutover and updates dataset source store id."""
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="move-cross-device", wait=True)
            before = self.dataset_populator.get_history_dataset_details(history_id, dataset_id=hda["id"])
            assert before["object_store_id"] == DEFAULT_OBJECT_STORE_ID

            _, _, final = self._run_move(
                history_id,
                SEPARATE_DEVICE_OBJECT_STORE_ID,
                [self._item(hda["id"])],
                include_items_on_terminal=True,
            )

            self._assert_run_counts(final["run"], succeeded=1, failed=0, skipped=0)
            assert final["items"][0]["state"] == "succeeded"
            assert final["items"][0]["bytes_processed"] > 0
            assert final["run"]["total_bytes_processed"] > 0
            self._assert_dataset_store_and_content(
                history_id,
                hda["id"],
                SEPARATE_DEVICE_OBJECT_STORE_ID,
                "move-cross-device\n",
            )

    @requires_celery
    def test_successive_moves_keep_dataset_readable(self):
        """A dataset remains readable after moving across multiple stores in sequence."""
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="multi-hop", wait=True)

            _, _, first_final = self._run_move(history_id, OTHER_OBJECT_STORE_ID, [self._item(hda["id"])])
            self._assert_run_counts(first_final["run"], succeeded=1, failed=0, skipped=0)
            self._assert_dataset_store_and_content(history_id, hda["id"], OTHER_OBJECT_STORE_ID, "multi-hop\n")

            _, _, second_final = self._run_move(
                history_id,
                SEPARATE_DEVICE_OBJECT_STORE_ID,
                [self._item(hda["id"])],
            )
            self._assert_run_counts(second_final["run"], succeeded=1, failed=0, skipped=0)
            self._assert_dataset_store_and_content(
                history_id,
                hda["id"],
                SEPARATE_DEVICE_OBJECT_STORE_ID,
                "multi-hop\n",
            )

    @requires_celery
    def test_skip_ineligible_true_skips_not_fails(self):
        """With skip_ineligible=True an ineligible dataset is skipped, not failed."""
        with self.dataset_populator.test_history() as history_id:
            eligible, to_skip = self.dataset_populator.fetch_hdas(
                history_id,
                [
                    {"src": "pasted", "paste_content": "eligible", "ext": "txt", "name": "eligible"},
                    {"src": "pasted", "paste_content": "skip_me", "ext": "txt", "name": "skip-me"},
                ],
                wait=True,
            )

            self.dataset_populator.update_object_store_id(to_skip["id"], OTHER_OBJECT_STORE_ID)

            _, run, final = self._run_move(
                history_id,
                OTHER_OBJECT_STORE_ID,
                [self._item(eligible["id"]), self._item(to_skip["id"])],
                include_items_on_terminal=True,
                search=FAILED_OR_SKIPPED_SEARCH,
            )

            assert run["state"] in ("pending", "running", "completed")
            self._assert_run_counts(final["run"], succeeded=1, failed=0, skipped=1)
            assert len(final["items"]) == 1
            assert final["items"][0]["dataset_id"] == to_skip["id"]
            assert final["items"][0]["state"] == "skipped"
            assert final["items"][0]["reason_code"] == ALREADY_IN_TARGET_REASON_CODE

            filtered_items = self._run_items(
                history_id,
                run["run_id"],
                search=f"state:skipped dataset_id:{to_skip['id']} reason_code:{ALREADY_IN_TARGET_REASON_CODE}",
            )
            assert len(filtered_items) == 1
            assert filtered_items[0]["dataset_id"] == to_skip["id"]
            assert filtered_items[0]["state"] == "skipped"
            assert filtered_items[0]["reason_code"] == ALREADY_IN_TARGET_REASON_CODE

    @requires_celery
    def test_run_items_search_filters_by_reason_code(self):
        with self.dataset_populator.test_history() as history_id:
            eligible, ineligible = self.dataset_populator.fetch_hdas(
                history_id,
                [
                    {"src": "pasted", "paste_content": "eligible", "ext": "txt", "name": "eligible"},
                    {"src": "pasted", "paste_content": "ineligible", "ext": "txt", "name": "ineligible"},
                ],
                wait=True,
            )
            self.dataset_populator.update_object_store_id(ineligible["id"], OTHER_OBJECT_STORE_ID)

            _, run, final = self._run_move(
                history_id,
                OTHER_OBJECT_STORE_ID,
                [self._item(eligible["id"]), self._item(ineligible["id"])],
                include_items_on_terminal=True,
                search=FAILED_OR_SKIPPED_SEARCH,
            )

            self._assert_run_counts(final["run"], succeeded=1, failed=0, skipped=1)
            reason_filtered_items = self._run_items(
                history_id,
                run["run_id"],
                search="reason_code:already_in_target",
            )
            assert len(reason_filtered_items) == 1
            assert reason_filtered_items[0]["dataset_id"] == ineligible["id"]
            assert reason_filtered_items[0]["state"] == "skipped"
            assert reason_filtered_items[0]["reason_code"] == ALREADY_IN_TARGET_REASON_CODE

    @requires_celery
    def test_skip_ineligible_false_fails_ineligible_item(self):
        """With skip_ineligible=False an ineligible dataset produces a failed run item."""
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="data", wait=True)

            self.dataset_populator.update_object_store_id(hda["id"], OTHER_OBJECT_STORE_ID)

            _, _, final = self._run_move(
                history_id,
                OTHER_OBJECT_STORE_ID,
                [self._item(hda["id"])],
                skip_ineligible=False,
                include_items_on_terminal=True,
                search=FAILED_OR_SKIPPED_SEARCH,
            )

            self._assert_run_counts(final["run"], succeeded=0, failed=1, skipped=0)
            assert len(final["items"]) == 1
            assert final["items"][0]["state"] == "failed"
            assert final["items"][0]["reason_code"] == ALREADY_IN_TARGET_REASON_CODE

    @requires_celery
    def test_skip_ineligible_true_skips_target_expiration_imminent(self):
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="expirable-skip", wait=True)
            self._set_dataset_create_time_days_ago(hda["id"], days_ago=25)

            _, _, final = self._run_move(
                history_id,
                EXPIRABLE_OBJECT_STORE_ID,
                [self._item(hda["id"])],
                skip_ineligible=True,
                include_items_on_terminal=True,
                search=FAILED_OR_SKIPPED_SEARCH,
            )

            self._assert_run_counts(final["run"], succeeded=0, failed=0, skipped=1)
            assert len(final["items"]) == 1
            assert final["items"][0]["state"] == "skipped"
            assert final["items"][0]["reason_code"] == TARGET_EXPIRATION_IMMINENT_REASON_CODE

    @requires_celery
    def test_skip_ineligible_false_fails_target_expiration_imminent(self):
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="expirable-fail", wait=True)
            self._set_dataset_create_time_days_ago(hda["id"], days_ago=25)

            _, _, final = self._run_move(
                history_id,
                EXPIRABLE_OBJECT_STORE_ID,
                [self._item(hda["id"])],
                skip_ineligible=False,
                include_items_on_terminal=True,
                search=FAILED_OR_SKIPPED_SEARCH,
            )

            self._assert_run_counts(final["run"], succeeded=0, failed=1, skipped=0)
            assert len(final["items"]) == 1
            assert final["items"][0]["state"] == "failed"
            assert final["items"][0]["reason_code"] == TARGET_EXPIRATION_IMMINENT_REASON_CODE

    def test_get_run_unknown_id_returns_404(self):
        """GET on an unknown run_id returns HTTP 404."""
        with self.dataset_populator.test_history() as history_id:
            self.dataset_populator.bulk_storage_operation_run_status(
                history_id, self._unknown_encoded_id(), expected_status=404
            )

    # ------------------------------------------------------------------ collection (HDCA) tests

    def test_preview_collection_eligible(self):
        """Preview of a list collection expands elements and classifies them as eligible."""
        with self.dataset_populator.test_history() as history_id:
            hdca = self._new_list_collection(history_id, ["element1", "element2"])

            preview = self._preview_move(history_id, OTHER_OBJECT_STORE_ID, [self._collection_item(hdca["id"])])

            # Two elements means two leaf datasets, all eligible.
            eligibility = self._assert_eligibility(preview, eligible=2, ineligible=0)
            assert eligibility["reasons"] == []
            assert preview["selection_counts"]["selected_items_count"] == 1
            assert preview["selection_counts"]["expanded_leaf_count"] == 2
            assert preview["selection_counts"]["unique_dataset_count"] == 2

    def test_preview_collection_partially_ineligible(self):
        """Preview of a collection where one element is already in the target is partially ineligible."""
        with self.dataset_populator.test_history() as history_id:
            hdca = self._new_list_collection(history_id, ["elem-a", "elem-b"])

            # Move the first element to the target store so it becomes ineligible.
            first_hda_id = hdca["elements"][0]["object"]["id"]
            self.dataset_populator.update_object_store_id(first_hda_id, OTHER_OBJECT_STORE_ID)

            preview = self._preview_move(history_id, OTHER_OBJECT_STORE_ID, [self._collection_item(hdca["id"])])

            eligibility = self._assert_eligibility(preview, eligible=1, ineligible=1)
            self._assert_eligibility_reason(eligibility, reason_code=ALREADY_IN_TARGET_REASON_CODE, count=1)

    @requires_celery
    def test_run_collection_move_completes(self):
        """Executing a move for a list collection succeeds for all elements."""
        with self.dataset_populator.test_history() as history_id:
            hdca = self._new_list_collection(history_id, ["col-data-1", "col-data-2"])

            _, _, final = self._run_move(
                history_id,
                OTHER_OBJECT_STORE_ID,
                [self._collection_item(hdca["id"])],
                include_items_on_terminal=True,
            )

            self._assert_run_counts(final["run"], succeeded=2, failed=0, skipped=0)
            assert all(item["state"] == "succeeded" for item in final["items"])

            # Verify all element datasets moved to the target store.
            for element in hdca["elements"]:
                hda_id = element["object"]["id"]
                dataset_details = self.dataset_populator.get_history_dataset_details(history_id, dataset_id=hda_id)
                assert dataset_details["object_store_id"] == OTHER_OBJECT_STORE_ID

    # ------------------------------------------------------------------ dataset_not_found failure path

    @requires_celery
    def test_execute_dataset_purged_between_preview_and_execute(self):
        """A dataset purged after snapshot creation produces a failed run item with dataset_not_found."""
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="ephemeral", wait=True)

            preview = self._preview_move(history_id, OTHER_OBJECT_STORE_ID, [self._item(hda["id"])])

            # Purge the dataset so it no longer exists at execution time.
            self.dataset_populator.delete_dataset(history_id, hda["id"], purge=True, wait_for_purge=True)

            execute_result = self._execute_snapshot(
                history_id,
                preview["snapshot_id"],
                skip_ineligible=False,
            )
            run = execute_result["run"]
            final = self.dataset_populator.wait_for_bulk_storage_operation_run(
                history_id,
                run["run_id"],
                include_items_on_terminal=True,
                search=FAILED_OR_SKIPPED_SEARCH,
            )

            self._assert_run_counts(final["run"], succeeded=0, failed=1, skipped=0)
            assert len(final["items"]) == 1
            assert final["items"][0]["state"] == "failed"
            assert final["items"][0]["reason_code"] == "dataset_not_found"

    @requires_celery
    def test_idempotent_reexecution_mixed_state_no_data_mutation(self):
        """Re-executing the same snapshot is safe and does not duplicate cross-device files."""
        with self.dataset_populator.test_history() as history_id:
            to_move, becomes_ineligible, control = self.dataset_populator.fetch_hdas(
                history_id,
                [
                    {"src": "pasted", "paste_content": "to-move\n", "ext": "txt", "name": "to-move"},
                    {
                        "src": "pasted",
                        "paste_content": "becomes-ineligible\n",
                        "ext": "txt",
                        "name": "becomes-ineligible",
                    },
                    {"src": "pasted", "paste_content": "control\n", "ext": "txt", "name": "control"},
                ],
                wait=True,
            )

            preview = self._preview_move(
                history_id,
                SEPARATE_DEVICE_OBJECT_STORE_ID,
                [self._item(to_move["id"]), self._item(becomes_ineligible["id"])],
            )
            self._assert_eligibility(preview, eligible=2, ineligible=0)

            # Simulate state drift after preview using a real move operation.
            _, _, drift_final = self._run_move(
                history_id,
                SEPARATE_DEVICE_OBJECT_STORE_ID,
                [self._item(becomes_ineligible["id"])],
            )
            self._assert_run_counts(drift_final["run"], succeeded=1, failed=0, skipped=0)

            baseline_default_count, baseline_separate_count = self._store_file_counts()

            first_execute = self._execute_snapshot(history_id, preview["snapshot_id"], skip_ineligible=True)
            first_run = self.dataset_populator.wait_for_bulk_storage_operation_run(
                history_id,
                first_execute["run"]["run_id"],
                include_items_on_terminal=True,
            )
            self._assert_run_counts(first_run["run"], succeeded=1, failed=0, skipped=1)

            first_items_by_dataset = self._run_items_by_dataset_id(first_run["items"])
            assert first_items_by_dataset[to_move["id"]]["state"] == "succeeded"
            assert first_items_by_dataset[to_move["id"]]["reason_code"] is None
            assert first_items_by_dataset[becomes_ineligible["id"]]["state"] == "skipped"
            assert first_items_by_dataset[becomes_ineligible["id"]]["reason_code"] == ALREADY_IN_TARGET_REASON_CODE

            first_default_count, first_separate_count = self._store_file_counts()
            assert first_default_count == baseline_default_count - 1
            assert first_separate_count == baseline_separate_count + 1

            self._assert_dataset_store_and_content(
                history_id,
                to_move["id"],
                SEPARATE_DEVICE_OBJECT_STORE_ID,
                "to-move\n",
            )
            self._assert_dataset_store_and_content(
                history_id,
                becomes_ineligible["id"],
                SEPARATE_DEVICE_OBJECT_STORE_ID,
                "becomes-ineligible\n",
            )
            self._assert_dataset_store_and_content(history_id, control["id"], DEFAULT_OBJECT_STORE_ID, "control\n")

            second_execute = self._execute_snapshot(history_id, preview["snapshot_id"], skip_ineligible=True)
            second_run = self.dataset_populator.wait_for_bulk_storage_operation_run(
                history_id,
                second_execute["run"]["run_id"],
                include_items_on_terminal=True,
            )
            assert second_execute["run"]["run_id"] != first_execute["run"]["run_id"]
            self._assert_run_counts(second_run["run"], succeeded=0, failed=0, skipped=2)

            second_items_by_dataset = self._run_items_by_dataset_id(second_run["items"])
            assert second_items_by_dataset[to_move["id"]]["state"] == "skipped"
            assert second_items_by_dataset[to_move["id"]]["reason_code"] == ALREADY_IN_TARGET_REASON_CODE
            assert second_items_by_dataset[becomes_ineligible["id"]]["state"] == "skipped"
            assert second_items_by_dataset[becomes_ineligible["id"]]["reason_code"] == ALREADY_IN_TARGET_REASON_CODE

            second_default_count, second_separate_count = self._store_file_counts()
            assert second_default_count == first_default_count
            assert second_separate_count == first_separate_count

            self._assert_dataset_store_and_content(
                history_id,
                to_move["id"],
                SEPARATE_DEVICE_OBJECT_STORE_ID,
                "to-move\n",
            )
            self._assert_dataset_store_and_content(
                history_id,
                becomes_ineligible["id"],
                SEPARATE_DEVICE_OBJECT_STORE_ID,
                "becomes-ineligible\n",
            )
            self._assert_dataset_store_and_content(history_id, control["id"], DEFAULT_OBJECT_STORE_ID, "control\n")

    def test_cross_device_checksum_mismatch_is_safe_and_rerunnable(self):
        """Checksum mismatch fails safely (no data loss) and the same snapshot can be re-run successfully."""
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="checksum-guard", wait=True)

            preview = self._preview_move(
                history_id,
                SEPARATE_DEVICE_OBJECT_STORE_ID,
                [self._item(hda["id"])],
            )
            self._assert_eligibility(preview, eligible=1, ineligible=0)
            baseline_default_count, baseline_separate_count = self._store_file_counts()

            # Force checksum mismatch during execution to simulate corruption or other transfer failure.
            # This uses a synchronous execution of the snapshot to ensure the mismatch occurs in the first run
            # and allows re-running the same snapshot without needing to wait for a real async run to complete.
            sa_session = cast(galaxy_scoped_session, self._app.model.session)
            snapshot_id = self._app.security.decode_id(preview["snapshot_id"])
            snapshot = sa_session.get(DatasetStorageOperationSnapshot, snapshot_id)
            assert snapshot is not None
            first_run_id = self._execute_snapshot_sync(
                sa_session,
                snapshot,
                skip_ineligible=False,
                force_checksum_mismatch=True,
            )
            first_run_status = self.dataset_populator.bulk_storage_operation_run_status(history_id, first_run_id)
            self._assert_run_counts(first_run_status["run"], succeeded=0, failed=1, skipped=0)
            assert first_run_status["run"]["total_bytes_processed"] == 0

            first_run_items = self._run_items(history_id, first_run_id)
            assert len(first_run_items) == 1
            assert first_run_items[0]["dataset_id"] == hda["id"]
            assert first_run_items[0]["state"] == "failed"
            assert first_run_items[0]["reason_code"] == "checksum_verification_failed"

            # Failed transfer should rollback target writes (no leftover files).
            failed_default_count, failed_separate_count = self._store_file_counts()
            assert failed_default_count == baseline_default_count
            assert failed_separate_count == baseline_separate_count

            # Failure path must keep data readable from source store (no data loss).
            self._assert_dataset_store_and_content(
                history_id,
                hda["id"],
                DEFAULT_OBJECT_STORE_ID,
                "checksum-guard\n",
            )

            # Re-run same snapshot without forced corruption; move should now succeed.
            second_run_id = self._execute_snapshot_sync(sa_session, snapshot, skip_ineligible=False)
            second_run_status = self.dataset_populator.bulk_storage_operation_run_status(history_id, second_run_id)
            self._assert_run_counts(second_run_status["run"], succeeded=1, failed=0, skipped=0)
            assert second_run_status["run"]["total_bytes_processed"] > 0

            second_run_items = self._run_items(history_id, second_run_id)
            assert len(second_run_items) == 1
            assert second_run_items[0]["dataset_id"] == hda["id"]
            assert second_run_items[0]["state"] == "succeeded"
            assert second_run_items[0]["reason_code"] is None
            assert second_run_items[0]["bytes_processed"] > 0

            succeeded_default_count, succeeded_separate_count = self._store_file_counts()
            assert succeeded_default_count == baseline_default_count - 1
            assert succeeded_separate_count == baseline_separate_count + 1

            self._assert_dataset_store_and_content(
                history_id,
                hda["id"],
                SEPARATE_DEVICE_OBJECT_STORE_ID,
                "checksum-guard\n",
            )

    @requires_celery
    def test_recover_stale_run_requeues_and_resumes_remaining_datasets(self):
        with self.dataset_populator.test_history() as history_id:
            first, second = self.dataset_populator.fetch_hdas(
                history_id,
                [
                    {"src": "pasted", "paste_content": "first\n", "ext": "txt", "name": "first"},
                    {"src": "pasted", "paste_content": "second\n", "ext": "txt", "name": "second"},
                ],
                wait=True,
            )

            preview = self._preview_move(
                history_id,
                SEPARATE_DEVICE_OBJECT_STORE_ID,
                [self._item(first["id"]), self._item(second["id"])],
            )

            sa_session = cast(galaxy_scoped_session, self._app.model.session)
            snapshot_id = self._app.security.decode_id(preview["snapshot_id"])
            snapshot = sa_session.get(DatasetStorageOperationSnapshot, snapshot_id)
            assert snapshot is not None

            storage_operation_manager = DatasetStorageOperationManager(self._app.object_store)
            dataset_manager = DatasetManager(self._app)
            user = self._get_required_user(snapshot.user_id)
            assert user is not None

            run, _ = storage_operation_manager.create_run_and_summary(
                sa_session=sa_session,
                snapshot=snapshot,
                skip_ineligible=False,
                notify_on_completion=False,
            )
            run.task_id = uuid4()
            sa_session.add(run)
            sa_session.commit()

            crashed_dataset_id = snapshot.resolved_dataset_ids[1]
            original_execute_dataset_transfer = StorageOperationRunExecutor._execute_dataset_transfer

            def crash_during_second_dataset(executor_self, dataset, dataset_id, quota_delta):
                if dataset_id == crashed_dataset_id:
                    executor_self._mark_run_item_running(dataset_id)
                    raise RuntimeError("simulated worker death")
                return original_execute_dataset_transfer(executor_self, dataset, dataset_id, quota_delta)

            with self.assertRaisesRegex(RuntimeError, "simulated worker death"):
                with patch.object(
                    StorageOperationRunExecutor,
                    "_execute_dataset_transfer",
                    autospec=True,
                    side_effect=crash_during_second_dataset,
                ):
                    executor = storage_operation_manager.create_run_executor(
                        sa_session=sa_session,
                        dataset_manager=dataset_manager,
                        app=self._app,
                        run=run,
                        user=user,
                    )
                    executor.execute_run(snapshot)

            sa_session.expire_all()
            reloaded_run = cast(DatasetStorageOperationRun, sa_session.get(DatasetStorageOperationRun, run.id))
            assert reloaded_run is not None
            assert reloaded_run.state == StorageOperationRunState.running.value
            reloaded_run.update_time = now() - timedelta(minutes=10)
            sa_session.add(reloaded_run)
            sa_session.commit()

            run_items = (
                sa_session.query(DatasetStorageOperationRunItem)
                .filter(DatasetStorageOperationRunItem.run_id == reloaded_run.id)
                .order_by(DatasetStorageOperationRunItem.dataset_id)
                .all()
            )
            assert len(run_items) == 2
            assert run_items[0].state == "succeeded"
            assert run_items[1].state == "running"

            recovered_task_result = SimpleNamespace(id=str(uuid4()))
            inspect_response = SimpleNamespace(active=lambda: {})
            with patch("galaxy.celery.tasks.celery_app.control.inspect", return_value=inspect_response):
                with patch("galaxy.celery.tasks.bulk_move_storage.delay", return_value=recovered_task_result) as delay:
                    recover_stale_bulk_storage_operation_runs(sa_session, stale_threshold_minutes=0)

            sa_session.expire_all()
            recovered_run = cast(
                DatasetStorageOperationRun,
                sa_session.get(DatasetStorageOperationRun, reloaded_run.id),
            )
            assert recovered_run is not None
            assert recovered_run.state == StorageOperationRunState.pending.value
            assert str(recovered_run.task_id) == recovered_task_result.id
            delay.assert_called_once_with(run_db_id=recovered_run.id, task_user_id=user.id, notify_on_completion=False)

            snapshot = sa_session.get(DatasetStorageOperationSnapshot, snapshot.id)
            assert snapshot is not None
            executor = storage_operation_manager.create_run_executor(
                sa_session=sa_session,
                dataset_manager=dataset_manager,
                app=self._app,
                run=recovered_run,
                user=user,
                current_task_id=recovered_task_result.id,
            )
            result = executor.execute_run(snapshot)
            assert result.state == StorageOperationRunState.completed

            encoded_run_id = self._app.security.encode_id(recovered_run.id)
            final = self.dataset_populator.bulk_storage_operation_run_status(history_id, encoded_run_id)
            self._assert_run_counts(final["run"], succeeded=2, failed=0, skipped=0)

            items = self._run_items(history_id, encoded_run_id)
            assert len(items) == 2
            assert all(item["state"] == "succeeded" for item in items)

            item_count = (
                sa_session.query(DatasetStorageOperationRunItem)
                .filter(DatasetStorageOperationRunItem.run_id == recovered_run.id)
                .count()
            )
            assert item_count == 2

            self._assert_dataset_store_and_content(
                history_id,
                first["id"],
                SEPARATE_DEVICE_OBJECT_STORE_ID,
                "first\n",
            )
            self._assert_dataset_store_and_content(
                history_id,
                second["id"],
                SEPARATE_DEVICE_OBJECT_STORE_ID,
                "second\n",
            )

    @requires_celery
    def test_recover_stale_run_finalizes_completed_move_without_committed_db_update(self):
        with self.dataset_populator.test_history() as history_id:
            new_hda = self.dataset_populator.new_dataset(history_id, content="late-commit", wait=True)

            preview = self._preview_move(
                history_id,
                SEPARATE_DEVICE_OBJECT_STORE_ID,
                [self._item(new_hda["id"])],
            )

            sa_session = cast(galaxy_scoped_session, self._app.model.session)
            snapshot_id = self._app.security.decode_id(preview["snapshot_id"])
            snapshot = sa_session.get(DatasetStorageOperationSnapshot, snapshot_id)
            assert snapshot is not None

            storage_operation_manager = DatasetStorageOperationManager(self._app.object_store)
            dataset_manager = DatasetManager(self._app)
            user = self._get_required_user(snapshot.user_id)

            run, _ = storage_operation_manager.create_run_and_summary(
                sa_session=sa_session,
                snapshot=snapshot,
                skip_ineligible=False,
            )
            run.task_id = uuid4()
            run.state = StorageOperationRunState.running.value
            sa_session.add(run)
            sa_session.commit()

            executor = storage_operation_manager.create_run_executor(
                sa_session=sa_session,
                dataset_manager=dataset_manager,
                app=self._app,
                run=run,
                user=user,
            )

            hda = sa_session.get(HistoryDatasetAssociation, self._app.security.decode_id(new_hda["id"]))
            assert hda is not None
            dataset = hda.dataset
            assert dataset is not None

            source_proxy = executor._dataset_proxy(dataset, str(dataset.object_store_id))
            target_proxy = executor._dataset_proxy(dataset, SEPARATE_DEVICE_OBJECT_STORE_ID)
            executor._mark_run_item_running(dataset.id)
            executor._copy_dataset_to_target_store(
                dataset, str(dataset.object_store_id), SEPARATE_DEVICE_OBJECT_STORE_ID
            )
            executor._verify_copied_dataset_integrity(
                dataset, str(dataset.object_store_id), SEPARATE_DEVICE_OBJECT_STORE_ID
            )
            executor._cleanup_source_dataset_data(source_proxy, dataset.extra_files_path_name)
            sa_session.expire_all()

            reloaded_run = cast(DatasetStorageOperationRun, sa_session.get(DatasetStorageOperationRun, run.id))
            assert reloaded_run is not None
            reloaded_run.update_time = now() - timedelta(minutes=10)
            sa_session.add(reloaded_run)
            sa_session.commit()

            dataset = sa_session.get(Dataset, dataset.id)
            assert dataset is not None
            assert dataset.object_store_id == DEFAULT_OBJECT_STORE_ID
            assert not self._app.object_store.exists(source_proxy)
            assert self._app.object_store.exists(target_proxy)

            recovered_task_result = SimpleNamespace(id=str(uuid4()))
            inspect_response = SimpleNamespace(active=lambda: {})
            with patch("galaxy.celery.tasks.celery_app.control.inspect", return_value=inspect_response):
                with patch("galaxy.celery.tasks.bulk_move_storage.delay", return_value=recovered_task_result):
                    recover_stale_bulk_storage_operation_runs(sa_session, stale_threshold_minutes=0)

            sa_session.expire_all()
            recovered_run = cast(DatasetStorageOperationRun, sa_session.get(DatasetStorageOperationRun, run.id))
            assert recovered_run is not None
            snapshot = sa_session.get(DatasetStorageOperationSnapshot, snapshot.id)
            assert snapshot is not None
            executor = storage_operation_manager.create_run_executor(
                sa_session=sa_session,
                dataset_manager=dataset_manager,
                app=self._app,
                run=recovered_run,
                user=user,
                current_task_id=recovered_task_result.id,
            )
            result = executor.execute_run(snapshot)
            assert result.state == StorageOperationRunState.completed

            encoded_run_id = self._app.security.encode_id(recovered_run.id)
            final = self.dataset_populator.bulk_storage_operation_run_status(history_id, encoded_run_id)
            self._assert_run_counts(final["run"], succeeded=1, failed=0, skipped=0)

            items = self._run_items(history_id, encoded_run_id)
            assert len(items) == 1
            assert items[0]["state"] == "succeeded"

            dataset_details = self.dataset_populator.get_history_dataset_details(history_id, dataset_id=new_hda["id"])
            assert dataset_details["object_store_id"] == SEPARATE_DEVICE_OBJECT_STORE_ID
            self._assert_dataset_store_and_content(
                history_id,
                new_hda["id"],
                SEPARATE_DEVICE_OBJECT_STORE_ID,
                "late-commit\n",
            )

    def test_recovery_handles_crash_after_source_cleanup(self):
        """Verify safe recovery when worker crashes after source files are deleted but before DB update.

        Exercises the reconciliation path: source missing + target present + DB shows old store
        + run_item in "running" state → finalize and succeed.
        """
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="crash-recovery\n", wait=True)

            preview = self._preview_move(history_id, SEPARATE_DEVICE_OBJECT_STORE_ID, [self._item(hda["id"])])
            self._assert_eligibility(preview, eligible=1, ineligible=0)

            sa_session = self._sa_session
            snapshot = sa_session.get(DatasetStorageOperationSnapshot, self._decode_id(preview["snapshot_id"]))
            assert snapshot is not None

            storage_operation_manager = DatasetStorageOperationManager(self._app.object_store)
            dataset_manager = DatasetManager(self._app)
            user = self._get_required_user(snapshot.user_id)
            assert user is not None

            run, _ = storage_operation_manager.create_run_and_summary(
                sa_session=sa_session,
                snapshot=snapshot,
                skip_ineligible=False,
            )

            hda_obj = sa_session.get(HistoryDatasetAssociation, self._decode_id(hda["id"]))
            assert hda_obj is not None
            dataset = hda_obj.dataset
            assert dataset is not None
            original_store = str(dataset.object_store_id)

            # Use a temporary executor to set up the crash state via file operations only:
            # copy data to target, delete from source — intentionally skipping
            # _finalize_cross_device_move so the DB still shows the old store.
            executor = storage_operation_manager.create_run_executor(
                sa_session=sa_session,
                dataset_manager=dataset_manager,
                app=self._app,
                run=run,
                user=user,
            )
            source_proxy = executor._dataset_proxy(dataset, original_store)
            target_proxy = executor._dataset_proxy(dataset, SEPARATE_DEVICE_OBJECT_STORE_ID)
            executor._copy_dataset_to_target_store(dataset, original_store, SEPARATE_DEVICE_OBJECT_STORE_ID)
            executor._cleanup_source_dataset_data(source_proxy, dataset.extra_files_path_name)

            assert not self._app.object_store.exists(source_proxy)
            assert self._app.object_store.exists(target_proxy)
            assert dataset.object_store_id == original_store  # DB still shows old store

            # Simulate a run_item left in "running" state by the crashed worker.
            sa_session.add(
                DatasetStorageOperationRunItem(
                    run_id=run.id,
                    dataset_id=dataset.id,
                    state="running",
                    reason_code=None,
                    bytes_processed=0,
                )
            )
            sa_session.commit()

            # Recovery: a new executor should detect source-missing + target-present and finalize.
            executor_recovered = storage_operation_manager.create_run_executor(
                sa_session=sa_session,
                dataset_manager=dataset_manager,
                app=self._app,
                run=run,
                user=user,
            )
            result = executor_recovered.execute_run(snapshot)

            assert result.state == StorageOperationRunState.completed
            self._assert_dataset_store_and_content(
                history_id,
                hda["id"],
                SEPARATE_DEVICE_OBJECT_STORE_ID,
                "crash-recovery\n",
            )

    def test_prune_expired_unused_snapshot(self):
        with self.dataset_populator.test_history() as history_id:
            dataset = self.dataset_populator.new_dataset(history_id, content="test", wait=False, fetch_data=False)
            preview = self._preview_move(history_id, OTHER_OBJECT_STORE_ID, [self._item(dataset["id"])])

            self._expire_snapshot(preview["snapshot_id"])

            self._prune_expired_bulk_storage_operations()
            assert self._snapshot_has_been_pruned(preview["snapshot_id"])

    def test_prune_expired_snapshot_with_completed_run_keeps_run_related_data(self):
        with self.dataset_populator.test_history() as history_id:
            dataset = self.dataset_populator.new_dataset(history_id, content="test", wait=False, fetch_data=False)
            preview, run_id = self._preview_and_execute_sync(
                history_id, DEFAULT_OBJECT_STORE_ID, [self._item(dataset["id"])], skip_ineligible=True
            )

            run_status = self.dataset_populator.bulk_storage_operation_run_status(history_id, run_id)
            assert run_status["run"]["state"] == "completed"
            original_item_count = len(self._run_items(history_id, run_id))
            assert original_item_count > 0

            self._expire_snapshot(preview["snapshot_id"])
            self._prune_expired_bulk_storage_operations()

            # Expired snapshot will not be pruned since it has an associated run
            assert not self._snapshot_has_been_pruned(preview["snapshot_id"])
            run_status_after_prune = self.dataset_populator.bulk_storage_operation_run_status(history_id, run_id)
            assert run_status_after_prune["run"]["state"] == "completed"
            assert len(self._run_items(history_id, run_id)) == original_item_count

    def test_prune_completed_runs_older_than_retention_also_prunes_expired_snapshots(self):
        with self.dataset_populator.test_history() as history_id:
            dataset = self.dataset_populator.new_dataset(history_id, content="test", wait=False, fetch_data=False)
            preview, run_id = self._preview_and_execute_sync(
                history_id, DEFAULT_OBJECT_STORE_ID, [self._item(dataset["id"])], skip_ineligible=True
            )

            run_status = self.dataset_populator.bulk_storage_operation_run_status(history_id, run_id)
            assert run_status["run"]["state"] == "completed"
            assert len(self._run_items(history_id, run_id)) > 0

            self._expire_snapshot(preview["snapshot_id"])
            self._age_run_past_retention(run_id)

            self._prune_expired_bulk_storage_operations()
            assert self._snapshot_has_been_pruned(preview["snapshot_id"])
            assert self._run_has_been_pruned(history_id, run_id)
