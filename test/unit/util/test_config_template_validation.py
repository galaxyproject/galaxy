from typing import (
    Any,
    Dict,
    List,
    Optional,
)

import pytest

from galaxy.exceptions import (
    RequestParameterInvalidException,
    RequestParameterMissingException,
)
from galaxy.tool_util_models.parameter_validators import (
    InRangeParameterValidatorModel,
    LengthParameterValidatorModel,
    RegexParameterValidatorModel,
)
from galaxy.util.config_templates import (
    split_ftp_host_path,
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


def test_variable_typing_multiline_string():
    template = _template_with_variable(
        TemplateVariableString(name="test_var", help=None, type="string", multiline=True)
    )
    instance = _test_instance_with_variables({"test_var": "line1\nline2"})
    validate_secrets_and_variables(instance, template)


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
        RegexParameterValidatorModel(
            expression=r"^.*[^/]$",
            message="Value cannot end with a trailing slash",
        ),
        RegexParameterValidatorModel(
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
    validator = RegexParameterValidatorModel(
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
    validator = LengthParameterValidatorModel(
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
    validator = LengthParameterValidatorModel(
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


# --- split_ftp_host_path tests ---


@pytest.mark.parametrize(
    "data, expected_host, expected_root",
    [
        # Plain host, no path
        ({"host": "ftp.gnu.org"}, "ftp.gnu.org", None),
        # Host with path
        ({"host": "ftp.gnu.org/gnu/"}, "ftp.gnu.org", "/gnu/"),
        ({"host": "ftp.ensemblgenomes.org/pub/version/"}, "ftp.ensemblgenomes.org", "/pub/version/"),
        # Protocol prefix
        ({"host": "ftp://ftp.gnu.org/gnu/"}, "ftp.gnu.org", "/gnu/"),
        ({"host": "ftps://ftp.gnu.org/gnu/"}, "ftp.gnu.org", "/gnu/"),
        ({"host": "ftp://ftp.gnu.org"}, "ftp.gnu.org", None),
        # Trailing slash only
        ({"host": "ftp.gnu.org/"}, "ftp.gnu.org", "/"),
        # Host with port and path
        ({"host": "ftp.gnu.org:2121/gnu/"}, "ftp.gnu.org:2121", "/gnu/"),
        # No host
        ({"port": 21}, None, None),
    ],
)
def test_split_ftp_host_path(data, expected_host, expected_root):
    result = split_ftp_host_path(data)
    if expected_host is None:
        assert "host" not in result or result.get("host") == data.get("host")
    else:
        assert result["host"] == expected_host
    if expected_root is None:
        assert "root" not in result
    else:
        assert result["root"] == expected_root


@pytest.mark.parametrize(
    "root_value",
    ["/custom", ""],
)
def test_split_ftp_host_path_explicit_root_not_overridden(root_value):
    result = split_ftp_host_path({"host": "ftp.gnu.org/gnu/", "root": root_value})
    assert result["host"] == "ftp.gnu.org/gnu/"
    assert result["root"] == root_value


def test_split_ftp_host_path_preserves_other_keys():
    result = split_ftp_host_path({"host": "ftp.gnu.org/gnu/", "user": "anon", "port": 21})
    assert result["host"] == "ftp.gnu.org"
    assert result["root"] == "/gnu/"
    assert result["user"] == "anon"
    assert result["port"] == 21


@pytest.mark.parametrize("non_dict", [None, "ftp://ftp.gnu.org", 42, []])
def test_split_ftp_host_path_non_dict_input(non_dict):
    assert split_ftp_host_path(non_dict) == non_dict


def test_split_ftp_host_path_does_not_mutate_input():
    original = {"host": "ftp.gnu.org/gnu/"}
    split_ftp_host_path(original)
    assert original == {"host": "ftp.gnu.org/gnu/"}


@pytest.mark.parametrize(
    "root",
    ["../etc", "/gnu/../etc", "/..", "foo/../bar", "/gnu/../../etc"],
)
def test_split_ftp_host_path_rejects_traversal_in_explicit_root(root):
    with pytest.raises(ValueError, match="must not contain '\\.\\.'"):
        split_ftp_host_path({"host": "ftp.gnu.org", "root": root})


def test_split_ftp_host_path_rejects_traversal_in_host_derived_root():
    with pytest.raises(ValueError, match="must not contain '\\.\\.'"):
        split_ftp_host_path({"host": "ftp.gnu.org/../etc"})


def test_length_validator_max_only():
    """Test length validation with only maximum."""
    validator = LengthParameterValidatorModel(
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
    validator = InRangeParameterValidatorModel(
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


def test_variable_default_does_not_imply_optional():
    """A default value (including empty string) must not make a variable optional."""
    template = _template_with_variable(TemplateVariableString(name="string_var", help=None, type="string", default=""))

    # Default alone does not make the variable optional
    instance = _test_instance_with_variables({})
    e = assert_validation_throws(instance, template)
    assert isinstance(e, RequestParameterMissingException)


def test_variable_optional_flag_allows_omission_without_default():
    """optional=True alone allows a variable to be omitted even without a default."""
    template = _template_with_variable(
        TemplateVariableString(name="optional_var", help=None, type="string", optional=True)
    )

    # Should not require the variable when optional=True
    instance = _test_instance_with_variables({})
    validate_secrets_and_variables(instance, template)

    # Should pass when variable is provided
    instance = _test_instance_with_variables({"optional_var": "some_value"})
    validate_secrets_and_variables(instance, template)


def test_secret_optional_flag_allows_omission_without_default():
    """optional=True alone allows a secret to be omitted even without a default."""
    secret = TemplateSecret(name="optional_secret", help="Help for secret.", optional=True)
    template = TestTemplate(
        id=TEST_TEMPLATE_ID,
        version=TEST_TEMPLATE_VERSION,
        variables=[],
        secrets=[secret],
        environment=None,
    )

    # Should not require the secret when optional=True
    instance = _test_instance_with_secrets({})
    validate_secrets_and_variables(instance, template)

    # Should pass when secret is provided
    instance = _test_instance_with_secrets({"optional_secret": "myvalue"})
    validate_secrets_and_variables(instance, template)


def test_optional_variable_validators_run_only_when_value_is_provided():
    """Optional variables are not required, but validators run when a value is supplied."""
    validator = LengthParameterValidatorModel(
        min=3,
        message="Value must be at least 3 characters",
    )
    template = _template_with_variable(
        TemplateVariableString(name="optional_var", help=None, type="string", optional=True, validators=[validator])
    )

    # Should not require the variable when optional=True
    instance = _test_instance_with_variables({})
    validate_secrets_and_variables(instance, template)

    # Should run validator when value is provided but invalid
    instance = _test_instance_with_variables({"optional_var": "ab"})  # Too short
    e = assert_validation_throws(instance, template)
    assert isinstance(e, RequestParameterInvalidException)
    assert "at least 3 characters" in str(e)

    # Should pass with valid value
    instance = _test_instance_with_variables({"optional_var": "valid"})
    validate_secrets_and_variables(instance, template)

    # Defaults for optional fields are validated when they are applied
    # Invalid default should fail validation
    template_with_bad_default = _template_with_variable(
        TemplateVariableString(
            name="optional_var",
            help=None,
            type="string",
            optional=True,
            default="ab",  # too short
            validators=[validator],
        )
    )
    instance = _test_instance_with_variables({})
    e = assert_validation_throws(instance, template_with_bad_default)
    assert isinstance(e, RequestParameterInvalidException)

    # Valid default should pass validation
    template_with_good_default = _template_with_variable(
        TemplateVariableString(
            name="optional_var",
            help=None,
            type="string",
            optional=True,
            default="good",
            validators=[validator],
        )
    )
    instance = _test_instance_with_variables({})
    validate_secrets_and_variables(instance, template_with_good_default)


def test_variable_optional_with_valid_default():
    """Test that optional variables with valid defaults work correctly."""
    # Optional string variable with default
    template = _template_with_variable(
        TemplateVariableString(name="optional_string", help=None, type="string", optional=True, default="default_value")
    )
    # Should use default when not provided
    instance = _test_instance_with_variables({})
    validate_secrets_and_variables(instance, template)

    # Should accept override
    instance = _test_instance_with_variables({"optional_string": "override"})
    validate_secrets_and_variables(instance, template)

    # Optional integer variable with default
    template = _template_with_variable(
        TemplateVariableInteger(name="optional_int", help=None, type="integer", optional=True, default=100)
    )
    instance = _test_instance_with_variables({})
    validate_secrets_and_variables(instance, template)

    # Optional boolean variable with default
    template = _template_with_variable(
        TemplateVariableBoolean(name="optional_bool", help=None, type="boolean", optional=True, default=False)
    )
    instance = _test_instance_with_variables({})
    validate_secrets_and_variables(instance, template)
