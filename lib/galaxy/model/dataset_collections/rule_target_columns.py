"""Column header parsing for workbook uploads.

This module handles the flexible parsing of user-provided column headers in workbooks
(Excel/CSV files) and maps them to Galaxy's internal column target types.

Key Concept - Flexible Header Parsing:
    Users can write column headers in many ways:
    - "Name", "name", "NAME"           -> all map to "name"
    - "URI", "URL", "uri"              -> all map to "url"
    - "MD5 Sum", "MD5", "Hash MD5"     -> all map to "hash_md5"
    - "Genome", "DBKey", "build"       -> all map to "dbkey"

The parsing logic:
    1. Normalizes the header (removes whitespace, special chars, case-insensitive)
    2. Checks exact match against known prefixes
    3. Checks prefix/suffix match if no exact match
    4. Returns the target type key or None if not recognized

Example Flow:
    User workbook header: "MD5 Sum (Optional)"
    ↓ Normalize: "md5sum" (removed spaces, parens, "optional", lowercased)
    ↓ Match: Found in COLUMN_TITLE_PREFIXES["md5sum"] = "hash_md5"
    ↓ Result: HeaderColumn(type="hash_md5", title="MD5 Sum (Optional)", type_index=0)
"""

import re
from dataclasses import dataclass
from typing import (
    Optional,
)

from pydantic import BaseModel

from galaxy.model.dataset_collections.rule_target_models import (
    ColumnTarget,
    RuleBuilderMappingTargetKey,
    target_model_by_type,
)

# Mapping of normalized column header text to target type keys
# All keys are lowercase with no spaces/special chars
# Used for flexible parsing: "MD5 Sum" -> normalize to "md5sum" -> maps to "hash_md5"
COLUMN_TITLE_PREFIXES: dict[str, RuleBuilderMappingTargetKey] = {
    # Dataset naming
    "name": "name",
    "listname": "collection_name",
    "collectionname": "collection_name",
    # URI/URL columns - where to get the data
    "uri": "url",
    "url": "url",
    "urldeferred": "url_deferred",
    "deferredurl": "url_deferred",
    # Genome/reference information
    "genome": "dbkey",
    "dbkey": "dbkey",
    "genomebuild": "dbkey",
    "build": "dbkey",
    # File type/extension
    "filetype": "file_type",
    "extension": "file_type",
    "fileextension": "file_type",
    "type": "file_type",
    # Metadata fields
    "info": "info",
    # Tagging
    "tag": "tags",
    "grouptag": "group_tags",
    "nametag": "name_tag",
    # Collection structure
    "listidentifier": "list_identifiers",
    "pairedidentifier": "paired_identifier",
    # MD5 hashes - all variations
    "hashmd5sum": "hash_md5",
    "hashmd5": "hash_md5",
    "md5sum": "hash_md5",
    "md5": "hash_md5",
    # SHA-1 hashes - all variations
    "sha1hash": "hash_sha1",
    "hashsha1sum": "hash_sha1",
    "hashsha1": "hash_sha1",
    "sha1sum": "hash_sha1",
    "sha1": "hash_sha1",
    # SHA-256 hashes - all variations
    "sha256hash": "hash_sha256",
    "hashsha256sum": "hash_sha256",
    "hashsha256": "hash_sha256",
    "sha256sum": "hash_sha256",
    "sha256": "hash_sha256",
    # SHA-512 hashes - all variations
    "sha512hash": "hash_sha512",
    "hashsha512sum": "hash_sha512",
    "hashsha512": "hash_sha512",
    "sha512sum": "hash_sha512",
    "sha512": "hash_sha512",
}


