import io
import json
import os
import urllib
from typing import Any
from unittest import mock

import pytest
import responses

from galaxy.files import (
    DictFileSourcesUserContext,
    ProvidesFileSourcesUserContext,
)
from ._util import (
    assert_realizes_as,
    assert_realizes_contains,
    configured_file_sources,
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

    with mock.patch.object(urllib.request, "urlopen", new=check_specific_header):
        user_context = user_context_fixture()
        file_sources = configured_file_sources(FILE_SOURCES_CONF)
        file_source_pair = file_sources.get_file_source_path(test_url)

        assert file_source_pair.path == test_url
        assert file_source_pair.file_source.id == "test1"

        assert_realizes_as(file_sources, test_url, "hello drs world", user_context=user_context)


@responses.activate
def test_file_source_drs_s3():
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

    with mock.patch.object(urllib.request, "urlopen", new=check_download):
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
