"""
Update job-state-summary view for hdca elements to include job directly tied with the hdca
"""

import logging

from galaxy.model.view import HistoryDatasetCollectionJobStateSummary
from galaxy.model.view.utils import CreateView, DropView

log = logging.getLogger(__name__)


def upgrade(migrate_engine):
    print(__doc__)
    # drop first because sqlite does not support or_replace
    downgrade(migrate_engine)
    view = HistoryDatasetCollectionJobStateSummary
    create_view = CreateView(view.name, view.__view__)
    migrate_engine.execute(create_view)


def downgrade(migrate_engine):
    drop_view = DropView(HistoryDatasetCollectionJobStateSummary.name)
    migrate_engine.execute(drop_view)
