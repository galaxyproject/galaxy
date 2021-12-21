import re

from alembic import context
from alembic import script
from sqlalchemy import create_engine

from galaxy.config import GalaxyAppConfiguration
from galaxy.model.migrations import GXY, TSI

config = context.config
target_metadata = None  # Not implemented: used for autogenerate, which we don't use here.

galaxy_config = GalaxyAppConfiguration()
URLS = {
    GXY: galaxy_config.database_connection,
    TSI: galaxy_config.install_database_connection or galaxy_config.database_connection,
}


def run_migrations_offline():
    """Run migrations in offline mode; database url required."""
    if not config.cmd_opts:  # invoked programmatically
        url = _get_url_from_config()
        _configure_and_run_migrations_offline(url)
    else:  # invoked via script
        f = _configure_and_run_migrations_offline
        _run_migrations_invoked_via_script(f)


def run_migrations_online():
    """Run migrations in online mode: engine and connection required."""
    if not config.cmd_opts:  # invoked programmatically
        url = _get_url_from_config()
        _configure_and_run_migrations_online(url)
    else:  # invoked via script
        f = _configure_and_run_migrations_online
        # Special case: runs online; config.cmd_opts has no revision property
        if config.cmd_opts.cmd[0].__name__ == 'current':
            for url in URLS.values():
                f(url)
            return
        _run_migrations_invoked_via_script(f)


def _run_migrations_invoked_via_script(run_migrations):
    revision_str = config.cmd_opts.revision

    if revision_str.startswith(f'{GXY}@'):
        url = URLS[GXY]
    elif revision_str.startswith(f'{TSI}@'):
        url = URLS[TSI]
    else:
        revision = _get_revision(revision_str)
        if GXY in revision.branch_labels:
            url = URLS[GXY]
        elif TSI in revision.branch_labels:
            url = URLS[TSI]

    run_migrations(url)


def _get_revision(revision_str):
    revision_id = _get_revision_id(revision_str)
    script_directory = script.ScriptDirectory.from_config(config)
    revision = script_directory.get_revision(revision_id)
    if not revision:
        raise Exception(f'Revision not found: "{revision}"')
    return revision


def _get_revision_id(revision_str):
    # Match a full or partial revision (GUID) or a relative migration identifier
    p = re.compile(r'([0-9A-Fa-f]+)([+-]\d)?')
    m = p.match(revision_str)
    if not m:
        raise Exception(f'Invalid revision or migration identifier: "{revision_str}"')
    return m.group(1)


def _configure_and_run_migrations_offline(url):
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _configure_and_run_migrations_online(url):
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


def _get_url_from_config():
    return config.get_main_option("sqlalchemy.url")


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
