from typing import Any

import pytest

from galaxy.tools.actions import (
    upload,
    upload_common,
)
from galaxy.util.bunch import Bunch


@pytest.mark.parametrize(
    ("url", "expected_name"),
    [
        ("https://example.org/data/input.txt", "input.txt"),
        ("https://fetchuser:s3cret@example.org", "example.org"),
        ("https://fetchuser:s3cret@example.org/data/input.txt", "input.txt"),
    ],
)
def test_precreated_url_dataset_name_hides_userinfo(monkeypatch, url, expected_name):
    created_names = []

    def new_upload(trans, cntrller, uploaded_dataset, **kwargs):
        created_names.append(uploaded_dataset.name)
        return Bunch(id=len(created_names))

    monkeypatch.setattr(upload_common, "new_upload", new_upload)
    trans: Any = None
    outputs: list[Any] = []
    upload._precreate_fetched_hdas(trans, None, {"elements": [{"src": "url", "url": url}]}, outputs)
    assert created_names == [expected_name]
