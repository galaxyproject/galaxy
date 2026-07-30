import os
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
CLOUD_AWS_TEST_CONFIG = """<object_store type="cloud" provider="aws">
    blah...
</object_store>
"""
CLOUD_GOOGLE_TEST_CONFIG_YAML = """
type: cloud
provider: google
other_attributes: blah
"""
CLOUD_NO_PROVIDER_TEST_CONFIG_YAML = """
type: cloud
other_attributes: blah
"""
DISTRIBUTED_WITH_CLOUD_PROVIDERS_CONFIG_YAML = """
type: distributed
backends:
   - id: files1
     type: cloud
     provider: azure
   - id: files2
     type: cloud
     provider: openstack
   - id: files3
     type: cloud
     provider: azure
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


def test_default_objectstore_needs_no_cloudbridge():
    with _config_context() as cc:
        cds = cc.get_cond_deps()
        assert not cds.check_cloudbridge()
        assert cds.extras("cloudbridge") == []


def test_cloud_objectstore_xml_installs_provider_extra():
    with _config_context() as cc:
        object_store_config = cc.write_config("objectstore.xml", CLOUD_AWS_TEST_CONFIG)
        config = {
            "object_store_config_file": object_store_config,
        }
        cds = cc.get_cond_deps(config)
        assert cds.check_cloudbridge()
        assert cds.extras("cloudbridge") == ["aws"]


def test_cloud_objectstore_google_provider_uses_gcp_extra():
    # Galaxy's provider name and cloudbridge's extra differ for Google.
    with _config_context() as cc:
        object_store_config = cc.write_config("objectstore.yml", CLOUD_GOOGLE_TEST_CONFIG_YAML)
        config = {
            "object_store_config_file": object_store_config,
        }
        cds = cc.get_cond_deps(config)
        assert cds.extras("cloudbridge") == ["gcp"]


def test_cloud_objectstore_nested_yaml_collects_every_provider():
    with _config_context() as cc:
        object_store_config = cc.write_config("objectstore.yml", DISTRIBUTED_WITH_CLOUD_PROVIDERS_CONFIG_YAML)
        config = {
            "object_store_config_file": object_store_config,
        }
        cds = cc.get_cond_deps(config)
        assert cds.check_cloudbridge()
        assert cds.extras("cloudbridge") == ["azure", "openstack"]


def test_cloud_objectstore_without_provider_installs_base_cloudbridge():
    with _config_context() as cc:
        object_store_config = cc.write_config("objectstore.yml", CLOUD_NO_PROVIDER_TEST_CONFIG_YAML)
        config = {
            "object_store_config_file": object_store_config,
        }
        cds = cc.get_cond_deps(config)
        assert cds.check_cloudbridge()
        assert cds.extras("cloudbridge") == []


def test_non_cloud_objectstore_needs_no_cloudbridge_extras():
    with _config_context() as cc:
        object_store_config = cc.write_config("objectstore.yml", AZURE_BLOB_TEST_CONFIG_YAML)
        config = {
            "object_store_config_file": object_store_config,
        }
        cds = cc.get_cond_deps(config)
        assert not cds.check_cloudbridge()
        assert cds.extras("cloudbridge") == []


def test_optional_requirements_carry_cloudbridge_extras():
    # The line handed to pip must request the provider's extra.
    with _config_context() as cc:
        object_store_config = cc.write_config("objectstore.yml", DISTRIBUTED_WITH_CLOUD_PROVIDERS_CONFIG_YAML)
        galaxy_config = cc.write_config("galaxy.yml", f"galaxy:\n  object_store_config_file: {object_store_config}\n")
        requirements = optional(galaxy_config)
        assert "cloudbridge[azure,openstack]" in requirements
        assert "cloudbridge" not in requirements


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
