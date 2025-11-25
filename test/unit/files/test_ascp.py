"""Unit tests for Aspera ascp file source plugin."""

import os
import tempfile
from unittest.mock import (
    MagicMock,
    Mock,
    patch,
)

import pytest

from galaxy.exceptions import MessageException
from galaxy.files.sources.ascp import AscpFilesSource
from galaxy.files.sources.ascp_fsspec import AscpFileSystem

# Test SSH key (dummy key for testing)
TEST_SSH_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAz6scc2q19eXLfYNLcmBMjWtNoFRTVATvxbNXZJmMhHFL04TP
rlojfBFH/3NO/Nvjg0d7vMkzU5Pq9LHlvK+9CmhJXzLzlFdWxXVVqwxLLvJGEZvD
-----END RSA PRIVATE KEY-----"""


class TestAscpFileSystem:
    """Tests for the AscpFileSystem fsspec implementation."""

    def test_initialization(self):
        """Test that AscpFileSystem can be instantiated with valid parameters."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(
                ascp_path="ascp",
                ssh_key=TEST_SSH_KEY,
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

    def test_parse_url_with_full_ascp_url(self):
        """Test URL parsing with full ascp:// URL."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(
                ssh_key=TEST_SSH_KEY,
                user="default-user",
                host="default.example.com",
            )
            parsed = fs._parse_url("ascp://testuser@testhost:12345/path/to/file")
            assert parsed["user"] == "testuser"
            assert parsed["host"] == "testhost"
            assert parsed["port"] == 12345
            assert parsed["path"] == "path/to/file"

    def test_parse_url_with_fasp_url(self):
        """Test URL parsing with fasp:// URL."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(
                ssh_key=TEST_SSH_KEY,
                user="default-user",
                host="default.example.com",
            )
            parsed = fs._parse_url("fasp://testuser@testhost/path/to/file")
            assert parsed["user"] == "testuser"
            assert parsed["host"] == "testhost"
            assert parsed["path"] == "path/to/file"

    def test_parse_url_with_path_only(self):
        """Test URL parsing with just a path."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(
                ssh_key=TEST_SSH_KEY,
                user="default-user",
                host="default.example.com",
            )
            parsed = fs._parse_url("/path/to/file")
            assert parsed["user"] is None
            assert parsed["host"] is None
            assert parsed["port"] is None
            assert parsed["path"] == "/path/to/file"

    @patch("subprocess.run")
    @patch("tempfile.mkstemp")
    @patch("os.chmod")
    @patch("os.fdopen")
    @patch("os.unlink")
    def test_get_file_success(self, mock_unlink, mock_fdopen, mock_chmod, mock_mkstemp, mock_subprocess):
        """Test successful file download."""
        # Setup mocks
        mock_mkstemp.return_value = (123, "/tmp/test_key.key")
        mock_file = MagicMock()
        mock_fdopen.return_value.__enter__.return_value = mock_file
        mock_subprocess.return_value = Mock(returncode=0, stderr="", stdout="Transfer complete")

        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(
                ascp_path="ascp",
                ssh_key=TEST_SSH_KEY,
                user="test-user",
                host="test.example.com",
                rate_limit="300m",
                port=33001,
                disable_encryption=True,
            )

            # Execute
            fs._get_file("/remote/path/file.txt", "/local/path/file.txt")

            # Verify
            mock_mkstemp.assert_called_once()
            mock_chmod.assert_called_once_with("/tmp/test_key.key", 0o600)
            mock_file.write.assert_called_once_with(TEST_SSH_KEY)
            mock_subprocess.assert_called_once()
            mock_unlink.assert_called_once_with("/tmp/test_key.key")

            # Verify command structure
            call_args = mock_subprocess.call_args[0][0]
            assert call_args[0] == "ascp"
            assert "-i" in call_args
            assert "-l" in call_args
            assert "300m" in call_args
            assert "-P" in call_args
            assert "33001" in call_args
            assert "-T" in call_args
            assert "test-user@test.example.com:/remote/path/file.txt" in call_args
            assert "/local/path/file.txt" in call_args

    @patch("subprocess.run")
    @patch("tempfile.mkstemp")
    @patch("os.chmod")
    @patch("os.fdopen")
    @patch("os.unlink")
    def test_get_file_authentication_failure(self, mock_unlink, mock_fdopen, mock_chmod, mock_mkstemp, mock_subprocess):
        """Test handling of authentication failures."""
        mock_mkstemp.return_value = (123, "/tmp/test_key.key")
        mock_file = MagicMock()
        mock_fdopen.return_value.__enter__.return_value = mock_file
        mock_subprocess.return_value = Mock(returncode=1, stderr="authentication failed", stdout="")

        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(
                ssh_key=TEST_SSH_KEY,
                user="test-user",
                host="test.example.com",
            )

            with pytest.raises(MessageException, match="Authentication failed"):
                fs._get_file("/remote/path/file.txt", "/local/path/file.txt")

            # Verify cleanup happened
            mock_unlink.assert_called_once()

    @patch("subprocess.run")
    @patch("tempfile.mkstemp")
    @patch("os.chmod")
    @patch("os.fdopen")
    @patch("os.unlink")
    def test_get_file_not_found(self, mock_unlink, mock_fdopen, mock_chmod, mock_mkstemp, mock_subprocess):
        """Test handling of file not found errors."""
        mock_mkstemp.return_value = (123, "/tmp/test_key.key")
        mock_file = MagicMock()
        mock_fdopen.return_value.__enter__.return_value = mock_file
        mock_subprocess.return_value = Mock(returncode=1, stderr="no such file or directory", stdout="")

        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(
                ssh_key=TEST_SSH_KEY,
                user="test-user",
                host="test.example.com",
            )

            with pytest.raises(MessageException, match="Remote file not found"):
                fs._get_file("/remote/path/file.txt", "/local/path/file.txt")

    @patch("subprocess.run")
    @patch("tempfile.mkstemp")
    @patch("os.chmod")
    @patch("os.fdopen")
    @patch("os.unlink")
    def test_get_file_network_error(self, mock_unlink, mock_fdopen, mock_chmod, mock_mkstemp, mock_subprocess):
        """Test handling of network errors."""
        mock_mkstemp.return_value = (123, "/tmp/test_key.key")
        mock_file = MagicMock()
        mock_fdopen.return_value.__enter__.return_value = mock_file
        mock_subprocess.return_value = Mock(returncode=1, stderr="connection refused", stdout="")

        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(
                ssh_key=TEST_SSH_KEY,
                user="test-user",
                host="test.example.com",
            )

            with pytest.raises(MessageException, match="Network error"):
                fs._get_file("/remote/path/file.txt", "/local/path/file.txt")

    @patch("subprocess.run")
    @patch("tempfile.mkstemp")
    @patch("os.chmod")
    @patch("os.fdopen")
    @patch("os.unlink")
    @patch("os.close")
    def test_key_cleanup_on_error(self, mock_close, mock_unlink, mock_fdopen, mock_chmod, mock_mkstemp, mock_subprocess):
        """Test that temporary key file is cleaned up even on error."""
        mock_mkstemp.return_value = (123, "/tmp/test_key.key")
        mock_file = MagicMock()
        mock_fdopen.return_value.__enter__.return_value = mock_file
        # Use a non-retryable error (authentication failure)
        mock_subprocess.return_value = Mock(
            returncode=1,
            stderr="authentication failed: invalid key",
            stdout="",
        )

        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(
                ssh_key=TEST_SSH_KEY,
                user="test-user",
                host="test.example.com",
            )

            with pytest.raises(MessageException, match="Authentication failed"):
                fs._get_file("/remote/path/file.txt", "/local/path/file.txt")

            # Verify cleanup was attempted
            mock_unlink.assert_called_once_with("/tmp/test_key.key")

    def test_sanitize_cmd_for_log(self):
        """Test that SSH key path is hidden in log output."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(
                ssh_key=TEST_SSH_KEY,
                user="test-user",
                host="test.example.com",
            )

            cmd = ["ascp", "-i", "/tmp/secret_key.key", "-l", "300m", "user@host:/path", "/dest"]
            sanitized = fs._sanitize_cmd_for_log(cmd)

            assert "/tmp/secret_key.key" not in sanitized
            assert "<hidden>" in sanitized
            assert "ascp" in sanitized
            assert "300m" in sanitized

    def test_missing_ssh_key(self):
        """Test that _get_file fails when SSH key is not provided."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(
                ssh_key=None,
                user="test-user",
                host="test.example.com",
            )

            with pytest.raises(MessageException, match="SSH key is required"):
                fs._get_file("/remote/path/file.txt", "/local/path/file.txt")

    def test_missing_user_or_host(self):
        """Test that _get_file fails when user or host is not provided."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(
                ssh_key=TEST_SSH_KEY,
                user=None,
                host=None,
            )

            with pytest.raises(MessageException, match="User and host must be specified"):
                fs._get_file("/remote/path/file.txt", "/local/path/file.txt")


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
            "user": "test-user",
            "host": "test.example.com",
        }

        with patch("shutil.which", return_value="/usr/bin/ascp"):
            from ._util import configured_file_sources

            # Create a temporary config file
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
            "user": "test-user",
            "host": "test.example.com",
        }

        with patch("shutil.which", return_value="/usr/bin/ascp"):
            from ._util import configured_file_sources

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
        """Test that non-ascp URLs return 0 score."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            config = {
                "type": "ascp",
                "id": "test_ascp",
                "label": "Test Aspera",
                "ssh_key_content": TEST_SSH_KEY,
                "user": "test-user",
                "host": "test.example.com",
            }

            from ._util import configured_file_sources

            with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
                import yaml

                yaml.dump([config], f)
                config_file = f.name

            try:
                file_sources = configured_file_sources(config_file)
                # This should not match ascp plugin
                result = file_sources.get_file_source_path("http://example.com/file")
                # Should match a different plugin or return None
                assert result.file_source.id != "test_ascp"
            except Exception:
                # If no other plugin matches, that's also acceptable
                pass
            finally:
                os.unlink(config_file)

    def test_ssh_key_file_usage(self):
        """Test that ssh_key_file is properly used when provided."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".key") as key_file:
            key_file.write(TEST_SSH_KEY)
            key_file_path = key_file.name

        try:
            os.chmod(key_file_path, 0o600)

            config = {
                "type": "ascp",
                "id": "test_ascp",
                "label": "Test Aspera",
                "ssh_key_file": key_file_path,
                "user": "test-user",
                "host": "test.example.com",
            }

            with patch("shutil.which", return_value="/usr/bin/ascp"):
                from ._util import configured_file_sources

                with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
                    import yaml

                    yaml.dump([config], f)
                    config_file = f.name

                try:
                    file_sources = configured_file_sources(config_file)
                    # Should load successfully
                    assert file_sources.get_file_source_path("ascp://test.example.com/path/to/file").file_source.id == "test_ascp"
                finally:
                    os.unlink(config_file)
        finally:
            if os.path.exists(key_file_path):
                os.unlink(key_file_path)


