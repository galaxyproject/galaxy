"""
Testing approach:
- Use test database(s), store revision scripts in a different location; leave the rest unchanged.
- Use alembic api for setup and accessing the database.
- Run command as subprocess, verify captured output + database state.
"""
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
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from ..testing_utils import (  # noqa: F401  (url_factory is a fixture we have to import explicitly)
    create_and_drop_database,
    disposing_engine,
    drop_existing_database,
    url_factory,
)

DbUrl = NewType("DbUrl", str)


GXY_BRANCH_LABEL = "gxy"
TSI_BRANCH_LABEL = "tsi"
GXY_BASE_ID = "gxy0"
TSI_BASE_ID = "tsi0"

ADMIN_CMD = "./manage_db.sh"
DEV_CMD = "./scripts/db_dev.sh"
COMMANDS = [ADMIN_CMD, DEV_CMD]


@pytest.fixture(scope="session")
def alembic_env_dir() -> str:
    """[galaxy-root]/lib/galaxy/model/migrations/alembic/"""
    galaxy_root = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..")
    return os.path.join(galaxy_root, "lib", "galaxy", "model", "migrations", "alembic")


@pytest.fixture(scope="session")
def alembic_config_text(alembic_env_dir) -> List[str]:
    """Contents of production alembic.ini as list of lines"""
    current_config_path = os.path.join(alembic_env_dir, "..", "alembic.ini")
    with open(current_config_path, "r") as f:
        return f.readlines()


@pytest.fixture()
def tmp_directory():
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture(params=["one database", "two databases"])
def config(url_factory, alembic_env_dir, alembic_config_text, tmp_directory, monkeypatch, request):  # noqa: F811
    """
    Construct Config object for staging; setup staging env.
    """
    # Create staging location for revision sctipts
    gxy_versions_dir = os.path.join(tmp_directory, "versions_gxy")
    tsi_versions_dir = os.path.join(tmp_directory, "versions_tsi")
    version_locations = f"{gxy_versions_dir};{tsi_versions_dir}"

    # Create test database(s)
    gxy_dburl = url_factory()
    tsi_dburl = gxy_dburl if request.param == "one database" else url_factory()

    # Copy production alembic.ini to staging location
    config_file_path = os.path.join(tmp_directory, "alembic.ini")
    update_config_for_staging(alembic_config_text, alembic_env_dir, version_locations, gxy_dburl)
    write_config_file(config_file_path, alembic_config_text)

    alembic_cfg = Config(config_file_path)
    create_alembic_branches(alembic_cfg, gxy_versions_dir, tsi_versions_dir)

    # Point tests to test database(s)
    monkeypatch.setenv("ALEMBIC_CONFIG", config_file_path)
    monkeypatch.setenv("GALAXY_CONFIG_OVERRIDE_DATABASE_CONNECTION", gxy_dburl)
    monkeypatch.setenv("GALAXY_INSTALL_CONFIG_OVERRIDE_INSTALL_DATABASE_CONNECTION", tsi_dburl)

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


def create_alembic_branches(config: Config, gxy_versions_dir: str, tsi_versions_dir: str) -> None:
    """
    Create gxy and tsi branches (required for galaxy's alembic setup; included with 22.05 release)
    """
    alembic.command.revision(
        config, branch_label=GXY_BRANCH_LABEL, head="base", rev_id=GXY_BASE_ID, version_path=gxy_versions_dir
    )
    alembic.command.revision(
        config, branch_label=TSI_BRANCH_LABEL, head="base", rev_id=TSI_BASE_ID, version_path=tsi_versions_dir
    )


def dburl_from_config(config: Config) -> str:
    url = config.get_main_option("sqlalchemy.url")
    assert url
    return url


def run_command(cmd: str) -> subprocess.CompletedProcess:
    if in_packages():
        cmd = f"../.{cmd}"  # if this is run from `packages`, manage_db.sh is in parent directory

    completed_process = subprocess.run(cmd.split(), capture_output=True, text=True)

    return completed_process


