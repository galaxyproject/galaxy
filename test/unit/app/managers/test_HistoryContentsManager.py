""" """

import datetime
import random

from sqlalchemy import (
    column,
    desc,
    false,
    true,
)

from galaxy.managers import (
    base,
    collections,
    hdas,
    history_contents,
)
from galaxy.managers.histories import HistoryManager
from .base import (
    BaseTestCase,
    CreatesCollectionsMixin,
)

default_password = "123456"
user2_data = dict(email="user2@user2.user2", username="user2", password=default_password)
user3_data = dict(email="user3@user3.user3", username="user3", password=default_password)
user4_data = dict(email="user4@user4.user4", username="user4", password=default_password)
parsed_filter = base.ModelFilterParser.parsed_filter


# =============================================================================
class HistoryAsContainerBaseTestCase(BaseTestCase, CreatesCollectionsMixin):
    def set_up_managers(self):
        super().set_up_managers()
        self.history_manager = self.app[HistoryManager]
        self.hda_manager = self.app[hdas.HDAManager]
        self.collection_manager = self.app[collections.DatasetCollectionManager]
        self.contents_manager = self.app[history_contents.HistoryContentsManager]
        self.history_contents_filters = self.app[history_contents.HistoryContentsFilters]

    def add_hda_to_history(self, history, **kwargs):
        dataset = self.hda_manager.dataset_manager.create()
        hda = self.hda_manager.create(history=history, dataset=dataset, **kwargs)
        return hda

    def add_list_collection_to_history(self, history, hdas, name="test collection", **kwargs):
        hdca = self.collection_manager.create(
            self.trans, history, name, "list", element_identifiers=self.build_element_identifiers(hdas), **kwargs
        )
        return hdca


