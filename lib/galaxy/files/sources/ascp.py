"""Galaxy file source plugin for Aspera ascp transfers.

This plugin provides download-only functionality using the Aspera ascp command-line tool.
It is designed as a configured plugin (not stock) requiring explicit configuration with
embedded SSH keys.

Architecture:
- ascp.py (this file): Galaxy plugin configuration and lifecycle management
- ascp_fsspec.py: Custom fsspec.AbstractFileSystem implementation

The two-layer design separates concerns:
- Galaxy integration (Pydantic models, template expansion, plugin registration)
- Transfer implementation (ascp command wrapping, retry logic, error handling)

Note: This is Galaxy's only custom fsspec implementation. Other file sources
(s3fs, webdav, etc.) use existing fsspec packages from PyPI. This custom
implementation was necessary because no fsspec implementation exists for ascp.

The implementation is extensible to support future enhancements such as:
- ENA-specific handling with fallback to FTP
- Upload support
- Directory browsing via SSH/SFTP
"""

import logging
from typing import (
    Optional,
    Union,
)
from urllib.parse import urlparse

from galaxy.exceptions import MessageException
from galaxy.files.models import (
    FilesSourceRuntimeContext,
)
from galaxy.files.uris import stream_url_to_file
from galaxy.files.sources._fsspec import (
    CacheOptionsDictType,
    FsspecBaseFileSourceConfiguration,
    FsspecBaseFileSourceTemplateConfiguration,
    FsspecFilesSource,
)
from galaxy.files.sources.ascp_fsspec import AscpFileSystem
from galaxy.util.config_templates import TemplateExpansion

log = logging.getLogger(__name__)

PLUGIN_TYPE = "ascp"


class AscpFilesSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    """Template configuration for Aspera ascp file source.

    This configuration supports template expansion for all fields, allowing
    dynamic configuration based on user context or other variables.

    Note: ssh_key_content is required for SSH authentication. Key content (not file paths)
    is used because Galaxy jobs often run on clusters that don't mount Galaxy's root or
    configuration directories. The configuration block is copied to the job's directory,
    but referenced key paths wouldn't be accessible.
    """

    ascp_path: Union[str, TemplateExpansion] = "ascp"
    ssh_key_content: Union[str, TemplateExpansion]  # SSH key content as string (required)
    ssh_key_passphrase: Union[str, TemplateExpansion, None] = None  # Passphrase for the SSH key (required)
    user: Union[str, TemplateExpansion]  # Required field
    host: Union[str, TemplateExpansion]  # Required field
    rate_limit: Union[str, TemplateExpansion] = "300m"
    port: Union[int, TemplateExpansion] = 33001
    disable_encryption: Union[bool, TemplateExpansion] = True
    max_retries: Union[int, TemplateExpansion] = 5
    retry_base_delay: Union[float, TemplateExpansion] = 5.0
    retry_max_delay: Union[float, TemplateExpansion] = 60.0
    enable_resume: Union[bool, TemplateExpansion] = True
    transfer_timeout: Union[int, TemplateExpansion] = 1800
    fallback_scheme: Union[str, TemplateExpansion, None] = None
    fallback_host: Union[str, TemplateExpansion, None] = None
    fallback_user: Union[str, TemplateExpansion, None] = None


class AscpFilesSourceConfiguration(FsspecBaseFileSourceConfiguration):
    """Resolved runtime configuration for Aspera ascp file source.

    This configuration contains the actual values after template expansion.

    Note: ssh_key_content is required for SSH authentication. Key content (not file paths)
    is used because Galaxy jobs often run on clusters that don't mount Galaxy's root or
    configuration directories. The configuration block is copied to the job's directory,
    but referenced key paths wouldn't be accessible.
    """

    ascp_path: str = "ascp"
    ssh_key_content: str  # SSH key content as string (required)
    ssh_key_passphrase: Optional[str] = None  # Passphrase for the SSH key (optional)
    user: str  # Required field
    host: str  # Required field
    rate_limit: str = "300m"
    port: int = 33001
    disable_encryption: bool = True
    max_retries: int = 5
    retry_base_delay: float = 5.0
    retry_max_delay: float = 60.0
    enable_resume: bool = True
    transfer_timeout: int = 1800
    fallback_scheme: Optional[str] = None
    fallback_host: Optional[str] = None
    fallback_user: Optional[str] = None


