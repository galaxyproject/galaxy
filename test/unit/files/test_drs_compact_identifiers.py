from unittest.mock import (
    Mock,
    patch,
)

import pytest

from galaxy.files.sources.util import (
    CompactIdentifierResolver,
    parse_compact_identifier,
    resolve_compact_identifier_to_url,
)


class TestCompactIdentifierParsing:
    def test_parse_valid_compact_identifier(self):
        prefix, accession = parse_compact_identifier("drs://drs.anv0:v2_64634a63-6ab8-361c-9bc2-e0f04ac9f7fd")
        assert prefix == "drs.anv0"
        assert accession == "v2_64634a63-6ab8-361c-9bc2-e0f04ac9f7fd"

    def test_parse_with_provider_code(self):
        prefix, accession = parse_compact_identifier("drs://provider.namespace:12345")
        assert prefix == "provider.namespace"
        assert accession == "12345"

    def test_parse_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid compact identifier format"):
            parse_compact_identifier("drs://no-colon-here")

    def test_parse_empty_components(self):
        with pytest.raises(ValueError, match="Empty prefix or accession"):
            parse_compact_identifier("drs://:accession-only")

    def test_parse_invalid_prefix_format(self):
        with pytest.raises(ValueError, match="Invalid prefix format"):
            parse_compact_identifier("drs://UPPERCASE:accession")

    def test_parse_not_drs_uri(self):
        with pytest.raises(ValueError, match="Not a valid DRS URI"):
            parse_compact_identifier("https://example.com")


class TestCompactIdentifierResolver:
    @patch("galaxy.files.sources.util.requests.get")
    def test_identifiers_org_resolution(self, mock_get):
        namespace_response = Mock()
        namespace_response.json.return_value = {
            "_links": {
                "self": {"href": "https://registry.api.identifiers.org/restApi/namespaces/123"},
                "resources": {"href": "https://registry.api.identifiers.org/restApi/namespaces/123/resources"},
            }
        }
        namespace_response.raise_for_status.return_value = None

        resources_response = Mock()
        resources_response.json.return_value = {
            "_embedded": {"resources": [{"urlPattern": "https://example.com/objects/{$id}", "official": True}]}
        }
        resources_response.raise_for_status.return_value = None

        mock_get.side_effect = [namespace_response, resources_response]

        resolver = CompactIdentifierResolver()
        url_pattern = resolver._query_identifiers_org("test.prefix")

        assert url_pattern == "https://example.com/objects/{$id}"

        assert mock_get.call_count == 2
        mock_get.assert_any_call(
            "https://registry.api.identifiers.org/restApi/namespaces/search/findByPrefix?prefix=test.prefix",
            timeout=600,
        )
        mock_get.assert_any_call("https://registry.api.identifiers.org/restApi/namespaces/123/resources", timeout=600)

    @patch("galaxy.files.sources.util.requests.get")
    def test_identifiers_org_resolution_unofficial_resource(self, mock_get):
        namespace_response = Mock()
        namespace_response.json.return_value = {
            "_links": {"resources": {"href": "https://registry.api.identifiers.org/restApi/namespaces/456/resources"}}
        }
        namespace_response.raise_for_status.return_value = None

        resources_response = Mock()
        resources_response.json.return_value = {
            "_embedded": {
                "resources": [{"urlPattern": "https://unofficial.example.com/objects/{$id}", "official": False}]
            }
        }
        resources_response.raise_for_status.return_value = None

        mock_get.side_effect = [namespace_response, resources_response]

        resolver = CompactIdentifierResolver()
        url_pattern = resolver._query_identifiers_org("test.prefix")

        assert url_pattern == "https://unofficial.example.com/objects/{$id}"

    def test_cache_behavior(self):
        # Reset singleton for test isolation
        CompactIdentifierResolver._reset_singleton()

        resolver = CompactIdentifierResolver(cache_ttl=3600)
        resolver._cache_result("test.prefix", "https://example.com/{$id}")

        assert resolver._is_cached("test.prefix")
        assert resolver.resolve_prefix("test.prefix") == "https://example.com/{$id}"

        import time

        resolver._cache["test.prefix"]["timestamp"] = time.time() - 3700
        assert not resolver._is_cached("test.prefix")


class TestResolution:
    @patch("galaxy.files.sources.util.CompactIdentifierResolver.resolve_prefix")
    def test_full_resolution(self, mock_resolve):
        mock_resolve.return_value = "https://example.com/ga4gh/drs/v1/objects/{$id}"

        url = resolve_compact_identifier_to_url("drs://test.prefix:abc/123")

        assert url == "https://example.com/ga4gh/drs/v1/objects/abc%2F123"

    @patch("galaxy.files.sources.util.CompactIdentifierResolver.resolve_prefix")
    def test_resolution_with_special_chars(self, mock_resolve):
        mock_resolve.return_value = "https://example.com/objects/{$id}"

        url = resolve_compact_identifier_to_url("drs://test.prefix:abc:def/123#456")
        assert url == "https://example.com/objects/abc%3Adef%2F123%23456"

    @patch("galaxy.files.sources.util.CompactIdentifierResolver.resolve_prefix")
    def test_resolution_failure(self, mock_resolve):
        mock_resolve.return_value = None

        with pytest.raises(ValueError, match="Could not resolve prefix"):
            resolve_compact_identifier_to_url("drs://unknown.prefix:accession")

    @patch("galaxy.files.sources.util.CompactIdentifierResolver.resolve_prefix")
    def test_invalid_resolved_url(self, mock_resolve):
        mock_resolve.return_value = "ftp://example.com/{$id}"

        with pytest.raises(ValueError, match="Resolved URL is not HTTP"):
            resolve_compact_identifier_to_url("drs://test.prefix:accession")


class TestFetchDrsToFile:
    @patch("galaxy.files.sources.util.resolve_compact_identifier_to_url")
    @patch("galaxy.files.sources.util.retry_and_get")
    @patch("galaxy.files.sources.util.stream_url_to_file")
    def test_fetch_compact_identifier_drs(self, mock_stream, mock_retry_get, mock_resolve):
        from galaxy.files.sources.util import fetch_drs_to_file

        mock_resolve.return_value = "https://example.com/ga4gh/drs/v1/objects/object123"

        mock_response = Mock()
        mock_response.json.return_value = {
            "access_methods": [{"type": "https", "access_url": {"url": "https://download.example.com/file.txt"}}]
        }
        mock_response.raise_for_status.return_value = None
        mock_retry_get.return_value = mock_response

        fetch_drs_to_file("drs://test.prefix:object123", "/tmp/output.txt", None)

        mock_resolve.assert_called_once()
        mock_retry_get.assert_called_once()
        args = mock_retry_get.call_args[0]
        assert args[0] == "https://example.com/ga4gh/drs/v1/objects/object123"
        mock_stream.assert_called_once()
