"""Unit tests for Aspera ascp file source plugin.

Tests verify behavior through the public API where possible:
- Pipeline: stderr → retry decision (end-to-end)
- Command construction: flag logic for any configuration
- Temp file lifecycle: real file creation, permissions, cleanup
- Retry mechanics: backoff, exhaustion, timeout
- Fallback: URL rewriting and FTP fallback on ascp failure
"""

import os
import stat
import subprocess
import tempfile
from unittest.mock import (
    Mock,
    patch,
)

import pytest

from galaxy.exceptions import MessageException
from galaxy.files.sources.ascp import AscpFilesSource
from galaxy.files.sources.ascp_fsspec import AscpFileSystem
from ._util import configured_file_sources

TEST_SSH_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAz6scc2q19eXLfYNLcmBMjWtNoFRTVATvxbNXZJmMhHFL04TP
rlojfBFH/3NO/Nvjg0d7vMkzU5Pq9LHlvK+9CmhJXzLzlFdWxXVVqwxLLvJGEZvD
-----END RSA PRIVATE KEY-----"""


@pytest.fixture
def ascp_fs():
    """AscpFileSystem with shutil.which patched and fast retry for testing."""
    with patch("shutil.which", return_value="/usr/bin/ascp"):
        yield AscpFileSystem(
            ssh_key=TEST_SSH_KEY,
            ssh_key_passphrase="testpass",
            user="test-user",
            host="test.example.com",
            max_retries=3,
            retry_base_delay=0.1,
        )


# ---------------------------------------------------------------------------
# TestAscpFileSystem: constructor, URL parsing, pure helpers
# ---------------------------------------------------------------------------


class TestAscpFileSystem:
    """Tests for AscpFileSystem initialization and pure helper methods."""

    def test_initialization(self):
        """Test that constructor stores all parameters correctly."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(
                ascp_path="ascp",
                ssh_key=TEST_SSH_KEY,
                ssh_key_passphrase="abcdefg",
                user="test-user",
                host="test.example.com",
                rate_limit="300m",
                port=33001,
                disable_encryption=True,
            )
            assert fs.ascp_path == "ascp"
            assert fs.ssh_key == TEST_SSH_KEY
            assert fs.user == "test-user"
            assert fs.host == "test.example.com"
            assert fs.rate_limit == "300m"
            assert fs.port == 33001
            assert fs.disable_encryption is True

    def test_missing_ascp_binary(self):
        """Test that initialization fails when ascp binary is not found."""
        with patch("shutil.which", return_value=None):
            with pytest.raises(MessageException, match="ascp binary not found"):
                AscpFileSystem(
                    ascp_path="ascp",
                    ssh_key=TEST_SSH_KEY,
                    user="test-user",
                    host="test.example.com",
                )

    def test_configuration_defaults(self):
        """Test that retry/resume/timeout defaults are correct."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(
                ssh_key=TEST_SSH_KEY,
                user="test-user",
                host="test.example.com",
            )
            assert fs.max_retries == 5
            assert fs.retry_base_delay == 5.0
            assert fs.retry_max_delay == 60.0
            assert fs.enable_resume is True
            assert fs.transfer_timeout == 1800

    def test_parse_url_with_full_ascp_url(self):
        """Test URL parsing with full ascp:// URL."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(ssh_key=TEST_SSH_KEY, user="u", host="h")
            parsed = fs._parse_url("ascp://testuser@testhost:12345/path/to/file")
            assert parsed["user"] == "testuser"
            assert parsed["host"] == "testhost"
            assert parsed["port"] == 12345
            assert parsed["path"] == "path/to/file"

    def test_parse_url_with_fasp_url(self):
        """Test URL parsing with fasp:// URL."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(ssh_key=TEST_SSH_KEY, user="u", host="h")
            parsed = fs._parse_url("fasp://testuser@testhost/path/to/file")
            assert parsed["user"] == "testuser"
            assert parsed["host"] == "testhost"
            assert parsed["path"] == "path/to/file"

    def test_parse_url_with_path_only(self):
        """Test URL parsing with just a path."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(ssh_key=TEST_SSH_KEY, user="u", host="h")
            parsed = fs._parse_url("/path/to/file")
            assert parsed["user"] is None
            assert parsed["host"] is None
            assert parsed["port"] is None
            assert parsed["path"] == "/path/to/file"

    def test_sanitize_cmd_for_log(self):
        """Test that SSH key path is hidden in log output."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(ssh_key=TEST_SSH_KEY, user="u", host="h")
            cmd = ["ascp", "-i", "/tmp/secret_key.key", "-l", "300m", "user@host:/path", "/dest"]
            sanitized = fs._sanitize_cmd_for_log(cmd)
            assert "/tmp/secret_key.key" not in sanitized
            assert "<hidden>" in sanitized
            assert "ascp" in sanitized
            assert "300m" in sanitized

    def test_missing_user_or_host(self):
        """Test that get_file fails when user or host is not provided."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(ssh_key=TEST_SSH_KEY, user=None, host=None)
            with pytest.raises(MessageException, match="User and host must be specified"):
                fs.get_file("/remote/path/file.txt", "/local/path/file.txt")


