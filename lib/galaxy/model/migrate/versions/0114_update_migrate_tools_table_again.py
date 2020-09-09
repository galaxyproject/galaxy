"""
Migration script to update the migrate_tools.repository_path column to point to the new location lib/tool_shed/galaxy_install/migrate.
"""

import logging

log = logging.getLogger(__name__)


def upgrade(migrate_engine):
    print(__doc__)
    # Create the table.
    try:
        cmd = "UPDATE migrate_tools set repository_path='lib/tool_shed/galaxy_install/migrate';"
        migrate_engine.execute(cmd)
    except Exception:
        log.exception("Updating migrate_tools.repository_path column to point to the new location lib/tool_shed/galaxy_install/migrate failed.")


def downgrade(migrate_engine):
    try:
        cmd = "UPDATE migrate_tools set repository_path='lib/galaxy/tool_shed/migrate';"
        migrate_engine.execute(cmd)
    except Exception:
        log.exception("Updating migrate_tools.repository_path column to point to the old location lib/galaxy/tool_shed/migrate failed.")
