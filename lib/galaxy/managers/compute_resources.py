"""User-self-registered compute resources.

This module exposes :class:`ComputeResourceManager`, registered as a Lagom
singleton and reachable on the live Galaxy app as
``app.compute_resource_manager`` so TPV rules can resolve the acting
user's active compute resource at job dispatch time via
``app.compute_resource_manager.get_active_for(user)``.

Dependencies (session, vault, config) are injected directly via Lagom
rather than reached for through ``app.*``.
"""

from __future__ import annotations

import logging
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from typing import (
    Any,
    Optional,
)

import jwt
from pulsar_relay_client import (
    default_relay_client_factory,
    RefreshTokenRejectedError,
    RelayClient,
    RelayClientError,
    RelayClientFactory,
    TopicOwnershipConflictError,
)
from sqlalchemy import (
    delete,
    func,
    select,
)

from galaxy.config import GalaxyAppConfiguration
from galaxy.model import (
    ComputeResource,
    ComputeResourceRegistration,
    Job,
    User,
)
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.security.vault import (
    UserVaultWrapper,
    Vault,
)

log = logging.getLogger(__name__)

#: Status values for ``ComputeResource.status``. The schema stores a free-form
#: string; lifecycle is enforced by this manager.
STATUS_PENDING = "pending"
STATUS_ACTIVE = "active"
STATUS_DISABLED = "disabled"
STATUS_DELETED = "deleted"

#: Runner id (``Job.job_runner_name``) used when a job is dispatched to a
#: compute resource. Must match the ``id`` an operator gives the
#: :class:`PulsarMQBYOCJobRunner` in ``job_conf.yml``; the sample config
#: ships with this identifier.
COMPUTE_RESOURCE_RUNNER_ID = "compute_resource"

#: Destination-param key the TPV rule injects to bind a job to a specific
#: compute-resource row. The runner reads this to look the resource up
#: (and to filter non-terminal jobs in :meth:`ComputeResourceManager.purge`).
COMPUTE_RESOURCE_ID_PARAM = "compute_resource_id"

#: TTL for registration tokens. Long enough for a user to switch terminals
#: and paste the one-liner; short enough that a leaked token isn't useful.
REGISTRATION_TOKEN_TTL = timedelta(minutes=15)

#: Rate limit on ``start_registration``: cap each user at this many tokens
#: minted in a rolling hour. Mostly to keep abusive callers from filling
#: the registration-token table; the tokens are single-use, so the cap
#: doesn't meaningfully restrict good-faith retries.
RATE_LIMIT_PER_HOUR = 5
RATE_LIMIT_WINDOW = timedelta(hours=1)

#: Pulsar subscribes to ``{prefix}_{manager_name}`` for each of these
#: three topic prefixes — the wire contract between Galaxy (publisher,
#: of job_setup / job_kill) and the user's Pulsar daemon (publisher of
#: job_status_update; consumer of the other two).
RELAY_TOPIC_PREFIXES = ("job_setup", "job_kill", "job_status_update")

#: Topic stem Pulsar publishes its capability snapshot to (post-namespace,
#: per the publisher's `__make_capabilities_topic_name` convention in
#: pulsar/messaging/bind_relay.py). The full topic on the wire is
#: ``[<topic_prefix>_]pulsar_capabilities[_<manager>]`` — see
#: :func:`_make_capabilities_topic_name` below.
CAPABILITIES_TOPIC_STEM = "pulsar_capabilities"

#: Schema versions this Galaxy understands for the capability snapshot.
#: Unknown versions are dropped with a one-time warning so the runner
#: falls back to operator-supplied params.
SUPPORTED_CAPABILITIES_SCHEMA_VERSIONS = frozenset({1})

#: Default TTL for the in-memory capability cache. Short enough that an
#: admin restart of pulsar (with a new container runtime added) is picked
#: up within a minute; long enough that a burst of N jobs to one
#: destination triggers at most one fetch.
CAPABILITIES_CACHE_TTL_SECONDS = 60.0


def relay_refresh_token_vault_path(resource_id: int) -> str:
    """Vault path under which the relay refresh token for a compute resource lives.

    Centralised so the manager (writer + capability fetcher) and the
    pulsar runner (reader + rotation persister) cannot drift apart on the
    layout.
    """
    return f"compute_resource/{resource_id}/relay_refresh_token"


