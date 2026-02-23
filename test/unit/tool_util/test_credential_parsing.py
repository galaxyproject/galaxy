"""Unit tests for credential parsing in tool XML and YAML test definitions."""

import os
import shutil
import tempfile

import pytest

from galaxy.tool_util.parser.factory import get_tool_source
from galaxy.util.unittest import TestCase

# Minimal tool XML wrapper that includes a test
_TOOL_XML_TEMPLATE = """\
<tool id="cred_test" name="Cred Test" version="1.0.0">
    <command>echo done</command>
    <inputs/>
    <outputs/>
    <tests>
{tests}
    </tests>
</tool>
"""

# Minimal tool YAML wrapper
_TOOL_YAML_TEMPLATE = """\
class: GalaxyTool
id: cred_test
name: Cred Test
version: "1.0.0"
shell_command: echo done
inputs: []
outputs: []
tests:
{tests}
"""


def _write_temp_tool(content: str, suffix: str, directory: str) -> str:
    path = os.path.join(directory, f"cred_test{suffix}")
    with open(path, "w") as f:
        f.write(content)
    return path


def _parse_tests(path: str):
    tool_source = get_tool_source(path)
    return tool_source.parse_tests_to_dict()["tests"]


class TestXmlCredentialParsing(TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _parse_xml_tests(self, test_block: str):
        xml = _TOOL_XML_TEMPLATE.format(tests=test_block)
        path = _write_temp_tool(xml, ".xml", self.tmpdir)
        return _parse_tests(path)

    def test_no_credentials(self):
        tests = self._parse_xml_tests("<test><assert_stdout><has_text text='done'/></assert_stdout></test>")
        assert tests[0]["credentials"] is None

    def test_single_credential_with_variable_and_secret(self):
        tests = self._parse_xml_tests("""<test>
                <credentials name="my_service">
                    <variable name="MY_USER" value="testuser"/>
                    <secret name="MY_PASS" value="testpass"/>
                </credentials>
            </test>""")
        creds = tests[0]["credentials"]
        assert creds is not None
        assert len(creds) == 1
        cred = creds[0]
        assert cred["name"] == "my_service"
        assert len(cred["variables"]) == 1
        assert cred["variables"][0] == {"name": "MY_USER", "value": "testuser"}
        assert len(cred["secrets"]) == 1
        assert cred["secrets"][0] == {"name": "MY_PASS", "value": "testpass"}

    def test_credential_version_explicit(self):
        tests = self._parse_xml_tests("""<test>
                <credentials name="svc" version="2.5">
                    <variable name="X" value="y"/>
                </credentials>
            </test>""")
        cred = tests[0]["credentials"][0]
        assert cred.get("version") == "2.5"

    def test_credential_version_omitted(self):
        """When version is absent, the field should not be present (no default injected by parser)."""
        tests = self._parse_xml_tests("""<test>
                <credentials name="svc">
                    <variable name="X" value="y"/>
                </credentials>
            </test>""")
        cred = tests[0]["credentials"][0]
        assert "version" not in cred

    def test_multiple_credentials(self):
        tests = self._parse_xml_tests("""<test>
                <credentials name="svc_a">
                    <variable name="A" value="1"/>
                </credentials>
                <credentials name="svc_b">
                    <secret name="B" value="2"/>
                </credentials>
            </test>""")
        creds = tests[0]["credentials"]
        assert len(creds) == 2
        assert creds[0]["name"] == "svc_a"
        assert creds[1]["name"] == "svc_b"

    def test_credentials_only_variables(self):
        tests = self._parse_xml_tests("""<test>
                <credentials name="svc">
                    <variable name="V" value="val"/>
                </credentials>
            </test>""")
        cred = tests[0]["credentials"][0]
        assert len(cred["variables"]) == 1
        assert cred["secrets"] == []

    def test_credentials_only_secrets(self):
        tests = self._parse_xml_tests("""<test>
                <credentials name="svc">
                    <secret name="S" value="sec"/>
                </credentials>
            </test>""")
        cred = tests[0]["credentials"][0]
        assert cred["variables"] == []
        assert len(cred["secrets"]) == 1

    def test_missing_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            self._parse_xml_tests("""<test>
                    <credentials>
                        <variable name="V" value="v"/>
                    </credentials>
                </test>""")

    def test_missing_variable_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            self._parse_xml_tests("""<test>
                    <credentials name="svc">
                        <variable value="v"/>
                    </credentials>
                </test>""")

    def test_missing_variable_value_raises(self):
        with pytest.raises(ValueError, match="value"):
            self._parse_xml_tests("""<test>
                    <credentials name="svc">
                        <variable name="V"/>
                    </credentials>
                </test>""")

    def test_missing_secret_value_raises(self):
        with pytest.raises(ValueError, match="value"):
            self._parse_xml_tests("""<test>
                    <credentials name="svc">
                        <secret name="S"/>
                    </credentials>
                </test>""")


class TestYamlCredentialParsing(TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _parse_yaml_tests(self, test_block: str):
        yaml = _TOOL_YAML_TEMPLATE.format(tests=test_block)
        path = _write_temp_tool(yaml, ".yml", self.tmpdir)
        return _parse_tests(path)

    def test_no_credentials(self):
        tests = self._parse_yaml_tests("  - doc: simple\n    outputs: {}\n")
        assert tests[0]["credentials"] is None

    def test_list_format_with_variable_and_secret(self):
        tests = self._parse_yaml_tests("""\
  - doc: cred test
    credentials:
      - name: my_service
        variables:
          - name: MY_USER
            value: testuser
        secrets:
          - name: MY_PASS
            value: testpass
    outputs: {}
""")
        creds = tests[0]["credentials"]
        assert creds is not None
        assert len(creds) == 1
        cred = creds[0]
        assert cred["name"] == "my_service"
        assert cred["variables"] == [{"name": "MY_USER", "value": "testuser"}]
        assert cred["secrets"] == [{"name": "MY_PASS", "value": "testpass"}]

    def test_dict_format(self):
        tests = self._parse_yaml_tests("""\
  - doc: cred test
    credentials:
      my_service:
        variables:
          - name: V
            value: v
        secrets: []
    outputs: {}
""")
        creds = tests[0]["credentials"]
        assert len(creds) == 1
        assert creds[0]["name"] == "my_service"

    def test_version_in_list_format(self):
        tests = self._parse_yaml_tests("""\
  - doc: cred test
    credentials:
      - name: svc
        version: "2.0"
        variables:
          - name: V
            value: v
        secrets: []
    outputs: {}
""")
        cred = tests[0]["credentials"][0]
        assert cred.get("version") == "2.0"

    def test_version_omitted(self):
        tests = self._parse_yaml_tests("""\
  - doc: cred test
    credentials:
      - name: svc
        variables:
          - name: V
            value: v
        secrets: []
    outputs: {}
""")
        cred = tests[0]["credentials"][0]
        assert "version" not in cred

    def test_missing_variable_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            self._parse_yaml_tests("""\
  - doc: cred test
    credentials:
      - name: svc
        variables:
          - value: v
        secrets: []
    outputs: {}
""")

    def test_missing_variable_value_raises(self):
        with pytest.raises(ValueError, match="value"):
            self._parse_yaml_tests("""\
  - doc: cred test
    credentials:
      - name: svc
        variables:
          - name: V
        secrets: []
    outputs: {}
""")
