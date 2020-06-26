"""
Add a user_id column to the job table.
"""

import logging

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    Table
)

from galaxy.model.migrate.versions.util import (
    add_column,
    drop_column
)

log = logging.getLogger(__name__)
metadata = MetaData()


def upgrade(migrate_engine):
    print(__doc__)
    metadata.bind = migrate_engine
    metadata.reflect()

    Job_table = Table("job", metadata, autoload=True)
    col = Column("user_id", Integer, ForeignKey("galaxy_user.id"), index=True, nullable=True)
    add_column(col, Job_table, metadata, index_name='ix_job_user_id')
    try:
        cmd = "SELECT job.id AS galaxy_job_id, " \
            + "galaxy_session.user_id AS galaxy_user_id " \
            + "FROM job " \
            + "JOIN galaxy_session ON job.session_id = galaxy_session.id;"
        job_users = migrate_engine.execute(cmd).fetchall()
        print("Updating user_id column in job table for ", len(job_users), " rows...")
        print("")
        update_count = 0
        for row in job_users:
            if row.galaxy_user_id:
                cmd = "UPDATE job SET user_id = %d WHERE id = %d" % (int(row.galaxy_user_id), int(row.galaxy_job_id))
                update_count += 1
            migrate_engine.execute(cmd)
        print("Updated column 'user_id' for ", update_count, " rows of table 'job'.")
        print(len(job_users) - update_count, " rows have no user_id since the value was NULL in the galaxy_session table.")
        print("")
    except Exception:
        log.exception("Updating column 'user_id' of table 'job' failed.")


def downgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    drop_column('user_id', 'job', metadata)