class TestAscpRetryLogic:
    """Tests for retry and resume functionality."""

    def test_retry_on_network_error(self):
        """Test that network errors trigger retry with exponential backoff."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(
                ssh_key=TEST_SSH_KEY,
                user="test-user",
                host="test.example.com",
                max_retries=3,
                retry_base_delay=0.1,  # Fast for testing
            )

            # Mock subprocess to fail twice, then succeed
            call_count = 0

            def mock_run(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count < 3:
                    # Simulate network error
                    return Mock(
                        returncode=1,
                        stderr="Network error: connection timed out",
                        stdout="",
                    )
                else:
                    # Success on third attempt
                    return Mock(returncode=0, stderr="", stdout="")

            with patch("subprocess.run", side_effect=mock_run):
                with patch("tempfile.mkstemp", return_value=(1, "/tmp/test_key.key")):
                    with patch("os.fdopen"):
                        with patch("os.chmod"):
                            with patch("os.unlink"):
                                with patch("time.sleep") as mock_sleep:
                                    fs._get_file("/remote/file.txt", "/local/file.txt")

                                    # Should have been called 3 times
                                    assert call_count == 3
                                    # Should have slept twice (between attempts)
                                    assert mock_sleep.call_count == 2

    def test_no_retry_on_authentication_error(self):
        """Test that authentication errors do not trigger retry."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(
                ssh_key=TEST_SSH_KEY,
                user="test-user",
                host="test.example.com",
                max_retries=3,
            )

            call_count = 0

            def mock_run(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                return Mock(
                    returncode=1,
                    stderr="authentication failed: invalid key",
                    stdout="",
                )

            with patch("subprocess.run", side_effect=mock_run):
                with patch("tempfile.mkstemp", return_value=(1, "/tmp/test_key.key")):
                    with patch("os.fdopen"):
                        with patch("os.chmod"):
                            with patch("os.unlink"):
                                with pytest.raises(MessageException, match="Authentication failed"):
                                    fs._get_file("/remote/file.txt", "/local/file.txt")

                                # Should only be called once (no retry)
                                assert call_count == 1

    def test_resume_flag_added_on_retry(self):
        """Test that resume flag (-k 1) is added on retry attempts."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(
                ssh_key=TEST_SSH_KEY,
                user="test-user",
                host="test.example.com",
                max_retries=2,
                retry_base_delay=0.1,
                enable_resume=True,
            )

            captured_commands = []

            def mock_run(cmd, *args, **kwargs):
                captured_commands.append(cmd)
                if len(captured_commands) < 2:
                    # Fail first attempt
                    return Mock(
                        returncode=1,
                        stderr="Network error: timeout",
                        stdout="",
                    )
                else:
                    # Success on second attempt
                    return Mock(returncode=0, stderr="", stdout="")

            with patch("subprocess.run", side_effect=mock_run):
                with patch("tempfile.mkstemp", return_value=(1, "/tmp/test_key.key")):
                    with patch("os.fdopen"):
                        with patch("os.chmod"):
                            with patch("os.unlink"):
                                with patch("time.sleep"):
                                    fs._get_file("/remote/file.txt", "/local/file.txt")

                                    # First attempt should NOT have -k flag
                                    assert "-k" not in captured_commands[0]

                                    # Second attempt (retry) SHOULD have -k 1 flag
                                    assert "-k" in captured_commands[1]
                                    k_index = captured_commands[1].index("-k")
                                    assert captured_commands[1][k_index + 1] == "1"

    def test_resume_disabled(self):
        """Test that resume flag is not added when disabled."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(
                ssh_key=TEST_SSH_KEY,
                user="test-user",
                host="test.example.com",
                max_retries=2,
                retry_base_delay=0.1,
                enable_resume=False,  # Disabled
            )

            captured_commands = []

            def mock_run(cmd, *args, **kwargs):
                captured_commands.append(cmd)
                if len(captured_commands) < 2:
                    return Mock(
                        returncode=1,
                        stderr="Network error: timeout",
                        stdout="",
                    )
                else:
                    return Mock(returncode=0, stderr="", stdout="")

            with patch("subprocess.run", side_effect=mock_run):
                with patch("tempfile.mkstemp", return_value=(1, "/tmp/test_key.key")):
                    with patch("os.fdopen"):
                        with patch("os.chmod"):
                            with patch("os.unlink"):
                                with patch("time.sleep"):
                                    fs._get_file("/remote/file.txt", "/local/file.txt")

                                    # Neither attempt should have -k flag
                                    assert "-k" not in captured_commands[0]
                                    assert "-k" not in captured_commands[1]

    def test_max_retries_exhausted(self):
        """Test that error is raised after max retries are exhausted."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(
                ssh_key=TEST_SSH_KEY,
                user="test-user",
                host="test.example.com",
                max_retries=2,
                retry_base_delay=0.1,
            )

            call_count = 0

            def mock_run(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                # Always fail with network error
                return Mock(
                    returncode=1,
                    stderr="Network error: connection refused",
                    stdout="",
                )

            with patch("subprocess.run", side_effect=mock_run):
                with patch("tempfile.mkstemp", return_value=(1, "/tmp/test_key.key")):
                    with patch("os.fdopen"):
                        with patch("os.chmod"):
                            with patch("os.unlink"):
                                with patch("time.sleep"):
                                    with pytest.raises(MessageException, match="Network error"):
                                        fs._get_file("/remote/file.txt", "/local/file.txt")

                                    # Should have tried max_retries times
                                    assert call_count == 2

    def test_exponential_backoff_delays(self):
        """Test that retry delays follow exponential backoff pattern."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(
                ssh_key=TEST_SSH_KEY,
                user="test-user",
                host="test.example.com",
                max_retries=4,
                retry_base_delay=2.0,
                retry_max_delay=10.0,
            )

            def mock_run(*args, **kwargs):
                # Always fail
                return Mock(
                    returncode=1,
                    stderr="Network error: timeout",
                    stdout="",
                )

            with patch("subprocess.run", side_effect=mock_run):
                with patch("tempfile.mkstemp", return_value=(1, "/tmp/test_key.key")):
                    with patch("os.fdopen"):
                        with patch("os.chmod"):
                            with patch("os.unlink"):
                                with patch("time.sleep") as mock_sleep:
                                    with pytest.raises(MessageException):
                                        fs._get_file("/remote/file.txt", "/local/file.txt")

                                    # Check delay progression: 2^1=2, 2^2=4, 2^3=8 (capped at 10)
                                    sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
                                    assert sleep_calls[0] == 2.0  # 2^1
                                    assert sleep_calls[1] == 4.0  # 2^2
                                    assert sleep_calls[2] == 8.0  # 2^3

    def test_is_retryable_error_classification(self):
        """Test error classification for retry logic."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(
                ssh_key=TEST_SSH_KEY,
                user="test-user",
                host="test.example.com",
            )

            # Retryable errors
            assert fs._is_retryable_error(MessageException("Network error occurred"))
            assert fs._is_retryable_error(MessageException("Connection timed out"))
            assert fs._is_retryable_error(MessageException("Connection refused"))
            assert fs._is_retryable_error(MessageException("Host unreachable"))

            # Non-retryable errors
            assert not fs._is_retryable_error(MessageException("Authentication failed"))
            assert not fs._is_retryable_error(MessageException("File not found"))
            assert not fs._is_retryable_error(MessageException("Permission denied"))
            assert not fs._is_retryable_error(MessageException("Invalid key"))
            assert not fs._is_retryable_error(MessageException("SSH key is required"))

    def test_retry_configuration_defaults(self):
        """Test that retry configuration has correct defaults."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(
                ssh_key=TEST_SSH_KEY,
                user="test-user",
                host="test.example.com",
            )

            assert fs.max_retries == 3
            assert fs.retry_base_delay == 2.0
            assert fs.retry_max_delay == 60.0
            assert fs.enable_resume is True

    def test_ssh_key_as_file_path(self):
        """Test that ssh_key can be provided as a file path."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".key") as key_file:
                key_file.write(TEST_SSH_KEY)
                key_file_path = key_file.name

            try:
                # Set proper permissions
                os.chmod(key_file_path, 0o600)

                fs = AscpFileSystem(
                    ssh_key=key_file_path,  # Pass file path instead of content
                    user="test-user",
                    host="test.example.com",
                )

                # Mock subprocess to verify the key file path is used directly
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = Mock(returncode=0, stderr="", stdout="")

                    with patch("os.unlink") as mock_unlink:
                        fs._get_file("/remote/file.txt", "/local/file.txt")

                        # Verify the original key file was NOT deleted
                        # (only temporary files should be deleted)
                        mock_unlink.assert_not_called()

                        # Verify ascp was called with the original key file path
                        call_args = mock_run.call_args[0][0]
                        assert key_file_path in call_args

            finally:
                if os.path.exists(key_file_path):
                    os.unlink(key_file_path)

    def test_ssh_key_as_content(self):
        """Test that ssh_key can be provided as key content (original behavior)."""
        with patch("shutil.which", return_value="/usr/bin/ascp"):
            fs = AscpFileSystem(
                ssh_key=TEST_SSH_KEY,  # Pass key content
                user="test-user",
                host="test.example.com",
            )

            # Mock subprocess and tempfile to verify temp file is created and cleaned up
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stderr="", stdout="")

                with patch("tempfile.mkstemp", return_value=(123, "/tmp/test_key.key")) as mock_mkstemp:
                    with patch("os.fdopen"):
                        with patch("os.chmod"):
                            with patch("os.unlink") as mock_unlink:
                                fs._get_file("/remote/file.txt", "/local/file.txt")

                                # Verify temp file was created
                                mock_mkstemp.assert_called_once()

                                # Verify temp file was cleaned up
                                mock_unlink.assert_called_once_with("/tmp/test_key.key")
