from datetime import (
    datetime,
    timedelta,
    timezone,
)

import jwt
import pytest
from pulsar_relay_client.testing import FakeRelayClient
from sqlalchemy import select

from galaxy.managers.pulsar_byoc import (
    BootstrapTokenExpired,
    BootstrapTokenInvalid,
    PulsarByocManager,
    RATE_LIMIT_PER_HOUR,
    RegistrationRateLimited,
    RelayVerificationFailed,
    ResourceHasRunningJobs,
    STATUS_ACTIVE,
    STATUS_DELETED,
    STATUS_DISABLED,
    STATUS_PENDING,
)
from galaxy.model import (
    Job,
    PulsarByocBootstrapToken,
    PulsarByocResource,
)
from galaxy.security.vault import UserVaultWrapper
from .base import BaseTestCase


def _signed_jwt(sub: str) -> str:
    """Mint a JWT-shaped string carrying ``sub``. We never verify signatures
    here (the relay would have); we pad the HMAC secret to suppress
    PyJWT's short-key warning."""
    return jwt.encode({"sub": sub}, "x" * 32, algorithm="HS256")


def _fake_relay_client(sub: str = "default-sub", rotated_refresh_token: str = "RT-ROTATED") -> FakeRelayClient:
    """Build a :class:`FakeRelayClient` that returns an access token decodable
    to ``sub`` (the manager verifies the sub claim against the supplied
    ``manager_name``)."""
    return FakeRelayClient(
        user_id=f"u-{sub}",
        username=sub,
        rotated_access_token=_signed_jwt(sub),
        rotated_refresh_token=rotated_refresh_token,
    )


