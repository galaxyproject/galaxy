"""Models for rule builder column targets.

This module defines the data models and types used by Galaxy's workbook upload system
to map user-provided column headers to specific metadata fields. When users upload
Excel/CSV workbooks containing dataset URIs and metadata, these models define what
column types are available and how they should be interpreted.

Example workbook row:
    URI                        | Name      | MD5                              | Genome
    http://example.com/data.gz | Sample_1  | 5d41402abc4b2a76b9719d911017c592 | hg19

The column headers "URI", "Name", "MD5", and "Genome" are parsed and mapped to
target types "url", "name", "hash_md5", and "dbkey" respectively.
"""

from typing import (
    Literal,
    Optional,
)

import yaml
from pydantic import (
    BaseModel,
    RootModel,
)

from galaxy.util.resources import resource_string

# Defines whether a column target is used when importing individual datasets or collections
RuleBuilderImportType = Literal["datasets", "collections"]

# Defines the upload modes where a column target is applicable
# - raw: Direct URI/URL upload
# - ftp: FTP server upload
# - datasets: Existing datasets in history
# - library_datasets: Datasets from data libraries
# - collection_contents: Elements from existing collections
RuleBuilderModes = Literal[
    "raw",
    "ftp",
    "datasets",
    "library_datasets",
    "collection_contents",
]


class ColumnTarget(BaseModel):
    """Defines a single column target type that can appear in a workbook.

    Each target type represents a specific piece of metadata or structural information
    that can be associated with uploaded datasets.

    Attributes:
        label: User-facing label for this column type in UI
        help: Detailed help text explaining what this column is for
        modes: Which upload modes support this column type (None = all modes)
        importType: Whether used for datasets, collections, or both (None = both)
        multiple: If True, can have multiple columns of this type (e.g., multiple tags)
        columnHeader: Default header text when generating workbooks
        advanced: If True, considered an advanced/optional column
        requiresFtp: If True, only available when FTP upload is configured
        example_column_names: Example header texts that would map to this target type

    Example:
        For the "hash_md5" target type:
        - label: "Hash (MD5)"
        - example_column_names: ["MD5", "MD5 hash", "MD5-Sum"]
        - help: "This is the MD5 hash of the URI..."
    """

    label: str
    help: Optional[str]
    modes: Optional[list[RuleBuilderModes]] = None
    importType: Optional[RuleBuilderImportType] = None
    multiple: Optional[bool] = False
    columnHeader: Optional[str] = None
    advanced: Optional[bool] = False
    requiresFtp: Optional[bool] = False
    example_column_names: Optional[list[str]] = None

    @property
    def example_column_names_as_str(self) -> Optional[str]:
        """Format example column names as a quoted, comma-separated string for display."""
        if self.example_column_names:
            return '"' + '", "'.join(self.example_column_names) + '"'
        return ""


# All valid column target type identifiers used internally by Galaxy
# These are the normalized keys that user-provided column headers map to
RuleBuilderMappingTargetKey = Literal[
    "list_identifiers",  # List structure identifiers (e.g., "Sample_A")
    "paired_identifier",  # Paired-end indicator (1/2, forward/reverse)
    "paired_or_unpaired_identifier",  # Optional paired-end indicator
    "collection_name",  # Name for grouping datasets into collections
    "name_tag",  # Name-based tags (propagated to derived datasets)
    "tags",  # General purpose tags
    "group_tags",  # Group tags for factorial experiments
    "name",  # Dataset name in history
    "dbkey",  # Genome build (e.g., hg19, mm10)
    "hash_sha1",  # SHA-1 checksum for verification
    "hash_md5",  # MD5 checksum for verification
    "hash_sha256",  # SHA-256 checksum for verification
    "hash_sha512",  # SHA-512 checksum for verification
    "file_type",  # Galaxy datatype (e.g., fastqsanger, bam)
    "url",  # URI/URL to download file from
    "url_deferred",  # URI/URL for deferred download (on-demand)
    "info",  # Unstructured text displayed in history
    "ftp_path",  # Path relative to user's FTP directory
    "deferred",  # Boolean: defer download until needed
    "to_posix_lines",  # Boolean: convert line endings
    "space_to_tab",  # Boolean: convert spaces to tabs
    "auto_decompress",  # Boolean: auto-decompress if compressed
]


# Mapping of target type keys to their full ColumnTarget definitions
ColumnTargetsConfig = dict[RuleBuilderMappingTargetKey, ColumnTarget]
ColumnTargetsConfigRootModel = RootModel[ColumnTargetsConfig]


def target_models() -> ColumnTargetsConfig:
    """Load all column target definitions from rule_targets.yml.

    Returns:
        Dictionary mapping target type keys (e.g., "name", "url") to their ColumnTarget definitions

    Example:
        targets = target_models()
        name_target = targets["name"]
        # name_target.label == "Name"
        # name_target.help == "This is just the name of the dataset..."
    """
    column_targets_str = resource_string(__name__, "rule_targets.yml")
    column_targets_raw = yaml.safe_load(column_targets_str)
    return ColumnTargetsConfigRootModel.model_validate(column_targets_raw).root


def target_model_by_type(type: RuleBuilderMappingTargetKey) -> ColumnTarget:
    """Get the ColumnTarget definition for a specific target type.

    Args:
        type: The target type key (e.g., "url", "name", "hash_md5")

    Returns:
        The ColumnTarget definition with label, help text, and other metadata

    Example:
        md5_target = target_model_by_type("hash_md5")
        # md5_target.label == "Hash (MD5)"
        # md5_target.example_column_names == ["MD5", "MD5 hash", "MD5-Sum"]
    """
    return target_models()[type]


# Common metadata column types that should be available for any URI-based workbook upload.
# These columns are universally applicable across different upload modes and provide
# standard dataset metadata (names, genome builds, tags) and file integrity verification (hashes).
# This list is used when generating workbook templates to show users what optional columns they can add.
COMMON_COLUMN_TARGETS = [
    target_model_by_type("name"),  # Dataset name
    target_model_by_type("dbkey"),  # Genome build
    target_model_by_type("info"),  # Description text
    target_model_by_type("file_type"),  # Galaxy datatype
    target_model_by_type("tags"),  # General tags
    target_model_by_type("group_tags"),  # Group tags
    target_model_by_type("name_tag"),  # Name tags
    target_model_by_type("hash_md5"),  # MD5 checksum
    target_model_by_type("hash_sha1"),  # SHA-1 checksum
    target_model_by_type("hash_sha256"),  # SHA-256 checksum
    target_model_by_type("hash_sha512"),  # SHA-512 checksum
]
