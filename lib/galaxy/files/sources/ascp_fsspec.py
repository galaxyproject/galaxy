"""Custom fsspec filesystem implementation for Aspera ascp transfers.

This module provides an fsspec-compatible filesystem wrapper around the Aspera ascp
command-line tool for high-speed file transfers. It is designed to be extensible
for future enhancements such as ENA-specific handling, retry logic, and fallback mechanisms.
"""

import logging
import os
import shutil
import subprocess
import tempfile
import time
from typing import (
    Any,
    Optional,
)
from urllib.parse import urlparse

from fsspec import AbstractFileSystem

from galaxy.exceptions import MessageException

log = logging.getLogger(__name__)


class AscpFileSystem(AbstractFileSystem):
    """Custom fsspec filesystem implementation for Aspera ascp transfers.

    This module implements fsspec.AbstractFileSystem for the ascp command-line tool.
    It is used by the Galaxy file source plugin in ascp.py but is designed to be
    independent and reusable.

    Architecture:
    - ascp.py: Galaxy plugin configuration and lifecycle management
    - ascp_fsspec.py (this file): Custom fsspec.AbstractFileSystem implementation

    The two-layer design separates concerns:
    - Galaxy integration (Pydantic models, template expansion, plugin registration)
    - Transfer implementation (ascp command wrapping, retry logic, error handling)

    Note: This is Galaxy's only custom fsspec implementation. Other file sources
    (s3fs, webdav, etc.) use existing fsspec packages from PyPI. This custom
    implementation was necessary because no fsspec implementation exists for ascp.

    This class wraps the ascp command-line tool to provide download functionality
    through the fsspec interface. It handles SSH key management, command construction,
    and error handling.

    The implementation is designed to be extensible for future enhancements:
    - Subclassing for ENA-specific handling
    - Adding retry logic with exponential backoff
    - Implementing fallback mechanisms (e.g., to FTP)
    - Supporting additional ascp features

    Args:
        ascp_path: Path to the ascp binary (default: "ascp")
        ssh_key: SSH private key content as a string (required)
        ssh_key_passphrase: SSH private key passphrase as a string
        user: Username for ascp connection (e.g., "era-fasp")
        host: Hostname (e.g., "fasp.sra.ebi.ac.uk")
        rate_limit: Transfer rate limit (default: "300m")
        port: SSH port (default: 33001)
        disable_encryption: Use -T flag for maximum speed (default: True)
        max_retries: Maximum retry attempts for failed transfers (default: 3)
        retry_base_delay: Base delay for exponential backoff (default: 2.0)
        retry_max_delay: Maximum delay between retries (default: 60.0)
        enable_resume: Enable resume for interrupted transfers (default: True)
        **kwargs: Additional arguments passed to AbstractFileSystem
    """

    protocol = ("ascp", "fasp")  # Support both ascp:// and fasp:// URLs

    def __init__(
        self,
        ssh_key: str,
        ssh_key_passphrase: Optional[str] = None,
        ascp_path: str = "ascp",
        user: Optional[str] = None,
        host: Optional[str] = None,
        rate_limit: str = "300m",
        port: int = 33001,
        disable_encryption: bool = True,
        max_retries: int = 5,
        retry_base_delay: float = 5.0,
        retry_max_delay: float = 60.0,
        enable_resume: bool = True,
        transfer_timeout: int = 1800,
        **kwargs: Any,
    ):
        """Initialize the AscpFileSystem.

        Args:
            max_retries: Maximum number of retry attempts for failed transfers (default: 5)
            retry_base_delay: Base delay in seconds for exponential backoff (default: 5.0)
            retry_max_delay: Maximum delay in seconds between retries (default: 60.0)
            enable_resume: Enable resume support for interrupted transfers (default: True)
            transfer_timeout: Timeout in seconds for each ascp subprocess call (default: 1800)

        Raises:
            MessageException: If ascp binary is not found or required parameters are missing
        """
        super().__init__(**kwargs)
        self.ascp_path = ascp_path
        self.ssh_key = ssh_key
        self.ssh_key_passphrase = ssh_key_passphrase
        self.user = user
        self.host = host
        self.rate_limit = rate_limit
        self.port = port
        self.disable_encryption = disable_encryption

        # Retry configuration
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self.retry_max_delay = retry_max_delay
        self.enable_resume = enable_resume
        self.transfer_timeout = transfer_timeout

        # Verify ascp binary exists
        if not shutil.which(self.ascp_path):
            raise MessageException(
                f"Aspera ascp binary not found at '{self.ascp_path}'. "
                "Please ensure ascp is installed and accessible in your PATH."
            )

    def isdir(self, path):
        """Is this entry directory-like?"""
        return False

    def isfile(self, path):
        """Is this entry file-like?"""
        return True

    def get_file(self, rpath: str, lpath: str, **kwargs: Any) -> None:
        """Download a file from remote path to local path using ascp with retry logic.

        This method handles:
        - Retry logic with exponential backoff for transient failures
        - Resume support for interrupted transfers
        - Secure temporary SSH key file creation
        - ascp command construction with appropriate flags
        - Subprocess execution with error handling
        - Cleanup of temporary files

        Args:
            rpath: Remote file path (can be full URL or just the path component)
            lpath: Local destination path
            **kwargs: Additional arguments (unused, for fsspec compatibility)

        Raises:
            MessageException: If download fails after all retries
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                self._execute_ascp_transfer(rpath, lpath, attempt)
                return  # Success!
            except MessageException as e:
                last_exception = e

                # Check if error is retryable
                if self._is_retryable_error(e) and attempt < self.max_retries - 1:
                    delay = min(self.retry_base_delay ** (attempt + 1), self.retry_max_delay)
                    log.warning(
                        f"ascp transfer failed (attempt {attempt + 1}/{self.max_retries}): {e}. "
                        f"Retrying in {delay:.1f} seconds..."
                    )
                    time.sleep(delay)
                else:
                    # Non-retryable error or last attempt
                    raise

        # Should not reach here, but just in case
        raise MessageException(
            f"Failed to download {rpath} after {self.max_retries} attempts. Last error: {last_exception}"
        )

    def _execute_ascp_transfer(self, rpath: str, lpath: str, attempt: int) -> None:
        """Execute a single ascp transfer attempt.

        Args:
            rpath: Remote file path
            lpath: Local destination path
            attempt: Current attempt number (0-indexed)

        Raises:
            MessageException: If transfer fails
        """
        # Parse URL if provided, otherwise use configured host/user
        parsed_url = self._parse_url(rpath)
        user = parsed_url.get("user") or self.user
        host = parsed_url.get("host") or self.host
        port = parsed_url.get("port") or self.port
        remote_path = parsed_url.get("path", rpath)

        if not user or not host:
            raise MessageException(
                "User and host must be specified either in configuration or in the URL. "
                f"Got user='{user}', host='{host}'"
            )

        # Type narrowing: after validation, user and host are guaranteed to be str
        assert isinstance(user, str)
        assert isinstance(host, str)

        if not self.ssh_key:
            raise MessageException("SSH key is required for ascp authentication.")

        # Create temporary file for key content
        key_fd = None
        key_path = None

        try:
            # Create temporary file for key content
            key_fd, key_path = tempfile.mkstemp(suffix=".key", text=True)

            # Write key with proper permissions (required by ascp)
            os.chmod(key_path, 0o600)
            with os.fdopen(key_fd, "w") as key_file:
                key_file.write(self.ssh_key)
            key_fd = None  # Prevent double-close

            # Type narrowing: key_path is guaranteed to be set by this point
            assert key_path is not None

            # Build ascp command
            cmd = [
                self.ascp_path,
                "-i",
                key_path,
                "-l",
                self.rate_limit,
                "-P",
                str(port),
            ]

            # Add encryption flag if disabled
            if self.disable_encryption:
                cmd.append("-T")

            # Add resume flag if enabled (on all attempts to handle interrupted transfers)
            if self.enable_resume:
                cmd.extend(["-k", "1"])  # Resume level 1: check file size
                if attempt > 0:
                    log.debug(f"Resume enabled for retry attempt {attempt + 1}")

            # Add source and destination
            cmd.append(f"{user}@{host}:{remote_path}")
            cmd.append(lpath)

            log.debug(f"Executing ascp command (key path hidden): {self._sanitize_cmd_for_log(cmd)}")

            if self.ssh_key_passphrase:
                env = os.environ.copy()
                env["ASPERA_SCP_PASS"] = self.ssh_key_passphrase
            else:
                env = None
            # Execute ascp
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,  # We'll handle errors manually
                    env=env,
                    timeout=self.transfer_timeout,
                )
            except subprocess.TimeoutExpired:
                raise MessageException(
                    f"ascp transfer timed out after {self.transfer_timeout} seconds for {remote_path}. "
                    "Consider increasing the transfer_timeout configuration."
                )

            if result.returncode != 0:
                self._handle_ascp_error(result, remote_path)

            log.info(f"Successfully downloaded {remote_path} to {lpath}")

        except subprocess.SubprocessError as e:
            raise MessageException(f"Failed to execute ascp command: {e}") from e
        except OSError as e:
            raise MessageException(f"File system error during ascp transfer: {e}") from e
        finally:
            # Cleanup temporary key file
            if key_fd is not None:
                try:
                    os.close(key_fd)
                except Exception:
                    pass  # Best effort
            if key_path is not None:
                try:
                    os.unlink(key_path)
                except Exception:
                    pass  # Best effort

    def _is_retryable_error(self, exception: MessageException) -> bool:
        """Determine if an error is worth retrying.

        Uses a blacklist approach: all errors are retried UNLESS they match a
        known non-retryable pattern. This is safer than a whitelist because
        transient errors (e.g., "Session Stop", "unable to connect") can have
        many different message formats that are hard to enumerate.

        Non-retryable errors (will NOT be retried):
        - Authentication failures
        - File not found
        - Permission denied
        - Invalid SSH key
        - Configuration errors (missing user/host)

        Everything else is assumed transient and WILL be retried.

        Args:
            exception: The exception to check

        Returns:
            True if the error is retryable, False otherwise
        """
        error_msg = str(exception).lower()

        # Non-retryable error patterns — known permanent failures
        non_retryable_patterns = [
            "authentication failed",
            "file not found",
            "remote file not found",
            "permission denied",
            "invalid key",
            "ssh key is required",
            "user and host must be specified",
            "ascp binary not found",
        ]

        if any(pattern in error_msg for pattern in non_retryable_patterns):
            return False

        # Everything else is assumed retryable (network errors, session stops,
        # connection failures, timeouts, server errors, etc.)
        return True

    def _parse_url(self, url: str) -> dict[str, Any]:
        """Parse ascp:// or fasp:// URL to extract components.

        Supports URLs in the format:
        - ascp://user@host:port/path
        - fasp://user@host:port/path
        - /path (uses configured host/user)

        Args:
            url: URL or path to parse

        Returns:
            Dictionary with keys: user, host, port, path
        """
        if url.startswith(("ascp://", "fasp://")):
            parsed = urlparse(url)
            return {
                "user": parsed.username,
                "host": parsed.hostname,
                "port": parsed.port,
                "path": parsed.path.lstrip("/") if parsed.path else "",
            }
        else:
            # Assume it's just a path
            return {"user": None, "host": None, "port": None, "path": url}

    def _handle_ascp_error(self, result: subprocess.CompletedProcess, remote_path: str) -> None:
        """Parse ascp error output and raise appropriate exception.

        This method can be extended in subclasses to handle specific error types
        (e.g., for retry logic or fallback mechanisms).

        Args:
            result: Completed subprocess result
            remote_path: Remote path that was being accessed

        Raises:
            MessageException: With user-friendly error message
        """
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()

        # Check for common error patterns
        if "authentication" in stderr.lower() or "permission denied" in stderr.lower():
            raise MessageException(
                f"Authentication failed for {remote_path}. "
                "Please verify your SSH key is correct and has appropriate permissions."
            )
        elif "no such file" in stderr.lower() or "not found" in stderr.lower():
            raise MessageException(f"Remote file not found: {remote_path}")
        elif "connection" in stderr.lower() or "connect" in stderr.lower() or "network" in stderr.lower():
            raise MessageException(
                f"Network error while downloading {remote_path}. Please check your network connection and try again."
            )
        elif "session stop" in stderr.lower():
            raise MessageException(
                f"ascp session stopped while downloading {remote_path}. Error: {stderr.strip()}"
            )
        elif "timed out" in stderr.lower() or "timeout" in stderr.lower():
            raise MessageException(f"Transfer timed out for {remote_path}. Please try again later.")
        else:
            # Generic error message
            error_msg = stderr or stdout or "Unknown error"
            raise MessageException(
                f"ascp transfer failed for {remote_path} with exit code {result.returncode}. Error: {error_msg}"
            )

    def _sanitize_cmd_for_log(self, cmd: list[str]) -> str:
        """Sanitize command for logging by hiding sensitive information.

        Args:
            cmd: Command list

        Returns:
            Sanitized command string safe for logging
        """
        sanitized = []
        hide_next = False
        for arg in cmd:
            if hide_next:
                sanitized.append("<hidden>")
                hide_next = False
            elif arg == "-i":
                sanitized.append(arg)
                hide_next = True
            else:
                sanitized.append(arg)
        return " ".join(sanitized)

    # Optional: Methods for future extensibility

    def _open(self, path: str, mode: str = "rb", **kwargs: Any):
        """Open a file for reading.

        Not implemented in the base version as we focus on download-only functionality.
        Can be implemented in subclasses if needed.
        """
        raise NotImplementedError("Direct file opening is not supported. Use get_file() instead.")

    def ls(self, path: str, detail: bool = True, **kwargs: Any) -> list:
        """List directory contents.

        Not implemented in the base version as we focus on download-only functionality.
        Can be implemented in subclasses using SSH/SFTP for browsing.
        """
        raise NotImplementedError("Directory listing is not supported in this version.")

    def info(self, path: str, **kwargs: Any) -> dict:
        """Get file information.

        Not implemented in the base version as we focus on download-only functionality.
        Can be implemented in subclasses using SSH/SFTP.
        """
        raise NotImplementedError("File info is not supported in this version.")


__all__ = ("AscpFileSystem",)
