import pytest

from galaxy.model.migrations.scripts import LegacyScripts


class TestLegacyScripts():

    def test_pop_database_name__pop_and_return(self):
        arg_value = 'install'
        argv = ['caller', '--alembic-config', 'path-to-alembic', 'upgrade', '--version=abc', arg_value]
        database = LegacyScripts().pop_database_argument(argv)
        assert database == arg_value
        assert argv == ['caller', '--alembic-config', 'path-to-alembic', 'upgrade', '--version=abc']

    def test_pop_database_name__pop_and_return_default(self):
        arg_value = 'galaxy'
        argv = ['caller', '--alembic-config', 'path-to-alembic', 'upgrade', '--version=abc', arg_value]
        database = LegacyScripts().pop_database_argument(argv)
        assert database == arg_value
        assert argv == ['caller', '--alembic-config', 'path-to-alembic', 'upgrade', '--version=abc']

    def test_pop_database_name__return_default(self):
        argv = ['caller', '--alembic-config', 'path-to-alembic', 'upgrade', '--version=abc']
        database = LegacyScripts().pop_database_argument(argv)
        assert database == 'galaxy'
        assert argv == ['caller', '--alembic-config', 'path-to-alembic', 'upgrade', '--version=abc']

    @pytest.mark.parametrize('arg_name', LegacyScripts.LEGACY_CONFIG_FILE_ARG_NAMES)
    def test_rename_config_arg(self, arg_name):
        # `-c|--config|__config-file` should be renamed to `--galaxy-config`
        argv = ['caller', '--alembic-config', 'path-to-alembic', arg_name, 'path-to-galaxy', 'upgrade', '--version=abc']
        LegacyScripts().rename_config_argument(argv)
        assert argv == ['caller', '--alembic-config', 'path-to-alembic', '--galaxy-config', 'path-to-galaxy', 'upgrade', '--version=abc']

    def test_rename_config_arg_reordered_args(self):
        # `-c|--config|__config-file` should be renamed to `--galaxy-config`
        argv = ['caller', '--alembic-config', 'path-to-alembic', 'upgrade', '--version=abc', '-c', 'path-to-galaxy']
        LegacyScripts().rename_config_argument(argv)
        assert argv == ['caller', '--alembic-config', 'path-to-alembic', 'upgrade', '--version=abc', '--galaxy-config', 'path-to-galaxy']

    def test_rename_alembic_config_arg(self):
        # `--alembic-config` should be renamed to `-c`
        argv = ['caller', '--alembic-config', 'path-to-alembic', 'upgrade', '--version=abc']
        LegacyScripts().rename_alembic_config_argument(argv)
        assert argv == ['caller', '-c', 'path-to-alembic', 'upgrade', '--version=abc']

    def test_rename_alembic_config_arg_raises_error_if_c_arg_present(self):
        # Ensure alembic config arg is renamed AFTER renaming the galaxy config arg. Raise error otherwise.
        argv = ['caller', '--alembic-config', 'path-to-alembic', '-c', 'path-to-galaxy', 'upgrade', '--version=abc']
        with pytest.raises(Exception):
            LegacyScripts().rename_alembic_config_argument(argv)

    def test_convert_version_argument_1(self):
        # `--version foo` should be converted to `foo`
        argv = ['caller', '-c', 'path-to-alembic', 'upgrade', '--version', 'abc']
        LegacyScripts().convert_version_argument(argv, 'galaxy')
        assert argv == ['caller', '-c', 'path-to-alembic', 'upgrade', 'abc']

    def test_convert_version_argument_2(self):
        # `--version=foo` should be converted to `foo`
        argv = ['caller', '-c', 'path-to-alembic', 'upgrade', '--version=abc']
        LegacyScripts().convert_version_argument(argv, 'galaxy')
        assert argv == ['caller', '-c', 'path-to-alembic', 'upgrade', 'abc']

    def test_no_version_argument(self):
        # No version should be converted to `X@head` where `X` is either gxy or tsi, depending on the target database.
        database = 'galaxy'
        argv = ['caller', '-c', 'path-to-alembic', 'upgrade']
        LegacyScripts().convert_version_argument(argv, database)
        assert argv == ['caller', '-c', 'path-to-alembic', 'upgrade', 'gxy@head']

        database = 'install'
        argv = ['caller', '-c', 'path-to-alembic', 'upgrade']
        LegacyScripts().convert_version_argument(argv, database)
        assert argv == ['caller', '-c', 'path-to-alembic', 'upgrade', 'tsi@head']

    def test_downgrade_with_no_version_argument_raises_error(self):
        database = 'galaxy'
        argv = ['caller', '-c', 'path-to-alembic', 'downgrade']
        with pytest.raises(Exception):
            LegacyScripts().convert_version_argument(argv, database)
