from decimal import Decimal
from typing import (
    Any,
    cast,
)

import pytest
from pydantic import ValidationError

from galaxy.datatypes.registry import example_datatype_registry_for_sample
from galaxy.model import (
    Dataset,
    DatasetCollection,
    DatasetCollectionElement,
    DatasetSource,
    HistoryDatasetAssociation,
    ImplicitlyConvertedDatasetAssociation,
    set_datatypes_registry,
)
from galaxy.tool_util_models.parameters import (
    build_collection_model_for_type,
    DataCollectionListRuntime,
    DataCollectionPairedOrUnpairedRuntime,
    DataCollectionPairedRuntime,
    DataCollectionRecordRuntime,
    DataCollectionSampleSheetRuntime,
    DataInternalJson,
    DataRequestInternalHda,
)
from galaxy.tools.runtime import (
    _validate_collection_runtime_dict,
    collection_to_runtime,
    setup_for_runtimeify,
)


@pytest.fixture
def mock_adapt_dataset():
    def adapt(request):
        return DataInternalJson(
            **{
                "class": "File",
                "location": f"step_input://{request.id}",
                "format": "txt",
                "path": f"/path/to/{request.id}",
                "size": 100,
                "listing": [],
                "basename": f"file_{request.id}.txt",
                "nameroot": f"file_{request.id}",
                "nameext": "txt",
            }
        )

    return adapt


def create_model_collection(collection_type, elements_data):
    # Create collection using real model
    collection = DatasetCollection(collection_type=collection_type)

    # Manually initialize list for in-memory relationship if needed
    if not hasattr(collection, "elements"):
        collection.elements = []

    for i, (name, content) in enumerate(elements_data):
        if isinstance(content, list):  # Nested collection [type, elements]
            child_collection = create_model_collection(content[0], content[1])
            dce = DatasetCollectionElement(
                collection=collection, element_identifier=name, element_index=i, element=child_collection
            )
        else:  # HDA
            hda = HistoryDatasetAssociation(create_dataset=True, flush=False, name=content)
            hda.id = i + 100  # Fake ID for testing
            # Also satisfy accessing hda.dataset.created_from_basename or hda.name in generic adapt if needed
            assert hda.dataset is not None
            hda.dataset.id = i + 1000

            dce = DatasetCollectionElement(collection=collection, element_identifier=name, element_index=i, element=hda)

        # SA relationship may handle append if active, but let's check.
        # If we double-append, we get duplicates.
        # If we don't append and SA mocks aren't active, we get empty.
        # Safe approach: check if in list
        if dce not in collection.elements:
            collection.elements.append(dce)

    return collection


def test_collection_to_runtime_paired(mock_adapt_dataset):
    # Paired collection
    collection = create_model_collection("paired", [("forward", "hda1"), ("reverse", "hda2")])

    runtime = collection_to_runtime(
        collection, name="test_paired", tags=["t1"], adapt_dataset=mock_adapt_dataset, compute_environment=None
    )

    assert isinstance(runtime, DataCollectionPairedRuntime)
    assert runtime.collection_type == "paired"
    # DataCollectionPairedRuntime.elements is an object with forward/reverse fields
    assert runtime.elements.forward.class_ == "File"
    assert runtime.elements.reverse.class_ == "File"


def test_collection_to_runtime_list(mock_adapt_dataset):
    # List collection
    collection = create_model_collection("list", [("e1", "hda1"), ("e2", "hda2")])

    runtime = collection_to_runtime(
        collection, name="test_list", tags=[], adapt_dataset=mock_adapt_dataset, compute_environment=None
    )

    assert isinstance(runtime, DataCollectionListRuntime)
    assert runtime.collection_type == "list"
    assert len(runtime.elements) == 2
    assert runtime.elements[0].element_identifier == "e1"


