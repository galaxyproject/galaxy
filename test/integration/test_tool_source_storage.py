"""Integration tests for tool source storage backends.

These tests configure Galaxy to use different tool source storage backends
and verify that the toolbox boots and serves tools through the API.
Dataset uploads / job execution are exercised by Galaxy's general
integration suite — these tests focus only on the tool source storage
plumbing.
"""

import os
import tempfile

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util


class BaseToolSourceStorageIntegrationTestCase(integration_util.IntegrationTestCase):
    """Base class for tool source storage integration tests."""

    framework_tool_and_types = True

    def _test_api_tools_list(self):
        # ``in_panel=False`` is what the Galaxy client uses
        # (``client/src/stores/toolStore.ts``) and what ``LazyToolBox.to_dict``
        # serves straight from the index. The default ``in_panel=True``
        # path walks the rendered panel which, under ``use_lazy_toolbox=true``,
        # is the un-materialised ``_tool_panel`` and returns empty until
        # individual tools are requested — failing this bare
        # ``len(tools) > 0`` assertion when the workflow_dispatch CI run
        # globally enables ``use_lazy_toolbox``.
        response = self._get("tools", data={"in_panel": "False"})
        self._assert_status_code_is(response, 200)
        tools = response.json()
        assert len(tools) > 0, "Expected at least one tool to be loaded"

    def _test_api_tools_show(self, tool_id: str = "cat1"):
        response = self._get(f"tools/{tool_id}")
        self._assert_status_code_is(response, 200)
        tool_info = response.json()
        assert tool_info["id"] == tool_id


class TestEagerBootSkipsStore(BaseToolSourceStorageIntegrationTestCase):
    """Default deployments never initialize a tool source store."""

    def test_no_store_initialized(self):
        assert self._app.tool_source_store is None
        self._test_api_tools_list()
        self._test_api_tools_show()


class TestSqliteToolSourceStorage(BaseToolSourceStorageIntegrationTestCase):
    """Integration tests with the default sqlite tool source store."""

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["use_lazy_toolbox"] = True

    def test_api_tools_list(self):
        self._test_api_tools_list()

    def test_api_tools_show(self):
        self._test_api_tools_show()

    def test_default_store_is_sqlalchemy_backend(self):
        from galaxy.tools.source_store.sqlalchemy import SqlAlchemyToolSourceStore

        assert isinstance(self._app.tool_source_store, SqlAlchemyToolSourceStore)


