"""This module define an abstract class for reasoning about Galaxy's
dataset collection after jobs are finished.
"""

import abc
from typing import (
    List,
    Optional,
)

from galaxy.tool_util_models.tool_outputs import (
    DatasetCollectionDescriptionT,
    DiscoverViaT,
    FilePatternDatasetCollectionDescription as FilePatternDatasetCollectionDescriptionModel,
    SortCompT,
    SortKeyT,
    ToolProvidedMetadataDatasetCollection as ToolProvidedMetadataDatasetCollectionModel,
)
from galaxy.util import asbool
from .util import is_dict

DEFAULT_EXTRA_FILENAME_PATTERN = (
    r"primary_DATASET_ID_(?P<designation>[^_]+)_(?P<visible>[^_]+)_(?P<ext>[^_]+)(_(?P<dbkey>[^_]+))?"
)
DEFAULT_SORT_BY = "filename"
DEFAULT_SORT_COMP = "lexical"


# XML can describe custom patterns, but these literals describe named
# patterns that will be replaced.
NAMED_PATTERNS = {
    "__default__": DEFAULT_EXTRA_FILENAME_PATTERN,
    "__name__": r"(?P<name>.*)",
    "__designation__": r"(?P<designation>.*)",
    "__name_and_ext__": r"(?P<name>.*)\.(?P<ext>[^\.]+)?",
    "__designation_and_ext__": r"(?P<designation>.*)\.(?P<ext>[^\._]+)?",
}

INPUT_DBKEY_TOKEN = "__input__"
LEGACY_DEFAULT_DBKEY = None  # don't use __input__ for legacy default collection


def dataset_collector_descriptions_from_elem(elem, legacy=True):
    primary_dataset_elems = elem.findall("discover_datasets")
    num_discover_dataset_blocks = len(primary_dataset_elems)
    if num_discover_dataset_blocks == 0 and legacy:
        collectors = [DEFAULT_DATASET_COLLECTOR_DESCRIPTION]
    else:
        default_format = elem.attrib.get("format")
        collectors = []
        for e in primary_dataset_elems:
            description_attributes = e.attrib
            if default_format and "format" not in description_attributes and "ext" not in description_attributes:
                description_attributes["format"] = default_format
            collectors.append(dataset_collection_description(**description_attributes))

    return _validate_collectors(collectors)


def dataset_collector_descriptions_from_output_dict(as_dict):
    discover_datasets_dicts = as_dict.get("discover_datasets", [])
    if is_dict(discover_datasets_dicts):
        discover_datasets_dicts = [discover_datasets_dicts]
    dataset_collector_descriptions = dataset_collector_descriptions_from_list(discover_datasets_dicts)
    return _validate_collectors(dataset_collector_descriptions)


def _validate_collectors(collectors):
    num_discover_dataset_blocks = len(collectors)
    if num_discover_dataset_blocks > 1:
        for collector in collectors:
            if collector.discover_via == "tool_provided_metadata":
                raise Exception(
                    "Cannot specify more than one discover dataset condition if any of them specify tool_provided_metadata."
                )

    return collectors


def dataset_collector_descriptions_from_list(discover_datasets_dicts):
    return [dataset_collection_description(**kwds) for kwds in discover_datasets_dicts]


def dataset_collection_description(**kwargs):
    from_provided_metadata = asbool(kwargs.get("from_provided_metadata", False))
    discover_via = kwargs.get("discover_via", "tool_provided_metadata" if from_provided_metadata else "pattern")
    if discover_via == "tool_provided_metadata":
        for key in ["pattern", "sort_by"]:
            if kwargs.get(key):
                raise Exception(f"Cannot specify attribute [{key}] if from_provided_metadata is True")
        return ToolProvidedMetadataDatasetCollection(**kwargs)
    else:
        return FilePatternDatasetCollectionDescription(**kwargs)


