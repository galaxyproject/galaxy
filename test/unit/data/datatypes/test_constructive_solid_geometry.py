from lib.galaxy.datatypes.constructive_solid_geometry import VtkXml, GocadSGrid, FeflowFem
from .util import (
    get_dataset,
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


def test_GocadSGrid_set_meta():
    gocad = GocadSGrid()
    with get_dataset("testfile.sg") as dataset:
        dataset.dataset = MockDatasetDataset(dataset.get_file_name())
        gocad.set_meta(dataset)

    assert dataset.metadata.gocad_version == "1"
    assert dataset.metadata.name == "flow_simulation_grid_stair-stepped"


def test_FeflowFem_set_meta():
    feflow = FeflowFem()
    with get_dataset("testfile.fem") as dataset:
        dataset.dataset = MockDatasetDataset(dataset.get_file_name())
        feflow.set_meta(dataset)

    assert dataset.metadata.feflow_version == "v.6.004"
    assert dataset.metadata.problem_type == "A new FEFLOW problem"
