"""Add skipped state to collection_job_state_summary_view

Revision ID: c39f1de47a04
Revises: 3100452fa030
Create Date: 2023-01-16 11:53:59.783836

"""
from typing import Generator

from alembic import (
    context,
    op,
)
from alembic_utils.pg_view import PGView
from sqlalchemy import text as sql_text
from sqlalchemy.engine.url import make_url
from sqlalchemy.sql.elements import TextClause

from galaxy.model.view import HistoryDatasetCollectionJobStateSummary

# revision identifiers, used by Alembic.
revision = "c39f1de47a04"
down_revision = "3100452fa030"
branch_labels = None
depends_on = None

PREVIOUS_AGGREGATE_QUERY = """
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


class SqlitePGView(PGView):
    def to_sql_statement_create_or_replace(self) -> Generator[TextClause, None, None]:
        """Generates a SQL "create or replace view" statement"""

        yield sql_text(f"""DROP VIEW IF EXISTS {self.literal_schema}."{self.signature}";""")
        yield sql_text(f"""CREATE VIEW {self.literal_schema}."{self.signature}" AS {self.definition};""")


def get_view_instance(definition: str):
    try:
        url = make_url(context.config.get_main_option("sqlalchemy.url"))
        dialect = url.get_dialect().name
    except Exception:
        # If someone's doing offline migrations they're probably using PostgreSQL
        dialect = "postgresql"
    if dialect == "postgresql":
        ViewClass = PGView
        schema = "public"
    elif dialect == "sqlite":
        ViewClass = SqlitePGView
        schema = "main"
    else:
        raise Exception(f"Don't know how to generate view for dialect '{dialect}'")
    return ViewClass(schema=schema, signature="collection_job_state_summary_view", definition=definition)


def upgrade():
    view = get_view_instance(HistoryDatasetCollectionJobStateSummary.aggregate_state_query)
    # op.replace_entity comes from alembic_utils plugin
    op.replace_entity(view)  # type: ignore[attr-defined]


def downgrade():
    view = get_view_instance(PREVIOUS_AGGREGATE_QUERY)
    op.replace_entity(view)  # type: ignore[attr-defined]
