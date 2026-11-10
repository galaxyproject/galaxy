"""Manager for the OAuth 2.0 device flow, which lets an external app log in to Galaxy for a user."""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import (
    exists,
    select,
    update,
)

from galaxy import model
from galaxy.exceptions import (
    Conflict,
    ObjectNotFound,
)
from galaxy.managers.api_keys import ApiKeyManager
from galaxy.model import OAuthDeviceAuthorization
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.schema.oauth import OAuthErrorCode
from galaxy.util import now

# Apps allowed to start a device flow login, by client ID, with the name shown on the approval page.
# (Later, we can add apps like `galaxy-mcp` etc.)
KNOWN_APPS: dict[str, str] = {
    "galaxy-cli": "Galaxy CLI",
}

# Seconds a device login stays valid, and the minimum seconds between token requests.
DEVICE_CODE_EXPIRES_IN = 900
POLLING_INTERVAL = 5

# The `grant_type` RFC 8628 §3.4 defines for device flow token requests. OAuth has a single token
# endpoint for every kind of grant, so the app names which one it is using with this standard URN.
DEVICE_CODE_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"

# Consonants only, so codes are easy to read and type and can't spell words (RFC 8628 §6.1).
USER_CODE_ALPHABET = "BCDFGHJKLMNPQRSTVWXZ"


class OAuthError(Exception):
    """An error to send back as an OAuth error response, e.g. `invalid_client`."""

    def __init__(self, error: OAuthErrorCode, description: str | None = None):
        super().__init__(description or error)
        self.error = error
        self.description = description


@dataclass
class IssuedToken:
    access_token: str
    # Seconds until the token expires, or None if it does not expire.
    expires_in: int | None
    scope: str | None


@dataclass
class StartedAuthorization:
    authorization: OAuthDeviceAuthorization
    # Only returned here; the database keeps a hash of it.
    device_code: str


def hash_device_code(device_code: str) -> str:
    return hashlib.sha256(device_code.encode()).hexdigest()


def normalize_user_code(user_code: str) -> str:
    """Accept codes typed in any case, with or without the dash, e.g. `wdjb mjht`."""
    chars = "".join(c for c in user_code.upper() if c.isalpha())
    return f"{chars[:4]}-{chars[4:]}"


def generate_user_code() -> str:
    """Return a code like `WDJB-MJHT`."""
    chars = [secrets.choice(USER_CODE_ALPHABET) for _ in range(8)]
    return f"{''.join(chars[:4])}-{''.join(chars[4:])}"


