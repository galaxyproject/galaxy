import io
import json
import os
import tempfile
from typing import Any
from unittest import mock

import pytest
import responses

from galaxy.exceptions import (
    ConfigDoesNotAllowException,
    RequestParameterInvalidException,
)
from galaxy.files import (
    DictFileSourcesUserContext,
    ProvidesFileSourcesUserContext,
)
from galaxy.files.models import RealizedSourceMetadata
from galaxy.files.sources.util import (
    CompactIdentifierResolver,
    fetch_drs_to_file,
    RetryOptions,
    sanitize_drs_name,
)
from ._util import (
    assert_realizes_as,
    assert_realizes_contains,
    configured_file_sources,
    patch_http_open,
    user_context_fixture,
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "drs_file_sources_conf.yml")
DRS_OIDC_FILE_SOURCES_CONF = os.path.join(SCRIPT_DIRECTORY, "drs_oidc_file_sources_conf.yml")


def test_provides_file_sources_user_context_oidc_access_tokens():
    """ProvidesFileSourcesUserContext.oidc_access_tokens reads all providers from social_auth."""

    class DummyToken:
        def __init__(self, provider, access_token):
            self.provider = provider
            self.extra_data = {"access_token": access_token}

    class DummyUser:
        social_auth = [
            DummyToken("oidc", "oidc-token"),
            DummyToken("keycloak", "keycloak-token"),
            DummyToken("no_token_provider", None),  # skipped — no access_token
        ]

    class DummyTrans:
        user = DummyUser()

    tokens = ProvidesFileSourcesUserContext(DummyTrans()).oidc_access_tokens
    assert tokens == {"oidc": "oidc-token", "keycloak": "keycloak-token"}


def test_provides_file_sources_user_context_oidc_access_tokens_anonymous():
    """ProvidesFileSourcesUserContext.oidc_access_tokens returns None for anonymous users."""

    class DummyTrans:
        user = None

    assert ProvidesFileSourcesUserContext(DummyTrans()).oidc_access_tokens is None


def test_drs_http_headers_template_expansion():
    """Dict values in http_headers are expanded as templates during file source serialization."""
    oidc_token = "my-token"
    file_sources = configured_file_sources(DRS_OIDC_FILE_SOURCES_CONF)
    user_context = DictFileSourcesUserContext(
        username="alice",
        email="alice@galaxyproject.org",
        preferences={},
        role_names=set(),
        group_names=set(),
        is_admin=False,
        oidc_access_tokens={"oidc": oidc_token},
    )
    file_sources_dict = file_sources.to_dict(for_serialization=True, user_context=user_context)
    drs_source = next(s for s in file_sources_dict["file_sources"] if s.get("type") == "drs")
    assert drs_source["http_headers"]["Authorization"] == f"Bearer {oidc_token}"


def test_drs_oidc_token_wrong_provider_raises():
    """Referencing a provider the user doesn't have raises KeyError at serialization time."""
    file_sources = configured_file_sources(DRS_OIDC_FILE_SOURCES_CONF)
    user_context = DictFileSourcesUserContext(
        username="alice",
        email="alice@galaxyproject.org",
        preferences={},
        role_names=set(),
        group_names=set(),
        is_admin=False,
        oidc_access_tokens={"keycloak": "kc-token"},
    )
    with pytest.raises(KeyError):
        file_sources.to_dict(for_serialization=True, user_context=user_context)


def test_drs_oidc_token_no_tokens_raises():
    """A user with no OIDC tokens raises TypeError at serialization time."""
    file_sources = configured_file_sources(DRS_OIDC_FILE_SOURCES_CONF)
    user_context = DictFileSourcesUserContext(
        username="alice",
        email="alice@galaxyproject.org",
        preferences={},
        role_names=set(),
        group_names=set(),
        is_admin=False,
    )
    with pytest.raises(TypeError):
        file_sources.to_dict(for_serialization=True, user_context=user_context)


