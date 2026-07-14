"""Unit tests for Invenio multipart upload functionality."""

import pytest

from galaxy.files.sources.invenio import (
    calculate_multipart_params,
    MAX_UPLOAD_PART_SIZE,
    MAX_UPLOAD_PARTS,
    MIN_UPLOAD_PART_SIZE,
)


class TestCalculateMultipartParams:
    """Tests for calculate_multipart_params function."""

    def test_calculate_multipart_params_zero_byte(self):
        """Zero-byte files should return (1, 0)."""
        parts, part_size = calculate_multipart_params(0)
        assert parts == 1
        assert part_size == 0

    def test_calculate_multipart_params_small_file(self):
        """Files under 5 MiB should use minimum part size."""
        # 2 MiB file
        file_size = 2 * 1024 * 1024
        parts, part_size = calculate_multipart_params(file_size)
        assert parts == 1
        assert part_size == MIN_UPLOAD_PART_SIZE

    def test_calculate_multipart_params_medium_file(self):
        """Files between 5 MiB and 10 MiB."""
        # 7.5 MiB file
        file_size = 7 * 1024 * 1024 + 512 * 1024
        parts, part_size = calculate_multipart_params(file_size)
        assert parts == 2
        assert part_size == MIN_UPLOAD_PART_SIZE

    def test_calculate_multipart_params_large_file(self):
        """Large files requiring multiple parts."""
        # 25 MiB file
        file_size = 25 * 1024 * 1024
        parts, part_size = calculate_multipart_params(file_size)
        assert parts == 5
        assert part_size == MIN_UPLOAD_PART_SIZE

    def test_calculate_multipart_params_respects_max_parts(self):
        """Very large files should not exceed MAX_UPLOAD_PARTS."""
        # File larger than MAX_UPLOAD_PARTS * MIN_UPLOAD_PART_SIZE
        file_size = MAX_UPLOAD_PARTS * MIN_UPLOAD_PART_SIZE + MIN_UPLOAD_PART_SIZE
        parts, part_size = calculate_multipart_params(file_size)
        assert parts <= MAX_UPLOAD_PARTS
        assert part_size >= MIN_UPLOAD_PART_SIZE

    def test_calculate_multipart_params_extremely_large_file(self):
        """Extremely large files should hit both MAX limits.

        Note: Files larger than MAX_UPLOAD_PARTS * MAX_UPLOAD_PART_SIZE (~48.8 TiB)
        cannot be uploaded via multipart, but we cap params rather than fail here.
        The upload would fail server-side anyway.
        """
        # 100 TiB file - exceeds theoretical maximum (~48.8 TiB)
        file_size = 100 * 1024**4  # 100 TiB
        parts, part_size = calculate_multipart_params(file_size)
        # Parts should be capped at MAX_UPLOAD_PARTS
        assert parts == MAX_UPLOAD_PARTS
        # Part size should hit max
        assert part_size == MAX_UPLOAD_PART_SIZE

    def test_calculate_multipart_params_respects_preferred_part_size(self):
        """Should use preferred part size when provided and valid."""
        # 150 MiB file with 100 MiB preferred part size
        file_size = 150 * 1024 * 1024
        preferred_part_size = 100 * 1024 * 1024  # 100 MiB
        parts, part_size = calculate_multipart_params(file_size, preferred_part_size)
        assert parts == 2
        assert part_size == preferred_part_size

    def test_calculate_multipart_params_preferred_too_small(self):
        """Should use minimum part size if preferred is too small."""
        # 100 MiB file with 1 MiB preferred part size (too small)
        file_size = 100 * 1024 * 1024
        preferred_part_size = 1 * 1024 * 1024  # 1 MiB - too small
        parts, part_size = calculate_multipart_params(file_size, preferred_part_size)
        assert part_size == MIN_UPLOAD_PART_SIZE  # Should be bumped to minimum

    def test_calculate_multipart_params_preferred_exceeds_max(self):
        """Should cap at MAX_UPLOAD_PART_SIZE if preferred exceeds it."""
        # Small file with huge preferred part size
        file_size = 100 * 1024 * 1024
        preferred_part_size = MAX_UPLOAD_PART_SIZE * 2  # Exceeds max
        parts, part_size = calculate_multipart_params(file_size, preferred_part_size)
        assert parts == 1
        assert part_size == MAX_UPLOAD_PART_SIZE

    def test_calculate_multipart_params_exact_multiple(self):
        """File size that's an exact multiple of part size."""
        # Exactly 3 * MIN_UPLOAD_PART_SIZE
        file_size = 3 * MIN_UPLOAD_PART_SIZE
        parts, part_size = calculate_multipart_params(file_size)
        assert parts == 3
        assert part_size == MIN_UPLOAD_PART_SIZE

    def test_calculate_multipart_params_one_byte_over(self):
        """File size one byte over an exact multiple."""
        # 3 * MIN_UPLOAD_PART_SIZE + 1 byte
        file_size = 3 * MIN_UPLOAD_PART_SIZE + 1
        parts, part_size = calculate_multipart_params(file_size)
        assert parts == 4  # Need 4 parts for 3 full + 1 byte
        assert part_size == MIN_UPLOAD_PART_SIZE

    def test_calculate_multipart_params_at_boundary(self):
        """Test file at MAX_UPLOAD_PARTS boundary."""
        # Exactly at the boundary where we need to increase part size
        file_size = (MAX_UPLOAD_PARTS + 1) * MIN_UPLOAD_PART_SIZE
        parts, part_size = calculate_multipart_params(file_size)
        assert parts <= MAX_UPLOAD_PARTS
        # Part size should have increased
        assert part_size > MIN_UPLOAD_PART_SIZE
