from typing import Any

import pytest

from galaxy.datatypes.constructive_solid_geometry import (
    AsciiRaster,
    FeflowFem,
    GocadSGrid,
    VtkXml,
)
from .util import (
    get_dataset,
    MockDataset,
    MockDatasetDataset,
)


def test_vtkXml_set_meta():
    vtkXml = VtkXml()
    with get_dataset("data.vtu") as dataset:
        dataset.dataset = MockDatasetDataset(dataset.get_file_name())
        vtkXml.set_meta(dataset)

    assert dataset.metadata.vtk_version == "0.1"
    assert dataset.metadata.file_format == "XML"
    assert dataset.metadata.dataset_type == "UnstructuredGrid"


def _vtk_xml_dataset(dataset_type: str | None) -> Any:
    dataset: Any = MockDataset(1)
    dataset.extension = "vtkxml"
    dataset.metadata.dataset_type = dataset_type
    return dataset


@pytest.mark.parametrize(
    "dataset_type, expected_extension",
    [
        ("ImageData", "vti"),
        ("PolyData", "vtp"),
        ("RectilinearGrid", "vtr"),
        ("StructuredGrid", "vts"),
        ("UnstructuredGrid", "vtu"),
        ("PImageData", "pvti"),
        ("PPolyData", "pvtp"),
        ("PRectilinearGrid", "pvtr"),
        ("PStructuredGrid", "pvts"),
        ("PUnstructuredGrid", "pvtu"),
    ],
)
def test_vtkXml_download_extension(dataset_type, expected_extension):
    assert VtkXml().get_download_extension(_vtk_xml_dataset(dataset_type)) == expected_extension


@pytest.mark.parametrize("dataset_type", [None, "?", "NotAVTKDataSetType"])
def test_vtkXml_download_extension_unknown_type(dataset_type):
    assert VtkXml().get_download_extension(_vtk_xml_dataset(dataset_type)) == "vtkxml"


def test_vtkXml_download_filename():
    vtkXml = VtkXml()
    with get_dataset("data.vtu") as dataset:
        dataset.dataset = MockDatasetDataset(dataset.get_file_name())
        dataset.extension = "vtkxml"
        dataset.name = "my unstructured grid"
        dataset.hid = 3
        vtkXml.set_meta(dataset)

        # clients that just pass the extension of the dataset get the specific one
        assert vtkXml._download_filename(dataset) == "Galaxy3-[my unstructured grid].vtu"
        assert vtkXml._download_filename(dataset, to_ext="vtkxml") == "Galaxy3-[my unstructured grid].vtu"
        assert vtkXml._download_filename(dataset, to_ext="data") == "Galaxy3-[my unstructured grid].vtu"
        # an explicitly requested extension is respected
        assert vtkXml._download_filename(dataset, to_ext="vtp") == "Galaxy3-[my unstructured grid].vtp"


def test_GocadSGrid_set_meta():
    gocad = GocadSGrid()
    with get_dataset("testfile.gocad.sg") as dataset:
        dataset.dataset = MockDatasetDataset(dataset.get_file_name())
        gocad.set_meta(dataset)

    assert dataset.metadata.gocad_version == "1"
    assert dataset.metadata.name == "flow_simulation_grid_stair-stepped"


def test_FeflowFem_set_meta():
    feflow = FeflowFem()
    with get_dataset("testfile.feflow.fem") as dataset:
        dataset.dataset = MockDatasetDataset(dataset.get_file_name())
        feflow.set_meta(dataset)

    assert dataset.metadata.feflow_version == "v.6.004"
    assert dataset.metadata.problem_type == "A new FEFLOW problem"


def test_AsciiRaster_set_meta():
    asciiRaster = AsciiRaster()
    with get_dataset("testfile.raster.asc") as dataset:
        dataset.dataset = MockDatasetDataset(dataset.get_file_name())
        asciiRaster.set_meta(dataset)

    assert dataset.metadata.ncols == 20
    assert dataset.metadata.nrows == 39
