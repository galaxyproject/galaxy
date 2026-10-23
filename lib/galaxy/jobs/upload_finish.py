"""Opt-in transactional completion receipts for standard upload and fetch jobs.

The caller serializes completion for one job, preserves an immutable metadata
store and execution token, and retries interruptions with a fresh SQL session.
Only standard upload/fetch jobs without completion hooks or external publication
are supported. Runners must explicitly adopt this context; ordinary Galaxy
finish/import behavior is unchanged.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from sqlalchemy import (
    inspect,
    select,
)
from sqlalchemy.exc import IntegrityError

from galaxy import model
from galaxy.model import store
from galaxy.tool_util.output_checker import DETECTED_JOB_STATE
from galaxy.tools import Tool

RECEIPT_KEY = "upload_finish_recovery"
RECEIPT_VERSION = 1


class UploadFinishError(RuntimeError):
    """A permanent protocol/identity error; retain files for investigation."""


class UploadFinishCancelled(UploadFinishError):
    """Cancellation won the race with an uncommitted finish phase."""


def validate_upload(wrapper):
    """Reject unsupported side effects before an eligible command is started."""
    tool = wrapper.tool
    job = wrapper.get_job()
    if job.tool_id not in {"upload1", "__DATA_FETCH__"} or getattr(tool, "id", None) != job.tool_id:
        raise UploadFinishError("Upload completion recovery supports only the standard upload and fetch tools")
    after_process = getattr(tool, "exec_after_process", None)
    if getattr(after_process, "__func__", after_process) is not Tool.exec_after_process:
        raise UploadFinishError("Upload completion recovery does not support custom completion methods")
    if tool.get_hook("exec_after_process") is not None:
        raise UploadFinishError("Upload completion recovery does not support completion code hooks")
    if job.post_job_actions:
        raise UploadFinishError("Upload completion recovery does not support post-job actions")
    if wrapper.app.config.enable_celery_tasks:
        raise UploadFinishError("Upload completion recovery does not support external Celery publication")
    if not wrapper.external_output_metadata.extended:
        raise UploadFinishError("Upload completion recovery requires extended metadata")


def manifest_digest(directory):
    """Hash the frozen model-store files, including their relative filenames."""
    directory = Path(directory)
    required = (store.ATTRS_FILENAME_EXPORT, store.ATTRS_FILENAME_DATASETS, store.ATTRS_FILENAME_JOBS)
    if not directory.is_dir() or any(not (directory / name).is_file() for name in required):
        raise UploadFinishError("The completed upload metadata store is missing")
    if (directory / store.TRACEBACK).exists():
        raise UploadFinishError("The upload metadata store contains a traceback")
    for name in (
        store.ATTRS_FILENAME_EXPORT,
        store.ATTRS_FILENAME_DATASETS,
        store.ATTRS_FILENAME_JOBS,
        store.ATTRS_FILENAME_COLLECTIONS,
        store.ATTRS_FILENAME_LIBRARIES,
        store.ATTRS_FILENAME_LIBRARY_FOLDERS,
        store.ATTRS_FILENAME_HISTORY,
        store.ATTRS_FILENAME_INVOCATIONS,
        store.ATTRS_FILENAME_IMPLICIT_COLLECTION_JOBS,
        store.ATTRS_FILENAME_CONVERSIONS,
    ):
        path = directory / name
        if not path.exists():
            continue
        try:
            contents = json.loads(path.read_text())
        except (ValueError, UnicodeError) as error:
            raise UploadFinishError("The frozen upload metadata store contains invalid JSON") from error
        expected_type = dict if name in (store.ATTRS_FILENAME_EXPORT, store.ATTRS_FILENAME_HISTORY) else list
        if not isinstance(contents, expected_type) or (
            isinstance(contents, list) and any(not isinstance(item, dict) for item in contents)
        ):
            raise UploadFinishError("The frozen upload metadata store contains invalid object attributes")
    digest = hashlib.sha256()
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise UploadFinishError("The frozen upload metadata store must not contain symlinks")
        if not path.is_file():
            continue
        name = str(path.relative_to(directory)).encode("utf-8")
        digest.update(len(name).to_bytes(8, "big"))
        digest.update(name)
        digest.update(path.stat().st_size.to_bytes(8, "big"))
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


class UploadFinishContext:
    """Resume upload database completion from committed phase receipts.

    The runner must serialize completion for this job, preserve its execution
    token and metadata store, and recreate the context with a fresh SQL session
    after an interruption. This context does not arrange retries or process
    recovery on its own.
    """

    enabled = True

    def __init__(self, wrapper, execution_token):
        if not isinstance(execution_token, str) or not execution_token:
            raise UploadFinishError("A stable upload execution token is required")
        self.wrapper = wrapper
        self.job = wrapper.get_job()
        self.session = wrapper.sa_session
        self.execution_token = execution_token
        self.directory = Path(wrapper.working_directory) / "metadata" / "outputs_populated"
        self.receipt = {}
        self.already_finalized = False
        self.detected_state = None

    def _identity(self):
        job = self.job
        return {
            "job_id": job.id,
            "user_id": job.user_id,
            "history_id": job.history_id,
            "tool_id": job.tool_id,
            "tool_version": job.tool_version,
        }

    def begin(self):
        validate_upload(self.wrapper)
        self.session.refresh(self.job)
        identity = self._identity()
        if identity["job_id"] is None:
            raise UploadFinishError("The upload job has not been persisted")
        receipt = (self.job.destination_params or {}).get(RECEIPT_KEY)
        if receipt is not None:
            if (
                not isinstance(receipt, dict)
                or receipt.get("version") != RECEIPT_VERSION
                or receipt.get("execution_token") != self.execution_token
                or receipt.get("identity") != identity
                or not isinstance(receipt.get("manifest_sha256"), str)
                or not isinstance(receipt.get("imported"), dict)
                or not isinstance(receipt["imported"].get("ids"), dict)
                or not isinstance(receipt["imported"].get("job_states"), dict)
            ):
                raise UploadFinishError("The upload finish receipt does not match this execution")
            self.receipt = copy.deepcopy(receipt)
            for phase in ("postprocessed", "finalized"):
                if phase in receipt and (
                    not isinstance(receipt[phase], dict)
                    or receipt[phase].get("final_state") not in (model.Job.states.OK, model.Job.states.ERROR)
                ):
                    raise UploadFinishError("The upload finish receipt has an invalid final state")
            self._validate_receipt()
            self.detected_state = DETECTED_JOB_STATE(receipt["imported"]["detected_state"])
        if self.job.state in model.Job.terminal_states:
            finalized = self.receipt.get("finalized", {})
            if (
                not self.receipt.get("postprocessed")
                or finalized.get("final_state") != self.job.state
                or self.receipt["postprocessed"].get("final_state") != self.job.state
            ):
                raise UploadFinishError("The terminal upload job has no matching finish receipt")
            self.already_finalized = True
            return
        digest = manifest_digest(self.directory)
        if receipt is not None and receipt["manifest_sha256"] != digest:
            raise UploadFinishError("The frozen upload metadata changed after its import")
        if receipt is None:
            self.receipt = {
                "version": RECEIPT_VERSION,
                "execution_token": self.execution_token,
                "identity": identity,
                "manifest_sha256": digest,
            }
        if self.receipt.get("postprocessed") and not self.receipt.get("imported"):
            raise UploadFinishError("The upload finish receipt has inconsistent phases")
        if self.receipt.get("imported"):
            self._verify_identities()
            phase = self.receipt.get("postprocessed") or self.receipt["imported"]
            self.job.job_messages = copy.deepcopy(phase["job_messages"])

    def _validate_receipt(self):
        imported = self.receipt["imported"]
        identities = imported["ids"]
        mappings = (
            "hdas_by_key",
            "hdas_by_id",
            "lddas_by_key",
            "hdcas_by_key",
            "hdcas_by_id",
            "dces_by_key",
            "dces_by_id",
            "datasets_by_uuid",
            "collections_by_id",
        )
        for name in mappings:
            mapping = identities.get(name)
            if not isinstance(mapping, dict) or any(type(value) is not int or value <= 0 for value in mapping.values()):
                raise UploadFinishError("The upload finish receipt has an invalid object mapping")
        try:
            valid_raw_hda_keys = all(
                type(key) is str and str(int(key)) == key and int(key) > 0 for key in identities["hdas_by_id"]
            )
        except (TypeError, ValueError):
            valid_raw_hda_keys = False
        if not valid_raw_hda_keys:
            raise UploadFinishError("The upload finish receipt has an invalid raw HDA identity")
        for name in ("output_datasets", "output_library_datasets", "output_collections"):
            edges = identities.get(name)
            if not isinstance(edges, list) or any(
                not isinstance(edge, list)
                or len(edge) != 2
                or not isinstance(edge[0], str)
                or type(edge[1]) is not int
                or edge[1] <= 0
                for edge in edges
            ):
                raise UploadFinishError("The upload finish receipt has invalid output associations")
        try:
            DETECTED_JOB_STATE(imported["detected_state"])
            valid_states = all(
                self._matches_job_id(key) and state in (model.Job.states.OK, model.Job.states.ERROR)
                for key, state in imported["job_states"].items()
            )
        except (KeyError, ValueError, TypeError):
            valid_states = False
        if not valid_states:
            raise UploadFinishError("The upload finish receipt has invalid tool states")
        for phase in (imported, self.receipt.get("postprocessed", {})):
            if phase and not isinstance(phase.get("job_messages"), list):
                raise UploadFinishError("The upload finish receipt has invalid job messages")
        if "finalized" in self.receipt and (
            not self.receipt.get("postprocessed")
            or self.receipt["finalized"].get("final_state") != self.receipt["postprocessed"].get("final_state")
        ):
            raise UploadFinishError("The upload finish receipt has inconsistent final phases")

    @property
    def imported(self):
        return bool(self.receipt.get("imported"))

    @property
    def postprocessed(self):
        return bool(self.receipt.get("postprocessed"))

    @property
    def final_job_state(self):
        return self.receipt["postprocessed"]["final_state"]

    def _verify_manifest(self):
        if manifest_digest(self.directory) != self.receipt["manifest_sha256"]:
            raise UploadFinishError("The frozen upload metadata changed during finish")

    def import_outputs(self, importer):
        if self.receipt.get("imported"):
            tracker = store.ObjectImportTracker()
            identities = self.receipt["imported"]["ids"]
            # Native finish applies default permissions to imported HDAs after
            # the import phase commits. Restore both mappings so a crash at
            # that boundary cannot leave recovered outputs without permissions.
            tracker.hdas_by_key = {
                key: self.session.get(model.HistoryDatasetAssociation, object_id)
                for key, object_id in identities["hdas_by_key"].items()
            }
            tracker.hdas_by_id = {
                int(key): self.session.get(model.HistoryDatasetAssociation, object_id)
                for key, object_id in identities["hdas_by_id"].items()
            }
            tracker.job_states_by_id = {
                int(key): state for key, state in self.receipt["imported"].get("job_states", {}).items()
            }
            return tracker
        if importer.import_options.commit:
            raise UploadFinishError("The upload import must leave transaction ownership with its finish context")
        if (
            importer.defines_new_history()
            or importer.invocations_properties()
            or list(importer.workflow_paths())
            or importer.implicit_collection_jobs_properties()
        ):
            raise UploadFinishError("The upload metadata store contains unsupported model objects")
        jobs = importer.jobs_properties()
        if any(not self._matches_job_id(attributes.get("id")) for attributes in jobs):
            raise UploadFinishError("The upload metadata store contains an unrelated job")
        self._verify_manifest()
        try:
            self._lock_current_job()
            self._validate_import_identities(importer)
            tracker = importer.perform_import(history=self.job.history, job=self.job)
            # Native extended metadata may serialize a raw ID as a decimal
            # string. Keep the frozen store intact and expose canonical IDs to
            # the finish path, including its metadata-error state lookup.
            tracker.job_states_by_id = {int(key): state for key, state in tracker.job_states_by_id.items()}
            self._deduplicate_job_associations()
            self.session.flush()
            self.receipt["imported"] = {
                "ids": self._identity_map(tracker),
                "job_states": {str(key): state for key, state in tracker.job_states_by_id.items()},
                "detected_state": self.detected_state
                or (
                    DETECTED_JOB_STATE.GENERIC_ERROR
                    if tracker.job_states_by_id.get(self.job.id) == model.Job.states.ERROR
                    else DETECTED_JOB_STATE.OK
                ),
                "job_messages": copy.deepcopy(self.job.job_messages or []),
            }
            self._verify_identities()
            self._commit()
            return tracker
        except (AssertionError, KeyError, ValueError, TypeError, store.MalformedContents, IntegrityError) as error:
            self._rollback()
            raise UploadFinishError("The upload metadata store could not be imported safely") from error
        except BaseException:
            self._rollback()
            raise

    def _matches_job_id(self, identifier):
        return (type(identifier) is int and identifier == self.job.id) or (
            type(identifier) is str and identifier == str(self.job.id)
        )

    def _validate_import_identities(self, importer):
        # Extended metadata may edit existing output placeholders. Reject a
        # stale raw identity before the importer changes its files or objects.
        library_ids = {
            association.ldda_id for association in self.job.input_library_datasets + self.job.output_library_datasets
        }
        for attributes in importer.datasets_properties():
            if attributes.get("model_class", "HistoryDatasetAssociation") not in {
                "HistoryDatasetAssociation",
                "LibraryDatasetDatasetAssociation",
            }:
                raise UploadFinishError("The upload metadata store contains an unsupported dataset type")
            if "id" not in attributes:
                continue
            if attributes.get("model_class") == "HistoryDatasetAssociation":
                instance = self.session.get(model.HistoryDatasetAssociation, attributes["id"])
                valid = instance is not None and instance.history_id == self.job.history_id
            elif attributes.get("model_class") == "LibraryDatasetDatasetAssociation":
                instance = self.session.get(model.LibraryDatasetDatasetAssociation, attributes["id"])
                valid = instance is not None and instance.id in library_ids
            else:
                instance, valid = None, False
            if not valid:
                raise UploadFinishError("An existing upload output does not belong to this job")
            dataset = attributes.get("dataset", {})
            if ("id" in dataset and dataset["id"] != instance.dataset.id) or (
                "uuid" in dataset and str(dataset["uuid"]) != str(instance.dataset.uuid)
            ):
                raise UploadFinishError("An existing upload dataset identity changed")
        allowed_collections = set()

        def allow_collection(collection):
            allowed_collections.add(collection.id)
            for element in collection.elements:
                if element.child_collection is not None:
                    allow_collection(element.child_collection)

        for association in self.job.input_dataset_collections:
            allow_collection(association.dataset_collection.collection)
        for association in self.job.output_dataset_collection_instances:
            allow_collection(association.dataset_collection_instance.collection)
        for association in self.job.output_dataset_collections:
            allow_collection(association.dataset_collection)
        collections = importer.collections_properties()
        for attributes in collections:
            if "collection" in attributes and "id" in attributes:
                instance = self.session.get(model.HistoryDatasetCollectionAssociation, attributes["id"])
                collection = attributes["collection"]
                if (
                    instance is None
                    or instance.history_id != self.job.history_id
                    or ("id" in collection and collection["id"] != instance.collection_id)
                ):
                    raise UploadFinishError("An existing upload collection identity changed")
                allow_collection(instance.collection)

        def validate_collection(attributes):
            if "id" in attributes and attributes["id"] not in allowed_collections:
                raise UploadFinishError("An existing upload child collection identity changed")
            for element in attributes.get("elements", []):
                if "child_collection" in element:
                    validate_collection(element["child_collection"])

        for attributes in collections:
            validate_collection(attributes.get("collection", attributes))

    def _deduplicate_job_associations(self):
        # The native importer appends connections for the edited job, including
        # connections that were already created when an upload was submitted.
        # Keep one instance per actual IO edge only in this opt-in path.
        for relationship, target in (
            ("input_datasets", "dataset_id"),
            ("output_datasets", "dataset_id"),
            ("input_dataset_collections", "dataset_collection_id"),
            ("output_dataset_collection_instances", "dataset_collection_id"),
        ):
            seen = set()
            associations = getattr(self.job, relationship)
            for association in list(associations):
                key = (association.name, getattr(association, target))
                if key not in seen:
                    seen.add(key)
                    continue
                associations.remove(association)
                if inspect(association).persistent:
                    self.session.delete(association)
                elif inspect(association).pending:
                    self.session.expunge(association)

    def _identity_map(self, tracker):
        result = {}
        for name in (
            "hdas_by_key",
            "hdas_by_id",
            "lddas_by_key",
            "hdcas_by_key",
            "hdcas_by_id",
            "dces_by_key",
            "dces_by_id",
        ):
            result[name] = {str(key): item.id for key, item in getattr(tracker, name).items()}
        datasets = {}
        instances = [association.dataset for association in self.job.output_datasets + self.job.output_library_datasets]
        for name in ("hdas_by_key", "hdas_by_id", "lddas_by_key"):
            instances.extend(getattr(tracker, name).values())
        for instance in instances:
            dataset = instance.dataset
            datasets[str(dataset.uuid)] = dataset.id
        result["datasets_by_uuid"] = datasets
        collections = {}

        def record_collection(collection):
            collections[str(collection.id)] = collection.id
            for element in collection.elements:
                if element.child_collection is not None:
                    record_collection(element.child_collection)

        for name in ("hdcas_by_key", "hdcas_by_id"):
            for instance in getattr(tracker, name).values():
                record_collection(instance.collection)
        result["collections_by_id"] = collections
        result["output_datasets"] = sorted(
            [[association.name, association.dataset_id] for association in self.job.output_datasets]
        )
        result["output_library_datasets"] = sorted(
            [[association.name, association.ldda_id] for association in self.job.output_library_datasets]
        )
        result["output_collections"] = sorted(
            [
                [association.name, association.dataset_collection_id]
                for association in self.job.output_dataset_collection_instances
            ]
        )
        return result

    def _verify_identities(self):
        identities = self.receipt["imported"].get("ids", {})
        for name, model_class in (
            ("hdas_by_key", model.HistoryDatasetAssociation),
            ("hdas_by_id", model.HistoryDatasetAssociation),
            ("lddas_by_key", model.LibraryDatasetDatasetAssociation),
            ("hdcas_by_key", model.HistoryDatasetCollectionAssociation),
            ("hdcas_by_id", model.HistoryDatasetCollectionAssociation),
            ("dces_by_key", model.DatasetCollectionElement),
            ("dces_by_id", model.DatasetCollectionElement),
            ("collections_by_id", model.DatasetCollection),
        ):
            for object_id in identities.get(name, {}).values():
                item = self.session.get(model_class, object_id)
                if item is None or (
                    isinstance(item, (model.HistoryDatasetAssociation, model.HistoryDatasetCollectionAssociation))
                    and item.history_id != self.job.history_id
                ):
                    raise UploadFinishError("An imported upload output identity no longer matches")
        for dataset_uuid, dataset_id in identities.get("datasets_by_uuid", {}).items():
            dataset = self.session.get(model.Dataset, dataset_id)
            if dataset is None or str(dataset.uuid) != dataset_uuid:
                raise UploadFinishError("An imported upload dataset identity no longer matches")
        actual_datasets = sorted(
            [[association.name, association.dataset_id] for association in self.job.output_datasets]
        )
        actual_libraries = sorted(
            [[association.name, association.ldda_id] for association in self.job.output_library_datasets]
        )
        actual_collections = sorted(
            [
                [association.name, association.dataset_collection_id]
                for association in self.job.output_dataset_collection_instances
            ]
        )
        if (
            identities.get("output_datasets") != actual_datasets
            or identities.get("output_library_datasets") != actual_libraries
            or identities.get("output_collections") != actual_collections
        ):
            raise UploadFinishError("The imported upload output associations changed")

    def prepare_postprocessing(self):
        self._lock_current_job()

    def prepare_finalization(self):
        # set_final_state and lazy relationship reads may flush. Acquire this
        # phase's lock before either can overwrite a concurrent cancellation.
        self._lock_current_job()

    def commit_postprocessed(self, final_job_state):
        if not self.receipt.get("imported") or self.postprocessed:
            raise UploadFinishError("The upload postprocessing phase is not ready")
        self.receipt["postprocessed"] = {
            "final_state": final_job_state,
            "job_messages": copy.deepcopy(self.job.job_messages or []),
        }
        self._commit()

    def commit_finalized(self, final_job_state):
        if not self.postprocessed or final_job_state != self.final_job_state:
            raise UploadFinishError("The upload final state does not match postprocessing")
        self.receipt["finalized"] = {"final_state": final_job_state}
        self._commit()

    def _commit(self):
        try:
            self._lock_current_job()
            self._verify_manifest()
            parameters = copy.deepcopy(self.job.destination_params or {})
            parameters[RECEIPT_KEY] = copy.deepcopy(self.receipt)
            self.job.destination_params = parameters
            self.session.commit()
        except BaseException:
            self._rollback()
            raise

    def _lock_current_job(self):
        # Lock only this phase, not across the native split between quota/user
        # changes and workflow/final-state updates. Never flush a pending OK
        # before reading a concurrent cancellation from the database.
        with self.session.no_autoflush:
            state = self.session.execute(
                select(model.Job.state).where(model.Job.id == self.job.id).with_for_update()
            ).scalar_one()
        if state in {
            model.Job.states.DELETING,
            model.Job.states.DELETED,
            model.Job.states.STOPPING,
            model.Job.states.STOPPED,
            model.Job.states.ERROR,
        }:
            self._rollback()
            raise UploadFinishCancelled("The upload was cancelled while its outputs were being finalized")

    def _rollback(self):
        try:
            self.session.rollback()
        except Exception:
            # A connection error after COMMIT was accepted can leave the
            # Session unusable. The runner discards it and reads a fresh receipt.
            pass
