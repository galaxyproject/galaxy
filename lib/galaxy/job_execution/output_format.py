"""Shared input datatype resolution for declared and discovered outputs."""

import json
import logging
import re
from collections.abc import Mapping
from typing import (
    Optional,
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from galaxy.model import (
        DatasetInstance,
        HistoryDatasetCollectionAssociation,
    )
    from galaxy.tools.execution_helpers import ToolExecutionCache

log = logging.getLogger(__name__)


def get_ext_or_implicit_ext(hda: "DatasetInstance") -> Optional[str]:
    if hda.implicitly_converted_parent_datasets:
        # Conversion associations record the datatype actually supplied to the tool.
        return hda.implicitly_converted_parent_datasets[0].type
    return hda.ext


def resolve_format_source(
    format_source: str,
    input_datasets: Mapping[str, Optional["DatasetInstance"]],
    input_dataset_collections: Mapping[str, "HistoryDatasetCollectionAssociation"],
    default_format: Optional[str],
    execution_cache: Optional["ToolExecutionCache"] = None,
) -> Optional[str]:
    """Resolve an input datatype, retaining the default when the source is unavailable."""
    ext = default_format
    if format_source in input_datasets:
        try:
            input_dataset = input_datasets[format_source]
            if input_dataset is not None:
                ext = get_ext_or_implicit_ext(input_dataset)
        except Exception:
            pass
    else:
        element_index = None
        collection_name = format_source
        if re.match(r"^[^\[\]]*\[[^\[\]]*\]$", format_source):
            collection_name, element_index = format_source[0:-1].split("[")
            # Treat as json to interpret "forward" vs 0 with type
            # Make it feel more like Python, single quote better in XML also.
            element_index = element_index.replace("'", '"')
            element_index = json.loads(element_index)

        if collection_name in input_dataset_collections:
            try:
                input_collection = input_dataset_collections[collection_name]
                input_collection_collection = input_collection.collection
                if element_index is None:
                    # just pick the first HDA
                    input_dataset = input_collection_collection.dataset_instances[0]
                else:
                    try:
                        input_element = input_collection_collection[element_index]
                    except KeyError:
                        if execution_cache:
                            dataset_elements = execution_cache.cached_collection_elements.get(
                                input_collection_collection.id
                            )
                            if dataset_elements is None:
                                dataset_elements = execution_cache.cached_collection_elements[
                                    input_collection_collection.id
                                ] = input_collection_collection.dataset_elements
                        else:
                            dataset_elements = input_collection_collection.dataset_elements
                        for element in dataset_elements:
                            if element.element_identifier == element_index:
                                input_element = element
                                break
                    input_dataset = input_element.element_object
                ext = get_ext_or_implicit_ext(input_dataset)
            except Exception as e:
                log.debug("Exception while trying to determine format_source: %s", e)
    return ext