class TestCompositeToolSourceStorage(BaseToolSourceStorageIntegrationTestCase):
    """Galaxy boots with a default DB store + a per-conf read-only sqlite store.

    Verifies the composite wiring: a tool_conf carrying ``store="cvmfs_main"``
    plus ``use_lazy_toolbox: true`` causes ``build_tool_source_store`` to wrap
    the default backend in a composite store.
    """

    _sqlite_path: str
    _conf_path: str
    _tmpdir: str

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls._tmpdir = tempfile.mkdtemp(prefix="composite_tss_")
        cls._sqlite_path = os.path.join(cls._tmpdir, "sources.sqlite")

        from galaxy.tools.source_store.sqlalchemy import SqlAlchemyToolSourceStore

        SqlAlchemyToolSourceStore(url=f"sqlite:///{cls._sqlite_path}").count()

        cls._conf_path = os.path.join(cls._tmpdir, "extra_tool_conf.xml")
        with open(cls._conf_path, "w") as f:
            f.write('<?xml version="1.0"?>\n<toolbox store="cvmfs_main"/>\n')

        config["use_lazy_toolbox"] = True
        existing_confs = config.get("tool_config_file") or "config/tool_conf.xml.sample"
        if isinstance(existing_confs, str):
            config["tool_config_file"] = f"{existing_confs},{cls._conf_path}"
        else:
            config["tool_config_file"] = list(existing_confs) + [cls._conf_path]
        config["tool_source_stores"] = {
            "cvmfs_main": {
                "url": f"sqlite:///file:{cls._sqlite_path}?mode=ro&uri=true",
                "read_only": True,
            }
        }

    def test_composite_store_is_wired(self):
        # The boot path must produce a CompositeToolSourceStore when a
        # tool_conf opts into a named per-conf store and use_lazy_toolbox
        # is enabled. Verifying the live app's store directly is more
        # robust than relying on /api/tools, which depends on whether the
        # store was populated in advance.
        from galaxy.tools.source_store.composite import CompositeToolSourceStore

        assert isinstance(self._app.tool_source_store, CompositeToolSourceStore)

    def test_api_tools_list_populated_via_bootstrap(self):
        # With use_lazy_toolbox=true and an empty store, LazyToolBox
        # auto-bootstraps from the configured tool confs on first boot;
        # /api/tools must therefore return a non-empty tool list AND must
        # contain every tool referenced by the active tool confs. The bare
        # ``len(tools) > 0`` check used to mask a bug where ~third of stored
        # sources were silently dropped during index build.
        #
        # ``in_panel=False`` is what the UI uses (``client/src/stores/toolStore.ts``)
        # and what serves directly from the index; the default ``in_panel=True``
        # path walks the un-materialised lazy panel and would only see tools
        # that had been individually requested.
        response = self._get("tools", data={"in_panel": "False"})
        self._assert_status_code_is(response, 200)
        tools = response.json()
        assert isinstance(tools, list)
        tool_ids = {t["id"] for t in tools}
        # Each id below anchors a distinct bootstrap dropout that previously
        # failed silently:
        #   - ``cat1`` lives under tool_conf.xml.sample, exercising the
        #     ``${model_tools_path}`` template-expansion path.
        #   - ``job_properties`` lives under sample_tool_conf.xml, exercising
        #     the ``${tool_conf_dir}`` template-expansion path.
        #   - ``cat_user_defined`` is a YAML tool, exercising the non-XML
        #     branch (no ``xml_tree``) that used to drop every YAML source.
        for required in ("cat1", "job_properties", "cat_user_defined"):
            assert required in tool_ids, (
                f"Bootstrap silently dropped {required!r} from the index "
                f"(have {len(tool_ids)} ids: {sorted(tool_ids)[:10]}…)"
            )


class TestLazyToolBoxReload(BaseToolSourceStorageIntegrationTestCase):
    """Toolbox reload under lazy mode — own class, reload mutates global state."""

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["use_lazy_toolbox"] = True

    def test_base_tools_survive_toolbox_reload(self):
        from galaxy.queue_worker import reload_toolbox

        self._test_api_tools_show("cat1")
        assert self._app.toolbox.get_tool("upload1") is not None
        reload_toolbox(self._app)
        self._test_api_tools_show("cat1")
        self._test_api_tools_list()
        assert self._app.toolbox.get_tool("upload1") is not None

    def test_reload_sees_inline_repopulate_over_foreign_index(self):
        # Another Galaxy instance sharing this database (the CI integration
        # shards share one postgres DB) replaces the singleton tool_index row
        # with its own, much smaller view, and the peer broadcast invalidates
        # our store cache. A subsequent reload must serve THIS instance's
        # tools from its inline repopulate, not the foreign index.
        from galaxy.tools.source_store import ToolIndex
        from galaxy.tools.source_store.sqlalchemy import SqlAlchemyToolSourceStore

        store = self._app.tool_source_store
        assert store is not None
        connection = self._app.config.tool_source_database_connection
        assert connection is not None
        foreign_store = SqlAlchemyToolSourceStore(url=connection)
        foreign_store.store_index(ToolIndex())
        store.invalidate_index_cache()
        # Drop one store row so the reload takes the inline-repopulate path.
        upload_stored = store.get_by_tool_id("upload1")
        assert upload_stored
        store.delete(upload_stored[0].hash)

        from galaxy.queue_worker import reload_toolbox

        old_toolbox = self._app.toolbox
        reload_toolbox(self._app)
        assert self._app.toolbox is not old_toolbox

        assert self._app.toolbox.get_tool("upload1") is not None
        self._test_api_tools_show("cat1")
        self._test_api_tools_list()

    def test_reload_repopulates_inline_after_store_wipe(self):
        store = self._app.tool_source_store
        assert store is not None
        for source_hash in list(store.list_all()):
            store.delete(source_hash)
        store.invalidate_index_cache()
        from galaxy.queue_worker import reload_toolbox

        reload_toolbox(self._app)
        assert self._app.toolbox.get_tool("upload1") is not None
        self._test_api_tools_show("cat1")
        self._test_api_tools_list()