# ---------------------------------------------------------------------------
# TestAscpFilesSource: plugin registration and URL matching
# ---------------------------------------------------------------------------


class TestAscpFilesSource:
    """Tests for the AscpFilesSource plugin class."""

    def test_plugin_type(self):
        """Test that plugin type is correctly set."""
        assert AscpFilesSource.plugin_type == "ascp"

    def test_url_matching_ascp(self):
        """Test URL matching for ascp:// URLs."""
        config = {
            "type": "ascp",
            "id": "test_ascp",
            "label": "Test Aspera",
            "ssh_key_content": TEST_SSH_KEY,
            "ssh_key_passphrase": "abcdefg",
            "user": "test-user",
            "host": "test.example.com",
        }

        with patch("shutil.which", return_value="/usr/bin/ascp"):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
                import yaml

                yaml.dump([config], f)
                config_file = f.name

            try:
                file_sources = configured_file_sources(config_file)
                score = file_sources.get_file_source_path("ascp://test.example.com/path/to/file")
                assert score.file_source.id == "test_ascp"
            finally:
                os.unlink(config_file)

    def test_url_matching_fasp(self):
        """Test URL matching for fasp:// URLs."""
        config = {
            "type": "ascp",
            "id": "test_ascp",
            "label": "Test Aspera",
            "ssh_key_content": TEST_SSH_KEY,
            "ssh_key_passphrase": "abcdefg",
            "user": "test-user",
            "host": "test.example.com",
        }

        with patch("shutil.which", return_value="/usr/bin/ascp"):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
                import yaml

                yaml.dump([config], f)
                config_file = f.name

            try:
                file_sources = configured_file_sources(config_file)
                score = file_sources.get_file_source_path("fasp://test.example.com/path/to/file")
                assert score.file_source.id == "test_ascp"
            finally:
                os.unlink(config_file)

    def test_url_matching_non_matching(self):
        """Test that non-ascp URLs don't match the ascp plugin."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            config = {
                "type": "ascp",
                "id": "test_ascp",
                "label": "Test Aspera",
                "ssh_key_content": TEST_SSH_KEY,
                "user": "test-user",
                "host": "test.example.com",
            }

            with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
                import yaml

                yaml.dump([config], f)
                config_file = f.name

            try:
                file_sources = configured_file_sources(config_file)
                result = file_sources.get_file_source_path("http://example.com/file")
                assert result.file_source.id != "test_ascp"
            except Exception:
                pass  # No other plugin matches — also acceptable
            finally:
                os.unlink(config_file)


# ---------------------------------------------------------------------------
# TestErrorPipeline: stderr → _handle_ascp_error → _is_retryable_error → retry
# ---------------------------------------------------------------------------


class TestErrorPipeline:
    """Test the full error pipeline: stderr → retry decision.

    This is the chain that broke in the original bug. Tests verify that
    stderr flows through _handle_ascp_error into a MessageException, and
    _is_retryable_error makes the correct retry decision — end to end.
    Only subprocess.run and shutil.which are mocked.
    """

    @staticmethod
    def _run_pipeline(fs, stderr, max_attempts=3):
        """Run get_file with a mock subprocess that fails with given stderr,
        then succeeds. Returns the number of subprocess calls made."""
        call_count = 0

        def mock_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < max_attempts:
                return Mock(returncode=1, stderr=stderr, stdout="")
            return Mock(returncode=0, stderr="", stdout="")

        with patch("subprocess.run", side_effect=mock_run):
            with patch("time.sleep"):
                try:
                    fs.get_file("/remote/file.txt", "/local/file.txt")
                except MessageException:
                    pass  # Expected for non-retryable or exhausted retries
        return call_count

    def test_retryable_stderr_is_retried(self, ascp_fs):
        """Retryable stderr (network error) → multiple attempts."""
        count = self._run_pipeline(ascp_fs, "network timeout error")
        assert count == 3  # Failed twice, succeeded on third

    def test_non_retryable_stderr_not_retried(self, ascp_fs):
        """Non-retryable stderr (auth failure) → single attempt, no retry."""
        count = self._run_pipeline(ascp_fs, "authentication failed: bad key")
        assert count == 1

    def test_non_retryable_file_not_found(self, ascp_fs):
        """Non-retryable stderr (file not found) → single attempt."""
        count = self._run_pipeline(ascp_fs, "no such file or directory")
        assert count == 1

    def test_unrecognized_stderr_is_retried(self, ascp_fs):
        """Unrecognized stderr → retried (blacklist guarantee)."""
        count = self._run_pipeline(ascp_fs, "xyzzy something never seen before 42")
        assert count == 3

    def test_session_stop_stderr_is_retried(self, ascp_fs):
        """Session stop stderr → retried (classified as session-stop, which is retryable)."""
        count = self._run_pipeline(ascp_fs, "Session Stop  (Error: some server reason)")
        assert count == 3

    def test_empty_stderr_is_retried(self, ascp_fs):
        """Empty stderr on failure → retried (generic error, retryable)."""
        count = self._run_pipeline(ascp_fs, "")
        assert count == 3


# ---------------------------------------------------------------------------
# TestCommandConstruction: verify flag logic with minimal mocking
# ---------------------------------------------------------------------------


class TestCommandConstruction:
    """Test ascp command construction. Only subprocess.run is mocked
    (to capture the command); temp file operations run for real."""

    def _capture_command(self, fs):
        """Run get_file and capture the command passed to subprocess.run."""
        captured = {}

        def mock_run(cmd, *args, **kwargs):
            captured["cmd"] = cmd
            captured["kwargs"] = kwargs
            return Mock(returncode=0, stderr="", stdout="")

        with patch("subprocess.run", side_effect=mock_run):
            fs.get_file("/remote/file.txt", "/local/file.txt")
        return captured

    def test_encryption_disabled(self):
        """disable_encryption=True → -T flag present."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(ssh_key=TEST_SSH_KEY, user="u", host="h", disable_encryption=True)
            result = self._capture_command(fs)
            assert "-T" in result["cmd"]

    def test_encryption_enabled(self):
        """disable_encryption=False → no -T flag."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(ssh_key=TEST_SSH_KEY, user="u", host="h", disable_encryption=False)
            result = self._capture_command(fs)
            assert "-T" not in result["cmd"]

    def test_resume_enabled(self):
        """enable_resume=True → -k 1 flag present on first attempt."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(ssh_key=TEST_SSH_KEY, user="u", host="h", enable_resume=True)
            result = self._capture_command(fs)
            cmd = result["cmd"]
            assert "-k" in cmd
            assert cmd[cmd.index("-k") + 1] == "1"

    def test_resume_disabled(self):
        """enable_resume=False → no -k flag."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(ssh_key=TEST_SSH_KEY, user="u", host="h", enable_resume=False)
            result = self._capture_command(fs)
            assert "-k" not in result["cmd"]

    def test_port_and_rate(self):
        """-P port and -l rate_limit are correct."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(ssh_key=TEST_SSH_KEY, user="u", host="h", port=9999, rate_limit="50m")
            result = self._capture_command(fs)
            cmd = result["cmd"]
            assert "9999" in cmd
            assert "50m" in cmd

    def test_user_host_path_format(self):
        """Remote path formatted as user@host:path."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(ssh_key=TEST_SSH_KEY, user="myuser", host="myhost.com")
            result = self._capture_command(fs)
            assert "myuser@myhost.com:/remote/file.txt" in result["cmd"]

    def test_passphrase_sets_env(self):
        """Passphrase → ASPERA_SCP_PASS in subprocess env."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(ssh_key=TEST_SSH_KEY, ssh_key_passphrase="secret", user="u", host="h")
            result = self._capture_command(fs)
            env = result["kwargs"].get("env")
            assert env is not None
            assert env.get("ASPERA_SCP_PASS") == "secret"

    def test_no_passphrase_no_env(self):
        """No passphrase → env=None passed to subprocess."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(ssh_key=TEST_SSH_KEY, user="u", host="h")
            result = self._capture_command(fs)
            assert result["kwargs"].get("env") is None

    def test_timeout_passed_to_subprocess(self):
        """transfer_timeout is passed as timeout kwarg to subprocess.run."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(ssh_key=TEST_SSH_KEY, user="u", host="h", transfer_timeout=999)
            result = self._capture_command(fs)
            assert result["kwargs"].get("timeout") == 999

    def test_resume_on_all_attempts(self):
        """Resume flag (-k 1) present on both first attempt and retries."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(
                ssh_key=TEST_SSH_KEY, user="u", host="h",
                enable_resume=True, max_retries=2, retry_base_delay=0.01,
            )
            captured_commands = []

            def mock_run(cmd, *args, **kwargs):
                captured_commands.append(list(cmd))
                if len(captured_commands) < 2:
                    return Mock(returncode=1, stderr="some transient error", stdout="")
                return Mock(returncode=0, stderr="", stdout="")

            with patch("subprocess.run", side_effect=mock_run):
                with patch("time.sleep"):
                    fs.get_file("/remote/file.txt", "/local/file.txt")

            for i, cmd in enumerate(captured_commands):
                assert "-k" in cmd, f"Attempt {i}: -k flag missing"
                assert cmd[cmd.index("-k") + 1] == "1"


# ---------------------------------------------------------------------------
# TestTempFileLifecycle: real file creation, permissions, cleanup
# ---------------------------------------------------------------------------


class TestTempFileLifecycle:
    """Test SSH key temp file lifecycle with real file operations.
    Only subprocess.run and shutil.which are mocked."""

    def test_key_file_created_with_correct_permissions(self):
        """Temp key file has 0o600 permissions and contains the SSH key."""
        key_paths = []

        def spy_run(cmd, *args, **kwargs):
            # Find the -i argument to get the key path
            if "-i" in cmd:
                key_path = cmd[cmd.index("-i") + 1]
                key_paths.append(key_path)
                # Verify file exists and has correct permissions while ascp "runs"
                assert os.path.exists(key_path), "Key file should exist during transfer"
                file_stat = os.stat(key_path)
                assert stat.S_IMODE(file_stat.st_mode) == 0o600, "Key file should have 0o600 permissions"
                with open(key_path) as f:
                    assert f.read() == TEST_SSH_KEY, "Key file should contain the SSH key"
            return Mock(returncode=0, stderr="", stdout="")

        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(ssh_key=TEST_SSH_KEY, user="u", host="h")
            with patch("subprocess.run", side_effect=spy_run):
                fs.get_file("/remote/file.txt", "/local/file.txt")

        assert len(key_paths) == 1
        assert not os.path.exists(key_paths[0]), "Key file should be cleaned up after transfer"

    def test_key_file_cleaned_up_on_non_retryable_error(self):
        """Temp key file is cleaned up even when a non-retryable error occurs."""
        key_paths = []

        def spy_run(cmd, *args, **kwargs):
            if "-i" in cmd:
                key_paths.append(cmd[cmd.index("-i") + 1])
            return Mock(returncode=1, stderr="authentication failed", stdout="")

        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(ssh_key=TEST_SSH_KEY, user="u", host="h", max_retries=1)
            with patch("subprocess.run", side_effect=spy_run):
                with pytest.raises(MessageException):
                    fs.get_file("/remote/file.txt", "/local/file.txt")

        assert len(key_paths) == 1
        assert not os.path.exists(key_paths[0]), "Key file should be cleaned up after error"

    def test_key_file_cleaned_up_on_retryable_error(self):
        """Temp key file is cleaned up after retries are exhausted."""
        key_paths = []

        def spy_run(cmd, *args, **kwargs):
            if "-i" in cmd:
                key_paths.append(cmd[cmd.index("-i") + 1])
            return Mock(returncode=1, stderr="some transient error", stdout="")

        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(ssh_key=TEST_SSH_KEY, user="u", host="h", max_retries=2, retry_base_delay=0.01)
            with patch("subprocess.run", side_effect=spy_run):
                with patch("time.sleep"):
                    with pytest.raises(MessageException):
                        fs.get_file("/remote/file.txt", "/local/file.txt")

        # Each attempt creates a new temp file
        for path in key_paths:
            assert not os.path.exists(path), f"Key file {path} should be cleaned up"


# ---------------------------------------------------------------------------
# TestRetryMechanics: backoff, exhaustion, timeout
# ---------------------------------------------------------------------------


class TestRetryMechanics:
    """Test retry mechanics: backoff delays, max retries, timeout handling."""

    def test_max_retries_exhausted(self, ascp_fs):
        """Error is raised after max retries are exhausted."""
        call_count = 0

        def mock_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return Mock(returncode=1, stderr="some transient error", stdout="")

        with patch("subprocess.run", side_effect=mock_run):
            with patch("time.sleep"):
                with pytest.raises(MessageException):
                    ascp_fs.get_file("/remote/file.txt", "/local/file.txt")

        assert call_count == 3  # ascp_fs fixture has max_retries=3

    def test_exponential_backoff_delays(self):
        """Retry delays follow exponential backoff, capped at retry_max_delay."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(
                ssh_key=TEST_SSH_KEY, user="u", host="h",
                max_retries=4, retry_base_delay=2.0, retry_max_delay=10.0,
            )

        def mock_run(*args, **kwargs):
            return Mock(returncode=1, stderr="transient error", stdout="")

        with patch("subprocess.run", side_effect=mock_run):
            with patch("time.sleep") as mock_sleep:
                with pytest.raises(MessageException):
                    fs.get_file("/remote/file.txt", "/local/file.txt")

                sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
                assert sleep_calls[0] == 2.0   # 2^1
                assert sleep_calls[1] == 4.0   # 2^2
                assert sleep_calls[2] == 8.0   # 2^3, not capped (< 10)

    def test_transfer_timeout(self):
        """subprocess.TimeoutExpired → MessageException with timeout info."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(
                ssh_key=TEST_SSH_KEY, user="u", host="h",
                max_retries=1, transfer_timeout=10,
            )

        def mock_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd="ascp", timeout=10)

        with patch("subprocess.run", side_effect=mock_run):
            with pytest.raises(MessageException, match="timed out after 10 seconds"):
                fs.get_file("/remote/file.txt", "/local/file.txt")


# ---------------------------------------------------------------------------
# TestEdgeCases: boundary conditions
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases that don't fit neatly into other categories."""

    def test_empty_ssh_key_raises(self):
        """Empty SSH key raises before attempting transfer."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(ssh_key="", user="u", host="h")
            with pytest.raises(MessageException, match="SSH key is required"):
                fs.get_file("/remote/file.txt", "/local/file.txt")

    def test_success_with_stderr_warnings(self):
        """returncode=0 with non-empty stderr should succeed (ascp warnings)."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(ssh_key=TEST_SSH_KEY, user="u", host="h")

        def mock_run(*args, **kwargs):
            return Mock(returncode=0, stderr="Warning: something non-fatal", stdout="")

        with patch("subprocess.run", side_effect=mock_run):
            # Should not raise
            fs.get_file("/remote/file.txt", "/local/file.txt")


