import pytest
from pydantic import ValidationError
from galaxy.model import DatasetCollection, DatasetCollectionElement, HistoryDatasetAssociation
from galaxy.tool_util_models.parameters import (
    build_collection_model_for_type,
    DataCollectionPairedRuntime,
    DataCollectionListRuntime,
    DataCollectionRecordRuntime,
    DataCollectionPairedOrUnpairedRuntime,
    DataCollectionSampleSheetRuntime,
    DataInternalJson,
)
from galaxy.tools.runtime import collection_to_runtime

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
        if isinstance(content, list): # Nested collection [type, elements]
             child_collection = create_model_collection(content[0], content[1])
             dce = DatasetCollectionElement(
                 collection=collection,
                 element_identifier=name,
                 element_index=i,
                 element=child_collection
             )
        else: # HDA
             hda = HistoryDatasetAssociation(
                 create_dataset=True, 
                 flush=False,
                 name=content
             )
             hda.id = i + 100 # Fake ID for testing
             # Also satisfy accessing hda.dataset.created_from_basename or hda.name in generic adapt if needed
             hda.dataset.id = i + 1000
             
             dce = DatasetCollectionElement(
                 collection=collection,
                 element_identifier=name,
                 element_index=i,
                 element=hda
             )

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
        collection,
        name="test_paired",
        tags=["t1"],
        adapt_dataset=mock_adapt_dataset,
        compute_environment=None
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
        collection,
        name="test_list",
        tags=[],
        adapt_dataset=mock_adapt_dataset,
        compute_environment=None
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
        collection,
        name="test_nested",
        tags=[],
        adapt_dataset=mock_adapt_dataset,
        compute_environment=None
    )
    
    expected_model = build_collection_model_for_type("list:paired")
    assert isinstance(runtime, expected_model)
    assert type(runtime).__name__ == "DynamicCollection_list_paired"
    assert runtime.collection_type == "list:paired"
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
            collection,
            name="bad_paired",
            tags=[],
            adapt_dataset=mock_adapt_dataset,
            compute_environment=None
        )

def test_collection_to_runtime_record(mock_adapt_dataset):
    # Record collection
    collection = create_model_collection("record", [("f1", "hda1"), ("f2", "hda2")])
    collection.fields = [{"name": "f1", "type": "File"}, {"name": "f2", "type": "File"}]
    
    runtime = collection_to_runtime(
        collection,
        name="test_record",
        tags=[],
        adapt_dataset=mock_adapt_dataset,
        compute_environment=None
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
        collection,
        name="test_sheet",
        tags=[],
        adapt_dataset=mock_adapt_dataset,
        compute_environment=None
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
        collection,
        name="test_pou_paired",
        tags=[],
        adapt_dataset=mock_adapt_dataset,
        compute_environment=None
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
        compute_environment=None
    )
    
    assert isinstance(runtime_unpaired, DataCollectionPairedOrUnpairedRuntime)
    assert runtime_unpaired.elements["unpaired"].class_ == "File"


# --- Dynamic model factory tests ---

_FILE_ELEMENT = {
    "class": "File",
    "element_identifier": "f1",
    "basename": "f1.txt",
    "location": "step_input://0",
    "path": "/tmp/f1.txt",
    "nameroot": "f1",
    "nameext": ".txt",
    "format": "txt",
    "size": 100,
}


def test_build_collection_model_returns_static_for_leaf():
    assert build_collection_model_for_type("list") is DataCollectionListRuntime
    assert build_collection_model_for_type("paired") is DataCollectionPairedRuntime
    assert build_collection_model_for_type("record") is DataCollectionRecordRuntime


def test_build_collection_model_returns_none_for_unknown():
    assert build_collection_model_for_type("unknown_type") is None


def test_dynamic_model_accepts_correct_inner_type():
    model = build_collection_model_for_type("list:paired")
    result = model.model_validate({
        "class": "Collection", "name": "good",
        "collection_type": "list:paired", "tags": [],
        "elements": [{
            "class": "Collection", "name": "p1",
            "collection_type": "paired", "tags": [],
            "elements": {
                "forward": {**_FILE_ELEMENT, "element_identifier": "forward"},
                "reverse": {**_FILE_ELEMENT, "element_identifier": "reverse", "basename": "r.txt",
                            "location": "step_input://1", "path": "/tmp/r.txt", "nameroot": "r"},
            },
        }],
    })
    assert result.collection_type == "list:paired"
    assert isinstance(result.elements[0], DataCollectionPairedRuntime)


def test_dynamic_model_rejects_wrong_inner_type():
    model = build_collection_model_for_type("list:paired")
    with pytest.raises(ValidationError):
        model.model_validate({
            "class": "Collection", "name": "bad",
            "collection_type": "list:paired", "tags": [],
            "elements": [{
                "class": "Collection", "name": "l1",
                "collection_type": "list", "tags": [],
                "elements": [_FILE_ELEMENT],
            }],
        })