def in_packages() -> bool:
    """Checks if test is run from the packages directory."""
    path = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, os.pardir, os.pardir)
    path = os.path.normpath(path)
    return os.path.split(path)[1] == "packages"


def get_db_heads(config: Config) -> Tuple[str, ...]:
    dburl = dburl_from_config(config)
    engine = create_engine(dburl)
    with engine.connect() as conn:
        context = MigrationContext.configure(conn)
        heads = context.get_current_heads()
    engine.dispose()
    return heads


class TestRevisionCommand:
    def test_revision_cmd(self, config):
        run_command(f"{DEV_CMD} revision --message foo1")
        run_command(f"{DEV_CMD} revision --rev-id 2 --message foo2")
        run_command(f"{DEV_CMD} revision --rev-id 3 --message foo3")

        script_dir = ScriptDirectory.from_config(config)
        revisions = [rev for rev in script_dir.walk_revisions()]
        assert len(revisions) == 5  # verify total revisions: 2 base + 3 new

        rev = script_dir.get_revision("3")
        assert rev
        assert GXY_BRANCH_LABEL in rev.branch_labels  # verify branch label
        assert rev.down_revision == "2"  # verify parent revision
        assert rev.module.__name__ == "3_foo3_py"  # verify message

    def test_revision_cmd_missing_message_arg_error(self):
        completed = run_command(f"{DEV_CMD} revision --rev-id 1")
        assert completed.returncode == 2
        assert "the following arguments are required: -m/--message" in completed.stderr


class TestShowCommand:
    def test_show_cmd(self, config):
        alembic.command.revision(config, rev_id="42", head=GXY_BASE_ID)
        completed = run_command(f"{DEV_CMD} show 42")
        assert "Revision ID: 42" in completed.stdout

    def test_show_cmd_invalid_revision_error(self, config):
        alembic.command.revision(config, rev_id="42", head=GXY_BASE_ID)
        completed = run_command(f"{DEV_CMD} show idonotexist")
        assert completed.returncode == 1
        assert "Traceback" not in completed.stderr
        assert "Can't locate revision identified by 'idonotexist'" in completed.stderr

    def test_show_cmd_invalid_revision_error_with_traceback(self):
        completed = run_command(f"{DEV_CMD} --raiseerr show idonotexist")
        assert completed.returncode == 1
        assert "Traceback" in completed.stderr
        assert "Can't locate revision identified by 'idonotexist'" in completed.stderr

    def test_show_cmd_missing_revision_arg_error(self):
        completed = run_command(f"{DEV_CMD} show")
        assert completed.returncode == 2
        assert "the following arguments are required: revision" in completed.stderr


class TestHistoryCommand:
    def test_history_cmd(self, config):
        alembic.command.revision(config, rev_id="1", head=GXY_BASE_ID)
        alembic.command.revision(config, rev_id="2", head="1")
        alembic.command.revision(config, rev_id="3", head="2")

        completed = run_command(f"{DEV_CMD} history")
        assert completed.returncode == 0
        assert "2 -> 3 (gxy) (head), empty message" in completed.stdout
        assert "1 -> 2 (gxy)" in completed.stdout
        assert "gxy0 -> 1 (gxy)" in completed.stdout

    def test_history_cmd_verbose(self, config):
        alembic.command.revision(config, rev_id="1", head=GXY_BASE_ID)
        alembic.command.revision(config, rev_id="2", head="1")
        alembic.command.revision(config, rev_id="3", head="2")

        completed = run_command(f"{DEV_CMD} history --verbose")
        assert "Revision ID: 2" in completed.stdout
        assert "Revises: 1" in completed.stdout

    def test_history_cmd_indicate_current(self, config):
        alembic.command.revision(config, rev_id="1", head=GXY_BASE_ID)
        alembic.command.revision(config, rev_id="2", head="1")
        alembic.command.revision(config, rev_id="3", head="2")
        alembic.command.upgrade(config, "heads")

        completed = run_command(f"{DEV_CMD} history --indicate-current")
        assert completed.returncode == 0
        assert "2 -> 3 (gxy) (head) (current), empty message" in completed.stdout
        assert "1 -> 2 (gxy)" in completed.stdout
        assert "gxy0 -> 1 (gxy)" in completed.stdout


