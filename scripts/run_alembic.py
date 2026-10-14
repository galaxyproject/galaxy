#!/usr/bin/env python

"""
This script is intended to be invoked by the scripts/run_alembic.sh script.
"""

import logging
import os
import os.path
import sys

# Prefer installed workspace packages (galaxy-data); keep lib/ fallback for
# lib/galaxy_test leftovers.
try:
    import galaxy.model.migrations.scripts  # noqa: F401
except ImportError:
    sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))

from galaxy.model.migrations.scripts import (
    add_db_urls_to_command_arguments,
    get_configuration,
    invoke_alembic,
)

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


def _resolve_alembic_config() -> str:
    """Resolve the Galaxy alembic.ini from the installed galaxy-data package.

    Falls back to the source-tree path (packages/data/...) and then the legacy
    lib/ path so both installed and source checkouts keep working.
    """
    try:
        import galaxy.model.migrations.scripts as _scripts

        candidate = os.path.join(os.path.dirname(os.path.abspath(_scripts.__file__)), "alembic.ini")
        if os.path.exists(candidate):
            return candidate
    except Exception:
        pass
    for candidate in (
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "packages",
            "data",
            "src",
            "galaxy",
            "model",
            "migrations",
            "alembic.ini",
        ),
        "packages/data/src/galaxy/model/migrations/alembic.ini",
    ):
        if os.path.exists(candidate):
            return candidate
    # Default to the installed-package location even if the existence check
    # above failed (e.g. unusual cwd); alembic will report a clear error.
    return "packages/data/src/galaxy/model/migrations/alembic.ini"


ALEMBIC_CONFIG = _resolve_alembic_config()


def run():
    sys.argv.insert(1, "--config")
    sys.argv.insert(2, ALEMBIC_CONFIG)
    gxy_config, tsi_config, _ = get_configuration(sys.argv, os.getcwd())
    add_db_urls_to_command_arguments(sys.argv, gxy_config.url, tsi_config.url)
    invoke_alembic()


if __name__ == "__main__":
    run()
