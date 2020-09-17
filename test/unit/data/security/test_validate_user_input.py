from galaxy.security.validate_user_input import extract_domain


def test_extract_full_domain():
    assert extract_domain('jack@foo.com') == 'foo.com'
    assert extract_domain('jack@foo.bar.com') == 'foo.bar.com'


def test_extract_base_domain():
    # Use case: ignore subdomains to filter out disposable email addresses
    assert extract_domain('jack@foo.com', base_only=True) == 'foo.com'
    assert extract_domain('jack@foo.bar.com', base_only=True) == 'bar.com'
