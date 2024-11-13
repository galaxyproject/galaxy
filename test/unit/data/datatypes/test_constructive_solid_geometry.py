from galaxy.datatypes.constructive_solid_geometry import VtkXml
from .util import (
    get_input_files,
    MockDataset,
)


def test_vtkXml_set_meta():
    vtkXml = VtkXml()
    with get_input_files("data.vtu") as input_files:
        dataset = MockDataset(1)
        dataset.set_file_name(input_files[0])

        vtkXml.set_meta(dataset)

    assert dataset.metadata.vtk_version == "0.1"
    assert dataset.metadata.file_format == "XML"
    assert dataset.metadata.dataset_type == "UnstructuredGrid"