# =============================================================================
class TestHistoryAsContainer(HistoryAsContainerBaseTestCase):
    def test_contents(self):
        user2 = self.user_manager.create(**user2_data)
        self.trans.set_user(user2)
        history = self.history_manager.create(name="history", user=user2)

        self.log("calling contents on an empty history should return an empty list")
        assert [] == list(self.contents_manager.contents(history))

        self.log("calling contents on an history with hdas should return those in order of their hids")
        hdas = [self.add_hda_to_history(history, name=("hda-" + str(x))) for x in range(3)]
        random.shuffle(hdas)
        ordered_hda_contents = list(self.contents_manager.contents(history))
        assert [hda.hid for hda in ordered_hda_contents] == [1, 2, 3]

        self.log("calling contents on an history with both hdas and collections should return both")
        hdca = self.add_list_collection_to_history(history, hdas)
        all_contents = list(self.contents_manager.contents(history))
        assert all_contents == list(ordered_hda_contents) + [hdca]

    def test_copy_elements_on_collection_creation(self):
        user2 = self.user_manager.create(**user2_data)
        self.trans.set_user(user2)
        history = self.history_manager.create(name="history", user=user2)
        hdas = [self.add_hda_to_history(history, name=("hda-" + str(x))) for x in range(3)]
        hdca = self.add_list_collection_to_history(history, hdas)
        assert hdas == hdca.dataset_instances

        hdca = self.add_list_collection_to_history(history, hdas, copy_elements=True)
        assert hdas != hdca.dataset_instances

    def test_limit_and_offset(self):
        user2 = self.user_manager.create(**user2_data)
        self.trans.set_user(user2)
        history = self.history_manager.create(name="history", user=user2)
        contents = []
        contents.extend([self.add_hda_to_history(history, name=("hda-" + str(x))) for x in range(3)])
        contents.append(self.add_list_collection_to_history(history, contents[:3]))
        contents.extend([self.add_hda_to_history(history, name=("hda-" + str(x))) for x in range(4, 6)])
        contents.append(self.add_list_collection_to_history(history, contents[4:6]))

        self.log("should be able to limit and offset")
        results = self.contents_manager.contents(history)
        assert results == contents

        assert self.contents_manager.contents(history, limit=4) == contents[0:4]
        assert self.contents_manager.contents(history, offset=3) == contents[3:]
        assert self.contents_manager.contents(history, limit=4, offset=4) == contents[4:8]

        assert self.contents_manager.contents(history, limit=0) == []
        assert self.contents_manager.contents(history, offset=len(contents)) == []

    def test_orm_filtering(self):
        parse_filter = self.history_contents_filters.parse_filter
        user2 = self.user_manager.create(**user2_data)
        self.trans.set_user(user2)
        history = self.history_manager.create(name="history", user=user2)
        contents = []
        contents.extend([self.add_hda_to_history(history, name=("hda-" + str(x))) for x in range(3)])
        contents.append(self.add_list_collection_to_history(history, contents[:3]))
        contents.extend([self.add_hda_to_history(history, name=("hda-" + str(x))) for x in range(4, 6)])
        contents.append(self.add_list_collection_to_history(history, contents[4:6]))

        self.log("should allow filter on deleted")
        self.hda_manager.delete(contents[1])
        self.hda_manager.delete(contents[4])
        contents[6].deleted = True
        deleted = [contents[1], contents[4], contents[6]]
        session = self.app.model.context
        session.commit()

        # TODO: cross db compat?
        filters = [parse_filter("deleted", "eq", "True")]
        assert self.contents_manager.contents(history, filters=filters) == deleted

        # even stranger that sqlalx can use the first model in the union (HDA) for columns across the union
        HDA = self.hda_manager.model_class
        assert self.contents_manager.contents(history, filters=[parsed_filter("orm", HDA.deleted == true())]) == deleted
        filter_limited_contents = self.contents_manager.contents(
            history, filters=[parsed_filter("orm", HDA.deleted == true())], limit=2, offset=1
        )
        assert filter_limited_contents == deleted[1:]

        self.log("should allow filter on visible")
        contents[2].visible = False
        contents[5].visible = False
        contents[6].visible = False
        invisible = [contents[2], contents[5], contents[6]]
        session.commit()

        filters = [parse_filter("visible", "eq", "False")]
        assert self.contents_manager.contents(history, filters=filters) == invisible
        assert (
            self.contents_manager.contents(history, filters=[parsed_filter("orm", HDA.visible == false())]) == invisible
        )
        filter_limited_contents = self.contents_manager.contents(
            history, filters=[parsed_filter("orm", HDA.visible == false())], limit=2, offset=1
        )
        assert filter_limited_contents == invisible[1:]

        self.log("should allow filtering more than one attribute")
        deleted_and_invisible = [contents[6]]
        filters = [parse_filter("deleted", "eq", "True"), parse_filter("visible", "eq", "False")]
        assert self.contents_manager.contents(history, filters=filters) == deleted_and_invisible
        assert (
            self.contents_manager.contents(
                history,
                filters=[parsed_filter("orm", HDA.deleted == true()), parsed_filter("orm", HDA.visible == false())],
            )
            == deleted_and_invisible
        )
        offset_too_far = self.contents_manager.contents(
            history,
            filters=[parsed_filter("orm", HDA.deleted == true()), parsed_filter("orm", HDA.visible == false())],
            limit=2,
            offset=1,
        )
        assert offset_too_far == []

        self.log("should allow filtering more than one attribute")
        deleted_and_invisible = [contents[6]]
        # note the two syntaxes both work
        filters = [parse_filter("deleted", "eq", "True"), parse_filter("visible", "eq", "False")]
        assert self.contents_manager.contents(history, filters=filters) == deleted_and_invisible
        assert (
            self.contents_manager.contents(
                history,
                filters=[parsed_filter("orm", HDA.deleted == true()), parsed_filter("orm", HDA.visible == false())],
            )
            == deleted_and_invisible
        )
        offset_too_far = self.contents_manager.contents(
            history,
            filters=[parsed_filter("orm", HDA.deleted == true()), parsed_filter("orm", HDA.visible == false())],
            limit=2,
            offset=1,
        )
        assert offset_too_far == []

        self.log("should allow filtering using like")
        # find 'hda-4'
        assert [contents[4]] == self.contents_manager.contents(
            history, filters=[parsed_filter("orm", HDA.name.like("%-4"))]
        )

    def test_order_by(self):
        user2 = self.user_manager.create(**user2_data)
        self.trans.set_user(user2)
        history = self.history_manager.create(name="history", user=user2)
        contents = []
        contents.extend([self.add_hda_to_history(history, name=("hda-" + str(x))) for x in range(3)])
        contents.append(self.add_list_collection_to_history(history, contents[:3]))
        contents.extend([self.add_hda_to_history(history, name=("hda-" + str(x))) for x in range(4, 6)])
        contents.append(self.add_list_collection_to_history(history, contents[4:6]))

        self.log("should default to hid order_by")
        assert self.contents_manager.contents(history) == contents

        self.log("should allow asc, desc order_by")
        assert self.contents_manager.contents(history, order_by=desc("hid")) == contents[::-1]

        def get_create_time(item):
            create_time = getattr(item, "create_time", None)
            if not create_time:
                create_time = item.collection.create_time
            return create_time

        self.log("should allow create_time order_by")
        newest_first = sorted(contents, key=get_create_time, reverse=True)
        results = self.contents_manager.contents(history, order_by=desc("create_time"))
        assert newest_first == results

        self.log("should allow update_time order_by")
        # change the oldest created to update the update_time
        contents[0].name = "zany and/or wacky"
        session = self.app.model.context
        session.commit()
        results = self.contents_manager.contents(history, order_by=desc("update_time"))
        assert contents[0] == results[0]

    def test_update_time_filter(self):
        user2 = self.user_manager.create(**user2_data)
        self.trans.set_user(user2)
        history = self.history_manager.create(name="history", user=user2)
        contents = []
        contents.extend([self.add_hda_to_history(history, name=("hda-" + str(x))) for x in range(3)])
        contents.append(self.add_list_collection_to_history(history, contents[:3]))
        contents.extend([self.add_hda_to_history(history, name=("hda-" + str(x))) for x in range(4, 6)])
        contents.append(self.add_list_collection_to_history(history, contents[4:6]))

        self.log("should allow filtering by update_time")
        # change the update_time by updating the name
        contents[3].name = "big ball of mud"
        session = self.app.model.context
        session.commit()
        update_time = contents[3].update_time

        def get_update_time(item):
            update_time = getattr(item, "update_time", None)
            if not update_time:
                update_time = item.update_time
            return update_time

        results = self.contents_manager.contents(
            history, filters=[parsed_filter("orm", column("update_time") >= update_time)]
        )
        assert results == [contents[3]]

    def test_filtered_counting(self):
        parse_filter = self.history_contents_filters.parse_filter
        user2 = self.user_manager.create(**user2_data)
        self.trans.set_user(user2)
        history = self.history_manager.create(name="history", user=user2)
        contents = []
        contents.extend([self.add_hda_to_history(history, name=("hda-" + str(x))) for x in range(3)])
        contents.append(self.add_list_collection_to_history(history, contents[:3]))
        contents.extend([self.add_hda_to_history(history, name=("hda-" + str(x))) for x in range(4, 6)])
        contents.append(self.add_list_collection_to_history(history, contents[4:6]))

        self.log("should show correct count with filters")
        self.hda_manager.delete(contents[1])
        self.hda_manager.delete(contents[4])
        contents[6].deleted = True
        session = self.app.model.context
        session.commit()

        contents[2].visible = False
        contents[5].visible = False
        contents[6].visible = False
        session.commit()

        HDA = self.hda_manager.model_class
        assert self.contents_manager.contents_count(history, filters=[parsed_filter("orm", HDA.deleted == true())]) == 3
        filters = [parse_filter("visible", "eq", "False")]
        assert self.contents_manager.contents_count(history, filters=filters) == 3

        filters = [parse_filter("deleted", "eq", "True"), parse_filter("visible", "eq", "False")]
        assert self.contents_manager.contents_count(history, filters=filters) == 1

    def test_type_id(self):
        user2 = self.user_manager.create(**user2_data)
        self.trans.set_user(user2)
        history = self.history_manager.create(name="history", user=user2)
        contents = []
        contents.extend([self.add_hda_to_history(history, name=("hda-" + str(x))) for x in range(3)])
        contents.append(self.add_list_collection_to_history(history, contents[:3]))
        contents.extend([self.add_hda_to_history(history, name=("hda-" + str(x))) for x in range(4, 6)])
        contents.append(self.add_list_collection_to_history(history, contents[4:6]))

        self.log("should be able to use eq and in with hybrid type_id")
        filters = [parsed_filter("orm", column("type_id") == "dataset-2")]
        assert self.contents_manager.contents(history, filters=filters) == [contents[1]]
        filters = [parsed_filter("orm", column("type_id").in_(["dataset-1", "dataset-3"]))]
        assert self.contents_manager.contents(history, filters=filters) == [contents[0], contents[2]]
        filters = [parsed_filter("orm", column("type_id") == "dataset_collection-1")]
        assert self.contents_manager.contents(history, filters=filters) == [contents[3]]
        filters = [parsed_filter("orm", column("type_id").in_(["dataset-2", "dataset_collection-2"]))]
        assert self.contents_manager.contents(history, filters=filters) == [contents[1], contents[6]]


