from urllib.parse import quote
from xml.etree import ElementTree

import pytest

boto3 = pytest.importorskip("boto3")
from botocore.stub import Stubber
from werkzeug.wrappers import Response

from galaxy.objectstore.s3_boto3 import S3ObjectStore

PREFIX = "000/dataset_1_files/"


@pytest.fixture
def store_factory(monkeypatch):
    monkeypatch.setattr(S3ObjectStore, "_single_delete_endpoints", set())
    stores = []

    def create_store(endpoint_url=None, bucket="test-bucket"):
        store = object.__new__(S3ObjectStore)
        store.bucket = bucket
        store._client = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="test",
            aws_secret_access_key="test",
            endpoint_url=endpoint_url,
        )
        stores.append(store)
        return store

    yield create_store
    for store in stores:
        store._client.close()


@pytest.fixture
def store(store_factory):
    return store_factory()


def _list_params(store, continuation_token=None):
    params = {"Bucket": store.bucket, "Prefix": PREFIX, "StartAfter": PREFIX}
    if continuation_token:
        params["ContinuationToken"] = continuation_token
    return params


def _delete_params(store, keys):
    return {"Bucket": store.bucket, "Delete": {"Objects": [{"Key": key} for key in keys], "Quiet": True}}


@pytest.mark.parametrize("key_count", [0, 1, 1000, 1001, 2501])
def test_delete_remote_all_batches_paginated_keys(store, key_count):
    keys = [f"{PREFIX}subdir/file_{i}" for i in range(key_count)]
    with Stubber(store._client) as stubber:
        for offset in range(0, max(key_count, 1), 1000):
            page_keys = keys[offset : offset + 1000]
            response = {"IsTruncated": offset + 1000 < key_count}
            if page_keys:
                response["Contents"] = [{"Key": key} for key in page_keys]
            if response["IsTruncated"]:
                response["NextContinuationToken"] = str(offset + 1000)
            stubber.add_response("list_objects_v2", response, _list_params(store, str(offset) if offset else None))
            if page_keys:
                stubber.add_response("delete_objects", {}, _delete_params(store, page_keys))

        assert store._delete_remote_all(PREFIX) is True
        stubber.assert_no_pending_responses()


def test_delete_remote_all_batches_across_short_pages(store):
    keys = [f"{PREFIX}file_{i}" for i in range(1001)]
    with Stubber(store._client) as stubber:
        stubber.add_response(
            "list_objects_v2",
            {
                "Contents": [{"Key": key} for key in keys[:600]],
                "IsTruncated": True,
                "NextContinuationToken": "next",
            },
            _list_params(store),
        )
        stubber.add_response(
            "list_objects_v2",
            {"Contents": [{"Key": key} for key in keys[600:]], "IsTruncated": False},
            _list_params(store, "next"),
        )
        stubber.add_response("delete_objects", {}, _delete_params(store, keys[:1000]))
        stubber.add_response("delete_objects", {}, _delete_params(store, keys[1000:]))

        assert store._delete_remote_all(PREFIX) is True
        stubber.assert_no_pending_responses()


def test_delete_remote_all_reports_partial_failures_and_continues(store, caplog):
    keys = [f"{PREFIX}file_{i}" for i in range(1001)]
    errors = [
        {"Key": keys[0], "Code": "AccessDenied", "Message": "Access Denied"},
        {"Key": keys[1], "Code": "InternalError", "Message": "Please try again"},
    ]
    with Stubber(store._client) as stubber:
        stubber.add_response(
            "list_objects_v2",
            {
                "Contents": [{"Key": key} for key in keys[:1000]],
                "IsTruncated": True,
                "NextContinuationToken": "next",
            },
            _list_params(store),
        )
        stubber.add_response("delete_objects", {"Errors": errors}, _delete_params(store, keys[:1000]))
        stubber.add_response(
            "list_objects_v2",
            {"Contents": [{"Key": keys[-1]}], "IsTruncated": False},
            _list_params(store, "next"),
        )
        stubber.add_response("delete_objects", {}, _delete_params(store, keys[1000:]))

        assert store._delete_remote_all(PREFIX) is False
        stubber.assert_no_pending_responses()

    for error in errors:
        assert error["Key"] in caplog.text
        assert error["Code"] in caplog.text
        assert error["Message"] in caplog.text
    assert store.bucket in caplog.text


@pytest.mark.parametrize("operation", ["list_objects_v2", "delete_objects"])
@pytest.mark.parametrize("error_code", ["AccessDenied", "InternalError", "InvalidRequest", "InvalidDigest"])
def test_delete_remote_all_reports_request_failures(store, caplog, operation, error_code):
    keys = [f"{PREFIX}file"]
    with Stubber(store._client) as stubber:
        if operation == "delete_objects":
            stubber.add_response(
                "list_objects_v2", {"Contents": [{"Key": keys[0]}], "IsTruncated": False}, _list_params(store)
            )
        stubber.add_client_error(
            operation,
            service_error_code=error_code,
            service_message="Request failed",
            http_status_code=403,
            expected_params=_list_params(store) if operation == "list_objects_v2" else _delete_params(store, keys),
        )

        assert store._delete_remote_all(PREFIX) is False
        stubber.assert_no_pending_responses()

    assert PREFIX in caplog.text
    assert error_code in caplog.text


