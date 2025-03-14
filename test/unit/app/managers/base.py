""" """

import json
from typing import cast

import sqlalchemy

from galaxy.app_unittest_utils import galaxy_mock
from galaxy.managers.users import UserManager
from galaxy.util.unittest import TestCase
from galaxy.work.context import SessionRequestContext

# =============================================================================
admin_email = "admin@admin.admin"
admin_users = admin_email
default_password = "123456"


# =============================================================================
class BaseTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n", "-" * 20, "begin class", cls)

    @classmethod
    def tearDownClass(cls):
        print("\n", "-" * 20, "end class", cls)

    def setUp(self):
        self.log("." * 20, "begin test", self)
        self.set_up_mocks()
        self.set_up_managers()
        self.set_up_trans()

    def set_up_mocks(self):
        admin_users_list = [u for u in admin_users.split(",") if u]
        self.mock_trans = galaxy_mock.MockTrans(admin_users=admin_users, admin_users_list=admin_users_list)
        self.trans = cast(SessionRequestContext, self.mock_trans)
        self.app = self.trans.app

    def init_user_in_database(self):
        self.mock_trans.init_user_in_database()

    def set_up_managers(self):
        self.user_manager = self.app[UserManager]

    def set_up_trans(self):
        self.admin_user = self.user_manager.create(email=admin_email, username="admin", password=default_password)
        self.trans.set_user(self.admin_user)
        self.trans.set_history(None)

    def tearDown(self):
        self.log("." * 20, "end test", self, "\n")

    def log(self, *args, **kwargs):
        print(*args, **kwargs)

    # ---- additional test types
    TYPES_NEEDING_NO_SERIALIZERS = (str, bool, type(None), int, float)

    def assertKeys(self, obj, key_list):
        assert sorted(obj.keys()) == sorted(key_list)

    def assertHasKeys(self, obj, key_list):
        for key in key_list:
            assert key in obj

    def assertNullableBasestring(self, item):
        assert isinstance(item, (str, type(None)))
        # TODO: len mod 8 and hex re

    def assertEncodedId(self, item):
        assert isinstance(item, str)
        # TODO: len mod 8 and hex re

    def assertNullableEncodedId(self, item):
        if item is not None:
            self.assertEncodedId(item)

    def assertDate(self, item):
        assert isinstance(item, str)
        # TODO: no great way to parse this fully (w/o python-dateutil)
        # TODO: re?

    def assertUUID(self, item):
        assert isinstance(item, str)
        # TODO: re for d4d76d69-80d4-4ed7-80c7-211ebcc1a358

    def assertORMFilter(self, item):
        assert isinstance(
            item.filter, (sqlalchemy.sql.elements.BinaryExpression, sqlalchemy.sql.elements.BooleanClauseList)
        ), "Not an orm filter"

    def assertORMFunctionFilter(self, item):
        assert item.filter_type == "orm_function"
        assert callable(item.filter)

    def assertFnFilter(self, item):
        assert item.filter and callable(item.filter), "Not a fn filter"

    def assertIsJsonifyable(self, item):
        # TODO: use galaxy's override
        assert isinstance(json.dumps(item), str)


class CreatesCollectionsMixin:
    trans: SessionRequestContext

    def build_element_identifiers(self, elements):
        identifier_list = []
        for element in elements:
            src = "hda"
            # if isinstance( element, model.DatasetCollection ):
            #    src = 'collection'#?
            # elif isinstance( element, model.LibraryDatasetDatasetAssociation ):
            #    src = 'ldda'#?
            identifier_list.append(dict(src=src, name=element.name, id=element.id))
        return identifier_list
