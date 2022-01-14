from galaxy import model
from galaxy.celery import galaxy_task
from galaxy.jobs.manager import JobManager
from galaxy.managers.hdas import HDAManager
from galaxy.managers.lddas import LDDAManager
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.structured_app import MinimalManagerApp
from galaxy.util import ExecutionTimer
from galaxy.util.custom_logging import get_logger

log = get_logger(__name__)


@galaxy_task(ignore_result=True)
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


@galaxy_task(ignore_result=True)
def purge_hda(hda_manager: HDAManager, hda_id):
    hda = hda_manager.by_id(hda_id)
    hda_manager._purge(hda)


@galaxy_task
def set_metadata(hda_manager: HDAManager, ldda_manager: LDDAManager, dataset_id, model_class='HistoryDatasetAssociation'):
    if model_class == 'HistoryDatasetAssociation':
        dataset = hda_manager.by_id(dataset_id)
    elif model_class == 'LibraryDatasetDatasetAssociation':
        dataset = ldda_manager.by_id(dataset_id)
    dataset.datatype.set_meta(dataset)


@galaxy_task(ignore_result=True)
def export_history(
        app: MinimalManagerApp,
        sa_session: galaxy_scoped_session,
        job_manager: JobManager,
        store_directory: str,
        history_id: int,
        job_id: int,
        include_hidden=False,
        include_deleted=False):
    history = sa_session.query(model.History).get(history_id)
    with model.store.DirectoryModelExportStore(store_directory, app=app, export_files="symlink") as export_store:
        export_store.export_history(history, include_hidden=include_hidden, include_deleted=include_deleted)
    job = sa_session.query(model.Job).filter_by(id=job_id).one()
    job.state = model.Job.states.NEW
    sa_session.flush()
    job_manager.enqueue(job)


@galaxy_task
def prune_history_audit_table(sa_session: galaxy_scoped_session):
    """Prune ever growing history_audit table."""
    timer = ExecutionTimer()
    model.HistoryAudit.prune(sa_session)
    log.debug(f"Successfully pruned history_audit table {timer}")
