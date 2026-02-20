"""Unit tests for FTP file source plugin.

Integration tests (test_file_source_ftp_*) hit real FTP servers.
Unit tests (TestFtpRetry*) verify retry logic with mocked PyFilesystem2.
"""

import os
import tempfile
from unittest.mock import (
    Mock,
    patch,
)

import pytest
from fs.errors import (
    OperationTimeout,
    PermissionDenied,
    RemoteConnectionError,
    ResourceNotFound,
)

from galaxy.exceptions import MessageException
from galaxy.files.sources.ftp import (
    FTPFileSourceConfiguration,
    FtpFilesSource,
)
from ._util import (
    assert_realizes_contains,
    configured_file_sources,
    user_context_fixture,
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "ftp_file_sources_conf.yml")


# ---------------------------------------------------------------------------
# Integration tests (require network access to real FTP servers)
# ---------------------------------------------------------------------------


def test_file_source_ftp_specific():
    test_url = "ftp://ftp.gnu.org/README"
    user_context = user_context_fixture()
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    file_source_pair = file_sources.get_file_source_path(test_url)

    assert file_source_pair.path == test_url
    assert file_source_pair.file_source.id == "test1"

    try:
        assert_realizes_contains(
            file_sources,
            test_url,
            "This is ftp.gnu.org, the FTP server of the the GNU project.",
            user_context=user_context,
        )
    except RemoteConnectionError:
        pytest.skip("ftp.gnu.org not available")


def test_file_source_ftp_generic():
    test_url = "ftp://ftp.slackware.com/welcome.msg"
    user_context = user_context_fixture()
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    file_source_pair = file_sources.get_file_source_path(test_url)

    assert file_source_pair.path == test_url
    assert file_source_pair.file_source.id == "test2"

    assert_realizes_contains(
        file_sources,
        test_url,
        "Oregon State University",
        user_context=user_context,
    )


# ---------------------------------------------------------------------------
# Unit tests for FTP retry logic
# ---------------------------------------------------------------------------


class TestFtpConfigDefaults:
    """Test that FTP config defaults are correct."""

    def test_timeout_default(self):
        """Default timeout should be 60s (not the old 10s)."""
        fields = FTPFileSourceConfiguration.model_fields
        assert fields["timeout"].default == 60

    def test_retry_defaults(self):
        """Default retry config: 3 retries, 5.0s base delay."""
        fields = FTPFileSourceConfiguration.model_fields
        assert fields["max_retries"].default == 3
        assert fields["retry_base_delay"].default == 5.0


