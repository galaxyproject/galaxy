"""Unit tests for the MCP request/response stubs.

Regression coverage for the bug where MCP tools constructed a bare
``WorkRequestContext`` (no ``.request`` attribute), causing
``HDASerializer.serialize_old_display_applications`` to raise
``AttributeError: 'WorkRequestContext' object has no attribute 'request'``
whenever ``enable_old_display_applications`` was set.
"""

import pytest

from galaxy.tool_util.deps.mulled.recommend import (
    ContainerRecommendation,
    MatchQuality,
    RecommendationSource,
)
from galaxy.webapps.galaxy.api.mcp import (
    _biocontainer_recommendation_payload,
    _StaticRequest,
    _StaticResponse,
)
from galaxy.work.context import (
    GalaxyAbstractRequest,
    GalaxyAbstractResponse,
)


def _recording_recommender(image, match_quality=MatchQuality.EXACT_VERSION):
    """Fake recommend_container that records the specs it was given."""
    seen = {}

    def recommend(specs):
        seen["specs"] = list(specs)
        return ContainerRecommendation(
            image=image,
            source=RecommendationSource.QUAY_SINGLE if image else RecommendationSource.NONE,
            match_quality=match_quality,
            packages=tuple(specs),
            multi_package=len(specs) > 1,
            tag=(image.split(":")[-1] if image else None),
        )

    return recommend, seen


def test_recommend_biocontainer_payload_parses_and_shapes():
    recommend, seen = _recording_recommender("quay.io/biocontainers/samtools:1.17--h0_0")
    verify_calls = []

    def verify(image):
        verify_calls.append(image)
        return True

    out = _biocontainer_recommendation_payload(["samtools=1.17", " bwa "], recommend=recommend, verify=verify)

    # "name=version" and bare "name" (whitespace-trimmed) parse into PackageSpecs:
    assert [(p.name, p.version) for p in seen["specs"]] == [("samtools", "1.17"), ("bwa", None)]
    assert out == {
        "image": "quay.io/biocontainers/samtools:1.17--h0_0",
        "found": True,
        "match_quality": "exact_version",
        "source": "quay_single",
        "notes": [],
        "verified": True,
    }
    assert verify_calls == ["quay.io/biocontainers/samtools:1.17--h0_0"]


def test_recommend_biocontainer_payload_skips_blanks_and_handles_no_image():
    recommend, seen = _recording_recommender(None, match_quality=MatchQuality.NOT_FOUND)
    verify_calls = []

    def verify(image):
        verify_calls.append(image)
        return True

    out = _biocontainer_recommendation_payload(["", "   ", "nosuchpkg"], recommend=recommend, verify=verify)

    assert [(p.name, p.version) for p in seen["specs"]] == [("nosuchpkg", None)]  # blanks dropped
    assert out["found"] is False and out["image"] is None
    assert out["verified"] is None  # no image -> verifier not consulted
    assert verify_calls == []


@pytest.mark.external_dependency_management
def test_recommend_biocontainer_payload_real_lookup():
    out = _biocontainer_recommendation_payload(["samtools=1.17"])
    assert out["found"] is True
    assert out["image"].startswith("quay.io/biocontainers/samtools")


def test_static_request_implements_abstract_interface():
    request = _StaticRequest("http://localhost:8080")
    assert isinstance(request, GalaxyAbstractRequest)


def test_static_request_base_always_has_trailing_slash():
    # Matches GalaxyASGIRequest.base shape (Starlette base_url has trailing slash).
    assert _StaticRequest("http://localhost:8080").base == "http://localhost:8080/"
    assert _StaticRequest("http://localhost:8080/").base == "http://localhost:8080/"
    assert _StaticRequest("https://example.org/galaxy").base == "https://example.org/galaxy/"


def test_static_request_host_and_security():
    insecure = _StaticRequest("http://localhost:8080")
    assert insecure.host == "localhost:8080"
    assert insecure.is_secure is False

    secure = _StaticRequest("https://galaxy.example.org")
    assert secure.host == "galaxy.example.org"
    assert secure.is_secure is True


def test_static_request_get_cookie_returns_none():
    assert _StaticRequest("http://localhost:8080").get_cookie("anything") is None


def test_static_response_implements_abstract_interface():
    response = _StaticResponse()
    assert isinstance(response, GalaxyAbstractResponse)
    assert response.headers == {}
    response.set_cookie("k", "v")
