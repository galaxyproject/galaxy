import pytest

from galaxy.model.migrations.scripts import (
    LegacyScripts,
    LegacyScriptsException,
)


@pytest.fixture(autouse=True)
def set_db_urls(monkeypatch):
    # Do not try to access galaxy config; values not needed.
    def no_config_call(self):
        self.gxy_url = "a string"
        self.tsi_url = "a stirng"

    monkeypatch.setattr(LegacyScripts, "_get_db_urls", no_config_call)


@pytest.fixture(autouse=True)  # set combined db for all tests
def set_combined(monkeypatch):
    monkeypatch.setattr(LegacyScripts, "_is_one_database", lambda self: True)


@pytest.fixture
def set_separate(monkeypatch):
    monkeypatch.setattr(LegacyScripts, "_is_one_database", lambda self: False)


class TestLegacyScripts:
    @pytest.mark.parametrize("database_arg", ["galaxy", "install"])
    def test_pop_database_name(self, database_arg):
        #    arg_value = 'install'
        argv = ["caller", "--alembic-config", "path-to-alembic", "upgrade", "--version=abc", database_arg]
        ls = LegacyScripts(argv)

        ls.pop_database_argument()
        assert ls.database == database_arg
        assert argv == ["caller", "--alembic-config", "path-to-alembic", "upgrade", "--version=abc"]

    def test_pop_database_name_use_default(self):
        argv = ["caller", "--alembic-config", "path-to-alembic", "upgrade", "--version=abc"]
        ls = LegacyScripts(argv)
        ls.pop_database_argument()
        assert ls.database == LegacyScripts.DEFAULT_DB_ARG
        assert argv == ["caller", "--alembic-config", "path-to-alembic", "upgrade", "--version=abc"]

    @pytest.mark.parametrize("arg_name", LegacyScripts.LEGACY_CONFIG_FILE_ARG_NAMES)
    def test_rename_config_arg(self, arg_name):
        # `-c|--config|__config-file` should be renamed to `--galaxy-config`
        argv = ["caller", "--alembic-config", "path-to-alembic", arg_name, "path-to-galaxy", "upgrade", "--version=abc"]
        LegacyScripts(argv).rename_config_argument()
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
        LegacyScripts(argv).rename_config_argument()
        assert argv == [
            "caller",
            "--alembic-config",
            "path-to-alembic",
            "upgrade",
            "--version=abc",
            "--galaxy-config",
            "path-to-galaxy",
        ]

    def test_rename_alembic_config_arg(self):
        # `--alembic-config` should be renamed to `-c`
        argv = ["caller", "--alembic-config", "path-to-alembic", "upgrade", "--version=abc"]
        LegacyScripts(argv).rename_alembic_config_argument()
        assert argv == ["caller", "-c", "path-to-alembic", "upgrade", "--version=abc"]

    def test_rename_alembic_config_arg_raises_error_if_c_arg_present(self):
        # Ensure alembic config arg is renamed AFTER renaming the galaxy config arg. Raise error otherwise.
        argv = ["caller", "--alembic-config", "path-to-alembic", "-c", "path-to-galaxy", "upgrade", "--version=abc"]
        with pytest.raises(LegacyScriptsException):
            LegacyScripts(argv).rename_alembic_config_argument()

    def test_convert__version_arg_1(self):
        # `sh manage_db.sh upgrade --version X`  >> `... upgrade X`
        argv = ["caller", "--alembic-config", "path-to-alembic", "upgrade", "--version", "abc"]
        LegacyScripts(argv).convert_args()
        assert argv == ["caller", "-c", "path-to-alembic", "upgrade", "abc"]

    def test_convert__version_arg_2(self):
        # `sh manage_db.sh upgrade --version=X`  >> `... upgrade X`
        argv = ["caller", "--alembic-config", "path-to-alembic", "upgrade", "--version=abc"]
        LegacyScripts(argv).convert_args()
        assert argv == ["caller", "-c", "path-to-alembic", "upgrade", "abc"]

    def test_convert__no_version_no_model_combined_database(self):
        # `sh manage_db.sh upgrade`  >> `... upgrade heads`
        # No version and no model implies "upgrade the default db (which is galaxy) to its latest version".
        # If it is combined, we upgrade both models: gxy and tsi.
        argv = ["caller", "--alembic-config", "path-to-alembic", "upgrade"]
        LegacyScripts(argv).convert_args()
        assert argv == ["caller", "-c", "path-to-alembic", "upgrade", "heads"]

    def test_convert__no_version_galaxy_model_combined_database_(self):
        # `sh manage_db.sh upgrade galaxy`  >> `... upgrade heads`
        # same as no model: if combined we upgrade the whole database
        argv = ["caller", "--alembic-config", "path-to-alembic", "upgrade", "galaxy"]
        LegacyScripts(argv).convert_args()
        assert argv == ["caller", "-c", "path-to-alembic", "upgrade", "heads"]

    def test_convert__no_version_install_model_combined_database_(self):
        # `sh manage_db.sh upgrade install`  >> `... upgrade heads`
        # same as no model: if combined we upgrade the whole database
        argv = ["caller", "--alembic-config", "path-to-alembic", "upgrade", "install"]
        LegacyScripts(argv).convert_args()
        assert argv == ["caller", "-c", "path-to-alembic", "upgrade", "heads"]

    def test_convert__no_version_no_model_separate_databases(self, set_separate):
        # `sh manage_db.sh upgrade`  >> `... upgrade gxy@head`
        # No version and no model implies "upgrade the default db (which is galaxy) to its latest version".
        # Since the tsi model has its own db, we only upgrade the gxy model.
        argv = ["caller", "--alembic-config", "path-to-alembic", "upgrade"]
        LegacyScripts(argv).convert_args()
        assert argv == ["caller", "-c", "path-to-alembic", "upgrade", "gxy@head"]

    def test_convert__no_version_galaxy_model_separate_databases(self, set_separate):
        # `sh manage_db.sh upgrade galaxy`  >> `... upgrade gxy@head`
        # No version + a model implies "upgrade the db for the specified model to its latest version".
        argv = ["caller", "--alembic-config", "path-to-alembic", "upgrade", "galaxy"]
        LegacyScripts(argv).convert_args()
        assert argv == ["caller", "-c", "path-to-alembic", "upgrade", "gxy@head"]

    def test_convert__no_version_install_model_separate_databases(self, set_separate):
        # `sh manage_db.sh upgrade install`  >> `... upgrade tsi@head`
        # No version + a model implies "upgrade the db for the specified model to its latest version".
        argv = ["caller", "--alembic-config", "path-to-alembic", "upgrade", "install"]
        LegacyScripts(argv).convert_args()
        assert argv == ["caller", "-c", "path-to-alembic", "upgrade", "tsi@head"]

    def test_downgrade_with_no_version_argument_raises_error(self):
        argv = ["caller", "--alembic-config", "path-to-alembic", "downgrade"]
        with pytest.raises(LegacyScriptsException):
            LegacyScripts(argv).convert_args()
