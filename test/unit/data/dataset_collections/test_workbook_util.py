from galaxy.model.dataset_collections.workbook_util import index_to_excel_column


def test_index_to_excel_column():
    assert index_to_excel_column(0) == "A"
    assert index_to_excel_column(25) == "Z"
    assert index_to_excel_column(26) == "AA"
    assert index_to_excel_column(700) == "ZY"
    assert index_to_excel_column(701) == "ZZ"
    assert index_to_excel_column(702) == "AAA"
