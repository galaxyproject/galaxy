
import os
import shutil
import tempfile

from galaxy.webapps.config_manage import main

THIS_DIR = os.path.dirname(__file__)


def test_simple_reports_conversion():
    with _config_directory("1607_root_samples") as config_dir:
        main(["--galaxy_root", config_dir.temp_directory, "convert", "reports"])


class _TestConfigDirectory(object):

    def __init__(self, base_name):
        temp_directory = tempfile.mkdtemp()
        os.removedirs(temp_directory)
        source_dir = os.path.join(THIS_DIR, base_name)
        shutil.copytree(source_dir, temp_directory)
        self.source_dir = source_dir
        self.temp_directory = temp_directory

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        shutil.rmtree(self.temp_directory)


def _config_directory(base_name):
    return _TestConfigDirectory(base_name)
