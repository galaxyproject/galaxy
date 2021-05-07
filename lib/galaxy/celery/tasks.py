from lagom import magic_bind_to_container
from sqlalchemy import (
    and_,
    func,
    tuple_
)
from sqlalchemy.orm.scoping import (
    scoped_session,
)

from galaxy import model
from galaxy.app import MinimalManagerApp
from galaxy.celery import celery_app
from galaxy.jobs.manager import JobManager
from galaxy.managers.hdas import HDAManager
from galaxy.managers.lddas import LDDAManager
from galaxy.util import ExecutionTimer
from galaxy.util.custom_logging import get_logger
from . import get_galaxy_app

log = get_logger(__name__)
CELERY_TASKS = []


def galaxy_task(func):
    CELERY_TASKS.append(func.__name__)
    app = get_galaxy_app()
    if app:
        return magic_bind_to_container(app)(func)
    return func


@celery_app.task(ignore_result=True)
@galaxy_task
def recalculate_user_disk_usage(session: scoped_session, user_id=None):
    if user_id:
        user = session.query(model.User).get(user_id)
        if user:
            user.calculate_and_set_disk_usage()
            log.info(f"New user disk usage is {user.disk_usage}")
        else:
            log.error("Recalculate user disk usage task failed, user %s not found" % user_id)
    else:
        log.error("Recalculate user disk usage task received without user_id.")


@celery_app.task(ignore_result=True)
@galaxy_task
def purge_hda(hda_manager: HDAManager, hda_id):
    hda = hda_manager.by_id(hda_id)
    hda_manager._purge(hda)


@celery_app.task
@galaxy_task
def set_metadata(hda_manager: HDAManager, ldda_manager: LDDAManager, dataset_id, model_class='HistoryDatasetAssociation'):
    if model_class == 'HistoryDatasetAssociation':
        dataset = hda_manager.by_id(dataset_id)
    elif model_class == 'LibraryDatasetDatasetAssociation':
        dataset = ldda_manager.by_id(dataset_id)
    dataset.datatype.set_meta(dataset)


@celery_app.task(ignore_result=True)
@galaxy_task
def export_history(
        app: MinimalManagerApp,
        sa_session: scoped_session,
        job_manager: JobManager,
        store_directory,
        history_id,
        job_id,
        include_hidden=False,
        include_deleted=False):
    history = sa_session.query(model.History).get(history_id)
    with model.store.DirectoryModelExportStore(store_directory, app=app, export_files="symlink") as export_store:
        export_store.export_history(history, include_hidden=include_hidden, include_deleted=include_deleted)
    job = sa_session.query(model.Job).get(job_id)
    job.state = model.Job.states.NEW
    sa_session.flush()
    job_manager.enqueue(job)


@celery_app.task
@galaxy_task
def prune_history_audit_table(sa_session: scoped_session):
    """Prune ever growing history_audit table."""
    history_audit_table = model.HistoryAudit.table
    latest_subq = sa_session.query(
        history_audit_table.c.history_id,
        func.max(history_audit_table.c.update_time).label('max_update_time')).group_by(history_audit_table.c.history_id).subquery()
    not_latest_query = sa_session.query(
        history_audit_table.c.history_id, history_audit_table.c.update_time
    ).select_from(latest_subq).join(
        history_audit_table, and_(
            history_audit_table.c.update_time < latest_subq.columns.max_update_time,
            history_audit_table.c.history_id == latest_subq.columns.history_id))
    d = history_audit_table.delete()
    timer = ExecutionTimer()
    sa_session.execute(d.where(tuple_(history_audit_table.c.history_id, history_audit_table.c.update_time).in_(not_latest_query)))
    log.debug(f"Successfully pruned history_audit table {timer}")
