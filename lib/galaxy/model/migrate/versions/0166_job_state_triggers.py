"""
Job state trigger syncs update_time in hdca table.
Add job-state-summary view for hdca elements
"""
from __future__ import print_function

import logging

from sqlalchemy import MetaData

from galaxy.model.triggers import (
    execute_statements,
    get_job_state_trigger_drop_sql,
    get_job_state_trigger_install_sql
)
from galaxy.model.view import HistoryDatasetCollectionJobStateSummary
from galaxy.model.view.utils import CreateView, DropView


log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata = MetaData()
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop collection job-state-summary (can't run create ore replace on sqlite)
    drop_view = DropView(HistoryDatasetCollectionJobStateSummary, if_exists=True)
    migrate_engine.execute(drop_view)

    # Install collection job-state-summary
    create_view = CreateView(HistoryDatasetCollectionJobStateSummary)
    migrate_engine.execute(create_view)

    # Install Triggers
    statements = get_job_state_trigger_install_sql(migrate_engine.name)
    execute_statements(migrate_engine, statements)


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    # Drop collection job-state-summary
    drop_view = DropView(HistoryDatasetCollectionJobStateSummary)
    migrate_engine.execute(drop_view)

    # Drop triggers
    statements = get_job_state_trigger_drop_sql(migrate_engine.name)
    execute_statements(migrate_engine, statements)
