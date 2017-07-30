import os
import tempfile
import unittest

try:
    import mockssh
except ImportError:
    raise unittest.SkipTest("Skipping tests that require mockssh")

from Crypto.PublicKey import RSA

from galaxy.jobs.runners.cli import CliInterface


class TestCliInterface(unittest.TestCase):

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.private_key)

    @classmethod
    def setUpClass(cls):
        cls.private_key = make_private_key()
        cls.username = 'testuser'
        cls.shell_params = {'username': cls.username,
                            'private_key': cls.private_key,
                            'hostname': 'localhost'}
        cls.cli_interface = CliInterface()

    def test_secure_shell_plugin_without_strict(self):
        with mockssh.Server(users={self.username: self.private_key}) as server:
            self.shell_params['port'] = server.port
            self.shell_params['plugin'] = 'SecureShell'
            self.shell_params['strict_host_key_checking'] = False
            self.shell = self.cli_interface.get_shell_plugin(self.shell_params)
            result = self.shell.execute(cmd='echo hello')
        assert result.stdout.strip() == 'hello'

    def test_get_shell_plugin(self):
        with mockssh.Server(users={self.username: self.private_key}) as server:
            self.shell_params['port'] = server.port
            self.shell_params['plugin'] = 'ParamikoShell'
            self.shell = self.cli_interface.get_shell_plugin(self.shell_params)
        assert self.shell.username == self.username

    def test_paramiko_shell_plugin(self):
        with mockssh.Server(users={self.username: self.private_key}) as server:
            self.shell_params['port'] = server.port
            self.shell_params['plugin'] = 'ParamikoShell'
            self.shell = self.cli_interface.get_shell_plugin(self.shell_params)
            result = self.shell.execute(cmd='echo hello')
        assert result.stdout.strip() == 'hello'


def make_private_key():
    key = RSA.generate(1024)
    private_fd, private_path = tempfile.mkstemp()
    open(private_path, 'w').write(key.exportKey('PEM'))
    return private_path