class TestLazyToolBoxApi(BaseToolSourceStorageIntegrationTestCase):
    """End-to-end coverage of LazyToolBox-served API behaviours.

    Regular CI does not run with ``use_lazy_toolbox=true``, so the bug
    surfaces fixed in commits 215638d..912544 are not covered by any
    push/PR run unless this class boots Galaxy with the flag itself.
    Every behaviour the round-2 fixes were meant to deliver is asserted
    here as a single API call against one shared boot:

    - ``<tool_dir>``, YAML, and ``${model_tools_path}`` bootstrap paths.
    - Multi-version index + version-aware ``/api/tools/{id}`` lookup.
    - Default panel-view response shape consumed by the UI.
    - Tokenised tool search across name + description.
    - ``remove_tool_by_id`` lifecycle on the live toolbox.
    - Container-resolver admin endpoint (sensitive to placeholder
      ``None`` Tool entries in ``_LazyToolsByIdView``).

    All methods share one boot via the class-scoped ``setUpClass`` —
    don't add tests that mutate global state in ways that would leak
    into sibling methods (besides ``test_remove_tool_makes_get_tool_return_none``,
    which deliberately removes a tool that no other method touches).
    """

    dataset_populator: DatasetPopulator

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["use_lazy_toolbox"] = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    # --- Bootstrap correctness ----------------------------------------------

    def test_tool_dir_directive_indexes_parameters_tools(self):
        # ``gx_int`` lives under ``test/functional/tools/parameters/`` and
        # gets pulled in by ``<tool_dir dir="parameters/" />``. The bootstrap
        # used to silently drop these because the discovery walker didn't
        # honour the directive.
        response = self._get("tools/gx_int")
        self._assert_status_code_is(response, 200)
        assert response.json()["id"] == "gx_int"

    def test_yaml_user_defined_tool_indexed_under_yaml_id(self):
        # YAML tool's id comes from the body's ``id:`` field, not the
        # filename — the previous bootstrap walked ``xml_tree`` and dropped
        # every YAML source.
        response = self._get("tools/cat_user_defined")
        self._assert_status_code_is(response, 200)
        assert response.json()["id"] == "cat_user_defined"

    def test_model_tools_path_template_substitution(self):
        # ``${model_tools_path}/build_list.xml`` resolves to
        # ``lib/galaxy/tools/build_list.xml`` (id ``__BUILD_LIST__``).
        # Exercises ``_resolve_file_template_kwds`` for the
        # ``model_tools_path`` substitution.
        response = self._get("tools/__BUILD_LIST__")
        self._assert_status_code_is(response, 200)
        assert response.json()["id"] == "__BUILD_LIST__"

    # --- Multi-version + version-aware lookup -------------------------------

    def test_show_unknown_version_falls_back_to_latest(self):
        response = self._get("tools/multiple_versions", data={"tool_version": "0.01"})
        self._assert_status_code_is(response, 200)
        # Default selection uses ``packaging.version.parse``; lex sort would
        # have picked ``"0.1+galaxy6"`` over ``"0.2"`` for a different prefix
        # so the regression matters even though it's invisible in this case.
        assert response.json()["version"] == "0.2"

    def test_show_lists_every_indexed_version(self):
        response = self._get("tools/multiple_versions_hidden", data={"tool_version": "0.1"})
        self._assert_status_code_is(response, 200)
        info = response.json()
        assert info["version"] == "0.1"
        assert info["versions"] == ["0.1", "0.2"]
        assert info["hidden_versions"] == ["0.1"]

    def test_run_specific_version_executes_that_version(self):
        with self.dataset_populator.test_history() as history_id:
            payload = self.dataset_populator.run_tool_payload(
                tool_id="multiple_versions_hidden",
                inputs={},
                history_id=history_id,
            )
            payload["tool_version"] = "0.1"
            response = self.dataset_populator._post("tools", data=payload)
            self._assert_status_code_is(response, 200)
            output = response.json()["outputs"][0]
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output)
            assert content.strip() == "Hidden Version 0.1"

    # --- Default-panel response shape ---------------------------------------

    def test_default_panel_view_section_tools_use_id_list(self):
        # Pins ``ToolSection.to_dict(only_ids=True)``: each section dict has a
        # ``tools`` key holding tool-id strings (interleaved with
        # ``ToolSectionLabel`` dicts where the conf places labels). The
        # regression this guards against is *Tool* dicts appearing in
        # ``tools`` — that breaks ``test_tools::test_index``, which walks
        # ``tool_or_section["tools"]`` to flatten sections and would
        # otherwise miss sectioned tools like ``upload1``.
        response = self._get("tool_panels/default")
        self._assert_status_code_is(response, 200)
        panel = response.json()

        sections_seen = 0
        for entry_id, entry in panel.items():
            if isinstance(entry, dict) and entry.get("model_class") == "ToolSection":
                sections_seen += 1
                assert "tools" in entry, f"section {entry_id} missing 'tools' key"
                for item in entry["tools"]:
                    if isinstance(item, str):
                        continue
                    assert (
                        isinstance(item, dict) and item.get("model_class") == "ToolSectionLabel"
                    ), f"section {entry_id} should hold tool-id strings or ToolSectionLabel dicts, got {item!r}"
        # Sanity: the framework conf has at least one section, otherwise the
        # assertion above never ran.
        assert sections_seen > 0, "expected at least one section in default panel view"

    def test_panel_views_endpoint_returns_views(self):
        # ``GET /api/tool_panels`` used to return ``views={}`` when the lazy
        # index hadn't pre-computed panel_views. The fallback to
        # ``toolbox.panel_view_dicts()`` keeps callers working.
        response = self._get("tool_panels")
        self._assert_status_code_is(response, 200)
        body = response.json()
        assert "views" in body and "default_panel_view" in body
        assert body["views"], "expected at least one panel view to be registered"

    # --- Search -------------------------------------------------------------

    def test_search_finds_tool_by_multi_token_query_across_fields(self):
        # ``cat1`` (for_workflows/catWrapper.xml) has name "Concatenate
        # multiple datasets or collections". A query whose tokens span
        # "Concatenate" + "datasets" forces the tokenised conjunction
        # path; the previous OR-within-single-field implementation
        # returned empty here.
        response = self._get("tools", data={"q": "Concatenate multiple datasets"})
        self._assert_status_code_is(response, 200)
        assert "cat1" in response.json()

    # --- Removal lifecycle --------------------------------------------------

    def test_remove_tool_makes_get_tool_return_none(self):
        # ``remove_tool_by_id`` had to clear ``_tool_index.entries`` /
        # ``entries_by_version`` / LRU + populate ``_tools_by_old_id``;
        # without that fix the call raised KeyError. We pick
        # ``cat_data_and_sleep`` because nothing else in this class
        # references it, so we can mutate the live toolbox without
        # breaking sibling tests.
        toolbox = self._app.toolbox
        assert toolbox.get_tool("cat_data_and_sleep") is not None
        toolbox.remove_tool_by_id("cat_data_and_sleep")
        assert toolbox.get_tool("cat_data_and_sleep") is None

    # --- Materialisation budget ---------------------------------------------

    def test_batch_endpoints_do_not_materialise_tools(self):
        # The whole point of LazyToolBox is that batch/read endpoints answer
        # from the pre-computed index without parsing tools. A regression that
        # sneaks a full-toolbox sweep touching an off-surface (or
        # _MATERIALIZE_OK) attribute would silently degrade these to O(N)
        # parses; under the permissive default it only logs a WARN, so CI
        # wouldn't catch it. Assert a zero materialise-count delta across the
        # batch surface instead. LAZY_TOOL_STRICT covers off-surface reads;
        # this also covers the ones strict can't (a filter that parses, an
        # _MATERIALIZE_OK attr read in a loop).
        from galaxy.tools.lazy_toolbox import LazyToolBox

        toolbox = self._app.toolbox
        # This class self-enables lazy mode; assert it (and narrow the type so
        # mypy accepts the lazy-only _lazy_materialize_count counter).
        assert isinstance(toolbox, LazyToolBox)

        # in_panel=False flat listing (runs the FilterFactory pass), the panel
        # walk, the panel-views endpoint, tests-summary, all_requirements, and
        # tokenised search — every batch reader the client hits. Track a
        # per-endpoint delta so a failure names the culprit.
        deltas = {}
        before = toolbox._lazy_materialize_count

        def _probe(label, resp):
            self._assert_status_code_is(resp, 200)
            nonlocal before
            deltas[label] = toolbox._lazy_materialize_count - before
            before = toolbox._lazy_materialize_count

        _probe("list_in_panel_false", self._get("tools", data={"in_panel": "False"}))
        _probe("list_in_panel_true", self._get("tools", data={"in_panel": "True"}))
        _probe("panel_default", self._get("tool_panels/default"))
        _probe("tests_summary", self._get("tools/tests_summary"))
        # all_requirements is admin-only; it aggregates from the index in lazy mode.
        _probe("all_requirements", self._get("tools/all_requirements", admin=True))
        # Search resolves whoosh hits against the registered stubs, not through
        # the materialising get_tool — the populator-owned index carries ~150
        # tool_conf.xml.sample ids that aren't loaded here, and resolving them
        # via get_tool would parse every one.
        _probe("search", self._get("tools", data={"q": "Concatenate multiple datasets"}))

        assert all(v == 0 for v in deltas.values()), f"batch endpoints materialised tools (expected 0 each): {deltas}"

    # --- Container resolution -----------------------------------------------

    def test_container_resolvers_resolve_tool(self):
        # ``galaxy.tool_util.deps.views.resolve`` does
        # ``self._app.toolbox.tools_by_id[tool_id]`` and then reads
        # ``.tool_requirements`` off that — used to fail with
        # ``'NoneType' object has no attribute 'tool_requirements'`` when
        # ``_LazyToolsByIdView`` returned a ``None`` placeholder for an
        # un-materialised tool. Fixed in c763b03 by populating
        # ``_tools_by_old_id`` and routing the view's ``__getitem__`` /
        # ``copy`` through ``get_tool``.
        #
        # Hit those exact lookups directly — going through
        # ``GET /api/container_resolvers/resolve`` runs the resolver
        # chain (including a remote mulled registry lookup over the
        # network), which periodically returns non-JSON and turns this
        # test into a flake unrelated to the lazy regression we want to
        # pin.
        tools_by_id = self._app.toolbox.tools_by_id
        tool = tools_by_id["cat1"]
        assert tool is not None
        assert getattr(tool, "tool_requirements", None) is not None
        # ``.copy()`` is what ``ContainerFinder.find_best_container_description``
        # invokes via ``copy.copy`` on the registry; placeholder ``None``
        # values would crash callers iterating the copy.
        copy = tools_by_id.copy()
        assert "cat1" in copy
        assert copy["cat1"] is not None