class TestPulsarByocManager(BaseTestCase):
    def set_up_managers(self):
        super().set_up_managers()
        # The vault is opt-in on MockApp; complete_registration writes the
        # rotated refresh token into it, so it must exist for the
        # registration tests below to pass.
        self.app.setup_test_vault()
        self.fake_relay_client = _fake_relay_client()
        self.byoc_manager = PulsarByocManager(
            self.app.model.context,
            self.app.vault,
            self.app.config,
            relay_client_factory=lambda _relay_url: self.fake_relay_client,
        )

    def _add_resource(self, user, *, status: str, manager_name: str) -> PulsarByocResource:
        resource = PulsarByocResource(
            user_id=user.id,
            manager_name=manager_name,
            relay_url="https://relay.example.test",
            status=status,
        )
        self.trans.sa_session.add(resource)
        self.trans.sa_session.commit()
        return resource

    def test_returns_none_for_anonymous(self):
        assert self.byoc_manager.get_active_for(None) is None

    def test_returns_none_when_user_has_no_resources(self):
        user = self.user_manager.create(email="byoc1@example.test", username="byoc1", password="x" * 8)
        assert self.byoc_manager.get_active_for(user) is None

    def test_returns_active_resource(self):
        user = self.user_manager.create(email="byoc2@example.test", username="byoc2", password="x" * 8)
        active = self._add_resource(user, status=STATUS_ACTIVE, manager_name=f"byoc_{user.id}_only")

        result = self.byoc_manager.get_active_for(user)
        assert result is not None
        assert result.id == active.id
        assert result.manager_name == active.manager_name

    def test_ignores_non_active_resources(self):
        user = self.user_manager.create(email="byoc3@example.test", username="byoc3", password="x" * 8)
        self._add_resource(user, status=STATUS_PENDING, manager_name=f"byoc_{user.id}_p")
        self._add_resource(user, status=STATUS_DISABLED, manager_name=f"byoc_{user.id}_d")
        self._add_resource(user, status=STATUS_DELETED, manager_name=f"byoc_{user.id}_x")

        assert self.byoc_manager.get_active_for(user) is None

    def test_scopes_to_requesting_user(self):
        user_a = self.user_manager.create(email="a@example.test", username="usera", password="x" * 8)
        user_b = self.user_manager.create(email="b@example.test", username="userb", password="x" * 8)
        a_resource = self._add_resource(user_a, status=STATUS_ACTIVE, manager_name=f"byoc_{user_a.id}_only")
        self._add_resource(user_b, status=STATUS_ACTIVE, manager_name=f"byoc_{user_b.id}_only")

        result_a = self.byoc_manager.get_active_for(user_a)
        result_b = self.byoc_manager.get_active_for(user_b)

        assert result_a is not None
        assert result_b is not None
        assert result_a.id == a_resource.id
        assert result_b.id != a_resource.id

    # ---- registration tests ----------------------------------------------

    def _stub_relay_exchange(self, *, sub: str, rotated_token: str = "RT-ROTATED"):
        """Reconfigure the injected fake to return the right ``sub`` for the
        access token the manager will receive."""
        self.fake_relay_client = _fake_relay_client(sub=sub, rotated_refresh_token=rotated_token)

    def test_start_registration_persists_token(self):
        user = self.user_manager.create(email="reg1@example.test", username="reg1", password="x" * 8)
        ticket = self.byoc_manager.start_registration(user)
        assert ticket.bootstrap_token
        assert len(ticket.bootstrap_token) > 16
        assert ticket.expires_at > datetime.now(tz=timezone.utc).replace(tzinfo=None)
        # The one-liner contains the bootstrap token so the user can paste it
        # straight into a terminal.
        assert ticket.bootstrap_token in ticket.one_liner
        # Round-trips through the DB.
        fetched = self.trans.sa_session.scalars(
            select(PulsarByocBootstrapToken).where(PulsarByocBootstrapToken.token == ticket.bootstrap_token)
        ).first()
        assert fetched is not None
        assert fetched.user_id == user.id
        assert fetched.expiration_time > datetime.now(tz=timezone.utc).replace(tzinfo=None)

    def test_complete_registration_happy_path(self):
        user = self.user_manager.create(email="reg2@example.test", username="reg2", password="x" * 8)
        ticket = self.byoc_manager.start_registration(user)
        manager_name = f"byoc_{user.id}_lab"
        self._stub_relay_exchange(sub=manager_name)

        resource = self.byoc_manager.complete_registration(
            bootstrap_token=ticket.bootstrap_token,
            refresh_token="RT-ORIGINAL",
            relay_url="https://relay.example.test",
            manager_name=manager_name,
        )

        assert resource.id is not None
        assert resource.status == STATUS_ACTIVE
        assert resource.manager_name == manager_name
        assert resource.relay_url == "https://relay.example.test"
        # Token store is consumed on redemption.
        assert (
            self.trans.sa_session.scalars(
                select(PulsarByocBootstrapToken).where(PulsarByocBootstrapToken.token == ticket.bootstrap_token)
            ).first()
            is None
        )
        # Vault contains the rotated token (not the original).
        stored = UserVaultWrapper(self.app.vault, user).read_secret(f"pulsar_byoc/{resource.id}/relay_refresh_token")
        assert stored == "RT-ROTATED"

    def test_complete_registration_rejects_unknown_bootstrap_token(self):
        self.user_manager.create(email="reg3@example.test", username="reg3", password="x" * 8)
        self._stub_relay_exchange(sub="byoc_x_y")
        with pytest.raises(BootstrapTokenInvalid):
            self.byoc_manager.complete_registration(
                bootstrap_token="not-a-real-token",
                refresh_token="RT",
                relay_url="https://relay.example.test",
                manager_name="byoc_x_y",
            )

    def test_complete_registration_rejects_expired_bootstrap_token(self):
        user = self.user_manager.create(email="reg4@example.test", username="reg4", password="x" * 8)
        ticket = self.byoc_manager.start_registration(user)
        # Backdate the underlying DB row so the token is past its TTL.
        row = self.trans.sa_session.scalars(
            select(PulsarByocBootstrapToken).where(PulsarByocBootstrapToken.token == ticket.bootstrap_token)
        ).first()
        assert row is not None
        row.expiration_time = datetime.now(tz=timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
        self.trans.sa_session.add(row)
        self.trans.sa_session.commit()
        self._stub_relay_exchange(sub=f"byoc_{user.id}_x")

        with pytest.raises(BootstrapTokenExpired):
            self.byoc_manager.complete_registration(
                bootstrap_token=ticket.bootstrap_token,
                refresh_token="RT",
                relay_url="https://relay.example.test",
                manager_name=f"byoc_{user.id}_x",
            )
        # Expired tokens are cleaned up so they can't be retried.
        assert (
            self.trans.sa_session.scalars(
                select(PulsarByocBootstrapToken).where(PulsarByocBootstrapToken.token == ticket.bootstrap_token)
            ).first()
            is None
        )

    def test_complete_registration_rejects_sub_mismatch(self):
        """A user must not be able to redirect another relay user's topics
        into their Galaxy account."""
        user = self.user_manager.create(email="reg5@example.test", username="reg5", password="x" * 8)
        ticket = self.byoc_manager.start_registration(user)
        # Refresh token represents relay user 'someone_else' — but the
        # caller claims to be 'me'.
        self._stub_relay_exchange(sub="someone_else")

        with pytest.raises(RelayVerificationFailed, match="does not match"):
            self.byoc_manager.complete_registration(
                bootstrap_token=ticket.bootstrap_token,
                refresh_token="RT",
                relay_url="https://relay.example.test",
                manager_name="me",
            )

    def test_complete_registration_replaces_existing_active(self):
        user = self.user_manager.create(email="reg6@example.test", username="reg6", password="x" * 8)
        # First active resource — directly inserted.
        first = self._add_resource(user, status=STATUS_ACTIVE, manager_name=f"byoc_{user.id}_first")

        ticket = self.byoc_manager.start_registration(user)
        self._stub_relay_exchange(sub=f"byoc_{user.id}_second")
        new_resource = self.byoc_manager.complete_registration(
            bootstrap_token=ticket.bootstrap_token,
            refresh_token="RT",
            relay_url="https://relay.example.test",
            manager_name=f"byoc_{user.id}_second",
        )

        # Old row was disabled, new row is active.
        self.trans.sa_session.refresh(first)
        assert first.status == STATUS_DISABLED
        assert new_resource.status == STATUS_ACTIVE
        # ``get_active_for`` resolves the new one.
        active = self.byoc_manager.get_active_for(user)
        assert active is not None
        assert active.id == new_resource.id

    def test_delete_transitions_to_disabled(self):
        user = self.user_manager.create(email="del1@example.test", username="del1", password="x" * 8)
        resource = self._add_resource(user, status=STATUS_ACTIVE, manager_name=f"byoc_{user.id}_x")
        returned = self.byoc_manager.delete(user, resource.id)
        assert returned is not None
        assert returned.status == STATUS_DISABLED
        self.trans.sa_session.refresh(resource)
        assert resource.status == STATUS_DISABLED

    def test_delete_refuses_cross_user(self):
        owner = self.user_manager.create(email="del2@example.test", username="del2", password="x" * 8)
        intruder = self.user_manager.create(email="del3@example.test", username="del3", password="x" * 8)
        resource = self._add_resource(owner, status=STATUS_ACTIVE, manager_name=f"byoc_{owner.id}_x")
        assert self.byoc_manager.delete(intruder, resource.id) is None
        self.trans.sa_session.refresh(resource)
        assert resource.status == STATUS_ACTIVE  # unchanged

    def test_start_registration_rate_limits(self):
        user = self.user_manager.create(email="rl1@example.test", username="rl1", password="x" * 8)
        # Burn the rolling-hour budget.
        for _ in range(RATE_LIMIT_PER_HOUR):
            self.byoc_manager.start_registration(user)
        # The next call must be refused.
        with pytest.raises(RegistrationRateLimited):
            self.byoc_manager.start_registration(user)

    def test_start_registration_reaps_expired_tokens(self):
        """Expired tokens of *the same user* are deleted inline, so they
        don't count against the rate limit and don't accumulate in the DB."""
        user = self.user_manager.create(email="rl2@example.test", username="rl2", password="x" * 8)
        # Seed RATE_LIMIT_PER_HOUR already-expired + outside-window rows
        # directly. Going through the manager would commit + re-flush each
        # iteration and trip SQLAlchemy's strict identity-map rules in tests.
        past_expiration = datetime.now(tz=timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
        past_create = datetime.now(tz=timezone.utc).replace(tzinfo=None) - timedelta(hours=2)
        for i in range(RATE_LIMIT_PER_HOUR):
            self.trans.sa_session.add(
                PulsarByocBootstrapToken(
                    token=f"expired-{i}-{user.id}",
                    user_id=user.id,
                    create_time=past_create,
                    expiration_time=past_expiration,
                )
            )
        self.trans.sa_session.commit()

        # A fresh call should succeed (expired tokens reaped + outside the
        # rolling window).
        fresh = self.byoc_manager.start_registration(user)
        assert fresh.bootstrap_token

    def test_list_for_excludes_deleted(self):
        user = self.user_manager.create(email="list1@example.test", username="list1", password="x" * 8)
        self._add_resource(user, status=STATUS_ACTIVE, manager_name=f"byoc_{user.id}_a")
        self._add_resource(user, status=STATUS_DISABLED, manager_name=f"byoc_{user.id}_b")
        self._add_resource(user, status=STATUS_DELETED, manager_name=f"byoc_{user.id}_c")
        rows = self.byoc_manager.list_for(user)
        statuses = sorted(r.status for r in rows)
        assert statuses == [STATUS_ACTIVE, STATUS_DISABLED]

    # ---- purge tests ------------------------------------------------------

    def _seed_vault_token(self, user, resource_id: int, value: str = "RT-OLD"):
        from galaxy.security.vault import UserVaultWrapper

        UserVaultWrapper(self.app.vault, user).write_secret(f"pulsar_byoc/{resource_id}/relay_refresh_token", value)

    def _read_vault_token(self, user, resource_id: int):
        from galaxy.security.vault import UserVaultWrapper

        return UserVaultWrapper(self.app.vault, user).read_secret(f"pulsar_byoc/{resource_id}/relay_refresh_token")

    def test_purge_clears_vault_and_transitions_to_deleted(self):
        user = self.user_manager.create(email="pur1@example.test", username="pur1", password="x" * 8)
        resource = self._add_resource(user, status=STATUS_DISABLED, manager_name=f"byoc_{user.id}_d")
        self._seed_vault_token(user, resource.id)

        returned = self.byoc_manager.purge(user, resource.id)
        assert returned is not None
        assert returned.status == STATUS_DELETED
        # Vault was cleared.
        assert (self._read_vault_token(user, resource.id) or "") == ""

    def test_purge_is_idempotent_on_already_deleted(self):
        user = self.user_manager.create(email="pur2@example.test", username="pur2", password="x" * 8)
        resource = self._add_resource(user, status=STATUS_DELETED, manager_name=f"byoc_{user.id}_d2")
        # Should not raise.
        returned = self.byoc_manager.purge(user, resource.id)
        assert returned is not None
        assert returned.status == STATUS_DELETED

    def test_purge_refuses_cross_user(self):
        owner = self.user_manager.create(email="pur3@example.test", username="pur3", password="x" * 8)
        intruder = self.user_manager.create(email="pur4@example.test", username="pur4", password="x" * 8)
        resource = self._add_resource(owner, status=STATUS_DISABLED, manager_name=f"byoc_{owner.id}_d")
        assert self.byoc_manager.purge(intruder, resource.id) is None

    def test_purge_refuses_while_running_jobs_exist(self):
        user = self.user_manager.create(email="pur5@example.test", username="pur5", password="x" * 8)
        resource = self._add_resource(user, status=STATUS_DISABLED, manager_name=f"byoc_{user.id}_d")
        # Seed a non-terminal job bound to this resource.
        job = Job()
        job.user_id = user.id
        job.state = Job.states.RUNNING
        job.job_runner_name = "pulsar_byoc"
        job.destination_params = {"pulsar_byoc_resource_id": str(resource.id)}
        self.trans.sa_session.add(job)
        self.trans.sa_session.commit()

        with pytest.raises(ResourceHasRunningJobs):
            self.byoc_manager.purge(user, resource.id)

    def test_purge_allowed_when_only_terminal_jobs_remain(self):
        user = self.user_manager.create(email="pur6@example.test", username="pur6", password="x" * 8)
        resource = self._add_resource(user, status=STATUS_DISABLED, manager_name=f"byoc_{user.id}_d")
        job = Job()
        job.user_id = user.id
        job.state = Job.states.OK  # terminal
        job.job_runner_name = "pulsar_byoc"
        job.destination_params = {"pulsar_byoc_resource_id": str(resource.id)}
        self.trans.sa_session.add(job)
        self.trans.sa_session.commit()

        returned = self.byoc_manager.purge(user, resource.id)
        assert returned is not None
        assert returned.status == STATUS_DELETED

    # ---- capabilities_for tests ------------------------------------------

    def _capability_payload(self, **overrides) -> dict:
        """Minimal valid v1 snapshot used as the canned relay response."""
        base = {
            "schema_version": 1,
            "manager_name": "_default_",
            "pulsar_version": "0.15.16",
            "staging_directory": "/srv/pulsar/files/staging",
            "persistence_directory": "/srv/pulsar/files/persisted",
            "tool_dependency_dir": None,
            "dependency_resolvers": [],
            "conda_available": False,
            "container_runtime": {
                "docker_available": False,
                "singularity_available": False,
                "apptainer_available": False,
            },
            "manager": {"name": "_default_", "type": "queued_python", "num_concurrent_jobs": 1},
        }
        base.update(overrides)
        return base

    def _seed_capability_message(self, topic: str, payload: dict) -> None:
        """Make ``self.fake_relay_client.fetch_messages(topic, ...)`` return ``payload``."""
        self.fake_relay_client.stored_messages[topic] = [
            {
                "message_id": "1700000000-0",
                "topic": topic,
                "payload": payload,
                "timestamp": "2026-05-14T10:00:00.000Z",
                "metadata": None,
            }
        ]

    def _register_byoc(self, user, *, manager_name: str) -> "PulsarByocResource":
        """End-to-end registration so the vault has a refresh token under
        the right key. Reuses the same fake relay client the test setup
        configured."""
        ticket = self.byoc_manager.start_registration(user)
        self._stub_relay_exchange(sub=manager_name)
        return self.byoc_manager.complete_registration(
            bootstrap_token=ticket.bootstrap_token,
            refresh_token="RT-ORIGINAL",
            relay_url="https://relay.example.test",
            manager_name=manager_name,
        )

    def test_capabilities_for_returns_none_for_anonymous(self):
        user = self.user_manager.create(email="cap_anon@example.test", username="cap_anon", password="x" * 8)
        resource = self._register_byoc(user, manager_name=f"byoc_{user.id}_anon")
        assert self.byoc_manager.capabilities_for(resource, user=None) is None

    def test_capabilities_for_returns_none_when_no_vault_token(self):
        """Resource exists but vault is empty (e.g. registration interrupted
        before the vault write). capabilities_for must not crash; just
        return None so the runner trusts operator params."""
        user = self.user_manager.create(email="cap_novault@example.test", username="cap_novault", password="x" * 8)
        resource = self._add_resource(user, status=STATUS_ACTIVE, manager_name=f"byoc_{user.id}_n")
        assert self.byoc_manager.capabilities_for(resource, user=user) is None

    def test_capabilities_for_returns_payload_on_happy_path(self):
        user = self.user_manager.create(email="cap_ok@example.test", username="cap_ok", password="x" * 8)
        manager_name = f"byoc_{user.id}_lab"
        resource = self._register_byoc(user, manager_name=manager_name)
        payload = self._capability_payload(manager_name=manager_name, conda_available=True)
        # Topic mirrors pulsar's __make_capabilities_topic_name convention:
        # non-default manager name → suffix; no prefix configured here.
        self._seed_capability_message(f"pulsar_capabilities_{manager_name}", payload)

        out = self.byoc_manager.capabilities_for(resource, user=user)
        assert out == payload

    def test_capabilities_for_uses_topic_prefix_when_resource_carries_one(self):
        user = self.user_manager.create(email="cap_pfx@example.test", username="cap_pfx", password="x" * 8)
        manager_name = f"byoc_{user.id}_lab"
        resource = self._register_byoc(user, manager_name=manager_name)
        resource.relay_topic_prefix = "prod"
        self.trans.sa_session.add(resource)
        self.trans.sa_session.commit()
        payload = self._capability_payload(manager_name=manager_name)
        self._seed_capability_message(f"prod_pulsar_capabilities_{manager_name}", payload)

        out = self.byoc_manager.capabilities_for(resource, user=user)
        assert out is not None
        assert out["manager_name"] == manager_name

    def test_capabilities_for_returns_none_when_topic_empty(self):
        user = self.user_manager.create(email="cap_empty@example.test", username="cap_empty", password="x" * 8)
        manager_name = f"byoc_{user.id}_e"
        resource = self._register_byoc(user, manager_name=manager_name)
        # Don't seed any messages — the fake returns an empty list.
        assert self.byoc_manager.capabilities_for(resource, user=user) is None

    def test_capabilities_for_returns_none_for_unknown_schema_version(self):
        user = self.user_manager.create(email="cap_v99@example.test", username="cap_v99", password="x" * 8)
        manager_name = f"byoc_{user.id}_99"
        resource = self._register_byoc(user, manager_name=manager_name)
        self._seed_capability_message(
            f"pulsar_capabilities_{manager_name}",
            {"schema_version": 99, "manager_name": manager_name},
        )
        assert self.byoc_manager.capabilities_for(resource, user=user) is None

    def test_capabilities_for_caches_within_ttl(self):
        """Within the TTL window, two calls only invoke the relay once."""
        user = self.user_manager.create(email="cap_cached@example.test", username="cap_cached", password="x" * 8)
        manager_name = f"byoc_{user.id}_cached"
        resource = self._register_byoc(user, manager_name=manager_name)
        self._seed_capability_message(
            f"pulsar_capabilities_{manager_name}",
            self._capability_payload(manager_name=manager_name),
        )
        self.fake_relay_client.fetch_calls.clear()
        self.fake_relay_client.exchange_calls.clear()

        self.byoc_manager.capabilities_for(resource, user=user)
        self.byoc_manager.capabilities_for(resource, user=user)

        # Cache hit on the second call: no new fetch, no new exchange.
        assert len(self.fake_relay_client.fetch_calls) == 1
        assert len(self.fake_relay_client.exchange_calls) == 1

    def test_capabilities_for_persists_rotated_refresh_token(self):
        """The relay rotates the refresh token on every exchange; the
        manager must vault the new one so the runner's separately-cached
        client manager doesn't try to use a stale token next time."""
        user = self.user_manager.create(email="cap_rotate@example.test", username="cap_rotate", password="x" * 8)
        manager_name = f"byoc_{user.id}_rot"
        resource = self._register_byoc(user, manager_name=manager_name)
        # Reconfigure the fake to return a different rotated token on
        # this exchange than the one written by complete_registration.
        self._stub_relay_exchange(sub=manager_name, rotated_token="RT-ROTATED-AGAIN")
        self._seed_capability_message(
            f"pulsar_capabilities_{manager_name}",
            self._capability_payload(manager_name=manager_name),
        )

        self.byoc_manager.capabilities_for(resource, user=user)

        stored = UserVaultWrapper(self.app.vault, user).read_secret(f"pulsar_byoc/{resource.id}/relay_refresh_token")
        assert stored == "RT-ROTATED-AGAIN"
