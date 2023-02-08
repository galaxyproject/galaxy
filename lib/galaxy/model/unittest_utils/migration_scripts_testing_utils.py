import os
import subprocess
import tempfile
from typing import (
    List,
    Tuple,
)

import pytest
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine

from galaxy.model.unittest_utils.model_testing_utils import (  # noqa: F401 - url_factory is a fixture we have to import explicitly
    url_factory,
)
from galaxy.util import galaxy_directory


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


def update_config_for_staging(config_text: List[str], script_location: str, version_locations: str, dburl: str) -> None:
    """
    config_text is a list containing the text of an alembic.ini file split into lines.
    This function updates config_text in place, setting values to config options.
    """
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


def write_to_file(file_path: str, text: str) -> None:
    """Write text to file_path."""
    with open(file_path, "w") as f:
        f.write("".join(text))


def run_command(cmd: str) -> subprocess.CompletedProcess:
    """
    Run cmd as a new process.

    Example of incoming cmd: "scripts/db_dev.sh revision --message foo1".
    We need to make the path absolute, then build a sequence of args for subprocess.
    """
    cmd_as_list = cmd.split()
    cmd_path, cmd_args = cmd_as_list[0], cmd_as_list[1:]
    cmd_path = os.path.join(galaxy_directory(), cmd_path)
    args = ["sh", cmd_path] + cmd_args
    return subprocess.run(args, capture_output=True, text=True)


def get_db_heads(config: Config) -> Tuple[str, ...]:
    """Return revision ids (version heads) stored in the database."""
    dburl = config.get_main_option("sqlalchemy.url")
    engine = create_engine(dburl)
    with engine.connect() as conn:
        context = MigrationContext.configure(conn)
        heads = context.get_current_heads()
    engine.dispose()
    return heads
