"""Integration test for TPV ↔ compute-resource wiring.

Verifies that with the operator-facing compute_resources.yml.sample loaded
and a stubbed ``app.compute_resource_manager.get_active_for(user)``
returning a fake resource, TPV's mapper:
  * picks the ``compute_resource`` destination, and
  * fills in its params from the resource via the rule's f-string
    expressions, exactly as the deployed system will at job dispatch time.

When the compute_resource_manager returns ``None`` for the user, TPV falls back to the
``_default`` destination.
"""

import os

import pytest
import yaml

# tpv is a dev-only dep of the main lib install but isn't pulled in for
# package-isolation tests (galaxy-app's setup.cfg doesn't list it). Skip
# the whole module when it's missing so those CI shards can still run
# the rest of test/unit/app without crashing on collection.
pytest.importorskip("tpv")

from tpv.commands.test import mock_galaxy  # noqa: E402 — guarded by importorskip above
from tpv.rules import gateway  # noqa: E402 — guarded by importorskip above

from galaxy.jobs import JobDestination  # noqa: E402 — guarded by importorskip above


def _load_compute_resources_sample() -> dict:
    sample_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "lib",
        "galaxy",
        "config",
        "sample",
        "tpv",
        "compute_resources.yml.sample",
    )
    with open(sample_path) as f:
        return yaml.safe_load(f)


def _build_tpv_configs() -> list[dict]:
    """Compose the operator-shipped compute-resources sample with a minimal
    base config: a ``_pulsar`` parent for ``inherits``, plus a ``_default``
    fallback that accepts everything so non-compute-resource users still
    resolve to a destination.
    """
    base: dict = {
        "global": {"default_inherits": "default"},
        "destinations": {
            # ``default`` doubles as the inheritance parent and the fallback
            # destination for jobs without the ``compute_resource`` require-tag.
            "default": {
                "runner": "local",
                "max_accepted_cores": 16,
                "max_accepted_mem": 64,
                "scheduling": {"accept": ["general"]},
            },
            "_pulsar": {
                "abstract": True,
                "runner": "compute_resource",
                "max_accepted_cores": 16,
                "max_accepted_mem": 64,
                "scheduling": {"accept": ["general"]},
            },
        },
        "tools": {
            "default": {
                "cores": 1,
                "mem": 2,
                "scheduling": {"accept": ["general"]},
            },
        },
    }
    compute_resources = _load_compute_resources_sample()
    return [base, compute_resources]


class _StubComputeResource:
    def __init__(self, *, id: int, relay_url: str, manager_name: str):
        self.id = id
        self.relay_url = relay_url
        self.manager_name = manager_name


class _StubComputeResourceManager:
    """Replaces ``app.compute_resource_manager`` for the TPV rule context.

    The real manager (``galaxy.managers.compute_resources.ComputeResourceManager``)
    hits the DB; for a TPV-rule-evaluation test we just need a callable
    that returns the right shape.
    """

    def __init__(self, resource_for_user: dict):
        self._resource_for_user = resource_for_user

    def get_active_for(self, user):
        if user is None:
            return None
        return self._resource_for_user.get(user.email)


@pytest.fixture
def app_with_compute_resource():
    def _make(resource_for_user: dict):
        # create_model=True is required because TPV's JobConfiguration init
        # touches ``app.model.engine`` via ApplicationStack.supports_skip_locked.
        app = mock_galaxy.App(create_model=True)
        app.compute_resource_manager = _StubComputeResourceManager(resource_for_user)
        return app

    return _make


@pytest.fixture(autouse=True)
def reset_tpv_mapper_cache():
    """TPV caches mappers per-referrer in module state. Wipe it so each
    test gets a clean evaluation against its own ``app.compute_resource_manager`` stub."""
    gateway.ACTIVE_DESTINATION_MAPPERS = {}
    yield
    gateway.ACTIVE_DESTINATION_MAPPERS = {}


def _resolve(app, user, *, tool_id: str = "any_tool") -> JobDestination:
    tool = mock_galaxy.Tool(tool_id)
    job = mock_galaxy.Job()
    return gateway.map_tool_to_destination(
        app,
        job,
        tool,
        user,
        tpv_configs=_build_tpv_configs(),
        referrer=JobDestination(id="tpv_dispatcher"),
    )


def test_active_resource_routes_to_compute_resource_with_injected_params(app_with_compute_resource):
    user_email = "user@example.test"
    resource = _StubComputeResource(id=42, relay_url="https://relay.example.test", manager_name="byoc_7_lab")
    app = app_with_compute_resource({user_email: resource})
    user = mock_galaxy.User("byoc", user_email)

    destination = _resolve(app, user)

    assert destination.id == "compute_resource"
    assert destination.runner == "compute_resource"
    assert destination.params["compute_resource_id"] == "42"
    assert destination.params["relay_url"] == "https://relay.example.test"
    assert destination.params["manager"] == "byoc_7_lab"


def test_no_active_resource_falls_back_to_default(app_with_compute_resource):
    app = app_with_compute_resource({})  # nobody has an active resource
    user = mock_galaxy.User("plain", "plain@example.test")

    destination = _resolve(app, user)

    assert destination.id == "default"
    assert destination.runner == "local"
    # The ``inject_compute_resource_params`` rule should be skipped, so
    # none of those params end up on the destination.
    assert "compute_resource_id" not in destination.params
    assert "relay_url" not in destination.params
    assert "manager" not in destination.params


def test_anonymous_user_falls_back_to_default(app_with_compute_resource):
    app = app_with_compute_resource({})
    destination = _resolve(app, user=None)
    assert destination.id == "default"


def test_routing_is_scoped_to_owning_user(app_with_compute_resource):
    """User A has a compute resource; user B doesn't. The rule must read
    from the *currently dispatching* user's resource and not leak across."""
    owner_email = "owner@example.test"
    resource = _StubComputeResource(id=99, relay_url="https://owner.relay.test", manager_name="byoc_99_only")
    app = app_with_compute_resource({owner_email: resource})
    owner = mock_galaxy.User("owner", owner_email)
    other = mock_galaxy.User("other", "other@example.test")

    owner_dest = _resolve(app, owner)
    other_dest = _resolve(app, other)

    assert owner_dest.id == "compute_resource"
    assert owner_dest.params["compute_resource_id"] == "99"
    assert other_dest.id == "default"
