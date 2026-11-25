import os
import threading
import unittest
from queue import Queue
from typing import (
    Any,
)

from pulsar.managers.util.retry import RetryActionExecutor

try:
    import mockssh
    import mockssh.server
except ImportError:
    mockssh = None

from galaxy.jobs.runners.util.cli import CliInterface
from galaxy.jobs.runners.util.cli.shell.local import (
    TIMEOUT_ERROR_MESSAGE,
    TIMEOUT_RETURN_CODE,
)
from galaxy.security.ssh_util import (
    generate_ssh_keys,
    SSHKeys,
)
from galaxy.util.unittest import TestCase

if mockssh:

    class RaceFreeHandler(mockssh.server.Handler):  # type: ignore[misc]
        def run(self):
            # mockssh 0.9.1 creates the command queue with `if chanid not in queues: queues[chanid] = Queue()`.
            # If the exec request is processed between the check and the assignment, the queue holding the
            # command is replaced, the command never runs and no exit status is ever sent. Fixed upstream in
            # https://github.com/carletes/mock-ssh-server/pull/34, not released as of 0.9.1.
            self.transport.start_server(server=self)
            while (channel := self.transport.accept()) is not None:
                self.command_queues.setdefault(channel.chanid, Queue())
                threading.Thread(target=self.handle_client, args=(channel,), daemon=True).start()

    class MockSSHServer(mockssh.Server):  # type: ignore[misc]
        handler_cls = RaceFreeHandler

    class NoExitStatusHandler(mockssh.server.Handler):  # type: ignore[misc]
        def handle_client(self, channel):
            # Accept the exec request, but never send output, an exit status or close the channel.
            pass

    class NoExitStatusServer(mockssh.Server):  # type: ignore[misc]
        handler_cls = NoExitStatusHandler


class TestCliInterface(TestCase):
    ssh_keys: SSHKeys
    username: str
    shell_params: dict[str, Any]
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
        if not mockssh:
            raise unittest.SkipTest("Skipping tests that require mockssh")
        with MockSSHServer(users={self.username: self.ssh_keys.private_key_file}) as server:
            self.shell_params["port"] = server.port
            self.shell_params["plugin"] = "SecureShell"
            self.shell_params["strict_host_key_checking"] = False
            self.shell = self.cli_interface.get_shell_plugin(self.shell_params)
            result = self.shell.execute(cmd="echo hello")
        assert result.stdout.strip() == "hello"

    def test_get_shell_plugin(self):
        if not mockssh:
            raise unittest.SkipTest("Skipping tests that require mockssh")
        with MockSSHServer(users={self.username: self.ssh_keys.private_key_file}) as server:
            self.shell_params["port"] = server.port
            self.shell_params["plugin"] = "ParamikoShell"
            self.shell = self.cli_interface.get_shell_plugin(self.shell_params)
        assert self.shell.username == self.username

    def test_paramiko_shell_plugin(self):
        if not mockssh:
            raise unittest.SkipTest("Skipping tests that require mockssh")
        with MockSSHServer(users={self.username: self.ssh_keys.private_key_file}) as server:
            self.shell_params["port"] = server.port
            self.shell_params["plugin"] = "ParamikoShell"
            self.shell = self.cli_interface.get_shell_plugin(self.shell_params)
            # Fail instead of retrying for hours (production uses 100 retries of up to 300 s).
            self.shell.retry_action_executor = RetryActionExecutor()
            result = self.shell.execute(cmd="echo hello")
        assert result.stdout.strip() == "hello"

    def test_paramiko_shell_times_out_without_exit_status(self):
        if not mockssh:
            raise unittest.SkipTest("Skipping tests that require mockssh")
        with NoExitStatusServer(users={self.username: self.ssh_keys.private_key_file}) as server:
            shell_params = {**self.shell_params, "port": server.port, "plugin": "ParamikoShell"}
            shell = CliInterface().get_shell_plugin(shell_params)
            shell.retry_action_executor = RetryActionExecutor()
            result = shell.execute(cmd="echo hello", timeout=5)
        assert result.returncode == TIMEOUT_RETURN_CODE
        assert result.stderr == TIMEOUT_ERROR_MESSAGE
