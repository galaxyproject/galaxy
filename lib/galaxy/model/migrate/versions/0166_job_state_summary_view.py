"""
Job state trigger syncs update_time in hdca table.
Add job-state-summary view for hdca elements
"""

import logging

from galaxy.model.view import HistoryDatasetCollectionJobStateSummary
from galaxy.model.view.utils import CreateView, DropView

log = logging.getLogger(__name__)


def upgrade(migrate_engine):
    print(__doc__)
    # drop first because sqlite does not support or_replace
    downgrade(migrate_engine)
    create_view = CreateView(HistoryDatasetCollectionJobStateSummary)
    # print(str(create_view.compile(migrate_engine)))
    migrate_engine.execute(create_view)


def downgrade(migrate_engine):
    drop_view = DropView(HistoryDatasetCollectionJobStateSummary)
    # print(str(drop_view.compile(migrate_engine)))
    migrate_engine.execute(drop_view)
