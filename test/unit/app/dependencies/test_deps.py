import os
from contextlib import contextmanager
from shutil import rmtree
from tempfile import mkdtemp

from galaxy.dependencies import ConditionalDependencies


AZURE_BLOB_TEST_CONFIG = """<object_store type="azure_blob">
    blah...
</object_store>
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
