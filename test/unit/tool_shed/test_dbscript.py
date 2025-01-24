import os
from typing import NewType

import alembic
import pytest
from alembic.config import Config

from galaxy.model.unittest_utils.migration_scripts_testing_utils import (  # noqa: F401 - contains fixtures we have to import explicitly
    alembic_config_text,
    get_db_heads,
    run_command,
    tmp_directory,
    update_config_for_staging,
    write_to_file,
)
from galaxy.model.unittest_utils.model_testing_utils import (  # noqa: F401 - url_factory is a fixture we have to import explicitly
    url_factory,
)
from galaxy.util.resources import resource_path

DbUrl = NewType("DbUrl", str)

BASE_ID = "ts0"
COMMAND = "manage_toolshed_db.sh"


@pytest.fixture(scope="session")
def migrations_dir():
    """[galaxy-root]/lib/tool_shed/model/webapp/migrations/"""
    return resource_path("tool_shed.webapp.model", "migrations")


@pytest.fixture(scope="session")
def alembic_env_dir(migrations_dir) -> str:
    """[galaxy-root]/lib/tool_shed/model/webapp/migrations/alembic/"""
    return migrations_dir / "alembic"


@pytest.fixture
def config(url_factory, alembic_env_dir, alembic_config_text, tmp_directory, monkeypatch, request):  # noqa: F811
    """
    Construct Config object for staging; setup staging env.
    """
    # Create staging location for revision sctipts
    versions_dir = os.path.join(tmp_directory, "versions")
    version_locations = f"{versions_dir}"

    # Create test database(s)
    dburl = url_factory()

    # Copy production alembic.ini to staging location
    config_file_path = os.path.join(tmp_directory, "alembic.ini")
    update_config_for_staging(alembic_config_text, alembic_env_dir, version_locations, dburl)
    write_to_file(config_file_path, alembic_config_text)

    alembic_cfg = Config(config_file_path)
    create_alembic_branch(alembic_cfg, versions_dir)

    # Point tests to test database(s)
    monkeypatch.setenv("ALEMBIC_CONFIG", config_file_path)
    monkeypatch.setenv("TOOL_SHED_CONFIG_OVERRIDE_DATABASE_CONNECTION", dburl)

    return alembic_cfg


def create_alembic_branch(config: Config, versions_dir: str) -> None:
    """
    Create branch (required for galaxy's alembic setup; included with 22.05 release)
    """
    alembic.command.revision(config, head="base", rev_id=BASE_ID, version_path=versions_dir)


class TestVersionCommand:
    def test_version_cmd(self, config):
        alembic.command.revision(config, rev_id="1", head=BASE_ID)
        alembic.command.revision(config, rev_id="2", head="1")

        completed = run_command(f"{COMMAND} version")
        assert completed.returncode == 0
        assert "2 (head)" in completed.stdout

    def test_version_cmd_verbose(self, config):
        alembic.command.revision(config, rev_id="1", head=BASE_ID)
        alembic.command.revision(config, rev_id="2", head="1")

        completed = run_command(f"{COMMAND} version --verbose")
        assert completed.returncode == 0
        assert "Revision ID: 2" in completed.stdout
        assert "Revises: 1" in completed.stdout


class TestDbVersionCommand:
    def test_dbversion_cmd(self, config):
        alembic.command.revision(config, rev_id="1", head=BASE_ID)
        alembic.command.revision(config, rev_id="2", head="1")

        completed = run_command(f"{COMMAND} dbversion")
        assert completed.returncode == 0
        assert "(head)" not in completed.stdout  # there has been no upgrade

        alembic.command.upgrade(config, "heads")

        completed = run_command(f"{COMMAND} dbversion")
        assert completed.returncode == 0
        assert "2 (head)" in completed.stdout

    def test_dbversion_cmd_verbose(self, config):
        alembic.command.revision(config, rev_id="1", head=BASE_ID)
        alembic.command.revision(config, rev_id="2", head="1")

        alembic.command.upgrade(config, "heads")

        completed = run_command(f"{COMMAND} dbversion --verbose")
        assert completed.returncode == 0
        assert "Revision ID: 2" in completed.stdout
        assert "Revises: 1" in completed.stdout


