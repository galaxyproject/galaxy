import datetime
import json
import shutil
from concurrent.futures import TimeoutError
from functools import lru_cache
from pathlib import Path
from typing import (
    Any,
    Callable,
    Optional,
)

from sqlalchemy import (
    exists,
    select,
)

from galaxy import model
from galaxy.celery import (
    celery_app,
    galaxy_task,
)
from galaxy.config import GalaxyAppConfiguration
from galaxy.datatypes import sniff
from galaxy.datatypes.registry import Registry as DatatypesRegistry
from galaxy.exceptions import ObjectNotFound
from galaxy.jobs import MinimalJobWrapper
from galaxy.managers.collections import DatasetCollectionManager
from galaxy.managers.datasets import (
    DatasetAssociationManager,
    DatasetManager,
)
from galaxy.managers.hdas import HDAManager
from galaxy.managers.lddas import LDDAManager
from galaxy.managers.markdown_util import generate_branded_pdf
from galaxy.managers.model_stores import ModelStoreManager
from galaxy.managers.notification import NotificationManager
from galaxy.managers.tool_data import ToolDataImportManager
from galaxy.metadata.set_metadata import set_metadata_portable
from galaxy.model import (
    Job,
    User,
)
from galaxy.model.base import transaction
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.objectstore import BaseObjectStore
from galaxy.objectstore.caching import check_caches
from galaxy.queue_worker import GalaxyQueueWorker
from galaxy.schema.notifications import NotificationCreateRequest
from galaxy.schema.tasks import (
    ComputeDatasetHashTaskRequest,
    GenerateHistoryContentDownload,
    GenerateHistoryDownload,
    GenerateInvocationDownload,
    GeneratePdfDownload,
    ImportModelStoreTaskRequest,
    MaterializeDatasetInstanceTaskRequest,
    PrepareDatasetCollectionDownload,
    PurgeDatasetsTaskRequest,
    SetupHistoryExportJob,
    WriteHistoryContentTo,
    WriteHistoryTo,
    WriteInvocationTo,
)
from galaxy.short_term_storage import ShortTermStorageMonitor
from galaxy.structured_app import MinimalManagerApp
from galaxy.tools import create_tool_from_representation
from galaxy.tools.data_fetch import do_fetch
from galaxy.util import galaxy_directory
from galaxy.util.custom_logging import get_logger

log = get_logger(__name__)


@lru_cache
def setup_data_table_manager(app):
    app._configure_tool_data_tables(from_shed_config=False)


@lru_cache
def cached_create_tool_from_representation(app: MinimalManagerApp, raw_tool_source: str):
    return create_tool_from_representation(app=app, raw_tool_source=raw_tool_source, tool_source_class="XmlToolSource")


@galaxy_task(action="recalculate a user's disk usage")
def recalculate_user_disk_usage(
    session: galaxy_scoped_session, object_store: BaseObjectStore, task_user_id: Optional[int] = None
):
    if task_user_id:
        user = session.get(User, task_user_id)
        if user:
            user.calculate_and_set_disk_usage(object_store)
        else:
            log.error(f"Recalculate user disk usage task failed, user {task_user_id} not found")
    else:
        log.error("Recalculate user disk usage task received without user_id.")


@galaxy_task(ignore_result=True, action="purge a history dataset")
def purge_hda(hda_manager: HDAManager, hda_id: int, task_user_id: Optional[int] = None):
    hda = hda_manager.by_id(hda_id)
    hda_manager._purge(hda)


@galaxy_task(ignore_result=True, action="completely removes a set of datasets from the object_store")
def purge_datasets(
    dataset_manager: DatasetManager, request: PurgeDatasetsTaskRequest, task_user_id: Optional[int] = None
):
    dataset_manager.purge_datasets(request)


@galaxy_task(ignore_result=True, action="materializing dataset instance")
def materialize(
    hda_manager: HDAManager,
    request: MaterializeDatasetInstanceTaskRequest,
    task_user_id: Optional[int] = None,
):
    """Materialize datasets using HDAManager."""
    hda_manager.materialize(request)


@galaxy_task(action="set metadata for job")
def set_job_metadata(
    tool_job_working_directory,
    extended_metadata_collection: bool,
    job_id: int,
    sa_session: galaxy_scoped_session,
    task_user_id: Optional[int] = None,
) -> None:
    return abort_when_job_stops(
        set_metadata_portable,
        session=sa_session,
        job_id=job_id,
        tool_job_working_directory=tool_job_working_directory,
        extended_metadata_collection=extended_metadata_collection,
    )


