from galaxy.datatypes.binary import Xlsx


def test_sheet_names() :
    datatype = Xlsx()
    sheet_names = datatype.get_xlsx_sheet_names("test-data/sheet_name.xlsx")

    assert sheet_names == ["Sheet1", "Sheet2"]
