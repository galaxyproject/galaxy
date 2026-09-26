"""Tests for keyset token pagination."""

import pytest

from galaxy import exceptions
from galaxy.model.keyset_token_pagination import (
    KeysetPagination,
    SingleKeysetToken,
)


@pytest.fixture
def pagination():
    """Provide KeysetPagination instance."""
    return KeysetPagination()


class TestSingleKeysetToken:
    """Test SingleKeysetToken implementation."""

    def test_to_values(self):
        """Test converting token to values."""
        token = SingleKeysetToken(last_id=42)
        assert token.to_values() == [42]

    def test_from_values(self):
        """Test reconstructing token from values."""
        token = SingleKeysetToken.from_values([42])
        assert token.last_id == 42

    def test_from_values_multiple(self):
        """Test from_values uses first value only."""
        token = SingleKeysetToken.from_values([42, 100, 200])
        assert token.last_id == 42

    def test_from_values_empty_raises(self):
        """Test from_values raises on empty values."""
        with pytest.raises(ValueError, match="requires at least 1 value"):
            SingleKeysetToken.from_values([])


class TestKeysetPagination:
    """Test KeysetPagination encoder/decoder."""

    def test_encode_decode_roundtrip(self, pagination):
        """Test encoding and decoding roundtrip."""
        original = SingleKeysetToken(last_id=123)
        encoded = pagination.encode_token(original)
        decoded = pagination.decode_token(encoded, token_class=SingleKeysetToken)
        assert decoded is not None
        assert decoded.last_id == 123

    def test_decode_none_token_returns_none(self, pagination):
        """Test decoding None returns None."""
        result = pagination.decode_token(None, token_class=SingleKeysetToken)
        assert result is None

    def test_decode_empty_string_returns_none(self, pagination):
        """Test decoding empty string returns None."""
        result = pagination.decode_token("", token_class=SingleKeysetToken)
        assert result is None

    def test_decode_invalid_token_raises(self, pagination):
        """Test decoding invalid token raises MessageException."""
        with pytest.raises(exceptions.MessageException, match="Invalid page_token"):
            pagination.decode_token("invalid_token_!@#", token_class=SingleKeysetToken)

    def test_encode_multiple_values(self, pagination):
        """Test encoding handles multiple values."""
        # Create custom token class with multiple values
        from dataclasses import dataclass

        @dataclass
        class MultiValueToken:
            val1: int
            val2: int
            val3: int

            def to_values(self):
                return [self.val1, self.val2, self.val3]

            @classmethod
            def from_values(cls, values):
                return cls(val1=values[0], val2=values[1], val3=values[2])

        original = MultiValueToken(val1=1, val2=2, val3=3)
        encoded = pagination.encode_token(original)
        decoded = pagination.decode_token(encoded, token_class=MultiValueToken)
        assert decoded is not None
        assert decoded.val1 == 1
        assert decoded.val2 == 2
        assert decoded.val3 == 3
