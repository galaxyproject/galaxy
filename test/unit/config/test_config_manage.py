
import os
import shutil
import tempfile

import yaml

from galaxy.webapps.config_manage import main

THIS_DIR = os.path.dirname(__file__)


def test_reports_conversion_1607_sample():
    with _config_directory("1607_root_samples") as config_dir:
        config_dir.manage_cli(["convert", "reports"])
        config_dir.assert_not_exists("config/reports.ini")
        config_dir.assert_is_yaml("config/reports.yml")
        config_dir.assert_moved("config/reports.ini", "config/reports.ini.backup")
        with config_dir.open("config/reports.yml") as f:
            config = yaml.load(f)
        assert "reports" in config
        reports_config = config["reports"] or {}
        assert "use_beaker_session" not in reports_config

        assert "uwsgi" in config
        uwsgi_config = config["uwsgi"]
        assert uwsgi_config["module"] == "galaxy.webapps.reports.buildapp:uwsgi_app()"


def test_reports_build_sample():
    with _config_directory("1607_root_samples") as config_dir:
        config_dir.assert_not_exists("config/reports.yml.sample")
        config_dir.manage_cli(["build_sample_yaml", "reports", "--add-comments"])
        config_dir.assert_is_yaml("config/reports.yml.sample")


def test_shed_conversion_1607_sample():
    with _config_directory("1607_root_samples") as config_dir:
        config_dir.manage_cli(["convert", "tool_shed"])
        config_dir.assert_not_exists("config/tool_shed.ini")
        config_dir.assert_is_yaml("config/tool_shed.yml")
        config_dir.assert_moved("config/tool_shed.ini", "config/tool_shed.ini.backup")


def test_shed_build_sample():
    with _config_directory("1607_root_samples") as config_dir:
        config_dir.assert_not_exists("config/tool_shed.yml.sample")
        config_dir.manage_cli(["build_sample_yaml", "tool_shed", "--add-comments"])
        config_dir.assert_is_yaml("config/tool_shed.yml.sample")


def test_shed_conversion_1607_prefix():
    with _config_directory("1607_root_filters") as config_dir:
        config_dir.manage_cli(["convert", "tool_shed"])
        config_dir.assert_not_exists("config/tool_shed.ini")
        config_dir.assert_is_yaml("config/tool_shed.yml")
        config_dir.assert_moved("config/tool_shed.ini", "config/tool_shed.ini.backup")
        with config_dir.open("config/tool_shed.yml") as f:
            config = yaml.load(f)
        assert "uwsgi" in config
        uwsgi_config = config["uwsgi"]
        assert "module" not in uwsgi_config
        assert uwsgi_config["mount"].startswith("/shed=galaxy.")


def test_allow_library_path_paste_conversion():
    with _config_directory("1705_allow_path_paste") as config_dir:
        config_dir.manage_cli(["convert", "galaxy"])
        config_dir.assert_not_exists("config/galaxy.ini")
        config_dir.assert_is_yaml("config/galaxy.yml")
        config_dir.assert_moved("config/galaxy.ini", "config/galaxy.ini.backup")
        with config_dir.open("config/galaxy.yml") as f:
            config = yaml.load(f)
        assert "galaxy" in config
        galaxy_config = config["galaxy"]
        assert galaxy_config["allow_path_paste"] is True


def test_build_uwsgi_yaml():
    with _config_directory("1607_root_samples") as config_dir:
        config_dir.manage_cli(["build_uwsgi_yaml"])


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
