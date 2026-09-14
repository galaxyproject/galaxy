import pytest

from galaxy.tool_util.deps.mulled.util import (
    quay_repositories,
    version_sorted,
)


def test_quay_repositories_paginates(mocker):
    first_page = mocker.Mock()
    first_page.json.return_value = {
        "repositories": [{"name": "bwa"}],
        "next_page": "page-2",
    }
    second_page = mocker.Mock()
    second_page.json.return_value = {"repositories": [{"name": "samtools"}]}
    get = mocker.patch("galaxy.tool_util.deps.mulled.util.requests.get", side_effect=[first_page, second_page])

    assert quay_repositories("biocontainers") == ["bwa", "samtools"]
    assert get.call_args_list[0].kwargs["params"] == {"public": "true", "namespace": "biocontainers"}
    assert get.call_args_list[1].kwargs["params"]["next_page"] == "page-2"
    first_page.raise_for_status.assert_called_once_with()
    second_page.raise_for_status.assert_called_once_with()


@pytest.mark.parametrize(
    "tags,tag",
    [
        (["2.22--he941832_1", "2.22--he860b03_2", "2.22--hdbcaa40_3"], "2.22--hdbcaa40_3"),
        (["1.1.2--py27_0", "1.1.2--py36_0", "1.1.2--py35_0"], "1.1.2--py36_0"),
        (
            ["6725cda82000b8e514baddcbf8c2dce054e3f797-1", "6725cda82000b8e514baddcbf8c2dce054e3f797-0"],
            "6725cda82000b8e514baddcbf8c2dce054e3f797-1",
        ),
        (["python:3.5", "python:3.7", "python:3.7--2"], "python:3.7--2"),
    ],
)
def test_version_sorted(tags, tag):
    assert version_sorted(tags)[0] == tag
