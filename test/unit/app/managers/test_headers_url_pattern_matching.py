from galaxy.config.url_headers import UrlHeadersConfigFactory


def create_overlapping_patterns_config():
    """Create config with multiple overlapping patterns to test all-matches behavior."""
    config_dict = {
        "patterns": [
            {
                "url_pattern": r"^https://api\.github\.com/.*",
                "headers": [
                    {"name": "Accept", "sensitive": False},
                    {"name": "Content-Type", "sensitive": False},
                ],
            },
            {
                "url_pattern": r"^https://api\.github\.com/repos/.*",
                "headers": [
                    {"name": "Authorization", "sensitive": True},
                ],
            },
            {
                "url_pattern": r"^https://.*",
                "headers": [
                    {"name": "Accept-Encoding", "sensitive": False},
                ],
            },
        ]
    }

    return UrlHeadersConfigFactory.from_dict(config_dict)


class TestAllMatchesPatternBehavior:
    """Test that all matching patterns are considered (union of permissions)."""

    def test_find_all_matching_returns_all_patterns(self):
        """Test that find_all_matching returns all patterns that match a URL."""
        config = create_overlapping_patterns_config()

        # URL matches all three patterns
        url = "https://api.github.com/repos/owner/repo"
        matching = config.find_all_matching(url)

        assert len(matching) == 3

    def test_header_allowed_checks_all_matching_patterns(self):
        """Test that a header is allowed if ANY matching pattern allows it."""
        config = create_overlapping_patterns_config()

        url = "https://api.github.com/repos/owner/repo"

        # Each header should be allowed if it's in ANY matching pattern
        assert config.is_header_allowed_for_url("Accept", url)  # From github_basic
        assert config.is_header_allowed_for_url("Content-Type", url)  # From github_basic
        assert config.is_header_allowed_for_url("Authorization", url)  # From github_auth
        assert config.is_header_allowed_for_url("Accept-Encoding", url)  # From https_generic

        # Headers not in any pattern
        assert not config.is_header_allowed_for_url("X-Custom-Header", url)
        assert not config.is_header_allowed_for_url("Cookie", url)

    def test_header_allowed_subset_of_patterns(self):
        """Test headers allowed when only subset of patterns match."""
        config = create_overlapping_patterns_config()

        # URL only matches github_basic and https_generic (not github_auth)
        url = "https://api.github.com/users/octocat"

        assert config.is_header_allowed_for_url("Accept", url)  # From github_basic
        assert config.is_header_allowed_for_url("Accept-Encoding", url)  # From https_generic
        # Authorization not allowed because github_auth pattern doesn't match
        assert not config.is_header_allowed_for_url("Authorization", url)

    def test_header_sensitive_secure_by_default(self):
        """Test that if ANY pattern marks header sensitive, it's treated as sensitive."""
        config_dict = {
            "patterns": [
                {
                    "url_pattern": r"^https://test1\.example\.com/.*",
                    "headers": [{"name": "Authorization", "sensitive": False}],
                },
                {
                    "url_pattern": r"^https://.*\.example\.com/.*",
                    "headers": [{"name": "Authorization", "sensitive": True}],
                },
            ]
        }
        config = UrlHeadersConfigFactory.from_dict(config_dict)

        # URL matches both patterns
        url = "https://test1.example.com/api"

        # Should be treated as sensitive (secure by default)
        assert config.is_header_sensitive_for_url("Authorization", url)

    def test_multiple_overlapping_patterns_union(self):
        """Test that union of headers from all matching patterns is allowed."""
        config_dict = {
            "patterns": [
                {
                    "url_pattern": r"^https://example\.com/.*",
                    "headers": [
                        {"name": "Header-A", "sensitive": False},
                        {"name": "Header-B", "sensitive": True},
                    ],
                },
                {
                    "url_pattern": r"^https://example\.com/api/.*",
                    "headers": [
                        {"name": "Header-C", "sensitive": False},
                        {"name": "Header-D", "sensitive": True},
                    ],
                },
                {
                    "url_pattern": r"^https://example\.com/api/v1/.*",
                    "headers": [
                        {"name": "Header-E", "sensitive": False},
                    ],
                },
            ]
        }
        config = UrlHeadersConfigFactory.from_dict(config_dict)

        # URL matches all three patterns
        url = "https://example.com/api/v1/resource"

        # All headers from all patterns should be allowed
        assert config.is_header_allowed_for_url("Header-A", url)
        assert config.is_header_allowed_for_url("Header-B", url)
        assert config.is_header_allowed_for_url("Header-C", url)
        assert config.is_header_allowed_for_url("Header-D", url)
        assert config.is_header_allowed_for_url("Header-E", url)

        # Headers B and D should be sensitive
        assert config.is_header_sensitive_for_url("Header-B", url)
        assert config.is_header_sensitive_for_url("Header-D", url)

        # Headers A, C, E should not be sensitive
        assert not config.is_header_sensitive_for_url("Header-A", url)
        assert not config.is_header_sensitive_for_url("Header-C", url)
        assert not config.is_header_sensitive_for_url("Header-E", url)

    def test_no_matching_patterns(self):
        """Test behavior when no patterns match."""
        config = create_overlapping_patterns_config()

        # URL doesn't match any pattern
        url = "http://example.com/api"  # http, not https

        matching = config.find_all_matching(url)
        assert len(matching) == 0

        # No headers should be allowed
        assert not config.is_header_allowed_for_url("Accept", url)
        assert not config.is_header_allowed_for_url("Authorization", url)