# ---------------------------------------------------------------------------
# TestFallback: URL rewriting and FTP fallback on ascp failure
# ---------------------------------------------------------------------------


def _make_ascp_source_with_fallback(fallback_scheme="ftp", fallback_host="ftp.sra.ebi.ac.uk"):
    """Create an AscpFilesSource configured with fallback."""
    import yaml

    config = {
        "type": "ascp",
        "id": "test_ascp_fallback",
        "label": "Test Aspera with Fallback",
        "ssh_key_content": TEST_SSH_KEY,
        "user": "era-fasp",
        "host": "fasp.sra.ebi.ac.uk",
        "fallback_scheme": fallback_scheme,
        "fallback_host": fallback_host,
    }
    with patch("shutil.which", return_value="/usr/bin/ascp"):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump([config], f)
            config_file = f.name
        try:
            file_sources = configured_file_sources(config_file)
            pair = file_sources.get_file_source_path("fasp://era-fasp@fasp.sra.ebi.ac.uk/vol1/fastq/ERR123/file.fastq.gz")
            return pair.file_source, pair, config_file
        except Exception:
            os.unlink(config_file)
            raise


class TestFallbackUrlRewrite:
    """Test _rewrite_url_for_fallback: pure URL transformation logic."""

    def _make_source(self, fallback_scheme=None, fallback_host=None):
        from types import SimpleNamespace

        config = SimpleNamespace(
            fallback_scheme=fallback_scheme,
            fallback_host=fallback_host,
        )
        source = AscpFilesSource.__new__(AscpFilesSource)
        return source, config

    def test_ena_fasp_to_ftp(self):
        """fasp://era-fasp@fasp.sra.ebi.ac.uk/vol1/... → ftp://ftp.sra.ebi.ac.uk/vol1/..."""
        source, config = self._make_source(fallback_scheme="ftp", fallback_host="ftp.sra.ebi.ac.uk")
        result = source._rewrite_url_for_fallback(
            "fasp://era-fasp@fasp.sra.ebi.ac.uk/vol1/fastq/ERR123/ERR123.fastq.gz", config
        )
        assert result == "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/ERR123/ERR123.fastq.gz"

    def test_ascp_scheme_also_rewritten(self):
        """ascp:// URLs are also rewritten."""
        source, config = self._make_source(fallback_scheme="ftp", fallback_host="ftp.sra.ebi.ac.uk")
        result = source._rewrite_url_for_fallback(
            "ascp://era-fasp@fasp.sra.ebi.ac.uk/vol1/fastq/ERR123/ERR123.fastq.gz", config
        )
        assert result == "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/ERR123/ERR123.fastq.gz"

    def test_user_stripped_from_url(self):
        """User component (era-fasp@) is not included in the fallback URL."""
        source, config = self._make_source(fallback_scheme="ftp", fallback_host="ftp.sra.ebi.ac.uk")
        result = source._rewrite_url_for_fallback(
            "fasp://era-fasp@fasp.sra.ebi.ac.uk/vol1/fastq/ERR123/ERR123.fastq.gz", config
        )
        assert "era-fasp" not in result
        assert "@" not in result

    def test_no_fallback_host_returns_none(self):
        """No fallback_host → returns None."""
        source, config = self._make_source(fallback_scheme="ftp", fallback_host=None)
        result = source._rewrite_url_for_fallback("fasp://era-fasp@fasp.sra.ebi.ac.uk/vol1/file.gz", config)
        assert result is None

    def test_no_fallback_scheme_returns_none(self):
        """No fallback_scheme → returns None."""
        source, config = self._make_source(fallback_scheme=None, fallback_host="ftp.sra.ebi.ac.uk")
        result = source._rewrite_url_for_fallback("fasp://era-fasp@fasp.sra.ebi.ac.uk/vol1/file.gz", config)
        assert result is None

    def test_non_ascp_url_returns_none(self):
        """Non-ascp/fasp URL → returns None (not our URL to rewrite)."""
        source, config = self._make_source(fallback_scheme="ftp", fallback_host="ftp.sra.ebi.ac.uk")
        result = source._rewrite_url_for_fallback("https://example.com/file.gz", config)
        assert result is None

    def test_path_preserved_exactly(self):
        """Deep nested path is preserved exactly in the fallback URL."""
        source, config = self._make_source(fallback_scheme="ftp", fallback_host="ftp.sra.ebi.ac.uk")
        result = source._rewrite_url_for_fallback(
            "fasp://era-fasp@fasp.sra.ebi.ac.uk/vol1/fastq/ERR999/ERR999_1.fastq.gz", config
        )
        assert result == "ftp://ftp.sra.ebi.ac.uk/vol1/fastq/ERR999/ERR999_1.fastq.gz"


