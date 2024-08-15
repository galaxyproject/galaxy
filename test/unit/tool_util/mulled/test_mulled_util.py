import pytest

from galaxy.tool_util.deps.mulled.util import version_sorted


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
