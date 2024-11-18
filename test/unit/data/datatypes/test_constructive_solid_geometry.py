from galaxy.datatypes.constructive_solid_geometry import VtkXml
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
