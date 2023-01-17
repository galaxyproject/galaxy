import json
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
from galaxy.managers.tool_data import ToolDataImportManager
from galaxy.metadata.set_metadata import set_metadata_portable
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.schema.tasks import (
    ComputeDatasetHashTaskRequest,
    GenerateHistoryContentDownload,
    GenerateHistoryDownload,
    GenerateInvocationDownload,
    GeneratePdfDownload,
    ImportModelStoreTaskRequest,
    MaterializeDatasetInstanceTaskRequest,
    PrepareDatasetCollectionDownload,
    SetupHistoryExportJob,
    WriteHistoryContentTo,
    WriteHistoryTo,
    WriteInvocationTo,
)
from galaxy.structured_app import MinimalManagerApp
from galaxy.tools import create_tool_from_representation
from galaxy.tools.data_fetch import do_fetch
from galaxy.util import galaxy_directory
from galaxy.util.custom_logging import get_logger
from galaxy.web.short_term_storage import ShortTermStorageMonitor

log = get_logger(__name__)


@lru_cache()
def cached_create_tool_from_representation(app, raw_tool_source):
    return create_tool_from_representation(
        app=app, raw_tool_source=raw_tool_source, tool_dir="", tool_source_class="XmlToolSource"
    )


@galaxy_task(ignore_result=True, action="recalculate a user's disk usage")
def recalculate_user_disk_usage(session: galaxy_scoped_session, user_id: Optional[int] = None):
    if user_id:
        user = session.query(model.User).get(user_id)
        if user:
            user.calculate_and_set_disk_usage()
            log.info(f"New user disk usage is {user.disk_usage}")
        else:
            log.error(f"Recalculate user disk usage task failed, user {user_id} not found")
    else:
        log.error("Recalculate user disk usage task received without user_id.")


@galaxy_task(ignore_result=True, action="purge a history dataset")
def purge_hda(hda_manager: HDAManager, hda_id: int):
    hda = hda_manager.by_id(hda_id)
    hda_manager._purge(hda)


@galaxy_task(ignore_result=True, action="materializing dataset instance")
def materialize(
    hda_manager: HDAManager,
    request: MaterializeDatasetInstanceTaskRequest,
):
    """Materialize datasets using HDAManager."""
    hda_manager.materialize(request)


@galaxy_task(action="set metadata for job")
def set_job_metadata(
    tool_job_working_directory,
    extended_metadata_collection: bool,
    job_id: int,
    sa_session: galaxy_scoped_session,
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
):
    manager = _get_dataset_manager(hda_manager, ldda_manager, model_class)
    dataset_instance = manager.by_id(dataset_id)
    can_change_datatype = manager.ensure_can_change_datatype(dataset_instance, raiseException=False)
    if not can_change_datatype:
        log.info(f"Changing datatype is not allowed for {model_class} {dataset_instance.id}")
        return
    if datatype == "auto":
        path = dataset_instance.dataset.file_name
        datatype = sniff.guess_ext(path, datatypes_registry.sniff_order)
    datatypes_registry.change_datatype(dataset_instance, datatype)
    sa_session.flush()
    set_metadata(hda_manager, ldda_manager, sa_session, dataset_id, model_class)


@galaxy_task(action="set dataset association metadata")
def set_metadata(
    hda_manager: HDAManager,
    ldda_manager: LDDAManager,
    sa_session: galaxy_scoped_session,
    dataset_id: int,
    model_class: str = "HistoryDatasetAssociation",
    overwrite: bool = True,
):
    manager = _get_dataset_manager(hda_manager, ldda_manager, model_class)
    dataset_instance = manager.by_id(dataset_id)
    can_set_metadata = manager.ensure_can_set_metadata(dataset_instance, raiseException=False)
    if not can_set_metadata:
        log.info(f"Setting metadata is not allowed for {model_class} {dataset_instance.id}")
        return
    try:
        if overwrite:
            hda_manager.overwrite_metadata(dataset_instance)
        dataset_instance.datatype.set_meta(dataset_instance)
        dataset_instance.set_peek()
        dataset_instance.dataset.state = dataset_instance.dataset.states.OK
    except Exception as e:
        log.info(f"Setting metadata failed on {model_class} {dataset_instance.id}: {str(e)}")
        dataset_instance.dataset.state = dataset_instance.dataset.states.FAILED_METADATA
    sa_session.flush()


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
    self, job_id: int, raw_tool_source: str, app: MinimalManagerApp, sa_session: galaxy_scoped_session
):
    tool = cached_create_tool_from_representation(app=app, raw_tool_source=raw_tool_source)
    job = sa_session.query(model.Job).get(job_id)
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
def finish_job(job_id: int, raw_tool_source: str, app: MinimalManagerApp, sa_session: galaxy_scoped_session):
    tool = cached_create_tool_from_representation(app=app, raw_tool_source=raw_tool_source)
    job = sa_session.query(model.Job).get(job_id)
    # TODO: assert state ?
    mini_job_wrapper = MinimalJobWrapper(job=job, app=app, tool=tool)
    mini_job_wrapper.finish("", "")


