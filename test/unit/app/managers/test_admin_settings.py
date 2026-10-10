from pathlib import Path
from types import SimpleNamespace
from typing import (
    Any,
    cast,
)

import pytest

from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions import (
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.managers.admin_extensions import AdminExtensionsManager
from galaxy.managers.admin_settings import (
    AdminSettingsManager,
    RELOAD_TASK,
)
from galaxy.model import (
    AdminSetting,
    mapping,
    User,
)

FORM_CONFIG = """
id: anvil
section: AnVIL
items:
  - id: monitor
    type: link
    title: Cluster Monitor
    url: /monitor
  - id: batch
    type: form
    title: GCP Batch
    description: Runtime defaults for the Batch runner.
    inputs:
      - name: pool_ttl
        key: gcp_batch.pool_ttl_seconds
        type: integer
        label: Idle seconds
        default: 300
        min: 0
        max: 86400
      - name: spot
        key: gcp_batch.use_spot_instances
        type: boolean
        label: Spot instances
        default: false
      - name: tier
        type: select
        label: Tier
        options: [small, large]
      - name: note
        type: text
        label: Note
"""


class FakeQueueWorker:
    def __init__(self):
        self.tasks: list[tuple[str, dict[str, Any]]] = []

    def send_control_task(self, task, **kwargs):
        self.tasks.append((task, kwargs))


@pytest.fixture
def env(tmp_path: Path):
    extension_dir = tmp_path / "exts" / "anvil"
    extension_dir.mkdir(parents=True)
    (extension_dir / "config.yml").write_text(FORM_CONFIG)
    config = GalaxyAppConfiguration(admin_extensions_dir=str(tmp_path / "exts"), override_tempdir=False)
    extensions = AdminExtensionsManager(config)
    model = mapping.init("/tmp", f"sqlite:///{tmp_path / 'db.sqlite'}", create_tables=True)
    session = model.session
    user = User(email="admin@example.org", password="x", username="admin")
    session.add(user)
    session.commit()
    queue_worker = FakeQueueWorker()
    app = cast(Any, SimpleNamespace(queue_worker=queue_worker))
    manager = AdminSettingsManager(app, cast(Any, session), extensions)
    return SimpleNamespace(
        extensions=extensions, manager=manager, session=session, user=user, queue_worker=queue_worker
    )


def test_registry_assigns_default_keys_and_finds_forms(env):
    item = env.extensions.get_form_item("anvil", "batch")
    keys = [i.key for i in item.inputs]
    assert keys == [
        "gcp_batch.pool_ttl_seconds",
        "gcp_batch.use_spot_instances",
        "anvil.batch.tier",
        "anvil.batch.note",
    ]
    assert env.extensions.declared_input("gcp_batch.pool_ttl_seconds").type == "integer"
    assert env.extensions.declared_input("nobody.declares.this") is None
    with pytest.raises(ObjectNotFound):
        env.extensions.get_form_item("anvil", "monitor")


def test_get_returns_declared_default_before_any_save(env):
    assert env.manager.get("gcp_batch.pool_ttl_seconds") == 300
    assert env.manager.get("gcp_batch.use_spot_instances") is False
    assert env.manager.get("anvil.batch.tier") is None
    assert env.manager.get("anvil.batch.tier", "small") == "small"


def test_get_ignores_undeclared_keys_even_when_stored(env):
    env.session.add(AdminSetting(key="nobody.declares.this", value=42))
    env.session.commit()
    assert env.manager.get("nobody.declares.this", "fallback") == "fallback"


def test_update_saves_coerced_values_and_broadcasts(env):
    item = env.extensions.get_form_item("anvil", "batch")
    saved = env.manager.update_form_values(item, {"pool_ttl": "600", "spot": "true", "tier": "large"}, env.user)

    assert saved == {"pool_ttl": 600, "spot": True, "tier": "large", "note": None}
    rows = {r.key: r for r in env.session.query(AdminSetting).all()}
    assert rows["gcp_batch.pool_ttl_seconds"].value == 600
    assert rows["gcp_batch.use_spot_instances"].value is True
    assert rows["gcp_batch.pool_ttl_seconds"].user_id == env.user.id
    assert "anvil.batch.note" not in rows
    assert env.queue_worker.tasks == [(RELOAD_TASK, {"noop_self": True})]
    assert env.manager.get("gcp_batch.pool_ttl_seconds") == 600


def test_update_partial_leaves_other_inputs_unchanged(env):
    item = env.extensions.get_form_item("anvil", "batch")
    env.manager.update_form_values(item, {"pool_ttl": 10, "note": "first"}, env.user)
    env.manager.update_form_values(item, {"note": "second"}, env.user)
    assert env.manager.form_values(item)["pool_ttl"] == 10
    assert env.manager.form_values(item)["note"] == "second"


@pytest.mark.parametrize(
    "values",
    [
        {"pool_ttl": "many"},
        {"pool_ttl": -1},
        {"pool_ttl": 100000},
        {"spot": "maybe"},
        {"tier": "medium"},
        {"unknown": 1},
    ],
)
def test_update_rejects_bad_values_without_saving(env, values):
    item = env.extensions.get_form_item("anvil", "batch")
    with pytest.raises(RequestParameterInvalidException):
        env.manager.update_form_values(item, values, env.user)
    assert env.session.query(AdminSetting).count() == 0
    assert env.queue_worker.tasks == []


def test_stored_value_that_no_longer_fits_falls_back_to_default(env):
    env.session.add(AdminSetting(key="gcp_batch.pool_ttl_seconds", value="not a number"))
    env.session.commit()
    assert env.manager.get("gcp_batch.pool_ttl_seconds") == 300


def test_invalidate_drops_the_cache(env):
    assert env.manager.get("gcp_batch.pool_ttl_seconds") == 300
    env.session.add(AdminSetting(key="gcp_batch.pool_ttl_seconds", value=42))
    env.session.commit()
    assert env.manager.get("gcp_batch.pool_ttl_seconds") == 300  # cached
    env.manager.invalidate()
    assert env.manager.get("gcp_batch.pool_ttl_seconds") == 42


def test_form_inputs_shape_for_generic_form(env):
    item = env.extensions.get_form_item("anvil", "batch")
    inputs = {i["name"]: i for i in env.manager.form_inputs(item)}
    assert inputs["pool_ttl"] == {
        "name": "pool_ttl",
        "type": "integer",
        "label": "Idle seconds",
        "help": "",
        "value": 300,
        "optional": True,
        "min": 0,
        "max": 86400,
    }
    assert inputs["tier"]["options"] == [["small", "small"], ["large", "large"]]
    assert inputs["spot"]["value"] is False
