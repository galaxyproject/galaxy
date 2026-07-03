from galaxy.tool_util.toolbox.filters import FilterFactory
from galaxy.tool_util.unittest_utils import mock_trans
from galaxy.util.bunch import Bunch


def test_stock_filtering_requires_login_tools():
    anonymous_user_trans = mock_trans(has_user=False)
    filters = build_visibility_filters(anonymous_user_trans)["tool"]
    assert not is_filtered(filters, anonymous_user_trans, mock_tool(require_login=False))
    assert is_filtered(filters, anonymous_user_trans, mock_tool(require_login=True))

    logged_in_trans = mock_trans(has_user=True)
    filters = build_visibility_filters(logged_in_trans)["tool"]
    assert not is_filtered(filters, logged_in_trans, mock_tool(require_login=True))


def test_stock_filtering_hidden_tools():
    trans = mock_trans()
    filters = build_visibility_filters(trans)["tool"]
    assert not is_filtered(filters, trans, mock_tool(hidden=False))
    assert is_filtered(filters, trans, mock_tool(hidden=True))


def build_visibility_filters(trans):
    return filter_factory().build_filters(trans)


def filter_factory(config_dict=None):
    config_dict = config_dict or {}
    config = Bunch(**config_dict)
    app = Bunch(config=config)
    toolbox = Bunch(app=app)
    return FilterFactory(toolbox)


def is_filtered(filters, trans, tool):
    context = Bunch(trans=trans)
    return not all(_(context, tool) for _ in filters)


def mock_tool(require_login=False, hidden=False, allow_access=True):
    def allow_user_access(user, attempting_access):
        assert not attempting_access
        return allow_access

    tool = Bunch(
        require_login=require_login,
        hidden=hidden,
        allow_user_access=allow_user_access,
    )
    return tool