@pytest.mark.parametrize("error_code", ["MissingContentMD5", "NotImplemented"])
def test_delete_remote_all_remembers_batch_fallback(store, caplog, error_code):
    keys = [f"{PREFIX}file_{i}" for i in range(1001)]
    with Stubber(store._client) as stubber:
        stubber.add_response(
            "list_objects_v2",
            {
                "Contents": [{"Key": key} for key in keys[:1000]],
                "IsTruncated": True,
                "NextContinuationToken": "next",
            },
            _list_params(store),
        )
        stubber.add_client_error(
            "delete_objects", service_error_code=error_code, expected_params=_delete_params(store, keys[:1000])
        )
        for key in keys[:1000]:
            stubber.add_response("delete_object", {}, {"Bucket": store.bucket, "Key": key})
        stubber.add_response(
            "list_objects_v2",
            {"Contents": [{"Key": keys[-1]}], "IsTruncated": False},
            _list_params(store, "next"),
        )
        stubber.add_response("delete_object", {}, {"Bucket": store.bucket, "Key": keys[-1]})

        assert store._delete_remote_all(PREFIX) is True
        stubber.assert_no_pending_responses()

        # Later cleanups on the same store should not retry the unsupported batch API.
        key = f"{PREFIX}new_file"
        stubber.add_response("list_objects_v2", {"Contents": [{"Key": key}], "IsTruncated": False}, _list_params(store))
        stubber.add_response("delete_object", {}, {"Bucket": store.bucket, "Key": key})
        assert store._delete_remote_all(PREFIX) is True
        stubber.assert_no_pending_responses()

    assert error_code in caplog.text
    assert "falling back" in caplog.text


def test_delete_remote_all_fallback_reports_failure_and_continues(store, caplog):
    keys = [f"{PREFIX}file_{i}" for i in range(3)]
    with Stubber(store._client) as stubber:
        stubber.add_response(
            "list_objects_v2", {"Contents": [{"Key": key} for key in keys], "IsTruncated": False}, _list_params(store)
        )
        stubber.add_client_error(
            "delete_objects", service_error_code="MissingContentMD5", expected_params=_delete_params(store, keys)
        )
        stubber.add_response("delete_object", {}, {"Bucket": store.bucket, "Key": keys[0]})
        stubber.add_client_error(
            "delete_object", service_error_code="AccessDenied", expected_params={"Bucket": store.bucket, "Key": keys[1]}
        )
        stubber.add_response("delete_object", {}, {"Bucket": store.bucket, "Key": keys[2]})

        assert store._delete_remote_all(PREFIX) is False
        stubber.assert_no_pending_responses()

    assert keys[1] in caplog.text
    assert "AccessDenied" in caplog.text


@pytest.mark.parametrize("error_code", ["MissingContentMD5", "NotImplemented"])
def test_delete_remote_all_shares_fallback_only_with_same_endpoint(store_factory, error_code):
    endpoint = "https://s3.example.org"
    first = store_factory(endpoint_url=endpoint)
    existing = store_factory(endpoint_url=endpoint, bucket="another-bucket")
    key = f"{PREFIX}file"
    listing = {"Contents": [{"Key": key}], "IsTruncated": False}

    with Stubber(first._client) as stubber:
        stubber.add_response("list_objects_v2", listing, _list_params(first))
        stubber.add_client_error(
            "delete_objects", service_error_code=error_code, expected_params=_delete_params(first, [key])
        )
        stubber.add_response("delete_object", {}, {"Bucket": first.bucket, "Key": key})
        assert first._delete_remote_all(PREFIX) is True
        stubber.assert_no_pending_responses()

    # Both existing and newly constructed stores reuse the endpoint's fallback.
    new = store_factory(endpoint_url=f"{endpoint}/")
    for store in (existing, new):
        with Stubber(store._client) as stubber:
            stubber.add_response("list_objects_v2", listing, _list_params(store))
            stubber.add_response("delete_object", {}, {"Bucket": store.bucket, "Key": key})
            assert store._delete_remote_all(PREFIX) is True
            stubber.assert_no_pending_responses()

    other = store_factory(endpoint_url="https://other.example.org")
    with Stubber(other._client) as stubber:
        stubber.add_response("list_objects_v2", listing, _list_params(other))
        stubber.add_response("delete_objects", {}, _delete_params(other, [key]))
        assert other._delete_remote_all(PREFIX) is True
        stubber.assert_no_pending_responses()