@pytest.mark.parametrize("command", COMMANDS)
class TestVersionCommand:
    def test_version_cmd(self, config, command):
        alembic.command.revision(config, rev_id="1", head=GXY_BASE_ID)
        alembic.command.revision(config, rev_id="2", head="1")

        completed = run_command(f"{command} version")
        assert completed.returncode == 0
        assert "2 (gxy) (head)" in completed.stdout

    def test_version_cmd_verbose(self, config, command):
        alembic.command.revision(config, rev_id="1", head=GXY_BASE_ID)
        alembic.command.revision(config, rev_id="2", head="1")

        completed = run_command(f"{command} version --verbose")
        assert completed.returncode == 0
        assert "Revision ID: 2" in completed.stdout
        assert "Revises: 1" in completed.stdout


@pytest.mark.parametrize("command", COMMANDS)
class TestDbVersionCommand:
    def test_dbversion_cmd(self, config, command):
        alembic.command.revision(config, rev_id="1", head=GXY_BASE_ID)
        alembic.command.revision(config, rev_id="2", head="1")

        completed = run_command(f"{command} dbversion")
        assert completed.returncode == 0
        assert "(head)" not in completed.stdout  # there has been no upgrade

        alembic.command.upgrade(config, "heads")

        completed = run_command(f"{command} dbversion")
        assert completed.returncode == 0
        assert "2 (head)" in completed.stdout

    def test_dbversion_cmd_verbose(self, config, command):
        alembic.command.revision(config, rev_id="1", head=GXY_BASE_ID)
        alembic.command.revision(config, rev_id="2", head="1")

        alembic.command.upgrade(config, "heads")

        completed = run_command(f"{command} dbversion --verbose")
        assert completed.returncode == 0
        assert "Revision ID: 2" in completed.stdout
        assert "Revises: 1" in completed.stdout


@pytest.mark.parametrize("command", COMMANDS)
class TestUpgradeCommand:
    def test_upgrade_cmd(self, config, command):
        alembic.command.revision(config, rev_id="1", head=GXY_BASE_ID)
        alembic.command.revision(config, rev_id="2", head="1")

        # first upgrade: upgrades gxy to 2, tsi to base
        completed = run_command(f"{command} upgrade")
        assert completed.returncode == 0
        assert "Running upgrade gxy0 -> 1" in completed.stderr
        assert "Running upgrade 1 -> 2" in completed.stderr
        assert "Running upgrade  -> tsi0" in completed.stderr

        heads = get_db_heads(config)
        assert "2" in heads

        alembic.command.revision(config, rev_id="3", head="2")

        # next upgrade: upgrades gxy to 3
        completed = run_command(f"{command} upgrade")
        assert completed.returncode == 0
        assert "Running upgrade 2 -> 3" in completed.stderr
        assert "tsi0" not in completed.stderr  # no effect on tsi

        heads = get_db_heads(config)
        assert "3" in heads

    def test_upgrade_cmd_sql_only(self, config, command):
        alembic.command.revision(config, rev_id="1", head=GXY_BASE_ID)
        alembic.command.revision(config, rev_id="2", head="1")

        completed = run_command(f"{command} upgrade --sql")
        assert completed.returncode == 0
        assert "UPDATE alembic_version SET version_num='2'" in completed.stdout
        assert "UPDATE alembic_version SET version_num='3'" not in completed.stdout

        alembic.command.revision(config, rev_id="3", head="2")

        completed = run_command(f"{command} upgrade --sql")
        assert completed.returncode == 0
        assert "UPDATE alembic_version SET version_num='2'" in completed.stdout
        assert "UPDATE alembic_version SET version_num='3'" in completed.stdout

    def test_upgrade_cmd_with_revision_arg(self, config, command):
        alembic.command.revision(config, rev_id="1", head=GXY_BASE_ID)
        alembic.command.revision(config, rev_id="2", head="1")

        # upgrades gxy to 1
        completed = run_command(f"{command} upgrade 1")
        assert completed.returncode == 0
        assert "Running upgrade gxy0 -> 1" in completed.stderr

        heads = get_db_heads(config)
        assert heads == ("1",)

    def test_upgrade_cmd_with_relative_revision_syntax(self, config, command):
        alembic.command.revision(config, rev_id="a", head=GXY_BASE_ID)
        alembic.command.revision(config, rev_id="b", head="a")
        alembic.command.revision(config, rev_id="c", head="b")
        alembic.command.revision(config, rev_id="d", head="c")
        alembic.command.revision(config, rev_id="e", head="d")

        # upgrades gxy to b: none + 2 (none -> base -> a)
        completed = run_command(f"{command} upgrade +3")
        assert completed.returncode == 0
        assert "Running upgrade  -> gxy0" in completed.stderr
        assert "Running upgrade gxy0 -> a" in completed.stderr
        assert "Running upgrade a -> b" in completed.stderr

        heads = get_db_heads(config)
        assert heads == ("b",)

        # upgrades gxy to d relative to b: b + 2 (b -> c -> d)
        completed = run_command(f"{command} upgrade b+2")
        assert completed.returncode == 0
        assert "Running upgrade b -> c" in completed.stderr
        assert "Running upgrade c -> d" in completed.stderr

        heads = get_db_heads(config)
        assert heads == ("d",)


