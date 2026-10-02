"""Models describing the column targets a rule builder workbook can carry.

The target definitions themselves live in ``rule_targets.yml``; header parsing
onto these types lives in ``rule_target_columns.py``.
"""

from typing import (
    Literal,
)

import yaml
from pydantic import (
    BaseModel,
    RootModel,
)

from galaxy.util.resources import resource_string

RuleBuilderImportType = Literal["datasets", "collections"]
RuleBuilderModes = Literal[
    "raw",  # URIs supplied directly in the workbook
    "ftp",  # files staged in the user's FTP directory
    "datasets",
    "library_datasets",  # datasets from data libraries
    "collection_contents",  # elements of an existing collection
]


class ColumnTarget(BaseModel):
    """One column type a workbook may declare, as defined in ``rule_targets.yml``."""

    label: str
    help: str | None
    modes: list[RuleBuilderModes] | None = None
    importType: RuleBuilderImportType | None = None
    multiple: bool | None = False
    columnHeader: str | None = None
    advanced: bool | None = False
    requiresFtp: bool | None = False
    example_column_names: list[str] | None = None

    @property
    def example_column_names_as_str(self) -> str | None:
        if self.example_column_names:
            return '"' + '", "'.join(self.example_column_names) + '"'
        return ""


RuleBuilderMappingTargetKey = Literal[
    "list_identifiers",
    "paired_identifier",
    "paired_or_unpaired_identifier",  # as above, but the column may be blank
    "collection_name",
    "name_tag",  # name: tags, propagated to derived datasets
    "tags",
    "group_tags",  # group: tags, consumed by factorial tools
    "name",
    "dbkey",
    "hash_sha1",
    "hash_md5",
    "hash_sha256",
    "hash_sha512",
    "file_type",
    "url",
    "url_deferred",  # record the URI, fetch only when something needs it
    "info",  # unstructured text shown in the expanded history item
    "ftp_path",  # path relative to the user's FTP directory
    "deferred",  # boolean form of url_deferred
    "to_posix_lines",  # boolean, convert line endings on fetch
    "space_to_tab",  # boolean, convert spaces to tabs on fetch
    "auto_decompress",  # boolean, decompress on fetch
]


ColumnTargetsConfig = dict[RuleBuilderMappingTargetKey, ColumnTarget]
ColumnTargetsConfigRootModel = RootModel[ColumnTargetsConfig]


def target_models() -> ColumnTargetsConfig:
    column_targets_str = resource_string(__name__, "rule_targets.yml")
    column_targets_raw = yaml.safe_load(column_targets_str)
    return ColumnTargetsConfigRootModel.model_validate(column_targets_raw).root


def target_model_by_type(type: RuleBuilderMappingTargetKey) -> ColumnTarget:
    return target_models()[type]


# Any URI-based workbook should allow specifying these metadata column types.
COMMON_COLUMN_TARGETS = [
    target_model_by_type("name"),
    target_model_by_type("dbkey"),
    target_model_by_type("info"),
    target_model_by_type("file_type"),
    target_model_by_type("tags"),
    target_model_by_type("group_tags"),
    target_model_by_type("name_tag"),
    target_model_by_type("hash_md5"),
    target_model_by_type("hash_sha1"),
    target_model_by_type("hash_sha256"),
    target_model_by_type("hash_sha512"),
]