def column_title_to_target_type(column_title: str) -> Optional[RuleBuilderMappingTargetKey]:
    """Parse a column header string and map it to a target type.

    This function implements Galaxy's flexible column header parsing logic:
    1. Normalize the header (lowercase, remove spaces/parens/dashes/underscores/"optional")
    2. Try exact match against known headers
    3. Try prefix/suffix matching if no exact match
    4. Return the target type or None if not recognized

    Args:
        column_title: The raw column header from the workbook (e.g., "MD5 Sum (Optional)")

    Returns:
        The target type key (e.g., "hash_md5") or None if not recognized

    Examples:
        >>> column_title_to_target_type("Name")
        "name"
        >>> column_title_to_target_type("MD5 Sum")
        "hash_md5"
        >>> column_title_to_target_type("URI 1 (Forward)")
        "url"
        >>> column_title_to_target_type("Genome Build")
        "dbkey"
        >>> column_title_to_target_type("Unknown Column")
        None
    """
    # Normalize: lowercase, remove whitespace/parens/dashes/underscores and "optional"
    normalized_title = re.sub(r"[\s\(\)\-\_]|optional", "", column_title.lower())

    # First, try exact match
    if normalized_title not in COLUMN_TITLE_PREFIXES:
        # If no exact match, try prefix/suffix matching
        # This allows "URI 1 Forward" to match "uri" prefix
        for key in COLUMN_TITLE_PREFIXES.keys():
            if normalized_title.startswith(key):
                normalized_title = key
                break
            elif normalized_title.endswith(key):
                normalized_title = key
                break

    # If still not found, return None
    if normalized_title not in COLUMN_TITLE_PREFIXES:
        return None

    column_type: RuleBuilderMappingTargetKey = COLUMN_TITLE_PREFIXES[normalized_title]
    return column_type


@dataclass
class HeaderColumn:
    """Represents a parsed column header with its metadata.

    When processing a workbook, each column header is parsed into a HeaderColumn
    that tracks both the original user-facing title and the normalized target type.

    The type_index allows for multiple columns of the same type:
    - First URI column: HeaderColumn(type="url", title="URI 1", type_index=0)
    - Second URI column: HeaderColumn(type="url", title="URI 2", type_index=1)

    Attributes:
        type: The normalized target type key (e.g., "url", "name", "hash_md5")
        title: The original user-facing column header (e.g., "MD5 Sum (Optional)")
        type_index: Index when multiple columns of same type exist (0 for first, 1 for second, etc.)

    Examples:
        # Single name column
        HeaderColumn(type="name", title="Name", type_index=0)
        # -> name property returns: "name"

        # First and second URI columns for paired data
        HeaderColumn(type="url", title="URI 1 (Forward)", type_index=0)
        # -> name property returns: "url"
        HeaderColumn(type="url", title="URI 2 (Reverse)", type_index=1)
        # -> name property returns: "url_1"
    """

    type: RuleBuilderMappingTargetKey
    title: str  # user facing
    type_index: int  # 0 for first occurrence, 1 for second, etc.

    @property
    def width(self):
        """Column width for Excel display - URIs need more space."""
        if self.type in ["url", "url_deferred", "ftp_path"]:
            return 50
        else:
            return 20

    @property
    def name(self):
        """Internal column name used as dictionary key.

        Returns the type for first occurrence (index 0), otherwise type_index is appended.
        Examples: "url", "url_1", "list_identifiers", "list_identifiers_1"
        """
        if self.type_index == 0:
            return self.type
        else:
            return f"{self.type}_{self.type_index}"

    @property
    def help(self) -> str:
        """Get the help text for this column type from rule_targets.yml."""
        column_target = _column_header_to_column_target(self)
        return column_target.help if column_target.help else ""

    @property
    def parsed_column(self) -> "ParsedColumn":
        """Return a ParsedColumn representation of this header for serialization."""
        return ParsedColumn(
            type=self.type,
            type_index=self.type_index,
            title=self.title,
        )


def _column_header_to_column_target(column_header: HeaderColumn) -> ColumnTarget:
    """Lookup the ColumnTarget definition for a HeaderColumn."""
    return target_model_by_type(column_header.type)


class ParsedColumn(BaseModel):
    """Serializable representation of a parsed column (Pydantic model version of HeaderColumn).

    Used in API responses and logging to communicate which columns were recognized.
    """

    type: RuleBuilderMappingTargetKey
    type_index: int
    title: str

    @property
    def name(self):
        """Internal column name - matches HeaderColumn.name logic."""
        if self.type_index == 0:
            return self.type
        else:
            return f"{self.type}_{self.type_index}"


