"""
Galaxy sql view models
"""
from sqlalchemy import Integer
from sqlalchemy.orm import registry
from sqlalchemy.sql import (
    column,
    text,
)

from galaxy.model.view.utils import View


class HistoryDatasetCollectionJobStateSummary(View):
    name = "collection_job_state_summary_view"

    aggregate_state_query = """
SELECT
    hdca_id,
    SUM(CASE WHEN state = 'new' THEN 1 ELSE 0 END) AS new,
    SUM(CASE WHEN state = 'resubmitted' THEN 1 ELSE 0 END) AS resubmitted,
    SUM(CASE WHEN state = 'waiting' THEN 1 ELSE 0 END) AS waiting,
    SUM(CASE WHEN state = 'queued' THEN 1 ELSE 0 END) AS queued,
    SUM(CASE WHEN state = 'running' THEN 1 ELSE 0 END) AS running,
    SUM(CASE WHEN state = 'ok' THEN 1 ELSE 0 END) AS ok,
    SUM(CASE WHEN state = 'error' THEN 1 ELSE 0 END) AS error,
    SUM(CASE WHEN state = 'failed' THEN 1 ELSE 0 END) AS failed,
    SUM(CASE WHEN state = 'paused' THEN 1 ELSE 0 END) AS paused,
    SUM(CASE WHEN state = 'skipped' THEN 1 ELSE 0 END) AS skipped,
    SUM(CASE WHEN state = 'deleted' THEN 1 ELSE 0 END) AS deleted,
    SUM(CASE WHEN state = 'deleted_new' THEN 1 ELSE 0 END) AS deleted_new,
    SUM(CASE WHEN state = 'upload' THEN 1 ELSE 0 END) AS upload,
    SUM(CASE WHEN job_id IS NOT NULL THEN 1 ELSE 0 END) AS all_jobs
FROM (
    SELECT hdca.id AS hdca_id, job.id AS job_id, job.state as state
    FROM history_dataset_collection_association hdca
    LEFT JOIN implicit_collection_jobs icj
        ON icj.id = hdca.implicit_collection_jobs_id
    LEFT JOIN implicit_collection_jobs_job_association icjja
        ON icj.id = icjja.implicit_collection_jobs_id
    LEFT JOIN job
        ON icjja.job_id = job.id

    UNION

    SELECT hdca.id AS hdca_id, job.id AS job_id, job.state AS state
    FROM history_dataset_collection_association hdca
    LEFT JOIN job
        ON hdca.job_id = job.id
) jobstates
GROUP BY jobstates.hdca_id
"""

    __view__ = text(aggregate_state_query).columns(
        column("hdca_id", Integer),
        column("new", Integer),
        column("resubmitted", Integer),
        column("waiting", Integer),
        column("queued", Integer),
        column("running", Integer),
        column("ok", Integer),
        column("error", Integer),
        column("failed", Integer),
        column("paused", Integer),
        column("skipped", Integer),
        column("deleted", Integer),
        column("deleted_new", Integer),
        column("upload", Integer),
        column("all_jobs", Integer),
    )
    pkeys = {"hdca_id"}
    __table__ = View._make_table(name, __view__, pkeys)


mapper_registry = registry()
mapper_registry.map_imperatively(
    HistoryDatasetCollectionJobStateSummary, HistoryDatasetCollectionJobStateSummary.__table__
)
