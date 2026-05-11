"""User-self-registered Pulsar compute resources ("Bring Your Own Compute").

This module exposes :class:`PulsarByocManager`, which Galaxy hangs on the
``UniverseApplication`` as ``app.byoc_manager`` so TPV rules can resolve the
acting user's active BYOC resource at job dispatch time via
``app.byoc_manager.get_active_for(user)``.
"""

from __future__ import annotations

import logging
import secrets
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import Optional

import jwt
from sqlalchemy import (
    delete,
    func,
    select,
)

from pulsar_relay_client import (
    default_relay_client_factory,
    RefreshTokenRejectedError,
    RelayClient,
    RelayClientError,
    RelayClientFactory,
    TopicOwnershipConflictError,
)
from galaxy.model import (
    Job,
    PulsarByocBootstrapToken,
    PulsarByocResource,
    User,
)
from galaxy.security.vault import (
    UserVaultWrapper,
    Vault,
)
from galaxy.structured_app import BasicSharedApp

log = logging.getLogger(__name__)

#: Status values for ``PulsarByocResource.status``. The schema stores a free-form
#: string; lifecycle is enforced by this manager.
STATUS_PENDING = "pending"
STATUS_ACTIVE = "active"
STATUS_DISABLED = "disabled"
STATUS_DELETED = "deleted"

#: TTL for bootstrap tokens. Long enough for a user to switch terminals and
#: paste the one-liner; short enough that a leaked token isn't useful.
BOOTSTRAP_TOKEN_TTL = timedelta(minutes=15)

#: Rate limit on ``start_registration``: cap each user at this many tokens
#: minted in a rolling hour. Mostly to keep abusive callers from filling the
#: bootstrap-token table; the tokens are single-use, so the cap doesn't
#: meaningfully restrict good-faith retries.
RATE_LIMIT_PER_HOUR = 5
RATE_LIMIT_WINDOW = timedelta(hours=1)

#: Pulsar subscribes to ``{prefix}_{manager_name}`` for each of these
#: three topic prefixes — the wire contract between Galaxy (publisher,
#: of job_setup / job_kill) and the user's Pulsar daemon (publisher of
#: job_status_update; consumer of the other two).
BYOC_TOPIC_PREFIXES = ("job_setup", "job_kill", "job_status_update")


class PulsarByocError(Exception):
    """Domain errors that the API layer can translate into HTTP status codes."""


class BootstrapTokenInvalid(PulsarByocError):
    """The supplied bootstrap_token does not match any unredeemed ticket."""


class BootstrapTokenExpired(PulsarByocError):
    """The supplied bootstrap_token has aged past its TTL."""


class RelayVerificationFailed(PulsarByocError):
    """The relay rejected the supplied refresh token, or its access token's
    ``sub`` claim does not match ``manager_name``."""


class RegistrationRateLimited(PulsarByocError):
    """User has exceeded the per-hour rate limit on start_registration."""


class ResourceHasRunningJobs(PulsarByocError):
    """A purge was attempted on a resource that still has non-terminal jobs."""


