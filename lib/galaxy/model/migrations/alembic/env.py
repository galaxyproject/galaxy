import logging
import re
from typing import (
    Callable,
    cast,
    Dict,
)

from alembic import context
from alembic.script import ScriptDirectory
from alembic.script.base import Script
from sqlalchemy import create_engine

from galaxy.model import Base
from galaxy.model.migrations import (
    GXY,
    ModelId,
    TSI,
)

config = context.config
target_metadata = Base.metadata
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
    urls = _load_urls()

    # Special case: the `current` command has no config.cmd_opts.revision property,
    # so we check for it before checking for `upgrade/downgrade`.
    if _process_cmd_current(urls):
        return  # we're done

    try:
        revision_str = config.cmd_opts.revision  # type: ignore[union-attr]
    except AttributeError:
        revision_str = config.cmd_opts.revisions  # type: ignore[union-attr]
        if revision_str:
            if len(revision_str) > 1:
                log.error("Please run the commmand for one revision at a time")
            revision_str = revision_str[0]

    if revision_str.startswith(f"{GXY}@"):
        url = urls[GXY]
    elif revision_str.startswith(f"{TSI}@"):
        url = urls[TSI]
    else:
        revision = _get_revision(revision_str)
        if GXY in revision.branch_labels:
            url = urls[GXY]
        elif TSI in revision.branch_labels:
            url = urls[TSI]

    run_migrations(url)


def _process_cmd_current(urls: Dict[ModelId, str]) -> bool:
    if config.cmd_opts.cmd[0].__name__ == "current":  # type: ignore[union-attr]
        # Run command for each url only if urls are different; otherwise run once.
        are_urls_equal = len(set(urls.values())) == 1
        for url in urls.values():
            _configure_and_run_migrations_online(url)
            if are_urls_equal:
                break
        return True
    return False


def _get_revision(revision_str: str) -> Script:
    revision_id = _get_revision_id(revision_str)
    script_directory = ScriptDirectory.from_config(config)
    revision = script_directory.get_revision(revision_id)
    if not revision:
        raise Exception(f'Revision not found: "{revision}"')
    return revision


def _get_revision_id(revision_str: str) -> str:
    # Match a full or partial revision (GUID) or a relative migration identifier
    p = re.compile(r"([0-9A-Fa-f]+)([+-]\d)?")
    m = p.match(revision_str)
    if not m:
        raise Exception(f'Invalid revision or migration identifier: "{revision_str}"')
    return m.group(1)


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


def _load_urls() -> Dict[ModelId, str]:
    context_dict = cast(Dict, context.get_x_argument(as_dictionary=True))
    gxy_url = context_dict.get(f"{GXY}_url")
    tsi_url = context_dict.get(f"{TSI}_url")
    assert gxy_url and tsi_url
    return {
        GXY: gxy_url,
        TSI: tsi_url,
    }


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
