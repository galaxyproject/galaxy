import pytest

from galaxy.schema.fields import BaseDatabaseIdField
from galaxy.security.idencoding import IdEncodingHelper


@pytest.fixture(scope="session", autouse=True)
def security() -> IdEncodingHelper:
    BaseDatabaseIdField.security = IdEncodingHelper(id_secret="testing")
    return BaseDatabaseIdField.security
