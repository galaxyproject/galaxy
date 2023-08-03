import pytest

from galaxy.schema.fields import Security
from galaxy.security.idencoding import IdEncodingHelper


@pytest.fixture(scope="session", autouse=True)
def security() -> IdEncodingHelper:
    Security.security = IdEncodingHelper(id_secret="testing")
    return Security.security
