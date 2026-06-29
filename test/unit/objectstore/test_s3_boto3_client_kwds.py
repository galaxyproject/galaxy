"""Wiring tests for the boto3 object store's botocore client kwargs.

These exercise the seam that connects resolved checksum settings to the actual
botocore ``Config`` passed to ``boto3.client`` -- without any network access or
mocking -- by constructing a bare store instance and setting only the attributes
``_client_kwds`` reads.
"""

import pytest

pytest.importorskip("boto3")

from galaxy.objectstore.s3_boto3 import S3ObjectStore


def _store(endpoint_url=None, request=None, response=None, region=None):
    store = object.__new__(S3ObjectStore)
    store.endpoint_url = endpoint_url
    store.region = region
    store.access_key = "key"
    store.secret_key = "secret"
    store.request_checksum_calculation = request
    store.response_checksum_validation = response
    return store


def test_non_aws_endpoint_defaults_request_checksum_to_when_required():
    kwds = _store(endpoint_url="https://storage.googleapis.com/")._client_kwds()
    assert "config" in kwds
    assert kwds["config"].request_checksum_calculation == "when_required"
    assert kwds["endpoint_url"] == "https://storage.googleapis.com/"


def test_aws_endpoint_adds_no_config_override():
    # No endpoint at all -> AWS -> botocore default preserved (no config key).
    assert "config" not in _store(endpoint_url=None)._client_kwds()
    # Explicit amazonaws.com endpoint is also AWS.
    assert "config" not in _store(endpoint_url="https://s3.us-east-1.amazonaws.com")._client_kwds()


def test_explicit_value_wins_even_on_aws():
    kwds = _store(endpoint_url=None, request="when_supported")._client_kwds()
    assert kwds["config"].request_checksum_calculation == "when_supported"


def test_response_validation_passed_through_when_set():
    kwds = _store(endpoint_url="https://s3.amazonaws.com", response="when_required")._client_kwds()
    assert kwds["config"].response_checksum_validation == "when_required"