@galaxy_task(action="set or detect dataset datatype and updates metadata")
def change_datatype(
    hda_manager: HDAManager,
    ldda_manager: LDDAManager,
    datatypes_registry: DatatypesRegistry,
    sa_session: galaxy_scoped_session,
    dataset_id: int,
    datatype: str,
    model_class: str = "HistoryDatasetAssociation",
    task_user_id: Optional[int] = None,
):
    manager = _get_dataset_manager(hda_manager, ldda_manager, model_class)
    dataset_instance = manager.by_id(dataset_id)
    can_change_datatype = manager.ensure_can_change_datatype(dataset_instance, raiseException=False)
    if not can_change_datatype:
        log.info(f"Changing datatype is not allowed for {model_class} {dataset_instance.id}")
        return
    if datatype == "auto":
        path = dataset_instance.dataset.get_file_name()
        datatype = sniff.guess_ext(path, datatypes_registry.sniff_order)
    datatypes_registry.change_datatype(dataset_instance, datatype)
    with transaction(sa_session):
        sa_session.commit()
    set_metadata(hda_manager, ldda_manager, sa_session, dataset_id, model_class)


@galaxy_task(action="touch update_time of object")
def touch(
    sa_session: galaxy_scoped_session,
    item_id: int,
    model_class: str = "HistoryDatasetCollectionAssociation",
    task_user_id: Optional[int] = None,
):
    if model_class != "HistoryDatasetCollectionAssociation":
        raise NotImplementedError(f"touch method not implemented for '{model_class}'")
    stmt = select(model.HistoryDatasetCollectionAssociation).filter_by(id=item_id)
    item = sa_session.execute(stmt).scalar_one()
    item.touch()
    with transaction(sa_session):
        sa_session.commit()


@galaxy_task(action="set dataset association metadata")
def set_metadata(
    hda_manager: HDAManager,
    ldda_manager: LDDAManager,
    sa_session: galaxy_scoped_session,
    dataset_id: int,
    model_class: str = "HistoryDatasetAssociation",
    overwrite: bool = True,
    ensure_can_set_metadata: bool = True,
    task_user_id: Optional[int] = None,
):
    """
    ensure_can_set_metadata can be bypassed for new outputs.
    """
    manager = _get_dataset_manager(hda_manager, ldda_manager, model_class)
    dataset_instance = manager.by_id(dataset_id)
    if ensure_can_set_metadata:
        can_set_metadata = manager.ensure_can_set_metadata(dataset_instance, raiseException=False)
        if not can_set_metadata:
            log.info(f"Setting metadata is not allowed for {model_class} {dataset_instance.id}")
            return
    try:
        if overwrite:
            hda_manager.overwrite_metadata(dataset_instance)
        dataset_instance.datatype.set_meta(dataset_instance)  # type:ignore [arg-type]
        dataset_instance.set_peek()
        # Reset SETTING_METADATA state so the dataset instance getter picks the dataset state
        dataset_instance.set_metadata_success_state()
    except Exception as e:
        log.info(f"Setting metadata failed on {model_class} {dataset_instance.id}: {str(e)}")
        dataset_instance.state = dataset_instance.states.FAILED_METADATA
    with transaction(sa_session):
        sa_session.commit()


def _get_dataset_manager(
    hda_manager: HDAManager, ldda_manager: LDDAManager, model_class: str = "HistoryDatasetAssociation"
) -> DatasetAssociationManager:
    if model_class == "HistoryDatasetAssociation":
        return hda_manager
    elif model_class == "LibraryDatasetDatasetAssociation":
        return ldda_manager
    else:
        raise NotImplementedError(f"Cannot find manager for model_class {model_class}")


@galaxy_task(bind=True)
def setup_fetch_data(
    self,
    job_id: int,
    raw_tool_source: str,
    app: MinimalManagerApp,
    sa_session: galaxy_scoped_session,
    task_user_id: Optional[int] = None,
):
    tool = cached_create_tool_from_representation(app=app, raw_tool_source=raw_tool_source)
    job = sa_session.get(Job, job_id)
    assert job
    # self.request.hostname is the actual worker name given by the `-n` argument, not the hostname as you might think.
    job.handler = self.request.hostname
    job.job_runner_name = "celery"
    # TODO: assert state
    mini_job_wrapper = MinimalJobWrapper(job=job, app=app, tool=tool)
    mini_job_wrapper.change_state(model.Job.states.QUEUED, flush=False, job=job)
    # Set object store after job destination so can leverage parameters...
    mini_job_wrapper._set_object_store_ids(job)
    request_json = Path(mini_job_wrapper.working_directory) / "request.json"
    request_json_value = next(iter(p.value for p in job.parameters if p.name == "request_json"))
    request_json.write_text(json.loads(request_json_value))
    mini_job_wrapper.setup_external_metadata(
        output_fnames=mini_job_wrapper.job_io.get_output_fnames(),
        set_extension=True,
        tmp_dir=mini_job_wrapper.working_directory,
        # We don't want to overwrite metadata that was copied over in init_meta(), as per established behavior
        kwds={"overwrite": False},
    )
    mini_job_wrapper.prepare()
    return mini_job_wrapper.working_directory, str(request_json), mini_job_wrapper.job_io.file_sources_dict


