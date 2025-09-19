import pytest

from galaxy import config
from galaxy.security import validate_user_input
from galaxy.security.validate_user_input import (
    extract_domain,
    is_email_banned,
    validate_email_domain_name,
    validate_email_str,
    validate_publicname_str,
)


@pytest.fixture()
def appconfig():
    return config.GalaxyAppConfiguration(override_tempdir=False)


def test_extract_full_domain():
    assert extract_domain("jack@foo.com") == "foo.com"
    assert extract_domain("jack@foo.bar.com") == "foo.bar.com"
    assert extract_domain("foo.bar.com") == "foo.bar.com"
    assert extract_domain('"i-like-to-break-email-valid@tors"@foo.com') == "foo.com"


def test_extract_base_domain():
    # Use case: ignore subdomains to filter out disposable email addresses
    assert extract_domain("jack@foo.com", base_only=True) == "foo.com"
    assert extract_domain("jack@foo.bar.com", base_only=True) == "bar.com"


def test_validate_email_domain_name():
    assert validate_email_domain_name("example.org") == ""
    assert validate_email_domain_name("this is an invalid domain!") != ""


def test_validate_username():
    assert validate_publicname_str("testuser") == ""
    assert validate_publicname_str("test.user") == ""
    assert validate_publicname_str("test-user") == ""
    assert validate_publicname_str("test@user") != ""
    assert validate_publicname_str("test user") != ""


def test_validate_email_str():
    assert validate_email_str("test@foo.com") == ""
    assert validate_email_str("test-dot.user@foo.com") == ""
    assert validate_email_str("test-plus+user@foo.com") == ""
    assert validate_email_str("test-ünicode-user@foo.com") == ""
    assert validate_email_str("test@ünicode-domain.com") == ""
    assert validate_email_str("test-missing-domain@") != ""
    assert validate_email_str("@test-missing-local") != ""
    assert validate_email_str("test-invalid-local\\character@foo.com") != ""
    assert validate_email_str("test@invalid-domain-character!com") != ""
    assert validate_email_str("test@newlines.in.address.are.invalid\n\n.com") != ""
    assert validate_email_str('"i-like-to-break-email-valid@tors"@foo.com') != ""
    too_long_email = "N" * 255 + "@foo.com"
    assert validate_email_str(too_long_email) != ""


class TestIsEmailBanned:

    mock_ban_list = ["ab@foo.com", "ab@gmail.com", "Not.Canonical+email+gmail+address@gmail.com"]

    def test_default_canonical_rules(self, monkeypatch, appconfig):
        """Rules loaded from schema."""
        monkeypatch.setattr(validate_user_input, "_read_email_ban_list", lambda a: self.mock_ban_list)

        rules = appconfig.canonical_email_rules
        assert is_email_banned("ab@foo.com", "_", rules)
        assert not is_email_banned("Ab@foo.com", "_", rules)
        assert not is_email_banned("a.b@foo.com", "_", rules)
        assert not is_email_banned("ab+bar@foo.com", "_", rules)
        assert not is_email_banned("something-else@foo.com", "_", rules)

        # default rules for gmail are applied:
        assert is_email_banned("ab@googlemail.com", "_", rules)
        assert is_email_banned("Ab@gmail.com", "_", rules)
        assert is_email_banned("a.b@gmail.com", "_", rules)
        assert is_email_banned("ab+bar@gmail.com", "_", rules)
        assert not is_email_banned("ab-bar@gmail.com", "_", rules)  # different sub-addressing delimiter

    def test_no_canonical_rules(self, monkeypatch, appconfig):
        """No rules loaded."""
        monkeypatch.setattr(validate_user_input, "_read_email_ban_list", lambda a: self.mock_ban_list)

        rules = None
        assert is_email_banned("ab@foo.com", "_", rules)
        assert not is_email_banned("Ab@foo.com", "_", rules)
        assert not is_email_banned("a.b@foo.com", "_", rules)
        assert not is_email_banned("ab+bar@foo.com", "_", rules)
        assert not is_email_banned("something-else@foo.com", "_", rules)

        # default rules for gmail are NOT applied:
        assert not is_email_banned("ab@googlemail.com", "_", rules)
        assert not is_email_banned("Ab@gmail.com", "_", rules)
        assert not is_email_banned("a.b@gmail.com", "_", rules)
        assert not is_email_banned("ab+bar@gmail.com", "_", rules)

    def test_custom_canonical_rules(self, monkeypatch, appconfig):
        """No rules loaded."""
        monkeypatch.setattr(validate_user_input, "_read_email_ban_list", lambda a: self.mock_ban_list)

        rules = {"all": {"ignore_case": True}, "foo.com": {"ignore_dots": True}}
        assert is_email_banned("ab@foo.com", "_", rules)
        assert is_email_banned("Ab@foo.com", "_", rules)  # ignore_case for all
        assert is_email_banned("a.b@foo.com", "_", rules)  # ignore_dots for foo.com
        assert not is_email_banned("ab+bar@foo.com", "_", rules)
        assert not is_email_banned("something-else@foo.com", "_", rules)

        # default rules for gmail are NOT applied:
        assert not is_email_banned("ab@googlemail.com", "_", rules)
        assert is_email_banned("Ab@gmail.com", "_", rules)  # ignore_case for all
        assert not is_email_banned("a.b@gmail.com", "_", rules)
        assert not is_email_banned("ab+bar@gmail.com", "_", rules)
