"""
"""
import logging
import sys

from sqlalchemy import (
    MetaData,
    Table
)

from galaxy.model.migrate.versions.util import (
    add_index,
    engine_false
)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
format = "%(name)s %(levelname)s %(asctime)s %(message)s"
formatter = logging.Formatter(format)
handler.setFormatter(formatter)
log.addHandler(handler)

metadata = MetaData()


def upgrade(migrate_engine):
    metadata.bind = migrate_engine
    metadata.reflect()

    User_table = Table("galaxy_user", metadata, autoload=True)
    add_index('ix_galaxy_user_deleted', User_table, 'deleted')
    add_index('ix_galaxy_user_purged', User_table, 'purged')
    # Set the default data in the galaxy_user table, but only for null values
    cmd = "UPDATE galaxy_user SET deleted = %s WHERE deleted is null" % engine_false(migrate_engine)
    try:
        migrate_engine.execute(cmd)
    except Exception:
        log.exception("Setting default data for galaxy_user.deleted column failed.")
    cmd = "UPDATE galaxy_user SET purged = %s WHERE purged is null" % engine_false(migrate_engine)
    try:
        migrate_engine.execute(cmd)
    except Exception:
        log.exception("Setting default data for galaxy_user.purged column failed.")
    add_index('ix_hda_copied_from_library_dataset_dataset_association_id',
        'history_dataset_association',
        'copied_from_library_dataset_dataset_association_id', metadata)


def downgrade(migrate_engine):
    pass
