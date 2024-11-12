from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from galaxy.exceptions import (
    RequestParameterInvalidException,
    RequestParameterMissingException,
)
from galaxy.util.config_templates import (
    StrictModel,
    TemplateEnvironmentEntry,
    TemplateSecret,
    TemplateVariable,
    TemplateVariableBoolean,
    TemplateVariableInteger,
    TemplateVariablePathComponent,
    TemplateVariableString,
    validate_secrets_and_variables,
)

TEST_TEMPLATE_ID = "test_id"
TEST_TEMPLATE_VERSION = 0


class TestTemplate(StrictModel):
    id: str
    type: str = "test"
    version: int
    variables: Optional[List[TemplateVariable]]
    secrets: Optional[List[TemplateSecret]]
    environment: Optional[List[TemplateEnvironmentEntry]]


def _template_with_variable(variable: TemplateVariable) -> TestTemplate:
    return TestTemplate(
        id=TEST_TEMPLATE_ID,
        version=TEST_TEMPLATE_VERSION,
        variables=[variable],
        secrets=None,
        environment=None,
    )


def _template_with_secret(name: str) -> TestTemplate:
    secret = TemplateSecret(name=name, help="Help for secret.")
    return TestTemplate(
        id=TEST_TEMPLATE_ID,
        version=TEST_TEMPLATE_VERSION,
        variables=[],
        secrets=[secret],
        environment=None,
    )


class TestInstanceDefinition(StrictModel):
    template_id: str
    template_version: int
    variables: Dict[str, Any]
    secrets: Dict[str, str]


def _test_instance_with_variables(variables: Dict[str, Any]) -> TestInstanceDefinition:
    return TestInstanceDefinition(
        template_id=TEST_TEMPLATE_ID,
        template_version=TEST_TEMPLATE_VERSION,
        variables=variables,
        secrets={},
    )


def _test_instance_with_secrets(secrets: Dict[str, str]) -> TestInstanceDefinition:
    return TestInstanceDefinition(
        template_id=TEST_TEMPLATE_ID,
        template_version=TEST_TEMPLATE_VERSION,
        variables={},
        secrets=secrets,
    )


def test_variable_typing_string():
    template = _template_with_variable(TemplateVariableString(name="test_var", help=None, type="string"))
    instance = _test_instance_with_variables({"test_var": "moocow"})
    validate_secrets_and_variables(instance, template)

    instance = _test_instance_with_variables({"test_var": 5})
    e = assert_validation_throws(instance, template)
    assert isinstance(e, RequestParameterInvalidException)

    instance = _test_instance_with_variables({"test_var": False})
    e = assert_validation_throws(instance, template)
    assert isinstance(e, RequestParameterInvalidException)


def test_variable_typing_boolean():
    template = _template_with_variable(TemplateVariableBoolean(name="test_var", help=None, type="boolean"))
    instance = _test_instance_with_variables({"test_var": False})
    validate_secrets_and_variables(instance, template)

    instance = _test_instance_with_variables({"test_var": 0})
    e = assert_validation_throws(instance, template)
    assert isinstance(e, RequestParameterInvalidException)

    instance = _test_instance_with_variables({"test_var": "false"})
    e = assert_validation_throws(instance, template)
    assert isinstance(e, RequestParameterInvalidException)


def test_variable_typing_int():
    template = _template_with_variable(TemplateVariableInteger(name="test_var", help=None, type="integer"))
    instance = _test_instance_with_variables({"test_var": 6})
    validate_secrets_and_variables(instance, template)

    instance = _test_instance_with_variables({"test_var": False})
    e = assert_validation_throws(instance, template)
    assert isinstance(e, RequestParameterInvalidException)

    instance = _test_instance_with_variables({"test_var": "six"})
    e = assert_validation_throws(instance, template)
    assert isinstance(e, RequestParameterInvalidException)


def test_variable_typing_path_component():
    template = _template_with_variable(TemplateVariablePathComponent(name="test_var", help=None, type="path_component"))
    instance = _test_instance_with_variables({"test_var": "simple_directory"})
    validate_secrets_and_variables(instance, template)

    instance = _test_instance_with_variables({"test_var": 0})
    e = assert_validation_throws(instance, template)
    assert isinstance(e, RequestParameterInvalidException)

    instance = _test_instance_with_variables({"test_var": False})
    e = assert_validation_throws(instance, template)
    assert isinstance(e, RequestParameterInvalidException)

    instance = _test_instance_with_variables({"test_var": "../simple_directory"})
    e = assert_validation_throws(instance, template)
    assert isinstance(e, RequestParameterInvalidException)

    instance = _test_instance_with_variables({"test_var": "/simple_directory"})
    e = assert_validation_throws(instance, template)
    assert isinstance(e, RequestParameterInvalidException)

    instance = _test_instance_with_variables({"test_var": "simple_directory", "extra": "4"})
    e = assert_validation_throws(instance, template)
    assert isinstance(e, RequestParameterInvalidException)


def test_variable_missing():
    template = _template_with_variable(TemplateVariablePathComponent(name="test_var", help=None, type="path_component"))
    instance = _test_instance_with_variables({})
    e = assert_validation_throws(instance, template)
    assert isinstance(e, RequestParameterMissingException)


def test_secret_missing():
    template = _template_with_secret("mysecret")
    instance = _test_instance_with_secrets({})
    e = assert_validation_throws(instance, template)
    assert isinstance(e, RequestParameterMissingException)


def test_extra_secret():
    template = _template_with_secret("mysecret")
    instance = _test_instance_with_secrets({"mysecret": "myvalue"})
    validate_secrets_and_variables(instance, template)

    instance = _test_instance_with_secrets({"mysecret": "myvalue", "extrasecret": "extravalue"})
    e = assert_validation_throws(instance, template)
    assert isinstance(e, RequestParameterInvalidException)


def assert_validation_throws(instance: TestInstanceDefinition, template: TestTemplate) -> Exception:
    try:
        validate_secrets_and_variables(instance, template)
    except Exception as e:
        return e
    raise AssertionError("Expected validation error did not occur.")
