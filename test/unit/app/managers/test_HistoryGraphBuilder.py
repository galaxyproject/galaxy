import os

import pytest

from galaxy import model
from galaxy.exceptions import RequestParameterInvalidException
from galaxy.managers.collections import DatasetCollectionManager
from galaxy.managers.datasets import DatasetManager
from galaxy.managers.hdas import HDAManager
from galaxy.managers.histories import HistoryManager
from galaxy.managers.history_graph import HistoryGraphBuilder
from .base import (
    BaseTestCase,
    CreatesCollectionsMixin,
)

default_password = "123456"
_user_counter = 0


def _next_user_data():
    global _user_counter
    _user_counter += 1
    return dict(
        email=f"graphuser{_user_counter}@test.test",
        username=f"graphuser{_user_counter}",
        password=default_password,
    )


class TestHistoryGraphBuilder(BaseTestCase, CreatesCollectionsMixin):
    def set_up_managers(self):
        super().set_up_managers()
        self.dataset_manager = self.app[DatasetManager]
        self.hda_manager = self.app[HDAManager]
        self.history_manager = self.app[HistoryManager]
        self.collection_manager = self.app[DatasetCollectionManager]

    def _build_graph(
        self,
        history,
        seed=None,
        direction="both",
        depth=20,
        limit=500,
        seed_scope=None,
    ):
        builder = HistoryGraphBuilder(
            sa_session=self.trans.sa_session,
            security=self.app.security,
            history_id=history.id,
            limit=limit,
            seed=seed,
            direction=direction,
            depth=depth,
            seed_scope=seed_scope,
        )
        return builder.build()

    def _encode(self, prefix, db_id):
        return f"{prefix}{self.app.security.encode_id(db_id)}"

    def _create_history(self):
        user = self.user_manager.create(**_next_user_data())
        self.trans.set_user(user)
        return self.history_manager.create(name="test_history", user=user), user

    def _create_hda(self, history, name="test_dataset", extension="txt"):
        hda = self.hda_manager.create(name=name, history=history, dataset=self.dataset_manager.create())
        hda.extension = extension
        self.trans.sa_session.flush()
        return hda

    def _create_tool_source(self):
        ts = model.ToolSource()
        ts.hash = "abc123"
        ts.source = {"xml": "<tool/>"}
        ts.source_class = "XmlToolSource"
        session = self.trans.sa_session
        session.add(ts)
        session.flush()
        return ts

    def _create_tool_request(self, history, request_data=None, state="submitted"):
        ts = self._create_tool_source()
        tr = model.ToolRequest()
        tr.tool_source_id = ts.id
        tr.history_id = history.id
        tr.request = request_data or {}
        tr.state = state
        session = self.trans.sa_session
        session.add(tr)
        session.flush()
        return tr

    def _create_job(self, tool_request=None, tool_id="test_tool", tool_version="1.0"):
        job = model.Job()
        job.tool_id = tool_id
        job.tool_version = tool_version
        if tool_request:
            job.tool_request_id = tool_request.id
        session = self.trans.sa_session
        session.add(job)
        session.flush()
        return job

    def _append_payload_input(self, job, ref):
        if job.tool_request_id is None:
            return
        tr = self.trans.sa_session.get(model.ToolRequest, job.tool_request_id)
        if tr is None:
            return
        payload = dict(tr.request) if isinstance(tr.request, dict) else {}
        inputs = list(payload.get("inputs", []))
        inputs.append(ref)
        payload["inputs"] = inputs
        tr.request = payload

    def _link_job_input_hda(self, job, hda, name="input"):
        assoc = model.JobToInputDatasetAssociation(name=name, dataset=hda)
        assoc.job_id = job.id
        self._append_payload_input(job, {"src": "hda", "id": hda.id})
        session = self.trans.sa_session
        session.add(assoc)
        session.flush()
        return assoc

    def _link_job_output_hda(self, job, hda, name="output"):
        assoc = model.JobToOutputDatasetAssociation(name=name, dataset=hda)
        assoc.job_id = job.id
        session = self.trans.sa_session
        session.add(assoc)
        session.flush()
        return assoc

    def _link_job_input_hdca(self, job, hdca, name="input"):
        assoc = model.JobToInputDatasetCollectionAssociation(name=name, dataset_collection=hdca)
        assoc.job_id = job.id
        self._append_payload_input(job, {"src": "hdca", "id": hdca.id})
        session = self.trans.sa_session
        session.add(assoc)
        session.flush()
        return assoc

    def _link_job_output_hdca(self, job, hdca, name="output"):
        # Mirrors production: ``Job.add_output_dataset_collection`` only
        # creates the JobToOutputDatasetCollectionAssociation row.  It
        # does NOT set ``HDCA.job_id``.  The history graph builder must
        # therefore discover HDCA producers via the JobToOutput table,
        # not via HDCA.job_id alone.  Earlier versions of this helper
        # also set hdca.job_id which masked a real bug.
        assoc = model.JobToOutputDatasetCollectionAssociation(name=name, dataset_collection_instance=hdca)
        assoc.job_id = job.id
        session = self.trans.sa_session
        session.add(assoc)
        session.flush()
        return assoc

    def _link_implicit_collection(self, tool_request, hdca, output_name="output"):
        assoc = model.ToolRequestImplicitCollectionAssociation()
        assoc.tool_request_id = tool_request.id
        assoc.dataset_collection_id = hdca.id
        assoc.output_name = output_name
        session = self.trans.sa_session
        session.add(assoc)
        session.flush()
        return assoc

    def _build_linear_chain(self, history, length=3):
        """Build A -> tr1 -> B -> tr2 -> C -> ... Returns list of (hda, tool_request) pairs."""
        chain = []
        prev_hda = self._create_hda(history, name="input_0", extension="fastq")
        for i in range(length):
            tr = self._create_tool_request(history)
            job = self._create_job(tool_request=tr, tool_id=f"tool_{i}")
            self._link_job_input_hda(job, prev_hda)
            next_hda = self._create_hda(history, name=f"output_{i}", extension="bam")
            self._link_job_output_hda(job, next_hda)
            chain.append((prev_hda, tr, next_hda))
            prev_hda = next_hda
        return chain

    # ── History-scoped graph tests ──

    def test_empty_history(self):
        """Empty history produces empty graph."""
        history, _ = self._create_history()
        graph = self._build_graph(history)

        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0
        assert graph.truncated.scope_type == "recent"
        assert graph.truncated.seed_in_scope is None

    def test_standalone_datasets_included(self):
        """Standalone datasets (uploads) appear as isolated nodes."""
        history, _ = self._create_history()
        self._create_hda(history, name="uploaded.fastq")
        self._create_hda(history, name="another.bam")
        graph = self._build_graph(history)
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 0

    def test_full_history_graph(self):
        """Full history graph includes all items and edges."""
        history, _ = self._create_history()
        input_hda = self._create_hda(history, name="input.fastq", extension="fastq")
        output_hda = self._create_hda(history, name="output.bam", extension="bam")
        tr = self._create_tool_request(history)
        job = self._create_job(tool_request=tr, tool_id="bwa_mem")
        self._link_job_input_hda(job, input_hda)
        self._link_job_output_hda(job, output_hda)

        graph = self._build_graph(history)

        assert len(graph.nodes) == 3  # input + output + tool_request
        assert len(graph.edges) == 2  # dataset_input + dataset_output

        types = {n.type for n in graph.nodes}
        assert types == {"dataset", "tool_request"}

        edge_types = {e.type for e in graph.edges}
        assert edge_types == {"dataset_input", "dataset_output"}

    def test_disconnected_components(self):
        """Disconnected lineage branches are both included."""
        history, _ = self._create_history()
        # Branch 1
        hda1 = self._create_hda(history, name="input1")
        out1 = self._create_hda(history, name="output1")
        tr1 = self._create_tool_request(history)
        job1 = self._create_job(tool_request=tr1, tool_id="tool1")
        self._link_job_input_hda(job1, hda1)
        self._link_job_output_hda(job1, out1)

        # Branch 2 (disconnected)
        hda2 = self._create_hda(history, name="input2")
        out2 = self._create_hda(history, name="output2")
        tr2 = self._create_tool_request(history)
        job2 = self._create_job(tool_request=tr2, tool_id="tool2")
        self._link_job_input_hda(job2, hda2)
        self._link_job_output_hda(job2, out2)

        # Standalone upload
        self._create_hda(history, name="standalone")

        graph = self._build_graph(history)
        assert len(graph.nodes) == 7  # 5 datasets + 2 tool_requests
        assert len(graph.edges) == 4

    def test_data_fetch_excluded(self):
        """__DATA_FETCH__ tool_requests are excluded."""
        history, _ = self._create_history()
        tr = self._create_tool_request(history)
        self._create_job(tool_request=tr, tool_id="__DATA_FETCH__")

        graph = self._build_graph(history)
        tr_nodes = [n for n in graph.nodes if n.type == "tool_request"]
        assert len(tr_nodes) == 0

    def test_collection_node(self):
        """Collections appear as atomic nodes."""
        history, _ = self._create_history()
        hda1 = self._create_hda(history, name="el1")
        hda2 = self._create_hda(history, name="el2")
        element_identifiers = self.build_element_identifiers([hda1, hda2])
        hdca = self.collection_manager.create(
            self.trans, history, "test list", "list", element_identifiers=element_identifiers
        )
        tr = self._create_tool_request(history)
        job = self._create_job(tool_request=tr, tool_id="list_tool")
        self._link_job_input_hdca(job, hdca)

        graph = self._build_graph(history)
        collection_nodes = [n for n in graph.nodes if n.type == "collection"]
        assert len(collection_nodes) == 1
        assert collection_nodes[0].collection_type == "list"

    def test_element_input_resolves_to_top_level_item(self):
        """When a tool consumes an element HDA that is also a top-level history
        item, the input edge points to the dataset (not the collection)."""
        history, _ = self._create_history()
        hda1 = self._create_hda(history, name="el1")
        element_identifiers = self.build_element_identifiers([hda1])
        self.collection_manager.create(
            self.trans, history, "input list", "list", element_identifiers=element_identifiers
        )
        output_hda = self._create_hda(history, name="output")
        tr = self._create_tool_request(history)
        job = self._create_job(tool_request=tr, tool_id="element_tool")
        self._link_job_input_hda(job, hda1)  # Element but also top-level
        self._link_job_output_hda(job, output_hda)

        graph = self._build_graph(history)

        # hda1 is a top-level history item — input edge stays as dataset
        input_edges = [e for e in graph.edges if e.type == "dataset_input"]
        assert len(input_edges) >= 1
        assert any(e.source == self._encode("d", hda1.id) for e in input_edges)

    def test_edge_deduplication(self):
        """Multiple element edges collapse to one semantic edge."""
        history, _ = self._create_history()
        input_hda = self._create_hda(history, name="input")
        output_hda = self._create_hda(history, name="output")
        tr = self._create_tool_request(history)
        job1 = self._create_job(tool_request=tr, tool_id="tool")
        job2 = self._create_job(tool_request=tr, tool_id="tool")
        self._link_job_input_hda(job1, input_hda)
        self._link_job_input_hda(job2, input_hda)
        self._link_job_output_hda(job1, output_hda)
        self._link_job_output_hda(job2, output_hda)

        graph = self._build_graph(history)
        edge_keys = [(e.source, e.target, e.type) for e in graph.edges]
        assert len(edge_keys) == len(set(edge_keys))

    def test_dataset_node_fields(self):
        """Dataset nodes contain name, hid, and extension."""
        history, _ = self._create_history()
        hda = self._create_hda(history, name="test.fastq", extension="fastq")
        tr = self._create_tool_request(history)
        job = self._create_job(tool_request=tr, tool_id="tool")
        self._link_job_output_hda(job, hda)

        graph = self._build_graph(history)
        dataset_node = [n for n in graph.nodes if n.type == "dataset" and n.name == "test.fastq"][0]
        assert dataset_node.hid is not None
        assert dataset_node.extension == "fastq"

    def test_node_limit(self):
        """Node limit caps the graph at history scope."""
        history, _ = self._create_history()
        for i in range(10):
            self._create_hda(history, name=f"dataset_{i}")

        graph = self._build_graph(history, limit=5)
        assert len(graph.nodes) == 5
        assert graph.truncated.item_count_capped is True

    def test_deterministic_ordering(self):
        """Identical calls produce identical output."""
        history, _ = self._create_history()
        self._build_linear_chain(history, length=3)

        graph1 = self._build_graph(history)
        graph2 = self._build_graph(history)
        assert [n.id for n in graph1.nodes] == [n.id for n in graph2.nodes]
        assert [(e.source, e.target, e.type) for e in graph1.edges] == [
            (e.source, e.target, e.type) for e in graph2.edges
        ]

    def test_edge_types_semantic(self):
        """Edges use semantic types."""
        history, _ = self._create_history()
        input_hda = self._create_hda(history, name="input")
        hda1 = self._create_hda(history, name="el1")
        element_identifiers = self.build_element_identifiers([hda1])
        input_hdca = self.collection_manager.create(
            self.trans, history, "input list", "list", element_identifiers=element_identifiers
        )
        output_hda = self._create_hda(history, name="output")
        tr = self._create_tool_request(history)
        job = self._create_job(tool_request=tr, tool_id="tool")
        self._link_job_input_hda(job, input_hda)
        self._link_job_input_hdca(job, input_hdca)
        self._link_job_output_hda(job, output_hda)

        graph = self._build_graph(history)
        edge_types = {e.type for e in graph.edges}
        assert "dataset_input" in edge_types
        assert "collection_input" in edge_types
        assert "dataset_output" in edge_types

    def test_seed_subgraph_filter(self):
        """Seed parameter extracts a subgraph from the full graph."""
        history, _ = self._create_history()
        chain = self._build_linear_chain(history, length=3)
        # Add a disconnected standalone
        self._create_hda(history, name="standalone")

        full_graph = self._build_graph(history)
        seed = self._encode("d", chain[0][0].id)
        filtered = self._build_graph(history, seed=seed, direction="forward", depth=2)

        assert len(filtered.nodes) < len(full_graph.nodes)
        # Standalone should not be in filtered graph
        standalone_nodes = [n for n in filtered.nodes if n.name == "standalone"]
        assert len(standalone_nodes) == 0

    def test_seed_not_in_graph(self):
        """Seed referencing nonexistent node raises error."""
        history, _ = self._create_history()
        fake_seed = self._encode("d", 999999)
        with pytest.raises(RequestParameterInvalidException):
            self._build_graph(history, seed=fake_seed)

    def test_no_self_loops(self):
        """No edge has source == target."""
        history, _ = self._create_history()
        self._build_linear_chain(history, length=3)
        graph = self._build_graph(history)
        for e in graph.edges:
            assert e.source != e.target, f"Self-loop: {e.source}"

    def test_seed_scope_centers_on_item(self):
        """seed_scope centers the selection window on the specified item."""
        history, _ = self._create_history()
        # Create 10 standalone datasets
        hdas = [self._create_hda(history, name=f"dataset_{i}") for i in range(10)]

        # Use seed_scope to center on the middle item (limit=4 → should get ~4 items around it)
        middle = hdas[5]
        seed_scope = self._encode("d", middle.id)
        graph = self._build_graph(history, seed_scope=seed_scope, limit=4)

        assert len(graph.nodes) <= 4
        # The seed item must be in scope
        node_ids = {n.id for n in graph.nodes}
        assert seed_scope in node_ids
        assert graph.truncated.scope_type == "seed_centered"

    def test_seed_in_scope_true(self):
        """seed_in_scope is true when seed is in the constructed graph."""
        history, _ = self._create_history()
        chain = self._build_linear_chain(history, length=1)
        input_hda = chain[0][0]
        seed = self._encode("d", input_hda.id)
        graph = self._build_graph(history, seed=seed)
        assert graph.truncated.seed_in_scope is True

    def test_seed_in_scope_none_without_seed(self):
        """seed_in_scope is None when no seed is requested."""
        history, _ = self._create_history()
        self._create_hda(history, name="dataset")
        graph = self._build_graph(history)
        assert graph.truncated.seed_in_scope is None

    def test_seed_scope_not_found(self):
        """seed_scope with nonexistent item returns 422."""
        history, _ = self._create_history()
        self._create_hda(history, name="dataset")
        fake_scope = f"d{self.app.security.encode_id(99999)}"
        with pytest.raises(RequestParameterInvalidException):
            self._build_graph(history, seed_scope=fake_scope)

    def test_seed_scope_invalid_prefix(self):
        """seed_scope with invalid prefix returns 422."""
        history, _ = self._create_history()
        with pytest.raises(RequestParameterInvalidException):
            self._build_graph(history, seed_scope="x_invalid")

    # ── Step 5: Validation tests ──

    def test_map_over_input_edges(self):
        """Element inputs from a collection produce dataset_input edges to the consuming execution."""
        history, _ = self._create_history()
        el1 = self._create_hda(history, name="el1")
        el2 = self._create_hda(history, name="el2")
        element_identifiers = self.build_element_identifiers([el1, el2])
        self.collection_manager.create(
            self.trans, history, "input list", "list", element_identifiers=element_identifiers
        )
        output_hda = self._create_hda(history, name="mapped_output")
        tr = self._create_tool_request(history)
        job = self._create_job(tool_request=tr, tool_id="map_tool")
        self._link_job_input_hda(job, el1, name="input")
        self._link_job_input_hda(job, el2, name="input")
        self._link_job_output_hda(job, output_hda)

        graph = self._build_graph(history)

        tr_enc = self._encode("r", tr.id)
        # Consumer edges: selected element items → execution
        input_edges = [e for e in graph.edges if e.target == tr_enc and "input" in e.type]
        assert len(input_edges) == 2  # one per element
        # Producer edge: execution → output
        output_edges = [e for e in graph.edges if e.source == tr_enc]
        assert len(output_edges) == 1

    def test_map_over_output_edges(self):
        """Element outputs produce dataset_output edges from the producing execution."""
        history, _ = self._create_history()
        input_hda = self._create_hda(history, name="input")
        out_el1 = self._create_hda(history, name="out_el1")
        out_el2 = self._create_hda(history, name="out_el2")
        tr = self._create_tool_request(history)
        job = self._create_job(tool_request=tr, tool_id="map_tool")
        self._link_job_input_hda(job, input_hda)
        self._link_job_output_hda(job, out_el1)
        self._link_job_output_hda(job, out_el2)

        graph = self._build_graph(history)

        tr_enc = self._encode("r", tr.id)
        # Producer edges: execution → each output element
        output_edges = [e for e in graph.edges if e.source == tr_enc and "output" in e.type]
        assert len(output_edges) == 2
        # Consumer edge: input → execution
        input_edges = [e for e in graph.edges if e.target == tr_enc]
        assert len(input_edges) == 1

    def test_deleted_input_not_in_graph(self):
        """A deleted input HDA is filtered from the graph (not a node).

        The bounded model excludes deleted items from both the initial
        scope and the closure set (unless include_deleted=True).
        """
        history, _ = self._create_history()
        dataset = self.dataset_manager.create()
        execution_hda = self.hda_manager.create(name="execution", history=history, dataset=dataset)
        execution_hda.deleted = True
        visible_copy = self.hda_manager.create(name="visible_copy", history=history, dataset=dataset)
        visible_copy.visible = True
        output_hda = self._create_hda(history, name="output")
        self.trans.sa_session.flush()

        tr = self._create_tool_request(history)
        job = self._create_job(tool_request=tr, tool_id="copy_tool")
        self._link_job_input_hda(job, execution_hda)
        self._link_job_output_hda(job, output_hda)

        graph = self._build_graph(history)

        node_ids = {n.id for n in graph.nodes}
        assert self._encode("d", execution_hda.id) not in node_ids
        assert self._encode("d", visible_copy.id) in node_ids
        assert self._encode("d", output_hda.id) in node_ids

    def test_hidden_non_element_hda_included(self):
        """Hidden HDAs that are NOT collection elements appear as graph nodes."""
        history, _ = self._create_history()
        hidden_hda = self._create_hda(history, name="hidden_intermediate")
        hidden_hda.visible = False
        self.trans.sa_session.flush()
        output_hda = self._create_hda(history, name="output")

        tr = self._create_tool_request(history)
        job = self._create_job(tool_request=tr, tool_id="tool")
        self._link_job_input_hda(job, hidden_hda)
        self._link_job_output_hda(job, output_hda)

        graph = self._build_graph(history)

        hidden_enc = self._encode("d", hidden_hda.id)
        node_ids = {n.id for n in graph.nodes}
        assert hidden_enc in node_ids

    def test_closure_completes_tool_requests_at_seed_boundary(self):
        """Closure rule: a tool_request whose other side falls outside
        the seed window is still structurally complete in the response.

        Old behavior: tool_request kept, but its boundary item omitted —
        the visualization showed a half-connected execution node.
        New behavior (closure rule, locked 2026-04-09): the boundary
        item is pulled in by Stage 5 closure expansion so the
        tool_request always has all its top-level inputs and outputs.
        """
        history, _ = self._create_history()
        input_hda = self._create_hda(history, name="input")
        output_hda = self._create_hda(history, name="output")
        tr = self._create_tool_request(history)
        job = self._create_job(tool_request=tr, tool_id="tool")
        self._link_job_input_hda(job, input_hda)
        self._link_job_output_hda(job, output_hda)

        # Use limit=1 — seed window holds only one item.  Closure must
        # pull in the other side so the tool_request is complete.
        graph = self._build_graph(history, limit=1)

        tr_nodes = [n for n in graph.nodes if n.type == "tool_request"]
        assert len(tr_nodes) == 1
        assert graph.truncated.item_count_capped is True

        node_ids = {n.id for n in graph.nodes}
        assert self._encode("d", input_hda.id) in node_ids
        assert self._encode("d", output_hda.id) in node_ids

        # The tool_request has BOTH input and output edges.
        tr_enc = self._encode("r", tr.id)
        in_edges = [e for e in graph.edges if e.target == tr_enc and e.type == "dataset_input"]
        out_edges = [e for e in graph.edges if e.source == tr_enc and e.type == "dataset_output"]
        assert len(in_edges) == 1, "tool_request must have its top-level input edge after closure"
        assert len(out_edges) == 1, "tool_request must have its top-level output edge after closure"

    def test_deleted_items_with_include_deleted(self):
        """Deleted items appear when include_deleted=True."""
        history, _ = self._create_history()
        hda = self._create_hda(history, name="to_delete")
        hda.deleted = True
        self.trans.sa_session.flush()

        # Without include_deleted: not included
        graph = self._build_graph(history)
        assert len(graph.nodes) == 0

        # With include_deleted: included
        builder = HistoryGraphBuilder(
            sa_session=self.trans.sa_session,
            security=self.app.security,
            history_id=history.id,
            include_deleted=True,
        )
        graph = builder.build()
        assert len(graph.nodes) == 1

    def test_determinism_identical_requests(self):
        """Identical requests produce identical output."""
        history, _ = self._create_history()
        self._build_linear_chain(history, length=3)

        graph1 = self._build_graph(history)
        graph2 = self._build_graph(history)

        assert [n.id for n in graph1.nodes] == [n.id for n in graph2.nodes]
        assert [(e.source, e.target, e.type) for e in graph1.edges] == [
            (e.source, e.target, e.type) for e in graph2.edges
        ]

    def test_expanding_limit_generally_additive(self):
        """Expanding limit is generally additive for standalone datasets.

        Note: collapse rules (map-over, representability) mean this is not
        a hard invariant — adding items to scope can change which tool_requests
        are representable. This test covers the simple case.
        """
        history, _ = self._create_history()
        for i in range(8):
            self._create_hda(history, name=f"ds_{i}")

        small = self._build_graph(history, limit=4)
        large = self._build_graph(history, limit=8)

        small_ids = {n.id for n in small.nodes}
        large_ids = {n.id for n in large.nodes}
        # All nodes in the small graph should also be in the large graph
        assert small_ids.issubset(large_ids)
        assert len(large_ids) >= len(small_ids)

    # ── Zip / Unzip / Collection tests ──

    def test_zip_collection(self):
        """Zip: two input datasets → tool → one output paired collection.

        Verifies: dataset_input edges from both inputs, collection_output to
        the paired collection, no self-loops, no false edges.
        """
        history, _ = self._create_history()
        fwd = self._create_hda(history, name="forward.fastq")
        rev = self._create_hda(history, name="reverse.fastq")

        # Output: paired collection containing elements referencing fwd/rev
        element_identifiers = self.build_element_identifiers([fwd, rev])
        output_hdca = self.collection_manager.create(
            self.trans, history, "zipped pairs", "paired", element_identifiers=element_identifiers
        )

        tr = self._create_tool_request(history)
        job = self._create_job(tool_request=tr, tool_id="__ZIP_COLLECTION__")
        self._link_job_input_hda(job, fwd, name="forward")
        self._link_job_input_hda(job, rev, name="reverse")
        self._link_job_output_hdca(job, output_hdca)

        graph = self._build_graph(history)

        tr_enc = self._encode("r", tr.id)
        fwd_enc = self._encode("d", fwd.id)
        rev_enc = self._encode("d", rev.id)
        coll_enc = self._encode("c", output_hdca.id)

        # Two dataset_input edges
        input_edges = [e for e in graph.edges if e.target == tr_enc and e.type == "dataset_input"]
        input_sources = {e.source for e in input_edges}
        assert input_sources == {fwd_enc, rev_enc}

        # One collection_output edge
        output_edges = [e for e in graph.edges if e.source == tr_enc and e.type == "collection_output"]
        assert len(output_edges) == 1
        assert output_edges[0].target == coll_enc

        # No self-loops
        for e in graph.edges:
            assert e.source != e.target

    def test_unzip_collection(self):
        """Unzip: one input paired collection → tool → two output datasets.

        Verifies: collection_input from the paired collection, dataset_output
        edges to both outputs, no false input edges from output datasets.
        """
        history, _ = self._create_history()
        el1 = self._create_hda(history, name="el1")
        el2 = self._create_hda(history, name="el2")
        element_identifiers = self.build_element_identifiers([el1, el2])
        input_hdca = self.collection_manager.create(
            self.trans, history, "paired input", "paired", element_identifiers=element_identifiers
        )

        out1 = self._create_hda(history, name="unzipped_1")
        out2 = self._create_hda(history, name="unzipped_2")

        tr = self._create_tool_request(history)
        job = self._create_job(tool_request=tr, tool_id="__UNZIP_COLLECTION__")
        self._link_job_input_hdca(job, input_hdca)
        self._link_job_output_hda(job, out1, name="forward")
        self._link_job_output_hda(job, out2, name="reverse")

        graph = self._build_graph(history)

        tr_enc = self._encode("r", tr.id)
        coll_enc = self._encode("c", input_hdca.id)
        out1_enc = self._encode("d", out1.id)
        out2_enc = self._encode("d", out2.id)

        # One collection_input edge
        input_edges = [e for e in graph.edges if e.target == tr_enc and "input" in e.type]
        assert len(input_edges) == 1
        assert input_edges[0].source == coll_enc
        assert input_edges[0].type == "collection_input"

        # Two dataset_output edges
        output_edges = [e for e in graph.edges if e.source == tr_enc and e.type == "dataset_output"]
        output_targets = {e.target for e in output_edges}
        assert output_targets == {out1_enc, out2_enc}

        # No self-loops
        for e in graph.edges:
            assert e.source != e.target

    def test_unzip_with_shared_dataset_ids(self):
        """Unzip where outputs share dataset_id with input collection elements.

        When a tool has a collection input AND element-level dataset inputs
        (some Galaxy wrappers do this), and resolved dataset inputs point to
        outputs, the false input edges must be suppressed.
        """
        history, _ = self._create_history()
        # Shared datasets: elements and outputs reference the same Dataset
        ds1 = self.dataset_manager.create()
        ds2 = self.dataset_manager.create()

        el1 = self.hda_manager.create(name="el1", history=history, dataset=ds1)
        el2 = self.hda_manager.create(name="el2", history=history, dataset=ds2)
        element_identifiers = self.build_element_identifiers([el1, el2])
        input_hdca = self.collection_manager.create(
            self.trans, history, "paired input", "paired", element_identifiers=element_identifiers
        )

        # Outputs share dataset_id with elements (copy semantics)
        out1 = self.hda_manager.create(name="out1", history=history, dataset=ds1)
        out2 = self.hda_manager.create(name="out2", history=history, dataset=ds2)
        self.trans.sa_session.flush()

        tr = self._create_tool_request(history)
        job = self._create_job(tool_request=tr, tool_id="__UNZIP_COLLECTION__")
        self._link_job_input_hdca(job, input_hdca)
        # Also link elements as individual inputs (some wrappers do this)
        self._link_job_input_hda(job, el1, name="forward")
        self._link_job_input_hda(job, el2, name="reverse")
        self._link_job_output_hda(job, out1, name="forward")
        self._link_job_output_hda(job, out2, name="reverse")

        graph = self._build_graph(history)

        tr_enc = self._encode("r", tr.id)
        out1_enc = self._encode("d", out1.id)
        out2_enc = self._encode("d", out2.id)

        # Element inputs that resolve to outputs should be suppressed
        # (collection input exists + resolved points to output → suppress)
        input_edges = [e for e in graph.edges if e.target == tr_enc and "input" in e.type]
        # Should only have collection_input, not dataset_input pointing to out1/out2
        for e in input_edges:
            assert e.source not in (out1_enc, out2_enc), f"False input edge from output: {e.source} → {e.target}"

        # No self-loops
        for e in graph.edges:
            assert e.source != e.target

    def test_single_element_collection(self):
        """Collection with a single element behaves correctly."""
        history, _ = self._create_history()
        el = self._create_hda(history, name="single_element")
        element_identifiers = self.build_element_identifiers([el])
        hdca = self.collection_manager.create(
            self.trans, history, "singleton", "list", element_identifiers=element_identifiers
        )
        output_hda = self._create_hda(history, name="output")

        tr = self._create_tool_request(history)
        job = self._create_job(tool_request=tr, tool_id="single_tool")
        self._link_job_input_hdca(job, hdca)
        self._link_job_output_hda(job, output_hda)

        graph = self._build_graph(history)

        coll_enc = self._encode("c", hdca.id)
        tr_enc = self._encode("r", tr.id)

        # Collection input edge exists
        input_edges = [e for e in graph.edges if e.target == tr_enc and e.type == "collection_input"]
        assert len(input_edges) == 1
        assert input_edges[0].source == coll_enc

        # No self-loops
        for e in graph.edges:
            assert e.source != e.target

    def test_large_collection_no_explosion(self):
        """Collection with many elements does not cause graph explosion.

        The graph should contain one collection node, not individual element nodes.
        Node count must stay bounded regardless of element count.
        """
        history, _ = self._create_history()
        # Create collection with 100 elements (using 100 to keep test fast;
        # the principle is the same as 1000+)
        elements = [self._create_hda(history, name=f"el_{i}") for i in range(100)]
        element_identifiers = self.build_element_identifiers(elements)
        hdca = self.collection_manager.create(
            self.trans, history, "big list", "list", element_identifiers=element_identifiers
        )
        output_hda = self._create_hda(history, name="output")

        tr = self._create_tool_request(history)
        job = self._create_job(tool_request=tr, tool_id="big_tool")
        self._link_job_input_hdca(job, hdca)
        self._link_job_output_hda(job, output_hda)

        graph = self._build_graph(history)

        # Collection is one node, not 100
        collection_nodes = [n for n in graph.nodes if n.type == "collection"]
        assert len(collection_nodes) == 1

        # Total nodes: 100 element HDAs (hidden, removed as elements) +
        # 1 collection + 1 output + 1 tool_request = 3, but the element HDAs
        # are visible top-level items too, so they may appear. The key invariant
        # is that edge count stays bounded — one collection_input, not 100 dataset_inputs.
        input_edges = [e for e in graph.edges if e.target == self._encode("r", tr.id) and "input" in e.type]
        assert len(input_edges) == 1
        assert input_edges[0].type == "collection_input"

        # No self-loops
        for e in graph.edges:
            assert e.source != e.target

    # ── Remaining validation tests ──

    def test_multiple_copies_same_dataset(self):
        """Multiple HDAs sharing the same dataset_id appear as distinct nodes.

        Copy resolution only applies to execution artifacts outside scope.
        When both copies are in scope, they remain separate nodes.
        """
        history, _ = self._create_history()
        dataset = self.dataset_manager.create()
        copy1 = self.hda_manager.create(name="copy_1", history=history, dataset=dataset)
        copy2 = self.hda_manager.create(name="copy_2", history=history, dataset=dataset)
        copy3 = self.hda_manager.create(name="copy_3", history=history, dataset=dataset)
        self.trans.sa_session.flush()

        graph = self._build_graph(history)

        node_ids = {n.id for n in graph.nodes}
        assert self._encode("d", copy1.id) in node_ids
        assert self._encode("d", copy2.id) in node_ids
        assert self._encode("d", copy3.id) in node_ids
        assert len(graph.nodes) == 3

    def test_closure_resolves_hidden_element_input_to_parent_collection(self):
        """Real-data bug fix: a tool consumes a hidden element HDA
        directly via JobToInputDatasetAssociation (not via the
        element-association table).  The element HDA is filtered out
        by Rule N3, so closure must walk DCE → DC → HDCA via
        HDCA.collection_id and surface the parent collection as the
        user-visible input.

        Without this, tools like Convert that operate on the 'forward'
        half of a paired collection appear with no inputs at all.
        """
        history, _ = self._create_history()
        # Create a paired collection with two element HDAs.  These
        # element HDAs are hidden and visible-False (production
        # behaviour for collection elements).
        forward = self._create_hda(history, name="forward.fastq")
        reverse = self._create_hda(history, name="reverse.fastq")
        forward.visible = False
        reverse.visible = False
        element_identifiers = [
            {"name": "forward", "src": "hda", "id": forward.id},
            {"name": "reverse", "src": "hda", "id": reverse.id},
        ]
        paired = self.collection_manager.create(
            self.trans, history, "paired", "paired", element_identifiers=element_identifiers
        )
        self.trans.sa_session.flush()

        # Convert tool consumes the 'forward' element HDA directly.
        out_hda = self._create_hda(history, name="converted")
        tr = self._create_tool_request(history)
        job = self._create_job(tool_request=tr, tool_id="Convert")
        self._link_job_input_hda(job, forward)
        self._link_job_output_hda(job, out_hda)

        graph = self._build_graph(history)

        tr_enc = self._encode("r", tr.id)
        # The tool_request must have an input edge — and it should be a
        # collection_input edge to the parent paired collection, not a
        # dataset_input edge to the hidden forward element (which N3
        # filters out as not-top-level).
        in_edges = [e for e in graph.edges if e.target == tr_enc]
        assert (
            len(in_edges) == 1
        ), "Tool consuming hidden element HDA must have its parent collection surfaced as a closure input"
        edge = in_edges[0]
        assert edge.type == "collection_input"
        assert edge.source == self._encode("c", paired.id)

    def test_jtoda_only_output_caught(self):
        """Real-data bug fix: tools like Unzip claim existing datasets
        as outputs via JobToOutputDatasetAssociation but do NOT update
        Dataset.job_id.  The Rule N1 reverse query (Dataset.job_id)
        misses these — only the JobToOutputDatasetAssociation pathway
        finds them.

        Without this, Unzip-like tools appear with no outputs at all.
        """
        history, _ = self._create_history()
        # Original upload: an existing HDA whose Dataset.job_id points
        # at a different (upload) job.
        upload_job = self._create_job(tool_id="upload1")
        original = self._create_hda(history, name="paired.fastq")
        original.dataset.job_id = upload_job.id

        # The unwrapped HDA: same Dataset (so Dataset.job_id == upload_job.id)
        # but a different HDA in the same history.
        unwrapped = self.hda_manager.create(name="unwrapped", history=history, dataset=original.dataset)
        self.trans.sa_session.flush()

        # The "Unzip" tool claims unwrapped as its output via the
        # JobToOutputDatasetAssociation table only — without setting
        # Dataset.job_id (since the dataset already had one).
        tr = self._create_tool_request(history)
        unzip_job = self._create_job(tool_request=tr, tool_id="__UNZIP_COLLECTION__")
        self._link_job_input_hda(unzip_job, original)
        # Manually create the JTODA row WITHOUT touching Dataset.job_id.
        assoc = model.JobToOutputDatasetAssociation(name="forward", dataset=unwrapped)
        assoc.job_id = unzip_job.id
        self.trans.sa_session.add(assoc)
        self.trans.sa_session.flush()
        # Sanity check: Dataset.job_id is the upload job, NOT the unzip job.
        assert unwrapped.dataset.job_id == upload_job.id

        graph = self._build_graph(history)

        tr_enc = self._encode("r", tr.id)
        out_edges = [e for e in graph.edges if e.source == tr_enc and e.type == "dataset_output"]
        unwrapped_enc = self._encode("d", unwrapped.id)
        assert any(e.target == unwrapped_enc for e in out_edges), (
            "Unzip-style tools claiming an existing HDA via JobToOutputDatasetAssociation "
            "must produce an output edge even when Dataset.job_id points elsewhere"
        )

    def test_n2_jodca_only_hdca_has_producer_edge(self):
        """Rule N2 branch (b): an HDCA with no ``job_id``, no implicit
        collection chain, and no TRICA row — only a
        ``JobToOutputDatasetCollectionAssociation`` row — must still
        get a producer edge.

        This is the most common production case for non-implicit
        collection outputs (``Job.add_output_dataset_collection``).
        Earlier versions of the builder missed it because the test
        helper artificially set ``hdca.job_id`` and masked the gap.
        """
        history, _ = self._create_history()
        hda = self._create_hda(history, name="el")
        element_identifiers = self.build_element_identifiers([hda])
        hdca = self.collection_manager.create(
            self.trans, history, "out list", "list", element_identifiers=element_identifiers
        )
        # Verify production-mirroring helper does NOT set HDCA.job_id.
        assert hdca.job_id is None

        tr = self._create_tool_request(history)
        job = self._create_job(tool_request=tr, tool_id="zip_tool")
        self._link_job_input_hda(job, hda)
        # The helper writes a JobToOutputDatasetCollectionAssociation
        # but does not set HDCA.job_id (matches production).
        self._link_job_output_hdca(job, hdca)

        graph = self._build_graph(history)

        tr_enc = self._encode("r", tr.id)
        hdca_enc = self._encode("c", hdca.id)
        producer_edges = {(e.source, e.target) for e in graph.edges if e.type == "collection_output"}
        assert (
            tr_enc,
            hdca_enc,
        ) in producer_edges, (
            "HDCA producer edge must come from JobToOutputDatasetCollectionAssociation even when HDCA.job_id is None"
        )

    def test_n2_ambiguous_hdca_producer_has_node_but_no_edge(self):
        """Rule N2 dedupe fallback: when an HDCA resolves to ≥2 distinct
        producer tool_request_ids across the UNION branches, the builder
        emits no producer edge, keeps the HDCA as a node, and increments
        the internal ``_hdca_producer_ambiguity_count``.

        This is the deliberately conservative behavior — we do not pick
        an arbitrary winner at the response level.
        """
        from galaxy.managers.history_graph import HistoryGraphBuilder

        history, _ = self._create_history()
        in_hda = self._create_hda(history, name="input")

        # Build an HDCA with TWO disagreeing producer attributions:
        # (a) HDCA.job_id → tr_direct
        # (b) HDCA.implicit_collection_jobs_id → ICJ → job_b → tr_implicit
        # These resolve to different tool_request_ids → ambiguous.
        el = self._create_hda(history, name="el")
        element_identifiers = self.build_element_identifiers([el])
        hdca = self.collection_manager.create(
            self.trans, history, "ambiguous out", "list", element_identifiers=element_identifiers
        )

        tr_direct = self._create_tool_request(history)
        job_direct = self._create_job(tool_request=tr_direct, tool_id="tool_direct")
        self._link_job_input_hda(job_direct, in_hda)
        hdca.job_id = job_direct.id  # direct branch

        tr_implicit = self._create_tool_request(history)
        job_implicit = self._create_job(tool_request=tr_implicit, tool_id="tool_implicit")
        self._link_job_input_hda(job_implicit, in_hda)
        icj = model.ImplicitCollectionJobs(populated_state="ok")
        self.trans.sa_session.add(icj)
        self.trans.sa_session.flush()
        icja = model.ImplicitCollectionJobsJobAssociation()
        icja.implicit_collection_jobs_id = icj.id
        icja.job_id = job_implicit.id
        icja.order_index = 0
        self.trans.sa_session.add(icja)
        hdca.implicit_collection_jobs_id = icj.id  # implicit branch
        self.trans.sa_session.flush()

        builder = HistoryGraphBuilder(
            sa_session=self.trans.sa_session,
            security=self.app.security,
            history_id=history.id,
            limit=500,
        )
        graph = builder.build()

        hdca_enc = self._encode("c", hdca.id)
        node_ids = {n.id for n in graph.nodes}
        assert hdca_enc in node_ids, "Ambiguous HDCA should still be a node"

        # No producer edge for this HDCA.
        producer_targets = {e.target for e in graph.edges if e.type == "collection_output"}
        assert hdca_enc not in producer_targets, "Ambiguous HDCA must NOT get a producer edge (N2 fallback)"

    def test_seed_filter_issues_no_extra_queries(self):
        """Stage 9 lock: ``_extract_subgraph`` operates only on the
        already-materialized in-memory graph and must NOT trigger any
        additional DB queries.

        Approach: count SQL statements issued during ``build()`` via a
        SQLAlchemy event listener.  Assert that the seeded run does not
        issue MORE queries than the unseeded run (Stage 9 may not add
        DB access — it may incidentally avoid one due to autoflush
        ordering, which is fine).  Also assert the seeded result is a
        subset of the unseeded result (proving it's a pure post-filter,
        not a different construction path).
        """
        from sqlalchemy import event

        history, _ = self._create_history()
        # Build a small chain so there's something to filter.
        chain = self._build_linear_chain(history, length=3)
        # Seed on the middle dataset in the chain.
        seed_hda = chain[1][0]
        seed_enc = self._encode("d", seed_hda.id)

        # Flush any pending state so neither build triggers an
        # incidental autoflush during the measurement window.
        self.trans.sa_session.flush()

        engine = self.trans.sa_session.get_bind()

        counter = {"n": 0}

        def _count(_conn, _cursor, _statement, _parameters, _context, _executemany):
            counter["n"] += 1

        event.listen(engine, "before_cursor_execute", _count)
        try:
            self.trans.sa_session.flush()
            counter["n"] = 0
            unseeded = self._build_graph(history)
            unseeded_count = counter["n"]
            unseeded_ids = {n.id for n in unseeded.nodes}

            self.trans.sa_session.flush()
            counter["n"] = 0
            seeded = self._build_graph(history, seed=seed_enc, depth=20)
            seeded_count = counter["n"]
            seeded_ids = {n.id for n in seeded.nodes}
        finally:
            event.remove(engine, "before_cursor_execute", _count)

        # The Stage 9 lock requires that seeded never issues MORE queries
        # than unseeded — _extract_subgraph must add zero DB access.
        assert seeded_count <= unseeded_count, (
            f"Seeded build issued {seeded_count} SQL statements, "
            f"unseeded issued {unseeded_count}. Stage 9 must not trigger extra DB access."
        )
        assert seeded_ids.issubset(
            unseeded_ids
        ), "Seeded result must be a subset of unseeded — seed is a pure post-filter"
        assert seed_enc in seeded_ids, "Seed itself should be in the seeded result"

    def test_closure_invariant_no_partial_executions(self):
        """Closure invariant: every execution node in the graph has all
        of its top-level inputs and outputs (in this history) present
        as nodes, with the corresponding edges materialized.

        Constructs a multi-tool history at the seed-window boundary so
        that, without closure, several tool_requests would have missing
        sides.  Asserts that EVERY tool_request in the response has a
        complete neighborhood.
        """
        history, _ = self._create_history()
        # 5-step chain: hda0 → tr0 → hda1 → tr1 → hda2 → tr2 → hda3 → tr3 → hda4 → tr4 → hda5
        chain = self._build_linear_chain(history, length=5)

        # Center the seed window on the middle hda with limit=1, so the
        # window holds just that one item and closure must complete the
        # tool_request from there.
        middle_hda = chain[2][0]
        graph = self._build_graph(history, seed_scope=self._encode("d", middle_hda.id), limit=1)

        node_ids = {n.id for n in graph.nodes}
        tr_nodes = [n for n in graph.nodes if n.type == "tool_request"]
        assert len(tr_nodes) >= 1, "Expected at least one tool_request via closure"

        # For each tool_request in the graph, all its incident edges
        # must reference items that are also nodes in the graph.
        for tr_node in tr_nodes:
            connected_items = {e.source for e in graph.edges if e.target == tr_node.id} | {
                e.target for e in graph.edges if e.source == tr_node.id
            }
            for item_id in connected_items:
                assert item_id in node_ids, (
                    f"Tool_request {tr_node.id} has edge referencing missing node {item_id} — "
                    "closure invariant violated"
                )
            assert len(connected_items) >= 2, (
                f"Tool_request {tr_node.id} has only {len(connected_items)} connected items — "
                "expected at least one input and one output after closure"
            )

    def test_stability_new_items_shift_recent_window(self):
        """Adding new items shifts the recent-overview window.

        The most recent N items are selected. Adding a new item pushes
        the oldest item out of the window when limit is reached.
        """
        history, _ = self._create_history()
        original = [self._create_hda(history, name=f"ds_{i}") for i in range(5)]

        # All 5 in scope
        graph1 = self._build_graph(history, limit=5)
        ids1 = {n.id for n in graph1.nodes}
        assert len(ids1) == 5

        # Add a new item — now 6 total, limit=5 means oldest drops out
        new_hda = self._create_hda(history, name="ds_new")
        graph2 = self._build_graph(history, limit=5)
        ids2 = {n.id for n in graph2.nodes}
        assert len(ids2) == 5

        # The new item is in scope
        assert self._encode("d", new_hda.id) in ids2
        # The oldest original item is no longer in scope
        assert self._encode("d", original[0].id) not in ids2
        # The rest of the original items are still in scope
        for hda in original[1:]:
            assert self._encode("d", hda.id) in ids2


