"""Unit tests for credential parsing from tool test definitions."""

from galaxy.tool_util.unittest_utils import functional_test_tool_path
from galaxy.util.unittest import TestCase
from .test_parsing import FunctionalTestToolTestCase


class TestCredentialParsing(FunctionalTestToolTestCase):
    test_path = "credentials_test.xml"

    def test_credentials_parsing(self):
        tests_dict = self._tool_source.parse_tests_to_dict()
        tests = tests_dict["tests"]
        assert len(tests) == 2

        # First test: test_user / test_password_123
        creds = tests[0]["credentials"]
        assert creds is not None
        assert len(creds) == 1
        cred = creds[0]
        assert cred["name"] == "test_service"
        assert cred["variables"] == [{"name": "TEST_USERNAME", "value": "test_user"}]
        assert cred["secrets"] == [{"name": "TEST_PASSWORD", "value": "test_password_123"}]

        # Second test: another_user / secret
        creds2 = tests[1]["credentials"]
        assert creds2 is not None
        assert len(creds2) == 1
        assert creds2[0]["variables"] == [{"name": "TEST_USERNAME", "value": "another_user"}]
        assert creds2[0]["secrets"] == [{"name": "TEST_PASSWORD", "value": "secret"}]


class TestNoCredentials(TestCase):
    """Verify tools without credentials return None."""

    def test_no_credentials_field(self):
        from galaxy.tool_util.parser.factory import get_tool_source

        path = functional_test_tool_path("simple_constructs.xml")
        tool_source = get_tool_source(path)
        tests = tool_source.parse_tests_to_dict()["tests"]
        for test in tests:
            assert test.get("credentials") is None
