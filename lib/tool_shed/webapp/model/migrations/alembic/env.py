import logging
from typing import (
    Callable,
    cast,
    Dict,
)

from alembic import context
from sqlalchemy import create_engine

config = context.config
target_metadata = None  # Not implemented: used for autogenerate, which we don't use here.
log = logging.getLogger(__name__)


def run_migrations_offline() -> None:
    """Run migrations in offline mode; database url required."""
    if not config.cmd_opts:  # invoked programmatically
        url = _get_url_from_config()
        _configure_and_run_migrations_offline(url)
    else:  # invoked via script
        f = _configure_and_run_migrations_offline
        _run_migrations_invoked_via_script(f)


def run_migrations_online() -> None:
    """Run migrations in online mode: engine and connection required."""
    if not config.cmd_opts:  # invoked programmatically
        url = _get_url_from_config()
        _configure_and_run_migrations_online(url)
    else:  # invoked via script
        f = _configure_and_run_migrations_online
        _run_migrations_invoked_via_script(f)


def _run_migrations_invoked_via_script(run_migrations: Callable[[str], None]) -> None:
    url = _load_url()
    # Special case: the `current` command has no config.cmd_opts.revision property,
    # so we check for it before checking for `upgrade/downgrade`.
    if _process_cmd_current(url):
        return  # we're done
    run_migrations(url)


def _process_cmd_current(url: str) -> bool:
    if config.cmd_opts.cmd[0].__name__ == "current":  # type: ignore[union-attr]
        # Run command for each url only if urls are different; otherwise run once.
        _configure_and_run_migrations_online(url)
        return True
    return False


def _configure_and_run_migrations_offline(url: str) -> None:
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _configure_and_run_migrations_online(url) -> None:
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


def _get_url_from_config() -> str:
    url = config.get_main_option("sqlalchemy.url")
    return cast(str, url)


def _load_url() -> str:
    context_dict = cast(Dict, context.get_x_argument(as_dictionary=True))
    url = context_dict.get("url")
    assert url
    return url


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