def test_collection_to_runtime_nested(mock_adapt_dataset):
    # Nested list:paired
    paired_data = ["paired", [("forward", "hda1"), ("reverse", "hda2")]]
    collection = create_model_collection("list:paired", [("p1", paired_data)])

    runtime = collection_to_runtime(
        collection, name="test_nested", tags=[], adapt_dataset=mock_adapt_dataset, compute_environment=None
    )

    expected_model = build_collection_model_for_type("list:paired")
    assert expected_model is not None
    assert isinstance(runtime, expected_model)
    assert type(runtime).__name__ == "DynamicCollection_list_paired"
    assert runtime.collection_type == "list:paired"
    assert hasattr(runtime, "elements")
    assert len(runtime.elements) == 1

    inner = runtime.elements[0]
    assert isinstance(inner, DataCollectionPairedRuntime)
    assert inner.elements.forward.class_ == "File"


def test_collection_to_runtime_invalid_paired(mock_adapt_dataset):
    # Paired collection missing reverse
    collection = create_model_collection("paired", [("forward", "hda1")])

    # Should raise ValidationError because DataCollectionPairedRuntime requires forward and reverse
    with pytest.raises(ValidationError):
        collection_to_runtime(
            collection, name="bad_paired", tags=[], adapt_dataset=mock_adapt_dataset, compute_environment=None
        )


def test_collection_to_runtime_record(mock_adapt_dataset):
    # Record collection
    collection = create_model_collection("record", [("f1", "hda1"), ("f2", "hda2")])
    collection.fields = [{"name": "f1", "type": "File"}, {"name": "f2", "type": "File"}]

    runtime = collection_to_runtime(
        collection, name="test_record", tags=[], adapt_dataset=mock_adapt_dataset, compute_environment=None
    )

    assert isinstance(runtime, DataCollectionRecordRuntime)
    assert runtime.collection_type == "record"
    assert runtime.elements["f1"].class_ == "File"
    assert runtime.elements["f2"].class_ == "File"


def test_collection_to_runtime_sample_sheet(mock_adapt_dataset):
    # Sample sheet -> List runtime
    collection = create_model_collection("sample_sheet", [("s1", "hda1"), ("s2", "hda2")])
    collection.column_definitions = [{"name": "cond", "type": "str"}]
    # Mock elements should have columns
    for ele in collection.elements:
        ele.columns = ["treatment"]

    runtime = collection_to_runtime(
        collection, name="test_sheet", tags=[], adapt_dataset=mock_adapt_dataset, compute_environment=None
    )

    # Should use DataCollectionSampleSheetRuntime to preserve metadata
    assert isinstance(runtime, DataCollectionSampleSheetRuntime)
    assert runtime.collection_type == "sample_sheet"
    assert runtime.column_definitions is not None
    assert runtime.elements[0].columns == ["treatment"]


def test_collection_to_runtime_paired_or_unpaired(mock_adapt_dataset):
    # Paired mode
    collection = create_model_collection("paired_or_unpaired", [("forward", "hda1"), ("reverse", "hda2")])
    collection.has_single_item = False

    runtime = collection_to_runtime(
        collection, name="test_pou_paired", tags=[], adapt_dataset=mock_adapt_dataset, compute_environment=None
    )

    assert isinstance(runtime, DataCollectionPairedOrUnpairedRuntime)
    assert runtime.elements["forward"].class_ == "File"

    # Unpaired mode
    collection_unpaired = create_model_collection("paired_or_unpaired", [("unpaired", "hda3")])
    collection_unpaired.has_single_item = True

    runtime_unpaired = collection_to_runtime(
        collection_unpaired,
        name="test_pou_unpaired",
        tags=[],
        adapt_dataset=mock_adapt_dataset,
        compute_environment=None,
    )

    assert isinstance(runtime_unpaired, DataCollectionPairedOrUnpairedRuntime)
    assert runtime_unpaired.elements["unpaired"].class_ == "File"


