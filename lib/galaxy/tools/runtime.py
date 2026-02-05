from typing import (
    Any,
    Callable,
    Dict,
    Optional,
    TYPE_CHECKING,
)

from galaxy.model import (
    DatasetCollection,
    DatasetCollectionElement,
    HistoryDatasetAssociation,
    HistoryDatasetCollectionAssociation,
    InpDataDictT,
)
from galaxy.tool_util.cwl.util import set_basename_and_derived_properties
from galaxy.tool_util_models.parameters import (
    DataCollectionRequestInternal,
    DataInternalJson,
    DataRequestInternalDereferencedT,
    DataRequestInternalHda,
)

if TYPE_CHECKING:
    from galaxy.job_execution.compute_environment import ComputeEnvironment
    from galaxy.structured_app import MinimalToolApp


# Type aliases for callbacks
DatasetToRuntimeJson = Callable[[DataRequestInternalDereferencedT], DataInternalJson]
CollectionToRuntimeJson = Callable[[DataCollectionRequestInternal, Optional[str]], Dict[str, Any]]

# Input dataset collections dict type
InpDataCollectionsDictT = Dict[str, Any]


def is_list_like(collection_type: str) -> bool:
    """Returns True if this collection type has array elements.

    List-like types: list, sample_sheet
    Record-like types: paired, paired_or_unpaired, record
    """
    first_segment = collection_type.split(":")[0]
    return first_segment in ("list", "sample_sheet")


def setup_for_runtimeify(
    app: "MinimalToolApp",
    compute_environment: Optional["ComputeEnvironment"],
    input_datasets: InpDataDictT,
    input_dataset_collections: Optional[InpDataCollectionsDictT] = None,
):
    """Set up callbacks for runtimeify to convert tool state to runtime representations.

    Returns:
        Tuple of (hda_references, adapt_dataset, adapt_collection)
    """
    hda_references: list[HistoryDatasetAssociation] = []

    # Build lookup for individual datasets
    hdas_by_id = {d.id: (d, i) for (i, d) in enumerate(input_datasets.values()) if d is not None}

    # Build separate lookups for HDCAs and DCEs
    hdcas_by_id: Dict[int, HistoryDatasetCollectionAssociation] = {}
    dces_by_id: Dict[int, DatasetCollectionElement] = {}

    if input_dataset_collections:
        for name, value in input_dataset_collections.items():
            if isinstance(value, HistoryDatasetCollectionAssociation):
                hdcas_by_id[value.id] = value
            elif isinstance(value, DatasetCollectionElement):
                dces_by_id[value.id] = value

    def adapt_dataset(value: DataRequestInternalDereferencedT) -> DataInternalJson:
        hda_id = value.id
        if hda_id not in hdas_by_id:
            raise ValueError(f"Could not find HDA for dataset id {hda_id}")
        hda, index = hdas_by_id[hda_id]
        if not hda:
            raise ValueError(f"Could not find HDA for dataset id {hda_id}")
        size = hda.dataset.get_size() if hda and hda.dataset else 0
        properties = {
            "class": "File",
            "location": f"step_input://{index}",
            "format": hda.extension,
            "path": compute_environment.input_path_rewrite(hda) if compute_environment else hda.get_file_name(),
            "size": int(size),
            "listing": [],
        }
        set_basename_and_derived_properties(properties, hda.dataset.created_from_basename or hda.name)
        return DataInternalJson(**properties)

    def adapt_collection(
        value: DataCollectionRequestInternal,
        collection_type: Optional[str],
    ) -> Dict[str, Any]:
        """Convert a collection request to runtime representation.

        Args:
            value: Collection request with src ("hdca" or "dce") and id
            collection_type: Expected collection type from parameter definition

        Returns:
            Runtime representation dict with class, name, collection_type, tags, elements
        """
        # Handle DCE reference (subcollection mapping scenario)
        if value.src == "dce":
            dce = dces_by_id.get(value.id)
            if not dce:
                raise ValueError(f"DCE {value.id} not found")
            return _adapt_from_dce(dce, adapt_dataset, compute_environment)

        # Handle HDCA reference (direct collection input)
        hdca = hdcas_by_id.get(value.id)
        if hdca:
            return _adapt_from_hdca(hdca, adapt_dataset, compute_environment)

        raise ValueError(f"Collection {value.id} not found (src={value.src})")

    return hda_references, adapt_dataset, adapt_collection