@pytest.mark.usefixtures("fake_public_dns")
@responses.activate
def test_file_source_drs_http():
    def drs_repo_handler(request):
        assert request.headers["Authorization"] == "Bearer IBearTokens"
        data = {
            "id": "314159",
            "name": "hello-314159",
            "access_methods": [
                {
                    "type": "https",
                    "access_id": "1234",
                }
            ],
        }
        return (200, {}, json.dumps(data))

    def access_handler(request):
        assert request.headers["Authorization"] == "Bearer IBearTokens"
        access_data = {
            "url": "https://my.respository.org/myfile.txt",
            "headers": ["Authorization: Basic Z2E0Z2g6ZHJz"],
        }
        return (200, {}, json.dumps(access_data))

    responses.add_callback(
        responses.GET,
        "https://drs.example.org/ga4gh/drs/v1/objects/314159",
        callback=drs_repo_handler,
        content_type="application/json",
    )

    responses.add_callback(
        responses.GET,
        "https://drs.example.org/ga4gh/drs/v1/objects/314159/access/1234",
        callback=access_handler,
        content_type="application/json",
    )

    test_url = "drs://drs.example.org/314159"

    def check_specific_header(request, **kwargs):
        assert request.full_url == "https://my.respository.org/myfile.txt"
        assert request.headers["Authorization"] == "Basic Z2E0Z2g6ZHJz"
        response: Any = io.StringIO("hello drs world")
        response.headers = {}
        response.geturl = lambda: test_url
        return response

    with patch_http_open(check_specific_header):
        user_context = user_context_fixture()
        file_sources = configured_file_sources(FILE_SOURCES_CONF)
        file_source_pair = file_sources.get_file_source_path(test_url)

        assert file_source_pair.path == test_url
        assert file_source_pair.file_source.id == "test1"

        assert_realizes_as(file_sources, test_url, "hello drs world", user_context=user_context)

        # The DRS object's own name is reported back through metadata_out so callers can
        # name the dataset something better than the identifier in the URI.
        metadata_out: RealizedSourceMetadata = {}
        with tempfile.NamedTemporaryFile(mode="r") as temp:
            file_source_pair.file_source.realize_to(
                file_source_pair.path, temp.name, user_context=user_context, metadata_out=metadata_out
            )
        assert metadata_out["name"] == "hello-314159"


@pytest.mark.usefixtures("fake_public_dns")
@responses.activate
def test_file_source_drs_omits_unusable_name_from_metadata():
    """A DRS object with no usable name leaves metadata_out empty so callers keep their own fallback."""

    def drs_repo_handler(request):
        data = {
            "id": "271828",
            "access_methods": [{"type": "https", "access_url": {"url": "https://my.respository.org/myfile.txt"}}],
        }
        return (200, {}, json.dumps(data))

    responses.add_callback(
        responses.GET,
        "https://drs.example.org/ga4gh/drs/v1/objects/271828",
        callback=drs_repo_handler,
        content_type="application/json",
    )

    test_url = "drs://drs.example.org/271828"

    def download(request, **kwargs):
        response: Any = io.StringIO("hello drs world")
        response.headers = {}
        response.geturl = lambda: test_url
        return response

    with patch_http_open(download):
        user_context = user_context_fixture()
        file_sources = configured_file_sources(FILE_SOURCES_CONF)
        file_source_pair = file_sources.get_file_source_path(test_url)
        metadata_out: RealizedSourceMetadata = {}
        with tempfile.NamedTemporaryFile(mode="r") as temp:
            file_source_pair.file_source.realize_to(
                file_source_pair.path, temp.name, user_context=user_context, metadata_out=metadata_out
            )
        assert metadata_out == {}


