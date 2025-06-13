from typing import (
    Dict,
    List,
    Literal,
    Optional,
)

import yaml
from pydantic import (
    BaseModel,
    RootModel,
)

from galaxy.util.resources import resource_string

RuleBuilderImportType = Literal["datasets", "collections"]
RuleBuilderModes = Literal[
    "raw",
    "ftp",
    "datasets",
    "library_datasets",
    "collection_contents",
]


class ColumnTarget(BaseModel):
    label: str
    help: Optional[str]
    modes: Optional[List[RuleBuilderModes]] = None
    importType: Optional[RuleBuilderImportType] = None
    multiple: Optional[bool] = False
    columnHeader: Optional[str] = None
    advanced: Optional[bool] = False
    requiresFtp: Optional[bool] = False
    example_column_names: Optional[List[str]] = None

    @property
    def example_column_names_as_str(self) -> Optional[str]:
        if self.example_column_names:
            return '"' + '", "'.join(self.example_column_names) + '"'
        return ""


RuleBuilderMappingTargetKey = Literal[
    "list_identifiers",
    "paired_identifier",
    "paired_or_unpaired_identifier",
    "collection_name",
    "name_tag",
    "tags",
    "group_tags",
    "name",
    "dbkey",
    "hash_sha1",
    "hash_md5",
    "hash_sha256",
    "hash_sha512",
    "file_type",
    "url",
    "url_deferred",
    "info",
    "ftp_path",
]


ColumnTargetsConfig = Dict[RuleBuilderMappingTargetKey, ColumnTarget]
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