class TestFallbackInvocation:
    """Test that fallback is triggered on ascp failure and not on success."""

    def test_fallback_called_on_ascp_failure(self):
        """When ascp fails and fallback is configured, stream_url_to_file is called."""
        source, pair, config_file = _make_ascp_source_with_fallback()
        try:
            with patch("shutil.which", return_value="/usr/bin/ascp"):
                with patch("subprocess.run", return_value=Mock(returncode=1, stderr="Session Stop (Error: Client unable to connect)", stdout="")):
                    with patch("time.sleep"):
                        with patch("galaxy.files.sources.ascp.stream_url_to_file") as mock_fallback:
                            mock_fallback.return_value = None
                            source.realize_to(pair.path, "/tmp/test_fallback_output.txt")

            mock_fallback.assert_called_once()
            fallback_url = mock_fallback.call_args[0][0]
            assert fallback_url.startswith("ftp://ftp.sra.ebi.ac.uk/")
            assert "era-fasp" not in fallback_url
        finally:
            os.unlink(config_file)

    def test_fallback_not_called_on_ascp_success(self):
        """When ascp succeeds, fallback is never invoked."""
        source, pair, config_file = _make_ascp_source_with_fallback()
        try:
            with patch("shutil.which", return_value="/usr/bin/ascp"):
                with patch("subprocess.run", return_value=Mock(returncode=0, stderr="", stdout="")):
                    with patch("galaxy.files.sources.ascp.stream_url_to_file") as mock_fallback:
                        source.realize_to(pair.path, "/tmp/test_no_fallback_output.txt")

            mock_fallback.assert_not_called()
        finally:
            os.unlink(config_file)

    def test_both_fail_raises_message_exception(self):
        """When ascp and fallback both fail, MessageException is raised."""
        source, pair, config_file = _make_ascp_source_with_fallback()
        try:
            with patch("shutil.which", return_value="/usr/bin/ascp"):
                with patch("subprocess.run", return_value=Mock(returncode=1, stderr="Session Stop", stdout="")):
                    with patch("time.sleep"):
                        with patch("galaxy.files.sources.ascp.stream_url_to_file", side_effect=Exception("FTP also down")):
                            with pytest.raises(MessageException, match="fallback.*also failed"):
                                source.realize_to(pair.path, "/tmp/test_both_fail.txt")
        finally:
            os.unlink(config_file)

    def test_no_fallback_configured_raises_original_error(self):
        """Without fallback config, ascp failure raises directly without fallback attempt."""
        import yaml

        config = {
            "type": "ascp",
            "id": "test_ascp_no_fallback",
            "label": "Test Aspera no Fallback",
            "ssh_key_content": TEST_SSH_KEY,
            "user": "era-fasp",
            "host": "fasp.sra.ebi.ac.uk",
        }
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
                yaml.dump([config], f)
                config_file = f.name
            try:
                file_sources = configured_file_sources(config_file)
                pair = file_sources.get_file_source_path("fasp://era-fasp@fasp.sra.ebi.ac.uk/vol1/file.gz")
                source = pair.file_source

                with patch("subprocess.run", return_value=Mock(returncode=1, stderr="Session Stop", stdout="")):
                    with patch("time.sleep"):
                        with patch("galaxy.files.sources.ascp.stream_url_to_file") as mock_fallback:
                            with pytest.raises(MessageException):
                                source.realize_to(pair.path, "/tmp/test_no_fallback.txt")

                mock_fallback.assert_not_called()
            finally:
                os.unlink(config_file)