class InferredColumnMapping(BaseModel):
    """Records that a column at a specific index was successfully parsed and mapped.

    Used in parse logs to show users which columns were recognized and how they were interpreted.

    Example log entry:
        InferredColumnMapping(
            column_index=2,
            column_title="MD5 Sum",
            parsed_column=ParsedColumn(type="hash_md5", type_index=0, title="MD5 Sum")
        )
    """

    column_index: int
    column_title: str
    parsed_column: ParsedColumn


def column_titles_to_headers(
    column_titles: list[str], column_offset: int = 0
) -> tuple[list[HeaderColumn], list[InferredColumnMapping]]:
    """Parse all column headers from a workbook and convert to HeaderColumn objects.

    This is the main entry point for processing workbook column headers. It:
    1. Iterates through all column titles
    2. Attempts to parse each one using column_title_to_target_type()
    3. Tracks type_index for duplicate column types (e.g., url, url_1)
    4. Handles special case: "optional" paired identifiers -> paired_or_unpaired
    5. Returns both the headers and a log of inferred mappings

    Args:
        column_titles: List of column header strings from the workbook
        column_offset: Offset to add to column indices (default 0)

    Returns:
        Tuple of:
        - headers: List of HeaderColumn objects for recognized columns
        - inferred_columns: List of InferredColumnMapping log entries

    Example:
        Input: ["URI", "Name", "MD5", "URI 2 (Optional)"]
        Output:
        - headers: [
            HeaderColumn(type="url", title="URI", type_index=0),
            HeaderColumn(type="name", title="Name", type_index=0),
            HeaderColumn(type="hash_md5", title="MD5", type_index=0),
            HeaderColumn(type="url", title="URI 2 (Optional)", type_index=1)
          ]
        - inferred_columns: [list of InferredColumnMapping for each]

    Note:
        Unrecognized columns are silently skipped (not included in results).
    """
    headers: list[HeaderColumn] = []
    headers_of_type_seen: dict[RuleBuilderMappingTargetKey, int] = {}
    inferred_columns: list[InferredColumnMapping] = []

    for column_index, column_title in enumerate(column_titles):
        # Try to parse this column header
        column_type_: Optional[RuleBuilderMappingTargetKey] = column_title_to_target_type(column_title)
        if not column_type_:
            # Column not recognized - skip it (could add to parse log here)
            continue
        column_type: RuleBuilderMappingTargetKey = column_type_

        # Track how many times we've seen this type to assign type_index
        if column_type in headers_of_type_seen:
            type_index = headers_of_type_seen[column_type]
            headers_of_type_seen[column_type] += 1
        else:
            type_index = 0
            headers_of_type_seen[column_type] = 1

        # Create the header column
        header_column = HeaderColumn(
            type=column_type,
            type_index=type_index,
            title=column_title,
        )

        # Special case: paired identifier with "optional" in title becomes paired_or_unpaired
        if header_column.type == "paired_identifier" and implied_paired_or_unpaired_column_header(header_column):
            header_column.type = "paired_or_unpaired_identifier"

        headers.append(header_column)
        inferred_columns.append(
            InferredColumnMapping(
                column_index=column_index + column_offset,
                column_title=column_title,
                parsed_column=header_column.parsed_column,
            )
        )
    return headers, inferred_columns


def implied_paired_or_unpaired_column_header(column_header: HeaderColumn) -> bool:
    """Check if a column header implies optional pairing (paired_or_unpaired).

    If "optional" appears in the title, it signals that this column can have empty values,
    allowing for mixed paired and unpaired datasets in the same collection.

    Examples that return True:
    - "URI 2 - Reverse (Optional)"
    - "Optional URI 2"
    - "Optional Paired Identifier"

    This is used to upgrade "paired_identifier" -> "paired_or_unpaired_identifier"
    """
    return "optional" in column_header.title.lower()
