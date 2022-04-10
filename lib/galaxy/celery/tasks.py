from galaxy import model
from galaxy.celery import galaxy_task
from galaxy.managers.hdas import HDAManager
from galaxy.managers.lddas import LDDAManager
from galaxy.managers.model_stores import ModelStoreManager
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.schema.tasks import SetupHistoryExportJob
from galaxy.util.custom_logging import get_logger

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


@galaxy_task(action="pruning history audit table")
def prune_history_audit_table(sa_session: galaxy_scoped_session):
    """Prune ever growing history_audit table."""
    model.HistoryAudit.prune(sa_session)
