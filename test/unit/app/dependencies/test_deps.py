import os
from contextlib import contextmanager
from shutil import rmtree
from tempfile import mkdtemp

from galaxy.dependencies import ConditionalDependencies

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
FILES_SOURCES_DROPBOX = """
- type: webdav
- type: dropbox
"""
JOB_CONF_YAML = """
runners:
  runner1:
    load: job_runner_A
"""
VAULT_CONF_CUSTOS = """
type: custos
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


def test_fs_default():
    with _config_context() as cc:
        cds = cc.get_cond_deps()
        assert not cds.check_fs_dropboxfs()
        assert not cds.check_fs_webdavfs()


def test_fs_configured():
    with _config_context() as cc:
        file_sources_conf = cc.write_config("file_sources.yml", FILES_SOURCES_DROPBOX)
        config = {
            "file_sources_config_file": file_sources_conf,
        }
        cds = cc.get_cond_deps(config=config)
        assert cds.check_fs_dropboxfs()
        assert cds.check_fs_webdavfs()


def test_yaml_jobconf_runners():
    with _config_context() as cc:
        job_conf_file = cc.write_config("job_conf.yml", JOB_CONF_YAML)
        config = {
            "job_config_file": job_conf_file,
        }
        cds = cc.get_cond_deps(config=config)
        assert "job_runner_A" in cds.job_runners


def test_vault_custos_configured():
    with _config_context() as cc:
        vault_conf = cc.write_config("vault_conf.yml", VAULT_CONF_CUSTOS)
        config = {
            "vault_config_file": vault_conf,
        }
        cds = cc.get_cond_deps(config=config)
        assert cds.check_custos_sdk()
        assert not cds.check_hvac()


def test_vault_hashicorp_configured():
    with _config_context() as cc:
        vault_conf = cc.write_config("vault_conf.yml", VAULT_CONF_HASHICORP)
        config = {
            "vault_config_file": vault_conf,
        }
        cds = cc.get_cond_deps(config=config)
        assert cds.check_hvac()
        assert not cds.check_custos_sdk()


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
