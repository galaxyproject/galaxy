from unittest.mock import Mock


def mock_trans(has_user=True, is_admin=False):
    """A mock ``trans`` object for exposing user info to toolbox filter unit tests."""
    trans = Mock(user_is_admin=is_admin)
    if has_user:
        trans.user = Mock(preferences={})
    else:
        trans.user = None
    return trans
