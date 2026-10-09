import pytest

from galaxy.model.database_utils import is_postgres
from galaxy.model.migrations import AlembicManager
from galaxy.model.unittest_utils.migration_scripts_testing_utils import (  # noqa: F401 - contains fixtures we have to import explicitly
    run_command,
    tmp_directory,
)
from galaxy.model.unittest_utils.model_testing_utils import (  # noqa: F401 - url_factory is a fixture we have to import explicitly
    create_and_drop_database,
    disposing_engine,
    sqlite_url_factory,
    url_factory,
)


@pytest.fixture(params=["sqlite", "postgres"])
def dburl(request, url_factory, sqlite_url_factory):  # noqa: F811
    if request.param == "sqlite":
        return sqlite_url_factory()
    else:
        dburl = url_factory()
        if is_postgres(dburl):
            return dburl


def test_migrations(dburl, monkeypatch):
    """
    Verify that database migration revision scripts can be applied in the following sequence:
        1. `init` (initialize a new database from model definition)
        2. `downgrade base` (downgrade to pre-alembic state)
        3. `upgrade` (upgrade to up-to-date after downgrading)
        4. `downgrade base` (downgrade to pre-alembic state after upgradingx)
    Note that step "2" is not the same as step "4": the state of the database preceeding "2" is a result of
    initializing it from the model definition; the state of the database in "3" is a a result of running
    all the revision scripts in sequence from base to the current head (up-to-date state).

    If a postgresql connection is available, this text will be executed twice: against sqlite and postgresql.
    Otherwise, the test will run once against a sqlite database.
    The database is created and destroyed within the scope of this test function.
    """
    if not dburl:
        # If a postgresql url is not available, dburl will be None on the second run of the test.
        return

    command = "manage_db.sh"
    monkeypatch.setenv("GALAXY_CONFIG_OVERRIDE_DATABASE_CONNECTION", dburl)
    monkeypatch.setenv("GALAXY_INSTALL_CONFIG_OVERRIDE_INSTALL_DATABASE_CONNECTION", dburl)

    with create_and_drop_database(dburl), disposing_engine(dburl) as engine:
        # Step 1. Initialize database from model definition.
        completed = run_command(f"{command} init")
        assert completed.returncode == 0
        assert "Running stamp_revision" in completed.stderr
        dbversion_after_init = _get_database_version(engine)
        assert dbversion_after_init

        # Running `upgrade` next would be a noop, since the `init` command "stamps"
        # the alembic_version table with the latest revision.
        # Step 2. Downgrade to base (verify downgrading runs without errors)
        completed = run_command(f"{command} downgrade base")
        assert completed.returncode == 0
        assert "Running downgrade" in completed.stderr
        assert not _get_database_version(engine)

        # Step 3. Upgrade to current head (verify upgrading runs without errors)
        completed = run_command(f"{command} upgrade")
        assert completed.returncode == 0
        assert "Running upgrade" in completed.stderr
        dbversion_after_upgrade = _get_database_version(engine)
        assert dbversion_after_upgrade == dbversion_after_init

        # Step 4. Downgrade to base (verify downgrading after upgrading runs without errors)
        completed = run_command(f"{command} downgrade base")
        assert completed.returncode == 0
        assert "Running downgrade" in completed.stderr
        assert not _get_database_version(engine)


def _get_database_version(engine):
    alembic_manager = AlembicManager(engine)
    return alembic_manager.db_heads