@pytest.mark.parametrize(
    "raw_name, expected",
    [
        ("sample.bed", "sample.bed"),
        ("L1000_LINCS_DCIC_PBIOA020_HCC515_24H_G06.tsv.gz", "L1000_LINCS_DCIC_PBIOA020_HCC515_24H_G06.tsv.gz"),
        ("  padded.txt  ", "padded.txt"),
        ("ünïcödé.txt", "ünïcödé.txt"),
        ("../../../etc/passwd", "passwd"),
        ("/etc/passwd", "passwd"),
        ("..\\..\\windows\\system32\\cmd.exe", "cmd.exe"),
        ("sample\t\r\n.bed", "sample.bed"),
        ("sample\x00.bed", "sample.bed"),
        # Bidi overrides and zero-width characters are how a name gets to look like
        # something it isn't, so they go too.
        ("‮gnp.exe", "gnp.exe"),
        ("file​name.txt", "filename.txt"),
        ("a" * 300, "a" * 255),
        ("", None),
        ("   ", None),
        (".", None),
        ("..", None),
        ("some/dir/", None),
        ("\x00\x01", None),
        (None, None),
        (12345, None),
        (["sample.bed"], None),
        ({"value": "sample.bed"}, None),
    ],
)
def test_sanitize_drs_name(raw_name, expected):
    assert sanitize_drs_name(raw_name) == expected


@pytest.mark.parametrize(
    "raw_name",
    [
        "a" * 300,
        "\U0001f600" * 255,  # 255 characters, 1020 UTF-8 bytes
        "ü" * 200,
        "🎉ünïcödé" * 40,
    ],
)
def test_sanitize_drs_name_caps_encoded_bytes(raw_name):
    """The cap has to be on bytes -- POSIX NAME_MAX is a byte limit, so 255 emoji would overrun it."""
    sanitized = sanitize_drs_name(raw_name)
    assert sanitized
    assert len(sanitized.encode("utf-8")) <= 255
    # Truncation keeps a prefix and never leaves a mangled partial character behind.
    assert raw_name.startswith(sanitized)
    assert sanitized.encode("utf-8").decode("utf-8") == sanitized


@responses.activate
@mock.patch("galaxy.files.uris.validate_non_local")
def test_file_source_drs_s3(_validate_non_local):
    def drs_repo_handler(request):
        assert request.headers["Authorization"] == "Bearer IBearTokens"
        data = {
            "id": "314160",
            "name": "hello-314160",
            "access_methods": [
                {
                    "type": "s3",
                    "access_id": "1234",
                    "region": "us-east-1",
                }
            ],
        }
        return (200, {}, json.dumps(data))

    def access_handler(request):
        assert request.headers["Authorization"] == "Bearer IBearTokens"
        access_data = {
            "url": "s3://ga4gh-demo-data/phenopackets/Cao-2018-TGFBR2-Patient_4.json",
        }
        return (200, {}, json.dumps(access_data))

    responses.add_callback(
        responses.GET,
        "https://drs.example.org/ga4gh/drs/v1/objects/314160",
        callback=drs_repo_handler,
        content_type="application/json",
    )

    responses.add_callback(
        responses.GET,
        "https://drs.example.org/ga4gh/drs/v1/objects/314160/access/1234",
        callback=access_handler,
        content_type="application/json",
    )

    test_url = "drs://drs.example.org/314160"
    file_sources = configured_file_sources(FILE_SOURCES_CONF)
    user_context = user_context_fixture(file_sources=file_sources)
    file_source_pair = file_sources.get_file_source_path(test_url)

    assert file_source_pair.path == test_url
    assert file_source_pair.file_source.id == "test1"

    assert_realizes_contains(
        file_sources, test_url, "PMID:30101859-Cao-2018-TGFBR2-Patient_4", user_context=user_context
    )


