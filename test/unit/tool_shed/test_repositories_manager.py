import pytest

from galaxy.exceptions import RequestParameterInvalidException
from tool_shed.managers.repositories import guid_to_repository


def test_guid_to_repository_rejects_malformed_guid():
    # A guid without enough slashes used to raise a bare ValueError from the
    # tuple unpacking, surfacing as a 500 in the TRS API (see issue #23139).
    with pytest.raises(RequestParameterInvalidException):
        guid_to_repository(app=None, tool_id="localhost/repos/owner")
