import os
import subprocess
import tempfile
from typing import (
    List,
    NewType,
    Tuple,
)

import alembic
import pytest
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine

from galaxy.model.unittest_utils.model_testing_utils import (  # noqa: F401 - url_factory is a fixture we have to import explicitly
    url_factory,
)
from galaxy.util import (
    galaxy_directory,
    in_packages,
)
from galaxy.util.resources import resource_path

pytestmark = pytest.mark.skipif(in_packages(), reason="Running from packages")

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


@pytest.fixture(scope="session")
def alembic_config_text(migrations_dir) -> List[str]:
    """Contents of production alembic.ini as list of lines"""
    current_config_path = migrations_dir / "alembic.ini"
    with open(current_config_path) as f:
        return f.readlines()


@pytest.fixture()
def tmp_directory():
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


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
    write_config_file(config_file_path, alembic_config_text)

    alembic_cfg = Config(config_file_path)
    create_alembic_branch(alembic_cfg, versions_dir)

    # Point tests to test database(s)
    monkeypatch.setenv("ALEMBIC_CONFIG", config_file_path)
    monkeypatch.setenv("TOOL_SHED_CONFIG_OVERRIDE_DATABASE_CONNECTION", dburl)

    return alembic_cfg


def update_config_for_staging(config_text: List[str], script_location: str, version_locations: str, dburl: str) -> None:
    """Set script_location, version_locations, sqlalchemy.url values."""
    alembic_section_index, url_set = -1, False
    url_line = f"sqlalchemy.url = {dburl}\n"
    for i, line in enumerate(config_text):
        if line.strip() == "[alembic]":
            alembic_section_index = i
        elif line.startswith("script_location ="):
            config_text[i] = f"script_location = {script_location}\n"
        elif line.startswith("version_locations ="):
            config_text[i] = f"version_locations = {version_locations}\n"
        elif line.startswith("sqlalchemy.url ="):
            config_text[i] = url_line
            url_set = True
    if not url_set:  # True when executed for the first time
        config_text.insert(alembic_section_index + 1, url_line)


def write_config_file(config_file_path: str, config_text: str) -> None:
    with open(config_file_path, "w") as f:
        f.write("".join(config_text))


def create_alembic_branch(config: Config, versions_dir: str) -> None:
    """
    Create branch (required for galaxy's alembic setup; included with 22.05 release)
    """
    alembic.command.revision(config, head="base", rev_id=BASE_ID, version_path=versions_dir)


def dburl_from_config(config: Config) -> str:
    url = config.get_main_option("sqlalchemy.url")
    assert url
    return url


def run_command(cmd: str) -> subprocess.CompletedProcess:
    # Example of incoming cmd: "scripts/db_dev.sh revision --message foo1".
    # We need to make the path absolute, then build a sequence of args for subprocess.
    cmd_as_list = cmd.split()
    cmd_path, cmd_args = cmd_as_list[0], cmd_as_list[1:]
    cmd_path = os.path.join(galaxy_directory(), cmd_path)
    args = ["sh", cmd_path] + cmd_args
    return subprocess.run(args, capture_output=True, text=True)


def get_db_heads(config: Config) -> Tuple[str, ...]:
    dburl = dburl_from_config(config)
    engine = create_engine(dburl)
    with engine.connect() as conn:
        context = MigrationContext.configure(conn)
        heads = context.get_current_heads()
    engine.dispose()
    return heads


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