class PulsarByocManager:
    def __init__(
        self,
        app: BasicSharedApp,
        *,
        vault: Optional[Vault] = None,
        relay_client_factory: Optional[RelayClientFactory] = None,
    ) -> None:
        """Galaxy DI entry point. ``vault`` and ``relay_client_factory`` default
        to the app-bound vault and a real-HTTP factory; tests pass fakes."""
        self.app = app
        self.session = app.model.context
        # ``BasicSharedApp`` is the broadest contract we can declare and still
        # satisfy the manager's needs; the live app object (``UniverseApplication``)
        # always carries ``vault`` so the fall-through here is sound at runtime.
        self._vault: Vault = vault if vault is not None else app.vault  # type: ignore[attr-defined]
        self._relay_client_factory: RelayClientFactory = (
            relay_client_factory if relay_client_factory is not None else default_relay_client_factory
        )

    # ---- query ------------------------------------------------------------

    def get_active_for(self, user: Optional[User]) -> Optional[PulsarByocResource]:
        """Return the user's single active BYOC resource, or ``None``.

        Anonymous callers (``user is None``) always get ``None`` so TPV rules can
        unconditionally reference ``app.byoc_manager.get_active_for(user)``
        without guarding for the anonymous case.
        """
        if user is None:
            return None
        stmt = select(PulsarByocResource).where(
            PulsarByocResource.user_id == user.id,
            PulsarByocResource.status == STATUS_ACTIVE,
        )
        return self.session.scalars(stmt).first()

    def list_for(self, user: Optional[User]) -> list[PulsarByocResource]:
        if user is None:
            return []
        stmt = (
            select(PulsarByocResource)
            .where(PulsarByocResource.user_id == user.id)
            .where(PulsarByocResource.status != STATUS_DELETED)
            .order_by(PulsarByocResource.create_time.desc())
        )
        return list(self.session.scalars(stmt).all())

    def get_for_user(self, user: Optional[User], resource_id: int) -> Optional[PulsarByocResource]:
        """Look up a resource that belongs to ``user``. Returns ``None`` for
        cross-user lookups so the API can 404 without leaking existence."""
        if user is None:
            return None
        stmt = select(PulsarByocResource).where(
            PulsarByocResource.id == resource_id,
            PulsarByocResource.user_id == user.id,
        )
        return self.session.scalars(stmt).first()

    # ---- registration: start ---------------------------------------------

    def start_registration(self, user: User) -> PulsarByocBootstrapToken:
        """Mint a short-lived single-use bootstrap token.

        The returned row's ``token`` is the opaque secret the user passes to
        ``pulsar-config register-with-galaxy``; the row is deleted on
        successful redemption (or aged out by ``complete_registration``).

        Reaps any of this user's expired tokens inline, then enforces a
        rolling-hour rate limit of :data:`RATE_LIMIT_PER_HOUR` mints —
        cheap (single user-scoped count query) and avoids needing a
        background reaper for v1.
        """
        now_naive = datetime.now(tz=timezone.utc).replace(tzinfo=None)

        # Reap this user's expired bootstrap tokens. Bounded by their own
        # rate limit so the delete is small.
        self.session.execute(
            delete(PulsarByocBootstrapToken).where(
                PulsarByocBootstrapToken.user_id == user.id,
                PulsarByocBootstrapToken.expiration_time < now_naive,
            )
        )

        window_start = now_naive - RATE_LIMIT_WINDOW
        recent_count = (
            self.session.scalar(
                select(func.count(PulsarByocBootstrapToken.id)).where(
                    PulsarByocBootstrapToken.user_id == user.id,
                    PulsarByocBootstrapToken.create_time >= window_start,
                )
            )
            or 0
        )
        if recent_count >= RATE_LIMIT_PER_HOUR:
            self.session.commit()  # persist the reap even when we refuse
            raise RegistrationRateLimited(
                f"User has minted {recent_count} bootstrap tokens in the last "
                f"{int(RATE_LIMIT_WINDOW.total_seconds() / 60)} minutes "
                f"(limit: {RATE_LIMIT_PER_HOUR})."
            )

        token_value = secrets.token_urlsafe(48)
        row = PulsarByocBootstrapToken(
            token=token_value,
            user_id=user.id,
            expiration_time=now_naive + BOOTSTRAP_TOKEN_TTL,
        )
        self.session.add(row)
        self.session.commit()
        return row

    # ---- registration: complete ------------------------------------------

    def _relay_client(self, relay_url: str) -> RelayClient:
        """Build a :class:`RelayClient` for a given relay base URL.

        Indirection so tests can inject a fake factory at ``__init__`` time
        without touching the production HTTP code.
        """
        return self._relay_client_factory(relay_url)

    @staticmethod
    def _decode_sub(access_token: str) -> Optional[str]:
        """Pull ``sub`` out of a relay-issued access token.

        Signature verification is skipped because the relay has already
        validated the token before issuing it — we only need to learn which
        relay user it represents.
        """
        try:
            claims = jwt.decode(
                access_token,
                options={"verify_signature": False, "verify_aud": False},
            )
        except jwt.PyJWTError as exc:
            log.warning("Failed to decode relay access token: %s", exc)
            return None
        return claims.get("sub")

    def _redeem_bootstrap_token(self, token_value: str) -> PulsarByocBootstrapToken:
        # ``token`` is the unique-indexed secret column, not the PK — look it up
        # via select() rather than session.get().
        row = self.session.scalars(
            select(PulsarByocBootstrapToken).where(PulsarByocBootstrapToken.token == token_value)
        ).first()
        if row is None:
            raise BootstrapTokenInvalid("unknown bootstrap_token")
        now_naive = datetime.now(tz=timezone.utc).replace(tzinfo=None)
        if row.expiration_time < now_naive:
            self.session.delete(row)
            self.session.commit()
            raise BootstrapTokenExpired("bootstrap_token has expired")
        # Consume immediately — tokens are single-use even if downstream
        # steps fail. The user retries via ``start_registration``.
        self.session.delete(row)
        self.session.commit()
        return row

    def complete_registration(
        self,
        bootstrap_token: str,
        refresh_token: str,
        relay_url: str,
        manager_name: str,
        relay_topic_prefix: Optional[str] = None,
    ) -> PulsarByocResource:
        """Redeem a bootstrap token and persist a BYOC resource for that user.

        Validates the supplied ``refresh_token`` by round-tripping it through
        the relay's ``/auth/token/refresh`` — this both proves the token is
        live *and* yields the rotated token that we actually store in vault.
        Asserts ``sub == manager_name`` so a user can't redirect another
        relay user's topics into their Galaxy account.

        Replaces any existing ``active`` resource the user has (disables it)
        and returns the new ``active`` row.
        """
        ticket = self._redeem_bootstrap_token(bootstrap_token)
        user = self.session.get(User, ticket.user_id)
        if user is None:
            raise PulsarByocError("bootstrap_token references a missing user")

        client = self._relay_client(relay_url)
        try:
            body = client.exchange_refresh_token(refresh_token)
        except RefreshTokenRejectedError as exc:
            raise RelayVerificationFailed(str(exc)) from exc
        except RelayClientError as exc:
            raise RelayVerificationFailed(str(exc)) from exc

        rotated_refresh_token = body.get("refresh_token") or refresh_token
        access_token = body.get("access_token")
        if not access_token:
            raise RelayVerificationFailed("relay response missing access_token")
        sub = self._decode_sub(access_token)
        if sub is None:
            raise RelayVerificationFailed("relay access token has no sub claim")
        if sub != manager_name:
            raise RelayVerificationFailed(
                f"refresh_token's sub claim {sub!r} does not match manager_name {manager_name!r}"
            )

        # Pin the three BYOC topics for this manager to the BYOC user's
        # ownership before we commit anything to our own DB / vault. Any
        # later failure (DB, vault) cleans up cleanly because the rotated
        # refresh token can simply be re-exchanged later.
        try:
            for prefix in BYOC_TOPIC_PREFIXES:
                client.create_or_verify_topic(access_token, f"{prefix}_{manager_name}")
        except TopicOwnershipConflictError as exc:
            raise RelayVerificationFailed(str(exc)) from exc
        except RelayClientError as exc:
            raise RelayVerificationFailed(str(exc)) from exc

        # Disable any existing active row for this user — the invariant is
        # "at most one active BYOC per user". Running jobs continue to drain
        # on their existing client manager (which we don't tear down here).
        existing = self.get_active_for(user)
        if existing is not None:
            existing.status = STATUS_DISABLED
            self.session.add(existing)

        resource = PulsarByocResource(
            user_id=user.id,
            manager_name=manager_name,
            relay_url=relay_url,
            relay_topic_prefix=relay_topic_prefix,
            status=STATUS_PENDING,
        )
        self.session.add(resource)
        self.session.commit()  # flush so resource.id is populated

        UserVaultWrapper(self._vault, user).write_secret(
            f"pulsar_byoc/{resource.id}/relay_refresh_token", rotated_refresh_token
        )

        resource.status = STATUS_ACTIVE
        self.session.add(resource)
        self.session.commit()
        return resource

    # ---- delete -----------------------------------------------------------

    def delete(self, user: Optional[User], resource_id: int) -> Optional[PulsarByocResource]:
        """Soft-delete a resource. Running jobs continue to drain through the
        runner's still-cached client manager; new jobs no longer route here
        because TPV's ``get_active_for`` skips disabled rows."""
        resource = self.get_for_user(user, resource_id)
        if resource is None:
            return None
        if resource.status not in (STATUS_DELETED,):
            resource.status = STATUS_DISABLED
            self.session.add(resource)
            self.session.commit()
        return resource

    # ---- purge ------------------------------------------------------------

    def _has_running_jobs(self, user: User, resource_id: int) -> bool:
        """True if any non-terminal Job is bound to this BYOC resource.

        We don't have a denormalised FK from Job to PulsarByocResource (the
        binding lives inside ``destination_params``), so we fetch the user's
        non-terminal pulsar_byoc jobs and Python-filter. Safe because BYOC is
        owner-only — the candidate set is small.
        """
        stmt = (
            select(Job)
            .where(Job.user_id == user.id)
            .where(Job.state.in_(Job.non_ready_states))
            .where(Job.job_runner_name == "pulsar_byoc")
        )
        for job in self.session.scalars(stmt):
            params = job.destination_params or {}
            raw = params.get("pulsar_byoc_resource_id")
            if raw is None:
                continue
            try:
                bound_to = int(raw)
            except (TypeError, ValueError):
                continue
            if bound_to == resource_id:
                return True
        return False

    def purge(self, user: Optional[User], resource_id: int) -> Optional[PulsarByocResource]:
        """Fully delete a resource: clears the vault secret and transitions
        status to ``deleted``.

        Refuses to purge while non-terminal jobs reference this resource —
        in-flight jobs need the vault token to drain on the lazy-cached
        client manager; clearing it mid-drain would orphan them. Soft-delete
        first via :meth:`delete`, wait for drain, then purge.
        """
        resource = self.get_for_user(user, resource_id)
        if resource is None:
            return None
        # ``get_for_user`` returns None for anonymous callers so ``user`` is
        # narrowed to a real ``User`` from this point on.
        assert user is not None
        if resource.status == STATUS_DELETED:
            return resource
        if self._has_running_jobs(user, resource_id):
            raise ResourceHasRunningJobs(
                f"Resource id={resource_id} still has non-terminal jobs; wait for them to drain before purging."
            )

        # Vault wrapper namespaces under the user — clearing the secret here
        # is safe because the resource is owner-scoped.
        try:
            UserVaultWrapper(self._vault, user).write_secret(f"pulsar_byoc/{resource_id}/relay_refresh_token", "")
        except Exception:
            log.exception("Failed to clear vault secret for BYOC resource %s", resource_id)
            # Continue: the row is still going to ``deleted``; an orphaned
            # vault entry is a leak, not a correctness issue, and the
            # admin can clean it up if needed.

        resource.status = STATUS_DELETED
        self.session.add(resource)
        self.session.commit()
        return resource
