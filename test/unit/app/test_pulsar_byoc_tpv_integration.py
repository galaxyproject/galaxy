"""Integration test for TPV ↔ BYOC wiring.

Verifies that with the operator-facing byoc.yml.sample loaded and a stubbed
``app.byoc_manager.get_active_for(user)`` returning a fake resource, TPV's
mapper:
  * picks the ``pulsar_byoc`` destination, and
  * fills in its params from the resource via the rule's f-string
    expressions, exactly as the deployed system will at job dispatch time.

When the byoc_manager returns ``None`` for the user, TPV falls back to the
``_default`` destination.
"""

import os

import pytest
import yaml
from tpv.commands.test import mock_galaxy
from tpv.rules import gateway

from galaxy.jobs import JobDestination


def _load_byoc_sample() -> dict:
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
        "byoc.yml.sample",
    )
    with open(sample_path) as f:
        return yaml.safe_load(f)


def _build_tpv_configs() -> list[dict]:
    """Compose the operator-shipped BYOC sample with a minimal base config:
    a ``_pulsar`` parent for ``inherits``, plus a ``_default`` fallback that
    accepts everything so non-BYOC users still resolve to a destination.
    """
    base: dict = {
        "global": {"default_inherits": "default"},
        "destinations": {
            # ``default`` doubles as the inheritance parent and the fallback
            # destination for jobs without the ``pulsar_byoc`` require-tag.
            "default": {
                "runner": "local",
                "max_accepted_cores": 16,
                "max_accepted_mem": 64,
                "scheduling": {"accept": ["general"]},
            },
            "_pulsar": {
                "abstract": True,
                "runner": "pulsar_byoc",
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
    byoc = _load_byoc_sample()
    return [base, byoc]


class _StubBYOCResource:
    def __init__(self, *, id: int, relay_url: str, manager_name: str):
        self.id = id
        self.relay_url = relay_url
        self.manager_name = manager_name


class _StubBYOCManager:
    """Replaces ``app.byoc_manager`` for the TPV rule context.

    The real manager (``galaxy.managers.pulsar_byoc.PulsarByocManager``) hits
    the DB; for a TPV-rule-evaluation test we just need a callable that
    returns the right shape.
    """

    def __init__(self, resource_for_user: dict):
        self._resource_for_user = resource_for_user

    def get_active_for(self, user):
        if user is None:
            return None
        return self._resource_for_user.get(user.email)


@pytest.fixture
def app_with_byoc():
    def _make(resource_for_user: dict):
        # create_model=True is required because TPV's JobConfiguration init
        # touches ``app.model.engine`` via ApplicationStack.supports_skip_locked.
        app = mock_galaxy.App(create_model=True)
        app.byoc_manager = _StubBYOCManager(resource_for_user)
        return app

    return _make


@pytest.fixture(autouse=True)
def reset_tpv_mapper_cache():
    """TPV caches mappers per-referrer in module state. Wipe it so each
    test gets a clean evaluation against its own ``app.byoc_manager`` stub."""
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


def test_active_byoc_routes_to_pulsar_byoc_with_injected_params(app_with_byoc):
    user_email = "byoc@example.test"
    resource = _StubBYOCResource(id=42, relay_url="https://relay.example.test", manager_name="byoc_7_lab")
    app = app_with_byoc({user_email: resource})
    user = mock_galaxy.User("byoc", user_email)

    destination = _resolve(app, user)

    assert destination.id == "pulsar_byoc"
    assert destination.runner == "pulsar_byoc"
    assert destination.params["pulsar_byoc_resource_id"] == "42"
    assert destination.params["relay_url"] == "https://relay.example.test"
    assert destination.params["manager"] == "byoc_7_lab"


def test_no_active_byoc_falls_back_to_default(app_with_byoc):
    app = app_with_byoc({})  # nobody has an active BYOC
    user = mock_galaxy.User("plain", "plain@example.test")

    destination = _resolve(app, user)

    assert destination.id == "default"
    assert destination.runner == "local"
    # The ``inject_byoc_params`` rule should be skipped, so none of those
    # params end up on the destination.
    assert "pulsar_byoc_resource_id" not in destination.params
    assert "relay_url" not in destination.params
    assert "manager" not in destination.params


def test_anonymous_user_falls_back_to_default(app_with_byoc):
    app = app_with_byoc({})
    destination = _resolve(app, user=None)
    assert destination.id == "default"


def test_byoc_routing_is_scoped_to_owning_user(app_with_byoc):
    """User A has a BYOC; user B doesn't. The rule must read from the
    *currently dispatching* user's resource and not leak across."""
    owner_email = "owner@example.test"
    resource = _StubBYOCResource(id=99, relay_url="https://owner.relay.test", manager_name="byoc_99_only")
    app = app_with_byoc({owner_email: resource})
    owner = mock_galaxy.User("owner", owner_email)
    other = mock_galaxy.User("other", "other@example.test")

    owner_dest = _resolve(app, owner)
    other_dest = _resolve(app, other)

    assert owner_dest.id == "pulsar_byoc"
    assert owner_dest.params["pulsar_byoc_resource_id"] == "99"
    assert other_dest.id == "default"
