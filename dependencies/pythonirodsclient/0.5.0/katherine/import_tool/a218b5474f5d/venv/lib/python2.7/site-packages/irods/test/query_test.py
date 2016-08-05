#! /usr/bin/env python
import os
import sys
import unittest
from irods.models import User, Collection, DataObject, Resource
from irods.session import iRODSSession
from irods.exception import MultipleResultsFound
from irods.query import new_icat_keys
import irods.test.config as config


class TestQuery(unittest.TestCase):
    # test data
    coll_path = '/{0}/home/{1}/test_dir'.format(
        config.IRODS_SERVER_ZONE, config.IRODS_USER_USERNAME)
    obj_name = 'test1'
    obj_path = '{0}/{1}'.format(coll_path, obj_name)

    def setUp(self):
        self.sess = iRODSSession(host=config.IRODS_SERVER_HOST,
                                 port=config.IRODS_SERVER_PORT,  # 4444 why?
                                 user=config.IRODS_USER_USERNAME,
                                 password=config.IRODS_USER_PASSWORD,
                                 zone=config.IRODS_SERVER_ZONE)

        # Create test collection and (empty) test object
        self.coll = self.sess.collections.create(self.coll_path)
        self.obj = self.sess.data_objects.create(self.obj_path)

    def tearDown(self):
        '''Remove test data and close connections
        '''
        self.coll.remove(recurse=True, force=True)
        self.sess.cleanup()

    def test_collections_query(self):
        # collection query test
        result = self.sess.query(Collection.id, Collection.name).all()
        assert result.has_value(self.coll_path)

    def test_files_query(self):
        # file query test
        query = self.sess.query(
            DataObject.id, DataObject.collection_id, DataObject.name, User.name, Collection.name)

        # coverage
        for column in query.columns:
            repr(column)

        result = query.all()
        assert result.has_value(self.obj_name)

    def test_users_query(self):
        '''Lists all users and look for known usernames
        '''
        # query takes model(s) or column(s)
        # only need User.name here
        results = self.sess.query(User.name).all()

        # get user list from results
        users = [row[User.name] for row in results.rows]

        # assertions
        self.assertIn('rods', users)
        self.assertIn('public', users)

    def test_resources_query(self):
        '''Lists resources
        '''
        # query takes model(s) or column(s)
        results = self.sess.query(Resource).all()

        # check ResultSet.__str__()
        str(results)

        # get resource list from results
        resources = [row[Resource.name] for row in results.rows]

        # assertions
        self.assertIn('demoResc', resources)

    def test_query_first(self):
        # with no result
        results = self.sess.query(User.name).filter(User.name == 'boo').first()
        self.assertIsNone(results)

        # with result
        results = self.sess.query(User.name).first()
        self.assertEqual(len(results), 1)

    def test_query_one(self):
        # with multiple results
        with self.assertRaises(MultipleResultsFound):
            results = self.sess.query(User.name).one()

    def test_query_wrong_type(self):
        with self.assertRaises(TypeError):
            query = self.sess.query(str())

    def test_query_order_by(self):
        # query for user names
        results = self.sess.query(User.name).order_by(User.name).all()

        # get user names from results
        user_names = []
        for result in results:
            user_names.append(result[User.name])

        # make copy before sorting
        original = list(user_names)

        # check that list was already sorted
        user_names.sort()
        self.assertEqual(user_names, original)

    def test_query_order_by_desc(self):
        # query for user names
        results = self.sess.query(User.name).order_by(User.name, order='desc').all()

        # get user names from results
        user_names = []
        for result in results:
            user_names.append(result[User.name])

        # make copy before sorting
        original = list(user_names)

        # check that list was already sorted
        user_names.sort(reverse=True)
        self.assertEqual(user_names, original)

    def test_query_order_by_invalid_param(self):
        with self.assertRaises(ValueError):
            results = self.sess.query(User.name).order_by(User.name, order='moo').all()

    def test_query_strip(self):
        query = self.sess.query(Resource)
        query._strip()

        # should have none of the new stuff
        for key in new_icat_keys:
            self.assertNotIn(key, query.columns)


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
