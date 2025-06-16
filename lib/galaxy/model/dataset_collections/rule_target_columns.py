import re
from dataclasses import dataclass
from typing import (
    Dict,
    List,
    Optional,
    Tuple,
)

from pydantic import BaseModel

from galaxy.model.dataset_collections.rule_target_models import (
    ColumnTarget,
    RuleBuilderMappingTargetKey,
    target_model_by_type,
)

COLUMN_TITLE_PREFIXES: Dict[str, RuleBuilderMappingTargetKey] = {
    "name": "name",
    "listname": "collection_name",
    "collectionname": "collection_name",
    "uri": "url",
    "url": "url",
    "urldeferred": "url_deferred",
    "deferredurl": "url_deferred",
    "genome": "dbkey",
    "dbkey": "dbkey",
    "genomebuild": "dbkey",
    "filetype": "file_type",
    "extension": "file_type",
    "fileextension": "file_type",
    "info": "info",
    "tag": "tags",
    "grouptag": "group_tags",
    "nametag": "name_tag",
    "listidentifier": "list_identifiers",
    "pairedidentifier": "paired_identifier",
    "hashmd5sum": "hash_md5",
    "hashmd5": "hash_md5",
    "md5sum": "hash_md5",
    "md5": "hash_md5",
    "sha1hash": "hash_sha1",
    "hashsha1sum": "hash_sha1",
    "hashsha1": "hash_sha1",
    "sha1sum": "hash_sha1",
    "sha1": "hash_sha1",
    "sha256hash": "hash_sha256",
    "hashsha256sum": "hash_sha256",
    "hashsha256": "hash_sha256",
    "sha256sum": "hash_sha256",
    "sha256": "hash_sha256",
    "sha512hash": "hash_sha512",
    "hashsha512sum": "hash_sha512",
    "hashsha512": "hash_sha512",
    "sha512sum": "hash_sha512",
    "sha512": "hash_sha512",
}


def column_title_to_target_type(column_title: str) -> Optional[RuleBuilderMappingTargetKey]:
    normalized_title = re.sub(r"[\s\(\)\-\_]|optional", "", column_title.lower())
    if normalized_title not in COLUMN_TITLE_PREFIXES:
        for key in COLUMN_TITLE_PREFIXES.keys():
            if normalized_title.startswith(key):
                normalized_title = key
                break
            elif normalized_title.endswith(key):
                normalized_title = key
                break

    if normalized_title not in COLUMN_TITLE_PREFIXES:
        return None

    column_type: RuleBuilderMappingTargetKey = COLUMN_TITLE_PREFIXES[normalized_title]
    return column_type


@dataclass
class HeaderColumn:
    type: RuleBuilderMappingTargetKey
    title: str  # user facing
    # e.g. for paired data will have two columns of URIs, record types maybe have any number
    # and after dataset hash may have multiples of those also
    type_index: int

    @property
    def width(self):
        if self.type in ["url", "url_deferred", "ftp_path"]:
            return 50
        else:
            return 20

    @property
    def name(self):
        if self.type_index == 0:
            return self.type
        else:
            return f"{self.type}_{self.type_index}"

    @property
    def help(self) -> str:
        column_target = _column_header_to_column_target(self)
        return column_target.help if column_target.help else ""

    @property
    def parsed_column(self) -> "ParsedColumn":
        """Return a ParsedColumn representation of this header."""
        return ParsedColumn(
            type=self.type,
            type_index=self.type_index,
            title=self.title,
        )


def _column_header_to_column_target(column_header: HeaderColumn) -> ColumnTarget:
    return target_model_by_type(column_header.type)


class ParsedColumn(BaseModel):
    type: RuleBuilderMappingTargetKey
    type_index: int
    title: str

    @property
    def name(self):
        if self.type_index == 0:
            return self.type
        else:
            return f"{self.type}_{self.type_index}"


class InferredColumnMapping(BaseModel):
    column_index: int
    column_title: str
    parsed_column: ParsedColumn


def column_titles_to_headers(
    column_titles: List[str], column_offset: int = 0
) -> Tuple[List[HeaderColumn], List[InferredColumnMapping]]:
    headers: List[HeaderColumn] = []
    headers_of_type_seen: Dict[RuleBuilderMappingTargetKey, int] = {}
    inferred_columns: List[InferredColumnMapping] = []

    for column_index, column_title in enumerate(column_titles):
        column_type_: Optional[RuleBuilderMappingTargetKey] = column_title_to_target_type(column_title)
        if not column_type_:
            # make a note in parse log that this column was skipped
            continue
        column_type: RuleBuilderMappingTargetKey = column_type_
        if column_type in headers_of_type_seen:
            type_index = headers_of_type_seen[column_type]
            headers_of_type_seen[column_type] += 1
        else:
            type_index = 0
            headers_of_type_seen[column_type] = 1
        header_column = HeaderColumn(
            type=column_type,
            type_index=type_index,
            title=column_title,
        )
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
    # URI 2 - Reverse (Optional), Optional URI 2, Optional Paired Identifier all
    # imply paired_or_unpaired lists using this logic.
    return "optional" in column_header.title.lower()
