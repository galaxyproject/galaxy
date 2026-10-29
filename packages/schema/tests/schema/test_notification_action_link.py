import pytest
from pydantic import ValidationError

from galaxy.schema.notifications import ActionLink


def test_action_link_defaults_to_current_tab():
    assert ActionLink(action_name="Open", link="/histories").target == "_self"


def test_action_link_rejects_unrecognized_targets():
    with pytest.raises(ValidationError):
        ActionLink(action_name="Open", link="/histories", target="named-window")