class AscpFilesSource(FsspecFilesSource[AscpFilesSourceTemplateConfiguration, AscpFilesSourceConfiguration]):
    """Galaxy file source plugin for Aspera ascp transfers.

    This plugin provides high-speed file downloads using the Aspera ascp protocol.
    It requires the ascp binary to be installed and accessible, along with SSH
    private key content embedded in the configuration.

    Features:
    - Download-only functionality (no upload or browsing in base implementation)
    - Configurable transfer rate limiting
    - Optional encryption disabling for maximum speed
    - Support for both ascp:// and fasp:// URL schemes
    - Automatic retry with exponential backoff for transient failures
    - Resume support for interrupted transfers

    Configuration:
    - ssh_key_content: Required field containing the SSH private key as a string
    - The key content is automatically written to a temporary file during transfers
    - Temporary key files are securely cleaned up after each transfer

    Note: SSH key content (not file paths) is required because Galaxy jobs often run on
    clusters that don't mount Galaxy's root or configuration directories. The configuration
    block is copied to the job's directory, but referenced key paths wouldn't be accessible.

    The plugin is designed to be extensible for future enhancements such as:
    - Subclassing for ENA-specific handling
    - Fallback mechanisms to alternative protocols
    - Upload and browsing capabilities

    Implementation Details:
    This plugin uses a custom fsspec filesystem implementation (AscpFileSystem)
    defined in ascp_fsspec.py. The two-layer design separates Galaxy integration
    from the actual transfer implementation.
    """

    plugin_type = PLUGIN_TYPE
    required_module = AscpFileSystem
    required_package = "fsspec"  # Dummy requirement, need no external package

    template_config_class = AscpFilesSourceTemplateConfiguration
    resolved_config_class = AscpFilesSourceConfiguration

    # Override default capabilities
    supports_pagination = False  # Not applicable for download-only
    supports_search = False  # Not applicable for download-only
    supports_sorting = False  # Not applicable for download-only

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[AscpFilesSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ) -> AscpFileSystem:
        """Instantiate the custom ascp fsspec filesystem.

        Args:
            context: Runtime context with resolved configuration
            cache_options: Cache options for fsspec (not used for ascp)

        Returns:
            Configured AscpFileSystem instance
        """
        config = context.config

        return AscpFileSystem(
            ascp_path=config.ascp_path,
            ssh_key=config.ssh_key_content,
            ssh_key_passphrase=config.ssh_key_passphrase,
            user=config.user,
            host=config.host,
            rate_limit=config.rate_limit,
            port=config.port,
            disable_encryption=config.disable_encryption,
            max_retries=config.max_retries,
            retry_base_delay=config.retry_base_delay,
            retry_max_delay=config.retry_max_delay,
            enable_resume=config.enable_resume,
            transfer_timeout=config.transfer_timeout,
            **cache_options,
        )

    def score_url_match(self, url: str) -> int:
        """Score how well this plugin matches a given URL.

        This method is used by Galaxy to determine which file source plugin
        should handle a given URL. Higher scores indicate better matches.

        Args:
            url: The URL to match against

        Returns:
            Match score (length of matched prefix, or 0 for no match)
        """
        if url.startswith("ascp://"):
            return len("ascp://")
        elif url.startswith("fasp://"):
            return len("fasp://")
        return 0

    # Extension points for subclasses

    def _rewrite_url_for_fallback(self, url: str, config: AscpFilesSourceConfiguration) -> Optional[str]:
        """Rewrite an ascp/fasp URL to the configured fallback URL.

        Replaces the scheme and host, preserving the path. The user component
        is stripped (fallback protocols like FTP are typically anonymous).

        Example (ENA):
            fasp://era-fasp@fasp.sra.ebi.ac.uk/vol1/fastq/ERR123/file.fastq.gz
            → ftp://ftp.sra.ebi.ac.uk/vol1/fastq/ERR123/file.fastq.gz

        Returns None if fallback is not configured or URL cannot be parsed.
        """
        if not config.fallback_scheme or not config.fallback_host:
            return None
        if not url.startswith(("ascp://", "fasp://")):
            return None
        parsed = urlparse(url)
        path = parsed.path or ""
        return f"{config.fallback_scheme}://{config.fallback_host}{path}"

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[AscpFilesSourceConfiguration],
    ) -> None:
        """Download a file from the remote source to a local path.

        Attempts ascp first. If ascp fails and a fallback is configured
        (fallback_scheme + fallback_host), rewrites the URL and retries
        via stream_url_to_file using Galaxy's standard file source machinery.

        Args:
            source_path: Remote source path or URL
            native_path: Local destination path
            context: Runtime context with configuration
        """
        config = context.config
        fallback_url = self._rewrite_url_for_fallback(source_path, config)

        try:
            super()._realize_to(source_path, native_path, context)
            return
        except Exception as e:
            if fallback_url is None:
                raise
            log.warning(
                f"ascp transfer failed for {source_path}: {e}. "
                f"Falling back to {fallback_url}"
            )

        try:
            stream_url_to_file(
                fallback_url,
                target_path=native_path,
            )
            log.info(f"Fallback download succeeded for {fallback_url}")
        except Exception as fallback_exc:
            raise MessageException(
                f"ascp transfer failed for {source_path} and fallback to {fallback_url} also failed: {fallback_exc}"
            ) from fallback_exc


__all__ = ("AscpFilesSource",)
