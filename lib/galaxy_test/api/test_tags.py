import json
from typing import List
from unittest import SkipTest
from uuid import uuid4

from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    LibraryPopulator,
    WorkflowPopulator,
)
from ._framework import ApiTestCase


class TagsApiTests(ApiTestCase):
    api_name: str
    item_class: str
    publishable: bool

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def create_item(self) -> str:
        """Creates a taggable item and returns it's ID."""
        raise SkipTest("Abstract")

    def test_tags_on_item(self):
        item_id = self.create_item()
        self._assert_tags_in_item(item_id, [])

        new_tags = ["APITag"]
        update_history_tags_response = self._update_tags_using_tags_api(item_id, new_tags)
        self._assert_status_code_is(update_history_tags_response, 204)
        self._assert_tags_in_item(item_id, new_tags)

        # other users can't create or update tags
        with self._different_user():
            new_tags = ["otherAPITag"]
            update_history_tags_response = self._update_tags_using_tags_api(item_id, new_tags)
            self._assert_status_code_is(update_history_tags_response, 403)

    def _update_tags_using_tags_api(self, item_id, new_tags):
        payload = {"item_class": self.item_class, "item_id": item_id, "item_tags": new_tags}
        update_history_tags_response = self._put("tags", data=payload, json=True)
        return update_history_tags_response

    def _get_item(self, item_id: str):
        item_response = self._get(f"{self.api_name}/{item_id}")
        self._assert_status_code_is(item_response, 200)
        item = item_response.json()
        return item

    def _assert_tags_in_item(self, item_id, expected_tags: List[str]):
        item = self._get_item(item_id)
        assert "tags" in item
        assert item["tags"] == expected_tags


class TestHistoryTags(TagsApiTests):
    api_name = "histories"
    item_class = "History"

    def create_item(self) -> str:
        item_id = self.dataset_populator.new_history(name=f"history-{uuid4()}")
        return item_id


class TestDatasetTags(TagsApiTests):
    api_name = "datasets"
    item_class = "HistoryDatasetAssociation"

    def create_item(self) -> str:
        history_id = self.dataset_populator.new_history(name=f"history-{uuid4()}")
        item_id = self.dataset_populator.new_dataset(history_id=history_id)
        return item_id["id"]


class TestDatasetCollectionTags(TagsApiTests):
    api_name = "dataset_collections"
    item_class = "HistoryDatasetCollectionAssociation"

    def setUp(self):
        super().setUp()
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    def create_item(self) -> str:
        history_id = self.dataset_populator.new_history(name=f"history-{uuid4()}")
        response = self.dataset_collection_populator.create_list_in_history(history_id)
        self._assert_status_code_is(response, 200)
        hdca = response.json()["outputs"][0]
        return hdca["id"]


class TestLibraryDatasetTags(TagsApiTests):
    api_name = "libraries"
    item_class = "LibraryDatasetDatasetAssociation"

    def setUp(self):
        super().setUp()
        self.library_populator = LibraryPopulator(self.galaxy_interactor)

    def create_item(self) -> str:
        ld = self.library_populator.new_library_dataset(name=f"test-library-dataset-{uuid4()}")
        self.library_id = ld["parent_library_id"]
        return ld["id"]

    def _get_item(self, item_id: str):
        assert self.library_id is not None, "Library ID not set"
        item_response = self._get(f"{self.api_name}/{self.library_id}/contents/{item_id}")
        self._assert_status_code_is(item_response, 200)
        item = item_response.json()
        return item

    def test_upload_file_contents_with_tags(self):
        initial_tags = ["name:foobar", "barfoo"]
        ld = self.library_populator.new_library_dataset(
            name=f"test-library-dataset-{uuid4()}", tags=json.dumps(initial_tags)
        )
        assert ld["tags"] == initial_tags


class TestPageTags(TagsApiTests):
    api_name = "pages"
    item_class = "Page"

    def create_item(self) -> str:
        page = self.dataset_populator.new_page(slug=f"page-{uuid4()}")
        return page["id"]


class TestWorkflowTags(TagsApiTests):
    api_name = "workflows"
    item_class = "StoredWorkflow"

    def setUp(self):
        super().setUp()
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    def create_item(self) -> str:
        workflow = self.workflow_populator.load_workflow(name=f"workflow-{uuid4()}")
        data = dict(
            workflow=json.dumps(workflow),
        )
        upload_response = self._post("workflows", data=data)

        self._assert_status_code_is(upload_response, 200)
        return upload_response.json()["id"]


class TestVisualizationTags(TagsApiTests):
    api_name = "visualizations"
    item_class = "Visualization"

    def create_item(self) -> str:
        uuid_str = str(uuid4())

        title = f"Test Visualization {uuid_str}"
        slug = f"test-visualization-{uuid_str}"
        config = {
            "x": 10,
            "y": 12,
        }
        create_payload = {
            "title": title,
            "slug": slug,
            "type": "example",
            "dbkey": "hg17",
            "annotation": "this is a test visualization for tags",
            "config": config,
        }
        response = self._post("visualizations", data=create_payload, json=True)
        self._assert_status_code_is(response, 200)
        viz = response.json()
        return viz["id"]
