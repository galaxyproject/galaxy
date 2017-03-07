"""
Migration script to set the 'deleted' column of the
'history_dataset_association' table to True if 'purged' is True.
"""
from __future__ import print_function

import logging

log = logging.getLogger( __name__ )


def engine_true(migrate_engine):
    if migrate_engine.name in ['postgres', 'postgresql']:
        return "TRUE"
    elif migrate_engine.name in ['mysql', 'sqlite']:
        return 1
    else:
        raise Exception('Unknown database type: %s' % migrate_engine.name)


def upgrade(migrate_engine):
    print(__doc__)
    cmd = 'UPDATE history_dataset_association SET deleted=%s WHERE purged;' % engine_true(migrate_engine)
    try:
        migrate_engine.execute(cmd)
    except Exception:
        log.exception("Exception executing SQL command: %s" % cmd)


def downgrade(migrate_engine):
    pass
