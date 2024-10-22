from galaxy.files.templates import ConfiguredFileSourceTemplates
from .test_template_models import (
    LIBRARY_AWS,
    LIBRARY_HOME_DIRECTORY,
)


class MockConfig:
    def __init__(self, config_path):
        self.file_source_templates = None
        self.file_source_templates_config_file = config_path


def test_manager(tmpdir):
    config_path = tmpdir / "conf.yml"
    config_path.write_text(LIBRARY_HOME_DIRECTORY, "utf-8")
    config = MockConfig(config_path)
    templates = ConfiguredFileSourceTemplates.from_app_config(config)
    summaries = templates.summaries
    assert summaries
    assert len(summaries.root) == 1


def test_manager_throws_exception_if_vault_is_required_but_configured(tmpdir):
    config_path = tmpdir / "conf.yml"
    config_path.write_text(LIBRARY_AWS, "utf-8")
    config = MockConfig(config_path)
    exc = None
    try:
        ConfiguredFileSourceTemplates.from_app_config(config, vault_configured=False)
    except Exception as e:
        exc = e
    assert exc, "catalog creation should result in an exception"
    assert "vault must be configured" in str(exc)


def test_manager_with_secrets_is_fine_if_vault_is_required_and_configured(tmpdir):
    config_path = tmpdir / "conf.yml"
    config_path.write_text(LIBRARY_AWS, "utf-8")
    config = MockConfig(config_path)
    exc = None
    try:
        ConfiguredFileSourceTemplates.from_app_config(config, vault_configured=True)
    except Exception as e:
        exc = e
    assert exc is None


def test_manager_does_not_throw_exception_if_vault_is_not_required(tmpdir):
    config_path = tmpdir / "conf.yml"
    config_path.write_text(LIBRARY_HOME_DIRECTORY, "utf-8")
    config = MockConfig(config_path)
    exc = None
    try:
        ConfiguredFileSourceTemplates.from_app_config(config, vault_configured=False)
    except Exception as e:
        exc = e
    assert exc is None