def test_delete_remote_all_falls_back_from_http_checksum_error(store, httpserver):
    store._client.close()
    store.endpoint_url = httpserver.url_for("/")
    store.region = "us-east-1"
    store.access_key = "test"
    store.secret_key = "test"
    store._init_client()

    key = f"{PREFIX}file"
    httpserver.expect_ordered_request(f"/{store.bucket}", method="GET").respond_with_data(
        f'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        f"<IsTruncated>false</IsTruncated><Contents><Key>{key}</Key></Contents></ListBucketResult>",
        content_type="application/xml",
    )
    httpserver.expect_ordered_request(f"/{store.bucket}", method="POST", query_string="delete").respond_with_data(
        "<Error><Code>MissingContentMD5</Code><Message>Missing required Content-MD5 header</Message></Error>",
        status=400,
        content_type="application/xml",
    )
    httpserver.expect_ordered_request(f"/{store.bucket}/{key}", method="DELETE").respond_with_data("", status=204)

    success = store._delete_remote_all(PREFIX)
    httpserver.check_assertions()
    assert not httpserver.ordered_handlers
    assert success is True


@pytest.mark.parametrize("character", ["\x01", "\x0b", "\r", "\ufffe"])
@pytest.mark.parametrize("include_normal_key", [True, False])
def test_delete_remote_all_preserves_xml_unsafe_keys(store, httpserver, character, include_normal_key):
    store._client.close()
    store.endpoint_url = httpserver.url_for("/")
    store.region = "us-east-1"
    store.access_key = "test"
    store.secret_key = "test"
    store._init_client()

    unsafe_key = f"{PREFIX}unsafe{character}file"
    normal_key = f"{PREFIX}normal<&>\t\né😀"
    remaining = {unsafe_key, normal_key} if include_normal_key else {unsafe_key}
    batch_requests = []
    individual_deletes = []

    def list_objects(request):
        contents = "".join(f"<Contents><Key>{quote(key, safe='')}</Key></Contents>" for key in sorted(remaining))
        return Response(
            '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
            f"<EncodingType>url</EncodingType><IsTruncated>false</IsTruncated>{contents}</ListBucketResult>",
            content_type="application/xml",
        )

    def delete_objects(request):
        try:
            root = ElementTree.fromstring(request.data)
        except ElementTree.ParseError:
            return Response("<Error><Code>MalformedXML</Code></Error>", status=400, content_type="application/xml")
        keys = [element.text for element in root.findall("{*}Object/{*}Key")]
        batch_requests.append(keys)
        remaining.difference_update(keys)
        return Response(
            '<DeleteResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/"/>', content_type="application/xml"
        )

    def delete_object(request):
        key = request.path.removeprefix(f"/{store.bucket}/")
        individual_deletes.append(key)
        remaining.discard(key)
        return Response(status=204)

    httpserver.expect_request(f"/{store.bucket}", method="GET").respond_with_handler(list_objects)
    httpserver.expect_request(f"/{store.bucket}", method="POST", query_string="delete").respond_with_handler(
        delete_objects
    )
    httpserver.expect_request(f"/{store.bucket}/{unsafe_key}", method="DELETE").respond_with_handler(delete_object)

    success = store._delete_remote_all(PREFIX)
    httpserver.check_assertions()
    assert success is True
    assert not remaining
    assert individual_deletes == [unsafe_key]
    assert batch_requests == ([[normal_key]] if include_normal_key else [])

    # A key-specific restriction must not disable batching for subsequent cleanups.
    remaining.add(normal_key)
    assert store._delete_remote_all(PREFIX) is True
    httpserver.check_assertions()
    assert not remaining
    assert batch_requests[-1] == [normal_key]
    assert len(batch_requests) == (2 if include_normal_key else 1)


@pytest.mark.parametrize("individual_delete_fails", [True, False])
def test_delete_remote_all_mixed_keys_continue_across_pages(store, caplog, individual_delete_fails):
    keys = [f"{PREFIX}file_{i}" for i in range(1002)]
    keys[0] += "\x01"
    keys[1000] += "\r"
    with Stubber(store._client) as stubber:
        stubber.add_response(
            "list_objects_v2",
            {
                "Contents": [{"Key": key} for key in keys[:1000]],
                "IsTruncated": True,
                "NextContinuationToken": "next",
            },
            _list_params(store),
        )
        params = {"Bucket": store.bucket, "Key": keys[0]}
        if individual_delete_fails:
            stubber.add_client_error("delete_object", service_error_code="AccessDenied", expected_params=params)
        else:
            stubber.add_response("delete_object", {}, params)
        stubber.add_response("delete_objects", {}, _delete_params(store, keys[1:1000]))
        stubber.add_response(
            "list_objects_v2",
            {"Contents": [{"Key": key} for key in keys[1000:]], "IsTruncated": False},
            _list_params(store, "next"),
        )
        stubber.add_response("delete_object", {}, {"Bucket": store.bucket, "Key": keys[1000]})
        stubber.add_response("delete_objects", {}, _delete_params(store, keys[1001:]))

        assert store._delete_remote_all(PREFIX) is (not individual_delete_fails)
        stubber.assert_no_pending_responses()

    if individual_delete_fails:
        assert keys[0] in caplog.text
        assert "AccessDenied" in caplog.text
