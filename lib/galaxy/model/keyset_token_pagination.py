"""Keyset-based pagination support for cursor-stable pagination."""

import base64
import json
from dataclasses import dataclass
from typing import (
    cast,
    Optional,
    Protocol,
    TypeVar,
)

from galaxy import exceptions


class KeysetToken(Protocol):
    """Protocol for keyset tokens that can be encoded/decoded.

    Implementations must provide:
    - to_values(): Convert token to normalized list of values for encoding
    - from_values(): Reconstruct token from decoded values (classmethod)
    """

    def to_values(self) -> list:
        """Convert token to normalized list of values for encoding.

        Returns:
            List of values to be JSON-encoded
        """
        ...

    @classmethod
    def from_values(cls, values: list) -> "KeysetToken":
        """Reconstruct token from decoded values.

        Args:
            values: List of values from JSON decoding

        Returns:
            Token instance
        """
        ...


@dataclass
class SingleKeysetToken:
    """Single ID column keyset token.

    Used for pagination on a single numeric ID column (e.g., database IDs).
    """

    last_id: int

    def to_values(self) -> list:
        """Convert to normalized values."""
        return [self.last_id]

    @classmethod
    def from_values(cls, values: list) -> "SingleKeysetToken":
        """Reconstruct from decoded values."""
        if len(values) < 1:
            raise ValueError("SingleKeysetToken requires at least 1 value")
        return cls(last_id=values[0])


T = TypeVar("T", bound=KeysetToken)


class KeysetPagination:
    """Keyset pagination encoder/decoder using Protocol.

    Encodes tokens to opaque base64 strings, works with any KeysetToken
    implementation via Protocol duck typing.
    """

    def encode_token(self, token: KeysetToken) -> str:
        """Encode keyset token to opaque base64 string.

        Works with any KeysetToken implementation via Protocol.

        Args:
            token: Token implementing KeysetToken protocol

        Returns:
            Base64-encoded token string
        """
        values = token.to_values()
        payload = json.dumps(values)
        return base64.b64encode(payload.encode()).decode()

    def decode_token(
        self,
        encoded: Optional[str],
        token_class: type[T],
    ) -> Optional[T]:
        """Decode token using provided token class.

        Args:
            encoded: Base64-encoded token string
            token_class: Token class with from_values() classmethod

        Returns:
            Decoded token instance or None if encoded is None

        Raises:
            MessageException: If token is invalid
        """
        if not encoded:
            return None

        try:
            payload = base64.b64decode(encoded.encode()).decode()
            values = json.loads(payload)
            return cast(T, token_class.from_values(values))
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            raise exceptions.MessageException(f"Invalid page_token: {str(e)}")