@pytest.mark.usefixtures("fake_public_dns")
@responses.activate
def test_file_source_drs_attach_oidc_token():
    """When http_headers is configured with a template referencing the user's OIDC token, it is sent as a Bearer header."""
    oidc_token = "MyOIDCAccessToken"

    def drs_repo_handler(request):
        assert request.headers["Authorization"] == f"Bearer {oidc_token}"
        data = {
            "id": "999",
            "name": "oidc-test-file",
            "access_methods": [
                {
                    "type": "https",
                    "access_id": "abc",
                }
            ],
        }
        return (200, {}, json.dumps(data))

    def access_handler(request):
        assert request.headers["Authorization"] == f"Bearer {oidc_token}"
        access_data = {
            "url": "https://my.repository.org/oidcfile.txt",
            "headers": [],
        }
        return (200, {}, json.dumps(access_data))

    responses.add_callback(
        responses.GET,
        "https://drs.oidc-example.org/ga4gh/drs/v1/objects/999",
        callback=drs_repo_handler,
        content_type="application/json",
    )
    responses.add_callback(
        responses.GET,
        "https://drs.oidc-example.org/ga4gh/drs/v1/objects/999/access/abc",
        callback=access_handler,
        content_type="application/json",
    )

    test_url = "drs://drs.oidc-example.org/999"

    def check_download(request, **kwargs):
        response: Any = io.StringIO("hello oidc world")
        response.headers = {}
        response.geturl = lambda: test_url
        return response

    with patch_http_open(check_download):
        user_context = DictFileSourcesUserContext(
            username="alice",
            email="alice@galaxyproject.org",
            preferences={},
            role_names=set(),
            group_names=set(),
            is_admin=False,
            oidc_access_tokens={"oidc": oidc_token},
        )
        file_sources = configured_file_sources(DRS_OIDC_FILE_SOURCES_CONF)
        assert_realizes_as(file_sources, test_url, "hello oidc world", user_context=user_context)


@pytest.mark.usefixtures("fake_public_dns")
@responses.activate
def test_file_source_drs_access_lookup_sends_headers():
    object_url = "https://drs.example.org/ga4gh/drs/v1/objects/314161"
    responses.get(object_url, json={"id": "314161", "access_methods": [{"type": "https", "access_id": "1234"}]})

    def access_handler(request):
        assert request.headers["Authorization"] == "Bearer IBearTokens"
        assert request.headers["User-Agent"].startswith("galaxy/")
        return (200, {}, json.dumps({"url": "https://my.respository.org/myfile.txt"}))

    responses.add_callback(responses.GET, f"{object_url}/access/1234", callback=access_handler)

    with patch_http_open(_download_response):
        file_sources = configured_file_sources(FILE_SOURCES_CONF)
        assert_realizes_as(
            file_sources, "drs://drs.example.org/314161", "hello drs world", user_context=user_context_fixture()
        )


@pytest.mark.usefixtures("fake_public_dns")
@responses.activate
def test_drs_lookups_keep_galaxy_user_agent_over_configured_one(tmp_path):
    object_url = "https://drs.example.org/ga4gh/drs/v1/objects/1"
    responses.get(object_url, json={"access_methods": [{"type": "https", "access_id": "1234"}]})
    responses.get(f"{object_url}/access/1234", json={"url": "https://my.respository.org/myfile.txt"})
    with patch_http_open(_download_response):
        fetch_drs_to_file(
            "drs://drs.example.org/1", tmp_path / "out", user_context=None, headers={"User-Agent": "custom"}
        )
    assert [call.request.headers["User-Agent"].split("/")[0] for call in responses.calls] == ["galaxy"] * 2


def _download_response(request, **kwargs):
    response: Any = io.StringIO("hello drs world")
    response.headers = {}
    response.geturl = lambda: request.full_url
    return response


@pytest.mark.usefixtures("fake_public_dns")
@responses.activate
def test_drs_retry_after_202_keeps_headers(tmp_path):
    object_url = "https://drs.example.org/ga4gh/drs/v1/objects/314162"
    responses.get(object_url, status=202, headers={"Retry-After": "1"})
    responses.get(object_url, json=_public_object())
    retry_options = RetryOptions()
    retry_options.override_retry_after = 0.01

    with patch_http_open(_download_response):
        fetch_drs_to_file(
            "drs://drs.example.org/314162",
            tmp_path / "out",
            user_context=None,
            retry_options=retry_options,
            headers={"Authorization": "Bearer IBearTokens"},
        )

    assert [call.request.headers.get("Authorization") for call in responses.calls] == ["Bearer IBearTokens"] * 2


@responses.activate
def test_drs_object_lookup_refuses_private_address(tmp_path):
    with pytest.raises(ConfigDoesNotAllowException):
        fetch_drs_to_file("drs://127.0.0.1:8000/1", tmp_path / "out", user_context=None, force_http=True)
    assert not [call for call in responses.calls if (call.request.url or "").startswith("http://127.0.0.1")]


