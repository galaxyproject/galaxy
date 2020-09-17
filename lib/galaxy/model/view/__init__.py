"""
Galaxy sql view models
"""
from sqlalchemy import Integer, MetaData
from sqlalchemy.orm import mapper
from sqlalchemy.sql import column, text
from sqlalchemy_utils import create_view

from .utils import View

metadata = MetaData()


class HistoryDatasetCollectionJobStateSummary(View):

    __view__ = text("""
        SELECT
            hdca.id as hdca_id,
            SUM(CASE WHEN state = 'new' THEN 1 ELSE 0 END) AS new,
            SUM(CASE WHEN state = 'resubmitted' THEN 1 ELSE 0 END) AS resubmitted,
            SUM(CASE WHEN state = 'waiting' THEN 1 ELSE 0 END) AS waiting,
            SUM(CASE WHEN state = 'queued' THEN 1 ELSE 0 END) AS queued,
            SUM(CASE WHEN state = 'running' THEN 1 ELSE 0 END) AS running,
            SUM(CASE WHEN state = 'ok' THEN 1 ELSE 0 END) AS ok,
            SUM(CASE WHEN state = 'error' THEN 1 ELSE 0 END) AS error,
            SUM(CASE WHEN state = 'failed' THEN 1 ELSE 0 END) AS failed,
            SUM(CASE WHEN state = 'paused' THEN 1 ELSE 0 END) AS paused,
            SUM(CASE WHEN state = 'deleted' THEN 1 ELSE 0 END) AS deleted,
            SUM(CASE WHEN state = 'deleted_new' THEN 1 ELSE 0 END) AS deleted_new,
            SUM(CASE WHEN state = 'upload' THEN 1 ELSE 0 END) AS upload,
            SUM(CASE WHEN job.id IS NOT NULL THEN 1 ELSE 0 END) AS all_jobs
        FROM history_dataset_collection_association hdca
        LEFT JOIN implicit_collection_jobs icj
            ON icj.id = hdca.implicit_collection_jobs_id
        LEFT JOIN implicit_collection_jobs_job_association icjja
            ON icj.id = icjja.implicit_collection_jobs_id
        LEFT JOIN job
            ON icjja.job_id = job.id
        GROUP BY hdca.id
    """)

    __view__ = __view__.columns(
        column('hdca_id', Integer),
        column('new', Integer),
        column('resubmitted', Integer),
        column('waiting', Integer),
        column('queued', Integer),
        column('running', Integer),
        column('ok', Integer),
        column('error', Integer),
        column('failed', Integer),
        column('paused', Integer),
        column('deleted', Integer),
        column('deleted_new', Integer),
        column('upload', Integer),
        column('all_jobs', Integer)
    )

    __table__ = create_view('collection_job_state_summary_view', __view__, metadata)


mapper(HistoryDatasetCollectionJobStateSummary, HistoryDatasetCollectionJobStateSummary.__table__)