class TestFtpRetryPipeline:
    """Test the FTP retry pipeline: error → retry-or-fail.

    Uses a mock FTPFS to simulate errors without hitting real servers.
    The contract: RemoteConnectionError, OperationTimeout, and OSError
    are retried; ResourceNotFound and PermissionDenied are not.
    """

    @staticmethod
    def _make_ftp_source(max_retries=3, retry_base_delay=0.1, timeout=60):
        """Create an FtpFilesSource with a YAML config."""
        config = {
            "type": "ftp",
            "id": "test_ftp",
            "label": "Test FTP",
            "host": "ftp.example.com",
            "max_retries": max_retries,
            "retry_base_delay": retry_base_delay,
            "timeout": timeout,
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            import yaml

            yaml.dump([config], f)
            config_file = f.name

        try:
            file_sources = configured_file_sources(config_file)
            pair = file_sources.get_file_source_path("ftp://ftp.example.com/some/file.txt")
            return pair.file_source, pair, file_sources, config_file
        except Exception:
            os.unlink(config_file)
            raise

    @staticmethod
    def _run_realize(source, pair, file_sources, error_sequence):
        """Run realize_to with a mock FTPFS that raises errors in sequence.

        error_sequence: list of exceptions to raise, or None for success.
        Returns the number of download calls made.
        """
        call_count = 0

        def mock_download(path, write_file):
            nonlocal call_count
            call_count += 1
            if call_count <= len(error_sequence) and error_sequence[call_count - 1] is not None:
                raise error_sequence[call_count - 1]
            # Success: write some data
            write_file.write(b"file contents")

        mock_fs = Mock()
        mock_fs.download = mock_download
        mock_fs.__enter__ = Mock(return_value=mock_fs)
        mock_fs.__exit__ = Mock(return_value=False)

        with patch.object(type(source), "_open_fs", return_value=mock_fs):
            with patch("time.sleep"):
                source.realize_to(pair.path, "/tmp/test_output.txt")

        return call_count

    def test_retry_on_remote_connection_error(self):
        """RemoteConnectionError → retried."""
        source, pair, fs, config_file = self._make_ftp_source()
        try:
            count = self._run_realize(source, pair, fs, [
                RemoteConnectionError("connection lost"),
                RemoteConnectionError("connection lost"),
                None,  # Success on 3rd attempt
            ])
            assert count == 3
        finally:
            os.unlink(config_file)

    def test_retry_on_operation_timeout(self):
        """OperationTimeout → retried."""
        source, pair, fs, config_file = self._make_ftp_source()
        try:
            count = self._run_realize(source, pair, fs, [
                OperationTimeout("read timed out"),
                None,  # Success on 2nd attempt
            ])
            assert count == 2
        finally:
            os.unlink(config_file)

    def test_retry_on_os_error(self):
        """OSError (e.g., broken pipe) → retried."""
        source, pair, fs, config_file = self._make_ftp_source()
        try:
            count = self._run_realize(source, pair, fs, [
                OSError("Broken pipe"),
                None,
            ])
            assert count == 2
        finally:
            os.unlink(config_file)

    def test_no_retry_on_resource_not_found(self):
        """ResourceNotFound → immediate failure, no retry."""
        source, pair, fs, config_file = self._make_ftp_source()
        try:
            with pytest.raises(MessageException, match="FTP download failed"):
                self._run_realize(source, pair, fs, [
                    ResourceNotFound("/nonexistent"),
                ])
        finally:
            os.unlink(config_file)

    def test_no_retry_on_permission_denied(self):
        """PermissionDenied → immediate failure, no retry."""
        source, pair, fs, config_file = self._make_ftp_source()
        try:
            with pytest.raises(MessageException, match="FTP download failed"):
                self._run_realize(source, pair, fs, [
                    PermissionDenied("/secret"),
                ])
        finally:
            os.unlink(config_file)

    def test_max_retries_exhausted(self):
        """All retries exhausted → MessageException."""
        source, pair, fs, config_file = self._make_ftp_source(max_retries=2)
        try:
            with pytest.raises(MessageException, match="failed after 2 attempts"):
                self._run_realize(source, pair, fs, [
                    RemoteConnectionError("fail"),
                    RemoteConnectionError("fail"),
                ])
        finally:
            os.unlink(config_file)

    def test_exponential_backoff(self):
        """Retry delays follow exponential backoff."""
        source, pair, fs, config_file = self._make_ftp_source(max_retries=4, retry_base_delay=2.0)
        try:
            mock_fs = Mock()
            mock_fs.download = Mock(side_effect=RemoteConnectionError("fail"))
            mock_fs.__enter__ = Mock(return_value=mock_fs)
            mock_fs.__exit__ = Mock(return_value=False)

            with patch.object(type(source), "_open_fs", return_value=mock_fs):
                with patch("time.sleep") as mock_sleep:
                    with pytest.raises(MessageException):
                        source.realize_to(pair.path, "/tmp/test_output.txt")

                    sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
                    assert sleep_calls[0] == 2.0   # 2^1
                    assert sleep_calls[1] == 4.0   # 2^2
                    assert sleep_calls[2] == 8.0   # 2^3
        finally:
            os.unlink(config_file)

    def test_success_on_first_attempt(self):
        """No errors → single attempt, no retry."""
        source, pair, fs, config_file = self._make_ftp_source()
        try:
            count = self._run_realize(source, pair, fs, [None])
            assert count == 1
        finally:
            os.unlink(config_file)
