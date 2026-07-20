from typing import cast

import pytest

from galaxy.exceptions import RequestParameterInvalidException
from tool_shed.managers.repositories import guid_to_repository
from tool_shed.structured_app import ToolShedApp


def test_guid_to_repository_rejects_malformed_guid():
    # A guid without enough slashes used to raise a bare ValueError from the
    # tuple unpacking, surfacing as a 500 in the TRS API (see issue #23139).
    # The malformed-id check runs before app is dereferenced, so a cast None
    # is enough to exercise this path.
    app = cast(ToolShedApp, None)
    with pytest.raises(RequestParameterInvalidException):
        guid_to_repository(app, "localhost/repos/owner")
