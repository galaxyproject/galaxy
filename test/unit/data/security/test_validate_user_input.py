from galaxy.security.validate_user_input import (
    extract_domain,
    validate_email_str,
    validate_publicname_str,
)


def test_extract_full_domain():
    assert extract_domain("jack@foo.com") == "foo.com"
    assert extract_domain("jack@foo.bar.com") == "foo.bar.com"


def test_extract_base_domain():
    # Use case: ignore subdomains to filter out disposable email addresses
    assert extract_domain("jack@foo.com", base_only=True) == "foo.com"
    assert extract_domain("jack@foo.bar.com", base_only=True) == "bar.com"


def test_validate_username():
    assert validate_publicname_str("testuser") == ""
    assert validate_publicname_str("test.user") == ""
    assert validate_publicname_str("test-user") == ""
    assert validate_publicname_str("test@user") != ""
    assert validate_publicname_str("test user") != ""


def test_validate_email():
    assert validate_email_str("test@foo.com") == ""
    assert validate_email_str("test-dot.user@foo.com") == ""
    assert validate_email_str("test@com") != ""
    assert validate_email_str("@not-a-domain") != ""
    too_long_email = "N" * 255 + "@foo.com"
    assert validate_email_str(too_long_email) != ""
