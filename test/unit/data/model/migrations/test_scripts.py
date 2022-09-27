import random

import pytest

from galaxy.model.migrations.scripts import (
    DatabaseDoesNotExistError,
    DatabaseNotInitializedError,
    LegacyManageDb,
    verify_database_is_initialized,
)


@pytest.fixture(autouse=True)
def set_db_urls(monkeypatch):
    # Do not try to access galaxy config; values not needed.
    def no_config_call(self):
        self.gxy_url = "a string"
        self.tsi_url = "a string"

    monkeypatch.setattr(LegacyManageDb, "_load_db_urls", no_config_call)


class TestLegacyManageDb:
    @pytest.mark.parametrize("arg_name", LegacyManageDb.LEGACY_CONFIG_FILE_ARG_NAMES)
    def test_rename_config_arg(self, arg_name):
        # `-c|--config|__config-file` should be renamed to `--galaxy-config`
        argv = ["caller", "--alembic-config", "path-to-alembic", arg_name, "path-to-galaxy", "upgrade", "--version=abc"]
        LegacyManageDb().rename_config_argument(argv)
        assert argv == [
            "caller",
            "--alembic-config",
            "path-to-alembic",
            "--galaxy-config",
            "path-to-galaxy",
            "upgrade",
            "--version=abc",
        ]

    def test_rename_config_arg_reordered_args(self):
        # `-c|--config|__config-file` should be renamed to `--galaxy-config`
        argv = ["caller", "--alembic-config", "path-to-alembic", "upgrade", "--version=abc", "-c", "path-to-galaxy"]
        LegacyManageDb().rename_config_argument(argv)
        assert argv == [
            "caller",
            "--alembic-config",
            "path-to-alembic",
            "upgrade",
            "--version=abc",
            "--galaxy-config",
            "path-to-galaxy",
        ]


def test_verify_database_is_init_raises_error_if_no_database():
    nonexistant_path = str(random.random())[2:]
    db_url = f"sqlite:////{nonexistant_path}"
    with pytest.raises(DatabaseDoesNotExistError):
        verify_database_is_initialized(db_url)


def test_verify_database_is_init_raises_error_if_database_not_initialized(sqlite_memory_url):
    with pytest.raises(DatabaseNotInitializedError):
        verify_database_is_initialized(sqlite_memory_url)
