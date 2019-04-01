"""
Migration script to change the 'value' column of 'user_preference' table from numeric(22, 7) to numeric(26, 7)
"""
from __future__ import print_function

import logging

from sqlalchemy import MetaData, Numeric, Table

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    try:
        t = Table("job_metric_numeric", metadata, autoload=True)
        t.c.metric_value.alter(type=Numeric(26, 7))
        t = Table("task_metric_numeric", metadata, autoload=True)
        t.c.metric_value.alter(type=Numeric(26, 7))
    except Exception:
        log.exception("Modifying numeric column failed")


def downgrade(migrate_engine):
    # truncating columns would require truncating data in those columns, so it's best not to downgrade them
    pass
