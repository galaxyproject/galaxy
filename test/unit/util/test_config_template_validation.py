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
    TemplateVariableValidator,
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


def test_multiple_validators():
    """Test multiple validators on the same variable."""
    validators = [
        TemplateVariableValidator(
            type="regex",
            expression=r"^.*[^/]$",
            message="Value cannot end with a trailing slash",
        ),
        TemplateVariableValidator(
            type="regex",
            expression=r"^(?!\s)(?!.*\s$).*$",
            message="Value cannot have leading or trailing whitespace",
        ),
    ]
    template = _template_with_variable(
        TemplateVariableString(name="path", help=None, type="string", validators=validators)
    )

    # Valid path
    instance = _test_instance_with_variables({"path": "clean/path"})
    validate_secrets_and_variables(instance, template)

    # Invalid: trailing slash (first validator fails)
    instance = _test_instance_with_variables({"path": "path/"})
    e = assert_validation_throws(instance, template)
    assert isinstance(e, RequestParameterInvalidException)
    assert "trailing slash" in str(e)

    # Invalid: trailing whitespace (second validator fails)
    instance = _test_instance_with_variables({"path": "path "})
    e = assert_validation_throws(instance, template)
    assert isinstance(e, RequestParameterInvalidException)
    assert "whitespace" in str(e)


def test_regex_validator_negate():
    """Test regex validation with negate flag."""
    validator = TemplateVariableValidator(
        type="regex",
        expression=r"forbidden",
        message="Value cannot contain 'forbidden'",
        negate=True,
    )
    template = _template_with_variable(
        TemplateVariableString(name="username", help=None, type="string", validators=[validator])
    )

    # Valid: doesn't contain 'forbidden'
    instance = _test_instance_with_variables({"username": "john_doe"})
    validate_secrets_and_variables(instance, template)

    # Invalid: contains 'forbidden'
    instance = _test_instance_with_variables({"username": "forbidden_user"})
    e = assert_validation_throws(instance, template)
    assert isinstance(e, RequestParameterInvalidException)


def test_length_validator():
    """Test length validation."""
    validator = TemplateVariableValidator(
        type="length",
        min=3,
        max=10,
        message="Value must be between 3 and 10 characters",
    )
    template = _template_with_variable(
        TemplateVariableString(name="name", help=None, type="string", validators=[validator])
    )

    # Valid length
    instance = _test_instance_with_variables({"name": "test"})
    validate_secrets_and_variables(instance, template)

    instance = _test_instance_with_variables({"name": "a" * 10})
    validate_secrets_and_variables(instance, template)

    # Too short
    instance = _test_instance_with_variables({"name": "ab"})
    e = assert_validation_throws(instance, template)
    assert isinstance(e, RequestParameterInvalidException)

    # Too long
    instance = _test_instance_with_variables({"name": "a" * 11})
    e = assert_validation_throws(instance, template)
    assert isinstance(e, RequestParameterInvalidException)


def test_length_validator_min_only():
    """Test length validation with only minimum."""
    validator = TemplateVariableValidator(
        type="length",
        min=5,
        message="Value must be at least 5 characters",
    )
    template = _template_with_variable(
        TemplateVariableString(name="description", help=None, type="string", validators=[validator])
    )

    # Valid: meets minimum
    instance = _test_instance_with_variables({"description": "12345"})
    validate_secrets_and_variables(instance, template)

    instance = _test_instance_with_variables({"description": "a" * 100})
    validate_secrets_and_variables(instance, template)

    # Invalid: too short
    instance = _test_instance_with_variables({"description": "test"})
    e = assert_validation_throws(instance, template)
    assert isinstance(e, RequestParameterInvalidException)


def test_length_validator_max_only():
    """Test length validation with only maximum."""
    validator = TemplateVariableValidator(
        type="length",
        max=50,
        message="Value must be at most 50 characters",
    )
    template = _template_with_variable(
        TemplateVariableString(name="title", help=None, type="string", validators=[validator])
    )

    # Valid: under maximum
    instance = _test_instance_with_variables({"title": "Short title"})
    validate_secrets_and_variables(instance, template)

    instance = _test_instance_with_variables({"title": "a" * 50})
    validate_secrets_and_variables(instance, template)

    # Invalid: too long
    instance = _test_instance_with_variables({"title": "a" * 51})
    e = assert_validation_throws(instance, template)
    assert isinstance(e, RequestParameterInvalidException)


def test_range_validator():
    """Test range validation for numeric values."""
    validator = TemplateVariableValidator(
        type="range",
        min=1,
        max=100,
        message="Value must be between 1 and 100",
    )
    template = _template_with_variable(
        TemplateVariableInteger(name="port", help=None, type="integer", validators=[validator])
    )

    # Valid range
    instance = _test_instance_with_variables({"port": 80})
    validate_secrets_and_variables(instance, template)

    instance = _test_instance_with_variables({"port": 1})
    validate_secrets_and_variables(instance, template)

    instance = _test_instance_with_variables({"port": 100})
    validate_secrets_and_variables(instance, template)

    # Too small
    instance = _test_instance_with_variables({"port": 0})
    e = assert_validation_throws(instance, template)
    assert isinstance(e, RequestParameterInvalidException)

    # Too large
    instance = _test_instance_with_variables({"port": 101})
    e = assert_validation_throws(instance, template)
    assert isinstance(e, RequestParameterInvalidException)


def test_validators_skip_empty_optional_values():
    """Test that validators skip empty optional values."""
    validator = TemplateVariableValidator(
        type="length",
        min=3,
        message="Value must be at least 3 characters",
    )
    template = _template_with_variable(
        TemplateVariableString(name="optional_field", help=None, type="string", default="", validators=[validator])
    )

    # Empty value should not trigger validator
    instance = _test_instance_with_variables({"optional_field": ""})
    validate_secrets_and_variables(instance, template)


def test_validators_skip_null_values():
    """Test that validators skip empty values for optional fields with defaults."""
    validator = TemplateVariableValidator(
        type="length",
        min=3,
        message="Value must be at least 3 characters",
    )
    template = _template_with_variable(
        TemplateVariableString(name="optional_field", help=None, type="string", default="", validators=[validator])
    )

    # Empty value should not trigger validator when field has empty default
    instance = _test_instance_with_variables({})
    validate_secrets_and_variables(instance, template)


def test_invalid_regex_pattern():
    """Test that invalid regex patterns are handled gracefully."""
    validator = TemplateVariableValidator(
        type="regex",
        expression=r"[invalid(regex",  # Invalid regex
        message="Test message",
    )
    template = _template_with_variable(
        TemplateVariableString(name="test", help=None, type="string", validators=[validator])
    )

    instance = _test_instance_with_variables({"test": "value"})
    e = assert_validation_throws(instance, template)
    assert isinstance(e, RequestParameterInvalidException)
    assert "Invalid regex pattern" in str(e)