def test_dynamic_model_rejects_wrong_collection_type_literal():
    model = build_collection_model_for_type("list:paired")
    with pytest.raises(ValidationError):
        model.model_validate({
            "class": "Collection", "name": "bad",
            "collection_type": "list:list", "tags": [], "elements": [],
        })


def test_dynamic_model_rejects_depth_mismatch():
    model = build_collection_model_for_type("list:list:paired")
    # Inner is "paired" (depth 1) but should be "list:paired" (depth 2)
    with pytest.raises(ValidationError):
        model.model_validate({
            "class": "Collection", "name": "bad",
            "collection_type": "list:list:paired", "tags": [],
            "elements": [{
                "class": "Collection", "name": "p1",
                "collection_type": "paired", "tags": [],
                "elements": {
                    "forward": {**_FILE_ELEMENT, "element_identifier": "forward"},
                    "reverse": {**_FILE_ELEMENT, "element_identifier": "reverse", "basename": "r.txt",
                                "location": "step_input://1", "path": "/tmp/r.txt", "nameroot": "r"},
                },
            }],
        })


def test_dynamic_model_json_schema_precise():
    """JSON Schema for list:paired shows elements as array of paired, not Union."""
    model = build_collection_model_for_type("list:paired")
    schema = model.model_json_schema()
    # elements should reference paired model, NOT anyOf with all types
    elements_schema = schema["properties"]["elements"]
    schema_str = str(elements_schema)
    assert "anyOf" not in schema_str


def test_dynamic_model_caching():
    m1 = build_collection_model_for_type("list:paired")
    m2 = build_collection_model_for_type("list:paired")
    assert m1 is m2


# --- Step 2: E2E list:list:paired (gap #1) ---

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
    assert isinstance(runtime, expected_model)
    assert runtime.collection_type == "list:list:paired"
    assert len(runtime.elements) == 1

    middle = runtime.elements[0]
    expected_middle = build_collection_model_for_type("list:paired")
    assert isinstance(middle, expected_middle)
    assert middle.collection_type == "list:paired"
    assert len(middle.elements) == 1

    inner = middle.elements[0]
    assert isinstance(inner, DataCollectionPairedRuntime)
    assert inner.elements.forward.class_ == "File"


# --- Step 3: record:* nested dynamic models (gap #2) ---

def test_dynamic_model_record_paired_accepts_correct():
    """record:paired dynamic model: dict of paired collections."""
    model = build_collection_model_for_type("record:paired")
    assert model is not None
    result = model.model_validate({
        "class": "Collection", "name": "rec",
        "collection_type": "record:paired", "tags": [],
        "elements": {
            "sample_a": {
                "class": "Collection", "name": "sample_a",
                "collection_type": "paired", "tags": [],
                "elements": {
                    "forward": {**_FILE_ELEMENT, "element_identifier": "forward"},
                    "reverse": {**_FILE_ELEMENT, "element_identifier": "reverse",
                                "basename": "r.txt", "location": "step_input://1",
                                "path": "/tmp/r.txt", "nameroot": "r"},
                },
            },
        },
    })
    assert result.collection_type == "record:paired"
    assert isinstance(result.elements["sample_a"], DataCollectionPairedRuntime)


def test_dynamic_model_record_paired_rejects_wrong_inner():
    """record:paired rejects inner collection with wrong type (list instead of paired)."""
    model = build_collection_model_for_type("record:paired")
    with pytest.raises(ValidationError):
        model.model_validate({
            "class": "Collection", "name": "bad_rec",
            "collection_type": "record:paired", "tags": [],
            "elements": {
                "sample_a": {
                    "class": "Collection", "name": "sample_a",
                    "collection_type": "list", "tags": [],
                    "elements": [_FILE_ELEMENT],
                },
            },
        })


# --- Step 4: Unknown nested segments return None (gap #5) ---

def test_build_collection_model_returns_none_for_unknown_nested():
    assert build_collection_model_for_type("list:unknown_type") is None
    assert build_collection_model_for_type("record:unknown") is None
    assert build_collection_model_for_type("list:list:unknown") is None


# --- Step 5: Empty dict elements on record-like dynamic model (gap #6) ---

def test_dynamic_model_record_paired_empty_elements():
    """Empty dict elements on a record-like dynamic model should validate."""
    model = build_collection_model_for_type("record:paired")
    result = model.model_validate({
        "class": "Collection", "name": "empty_rec",
        "collection_type": "record:paired", "tags": [],
        "elements": {},
    })
    assert result.elements == {}


# --- Step 6: JSON schema for deeply nested models (gap #7) ---

def test_dynamic_model_json_schema_deeply_nested():
    """JSON Schema for list:list:paired has 3 levels, no anyOf at any level."""
    model = build_collection_model_for_type("list:list:paired")
    schema = model.model_json_schema()
    # Outer elements: array of list:paired models
    elements_schema = schema["properties"]["elements"]
    schema_str = str(elements_schema)
    assert "anyOf" not in schema_str

    # Should have definitions for multiple distinct models (at least the inner dynamic + leaf)
    defs = schema.get("$defs", {})
    assert len(defs) >= 2
    assert any("list_paired" in k for k in defs.keys())
