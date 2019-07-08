import os

from galaxy.auth import AuthManager
from galaxy.util.bunch import Bunch

AUTH_1_TEST_PATH = os.path.join(os.path.dirname(__file__), 'auth_1.xml')


def test_redact_config():
    config = Bunch(
        redact_username_in_logs=True,
        auth_config_file=AUTH_1_TEST_PATH,
    )
    app = Bunch(
        config=config
    )
    auth = AuthManager(app)
    assert auth.redact_username_in_logs

    config.redact_username_in_logs = False
    auth = AuthManager(app)
    assert not auth.redact_username_in_logs
