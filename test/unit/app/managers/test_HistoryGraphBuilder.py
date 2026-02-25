from galaxy import model
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

    def _build_graph(self, history):
        encoded_history_id = self.app.security.encode_id(history.id)
        builder = HistoryGraphBuilder(
            sa_session=self.trans.sa_session,
            security=self.app.security,
            history_id=history.id,
            encoded_history_id=encoded_history_id,
        )
        return builder.build()

    def _create_history(self):
        user = self.user_manager.create(**_next_user_data())
        self.trans.set_user(user)
        return self.history_manager.create(name="test_history", user=user), user

    def _create_hda(self, history, name="test_dataset"):
        return self.hda_manager.create(name=name, history=history, dataset=self.dataset_manager.create())

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

    def _link_job_output_hda(self, job, hda, name="output"):
        assoc = model.JobToOutputDatasetAssociation(name=name, dataset=hda)
        assoc.job_id = job.id
        session = self.trans.sa_session
        session.add(assoc)
        session.flush()
        return assoc

    def _link_job_output_hdca(self, job, hdca, name="output"):
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

    def test_empty_history(self):
        history, _ = self._create_history()
        graph = self._build_graph(history)
        assert graph.version == "2"
        assert graph.node_count == 0
        assert graph.edge_count == 0
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0
        assert len(graph.external_refs) == 0

    def test_disconnected_datasets_excluded(self):
        history, _ = self._create_history()
        self._create_hda(history, name="uploaded.fastq")
        graph = self._build_graph(history)
        assert graph.node_count == 0
        assert graph.edge_count == 0

    def test_single_tool_request(self):
        history, _ = self._create_history()
        input_hda = self._create_hda(history, name="input.fastq")
        output_hda = self._create_hda(history, name="output.bam")
        tr = self._create_tool_request(
            history,
            request_data={"reads": {"src": "hda", "id": input_hda.id}},
        )
        job = self._create_job(tool_request=tr, tool_id="bwa_mem")
        self._link_job_output_hda(job, output_hda, name="output")

        graph = self._build_graph(history)
        assert graph.node_count == 3
        assert graph.edge_count == 2

        types = {n.type for n in graph.nodes}
        assert types == {"dataset", "tool_request"}

        tr_node = [n for n in graph.nodes if n.type == "tool_request"][0]
        assert tr_node.tool_id == "bwa_mem"
        assert tr_node.state == "submitted"

        input_edges = [e for e in graph.edges if e.type == "input"]
        assert len(input_edges) == 1
        assert input_edges[0].name == "reads"

        output_edges = [e for e in graph.edges if e.type == "output"]
        assert len(output_edges) == 1
        assert output_edges[0].name == "output"

    def test_collection_is_atomic(self):
        history, _ = self._create_history()
        hda1 = self._create_hda(history, name="el1")
        hda2 = self._create_hda(history, name="el2")

        element_identifiers = self.build_element_identifiers([hda1, hda2])
        hdca = self.collection_manager.create(
            self.trans, history, "test list", "list", element_identifiers=element_identifiers
        )

        tr = self._create_tool_request(
            history,
            request_data={"input": {"src": "hdca", "id": hdca.id}},
        )
        self._create_job(tool_request=tr, tool_id="list_tool")

        graph = self._build_graph(history)
        collection_nodes = [n for n in graph.nodes if n.type == "collection"]
        assert len(collection_nodes) == 1
        assert collection_nodes[0].collection_type == "list"
        assert collection_nodes[0].element_count == 2

        edge_types = {e.type for e in graph.edges}
        assert edge_types <= {"input", "output"}

    def test_map_over_tool_request(self):
        history, _ = self._create_history()
        hda1 = self._create_hda(history, name="el1")
        hda2 = self._create_hda(history, name="el2")

        input_identifiers = self.build_element_identifiers([hda1, hda2])
        input_hdca = self.collection_manager.create(
            self.trans, history, "input list", "list", element_identifiers=input_identifiers
        )

        output_hda1 = self._create_hda(history, name="out1")
        output_hda2 = self._create_hda(history, name="out2")
        output_identifiers = self.build_element_identifiers([output_hda1, output_hda2])
        output_hdca = self.collection_manager.create(
            self.trans, history, "output list", "list", element_identifiers=output_identifiers
        )

        tr = self._create_tool_request(
            history,
            request_data={"input": {"src": "hdca", "id": input_hdca.id}},
        )
        job1 = self._create_job(tool_request=tr, tool_id="sort_tool")
        job2 = self._create_job(tool_request=tr, tool_id="sort_tool")
        self._link_job_output_hda(job1, output_hda1)
        self._link_job_output_hda(job2, output_hda2)
        self._link_implicit_collection(tr, output_hdca, output_name="output")

        graph = self._build_graph(history)
        tr_nodes = [n for n in graph.nodes if n.type == "tool_request"]
        assert len(tr_nodes) == 1

        input_edges = [e for e in graph.edges if e.type == "input"]
        assert len(input_edges) == 1
        assert input_edges[0].source.startswith("c")

        output_edges = [e for e in graph.edges if e.type == "output"]
        output_targets = {e.target for e in output_edges}
        has_collection_output = any(t.startswith("c") for t in output_targets)
        assert has_collection_output

    def test_multi_output_tool_request(self):
        history, _ = self._create_history()
        input_hda = self._create_hda(history, name="input")
        output_hda1 = self._create_hda(history, name="out1")
        output_hda2 = self._create_hda(history, name="out2")

        tr = self._create_tool_request(
            history,
            request_data={"input": {"src": "hda", "id": input_hda.id}},
        )
        job = self._create_job(tool_request=tr)
        self._link_job_output_hda(job, output_hda1, name="output1")
        self._link_job_output_hda(job, output_hda2, name="output2")

        graph = self._build_graph(history)
        output_edges = [e for e in graph.edges if e.type == "output"]
        assert len(output_edges) == 2
        output_names = {e.name for e in output_edges}
        assert output_names == {"output1", "output2"}

    def test_explicit_collection_output(self):
        history, _ = self._create_history()
        input_hda = self._create_hda(history, name="input")
        output_hda = self._create_hda(history, name="collected_out")

        element_identifiers = self.build_element_identifiers([output_hda])
        hdca = self.collection_manager.create(
            self.trans, history, "explicit output collection", "list", element_identifiers=element_identifiers
        )

        tr = self._create_tool_request(
            history,
            request_data={"input": {"src": "hda", "id": input_hda.id}},
        )
        job = self._create_job(tool_request=tr, tool_id="collection_tool")
        self._link_job_output_hdca(job, hdca, name="output_collection")

        graph = self._build_graph(history)
        output_edges = [e for e in graph.edges if e.type == "output"]
        collection_output_edges = [e for e in output_edges if e.target.startswith("c")]
        assert len(collection_output_edges) == 1
        assert collection_output_edges[0].name == "output_collection"

    def test_deleted_dataset(self):
        history, _ = self._create_history()
        hda = self._create_hda(history, name="deleted_file")
        hda.deleted = True
        self.trans.sa_session.flush()

        tr = self._create_tool_request(
            history,
            request_data={"input": {"src": "hda", "id": hda.id}},
        )
        self._create_job(tool_request=tr)

        graph = self._build_graph(history)
        dataset_nodes = [n for n in graph.nodes if n.type == "dataset"]
        assert len(dataset_nodes) == 1
        assert dataset_nodes[0].deleted is True

    def test_cross_history_input(self):
        history1, user = self._create_history()
        history2 = self.history_manager.create(name="other_history", user=user)
        external_hda = self._create_hda(history2, name="external_data")

        tr = self._create_tool_request(
            history1,
            request_data={"input": {"src": "hda", "id": external_hda.id}},
        )
        self._create_job(tool_request=tr)

        graph = self._build_graph(history1)
        assert len(graph.external_refs) == 1
        assert graph.external_refs[0].type == "dataset"
        assert graph.external_refs[0].name == "external_data"

        input_edges = [e for e in graph.edges if e.type == "input"]
        assert len(input_edges) == 1

    def test_internal_tool_excluded(self):
        history, _ = self._create_history()

        tr = self._create_tool_request(history, request_data={})
        self._create_job(tool_request=tr, tool_id="__DATA_FETCH__")

        graph = self._build_graph(history)
        tr_nodes = [n for n in graph.nodes if n.type == "tool_request"]
        assert len(tr_nodes) == 0

    def test_deterministic_ordering(self):
        history, _ = self._create_history()
        hda1 = self._create_hda(history, name="b_dataset")
        hda2 = self._create_hda(history, name="a_dataset")

        tr = self._create_tool_request(
            history,
            request_data={
                "input1": {"src": "hda", "id": hda1.id},
                "input2": {"src": "hda", "id": hda2.id},
            },
        )
        self._create_job(tool_request=tr, tool_id="multi_input")

        graph1 = self._build_graph(history)
        graph2 = self._build_graph(history)
        assert [n.id for n in graph1.nodes] == [n.id for n in graph2.nodes]
        assert [e.source for e in graph1.edges] == [e.source for e in graph2.edges]

    def test_edge_deduplication(self):
        history, _ = self._create_history()
        input_hda = self._create_hda(history, name="input")
        output_hda = self._create_hda(history, name="output")

        tr = self._create_tool_request(
            history,
            request_data={"input": {"src": "hda", "id": input_hda.id}},
        )
        job1 = self._create_job(tool_request=tr, tool_id="multi_job_tool")
        job2 = self._create_job(tool_request=tr, tool_id="multi_job_tool")
        self._link_job_output_hda(job1, output_hda, name="output")
        self._link_job_output_hda(job2, output_hda, name="output")

        graph = self._build_graph(history)
        output_edges = [e for e in graph.edges if e.type == "output"]
        assert len(output_edges) == 1

    def test_output_count_independent_of_job_count(self):
        history, _ = self._create_history()
        input_hda = self._create_hda(history, name="input")
        output_hda = self._create_hda(history, name="output")

        tr = self._create_tool_request(
            history,
            request_data={"input": {"src": "hda", "id": input_hda.id}},
        )
        for _ in range(10):
            job = self._create_job(tool_request=tr, tool_id="parallel_tool")
            self._link_job_output_hda(job, output_hda, name="output")

        graph = self._build_graph(history)
        assert graph.node_count == 3
        assert graph.edge_count == 2
        output_edges = [e for e in graph.edges if e.type == "output"]
        assert len(output_edges) == 1

    def test_legacy_job_ignored(self):
        history, _ = self._create_history()
        hda = self._create_hda(history, name="legacy_output")

        self._create_job(tool_request=None, tool_id="legacy_tool")

        graph = self._build_graph(history)
        assert graph.node_count == 0
        assert graph.edge_count == 0

    def test_tool_request_zero_jobs(self):
        history, _ = self._create_history()
        input_hda = self._create_hda(history, name="input")

        self._create_tool_request(
            history,
            request_data={"input": {"src": "hda", "id": input_hda.id}},
            state="new",
        )

        graph = self._build_graph(history)
        tr_nodes = [n for n in graph.nodes if n.type == "tool_request"]
        assert len(tr_nodes) == 1
        assert tr_nodes[0].state == "new"
        assert tr_nodes[0].tool_id is None
        assert tr_nodes[0].tool_version is None

        input_edges = [e for e in graph.edges if e.type == "input"]
        assert len(input_edges) == 1

        output_edges = [e for e in graph.edges if e.type == "output"]
        assert len(output_edges) == 0

    def test_tool_request_failed(self):
        history, _ = self._create_history()
        input_hda = self._create_hda(history, name="input")
        output_hda = self._create_hda(history, name="partial_output")

        tr = self._create_tool_request(
            history,
            request_data={"input": {"src": "hda", "id": input_hda.id}},
            state="failed",
        )
        job = self._create_job(tool_request=tr, tool_id="failing_tool")
        self._link_job_output_hda(job, output_hda, name="output")

        graph = self._build_graph(history)
        tr_nodes = [n for n in graph.nodes if n.type == "tool_request"]
        assert len(tr_nodes) == 1
        assert tr_nodes[0].state == "failed"

        output_edges = [e for e in graph.edges if e.type == "output"]
        assert len(output_edges) == 1
