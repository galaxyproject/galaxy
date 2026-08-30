import os
import re
from contextlib import contextmanager
from shutil import rmtree
from tempfile import mkdtemp

import pytest

from galaxy.dependencies import (
    ConditionalDependencies,
    optional,
)

AZURE_BLOB_TEST_CONFIG = """<object_store type="azure_blob">
    blah...
</object_store>
"""
AZURE_BLOB_TEST_CONFIG_YAML = """
type: azure_blob
other_attributes: blah
"""
DISTRIBUTED_WITH_AZURE_CONFIG_YAML = """
type: distributed
backends:
   - id: files1
     type: azure_blob
"""
FILES_SOURCES_CONFIG = """
- type: webdav
- type: dropbox
- type: googledrive
- type: irods
"""
JOB_CONF_YAML = """
runners:
  runner1:
    load: job_runner_A
"""
JOB_CONF_HTCONDOR_YAML = """
runners:
  htcondor:
    load: galaxy.jobs.runners.htcondor:HTCondorJobRunner
"""
VAULT_CONF_HASHICORP = """
type: hashicorp
"""
TOOL_SHED_CONFIG = """
tool_shed:
  sentry_dsn: https://public@sentry.example.com/1
  database_connection: postgresql://ts:ts@localhost/toolshed
  watch_tools: auto
"""


def test_default_objectstore():
    with _config_context() as cc:
        cds = cc.get_cond_deps()
        assert not cds.check_azure_storage()


def test_azure_objectstore_xml():
    with _config_context() as cc:
        object_store_config = cc.write_config("objectstore.xml", AZURE_BLOB_TEST_CONFIG)
        config = {
            "object_store_config_file": object_store_config,
        }
        cds = cc.get_cond_deps(config)
        assert cds.check_azure_storage()


def test_azure_objectstore_yaml():
    with _config_context() as cc:
        object_store_config = cc.write_config("objectstore.yml", AZURE_BLOB_TEST_CONFIG_YAML)
        config = {
            "object_store_config_file": object_store_config,
        }
        cds = cc.get_cond_deps(config)
        assert cds.check_azure_storage()


def test_azure_objectstore_nested_yaml():
    with _config_context() as cc:
        object_store_config = cc.write_config("objectstore.yml", DISTRIBUTED_WITH_AZURE_CONFIG_YAML)
        config = {
            "object_store_config_file": object_store_config,
        }
        cds = cc.get_cond_deps(config)
        assert cds.check_azure_storage()


def test_fs_default():
    with _config_context() as cc:
        cds = cc.get_cond_deps()
        assert not cds.check_gdrive_fsspec()
        assert not cds.check_dropboxdrivefs()
        assert not cds.check_webdav4()


def test_fs_configured():
    with _config_context() as cc:
        file_sources_conf = cc.write_config("file_sources.yml", FILES_SOURCES_CONFIG)
        config = {
            "file_sources_config_file": file_sources_conf,
        }
        cds = cc.get_cond_deps(config=config)
        assert cds.check_gdrive_fsspec()
        assert cds.check_dropboxdrivefs()
        assert cds.check_webdav4()
        assert cds.check_fs_irods()
        assert cds.check_mangofs()


def test_yaml_jobconf_runners():
    with _config_context() as cc:
        job_conf_file = cc.write_config("job_conf.yml", JOB_CONF_YAML)
        config = {
            "job_config_file": job_conf_file,
        }
        cds = cc.get_cond_deps(config=config)
        assert "job_runner_A" in cds.job_runners


def test_htcondor_not_required_by_default():
    with _config_context() as cc:
        cds = cc.get_cond_deps()
        assert not cds.check_htcondor()


def test_htcondor_required_when_runner_configured():
    with _config_context() as cc:
        job_conf_file = cc.write_config("job_conf.yml", JOB_CONF_HTCONDOR_YAML)
        config = {"job_config_file": job_conf_file}
        cds = cc.get_cond_deps(config=config)
        assert cds.check_htcondor()


