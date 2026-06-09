"""HTTP-layer integration tests for the compute-resources API.

These cover the four read/lifecycle routes — ``index``, ``show``, ``delete``,
``purge`` — that the heavy end-to-end suite
(``compute_resources/test_compute_resource_tool_execution.py``) never exercises:
that suite only drives the two path-param-less *registration* routes, so the
request/response contract of the ``{resource_id}`` routes (in particular the
encode/decode boundary on the resource id) had no coverage at all.

We bypass the relay-dependent registration handshake and seed a
``ComputeResource`` row directly, then drive the real FastAPI routes as the
owning user (and, for isolation, as a second user).
"""

from typing import Optional

from galaxy import model
from galaxy.model.db.user import get_user_by_email
from galaxy_test.base import api_asserts
from galaxy_test.base.api_util import random_name
from galaxy_test.driver import integration_util


class TestComputeResourcesApi(integration_util.IntegrationTestCase, integration_util.ConfiguresDatabaseVault):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        # ``purge`` clears the relay refresh token from the vault, so the
        # feature needs a real (database) vault rather than the NullVault.
        cls._configure_database_vault(config)
        config["enable_compute_resources"] = True

    # ---- helpers ---------------------------------------------------------

    @property
    def _sa_session(self):
        return self._app.model.session

    def _current_user_email(self) -> str:
        return self._get("users/current").json()["email"]

    def _seed_resource(
        self,
        *,
        owner_email: Optional[str] = None,
        status: str = "active",
        manager_name: Optional[str] = None,
    ) -> model.ComputeResource:
        """Insert a ``ComputeResource`` row owned by ``owner_email``
        (defaulting to the current API user) and return it."""
        email = owner_email or self._current_user_email()
        session = self._sa_session
        user = get_user_by_email(session, email)
        assert user is not None, f"no user row for {email!r}"
        resource = model.ComputeResource(
            user_id=user.id,
            manager_name=manager_name or random_name(prefix="cr_mgr"),
            relay_user_id="relay-sub-123",
            relay_url="https://relay.test",
            status=status,
        )
        session.add(resource)
        session.commit()
        return resource

    # ---- tests -----------------------------------------------------------

    def test_list_then_show_round_trip(self):
        """The id from a list/show response must feed straight back into the
        per-resource route. Regression test: the id is serialized *encoded*
        but the path param used to be a raw int, so this round-trip 422'd."""
        resource = self._seed_resource()
        expected_encoded_id = self._app.security.encode_id(resource.id)

        index = self._get("compute_resources")
        api_asserts.assert_status_code_is_ok(index)
        listed = {r["id"]: r for r in index.json()}
        assert expected_encoded_id in listed, listed
        # The wire form is the encoded id, not the raw primary key.
        assert expected_encoded_id != str(resource.id)
        assert listed[expected_encoded_id]["manager_name"] == resource.manager_name

        # Feed the encoded id from the list response straight into show.
        show = self._get(f"compute_resources/{expected_encoded_id}")
        api_asserts.assert_status_code_is_ok(show)
        body = show.json()
        assert body["id"] == expected_encoded_id
        assert body["manager_name"] == resource.manager_name
        assert body["status"] == "active"
        # The relay refresh token must never be exposed over the API.
        assert "relay_refresh_token" not in body

    def test_show_unknown_id_is_404(self):
        missing = self._app.security.encode_id(424242)
        response = self._get(f"compute_resources/{missing}")
        api_asserts.assert_status_code_is(response, 404)

    def test_delete_disables_resource(self):
        resource = self._seed_resource()
        encoded_id = self._app.security.encode_id(resource.id)

        delete = self._delete(f"compute_resources/{encoded_id}")
        api_asserts.assert_status_code_is(delete, 204)

        show = self._get(f"compute_resources/{encoded_id}")
        api_asserts.assert_status_code_is_ok(show)
        assert show.json()["status"] == "disabled"

    def test_purge_removes_resource_from_inventory(self):
        resource = self._seed_resource(status="disabled")
        encoded_id = self._app.security.encode_id(resource.id)

        purge = self._post(f"compute_resources/{encoded_id}/purge")
        api_asserts.assert_status_code_is(purge, 204)

        # Purge is a soft-delete: the resource drops out of the user's listed
        # inventory...
        index = self._get("compute_resources")
        api_asserts.assert_status_code_is_ok(index)
        assert encoded_id not in {r["id"] for r in index.json()}
        # ...but the row is retained for audit and stays fetchable by id,
        # reporting its terminal "deleted" status.
        show = self._get(f"compute_resources/{encoded_id}")
        api_asserts.assert_status_code_is_ok(show)
        assert show.json()["status"] == "deleted"

    def test_other_user_cannot_see_or_delete(self):
        """A resource is scoped to its owner: a second user gets a 404 (not a
        403 — existence isn't leaked) on show/delete and never sees it listed."""
        resource = self._seed_resource()
        encoded_id = self._app.security.encode_id(resource.id)

        with self._different_user():
            index = self._get("compute_resources")
            api_asserts.assert_status_code_is_ok(index)
            assert encoded_id not in {r["id"] for r in index.json()}

            show = self._get(f"compute_resources/{encoded_id}")
            api_asserts.assert_status_code_is(show, 404)

            delete = self._delete(f"compute_resources/{encoded_id}")
            api_asserts.assert_status_code_is(delete, 404)

        # The owner can still see it, untouched, afterwards.
        owner_show = self._get(f"compute_resources/{encoded_id}")
        api_asserts.assert_status_code_is_ok(owner_show)
        assert owner_show.json()["status"] == "active"