def _make_capabilities_topic_name(prefix: Optional[str], manager_name: str) -> str:
    """Mirror of pulsar/messaging/bind_relay.py:__make_capabilities_topic_name.

    Examples:
        ('', '_default_')      -> 'pulsar_capabilities'
        ('', 'cluster_a')      -> 'pulsar_capabilities_cluster_a'
        ('prod', '_default_')  -> 'prod_pulsar_capabilities'
        ('prod', 'cluster_a')  -> 'prod_pulsar_capabilities_cluster_a'
    """
    parts: list[str] = []
    if prefix:
        parts.append(prefix)
    parts.append(CAPABILITIES_TOPIC_STEM)
    if manager_name != "_default_":
        parts.append(manager_name)
    return "_".join(parts)


class RelayCapabilitiesCache:
    """In-memory TTL cache of capability snapshots, keyed by
    ``(relay_url, manager_name)``.

    The caller supplies a ``fetch`` callable on :meth:`get`; we invoke
    it only on cache miss/expiry. This lets the caller defer expensive
    setup (refresh-token exchange, access-token mint) to the moment a
    fetch is actually required, and lets the cache stay agnostic to
    *how* a snapshot is obtained — useful for tests too.

    ``None`` results are cached: a flapping relay or a pulsar that
    isn't publishing snapshots yet shouldn't trigger an HTTP fetch on
    every job. Validation (empty messages, missing payload, unknown
    ``schema_version``) lives in :meth:`extract_payload`, which the
    caller's fetch closure typically wraps around its HTTP call.
    """

    def __init__(
        self,
        ttl_seconds: float = CAPABILITIES_CACHE_TTL_SECONDS,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._entries: dict[tuple[str, str], tuple[Optional[dict[str, Any]], float]] = {}

    def get(
        self,
        relay_url: str,
        manager_name: str,
        fetch: Callable[[], Optional[dict[str, Any]]],
    ) -> Optional[dict[str, Any]]:
        key = (relay_url, manager_name)
        now = self._clock()
        with self._lock:
            cached = self._entries.get(key)
            if cached is not None and now - cached[1] < self._ttl:
                return cached[0]
        # Defer the I/O outside the lock: a slow fetch shouldn't block
        # other tenants. The trade-off is that two concurrent misses on
        # the same key both run their fetches; harmless because the
        # last-writer-wins on the dict and both call paths are
        # idempotent.
        snapshot = fetch()
        with self._lock:
            self._entries[key] = (snapshot, self._clock())
        return snapshot

    def invalidate(self, relay_url: str, manager_name: str) -> None:
        with self._lock:
            self._entries.pop((relay_url, manager_name), None)


def extract_capability_payload(response: dict[str, Any], topic: str, relay_url: str) -> Optional[dict[str, Any]]:
    """Pull the latest payload out of a ``PaginatedMessagesResponse`` body.

    Validates: at least one message, payload is a dict, ``schema_version``
    is one we understand. Logs a warning on rejection but never raises —
    the caller treats ``None`` as "no snapshot, trust operator params".
    """
    messages = response.get("messages") or []
    if not messages:
        log.debug("Capability topic %s on %s is empty (no snapshot published yet).", topic, relay_url)
        return None
    payload = messages[0].get("payload")
    if not isinstance(payload, dict):
        log.warning(
            "Capability message on %s has non-dict payload (got %s); ignoring.",
            topic,
            type(payload).__name__,
        )
        return None
    version = payload.get("schema_version")
    if version not in SUPPORTED_CAPABILITIES_SCHEMA_VERSIONS:
        log.warning(
            "Capability snapshot on %s has unsupported schema_version=%r (supported: %s); "
            "ignoring. Update Galaxy to consume newer snapshots.",
            topic,
            version,
            sorted(SUPPORTED_CAPABILITIES_SCHEMA_VERSIONS),
        )
        return None
    return payload


@dataclass(frozen=True)
class RegistrationTicketData:
    """Data the service hands to the user after :meth:`ComputeResourceManager.start_registration`.

    Holds the registration token plus the registration-command artifacts
    (configured relay URL + one-liner the user pastes) so the service layer
    is pure schema-mapping.
    """

    bootstrap_token: str
    expires_at: datetime
    relay_url: str
    one_liner: str


class ComputeResourceError(Exception):
    """Domain errors that the API layer can translate into HTTP status codes."""


class RegistrationTokenInvalid(ComputeResourceError):
    """The supplied bootstrap_token does not match any unredeemed ticket."""


class RegistrationTokenExpired(ComputeResourceError):
    """The supplied bootstrap_token has aged past its TTL."""


class RelayVerificationFailed(ComputeResourceError):
    """The relay rejected the supplied refresh token, or its access token's
    ``sub`` claim does not match ``manager_name``."""


class RegistrationRateLimited(ComputeResourceError):
    """User has exceeded the per-hour rate limit on start_registration."""


class ResourceHasRunningJobs(ComputeResourceError):
    """A purge was attempted on a resource that still has non-terminal jobs."""


class ComputeResourceManager:
    def __init__(
        self,
        session: galaxy_scoped_session,
        vault: Vault,
        config: GalaxyAppConfiguration,
        *,
        relay_client_factory: Optional[RelayClientFactory] = None,
        capabilities_cache: Optional[RelayCapabilitiesCache] = None,
    ) -> None:
        """Galaxy DI entry point.

        Dependencies are injected directly (Lagom resolves them by type)
        rather than reaching into ``app.*``. ``relay_client_factory`` and
        ``capabilities_cache`` are test seams.
        """
        self.session = session
        self._vault = vault
        self._config = config
        self._relay_client_factory: RelayClientFactory = (
            relay_client_factory if relay_client_factory is not None else default_relay_client_factory
        )
        self._capabilities_cache = capabilities_cache if capabilities_cache is not None else RelayCapabilitiesCache()

    # ---- query ------------------------------------------------------------

    def get_active_for(self, user: Optional[User]) -> Optional[ComputeResource]:
        """Return the user's single active compute resource, or ``None``.

        Anonymous callers (``user is None``) always get ``None`` so TPV rules can
        unconditionally reference ``app.compute_resource_manager.get_active_for(user)``
        without guarding for the anonymous case.
        """
        if user is None:
            return None
        stmt = select(ComputeResource).where(
            ComputeResource.user_id == user.id,
            ComputeResource.status == STATUS_ACTIVE,
        )
        return self.session.scalars(stmt).first()

    def list_for(self, user: Optional[User]) -> list[ComputeResource]:
        if user is None:
            return []
        stmt = (
            select(ComputeResource)
            .where(ComputeResource.user_id == user.id)
            .where(ComputeResource.status != STATUS_DELETED)
            .order_by(ComputeResource.create_time.desc())
        )
        return list(self.session.scalars(stmt).all())

    def get_for_user(self, user: Optional[User], resource_id: int) -> Optional[ComputeResource]:
        """Look up a resource that belongs to ``user``. Returns ``None`` for
        cross-user lookups so the API can 404 without leaking existence."""
        if user is None:
            return None
        stmt = select(ComputeResource).where(
            ComputeResource.id == resource_id,
            ComputeResource.user_id == user.id,
        )
        return self.session.scalars(stmt).first()

    # ---- capability snapshot ---------------------------------------------

    def capabilities_for(self, resource: ComputeResource, *, user: Optional[User]) -> Optional[dict[str, Any]]:
        """Return the latest capability snapshot for a compute resource, or ``None``.

        Most calls are a dict lookup against
        :class:`RelayCapabilitiesCache`; the closure that does the
        refresh-token exchange + ``HttpRelayClient.fetch_messages`` runs
        only on cache miss. Rotated refresh tokens are persisted back
        to vault so the runner's separately-cached client manager sees
        them on its next refresh.

        ``None`` means the snapshot is not available — older pulsar
        version, network glitch, schema mismatch, or no vault token.
        Callers treat ``None`` as "trust operator-supplied params" and
        skip downgrades.
        """
        if user is None:
            return None
        topic = _make_capabilities_topic_name(resource.relay_topic_prefix, resource.manager_name)
        return self._capabilities_cache.get(
            resource.relay_url,
            resource.manager_name,
            lambda: self._fetch_capabilities(resource, user, topic),
        )

    def _fetch_capabilities(self, resource: ComputeResource, user: User, topic: str) -> Optional[dict[str, Any]]:
        vault_wrapper = UserVaultWrapper(self._vault, user)
        secret_path = relay_refresh_token_vault_path(resource.id)
        refresh_token = vault_wrapper.read_secret(secret_path)
        if not refresh_token:
            log.debug(
                "No relay refresh token in vault for ComputeResource id=%s; cannot fetch capabilities.",
                resource.id,
            )
            return None

        client = self._relay_client(resource.relay_url)
        try:
            body = client.exchange_refresh_token(refresh_token)
        except (RefreshTokenRejectedError, RelayClientError) as exc:
            log.warning(
                "Relay refresh failed while fetching capabilities for resource id=%s: %s",
                resource.id,
                exc,
            )
            return None

        rotated = body.get("refresh_token")
        if rotated and rotated != refresh_token:
            # Persist the rotation so the runner's next exchange sees it
            # — same vault key the runner reads from.
            vault_wrapper.write_secret(secret_path, rotated)
        access_token = body.get("access_token")
        if not access_token:
            log.warning(
                "Relay refresh response missing access_token for resource id=%s.",
                resource.id,
            )
            return None

        try:
            response = client.fetch_messages(access_token, topic, limit=1, order="desc")
        except RelayClientError as exc:
            log.warning(
                "Capability fetch from %s on %s failed: %s",
                topic,
                resource.relay_url,
                exc,
            )
            return None
        return extract_capability_payload(response, topic, resource.relay_url)

    # ---- registration: start ---------------------------------------------

    def start_registration(self, user: User) -> RegistrationTicketData:
        """Mint a short-lived single-use registration token and return the
        registration ticket the user needs.

        The returned ``bootstrap_token`` is the opaque secret the user passes
        to ``pulsar-config register-with-galaxy``; the underlying row is
        deleted on successful redemption (or aged out by
        :meth:`complete_registration`).

        Reaps any of this user's expired tokens inline, then enforces a
        rolling-hour rate limit of :data:`RATE_LIMIT_PER_HOUR` mints —
        cheap (single user-scoped count query) and avoids needing a
        background reaper for v1.
        """
        now_naive = datetime.now(tz=timezone.utc).replace(tzinfo=None)

        # Reap this user's expired registration tokens. Bounded by their own
        # rate limit so the delete is small.
        self.session.execute(
            delete(ComputeResourceRegistration).where(
                ComputeResourceRegistration.user_id == user.id,
                ComputeResourceRegistration.expiration_time < now_naive,
            )
        )

        window_start = now_naive - RATE_LIMIT_WINDOW
        recent_count = (
            self.session.scalar(
                select(func.count(ComputeResourceRegistration.id)).where(
                    ComputeResourceRegistration.user_id == user.id,
                    ComputeResourceRegistration.create_time >= window_start,
                )
            )
            or 0
        )
        if recent_count >= RATE_LIMIT_PER_HOUR:
            # Persist the reap even when we refuse so a hot-looping client
            # doesn't keep regrowing the table between every refusal.
            self.session.commit()
            raise RegistrationRateLimited(
                f"User has minted {recent_count} registration tokens in the last "
                f"{int(RATE_LIMIT_WINDOW.total_seconds() / 60)} minutes "
                f"(limit: {RATE_LIMIT_PER_HOUR})."
            )

        token_value = secrets.token_urlsafe(48)
        row = ComputeResourceRegistration(
            token=token_value,
            user_id=user.id,
            expiration_time=now_naive + REGISTRATION_TOKEN_TTL,
        )
        self.session.add(row)
        self.session.commit()

        galaxy_url = self._config.galaxy_infrastructure_url or ""
        relay_url = self._config.compute_resource_relay_url or ""
        one_liner = f"pulsar-config register-with-galaxy --galaxy {galaxy_url} --token {row.token} --relay {relay_url}"
        return RegistrationTicketData(
            bootstrap_token=row.token,
            expires_at=row.expiration_time,
            relay_url=relay_url,
            one_liner=one_liner,
        )

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

    def _redeem_registration_token(self, token_value: str) -> ComputeResourceRegistration:
        # ``token`` is the unique-indexed secret column, not the PK — look it up
        # via select() rather than session.get().
        row = self.session.scalars(
            select(ComputeResourceRegistration).where(ComputeResourceRegistration.token == token_value)
        ).first()
        if row is None:
            raise RegistrationTokenInvalid("unknown bootstrap_token")
        now_naive = datetime.now(tz=timezone.utc).replace(tzinfo=None)
        if row.expiration_time < now_naive:
            self.session.delete(row)
            self.session.commit()
            raise RegistrationTokenExpired("bootstrap_token has expired")
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
    ) -> ComputeResource:
        """Redeem a registration token and persist a compute resource for that user.

        Validates the supplied ``refresh_token`` by round-tripping it through
        the relay's ``/auth/token/refresh`` — this both proves the token is
        live *and* yields the rotated token that we actually store in vault.
        Asserts ``sub == manager_name`` so a user can't redirect another
        relay user's topics into their Galaxy account.

        If the admin has pinned a relay URL via ``compute_resource_relay_url``,
        refuse any other ``relay_url`` — otherwise a user could bind their
        resource to an attacker-controlled relay.

        Replaces any existing ``active`` resource the user has (disables it)
        and returns the new ``active`` row.
        """
        configured_relay = self._config.compute_resource_relay_url
        if configured_relay and relay_url != configured_relay:
            raise RelayVerificationFailed(
                f"relay_url {relay_url!r} does not match configured compute_resource_relay_url"
            )

        ticket = self._redeem_registration_token(bootstrap_token)
        user = self.session.get(User, ticket.user_id)
        if user is None:
            raise ComputeResourceError("bootstrap_token references a missing user")

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

        # Pin the three job topics for this manager to the BYOC user's
        # ownership before we commit anything to our own DB / vault. Any
        # later failure (DB, vault) cleans up cleanly because the rotated
        # refresh token can simply be re-exchanged later.
        try:
            for prefix in RELAY_TOPIC_PREFIXES:
                client.create_or_verify_topic(access_token, f"{prefix}_{manager_name}")
        except TopicOwnershipConflictError as exc:
            raise RelayVerificationFailed(str(exc)) from exc
        except RelayClientError as exc:
            raise RelayVerificationFailed(str(exc)) from exc

        # Disable any existing active row for this user — the invariant is
        # "at most one active compute resource per user". Running jobs continue
        # to drain on their existing client manager (which we don't tear down here).
        existing = self.get_active_for(user)
        if existing is not None:
            existing.status = STATUS_DISABLED
            self.session.add(existing)

        resource = ComputeResource(
            user_id=user.id,
            manager_name=manager_name,
            relay_url=relay_url,
            relay_topic_prefix=relay_topic_prefix,
            status=STATUS_ACTIVE,
        )
        self.session.add(resource)
        # flush() (not commit()) so resource.id is populated for the vault
        # path. The vault write below and the commit are paired: if either
        # raises, the transaction rolls back and nothing is persisted —
        # closing the prior pending-row-without-vault-secret leak.
        self.session.flush()

        UserVaultWrapper(self._vault, user).write_secret(
            relay_refresh_token_vault_path(resource.id), rotated_refresh_token
        )
        self.session.commit()
        return resource

    # ---- delete -----------------------------------------------------------

    def delete(self, user: Optional[User], resource_id: int) -> Optional[ComputeResource]:
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
        """True if any non-terminal Job is bound to this compute resource.

        We don't have a denormalised FK from Job to ComputeResource (the
        binding lives inside ``destination_params``), so we fetch the user's
        non-terminal compute-resource jobs and Python-filter. Safe because
        the resources are owner-only — the candidate set is small.
        """
        stmt = (
            select(Job)
            .where(Job.user_id == user.id)
            .where(Job.state.in_(Job.non_ready_states))
            .where(Job.job_runner_name == COMPUTE_RESOURCE_RUNNER_ID)
        )
        for job in self.session.scalars(stmt):
            params = job.destination_params or {}
            raw = params.get(COMPUTE_RESOURCE_ID_PARAM)
            if raw is None:
                continue
            try:
                bound_to = int(raw)
            except (TypeError, ValueError):
                continue
            if bound_to == resource_id:
                return True
        return False

    def purge(self, user: Optional[User], resource_id: int) -> Optional[ComputeResource]:
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
            UserVaultWrapper(self._vault, user).write_secret(relay_refresh_token_vault_path(resource_id), "")
        except Exception:
            log.exception("Failed to clear vault secret for compute resource %s", resource_id)
            # Continue: the row is still going to ``deleted``; an orphaned
            # vault entry is a leak, not a correctness issue, and the
            # admin can clean it up if needed.

        resource.status = STATUS_DELETED
        self.session.add(resource)
        self.session.commit()
        return resource
