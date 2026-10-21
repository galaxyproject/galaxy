from galaxy.datatypes.registry import example_datatype_registry_for_sample
from galaxy.managers.datatypes import get_preferred_visualization


def test_preferred_visualization_direct_mapping():
    registry = example_datatype_registry_for_sample()
    mapping = get_preferred_visualization(registry, "hyphy_results.json")
    assert mapping
    assert mapping["visualization"] == "hyphyvision"


def test_preferred_visualization_not_inherited_by_sibling_subclass():
    registry = example_datatype_registry_for_sample()
    for extension in ("anvio_state", "freq.json", "hivtrace"):
        assert get_preferred_visualization(registry, extension) is None


def test_preferred_visualization_inherited_from_parent_datatype():
    registry = example_datatype_registry_for_sample()
    for extension, visualization in (("mbi", "h5web"), ("ome.tiff", "tiffviewer"), ("probam", "igv")):
        mapping = get_preferred_visualization(registry, extension)
        assert mapping
        assert mapping["visualization"] == visualization
