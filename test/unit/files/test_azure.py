import os

import pytest

from galaxy.util.unittest_utils import skip_unless_environ
from ._util import assert_can_write_and_read_to_conf

pytest.importorskip("fs.azblob")


@skip_unless_environ("GALAXY_TEST_AZURE_CONTAINER_NAME")
@skip_unless_environ("GALAXY_TEST_AZURE_ACCOUNT_KEY")
@skip_unless_environ("GALAXY_TEST_AZURE_ACCOUNT_NAME")
def test_azure():
    conf = {
        "type": "azure",
        "id": "azure_test",
        "doc": "Test an Azure Blob Store thing.",
        "container_name": os.environ["GALAXY_TEST_AZURE_CONTAINER_NAME"],
        "account_key": os.environ["GALAXY_TEST_AZURE_ACCOUNT_KEY"],
        "account_name": os.environ["GALAXY_TEST_AZURE_ACCOUNT_NAME"],
        "namespace_type": os.environ.get("GALAXY_TEST_AZURE_NAMESPACE_TYPE", "hierarchal"),
        "writable": True,
    }
    assert_can_write_and_read_to_conf(conf)
