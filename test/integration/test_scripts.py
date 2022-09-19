"""Integration tests for various scripts in scripts/.
"""

import json
import os
import subprocess
import tempfile
import unittest

import yaml

from galaxy.util import (
    galaxy_directory,
    unicodify,
)
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util


def skip_unless_module(module):
    available = True
    try:
        __import__(module)
    except ImportError:
        available = False
    if available:
        return lambda func: func
    template = "Module %s could not be loaded, dependent test skipped."
    return unittest.skip(template % module)


class ScriptsIntegrationTestCase(integration_util.IntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.config_dir = tempfile.mkdtemp()

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls._raw_config = config

    def test_helper(self):
        script = "helper.py"
        self._scripts_check_argparse_help(script)

        history_id = self.dataset_populator.new_history()
        dataset = self.dataset_populator.new_dataset(history_id, wait=True)
        dataset_id = dataset["id"]
        config_file = self.write_config_file()
        output = self._scripts_check_output(script, ["-c", config_file, "--decode-id", dataset_id])
        assert "Decoded " in output

    def test_cleanup(self):
        script = "cleanup_datasets/cleanup_datasets.py"
        self._scripts_check_argparse_help(script)

        history_id = self.dataset_populator.new_history()
        delete_response = self.dataset_populator._delete("histories/%s" % history_id)
        assert delete_response.status_code == 200
        assert delete_response.json()["purged"] is False
        config_file = self.write_config_file()
        output = self._scripts_check_output(script, ["-c", config_file, "--days", "0", "--purge_histories"])
        print(output)
        history_response = self.dataset_populator._get("histories/%s" % history_id)
        assert history_response.status_code == 200
        assert history_response.json()["purged"] is True, history_response.json()

    def test_pgcleanup(self):
        self._skip_unless_postgres()

        script = "cleanup_datasets/pgcleanup.py"
        self._scripts_check_argparse_help(script)

        history_id = self.dataset_populator.new_history()
        delete_response = self.dataset_populator._delete("histories/%s" % history_id)
        assert delete_response.status_code == 200
        assert delete_response.json()["purged"] is False
        config_file = self.write_config_file()
        output = self._scripts_check_output(
            script, ["-c", config_file, "--older-than", "0", "--sequence", "purge_deleted_histories"]
        )
        print(output)
        history_response = self.dataset_populator._get("histories/%s" % history_id)
        assert history_response.status_code == 200
        assert history_response.json()["purged"] is True, history_response.json()

    def test_set_user_disk_usage(self):
        script = "set_user_disk_usage.py"
        self._scripts_check_argparse_help(script)

        history_id = self.dataset_populator.new_history()
        self.dataset_populator.new_dataset(history_id, wait=True)
        config_file = self.write_config_file()
        output = self._scripts_check_output(script, ["-c", config_file])
        # verify the script runs to completion without crashing
        assert "100% complete" in output, output

    def test_set_dataset_sizes(self):
        script = "set_dataset_sizes.py"
        self._scripts_check_argparse_help(script)

        # TODO: change the size of the dataset and verify this works.
        history_id = self.dataset_populator.new_history()
        self.dataset_populator.new_dataset(history_id, wait=True)
        config_file = self.write_config_file()
        output = self._scripts_check_output(script, ["-c", config_file])
        # verify the script runs to completion without crashing
        assert "Completed 100%" in output, output

    def test_populate_uuid(self):
        script = "cleanup_datasets/populate_uuid.py"
        self._scripts_check_argparse_help(script)

        history_id = self.dataset_populator.new_history()
        self.dataset_populator.new_dataset(history_id, wait=True)
        config_file = self.write_config_file()
        output = self._scripts_check_output(script, ["-c", config_file])
        assert "Complete" in output

    def test_grt_export(self):
        script = "grt/export.py"
        self._scripts_check_argparse_help(script)

        history_id = self.dataset_populator.new_history()
        self.dataset_populator.new_dataset(history_id, wait=True)
        config_file = self.write_config_file()
        grt_config_file = os.path.join(self.config_dir, "grt.yml")
        with open(grt_config_file, "w") as f:
            yaml.dump({"grt": {"share_toolbox": True}, "sanitization": {"tools": []}, "tool_params": {}}, f)
        self._scripts_check_output(script, ["-c", config_file, "-g", grt_config_file, "-r", self.config_dir])
        report_files = os.listdir(self.config_dir)
        json_files = [j for j in report_files if j.endswith(".json")]
        assert len(json_files) == 1, "Expected one json report file in [%s]" % json_files
        json_file = os.path.join(self.config_dir, json_files[0])
        with open(json_file) as f:
            export = json.load(f)
        assert export["version"] == 3

    def test_admin_cleanup_datasets(self):
        self._scripts_check_argparse_help("cleanup_datasets/admin_cleanup_datasets.py")

    def test_secret_decoder_ring(self):
        script = "secret_decoder_ring.py"
        self._scripts_check_argparse_help(script)

        config_file = self.write_config_file()
        output = self._scripts_check_output(script, ["-c", config_file, "encode", "1"])
        encoded_id = output.strip()

        output = self._scripts_check_output(script, ["-c", config_file, "decode", encoded_id])
        assert output.strip() == "1"

    def test_database_scripts(self):
        self._scripts_check_argparse_help("create_toolshed_db.py")
        self._scripts_check_argparse_help("migrate_toolshed_db.py")
        # TODO: test creating a smaller database - e.g. tool install database based on fresh
        # config file.

    def test_galaxy_main(self):
        self._scripts_check_argparse_help("galaxy-main")

    def test_runtime_stats(self):
        self._skip_unless_postgres()
        self._scripts_check_argparse_help("runtime_stats.py")

    def _scripts_check_argparse_help(self, script):
        # Test imports and argparse response to --help with 0 exit code.
        output = self._scripts_check_output(script, ["--help"])
        # Test -h, --help in printed output message.
        assert "-h, --help" in output

    def _scripts_check_output(self, script, args):
        cwd = galaxy_directory()
        cmd = ["python", os.path.join(cwd, "scripts", script)] + args
        clean_env = {
            "PATH": os.environ.get("PATH", None),
        }  # Don't let testing environment variables interfere with config.
        try:
            return unicodify(subprocess.check_output(cmd, cwd=cwd, env=clean_env))
        except Exception as e:
            if isinstance(e, subprocess.CalledProcessError):
                raise Exception(f"{unicodify(e)}\nOutput was:\n{unicodify(e.output)}")
            raise

    def write_config_file(self):
        config_dir = self.config_dir
        path = os.path.join(config_dir, "galaxy.yml")
        self._test_driver.temp_directories.extend([config_dir])
        config = self._raw_config
        # Update config dict with database_connection, which might be set through env variables
        config["database_connection"] = self._app.config.database_connection
        with open(path, "w") as f:
            yaml.dump({"galaxy": config}, f)

        return path
