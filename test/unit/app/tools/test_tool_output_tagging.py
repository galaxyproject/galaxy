"""Test tagging behavior on tool outputs."""

from collections import OrderedDict
from typing import Any, List, Optional, cast

import galaxy.model
from galaxy.app_unittest_utils import tools_support
from galaxy.managers.collections import DatasetCollectionManager
from galaxy.model.orm.util import add_object_to_object_session
from galaxy.util.bunch import Bunch
from galaxy.util.unittest import TestCase


COLLECTION_CONTENTS = """<tool id="collection_tool" name="Collection Tool">
    <command>cat $param2 > $out1</command>
    <inputs>
        <param name="param2" type="data_collection" collection_type="paired" />
    </inputs>
    <outputs>
        <collection name="out1" type="list" label="Output Collection">
            <data name="element" format="data" />
        </collection>
    </outputs>
</tool>
"""


class TestToolOutputTagging(TestCase, tools_support.UsesTools):
    tool_action: Optional["MockAction"]

    def setUp(self):
        self.setup_app()
        self.history = galaxy.model.History()
        self.app.model.session.add(self.history)
        self.trans = MockTrans(self.app, self.history)
        self.app.dataset_collection_manager = cast(DatasetCollectionManager, MockCollectionService())
        self.tool_action = MockAction(self.trans)

    def tearDown(self):
        self.tear_down_app()

    def test_tagging_regular_tool_output(self):
        self._init_tool(tools_support.SIMPLE_TOOL_CONTENTS)
        hda = self.__add_dataset(1)
        tags = ["tag1", "tag2"]
        vars = self.__handle_with_incoming(param1=hda.id, tags=tags)
        self.__assert_executed(vars)

        assert self.tool_action is not None
        output_hda = self.tool_action.execution_call_args[0]["outgoing"]["out1"]
        assert isinstance(output_hda, galaxy.model.HistoryDatasetAssociation)

        raw_tags = getattr(output_hda, "tags", [])
        tags_list = raw_tags if isinstance(raw_tags, list) else [raw_tags] if raw_tags else []
        applied_tag_names = [tag.user_tag for tag in tags_list if hasattr(tag, "user_tag")]

        assert sorted(applied_tag_names) == sorted(tags)

    def test_tagging_mapped_tool_outputs(self):
        self.tool_action = MockMappedCollectionAction(self.trans)
        self._init_tool(COLLECTION_CONTENTS)

        hda1 = self.__add_dataset(1)
        hda2 = self.__add_dataset(2)
        hdca = self.__add_collection_dataset(10, "paired", hda1, hda2)

        tags = ["collection_tag1", "collection_tag2"]
        vars = self.__handle_with_incoming(param2=hdca.id, tags=tags)
        self.__assert_executed(vars)

        output_collection = self.tool_action.execution_call_args[0]["outgoing"]["out1"]
        assert isinstance(output_collection, galaxy.model.HistoryDatasetCollectionAssociation)

        for element in output_collection.collection.elements:
            hda = element.element_object
            applied_tags = []
            if isinstance(hda, (galaxy.model.HistoryDatasetAssociation, galaxy.model.LibraryDatasetDatasetAssociation)):
                raw_tags = getattr(hda, "tags", [])
                tags_list = raw_tags if isinstance(raw_tags, list) else [raw_tags] if raw_tags else []
                applied_tags = [t.user_tag for t in tags_list if hasattr(t, "user_tag")]
            assert sorted(applied_tags) == sorted(tags)

    def __handle_with_incoming(self, **kwds):
        return self.tool.handle_input(trans=self.trans, incoming=kwds)

    def __add_dataset(self, id, state="ok"):
        hda = galaxy.model.HistoryDatasetAssociation()
        hda.id = id
        hda.dataset = galaxy.model.Dataset()
        hda.dataset.state = state
        session = self.trans.sa_session
        session.add(hda)
        add_object_to_object_session(self.history, hda)
        self.history.datasets.append(hda)
        session.commit()
        return hda

    def __add_collection_dataset(self, id, collection_type="paired", *hdas):
        hdca = galaxy.model.HistoryDatasetCollectionAssociation()
        hdca.id = id
        collection = galaxy.model.DatasetCollection()
        hdca.collection = collection

        for i, hda in enumerate(hdas):
            element = galaxy.model.DatasetCollectionElement(
                collection=collection,
                element=hda,
                element_identifier=f"element_{i}",
                element_index=i
            )
            collection.elements.append(element)

        collection.collection_type = collection_type
        session = self.trans.sa_session
        session.add(hdca)
        add_object_to_object_session(self.history, hdca)
        self.history.dataset_collections.append(hdca)
        session.commit()
        return hdca

    def __assert_executed(self, vars):
        self.__assert_no_errors(vars)
        assert len(vars["jobs"]) > 0

    def __assert_no_errors(self, vars):
        assert "job_errors" in vars
        assert not vars["job_errors"]


