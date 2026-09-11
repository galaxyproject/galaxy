"""Browser-bound, single-use authentication state stored alongside PSA partials."""

import hashlib
import json
import math
import re
import secrets
import time
from collections.abc import Mapping
from typing import (
    Any,
    Literal,
)

from sqlalchemy import (
    delete,
    select,
)
from sqlalchemy.orm import Session

from galaxy.exceptions import AuthenticationFailed
from galaxy.model import (
    GalaxySession,
    PSAPartial,
)

FLOW_LIFETIME = 600
FLOW_NAMESPACE = "gxy-flow-"
FLOW_STEPS = {"authentication": -1, "confirmation": -2}
FlowPurpose = Literal["authentication", "confirmation"]


class InvalidFlow(AuthenticationFailed):
    def __init__(self) -> None:
        super().__init__("Authentication has expired or is invalid. Please start logging in again.")


def authentication_id(state: str | None) -> str:
    if not isinstance(state, str) or not state or len(state) > 1024:
        raise InvalidFlow()
    return hashlib.sha256(state.encode()).hexdigest()[:32]


class FlowState:
    def __init__(self, session: Session, galaxy_session: GalaxySession | None, provider: str) -> None:
        if galaxy_session is None or galaxy_session.id is None or not galaxy_session.is_valid:
            raise InvalidFlow()
        self.session = session
        self.galaxy_session = galaxy_session
        self.provider = provider
        # Keep the namespace within PSAPartial.backend's 32-character column.
        binding = f"{galaxy_session.id}:{provider}"
        self.namespace = FLOW_NAMESPACE + hashlib.sha256(binding.encode()).hexdigest()[:23]

    def save(
        self,
        purpose: FlowPurpose,
        payload: dict[str, Any],
        *,
        identifier: str | None = None,
        expires_at: float | None = None,
    ) -> str:
        now = time.time()
        if expires_at is not None and (
            not isinstance(expires_at, (int, float)) or not math.isfinite(expires_at) or expires_at <= now
        ):
            raise InvalidFlow()
        expires_at = min(now + FLOW_LIFETIME, expires_at) if expires_at is not None else now + FLOW_LIFETIME
        if not math.isfinite(expires_at) or expires_at <= now:
            raise InvalidFlow()
        identifier = identifier or secrets.token_hex(16)
        self._validate_identifier(identifier)
        self._cleanup(now)
        # A new attempt replaces the previous attempt for this browser/provider.
        self.session.execute(delete(PSAPartial).where(PSAPartial.backend == self.namespace))
        envelope = {
            "version": 1,
            "purpose": purpose,
            "session_id": self.galaxy_session.id,
            "provider": self.provider,
            "expires_at": expires_at,
            "payload": payload,
        }
        self.session.add(PSAPartial(identifier, json.dumps(envelope), FLOW_STEPS[purpose], self.namespace))
        self.session.commit()
        return identifier

    def consume(self, purpose: FlowPurpose, identifier: str) -> dict[str, Any]:
        self._validate_identifier(identifier)
        records = self.session.scalars(
            select(PSAPartial)
            .where(
                PSAPartial.backend == self.namespace,
                PSAPartial.next_step == FLOW_STEPS[purpose],
                PSAPartial.token == identifier,
            )
            .limit(2)
        ).all()
        if len(records) != 1:
            raise InvalidFlow()
        record = records[0]
        envelope = self._decode(record.data)
        if (
            envelope.get("version") != 1
            or envelope.get("purpose") != purpose
            or envelope.get("session_id") != self.galaxy_session.id
            or envelope.get("provider") != self.provider
            or not self._unexpired(envelope, time.time())
            or not isinstance(envelope.get("payload"), dict)
        ):
            raise InvalidFlow()
        # Do not use PSAPartial.destroy: a read followed by an unconditional delete
        # would allow two workers to complete the same authentication attempt.
        # Skip ORM synchronization: EXISTS cannot be evaluated in Python, and
        # only the affected-row count is needed; the loaded record is not reused.
        result = self.session.execute(
            delete(PSAPartial)
            .where(
                PSAPartial.id == record.id,
                PSAPartial.backend == self.namespace,
                PSAPartial.next_step == FLOW_STEPS[purpose],
                PSAPartial.token == identifier,
                PSAPartial.data == record.data,
                select(GalaxySession.id)
                .where(GalaxySession.id == self.galaxy_session.id, GalaxySession.is_valid.is_(True))
                .exists(),
            )
            .execution_options(synchronize_session=False)
        )
        self.session.commit()
        if result.rowcount != 1:
            raise InvalidFlow()
        # Consume before calling account creation helpers, which commit independently.
        return envelope["payload"]

    @staticmethod
    def _validate_identifier(identifier: str) -> None:
        if not isinstance(identifier, str) or not re.fullmatch(r"[0-9a-f]{32}", identifier):
            raise InvalidFlow()

    @staticmethod
    def _decode(data: str | None) -> dict[str, Any]:
        if data is None:
            return {}
        try:
            envelope = json.loads(data)
        except (TypeError, ValueError):
            return {}
        return envelope if isinstance(envelope, dict) else {}

    @staticmethod
    def _unexpired(envelope: Mapping[str, object], now: float) -> bool:
        expiry = envelope.get("expires_at")
        return isinstance(expiry, (int, float)) and math.isfinite(expiry) and expiry > now

    def _cleanup(self, now: float) -> None:
        # Bounded cleanup, restricted to our namespace; ordinary PSA partials are
        # owned by social-core and must never be interpreted as flow records.
        records = self.session.scalars(
            select(PSAPartial)
            .where(PSAPartial.backend.startswith(FLOW_NAMESPACE), PSAPartial.next_step.in_(FLOW_STEPS.values()))
            .order_by(PSAPartial.id)
            .limit(100)
        )
        expired = [record.id for record in records if not self._unexpired(self._decode(record.data), now)]
        if expired:
            self.session.execute(delete(PSAPartial).where(PSAPartial.id.in_(expired)))