# ── Scalability / Boundedness Tests ──

GRAPH_SCALE_HISTORY_SIZE = int(os.environ.get("GRAPH_SCALE_HISTORY_SIZE", 500))
GRAPH_SCALE_CHAIN_LENGTH = int(os.environ.get("GRAPH_SCALE_CHAIN_LENGTH", 100))
GRAPH_SCALE_COLLECTION_COUNT = int(os.environ.get("GRAPH_SCALE_COLLECTION_COUNT", 10))
GRAPH_SCALE_COLLECTION_SIZE = int(os.environ.get("GRAPH_SCALE_COLLECTION_SIZE", 50))


class TestHistoryGraphBuilderBoundedness(BaseTestCase, CreatesCollectionsMixin):
    """Scalability and boundedness tests for HistoryGraphBuilder.

    These validate that the builder produces bounded, structurally correct output
    on larger synthetic histories. They assert shape and boundedness, not timing.
    Sizes are env-configurable: GRAPH_SCALE_HISTORY_SIZE, GRAPH_SCALE_CHAIN_LENGTH,
    GRAPH_SCALE_COLLECTION_COUNT, GRAPH_SCALE_COLLECTION_SIZE.
    """

    def set_up_managers(self):
        super().set_up_managers()
        self.dataset_manager = self.app[DatasetManager]
        self.hda_manager = self.app[HDAManager]
        self.history_manager = self.app[HistoryManager]
        self.collection_manager = self.app[DatasetCollectionManager]

    def _build_graph(self, history, **kwargs):
        builder = HistoryGraphBuilder(
            sa_session=self.trans.sa_session,
            security=self.app.security,
            history_id=history.id,
            **kwargs,
        )
        return builder.build()

    def _encode(self, prefix, db_id):
        return f"{prefix}{self.app.security.encode_id(db_id)}"

    def _create_history(self):
        user = self.user_manager.create(**_next_user_data())
        self.trans.set_user(user)
        return self.history_manager.create(name="scale_history", user=user), user

    def _create_hda(self, history, name="ds", extension="txt"):
        hda = self.hda_manager.create(name=name, history=history, dataset=self.dataset_manager.create())
        hda.extension = extension
        self.trans.sa_session.flush()
        return hda

    def _create_tool_source(self):
        ts = model.ToolSource()
        ts.hash = "abc123"
        ts.source = {"xml": "<tool/>"}
        ts.source_class = "XmlToolSource"
        session = self.trans.sa_session
        session.add(ts)
        session.flush()
        return ts

    def _create_tool_request(self, history):
        ts = self._create_tool_source()
        tr = model.ToolRequest()
        tr.tool_source_id = ts.id
        tr.history_id = history.id
        tr.request = {}
        tr.state = "submitted"
        session = self.trans.sa_session
        session.add(tr)
        session.flush()
        return tr

    def _create_job(self, tool_request, tool_id="test_tool"):
        job = model.Job()
        job.tool_id = tool_id
        job.tool_version = "1.0"
        job.tool_request_id = tool_request.id
        session = self.trans.sa_session
        session.add(job)
        session.flush()
        return job

    def _append_payload_input(self, job, ref):
        if job.tool_request_id is None:
            return
        tr = self.trans.sa_session.get(model.ToolRequest, job.tool_request_id)
        if tr is None:
            return
        payload = dict(tr.request) if isinstance(tr.request, dict) else {}
        inputs = list(payload.get("inputs", []))
        inputs.append(ref)
        payload["inputs"] = inputs
        tr.request = payload

    def _link_job_input_hda(self, job, hda, name="input"):
        assoc = model.JobToInputDatasetAssociation(name=name, dataset=hda)
        assoc.job_id = job.id
        self._append_payload_input(job, {"src": "hda", "id": hda.id})
        self.trans.sa_session.add(assoc)
        self.trans.sa_session.flush()

    def _link_job_output_hda(self, job, hda, name="output"):
        assoc = model.JobToOutputDatasetAssociation(name=name, dataset=hda)
        assoc.job_id = job.id
        self.trans.sa_session.add(assoc)
        self.trans.sa_session.flush()

    def _link_job_input_hdca(self, job, hdca, name="input"):
        assoc = model.JobToInputDatasetCollectionAssociation(name=name, dataset_collection=hdca)
        assoc.job_id = job.id
        self._append_payload_input(job, {"src": "hdca", "id": hdca.id})
        self.trans.sa_session.add(assoc)
        self.trans.sa_session.flush()

    def _link_job_output_hdca(self, job, hdca, name="output"):
        assoc = model.JobToOutputDatasetCollectionAssociation(name=name, dataset_collection_instance=hdca)
        assoc.job_id = job.id
        self.trans.sa_session.add(assoc)
        self.trans.sa_session.flush()

    def _link_implicit_collection(self, tool_request, hdca):
        assoc = model.ToolRequestImplicitCollectionAssociation()
        assoc.tool_request_id = tool_request.id
        assoc.dataset_collection_id = hdca.id
        assoc.output_name = "output"
        self.trans.sa_session.add(assoc)
        self.trans.sa_session.flush()

    # ── Test cases ──

    def test_large_standalone_history(self):
        """N standalone HDAs with bounded limit.

        Assert: node count = min(N, limit), no edges, scope metadata valid.
        """
        n = GRAPH_SCALE_HISTORY_SIZE
        limit = 200
        history, _ = self._create_history()
        for i in range(n):
            self._create_hda(history, name=f"ds_{i}")

        graph = self._build_graph(history, limit=limit)

        assert len(graph.nodes) == min(n, limit)
        assert len(graph.edges) == 0
        assert graph.truncated.item_count_capped == (n > limit)

    def test_deep_linear_chain(self):
        """N-step linear chain: A→tr→B→tr→C→...

        Assert: bounded by limit, edges ≤ 2× representable TRs for this
        linear shape (each TR has exactly one dataset_input + one dataset_output).
        """
        n = GRAPH_SCALE_CHAIN_LENGTH
        limit = 50
        history, _ = self._create_history()

        prev = self._create_hda(history, name="input_0")
        for i in range(n):
            tr = self._create_tool_request(history)
            job = self._create_job(tr, tool_id=f"tool_{i}")
            self._link_job_input_hda(job, prev)
            out = self._create_hda(history, name=f"output_{i}")
            self._link_job_output_hda(job, out)
            prev = out

        graph = self._build_graph(history, limit=limit)

        # Items bounded by limit + closure (payload-driven closure can pull
        # in at most one extra input per representable TR).
        item_nodes = [nd for nd in graph.nodes if nd.type != "tool_request"]
        tr_nodes = [nd for nd in graph.nodes if nd.type == "tool_request"]
        assert len(item_nodes) <= limit + len(tr_nodes)

        # Each TR has at least one edge
        for tr_node in tr_nodes:
            tr_edges = [e for e in graph.edges if e.target == tr_node.id or e.source == tr_node.id]
            assert len(tr_edges) >= 1

    def test_collection_heavy_map_over(self):
        """M collections × K elements each, with map-over tool execution.

        Assert: no element-level dataset explosion, collection-level edges
        present, hidden element HDAs suppressed as nodes.
        """
        m = GRAPH_SCALE_COLLECTION_COUNT
        k = GRAPH_SCALE_COLLECTION_SIZE
        history, _ = self._create_history()
        total_hidden_elements = 0

        for coll_idx in range(m):
            # Create elements (hidden — simulate Galaxy's map-over behavior)
            elements = []
            for el_idx in range(k):
                hda = self._create_hda(history, name=f"el_{coll_idx}_{el_idx}")
                hda.visible = False
                elements.append(hda)
            self.trans.sa_session.flush()
            total_hidden_elements += len(elements)

            element_identifiers = self.build_element_identifiers(elements)
            input_hdca = self.collection_manager.create(
                self.trans,
                history,
                f"input_coll_{coll_idx}",
                "list",
                element_identifiers=element_identifiers,
            )

            # Output collection (implicit, from map-over)
            out_elements = []
            for el_idx in range(k):
                hda = self._create_hda(history, name=f"out_{coll_idx}_{el_idx}")
                hda.visible = False
                out_elements.append(hda)
            self.trans.sa_session.flush()
            total_hidden_elements += len(out_elements)

            out_identifiers = self.build_element_identifiers(out_elements)
            output_hdca = self.collection_manager.create(
                self.trans,
                history,
                f"output_coll_{coll_idx}",
                "list",
                element_identifiers=out_identifiers,
            )

            tr = self._create_tool_request(history)
            job = self._create_job(tr, tool_id=f"map_tool_{coll_idx}")
            self._link_job_input_hdca(job, input_hdca)
            # Link element-level inputs (map-over pattern)
            for el in elements:
                self._link_job_input_hda(job, el)
            # Link element-level outputs
            for el in out_elements:
                self._link_job_output_hda(job, el)
            self._link_implicit_collection(tr, output_hdca)

        graph = self._build_graph(history)

        # Collection nodes bounded by 2*m (input + output collections)
        coll_nodes = [nd for nd in graph.nodes if nd.type == "collection"]
        assert len(coll_nodes) <= 2 * m

        # No element-level dataset explosion: dataset nodes must be far fewer
        # than the total hidden elements created (m*k*2)
        dataset_nodes = [nd for nd in graph.nodes if nd.type == "dataset"]
        assert (
            len(dataset_nodes) < total_hidden_elements
        ), f"Element explosion: {len(dataset_nodes)} dataset nodes from {total_hidden_elements} hidden elements"

        # Collection-level edges present on representable TRs
        tr_nodes = [nd for nd in graph.nodes if nd.type == "tool_request"]
        for tr_node in tr_nodes:
            input_edges = [e for e in graph.edges if e.target == tr_node.id]
            output_edges = [e for e in graph.edges if e.source == tr_node.id]
            for e in input_edges:
                assert e.type == "collection_input", f"Expected collection_input, got {e.type}"
            for e in output_edges:
                assert e.type == "collection_output", f"Expected collection_output, got {e.type}"

        # Total edge count bounded: not m*k element edges
        assert len(graph.edges) <= 2 * len(tr_nodes)

    def test_seed_scope_on_older_item(self):
        """seed_scope on an early item in a large history.

        Assert: seed item in scope, response bounded, scope metadata valid.
        """
        n = GRAPH_SCALE_HISTORY_SIZE
        limit = 50
        history, _ = self._create_history()
        hdas = []
        for i in range(n):
            hdas.append(self._create_hda(history, name=f"ds_{i}"))

        # Pick an early item (10th from the beginning)
        early = hdas[9]
        seed_scope = self._encode("d", early.id)

        graph = self._build_graph(history, seed_scope=seed_scope, limit=limit)

        # Seed item must be in scope
        node_ids = {nd.id for nd in graph.nodes}
        assert seed_scope in node_ids

        # Response bounded
        assert len(graph.nodes) <= limit
        assert graph.truncated.scope_type == "seed_centered"

    def test_recent_overview_shift_after_append(self):
        """Recent overview shifts predictably when new items are appended.

        Create a history near the limit, add newer items, verify the window
        shifts and oldest items drop out.
        """
        limit = 50
        history, _ = self._create_history()
        original = []
        for i in range(limit):
            original.append(self._create_hda(history, name=f"ds_{i}"))

        before = self._build_graph(history, limit=limit)
        assert len(before.nodes) == limit
        assert before.truncated.item_count_capped is False

        # Add 10 newer items — pushes 10 oldest out
        added = 10
        for i in range(added):
            self._create_hda(history, name=f"new_{i}")

        after = self._build_graph(history, limit=limit)
        assert len(after.nodes) == limit
        assert after.truncated.item_count_capped is True

        after_ids = {nd.id for nd in after.nodes}
        # Oldest originals should be gone
        for hda in original[:added]:
            assert self._encode("d", hda.id) not in after_ids
        # Newest originals should remain
        for hda in original[added:]:
            assert self._encode("d", hda.id) in after_ids

    def test_large_hidden_element_suppression(self):
        """Many hidden element HDAs do not become nodes.

        Collection with many hidden elements: all suppressed, only the
        collection node appears.
        """
        k = GRAPH_SCALE_COLLECTION_SIZE * 2  # double size for stress
        history, _ = self._create_history()

        elements = []
        for i in range(k):
            hda = self._create_hda(history, name=f"hidden_el_{i}")
            hda.visible = False
            elements.append(hda)
        self.trans.sa_session.flush()

        element_identifiers = self.build_element_identifiers(elements)
        self.collection_manager.create(
            self.trans,
            history,
            "big hidden list",
            "list",
            element_identifiers=element_identifiers,
        )

        graph = self._build_graph(history)

        # No hidden element HDAs as nodes
        dataset_nodes = [nd for nd in graph.nodes if nd.type == "dataset"]
        assert len(dataset_nodes) == 0, f"Expected 0 dataset nodes (all hidden elements), got {len(dataset_nodes)}"

        # Collection is present
        coll_nodes = [nd for nd in graph.nodes if nd.type == "collection"]
        assert len(coll_nodes) == 1