@galaxy_task
def finish_job(
    job_id: int,
    raw_tool_source: str,
    app: MinimalManagerApp,
    sa_session: galaxy_scoped_session,
    task_user_id: Optional[int] = None,
):
    tool = cached_create_tool_from_representation(app=app, raw_tool_source=raw_tool_source)
    job = sa_session.get(Job, job_id)
    assert job
    # TODO: assert state ?
    mini_job_wrapper = MinimalJobWrapper(job=job, app=app, tool=tool)
    mini_job_wrapper.finish("", "")


def is_aborted(session: galaxy_scoped_session, job_id: int):
    return session.execute(
        select(
            exists(model.Job.state).where(
                model.Job.id == job_id,
                model.Job.state.in_([model.Job.states.DELETED, model.Job.states.DELETING]),
            )
        )
    ).scalar()


def abort_when_job_stops(function: Callable, session: galaxy_scoped_session, job_id: int, **kwargs) -> Any:
    if not is_aborted(session, job_id):
        future = celery_app.fork_pool.submit(
            function,
            timeout=None,
            **kwargs,
        )
        while True:
            try:
                return future.result(timeout=1)
            except TimeoutError:
                if is_aborted(session, job_id):
                    future.cancel()
                    return


def _fetch_data(setup_return):
    tool_job_working_directory, request_path, file_sources_dict = setup_return
    working_directory = Path(tool_job_working_directory) / "working"
    datatypes_registry = DatatypesRegistry()
    datatypes_registry.load_datatypes(
        galaxy_directory(),
        config=Path(tool_job_working_directory) / "metadata" / "registry.xml",
        use_build_sites=False,
        use_converters=False,
        use_display_applications=False,
    )
    do_fetch(
        request_path=request_path,
        working_directory=str(working_directory),
        registry=datatypes_registry,
        file_sources_dict=file_sources_dict,
    )
    return tool_job_working_directory


@galaxy_task(action="Run fetch_data")
def fetch_data(
    setup_return,
    job_id: int,
    app: MinimalManagerApp,
    sa_session: galaxy_scoped_session,
    task_user_id: Optional[int] = None,
) -> str:
    job = sa_session.get(Job, job_id)
    assert job
    mini_job_wrapper = MinimalJobWrapper(job=job, app=app)
    mini_job_wrapper.change_state(model.Job.states.RUNNING, flush=True, job=job)
    return abort_when_job_stops(_fetch_data, session=sa_session, job_id=job_id, setup_return=setup_return)


@galaxy_task(ignore_result=True, action="setting up export history job")
def export_history(
    model_store_manager: ModelStoreManager,
    request: SetupHistoryExportJob,
    task_user_id: Optional[int] = None,
):
    model_store_manager.setup_history_export_job(request)


@galaxy_task(action="preparing compressed file for collection download")
def prepare_dataset_collection_download(
    request: PrepareDatasetCollectionDownload,
    collection_manager: DatasetCollectionManager,
    task_user_id: Optional[int] = None,
):
    """Create a short term storage file tracked and available for download of target collection."""
    collection_manager.write_dataset_collection(request)


@galaxy_task(action="preparing Galaxy Markdown PDF for download")
def prepare_pdf_download(
    request: GeneratePdfDownload,
    config: GalaxyAppConfiguration,
    short_term_storage_monitor: ShortTermStorageMonitor,
    task_user_id: Optional[int] = None,
):
    """Create a short term storage file tracked and available for download of target PDF for Galaxy Markdown."""
    generate_branded_pdf(request, config, short_term_storage_monitor)


@galaxy_task(action="generate and stage a history model store for download")
def prepare_history_download(
    model_store_manager: ModelStoreManager,
    request: GenerateHistoryDownload,
    task_user_id: Optional[int] = None,
):
    model_store_manager.prepare_history_download(request)


@galaxy_task(action="generate and stage a history content model store for download")
def prepare_history_content_download(
    model_store_manager: ModelStoreManager,
    request: GenerateHistoryContentDownload,
    task_user_id: Optional[int] = None,
):
    model_store_manager.prepare_history_content_download(request)


@galaxy_task(action="generate and stage a workflow invocation store for download")
def prepare_invocation_download(
    model_store_manager: ModelStoreManager,
    request: GenerateInvocationDownload,
    task_user_id: Optional[int] = None,
):
    model_store_manager.prepare_invocation_download(request)


@galaxy_task(action="generate and stage a workflow invocation store to file source URI")
def write_invocation_to(
    model_store_manager: ModelStoreManager,
    request: WriteInvocationTo,
    task_user_id: Optional[int] = None,
):
    model_store_manager.write_invocation_to(request)


