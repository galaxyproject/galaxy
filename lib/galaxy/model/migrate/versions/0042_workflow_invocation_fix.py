"""
Drop and readd workflow invocation tables, allowing null jobs
"""

import datetime
import logging

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Table
)

from galaxy.model.migrate.versions.util import (
    create_table,
    drop_table
)

log = logging.getLogger(__name__)
now = datetime.datetime.utcnow
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    # 1) Drop
    for table_name in ["workflow_invocation_step", "workflow_invocation"]:
        t = Table(table_name, metadata, autoload=True)
        drop_table(t)
        metadata.remove(t)

    # 2) Re-add
    WorkflowInvocation_table = Table("workflow_invocation", metadata,
                                     Column("id", Integer, primary_key=True),
                                     Column("create_time", DateTime, default=now),
                                     Column("update_time", DateTime, default=now, onupdate=now),
                                     Column("workflow_id", Integer, ForeignKey("workflow.id"), index=True, nullable=False))

    WorkflowInvocationStep_table = Table("workflow_invocation_step", metadata,
                                         Column("id", Integer, primary_key=True),
                                         Column("create_time", DateTime, default=now),
                                         Column("update_time", DateTime, default=now, onupdate=now),
                                         Column("workflow_invocation_id", Integer, ForeignKey("workflow_invocation.id"), index=True, nullable=False),
                                         Column("workflow_step_id", Integer, ForeignKey("workflow_step.id"), index=True, nullable=False),
                                         Column("job_id", Integer, ForeignKey("job.id"), index=True, nullable=True))

    for table in [WorkflowInvocation_table, WorkflowInvocationStep_table]:
        create_table(table)


def downgrade(migrate_engine):
    pass
