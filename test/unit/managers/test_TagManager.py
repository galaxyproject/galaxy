# -*- coding: utf-8 -*-
from galaxy.managers import hdas
from galaxy.managers.datasets import DatasetManager
from galaxy.managers.histories import HistoryManager
from galaxy.managers.tags import GalaxyTagManager
from galaxy.util import unicodify
from .base import BaseTestCase

# =============================================================================
default_password = '123456'
user2_data = dict(email='user2@user2.user2', username='user2', password=default_password)


# =============================================================================
class TagManagerTestCase(BaseTestCase):

    def set_up_managers(self):
        super(TagManagerTestCase, self).set_up_managers()
        self.hda_manager = hdas.HDAManager(self.app)
        self.history_manager = HistoryManager(self.app)
        self.dataset_manager = DatasetManager(self.app)
        self.tag_manager = GalaxyTagManager(self.trans.sa_session)
        self.user = self.user_manager.create(**user2_data)

    def _create_vanilla_hda(self, user=None):
        owner = user or self.user
        history1 = self.history_manager.create(name='history1', user=owner)
        dataset1 = self.dataset_manager.create()
        return self.hda_manager.create(history=history1, dataset=dataset1)

    def _check_tag_list(self, tags, expected_tags):
        self.assertEqual(len(tags), len(expected_tags))
        actual_tags = []
        for tag in tags:
            if tag.user_value:
                tag = "%s:%s" % (tag.user_tname, tag.user_value)
            else:
                tag = tag.user_tname
            actual_tags.append(tag)
        expected = [unicodify(e) for e in expected_tags]
        assert sorted(expected) == sorted(actual_tags), "%s vs %s" % (expected, actual_tags)

    def test_apply_item_tags(self):
        tag_strings = [
            'tag1',
            'tag1:value1',
            'tag1:value1:value11',
            '\x00tag1',
            'tag1:\x00value1',
            'tag1,tag2'
        ]
        expected_tags = [
            ['tag1'],
            ['tag1:value1'],
            ['tag1:value1:value11'],
            ['tag1'],
            ['tag1:value1'],
            ['tag1', 'tag2']
        ]
        for tag_string, expected_tag in zip(tag_strings, expected_tags):
            hda = self._create_vanilla_hda()
            self.tag_manager.apply_item_tags(user=self.user, item=hda, tags_str=tag_string)
            self._check_tag_list(hda.tags, expected_tag)

    def test_set_tag_from_list(self):
        hda = self._create_vanilla_hda()
        tags = ['tag1', 'tag2']
        self.tag_manager.set_tags_from_list(self.user, hda, tags)
        self._check_tag_list(hda.tags, tags)
        # Setting tags should erase previous tags
        self.tag_manager.set_tags_from_list(self.user, hda, ['tag1'])
        self._check_tag_list(hda.tags, expected_tags=['tag1'])

    def test_add_tag_from_list(self):
        hda = self._create_vanilla_hda()
        tags = ['tag1', 'tag2']
        self.tag_manager.add_tags_from_list(self.user, hda, tags)
        self._check_tag_list(tags=hda.tags, expected_tags=tags)
        # Adding tags should keep previous tags
        self.tag_manager.add_tags_from_list(self.user, hda, ['tag3'])
        self._check_tag_list(hda.tags, expected_tags=['tag1', 'tag2', 'tag3'])

    def test_remove_tag_from_list(self):
        hda = self._create_vanilla_hda()
        tags = ['tag1', 'tag2']
        self.tag_manager.set_tags_from_list(self.user, hda, tags)
        self._check_tag_list(hda.tags, tags)
        self.tag_manager.remove_tags_from_list(self.user, hda, ['tag1'])
        self._check_tag_list(hda.tags, ['tag2'])

    def test_delete_item_tags(self):
        hda = self._create_vanilla_hda()
        tags = ['tag1']
        self.tag_manager.set_tags_from_list(self.user, hda, tags)
        self.tag_manager.delete_item_tags(user=self.user, item=hda)
        self.assertEqual(hda.tags, [])

    def test_item_has_tag(self):
        hda = self._create_vanilla_hda()
        tags = ['tag1']
        self.tag_manager.set_tags_from_list(self.user, hda, tags)
        self.assertTrue(self.tag_manager.item_has_tag(self.user, item=hda, tag='tag1'))
        # ItemTagAssociation
        self.assertTrue(self.tag_manager.item_has_tag(self.user, item=hda, tag=hda.tags[0]))
        # Tag
        self.assertTrue(self.tag_manager.item_has_tag(self.user, item=hda, tag=hda.tags[0].tag))
        self.assertFalse(self.tag_manager.item_has_tag(self.user, item=hda, tag='tag2'))
