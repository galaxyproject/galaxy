import os
import tempfile
from unittest.mock import (
    Mock,
    patch,
)

import pytest

from galaxy.files.sources.util import fetch_drs_to_file


class TestDRSCompactIdentifiersIntegration:
    @patch("galaxy.files.sources.util.requests.get")
    @patch("galaxy.files.sources.util.stream_url_to_file")
    def test_fetch_compact_identifier_drs_file(self, mock_stream, mock_get):
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
            "_embedded": {
                "resources": [{"urlPattern": "https://example-drs.com/ga4gh/drs/v1/objects/{$id}", "official": True}]
            }
        }
        resources_response.raise_for_status.return_value = None

        drs_response = Mock()
        drs_response.json.return_value = {
            "id": "test-object-id",
            "access_methods": [
                {
                    "type": "https",
                    "access_url": {
                        "url": "https://download.example.com/test-file.txt",
                        "headers": ["Authorization: Bearer test-token"],
                    },
                }
            ],
        }
        drs_response.raise_for_status.return_value = None
        drs_response.status_code = 200

        mock_get.side_effect = [namespace_response, resources_response, drs_response]

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            try:
                fetch_drs_to_file("drs://drs.test:test-object-id", tmp.name, None)

                assert mock_get.call_count == 3
                mock_get.assert_any_call(
                    "https://registry.api.identifiers.org/restApi/namespaces/search/findByPrefix?prefix=drs.test",
                    timeout=600,
                )
                mock_get.assert_any_call(
                    "https://registry.api.identifiers.org/restApi/namespaces/123/resources",
                    timeout=600,
                )

                mock_get.assert_any_call(
                    "https://example-drs.com/ga4gh/drs/v1/objects/test-object-id", timeout=600, headers=None
                )

                mock_stream.assert_called_once()
                call_args = mock_stream.call_args
                assert call_args[0][0] == "https://download.example.com/test-file.txt"
                assert call_args[1]["target_path"] == tmp.name

            finally:
                if os.path.exists(tmp.name):
                    os.unlink(tmp.name)

    def test_compact_identifier_error_handling(self):
        invalid_uris = [
            "drs://",  # No identifier
            "drs://no-colon",  # Missing colon
            "drs://:only-accession",  # Missing prefix
            "drs://prefix:",  # Missing accession
            "drs://UPPERCASE:accession",  # Invalid prefix format
            "https://not-drs:accession",  # Wrong scheme
        ]

        for uri in invalid_uris:
            with pytest.raises(ValueError):
                fetch_drs_to_file(uri, "/tmp/output", None)

    @patch("galaxy.files.sources.util.CompactIdentifierResolver._query_identifiers_org")
    def test_meta_resolver_failure_handling(self, mock_identifiers):
        mock_identifiers.return_value = None

        with pytest.raises(ValueError, match="Failed to resolve compact identifier DRS URI"):
            fetch_drs_to_file("drs://unknown.prefix:accession", "/tmp/output", None)
