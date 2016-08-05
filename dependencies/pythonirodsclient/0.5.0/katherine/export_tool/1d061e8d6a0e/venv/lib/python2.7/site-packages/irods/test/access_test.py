#! /usr/bin/env python
import os
import sys
import unittest
from irods.models import User
from irods.access import iRODSAccess
from irods.session import iRODSSession
import irods.test.config as config
import irods.test.helpers as helpers

from irods.models import (
    DataObject, Collection, User, DataAccess, CollectionAccess)


class TestAccess(unittest.TestCase):

    def setUp(self):
        self.sess = iRODSSession(host=config.IRODS_SERVER_HOST,
                                 port=config.IRODS_SERVER_PORT,
                                 user=config.IRODS_USER_USERNAME,
                                 password=config.IRODS_USER_PASSWORD,
                                 zone=config.IRODS_SERVER_ZONE)

        # Create dummy test collection
        self.coll_path = '/{0}/home/{1}/test_dir'.format(
            config.IRODS_SERVER_ZONE, config.IRODS_USER_USERNAME)
        self.coll = helpers.make_collection(self.sess, self.coll_path)

    def tearDown(self):
        '''Remove test data and close connections
        '''
        self.coll.remove(recurse=True, force=True)
        self.sess.cleanup()

    def test_list_acl(self):
        # test args
        collection = self.coll_path
        filename = 'foo'

        # get current user info
        user = self.sess.users.get(
            config.IRODS_USER_USERNAME, config.IRODS_SERVER_ZONE)

        # make object in test collection
        path = "{collection}/{filename}".format(**locals())
        obj = helpers.make_object(self.sess, path)

        # get object
        obj = self.sess.data_objects.get(path)

        # test exception
        with self.assertRaises(TypeError):
            self.sess.permissions.get(filename)

        # get object's ACLs
        # only one for now, the owner's own access
        acl = self.sess.permissions.get(obj)[0]

        # check values
        self.assertEqual(acl.access_name, 'own')
        self.assertEqual(acl.user_zone, user.zone)
        self.assertEqual(acl.user_name, user.name)

        # check repr()
        self.assertEqual(
            repr(acl), "<iRODSAccess {0} {1} {2} {3}>".format('own', path, user.name, user.zone))

        # remove object
        self.sess.data_objects.unlink(path)

    def test_set_data_acl(self):
        # test args
        collection = self.coll_path
        filename = 'foo'

        # get current user info
        user = self.sess.users.get(
            config.IRODS_USER_USERNAME, config.IRODS_SERVER_ZONE)

        # make object in test collection
        path = "{collection}/{filename}".format(**locals())
        obj = helpers.make_object(self.sess, path)

        # get object
        obj = self.sess.data_objects.get(path)

        # set permission to write
        acl1 = iRODSAccess('write', path, user.name, user.zone)
        self.sess.permissions.set(acl1)

        # get object's ACLs
        acl = self.sess.permissions.get(obj)[0]  # owner's write access

        # check values
        self.assertEqual(acl.access_name, 'modify object')
        self.assertEqual(acl.user_zone, user.zone)
        self.assertEqual(acl.user_name, user.name)

        # reset permission to own
        acl1 = iRODSAccess('own', path, user.name, user.zone)
        self.sess.permissions.set(acl1)

        # remove object
        self.sess.data_objects.unlink(path)

    def test_set_collection_acl(self):
        # use test coll
        coll = self.coll

        # get current user info
        user = self.sess.users.get(
            config.IRODS_USER_USERNAME, config.IRODS_SERVER_ZONE)

        # set permission to write
        acl1 = iRODSAccess('write', coll.path, user.name, user.zone)
        self.sess.permissions.set(acl1)

        # get collection's ACLs
        acl = self.sess.permissions.get(coll)[0]  # owner's write access

        # check values
        self.assertEqual(acl.access_name, 'modify object')
        self.assertEqual(acl.user_zone, user.zone)
        self.assertEqual(acl.user_name, user.name)

        # reset permission to own
        acl1 = iRODSAccess('own', coll.path, user.name, user.zone)
        self.sess.permissions.set(acl1)


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
