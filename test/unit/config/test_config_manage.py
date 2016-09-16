
import os
import shutil
import tempfile

import yaml

from galaxy.webapps.config_manage import main

THIS_DIR = os.path.dirname(__file__)


def test_simple_reports_conversion():
    with _config_directory("1607_root_samples") as config_dir:
        config_dir.manage_cli(["convert", "reports"])
        config_dir.assert_not_exists("config/reports.ini")
        config_dir.assert_is_yaml("config/reports.yml")
        config_dir.assert_moved("config/reports.ini", "config/reports.ini.backup")


def test_simple_shed_conversion():
    with _config_directory("1607_root_samples") as config_dir:
        config_dir.manage_cli(["convert", "tool_shed"])


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

    def assert_exists(self, path):
        assert os.path.exists(os.path.join(self.temp_directory, path))

    def assert_not_exists(self, path):
        assert not os.path.exists(os.path.join(self.temp_directory, path))

    def assert_is_yaml(self, path):
        self.assert_exists(path)
        with self.open(path, "r") as f:
            return yaml.load(f)

    def open(self, path, *args):
        return open(os.path.join(self.temp_directory, path), *args)

    def assert_moved(self, from_path, to_path):
        with open(os.path.join(self.source_dir, from_path), "r") as f:
            source_contents = f.read()

        with self.open(to_path, "r") as f:
            dest_contents = f.read()

        assert source_contents == dest_contents

    def manage_cli(self, argv):
        real_argv = ["--galaxy_root", self.temp_directory]
        real_argv.extend(argv)
        main(real_argv)


def _config_directory(base_name):
    return _TestConfigDirectory(base_name)