class TestUpgradeCommand:
    def test_upgrade_cmd(self, config):
        alembic.command.revision(config, rev_id="1", head=BASE_ID)
        alembic.command.revision(config, rev_id="2", head="1")

        # upgrades ts to 2
        completed = run_command(f"{COMMAND} upgrade")
        assert completed.returncode == 0
        assert "Running upgrade ts0 -> 1" in completed.stderr
        assert "Running upgrade 1 -> 2" in completed.stderr

        heads = get_db_heads(config)
        assert heads == ("2",)

    def test_upgrade_cmd_sql_only(self, config):
        alembic.command.revision(config, rev_id="1", head=BASE_ID)
        alembic.command.revision(config, rev_id="2", head="1")

        completed = run_command(f"{COMMAND} upgrade --sql")
        assert completed.returncode == 0
        assert "UPDATE alembic_version SET version_num='2'" in completed.stdout
        assert "UPDATE alembic_version SET version_num='3'" not in completed.stdout

        alembic.command.revision(config, rev_id="3", head="2")

        completed = run_command(f"{COMMAND} upgrade --sql")
        assert completed.returncode == 0
        assert "UPDATE alembic_version SET version_num='2'" in completed.stdout
        assert "UPDATE alembic_version SET version_num='3'" in completed.stdout

    def test_upgrade_cmd_with_revision_arg(self, config):
        alembic.command.revision(config, rev_id="1", head=BASE_ID)
        alembic.command.revision(config, rev_id="2", head="1")

        # upgrades ts to 1
        completed = run_command(f"{COMMAND} upgrade 1")
        assert completed.returncode == 0
        assert "Running upgrade ts0 -> 1" in completed.stderr

        heads = get_db_heads(config)
        assert heads == ("1",)

    def test_upgrade_cmd_with_relative_revision_syntax(self, config):
        alembic.command.revision(config, rev_id="a", head=BASE_ID)
        alembic.command.revision(config, rev_id="b", head="a")
        alembic.command.revision(config, rev_id="c", head="b")
        alembic.command.revision(config, rev_id="d", head="c")
        alembic.command.revision(config, rev_id="e", head="d")

        # upgrades ts to b: none + 2 (none -> base -> a)
        completed = run_command(f"{COMMAND} upgrade +3")
        assert completed.returncode == 0
        assert "Running upgrade  -> ts0" in completed.stderr
        assert "Running upgrade ts0 -> a" in completed.stderr
        assert "Running upgrade a -> b" in completed.stderr

        heads = get_db_heads(config)
        assert heads == ("b",)

        # upgrades ts to d relative to b: b + 2 (b -> c -> d)
        completed = run_command(f"{COMMAND} upgrade b+2")
        assert completed.returncode == 0
        assert "Running upgrade b -> c" in completed.stderr
        assert "Running upgrade c -> d" in completed.stderr

        heads = get_db_heads(config)
        assert heads == ("d",)


class TestDowngradeCommand:
    def test_downgrade_cmd(self, config):
        alembic.command.revision(config, rev_id="1", head=BASE_ID)
        alembic.command.revision(config, rev_id="2", head="1")
        alembic.command.revision(config, rev_id="3", head="2")
        alembic.command.upgrade(config, "heads")

        completed = run_command(f"{COMMAND} downgrade 1")  # downgrade ts to 1
        assert completed.returncode == 0
        assert "Running downgrade 3 -> 2" in completed.stderr
        assert "Running downgrade 2 -> 1" in completed.stderr

        heads = get_db_heads(config)
        assert heads == ("1",)

    def test_downgrade_cmd_sql_only(self, config):
        alembic.command.revision(config, rev_id="1", head=BASE_ID)
        alembic.command.revision(config, rev_id="2", head="1")
        alembic.command.revision(config, rev_id="3", head="2")
        alembic.command.upgrade(config, "heads")

        completed = run_command(f"{COMMAND} downgrade --sql 3:1")  # downgrade ts to 1
        assert completed.returncode == 0
        assert "UPDATE alembic_version SET version_num='2'" in completed.stdout
        assert "UPDATE alembic_version SET version_num='1'" in completed.stdout

    def test_downgrade_cmd_missing_revision_arg_error(self):
        completed = run_command(f"{COMMAND} downgrade")
        assert completed.returncode == 2
        assert "the following arguments are required: revision" in completed.stderr

    def test_downgrade_cmd_with_relative_revision_syntax(self, config):
        alembic.command.revision(config, rev_id="a", head=BASE_ID)
        alembic.command.revision(config, rev_id="b", head="a")
        alembic.command.revision(config, rev_id="c", head="b")
        alembic.command.revision(config, rev_id="d", head="c")
        alembic.command.revision(config, rev_id="e", head="d")
        alembic.command.upgrade(config, "heads")

        # downgrades ts to c: e - 2 (e -> d -> c)
        completed = run_command(f"{COMMAND} downgrade -2")

        assert completed.returncode == 0
        assert "Running downgrade e -> d" in completed.stderr
        assert "Running downgrade d -> c" in completed.stderr

        heads = get_db_heads(config)
        assert heads == ("c",)

        # downgrades ts to a relative to c: c - 2 (c -> b -> a)
        completed = run_command(f"{COMMAND} downgrade c-2")
        assert completed.returncode == 0
        assert "Running downgrade c -> b" in completed.stderr
        assert "Running downgrade b -> a" in completed.stderr

        heads = get_db_heads(config)
        assert heads == ("a",)
