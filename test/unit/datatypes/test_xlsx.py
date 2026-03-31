from galaxy.datatypes.binary import Xlsx

from .util import MockDataset

def test_sheet_names () :
    dataset = MockDataset(id=1)

    dataset.set_file_name("test-data/sheet_name.xlsx")

    datatype = Xlsx()
    datatype.set_meta(dataset)

    assert dataset.metadata.sheet_names == ["Sheet1", "Sheet2"]