class DatasetCollectionDescription(metaclass=abc.ABCMeta):
    discover_via: DiscoverViaT
    default_ext: Optional[str]
    default_visible: bool
    assign_primary_output: bool
    directory: Optional[str]
    recurse: bool
    match_relative_path: bool

    def __init__(self, **kwargs):
        self.default_dbkey = kwargs.get("dbkey", INPUT_DBKEY_TOKEN)
        self.default_ext = kwargs.get("ext", None)
        if self.default_ext is None and "format" in kwargs:
            self.default_ext = kwargs.get("format")
        self.default_visible = asbool(kwargs.get("visible", None))
        self.assign_primary_output = asbool(kwargs.get("assign_primary_output", False))
        self.directory = kwargs.get("directory", None)
        self.recurse = False
        self.match_relative_path = asbool(kwargs.get("match_relative_path", False))

    def _common_model_props(self):
        return {
            "discover_via": self.discover_via,
            "dbkey": self.default_dbkey,
            "format": self.default_ext,
            "visible": self.default_visible,
            "assign_primary_output": self.assign_primary_output,
            "directory": self.directory,
            "recurse": self.recurse,
            "match_relative_path": self.match_relative_path,
        }

    @abc.abstractmethod
    def to_model(self) -> DatasetCollectionDescriptionT: ...

    def to_dict(self) -> dict:
        return self.to_model().model_dump()

    @property
    def discover_patterns(self) -> List[str]:
        return []


class ToolProvidedMetadataDatasetCollection(DatasetCollectionDescription):
    discover_via = "tool_provided_metadata"

    def to_model(self) -> ToolProvidedMetadataDatasetCollectionModel:
        return ToolProvidedMetadataDatasetCollectionModel(
            discover_via=self.discover_via,
            dbkey=self.default_dbkey,
            format=self.default_ext,
            visible=self.default_visible,
            assign_primary_output=self.assign_primary_output,
            directory=self.directory,
            recurse=self.recurse,
            match_relative_path=self.match_relative_path,
        )

    def to_dict(self) -> dict:
        return self.to_model().model_dump()


class FilePatternDatasetCollectionDescription(DatasetCollectionDescription):
    discover_via = "pattern"
    sort_key: SortKeyT
    sort_comp: SortCompT
    pattern: str

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        pattern = kwargs.get("pattern", "__default__")
        self.recurse = asbool(kwargs.get("recurse", False))
        self.match_relative_path = asbool(kwargs.get("match_relative_path", False))
        if pattern in NAMED_PATTERNS:
            pattern = NAMED_PATTERNS[pattern]
        self.pattern = pattern
        self.sort_by = sort_by = kwargs.get("sort_by", DEFAULT_SORT_BY)
        if sort_by.startswith("reverse_"):
            self.sort_reverse = True
            sort_by = sort_by[len("reverse_") :]
        else:
            self.sort_reverse = False
        if "_" in sort_by:
            sort_comp, sort_by = sort_by.split("_", 1)
            assert sort_comp in ["lexical", "numeric"]
        else:
            sort_comp = DEFAULT_SORT_COMP
        assert sort_by in ["filename", "name", "designation", "dbkey"]
        self.sort_key = sort_by
        self.sort_comp = sort_comp

    def to_model(self) -> FilePatternDatasetCollectionDescriptionModel:
        return FilePatternDatasetCollectionDescriptionModel(
            discover_via=self.discover_via,
            dbkey=self.default_dbkey,
            format=self.default_ext,
            visible=self.default_visible,
            assign_primary_output=self.assign_primary_output,
            directory=self.directory,
            recurse=self.recurse,
            match_relative_path=self.match_relative_path,
            sort_key=self.sort_key,
            sort_comp=self.sort_comp,
            pattern=self.pattern,
            sort_by=self.sort_by,
        )

    @property
    def discover_patterns(self) -> List[str]:
        return [self.pattern]


DEFAULT_DATASET_COLLECTOR_DESCRIPTION = FilePatternDatasetCollectionDescription(
    default_dbkey=LEGACY_DEFAULT_DBKEY,
)