@galaxy_task(action="generate and stage a history store to file source URI")
def write_history_to(
    model_store_manager: ModelStoreManager,
    request: WriteHistoryTo,
    task_user_id: Optional[int] = None,
):
    model_store_manager.write_history_to(request)


@galaxy_task(action="generate and stage a history content model store to file source URI")
def write_history_content_to(
    model_store_manager: ModelStoreManager,
    request: WriteHistoryContentTo,
    task_user_id: Optional[int] = None,
):
    model_store_manager.write_history_content_to(request)


@galaxy_task(action="import objects from a target model store")
def import_model_store(
    model_store_manager: ModelStoreManager,
    request: ImportModelStoreTaskRequest,
    task_user_id: Optional[int] = None,
):
    model_store_manager.import_model_store(request)


@galaxy_task(action="compute dataset hash and store in database")
def compute_dataset_hash(
    dataset_manager: DatasetManager,
    request: ComputeDatasetHashTaskRequest,
    task_user_id: Optional[int] = None,
):
    dataset_manager.compute_hash(request)


@galaxy_task(action="import a data bundle")
def import_data_bundle(
    app: MinimalManagerApp,
    hda_manager: HDAManager,
    ldda_manager: LDDAManager,
    tool_data_import_manager: ToolDataImportManager,
    config: GalaxyAppConfiguration,
    src: str,
    uri: Optional[str] = None,
    id: Optional[int] = None,
    tool_data_file_path: Optional[str] = None,
    task_user_id: Optional[int] = None,
):
    setup_data_table_manager(app)
    if src == "uri":
        assert uri
        tool_data_import_manager.import_data_bundle_by_uri(config, uri, tool_data_file_path=tool_data_file_path)
    else:
        assert id
        dataset: model.DatasetInstance
        if src == "hda":
            dataset = hda_manager.by_id(id)
        else:
            dataset = ldda_manager.by_id(id)
        tool_data_import_manager.import_data_bundle_by_dataset(config, dataset, tool_data_file_path=tool_data_file_path)
    queue_worker = GalaxyQueueWorker(app)
    queue_worker.send_control_task("reload_tool_data_tables")


@galaxy_task(action="pruning history audit table")
def prune_history_audit_table(sa_session: galaxy_scoped_session):
    """Prune ever growing history_audit table."""
    model.HistoryAudit.prune(sa_session)


@galaxy_task(action="clean up short term storage")
def cleanup_short_term_storage(storage_monitor: ShortTermStorageMonitor):
    """Cleanup short term storage."""
    storage_monitor.cleanup()


@galaxy_task(action="clean up expired notifications")
def cleanup_expired_notifications(notification_manager: NotificationManager):
    """Cleanup expired notifications."""
    result = notification_manager.cleanup_expired_notifications()
    log.info(
        f"Successfully deleted {result.deleted_notifications_count} notifications and {result.deleted_associations_count} associations."
    )


@galaxy_task(action="prune object store cache directories")
def clean_object_store_caches(object_store: BaseObjectStore):
    check_caches(object_store.cache_targets())


@galaxy_task(action="send notifications to all recipients")
def send_notification_to_recipients_async(
    request: NotificationCreateRequest, notification_manager: NotificationManager
):
    """Send a notification to a list of users."""
    _, notifications_sent = notification_manager.send_notification_to_recipients(request=request)

    log.info(f"Successfully sent {notifications_sent} notifications.")


@galaxy_task(action="dispatch pending notifications")
def dispatch_pending_notifications(notification_manager: NotificationManager):
    """Dispatch pending notifications."""
    count = notification_manager.dispatch_pending_notifications_via_channels()
    if count:
        log.info(f"Successfully dispatched {count} notifications.")


@galaxy_task(action="clean up job working directories")
def cleanup_jwds(sa_session: galaxy_scoped_session, object_store: BaseObjectStore, days: int = 5):
    """Cleanup job working directories for failed jobs that are older than X days"""

    def get_failed_jobs():
        return sa_session.query(model.Job.id).filter(
            model.Job.state == "error",
            model.Job.update_time < datetime.datetime.now() - datetime.timedelta(days=days),
            model.Job.object_store_id.isnot(None),
        )

    def delete_jwd(job):
        try:
            # Get job working directory from object store
            path = object_store.get_filename(job, base_dir="job_work", dir_only=True, obj_dir=True)
            shutil.rmtree(path)
        except ObjectNotFound:
            # job working directory already deleted
            pass
        except OSError as e:
            log.error(f"Error deleting job working directory: {path} : {e.strerror}")

    failed_jobs = get_failed_jobs()

    if not failed_jobs:
        log.info("No failed jobs found within the last %s days", days)

    for job in failed_jobs:
        delete_jwd(job)
        log.info("Deleted job working directory for job %s", job.id)