def _adapt_from_hdca(
    hdca: HistoryDatasetCollectionAssociation,
    adapt_dataset: DatasetToRuntimeJson,
    compute_environment: Optional["ComputeEnvironment"],
) -> Dict[str, Any]:
    """Adapt an HDCA (direct collection input scenario)."""
    return collection_to_runtime(
        hdca.collection,
        name=hdca.name,
        tags=[str(t) for t in hdca.tags],
        adapt_dataset=adapt_dataset,
        compute_environment=compute_environment,
    )


def _adapt_from_dce(
    dce: DatasetCollectionElement,
    adapt_dataset: DatasetToRuntimeJson,
    compute_environment: Optional["ComputeEnvironment"],
) -> Dict[str, Any]:
    """Adapt a DatasetCollectionElement (subcollection mapping scenario).

    Note: Only auto-propagated tags are available in this scenario.
    Full HDCA tags are on the parent collection, not passed to individual jobs.
    """
    return collection_to_runtime(
        dce.child_collection,
        name=dce.element_identifier,
        tags=[str(t) for t in dce.auto_propagated_tags],
        adapt_dataset=adapt_dataset,
        compute_environment=compute_environment,
        columns=dce.columns,  # pass columns for sample_sheet:* types
    )


def collection_to_runtime(
    collection: DatasetCollection,
    name: Optional[str],
    tags: list[str],
    adapt_dataset: DatasetToRuntimeJson,
    compute_environment: Optional["ComputeEnvironment"],
    columns: Optional[list] = None,  # from parent DCE for sample_sheet elements
) -> Dict[str, Any]:
    """Convert DatasetCollection to runtime representation.

    Args:
        collection: The DatasetCollection to convert
        name: Name for the collection (from HDCA or element_identifier)
        tags: Tags list (from HDCA or auto_propagated_tags)
        adapt_dataset: Callback to convert individual datasets
        compute_environment: Compute environment for path rewriting
        columns: Optional columns from parent DCE (for sample_sheet)

    Returns:
        Runtime representation dict with class, name, collection_type, tags, elements
    """
    elements_list_like = is_list_like(collection.collection_type)

    if elements_list_like:
        # List-like: elements is array
        elements: Any = []
        for dce in sorted(collection.elements, key=lambda e: e.element_index):
            elements.append(_element_to_runtime(dce, adapt_dataset, compute_environment))
    else:
        # Record-like: elements is object
        elements = {}
        for dce in collection.elements:
            elements[dce.element_identifier] = _element_to_runtime(dce, adapt_dataset, compute_environment)

    result: Dict[str, Any] = {
        "class": "Collection",
        "name": name,
        "collection_type": collection.collection_type,
        "tags": tags,
        "elements": elements,
    }

    # Add special metadata where present
    if hasattr(collection, "column_definitions") and collection.column_definitions:
        result["column_definitions"] = collection.column_definitions
    if hasattr(collection, "fields") and collection.fields:
        result["fields"] = collection.fields
    if columns is not None:
        result["columns"] = columns
    if collection.collection_type == "paired_or_unpaired":
        result["has_single_item"] = len(collection.elements) == 1

    return result


def _element_to_runtime(
    element: DatasetCollectionElement,
    adapt_dataset: DatasetToRuntimeJson,
    compute_environment: Optional["ComputeEnvironment"],
) -> Dict[str, Any]:
    """Convert a single collection element to runtime representation."""
    if element.is_collection:
        return collection_to_runtime(
            element.child_collection,
            name=element.element_identifier,
            tags=list(element.auto_propagated_tags) if element.auto_propagated_tags else [],
            adapt_dataset=adapt_dataset,
            compute_environment=compute_environment,
            columns=element.columns,  # pass columns for sample_sheet:* types
        )
    else:
        hda = element.element_object
        request = DataRequestInternalHda(src="hda", id=hda.id)
        result = adapt_dataset(request).model_dump()
        # Rename class_ back to class for JSON output
        if "class_" in result:
            result["class"] = result.pop("class_")
        result["element_identifier"] = element.element_identifier
        # Add columns for sample_sheet leaf elements
        if element.columns:
            result["columns"] = element.columns
        return result
