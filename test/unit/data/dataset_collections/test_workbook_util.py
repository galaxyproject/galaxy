import base64

from galaxy.model.dataset_collections.workbook_util import (
    index_to_excel_column,
    load_workbook_from_base64,
)
from galaxy.util.resources import resource_path


def test_index_to_excel_column():
    assert index_to_excel_column(0) == "A"
    assert index_to_excel_column(25) == "Z"
    assert index_to_excel_column(26) == "AA"
    assert index_to_excel_column(700) == "ZY"
    assert index_to_excel_column(701) == "ZZ"
    assert index_to_excel_column(702) == "AAA"


def test_load_workbook_from_base64():
    workbook_base64 = resource_path_to_base64("filled_in_workbook_1.xlsx")
    workbook = load_workbook_from_base64(workbook_base64)
    assert workbook is not None

    workbook_base64 = resource_path_to_base64("filled_in_workbook_1.tsv")
    workbook = load_workbook_from_base64(workbook_base64)
    assert workbook is not None


def resource_path_to_base64(resource_name: str) -> str:
    resource_bytes = resource_path("galaxy.model.unittest_utils", resource_name).read_bytes()
    return base64.b64encode(resource_bytes).decode("utf-8")
