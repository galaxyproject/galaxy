from galaxy.datatypes.binary import Xlsx
from galaxy.datatypes.sniff import get_test_fname
from .util import MockDataset


def test_get_xlsx_sheet_names():
    sheet_names = Xlsx().get_xlsx_sheet_names(get_test_fname("sheet_name.xlsx"))
    assert sheet_names == ["Sheet1", "Sheet2"]


def test_set_meta_populates_sheet_names():
    dataset = MockDataset(id=1)
    dataset.set_file_name(get_test_fname("sheet_name.xlsx"))
    Xlsx().set_meta(dataset)
    assert dataset.metadata.sheet_names == ["Sheet1", "Sheet2"]