class OAuthDeviceManager:
    def __init__(self, sa_session: galaxy_scoped_session, api_keys_manager: ApiKeyManager):
        self.sa_session = sa_session
        self.api_keys_manager = api_keys_manager

    def get_app_name(self, client_id: str) -> str:
        """Return the display name of a known app, or raise if the client ID is not known."""
        name = KNOWN_APPS.get(client_id)
        if name is None:
            raise OAuthError(OAuthErrorCode.INVALID_CLIENT, f"Unknown client_id '{client_id}'.")
        return name

    def start_authorization(self, client_id: str, scope: str | None, requesting_ip: str | None) -> StartedAuthorization:
        """Record a new pending device login for a known app."""
        self.get_app_name(client_id)
        # TODO: Once scoped tokens exist, check each requested scope is a known one and raise
        #       `OAuthErrorCode.INVALID_SCOPE` if not.
        device_code = secrets.token_urlsafe(32)
        authorization = OAuthDeviceAuthorization(
            device_code_hash=hash_device_code(device_code),
            user_code=self._unused_user_code(),
            client_id=client_id,
            scope=scope,
            requesting_ip=requesting_ip,
            expires_at=now() + timedelta(seconds=DEVICE_CODE_EXPIRES_IN),
        )
        self.sa_session.add(authorization)
        self.sa_session.commit()
        return StartedAuthorization(authorization=authorization, device_code=device_code)

    def decide(self, user_code: str, user: model.User, approve: bool) -> None:
        """Record a user's approval or denial of a pending device login."""
        authorization = self.get_pending(user_code)
        statuses = OAuthDeviceAuthorization.statuses
        # Only a still-pending row is changed, so two answers at once can't overwrite each other.
        stmt = (
            update(OAuthDeviceAuthorization)
            .where(OAuthDeviceAuthorization.id == authorization.id, OAuthDeviceAuthorization.status == statuses.PENDING)
            .values(status=statuses.APPROVED if approve else statuses.DENIED, user_id=user.id)
            .returning(OAuthDeviceAuthorization.id)
        )
        decided_id = self.sa_session.scalar(stmt)
        self.sa_session.commit()
        if decided_id is None:
            raise Conflict("This code has already been used.", reason="used")

    def get_pending(self, user_code: str) -> OAuthDeviceAuthorization:
        """Return the device login for a user code, if it can still be approved or denied.

        Errors carry a `reason` (`unknown`, `expired` or `used`) so the verification page can tell them apart.
        """
        stmt = select(OAuthDeviceAuthorization).where(
            OAuthDeviceAuthorization.user_code == normalize_user_code(user_code)
        )
        authorization = self.sa_session.scalars(stmt).first()
        if authorization is None:
            raise ObjectNotFound(
                "No login request found for this code. Check the code in your terminal.", reason="unknown"
            )
        if authorization.expires_at <= now():
            raise Conflict("This code has expired. Start the login again from your terminal.", reason="expired")
        if authorization.status != OAuthDeviceAuthorization.statuses.PENDING:
            raise Conflict("This code has already been used.", reason="used")
        return authorization

    def respond_to_poll(self, client_id: str, device_code: str) -> IssuedToken:
        """Respond to an app's poll for a device login, returning a token once the user has approved it.

        Raises the RFC 8628 §3.5 errors until then. A device code gets at most one token.
        """
        self.get_app_name(client_id)
        statuses = OAuthDeviceAuthorization.statuses
        stmt = select(OAuthDeviceAuthorization).where(
            OAuthDeviceAuthorization.device_code_hash == hash_device_code(device_code)
        )
        authorization = self.sa_session.scalars(stmt).first()
        if authorization is None or authorization.client_id != client_id or authorization.status == statuses.USED:
            raise OAuthError(OAuthErrorCode.INVALID_GRANT, "Unknown or already used device_code.")
        if authorization.expires_at <= now():
            raise OAuthError(OAuthErrorCode.EXPIRED_TOKEN, "The device_code has expired.")

        last_polled_at = authorization.last_polled_at
        authorization.last_polled_at = now()
        self.sa_session.commit()
        if last_polled_at and authorization.last_polled_at - last_polled_at < timedelta(seconds=POLLING_INTERVAL):
            raise OAuthError(OAuthErrorCode.SLOW_DOWN, f"Wait at least {POLLING_INTERVAL} seconds between requests.")
        if authorization.status == statuses.PENDING:
            raise OAuthError(OAuthErrorCode.AUTHORIZATION_PENDING, "The user has not approved the login yet.")
        if authorization.status == statuses.DENIED:
            raise OAuthError(OAuthErrorCode.ACCESS_DENIED, "The user denied the login.")

        # Only the request that moves the row from approved to used gets the token, even if two arrive at once.
        mark_used = (
            update(OAuthDeviceAuthorization)
            .where(
                OAuthDeviceAuthorization.id == authorization.id, OAuthDeviceAuthorization.status == statuses.APPROVED
            )
            .values(status=statuses.USED)
            .returning(OAuthDeviceAuthorization.id)
        )
        marked_id = self.sa_session.scalar(mark_used)
        self.sa_session.commit()
        if marked_id is None:
            raise OAuthError(OAuthErrorCode.INVALID_GRANT, "Unknown or already used device_code.")
        assert authorization.user, "An approved device login always has a user."
        return self.issue_token(authorization.user, client_id, authorization.scope)

    def issue_token(self, user: model.User, client_id: str, scope: str | None) -> IssuedToken:
        """Issue a token for a user who approved a device flow login.

        TODO: Placeholder until scoped, expiring tokens exist. For now, returns the user's API
              key, which ignores the scope and never expires. Must not ship as is.
        """
        return IssuedToken(
            access_token=self.api_keys_manager.get_or_create_api_key(user),
            expires_in=None,
            scope=scope,
        )

    def _unused_user_code(self) -> str:
        # A clash is very unlikely (20^8 codes), but user codes must be unique.
        while True:
            user_code = generate_user_code()
            stmt = select(exists().where(OAuthDeviceAuthorization.user_code == user_code))
            if not self.sa_session.scalar(stmt):
                return user_code
