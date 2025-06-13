import base64

import pytest

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.model.dataset_collections.workbook_util import (
    index_to_excel_column,
    load_workbook_from_base64,
)


def test_index_to_excel_column():
    assert index_to_excel_column(0) == "A"
    assert index_to_excel_column(25) == "Z"
    assert index_to_excel_column(26) == "AA"
    assert index_to_excel_column(700) == "ZY"
    assert index_to_excel_column(701) == "ZZ"
    assert index_to_excel_column(702) == "AAA"


def test_loading_invalid_workbook():
    base64Tabular = base64.b64encode(b"1\t2\t3\n").decode("utf-8")
    with pytest.raises(RequestParameterInvalidException):
        load_workbook_from_base64(base64Tabular)
