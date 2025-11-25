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
    """Fsspec filesystem implementation for Aspera ascp transfers.

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
        ssh_key: SSH private key as string content OR path to key file
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
        ascp_path: str = "ascp",
        ssh_key: Optional[str] = None,
        user: Optional[str] = None,
        host: Optional[str] = None,
        rate_limit: str = "300m",
        port: int = 33001,
        disable_encryption: bool = True,
        max_retries: int = 3,
        retry_base_delay: float = 2.0,
        retry_max_delay: float = 60.0,
        enable_resume: bool = True,
        **kwargs: Any,
    ):
        """Initialize the AscpFileSystem.

        Args:
            max_retries: Maximum number of retry attempts for failed transfers (default: 3)
            retry_base_delay: Base delay in seconds for exponential backoff (default: 2.0)
            retry_max_delay: Maximum delay in seconds between retries (default: 60.0)
            enable_resume: Enable resume support for interrupted transfers (default: True)

        Raises:
            MessageException: If ascp binary is not found or required parameters are missing
        """
        super().__init__(**kwargs)
        self.ascp_path = ascp_path
        self.ssh_key = ssh_key
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

        # Verify ascp binary exists
        if not shutil.which(self.ascp_path):
            raise MessageException(
                f"Aspera ascp binary not found at '{self.ascp_path}'. "
                "Please ensure ascp is installed and accessible in your PATH."
            )

    def _get_file(self, rpath: str, lpath: str, **kwargs: Any) -> None:
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
            f"Failed to download {rpath} after {self.max_retries} attempts. "
            f"Last error: {last_exception}"
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

        # Determine if ssh_key is a file path or key content
        # If it looks like a path and the file exists, use it directly
        # Otherwise, treat it as key content and create a temporary file
        key_is_file = False
        key_fd = None
        key_path = None

        # Check if ssh_key is a file path
        if not self.ssh_key.startswith("-----BEGIN") and os.path.isfile(self.ssh_key):
            # It's a file path - use it directly
            key_path = self.ssh_key
            key_is_file = True

            # Verify permissions (should be 0600 or 0400)
            stat_info = os.stat(key_path)
            mode = stat_info.st_mode & 0o777
            if mode not in (0o600, 0o400):
                log.warning(
                    f"SSH key file {key_path} has permissions {oct(mode)}, "
                    "ascp may require 0600 or 0400"
                )

        try:
            # If not using an existing file, create temporary file for key content
            if not key_is_file:
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

            # Add resume flag if enabled and this is a retry attempt
            if self.enable_resume and attempt > 0:
                cmd.extend(["-k", "1"])  # Resume level 1: check file size
                log.debug(f"Resume enabled for retry attempt {attempt + 1}")

            # Add source and destination
            cmd.append(f"{user}@{host}:{remote_path}")
            cmd.append(lpath)

            log.debug(f"Executing ascp command (key path hidden): {self._sanitize_cmd_for_log(cmd)}")

            # Execute ascp
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,  # We'll handle errors manually
            )

            if result.returncode != 0:
                self._handle_ascp_error(result, remote_path)

            log.info(f"Successfully downloaded {remote_path} to {lpath}")

        except subprocess.SubprocessError as e:
            raise MessageException(f"Failed to execute ascp command: {e}") from e
        except OSError as e:
            raise MessageException(f"File system error during ascp transfer: {e}") from e
        finally:
            # Only cleanup temporary key file (not user-provided files)
            if not key_is_file:
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

        Retryable errors include:
        - Network errors (connection refused, timeouts, etc.)
        - Transient server errors

        Non-retryable errors include:
        - Authentication failures
        - File not found
        - Permission denied
        - Invalid SSH key

        Args:
            exception: The exception to check

        Returns:
            True if the error is retryable, False otherwise
        """
        error_msg = str(exception).lower()

        # Non-retryable error patterns
        non_retryable_patterns = [
            "authentication failed",
            "file not found",
            "remote file not found",
            "permission denied",
            "invalid key",
            "ssh key is required",
            "user and host must be specified",
        ]

        if any(pattern in error_msg for pattern in non_retryable_patterns):
            return False

        # Retryable error patterns
        retryable_patterns = [
            "network error",
            "connection",
            "timeout",
            "timed out",
            "refused",
            "unreachable",
        ]

        return any(pattern in error_msg for pattern in retryable_patterns)

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
        elif "connection" in stderr.lower() or "network" in stderr.lower():
            raise MessageException(
                f"Network error while downloading {remote_path}. "
                "Please check your network connection and try again."
            )
        elif "timed out" in stderr.lower() or "timeout" in stderr.lower():
            raise MessageException(f"Transfer timed out for {remote_path}. Please try again later.")
        else:
            # Generic error message
            error_msg = stderr or stdout or "Unknown error"
            raise MessageException(
                f"ascp transfer failed for {remote_path} with exit code {result.returncode}. "
                f"Error: {error_msg}"
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