def is_aborted(session: galaxy_scoped_session, job_id: int):
    return session.execute(
        select(
            exists(model.Job.state).where(
                model.Job.id == job_id,
                model.Job.state.in_(
                    [model.Job.states.DELETED, model.Job.states.DELETED_NEW, model.Job.states.DELETING]
                ),
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
                    return


def _fetch_data(setup_return):
    tool_job_working_directory, request_path, file_sources_dict = setup_return
    working_directory = Path(tool_job_working_directory) / "working"
    datatypes_registry = DatatypesRegistry()
    datatypes_registry.load_datatypes(
        galaxy_directory,
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
) -> str:
    job = sa_session.query(model.Job).get(job_id)
    mini_job_wrapper = MinimalJobWrapper(job=job, app=app)
    mini_job_wrapper.change_state(model.Job.states.RUNNING, flush=True, job=job)
    return abort_when_job_stops(_fetch_data, session=sa_session, job_id=job_id, setup_return=setup_return)


@galaxy_task(ignore_result=True, action="setting up export history job")
def export_history(
    model_store_manager: ModelStoreManager,
    request: SetupHistoryExportJob,
):
    model_store_manager.setup_history_export_job(request)


@galaxy_task(action="preparing compressed file for collection download")
def prepare_dataset_collection_download(
    request: PrepareDatasetCollectionDownload,
    collection_manager: DatasetCollectionManager,
):
    """Create a short term storage file tracked and available for download of target collection."""
    collection_manager.write_dataset_collection(request)


@galaxy_task(action="preparing Galaxy Markdown PDF for download")
def prepare_pdf_download(
    request: GeneratePdfDownload, config: GalaxyAppConfiguration, short_term_storage_monitor: ShortTermStorageMonitor
):
    """Create a short term storage file tracked and available for download of target PDF for Galaxy Markdown."""
    generate_branded_pdf(request, config, short_term_storage_monitor)


@galaxy_task(action="generate and stage a history model store for download")
def prepare_history_download(
    model_store_manager: ModelStoreManager,
    request: GenerateHistoryDownload,
):
    model_store_manager.prepare_history_download(request)


@galaxy_task(action="generate and stage a history content model store for download")
def prepare_history_content_download(
    model_store_manager: ModelStoreManager,
    request: GenerateHistoryContentDownload,
):
    model_store_manager.prepare_history_content_download(request)


@galaxy_task(action="generate and stage a workflow invocation store for download")
def prepare_invocation_download(
    model_store_manager: ModelStoreManager,
    request: GenerateInvocationDownload,
):
    model_store_manager.prepare_invocation_download(request)


@galaxy_task(action="generate and stage a workflow invocation store to file source URI")
def write_invocation_to(
    model_store_manager: ModelStoreManager,
    request: WriteInvocationTo,
):
    model_store_manager.write_invocation_to(request)


@galaxy_task(action="generate and stage a history store to file source URI")
def write_history_to(
    model_store_manager: ModelStoreManager,
    request: WriteHistoryTo,
):
    model_store_manager.write_history_to(request)


@galaxy_task(action="generate and stage a history content model store to file source URI")
def write_history_content_to(
    model_store_manager: ModelStoreManager,
    request: WriteHistoryContentTo,
):
    model_store_manager.write_history_content_to(request)


@galaxy_task(action="import objects from a target model store")
def import_model_store(
    model_store_manager: ModelStoreManager,
    request: ImportModelStoreTaskRequest,
):
    model_store_manager.import_model_store(request)


@galaxy_task(action="compute dataset hash and store in database")
def compute_dataset_hash(
    dataset_manager: DatasetManager,
    request: ComputeDatasetHashTaskRequest,
):
    dataset_manager.compute_hash(request)


@galaxy_task(action="import a data bundle")
def import_data_bundle(
    hda_manager: HDAManager,
    ldda_manager: LDDAManager,
    tool_data_import_manager: ToolDataImportManager,
    config: GalaxyAppConfiguration,
    src: str,
    uri: Optional[str] = None,
    id: Optional[int] = None,
):
    if src == "uri":
        assert uri
        tool_data_import_manager.import_data_bundle_by_uri(config, uri)
    else:
        assert id
        dataset: model.DatasetInstance
        if src == "hda":
            dataset = hda_manager.by_id(id)
        else:
            dataset = ldda_manager.by_id(id)
        tool_data_import_manager.import_data_bundle_by_dataset(config, dataset)


@galaxy_task(action="pruning history audit table")
def prune_history_audit_table(sa_session: galaxy_scoped_session):
    """Prune ever growing history_audit table."""
    model.HistoryAudit.prune(sa_session)


@galaxy_task(action="clean up short term storage")
def cleanup_short_term_storage(storage_monitor: ShortTermStorageMonitor):
    """Cleanup short term storage."""
    storage_monitor.cleanup()
