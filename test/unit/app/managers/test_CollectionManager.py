#!/usr/bin/env python
""" """
from galaxy import model
from galaxy.managers.collections import DatasetCollectionManager
from galaxy.managers.datasets import DatasetManager
from galaxy.managers.hdas import HDAManager
from galaxy.managers.histories import HistoryManager
from .base import (
    BaseTestCase,
    CreatesCollectionsMixin,
)

# =============================================================================
default_password = "123456"
user2_data = dict(email="user2@user2.user2", username="user2", password=default_password)
user3_data = dict(email="user3@user3.user3", username="user3", password=default_password)


# =============================================================================
class TestDatasetCollectionManager(BaseTestCase, CreatesCollectionsMixin):
    def set_up_managers(self):
        super().set_up_managers()
        self.dataset_manager = self.app[DatasetManager]
        self.hda_manager = self.app[HDAManager]
        self.history_manager = self.app[HistoryManager]
        self.collection_manager = self.app[DatasetCollectionManager]

    def test_create_simple_list(self):
        owner = self.user_manager.create(**user2_data)
        self.trans.set_user(owner)

        history = self.history_manager.create(name="history1", user=owner)

        hda1 = self.hda_manager.create(name="one", history=history, dataset=self.dataset_manager.create())
        hda2 = self.hda_manager.create(name="two", history=history, dataset=self.dataset_manager.create())
        hda3 = self.hda_manager.create(name="three", history=history, dataset=self.dataset_manager.create())

        self.log("should be able to create a new Collection via ids")
        element_identifiers = self.build_element_identifiers([hda1, hda2, hda3])
        hdca = self.collection_manager.create(
            self.trans, history, "test collection", "list", element_identifiers=element_identifiers
        )
        assert isinstance(hdca, model.HistoryDatasetCollectionAssociation)
        assert hdca.name == "test collection"
        assert hdca.hid == 4
        assert not hdca.deleted
        assert hdca.visible

        self.log("should contain an underlying, well-formed DatasetCollection")
        assert isinstance(hdca.collection, model.DatasetCollection)
        collection = hdca.collection
        assert collection.collection_type == "list"
        assert collection.state == "ok"
        assert len(collection.dataset_instances) == 3
        assert len(collection.elements) == 3

        self.log("and that collection should have three well-formed Elements")
        assert isinstance(collection.elements[0], model.DatasetCollectionElement)
        assert collection.elements[0].element_identifier == "one"
        assert collection.elements[0].element_index == 0
        assert collection.elements[0].element_type == "hda"
        assert collection.elements[0].element_object == hda1

        assert isinstance(collection.elements[1], model.DatasetCollectionElement)
        assert collection.elements[1].element_identifier == "two"
        assert collection.elements[1].element_index == 1
        assert collection.elements[1].element_type == "hda"
        assert collection.elements[1].element_object == hda2

        assert isinstance(collection.elements[2], model.DatasetCollectionElement)
        assert collection.elements[2].element_identifier == "three"
        assert collection.elements[2].element_index == 2
        assert collection.elements[2].element_type == "hda"
        assert collection.elements[2].element_object == hda3

        self.log("should be able to create a new Collection via objects")
        elements = dict(one=hda1, two=hda2, three=hda3)
        hdca2 = self.collection_manager.create(self.trans, history, "test collection 2", "list", elements=elements)
        assert isinstance(hdca2, model.HistoryDatasetCollectionAssociation)

    def test_update_from_dict(self):
        owner = self.user_manager.create(**user2_data)
        self.trans.set_user(owner)

        history = self.history_manager.create(name="history1", user=owner)

        hda1 = self.hda_manager.create(name="one", history=history, dataset=self.dataset_manager.create())
        hda2 = self.hda_manager.create(name="two", history=history, dataset=self.dataset_manager.create())
        hda3 = self.hda_manager.create(name="three", history=history, dataset=self.dataset_manager.create())

        elements = dict(one=hda1, two=hda2, three=hda3)
        hdca = self.collection_manager.create(self.trans, history, "test collection", "list", elements=elements)

        self.log("should be set from a dictionary")
        self.collection_manager._set_from_dict(
            self.trans,
            hdca,
            {
                "deleted": True,
                "visible": False,
                "name": "New Name",
                "tags": ["name:one", "group:two", "three"],
                # TODO: doesn't work
                # 'annotations'      : [?]
            },
        )
        assert hdca.name == "New Name"
        assert hdca.deleted
        assert not hdca.visible

        tag_names = hdca.make_tag_string_list()
        assert tag_names == ["name:one", "group:two", "three"]
        # assert hdca.annotations == ["one", "two", "three"]

    # def test_validation( self ):
    #    self.log("should be able to change the name")
    #    self.log("should be able to set deleted")
    #    self.log("should be able to set visible")
    #    self.log("should be able to set tags")
