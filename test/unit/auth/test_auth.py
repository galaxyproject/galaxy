from galaxy.auth.providers.alwaysreject import AlwaysReject
from galaxy.auth.providers.localdb import LocalDB
from galaxy.model import User


def test_alwaysreject():
    t = AlwaysReject()
    assert t.authenticate("testmail", "testuser", "secret", {}, None) == (None, "", "")


def test_localdb():
    user = User(email="testmail", username="tester")
    user.set_password_cleartext("test123")
    t = LocalDB()
    # Passing None as request object should not really mess up the tests as we
    # are not using any logic related to request object in AuthManager
    reject = t.authenticate_user(user, "wrong", {"redact_username_in_logs": False}, None)
    accept = t.authenticate_user(user, "test123", {"redact_username_in_logs": False}, None)
    assert reject is False
    assert accept is True
    # Password must conform to policy (length etc)
    try:
        user.set_password_cleartext("test")
    except Exception:
        pass
    else:
        raise Exception("Password policy validation failed")