@pytest.mark.parametrize("command", COMMANDS)
class TestDowngradeCommand:
    def test_downgrade_cmd(self, config, command):
        alembic.command.revision(config, rev_id="1", head=GXY_BASE_ID)
        alembic.command.revision(config, rev_id="2", head="1")
        alembic.command.revision(config, rev_id="3", head="2")
        alembic.command.upgrade(config, "heads")

        completed = run_command(f"{command} downgrade 1")  # downgrade gxy to 1
        assert completed.returncode == 0
        assert "Running downgrade 3 -> 2" in completed.stderr
        assert "Running downgrade 2 -> 1" in completed.stderr

        heads = get_db_heads(config)
        assert len(heads) == 2
        assert "1" in heads

    def test_downgrade_cmd_sql_only(self, config, command):
        alembic.command.revision(config, rev_id="1", head=GXY_BASE_ID)
        alembic.command.revision(config, rev_id="2", head="1")
        alembic.command.revision(config, rev_id="3", head="2")
        alembic.command.upgrade(config, "heads")

        completed = run_command(f"{command} downgrade --sql 3:1")  # downgrade gxy to 1, no effect on tsi
        assert completed.returncode == 0
        assert "UPDATE alembic_version SET version_num='2'" in completed.stdout
        assert "UPDATE alembic_version SET version_num='1'" in completed.stdout

    def test_downgrade_cmd_missing_revision_arg_error(self, command):
        completed = run_command(f"{command} downgrade")
        assert completed.returncode == 2
        assert "the following arguments are required: revision" in completed.stderr

    def test_downgrade_cmd_with_relative_revision_syntax(self, config, command):
        alembic.command.revision(config, rev_id="a", head=GXY_BASE_ID)
        alembic.command.revision(config, rev_id="b", head="a")
        alembic.command.revision(config, rev_id="c", head="b")
        alembic.command.revision(config, rev_id="d", head="c")
        alembic.command.revision(config, rev_id="e", head="d")
        alembic.command.upgrade(config, "heads")

        # downgrades gxy to c: e - 2 (e -> d -> c)
        completed = run_command(f"{command} downgrade -2")

        assert completed.returncode == 0
        assert "Running downgrade e -> d" in completed.stderr
        assert "Running downgrade d -> c" in completed.stderr

        heads = get_db_heads(config)
        assert "c" in heads

        # downgrades gxy to a relative to c: c - 2 (c -> b -> a)
        completed = run_command(f"{command} downgrade c-2")
        assert completed.returncode == 0
        assert "Running downgrade c -> b" in completed.stderr
        assert "Running downgrade b -> a" in completed.stderr

        heads = get_db_heads(config)
        assert "a" in heads
