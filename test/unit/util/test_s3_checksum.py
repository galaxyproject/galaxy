from galaxy.util.s3_checksum import (
    is_aws_s3_endpoint,
    s3_checksum_config_kwargs,
)


def test_is_aws_s3_endpoint_treats_empty_as_aws():
    assert is_aws_s3_endpoint(None) is True
    assert is_aws_s3_endpoint("") is True


def test_is_aws_s3_endpoint_matches_amazonaws_hosts():
    assert is_aws_s3_endpoint("https://s3.amazonaws.com") is True
    assert is_aws_s3_endpoint("https://s3.us-east-1.amazonaws.com") is True
    # case-insensitive host comparison
    assert is_aws_s3_endpoint("https://S3.AMAZONAWS.COM") is True


def test_is_aws_s3_endpoint_rejects_lookalike_and_third_party():
    assert is_aws_s3_endpoint("https://storage.googleapis.com/") is False
    assert is_aws_s3_endpoint("https://play.min.io:9000") is False
    assert is_aws_s3_endpoint("https://s3.example.org") is False
    # a host that merely contains the string is not under amazonaws.com
    assert is_aws_s3_endpoint("https://amazonaws.com.evil.example") is False


def test_default_when_required_for_non_aws_endpoint():
    kwargs = s3_checksum_config_kwargs("https://storage.googleapis.com/")
    assert kwargs == {"request_checksum_calculation": "when_required"}


def test_no_override_for_aws_endpoint():
    # Empty/None endpoint and amazonaws.com hosts keep botocore's default.
    assert s3_checksum_config_kwargs(None) == {}
    assert s3_checksum_config_kwargs("https://s3.us-east-1.amazonaws.com") == {}
