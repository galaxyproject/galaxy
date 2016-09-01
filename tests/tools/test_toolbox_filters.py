from galaxy.tools.toolbox.filters import FilterFactory

from galaxy.util.bunch import Bunch


def test_stock_filtering_requires_login_tools( ):
    anonymous_user_trans = mock_trans( has_user=False )
    filters = filter_factory( {} ).build_filters( mock_trans() )[ 'tool' ]
    assert not is_filtered( filters, anonymous_user_trans, mock_tool( require_login=False ) )
    assert is_filtered( filters, anonymous_user_trans, mock_tool( require_login=True ) )

    logged_in_trans = mock_trans( has_user=True )
    filters = filter_factory( {} ).build_filters( logged_in_trans )[ 'tool' ]
    assert not is_filtered( filters, logged_in_trans, mock_tool( require_login=True ) )


def test_stock_filtering_hidden_tools( ):
    filters = filter_factory( {} ).build_filters( mock_trans() )[ 'tool' ]
    assert not is_filtered( filters, mock_trans(), mock_tool( hidden=False ) )
    assert is_filtered( filters, mock_trans(), mock_tool( hidden=True ) )


def test_trackster_filtering( ):
    filters = filter_factory( {} ).build_filters( mock_trans(), trackster=True )[ 'tool' ]
    # Ekkk... is trackster_conf broken? Why is it showing up.
    # assert is_filtered( filters, mock_trans(), mock_tool( trackster_conf=False ) )
    assert not is_filtered( filters, mock_trans(), mock_tool( trackster_conf=True ) )


def test_custom_filters():
    filters = filter_factory().build_filters( mock_trans() )
    tool_filters = filters[ "tool" ]
    # TODO: the fact that -1 is the custom filter is an implementation
    # detail that should not be tested here.
    assert tool_filters[ -1 ].__doc__ == "Test Filter Tool"

    section_filters = filters[ "section" ]
    assert section_filters[ 0 ].__doc__ == "Test Filter Section"

    label_filters = filters[ "label" ]
    assert label_filters[ 0 ].__doc__ == "Test Filter Label 1"
    assert label_filters[ 1 ].__doc__ == "Test Filter Label 2"


def filter_factory(config_dict=None):
    if config_dict is None:
        config_dict = dict(
            tool_filters=["filtermod:filter_tool"],
            tool_section_filters=["filtermod:filter_section"],
            tool_label_filters=["filtermod:filter_label_1", "filtermod:filter_label_2"],
        )
    config = Bunch( **config_dict )
    config.toolbox_filter_base_modules = "galaxy.tools.filters,tools.filter_modules"
    app = Bunch(config=config)
    toolbox = Bunch(app=app)
    return FilterFactory(toolbox)


def is_filtered( filters, trans, tool ):
    context = Bunch( trans=trans )
    return not all( map( lambda filter: filter( context, tool ), filters ) )


def mock_tool( require_login=False, hidden=False, trackster_conf=False, allow_access=True ):
    def allow_user_access(user, attempting_access):
        assert not attempting_access
        return allow_access

    tool = Bunch(
        require_login=require_login,
        hidden=hidden,
        trackster_conf=trackster_conf,
        allow_user_access=allow_user_access,
    )
    return tool


def mock_trans( has_user=True, is_admin=False ):
    trans = Bunch( user_is_admin=lambda: is_admin )
    if has_user:
        trans.user = Bunch(preferences={})
    else:
        trans.user = None
    return trans
