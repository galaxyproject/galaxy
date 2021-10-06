from galaxy.util.bunch import Bunch


def mock_trans(has_user=True, is_admin=False):
    """A mock ``trans`` object for exposing user info to toolbox filter unit tests."""
    trans = Bunch(user_is_admin=is_admin)
    if has_user:
        trans.user = Bunch(preferences={})
    else:
        trans.user = None
    return trans
