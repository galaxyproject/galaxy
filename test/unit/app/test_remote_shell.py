import os
import unittest
from typing import (
    Any,
    Dict,
)

try:
    import mockssh
except ImportError:
    raise unittest.SkipTest("Skipping tests that require mockssh")

from galaxy.jobs.runners.util.cli import CliInterface
from galaxy.security.ssh_util import (
    generate_ssh_keys,
    SSHKeys,
)


class TestCliInterface(unittest.TestCase):
    ssh_keys: SSHKeys
    username: str
    shell_params: Dict[str, Any]
    cli_interface: CliInterface

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.ssh_keys.private_key_file)
        os.remove(cls.ssh_keys.public_key_file)

    @classmethod
    def setUpClass(cls):
        cls.ssh_keys = generate_ssh_keys()
        cls.username = "testuser"
        cls.shell_params = {
            "username": cls.username,
            "private_key": cls.ssh_keys.private_key_file,
            "strict_host_key_checking": False,
            "hostname": "localhost",
        }
        cls.cli_interface = CliInterface()

    def test_secure_shell_plugin_without_strict(self):
        with mockssh.Server(users={self.username: self.ssh_keys.private_key_file}) as server:
            self.shell_params["port"] = server.port
            self.shell_params["plugin"] = "SecureShell"
            self.shell_params["strict_host_key_checking"] = False
            self.shell = self.cli_interface.get_shell_plugin(self.shell_params)
            result = self.shell.execute(cmd="echo hello")
        assert result.stdout.strip() == "hello"

    def test_get_shell_plugin(self):
        with mockssh.Server(users={self.username: self.ssh_keys.private_key_file}) as server:
            self.shell_params["port"] = server.port
            self.shell_params["plugin"] = "ParamikoShell"
            self.shell = self.cli_interface.get_shell_plugin(self.shell_params)
        assert self.shell.username == self.username

    def test_paramiko_shell_plugin(self):
        with mockssh.Server(users={self.username: self.ssh_keys.private_key_file}) as server:
            self.shell_params["port"] = server.port
            self.shell_params["plugin"] = "ParamikoShell"
            self.shell = self.cli_interface.get_shell_plugin(self.shell_params)
            result = self.shell.execute(cmd="echo hello")
        assert result.stdout.strip() == "hello"
