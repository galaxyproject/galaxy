"""Galaxy file source plugin for Aspera ascp high-speed transfers.

This plugin provides download-only functionality using the Aspera ascp command-line tool.
It is designed as a configured plugin (not stock) requiring explicit configuration with
embedded SSH keys.

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

from galaxy.files.models import (
    FilesSourceRuntimeContext,
)
from galaxy.files.sources._fsspec import (
    CacheOptionsDictType,
    FsspecBaseFileSourceConfiguration,
    FsspecBaseFileSourceTemplateConfiguration,
    FsspecFilesSource,
)
from galaxy.util.config_templates import TemplateExpansion

try:
    from .ascp_fsspec import AscpFileSystem
except ImportError:
    AscpFileSystem = None  # type: ignore[assignment,misc]


log = logging.getLogger(__name__)

PLUGIN_TYPE = "ascp"
REQUIRED_PACKAGE = "ascp"  # Note: This is the binary, not a Python package


class AscpFilesSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    """Template configuration for Aspera ascp file source.

    This configuration supports template expansion for all fields, allowing
    dynamic configuration based on user context or other variables.

    Note: Exactly one of ssh_key_file or ssh_key_content must be provided.
    """

    ascp_path: Union[str, TemplateExpansion] = "ascp"
    ssh_key_file: Union[str, TemplateExpansion, None] = None  # Path to SSH key file
    ssh_key_content: Union[str, TemplateExpansion, None] = None  # SSH key content as string
    user: Union[str, TemplateExpansion]  # Required field
    host: Union[str, TemplateExpansion]  # Required field
    rate_limit: Union[str, TemplateExpansion] = "300m"
    port: Union[int, TemplateExpansion] = 33001
    disable_encryption: Union[bool, TemplateExpansion] = True
    max_retries: Union[int, TemplateExpansion] = 3
    retry_base_delay: Union[float, TemplateExpansion] = 2.0
    retry_max_delay: Union[float, TemplateExpansion] = 60.0
    enable_resume: Union[bool, TemplateExpansion] = True


class AscpFilesSourceConfiguration(FsspecBaseFileSourceConfiguration):
    """Resolved runtime configuration for Aspera ascp file source.

    This configuration contains the actual values after template expansion.

    Note: Exactly one of ssh_key_file or ssh_key_content must be provided.
    """

    ascp_path: str = "ascp"
    ssh_key_file: Optional[str] = None  # Path to SSH key file
    ssh_key_content: Optional[str] = None  # SSH key content as string
    user: str  # Required field
    host: str  # Required field
    rate_limit: str = "300m"
    port: int = 33001
    disable_encryption: bool = True
    max_retries: int = 3
    retry_base_delay: float = 2.0
    retry_max_delay: float = 60.0
    enable_resume: bool = True


class AscpFilesSource(FsspecFilesSource[AscpFilesSourceTemplateConfiguration, AscpFilesSourceConfiguration]):
    """Galaxy file source plugin for Aspera ascp transfers.

    This plugin provides high-speed file downloads using the Aspera ascp protocol.
    It requires the ascp binary to be installed and accessible, along with appropriate
    SSH credentials configured.

    Features:
    - Download-only functionality (no upload or browsing in base implementation)
    - Configurable transfer rate limiting
    - Optional encryption disabling for maximum speed
    - Support for both ascp:// and fasp:// URL schemes

    The plugin is designed to be extensible for future enhancements such as:
    - Subclassing for ENA-specific handling
    - Retry logic with exponential backoff
    - Fallback mechanisms to alternative protocols
    - Upload and browsing capabilities
    """

    plugin_type = PLUGIN_TYPE
    required_module = AscpFileSystem
    required_package = REQUIRED_PACKAGE

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

        Raises:
            Exception: If AscpFileSystem module is not available
        """
        if AscpFileSystem is None:
            raise self.required_package_exception

        config = context.config

        # Validate that exactly one of ssh_key_file or ssh_key_content is provided
        if config.ssh_key_file and config.ssh_key_content:
            raise ValueError("Cannot specify both ssh_key_file and ssh_key_content. Please provide only one.")
        if not config.ssh_key_file and not config.ssh_key_content:
            raise ValueError("Must specify either ssh_key_file or ssh_key_content for SSH authentication.")

        # Determine which key parameter to use
        ssh_key = config.ssh_key_file if config.ssh_key_file else config.ssh_key_content

        return AscpFileSystem(
            ascp_path=config.ascp_path,
            ssh_key=ssh_key,
            user=config.user,
            host=config.host,
            rate_limit=config.rate_limit,
            port=config.port,
            disable_encryption=config.disable_encryption,
            max_retries=config.max_retries,
            retry_base_delay=config.retry_base_delay,
            retry_max_delay=config.retry_max_delay,
            enable_resume=config.enable_resume,
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

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[AscpFilesSourceConfiguration],
    ) -> None:
        """Download a file from the remote source to a local path.

        This method can be overridden in subclasses to add:
        - Retry logic with exponential backoff
        - Fallback to alternative protocols (e.g., FTP)
        - Progress monitoring
        - Custom error handling

        Args:
            source_path: Remote source path or URL
            native_path: Local destination path
            context: Runtime context with configuration
        """
        super()._realize_to(source_path, native_path, context)


__all__ = ("AscpFilesSource",)
