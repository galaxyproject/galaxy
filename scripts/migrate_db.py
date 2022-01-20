"""
This script retrieves relevant configuration values and invokes
the Alembic console runner.
It is wrapped by run_alembic.sh (see that file for usage) and by
manage_db.sh (for legacy usage).
"""
import logging
import os.path
import sys

import alembic.config

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'lib')))

from galaxy.model.migrations import GXY, TSI
from galaxy.model.migrations.scripts import add_db_urls_to_command_arguments

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


def invoke_alembic():
    add_db_urls_to_command_arguments(sys.argv, os.getcwd())

    # Accept 'heads' as the target revision argument to enable upgrading both gxy and tsi in one command.
    # This is consistent with Alembic's CLI, which allows `upgrade heads`. However, this would not work for
    # separate gxy and tsi databases: we can't attach a database url to a revision after Alembic has been
    # invoked with the 'upgrade' command and the 'heads' argument. So, instead we invoke Alembic for each head.
    if 'heads' in sys.argv and 'upgrade' in sys.argv:
        i = sys.argv.index('heads')
        sys.argv[i] = f'{GXY}@head'
        alembic.config.main()
        sys.argv[i] = f'{TSI}@head'
        alembic.config.main()
    else:
        alembic.config.main()


if __name__ == '__main__':
    invoke_alembic()
