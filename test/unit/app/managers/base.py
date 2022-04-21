"""
"""

import json
import unittest

import sqlalchemy

from galaxy.app_unittest_utils import galaxy_mock
from galaxy.managers.users import UserManager

# =============================================================================
admin_email = "admin@admin.admin"
admin_users = admin_email
default_password = "123456"


# =============================================================================
class BaseTestCase(unittest.TestCase):
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
        self.trans = galaxy_mock.MockTrans(admin_users=admin_users, admin_users_list=admin_users_list)
        self.app = self.trans.app

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
        self.assertEqual(sorted(obj.keys()), sorted(key_list))

    def assertHasKeys(self, obj, key_list):
        for key in key_list:
            if key not in obj:
                self.fail("Missing key: " + key)
        else:
            self.assertTrue(True, "keys found in object")

    def assertNullableBasestring(self, item):
        if not isinstance(item, (str, type(None))):
            self.fail("Non-nullable basestring: " + str(type(item)))
        # TODO: len mod 8 and hex re
        self.assertTrue(True, "is nullable basestring: " + str(item))

    def assertEncodedId(self, item):
        if not isinstance(item, str):
            self.fail("Non-string: " + str(type(item)))
        # TODO: len mod 8 and hex re
        self.assertTrue(True, "is id: " + item)

    def assertNullableEncodedId(self, item):
        if item is None:
            self.assertTrue(True, "nullable id is None")
        else:
            self.assertEncodedId(item)

    def assertDate(self, item):
        if not isinstance(item, str):
            self.fail("Non-string: " + str(type(item)))
        # TODO: no great way to parse this fully (w/o python-dateutil)
        # TODO: re?
        self.assertTrue(True, "is date: " + item)

    def assertUUID(self, item):
        if not isinstance(item, str):
            self.fail("Non-string: " + str(type(item)))
        # TODO: re for d4d76d69-80d4-4ed7-80c7-211ebcc1a358
        self.assertTrue(True, "is uuid: " + item)

    def assertORMFilter(self, item, msg=None):
        if not isinstance(
            item.filter, (sqlalchemy.sql.elements.BinaryExpression, sqlalchemy.sql.elements.BooleanClauseList)
        ):
            self.fail("Not an orm filter: " + str(type(item.filter)))
        self.assertTrue(True, msg or ("is an orm filter: " + str(item.filter)))

    def assertORMFunctionFilter(self, item, msg=None):
        assert item.filter_type == "orm_function"
        assert callable(item.filter)

    def assertFnFilter(self, item, msg=None):
        if not item.filter or not callable(item.filter):
            self.fail("Not a fn filter: " + str(type(item.filter)))
        self.assertTrue(True, msg or ("is a fn filter: " + str(item.filter)))

    def assertIsJsonifyable(self, item):
        # TODO: use galaxy's override
        self.assertIsInstance(json.dumps(item), str)


class CreatesCollectionsMixin:
    trans: galaxy_mock.MockTrans

    def build_element_identifiers(self, elements):
        identifier_list = []
        for element in elements:
            src = "hda"
            # if isinstance( element, model.DatasetCollection ):
            #    src = 'collection'#?
            # elif isinstance( element, model.LibraryDatasetDatasetAssociation ):
            #    src = 'ldda'#?
            encoded_id = self.trans.security.encode_id(element.id)
            identifier_list.append(dict(src=src, name=element.name, id=encoded_id))
        return identifier_list


# =============================================================================
if __name__ == "__main__":
    # or more generally, nosetests test_resourcemanagers.py -s -v
    unittest.main()