def test_vault_hashicorp_configured():
    with _config_context() as cc:
        vault_conf = cc.write_config("vault_conf.yml", VAULT_CONF_HASHICORP)
        config = {
            "vault_config_file": vault_conf,
        }
        cds = cc.get_cond_deps(config=config)
        assert cds.check_hvac()


def test_pkce_default_disabled():
    with _config_context() as cc:
        cds = cc.get_cond_deps()
        assert cds.check_pkce() is False


def test_pkce_enabled_when_enable_oidc():
    with _config_context() as cc:
        cds = cc.get_cond_deps(config={"enable_oidc": True})
        assert cds.check_pkce() is True


def test_pkce_disabled_when_enable_oidc_off():
    with _config_context() as cc:
        cds = cc.get_cond_deps(config={"enable_oidc": False})
        assert cds.check_pkce() is False


def test_pkce_enabled_via_auth_pipeline():
    with _config_context() as cc:
        cds = cc.get_cond_deps(config={"oidc_auth_pipeline": ["galaxy.authnz.psa_authnz.verify"]})
        assert cds.check_pkce() is True


def test_pkce_enabled_via_auth_pipeline_extra():
    with _config_context() as cc:
        cds = cc.get_cond_deps(config={"oidc_auth_pipeline_extra": ["galaxy.authnz.psa_authnz.verify"]})
        assert cds.check_pkce() is True


@pytest.mark.parametrize(
    "config,expected",
    [
        (
            {
                "enable_celery_tasks": True,
            },
            False,
        ),
        (
            {
                "enable_celery_tasks": True,
                "celery_conf": {"result_backend": None},
            },
            False,
        ),
        (
            {
                "enable_celery_tasks": True,
                "celery_conf": {"broker_url": "redis://localhost:6379/0"},
            },
            True,
        ),
        (
            {
                "enable_celery_tasks": True,
                "celery_conf": {"result_backend": "redis://localhost:6379/0"},
            },
            True,
        ),
    ],
)
def test_conditional_redis(config, expected):
    with _config_context() as cc:
        cds = cc.get_cond_deps(config=config)
        assert cds.check_redis() is expected


def test_tool_shed_config_selects_dependencies():
    with _config_context() as cc:
        config_file = cc.write_config("tool_shed.yml", TOOL_SHED_CONFIG)
        assert "sentry-sdk" in _requirement_names(optional(config_file, app="tool_shed"))


def test_tool_shed_config_ignored_when_read_as_galaxy():
    with _config_context() as cc:
        config_file = cc.write_config("tool_shed.yml", TOOL_SHED_CONFIG)
        assert "sentry-sdk" not in _requirement_names(optional(config_file))


def test_tool_shed_skips_galaxy_only_dependencies():
    with _config_context() as cc:
        config_file = cc.write_config("tool_shed.yml", TOOL_SHED_CONFIG)
        names = _requirement_names(optional(config_file, app="tool_shed"))
        assert "psycopg2-binary" in names
        assert "watchdog" not in names


def test_optional_rejects_unknown_app():
    with pytest.raises(ValueError, match="Unknown app"):
        optional(app="reports")


def _requirement_names(requirements):
    return {re.split(r"[<>=!~;\[]", requirement, maxsplit=1)[0].strip() for requirement in requirements}


@contextmanager
def _config_context():
    config_dir = mkdtemp()
    try:
        yield ConfigContext(config_dir)
    finally:
        rmtree(config_dir)


class ConfigContext:
    def __init__(self, directory):
        self.tempdir = directory

    def write_config(self, path, contents):
        config_path = os.path.join(self.tempdir, path)
        with open(config_path, "w") as f:
            f.write(contents)
        return config_path

    def get_cond_deps(self, config=None):
        config = config or {}
        config_file = os.path.join(self.tempdir, "config.yml")
        return ConditionalDependencies(
            config_file,
            config=config,
        )