def test_collection_to_runtime_deeply_nested(mock_adapt_dataset):
    """End-to-end: list:list:paired through collection_to_runtime pipeline."""
    paired_data = ["paired", [("forward", "hda1"), ("reverse", "hda2")]]
    list_paired_data = ["list:paired", [("p1", paired_data)]]
    collection = create_model_collection("list:list:paired", [("batch1", list_paired_data)])

    runtime = collection_to_runtime(
        collection,
        name="test_deeply_nested",
        tags=[],
        adapt_dataset=mock_adapt_dataset,
        compute_environment=None,
    )

    expected_model = build_collection_model_for_type("list:list:paired")
    assert expected_model is not None
    assert isinstance(runtime, expected_model)
    assert runtime.collection_type == "list:list:paired"
    assert hasattr(runtime, "elements")
    assert len(runtime.elements) == 1

    middle = runtime.elements[0]
    expected_middle = build_collection_model_for_type("list:paired")
    assert expected_middle is not None
    assert isinstance(middle, expected_middle)
    assert hasattr(middle, "elements")
    assert middle.collection_type == "list:paired"
    assert len(middle.elements) == 1

    inner = middle.elements[0]
    assert isinstance(inner, DataCollectionPairedRuntime)
    assert inner.elements.forward.class_ == "File"


def test_validate_collection_runtime_dict_rejects_unknown_leaf():
    """Unknown leaf collection_type raises ValueError."""
    raw = {"class": "Collection", "name": "x", "collection_type": "banana", "tags": [], "elements": []}
    with pytest.raises(ValueError, match="Cannot build runtime model"):
        _validate_collection_runtime_dict(raw)


def test_validate_collection_runtime_dict_rejects_unknown_nested():
    """Unknown nested collection_type raises ValueError."""
    raw = {"class": "Collection", "name": "x", "collection_type": "list:banana", "tags": [], "elements": []}
    with pytest.raises(ValueError, match="Cannot build runtime model"):
        _validate_collection_runtime_dict(raw)


class RewritingComputeEnvironment:
    def input_path_rewrite(self, dataset):
        return f"/job/inputs/dataset_{dataset.id}.dat"

    def input_extra_files_rewrite(self, dataset):
        return f"/job/inputs/dataset_{dataset.id}_files"


def _adapt_input(extension, deferred_uri=None):
    set_datatypes_registry(example_datatype_registry_for_sample())
    hda = HistoryDatasetAssociation(create_dataset=True, flush=False, name="input", extension=extension)
    hda.id = 1
    assert hda.dataset is not None
    hda.dataset.file_size = Decimal(4)
    if deferred_uri:
        hda.dataset.state = Dataset.states.DEFERRED
        hda.dataset.sources = [DatasetSource(source_uri=deferred_uri)]
    _, adapt_dataset, _ = setup_for_runtimeify(
        cast(Any, None), cast(Any, RewritingComputeEnvironment()), {"input": hda}
    )
    return adapt_dataset(DataRequestInternalHda(src="hda", id=1))


def test_adapt_dataset_file():
    result = _adapt_input("txt")
    assert result.class_ == "File"
    assert result.path == "/job/inputs/dataset_1.dat"


@pytest.mark.parametrize("extension", ["directory", "zarr", "ome_zarr"])
def test_adapt_dataset_directory_datatypes(extension):
    result = _adapt_input(extension)
    assert result.class_ == "Directory"
    assert result.path == "/job/inputs/dataset_1_files"
    assert result.format == extension


def test_adapt_dataset_deferred_input_has_location_and_no_path():
    result = _adapt_input("zarr", deferred_uri="https://example.org/data/store.zarr")
    assert result.class_ == "Directory"
    assert result.location == "https://example.org/data/store.zarr"
    assert result.path is None


def test_adapt_dataset_resolves_an_implicitly_converted_input():
    set_datatypes_registry(example_datatype_registry_for_sample())
    original = HistoryDatasetAssociation(create_dataset=True, flush=False, name="input", extension="csv")
    original.id = 1
    converted = HistoryDatasetAssociation(create_dataset=True, flush=False, name="input", extension="tabular")
    converted.id = 2
    assert converted.dataset is not None
    converted.dataset.file_size = Decimal(4)
    ImplicitlyConvertedDatasetAssociation(parent=original, dataset=converted, file_type="tabular")

    _, adapt_dataset, _ = setup_for_runtimeify(
        cast(Any, None), cast(Any, RewritingComputeEnvironment()), {"input": converted}
    )
    # The request still names the dataset the user picked; the job runs on its conversion.
    result = adapt_dataset(DataRequestInternalHda(src="hda", id=1))

    assert result.format == "tabular"
    assert result.path == "/job/inputs/dataset_2.dat"