@pytest.mark.usefixtures("fake_public_dns")
@responses.activate
def test_drs_object_lookup_refuses_redirect_to_private_address(tmp_path):
    responses.get(
        "https://drs.example.org/ga4gh/drs/v1/objects/1",
        status=302,
        headers={"Location": "http://127.0.0.1:8000/secret"},
    )
    with pytest.raises(ConfigDoesNotAllowException):
        fetch_drs_to_file("drs://drs.example.org/1", tmp_path / "out", user_context=None)
    assert [call.request.url for call in responses.calls] == ["https://drs.example.org/ga4gh/drs/v1/objects/1"]


@pytest.mark.usefixtures("fake_public_dns")
@responses.activate
def test_drs_compact_identifier_lookup_refuses_redirect_to_private_address(tmp_path):
    resolved_url = "https://drs.example.org/ga4gh/drs/v1/objects/1"
    responses.get(resolved_url, status=302, headers={"Location": "http://127.0.0.1:8000/secret"})
    with mock.patch.object(
        CompactIdentifierResolver, "resolve_prefix", return_value="https://drs.example.org/ga4gh/drs/v1/objects/{$id}"
    ):
        with pytest.raises(ConfigDoesNotAllowException):
            fetch_drs_to_file("drs://test.prefix:1", tmp_path / "out", user_context=None)
    assert [call.request.url for call in responses.calls] == [resolved_url]


@pytest.mark.usefixtures("fake_public_dns")
@responses.activate
def test_drs_access_lookup_refuses_redirect_to_private_address(tmp_path):
    object_url = "https://drs.example.org/ga4gh/drs/v1/objects/1"
    responses.get(object_url, json={"access_methods": [{"type": "https", "access_id": "1234"}]})
    responses.get(f"{object_url}/access/1234", status=302, headers={"Location": "http://127.0.0.1:8000/secret"})
    with pytest.raises(ConfigDoesNotAllowException):
        fetch_drs_to_file("drs://drs.example.org/1", tmp_path / "out", user_context=None)
    assert [call.request.url for call in responses.calls] == [object_url, f"{object_url}/access/1234"]


@pytest.mark.usefixtures("fake_public_dns")
@responses.activate
def test_drs_unverifiable_access_url_keeps_verification_error(tmp_path):
    responses.get(
        "https://drs.example.org/ga4gh/drs/v1/objects/1",
        json={"access_methods": [{"type": "https", "access_url": {"url": "https://exa%6dple.org/myfile.txt"}}]},
    )
    with pytest.raises(RequestParameterInvalidException, match="Could not verify url"):
        fetch_drs_to_file("drs://drs.example.org/1", tmp_path / "out", user_context=None)


@pytest.mark.usefixtures("fake_public_dns")
@responses.activate
def test_drs_private_access_url_keeps_refusal(tmp_path):
    responses.get(
        "https://drs.example.org/ga4gh/drs/v1/objects/1",
        json={"access_methods": [{"type": "https", "access_url": {"url": "http://127.0.0.1:8000/secret"}}]},
    )
    with pytest.raises(ConfigDoesNotAllowException):
        fetch_drs_to_file("drs://drs.example.org/1", tmp_path / "out", user_context=None)


@pytest.mark.usefixtures("fake_public_dns")
@responses.activate
def test_drs_skips_access_method_without_handler(tmp_path):
    responses.get(
        "https://drs.example.org/ga4gh/drs/v1/objects/1",
        json={
            "access_methods": [
                {"type": "gsiftp", "access_url": {"url": "gsiftp://example.org/myfile.txt"}},
                *_public_object()["access_methods"],
            ]
        },
    )
    with patch_http_open(_download_response):
        fetch_drs_to_file("drs://drs.example.org/1", tmp_path / "out", user_context=None)
    assert (tmp_path / "out").read_text() == "hello drs world"


def _public_object():
    return {
        "access_methods": [{"type": "https", "access_url": {"url": "https://my.respository.org/myfile.txt"}}],
    }