class MockAction(tools_support.MockActionI):
    def __init__(self, expected_trans):
        self.expected_trans = expected_trans
        self.execution_call_args: List[dict[str, Any]] = []
        self._next_id = 1000

    def _get_next_id(self):
        next_id = self._next_id
        self._next_id += 1
        return next_id

    def execute(self, tool, trans, incoming=None, **kwds):
        assert self.expected_trans == trans
        job = galaxy.model.Job()
        outgoing = OrderedDict()

        hda = galaxy.model.HistoryDatasetAssociation()
        hda.id = self._get_next_id()
        hda.dataset = galaxy.model.Dataset()
        hda.dataset.state = "ok"
        hda.history = trans.get_history()
        if hasattr(hda, "tags") and hda.tags is not None and hasattr(hda.tags, "clear"):
            hda.tags.clear()

        outgoing["out1"] = hda
        job.output_datasets.append(
            galaxy.model.JobToOutputDatasetAssociation(name="out1", dataset=hda)
        )

        trans.tag_handler.apply_item_tags(trans.user, hda, ",".join(incoming.get("tags", [])))
        self.execution_call_args.append({"incoming": incoming, "outgoing": {"out1": hda}, **kwds})
        return job, outgoing


class MockMappedCollectionAction(MockAction):
    def execute(self, tool, trans, incoming=None, **kwds):
        job = galaxy.model.Job()
        collection = galaxy.model.DatasetCollection(collection_type="list")

        for i in range(2):
            hda = galaxy.model.HistoryDatasetAssociation()
            hda.id = self._get_next_id()
            hda.dataset = galaxy.model.Dataset()
            hda.dataset.state = "ok"
            hda.history = trans.get_history()
            if hasattr(hda, "tags") and hda.tags is not None and hasattr(hda.tags, "clear"):
                hda.tags.clear()

            trans.tag_handler.apply_item_tags(trans.user, hda, ",".join(incoming.get("tags", [])))

            element = galaxy.model.DatasetCollectionElement(element=hda)
            element.element_identifier = f"element_{i}"
            element.element_index = i
            collection.elements.append(element)

        hdca = galaxy.model.HistoryDatasetCollectionAssociation()
        hdca.id = self._get_next_id()
        hdca.collection = collection
        hdca.history = trans.get_history()
        hdca.tags = []

        trans.tag_handler.apply_item_tags(trans.user, hdca, ",".join(incoming.get("tags", [])))

        job.output_dataset_collection_instances.append(
            galaxy.model.JobToOutputDatasetCollectionAssociation("out1", hdca)
        )
        self.execution_call_args.append({
            "incoming": incoming,
            "outgoing": {"out1": hdca},
            **kwds
        })
        return job, {"out1": hdca}


class MockTagHandler:
    def apply_item_tags(self, user, item, tags_str, flush=False):
        if not hasattr(item, 'tags') or item.tags is None:
            item.tags = []

        tags = tags_str.split(",") if tags_str else []

        def add_tags(target_item, tag_class):
            raw_existing = getattr(target_item, 'tags', [])
            existing = {t.user_tag for t in raw_existing if t is not None and hasattr(t, "user_tag")}
            for tag in tags:
                if tag not in existing:
                    tag_assoc = tag_class()
                    tag_assoc.user_tag = tag
                    target_item.tags.append(tag_assoc)

        if isinstance(item, galaxy.model.HistoryDatasetAssociation):
            add_tags(item, galaxy.model.HistoryDatasetAssociationTagAssociation)
        elif isinstance(item, galaxy.model.HistoryDatasetCollectionAssociation):
            add_tags(item, galaxy.model.HistoryDatasetCollectionTagAssociation)
            for element in item.collection.elements:
                hda = element.element_object
                if isinstance(hda, (galaxy.model.HistoryDatasetAssociation, galaxy.model.LibraryDatasetDatasetAssociation)):
                    if not hasattr(hda, 'tags') or hda.tags is None:
                        hda.tags = cast(Any, [])
                    add_tags(hda, galaxy.model.HistoryDatasetAssociationTagAssociation)


class MockTrans:
    def __init__(self, app, history):
        self.app = app
        self.history = history
        self.user = None
        self.sa_session = self.app.model.context
        self.webapp = Bunch(name="galaxy")
        self.galaxy_session = None
        self.url_builder = None
        self.workflow_building_mode = False
        self.tag_handler = MockTagHandler()

    def get_history(self, **kwargs):
        return self.history

    def get_current_user_roles(self):
        return []

    def log_event(self, *args, **kwds):
        pass


class MockCollectionService:
    def __init__(self):
        self.collection_info = object()

    def match_collections(self, collections_to_match):
        return self.collection_info
