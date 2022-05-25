from galaxy import model
from galaxy.celery import galaxy_task
from galaxy.config import GalaxyAppConfiguration
from galaxy.managers.collections import DatasetCollectionManager
from galaxy.managers.hdas import HDAManager
from galaxy.managers.lddas import LDDAManager
from galaxy.managers.markdown_util import generate_branded_pdf
from galaxy.managers.model_stores import ModelStoreManager
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.schema.tasks import (
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
from galaxy.util.custom_logging import get_logger
from galaxy.web.short_term_storage import ShortTermStorageMonitor

log = get_logger(__name__)


@galaxy_task(ignore_result=True, action="recalculate a user's disk usage")
def recalculate_user_disk_usage(session: galaxy_scoped_session, user_id=None):
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
def purge_hda(hda_manager: HDAManager, hda_id):
    hda = hda_manager.by_id(hda_id)
    hda_manager._purge(hda)


@galaxy_task(ignore_result=True, action="materializing dataset instance")
def materialize(
    hda_manager: HDAManager,
    request: MaterializeDatasetInstanceTaskRequest,
):
    """Materialize datasets using HDAManager."""
    hda_manager.materialize(request)


@galaxy_task(action="set dataset association metadata")
def set_metadata(
    hda_manager: HDAManager, ldda_manager: LDDAManager, dataset_id, model_class="HistoryDatasetAssociation"
):
    if model_class == "HistoryDatasetAssociation":
        dataset = hda_manager.by_id(dataset_id)
    elif model_class == "LibraryDatasetDatasetAssociation":
        dataset = ldda_manager.by_id(dataset_id)
    dataset.datatype.set_meta(dataset)


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


@galaxy_task(action="pruning history audit table")
def prune_history_audit_table(sa_session: galaxy_scoped_session):
    """Prune ever growing history_audit table."""
    model.HistoryAudit.prune(sa_session)


@galaxy_task(action="clean up short term storage")
def cleanup_short_term_storage(storage_monitor: ShortTermStorageMonitor):
    """Cleanup short term storage."""
    storage_monitor.cleanup()