class TestHistoryContentsFilterParser(HistoryAsContainerBaseTestCase):
    def set_up_managers(self):
        super().set_up_managers()
        self.filter_parser = history_contents.HistoryContentsFilters(self.app)

    def test_date_parser(self):
        # -- seconds and milliseconds from epoch
        self.log("should be able to parse epoch seconds")
        assert self.filter_parser.parse_date("1234567890") == datetime.datetime.fromtimestamp(1234567890).isoformat(
            sep=" "
        )

        self.log("should be able to parse floating point epoch seconds.milliseconds")
        assert self.filter_parser.parse_date("1234567890.123") == datetime.datetime.fromtimestamp(
            1234567890.123
        ).isoformat(sep=" ")

        self.log("should error if bad epoch is used")
        with self.assertRaises(ValueError):
            self.filter_parser.parse_date("0x000234")

        # -- datetime strings
        self.log("should allow date alone")
        assert self.filter_parser.parse_date("2009-02-13") == "2009-02-13"

        self.log("should allow date and time")
        assert self.filter_parser.parse_date("2009-02-13 18:13:00") == "2009-02-13 18:13:00"
        assert self.filter_parser.parse_date("2009-02-13T18:13:00") == "2009-02-13 18:13:00"
        assert self.filter_parser.parse_date("2009-02-13T18:13:00Z") == "2009-02-13 18:13:00"

        self.log("should allow date and time with milliseconds")
        assert self.filter_parser.parse_date("2009-02-13 18:13:00.123") == "2009-02-13 18:13:00.123"
        assert self.filter_parser.parse_date("2009-02-13T18:13:00.123") == "2009-02-13 18:13:00.123"
        assert self.filter_parser.parse_date("2009-02-13T18:13:00.123Z") == "2009-02-13 18:13:00.123"

        self.log("should error if timezone is added")
        with self.assertRaises(ValueError):
            self.filter_parser.parse_date("2009-02-13T18:13:00.123+0700")

        self.log("should error if locale is used")
        with self.assertRaises(ValueError):
            self.filter_parser.parse_date("Fri Feb 13 18:31:30 2009")

        self.log("should error if wrong milliseconds format is used")
        with self.assertRaises(ValueError):
            self.filter_parser.parse_date("2009-02-13 18:13:00.")
        with self.assertRaises(ValueError):
            self.filter_parser.parse_date("2009-02-13 18:13:00.1234567")
