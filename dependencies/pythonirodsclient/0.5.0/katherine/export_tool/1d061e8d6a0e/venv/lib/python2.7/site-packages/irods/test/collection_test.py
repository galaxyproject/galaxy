#! /usr/bin/env python
import os
import sys
import unittest
from irods.session import iRODSSession
from irods.meta import iRODSMetaCollection
from irods.exception import CollectionDoesNotExist
import irods.test.config as config
import irods.test.helpers as helpers


class TestCollection(unittest.TestCase):
    test_coll_path = '/{0}/home/{1}/test_dir'.format(
        config.IRODS_SERVER_ZONE, config.IRODS_USER_USERNAME)

    def setUp(self):
        self.sess = iRODSSession(host=config.IRODS_SERVER_HOST,
                                 port=config.IRODS_SERVER_PORT,
                                 user=config.IRODS_USER_USERNAME,
                                 password=config.IRODS_USER_PASSWORD,
                                 zone=config.IRODS_SERVER_ZONE)

        self.test_coll = self.sess.collections.create(self.test_coll_path)

    def tearDown(self):
        """ Delete the test collection after each test """
        self.test_coll.remove(recurse=True, force=True)
        self.sess.cleanup()

    def test_get_collection(self):
        # path = "/tempZone/home/rods"
        coll = self.sess.collections.get(self.test_coll_path)
        self.assertEquals(self.test_coll_path, coll.path)

    # def test_new_collection(self):
    #    self.assertEquals(self.coll.name, 'test_dir')

    def test_append_to_collection(self):
        """ Append a new file to the collection"""
        pass

    def test_remove_from_collection(self):
        """ Delete a file from a collection """
        pass

    def test_update_in_collection(self):
        """ Modify a file in a collection """
        pass

    def test_remove_deep_collection(self):
        # depth = 100
        depth = 20  # placeholder
        root_coll_path = self.test_coll_path + "/deep_collection"

        # make test collection
        helpers.make_deep_collection(
            self.sess, root_coll_path, depth=depth, objects_per_level=1, object_content=None)

        # delete test collection
        self.sess.collections.remove(root_coll_path, recurse=True, force=True)

        # confirm delete
        with self.assertRaises(CollectionDoesNotExist):
            self.sess.collections.get(root_coll_path)

    def test_rename_collection(self):
        # test args
        args = {'collection': self.test_coll_path,
                'old_name': 'foo',
                'new_name': 'bar'}

        # make collection
        path = "{collection}/{old_name}".format(**args)
        coll = helpers.make_collection(self.sess, path)

        # get collection id
        saved_id = coll.id

        # rename coll
        new_path = "{collection}/{new_name}".format(**args)
        coll.move(new_path)
        # self.sess.collections.move(path, new_path)

        # get updated collection
        coll = self.sess.collections.get(new_path)

        # compare ids
        self.assertEqual(coll.id, saved_id)

        # remove collection
        coll.remove(recurse=True, force=True)

    def test_move_coll_to_coll(self):
        # test args
        args = {'base_collection': self.test_coll_path,
                'collection1': 'foo',
                'collection2': 'bar'}

        # make collection1 and collection2 in base collection
        path1 = "{base_collection}/{collection1}".format(**args)
        coll1 = helpers.make_collection(self.sess, path1)
        path2 = "{base_collection}/{collection2}".format(**args)
        coll2 = helpers.make_collection(self.sess, path2)

        # get collection2's id
        saved_id = coll2.id

        # move collection2 into collection1
        self.sess.collections.move(path2, path1)

        # get updated collection
        path2 = "{base_collection}/{collection1}/{collection2}".format(**args)
        coll2 = self.sess.collections.get(path2)

        # compare ids
        self.assertEqual(coll2.id, saved_id)

        # remove collection
        coll1.remove(recurse=True, force=True)

    def test_repr_coll(self):
        coll_name = self.test_coll.name.encode('utf-8')
        coll_id = self.test_coll.id

        self.assertEqual(
            repr(self.test_coll), "<iRODSCollection {coll_id} {coll_name}>".format(**locals()))

    def test_walk_collection_topdown(self):
        depth = 20

        # files that will be ceated in each subcollection
        filenames = ['foo', 'bar', 'baz']

        # make nested collections
        coll_path = self.test_coll_path
        for d in range(depth):
            # create subcollection with files
            coll_path += '/sub' + str(d)
            helpers.make_collection(self.sess, coll_path, filenames)

        # now walk nested collections
        colls = self.test_coll.walk()
        current_coll_name = self.test_coll.name
        for d in range(depth + 1):
            # get next result
            collection, subcollections, data_objects = colls.next()

            # check collection name
            self.assertEqual(collection.name, current_coll_name)

            # check subcollection name
            if d < depth:
                sub_coll_name = 'sub' + str(d)
                self.assertEqual(sub_coll_name, subcollections[0].name)
            else:
                # last coll has no subcolls
                self.assertListEqual(subcollections, [])

            # check data object names
            for data_object in data_objects:
                self.assertIn(data_object.name, filenames)

            # iterate
            current_coll_name = sub_coll_name

        # that should be it
        with self.assertRaises(StopIteration):
            colls.next()

    def test_walk_collection(self):
        depth = 20

        # files that will be ceated in each subcollection
        filenames = ['foo', 'bar', 'baz']

        # make nested collections
        coll_path = self.test_coll_path
        for d in range(depth):
            # create subcollection with files
            coll_path += '/sub' + str(d)
            helpers.make_collection(self.sess, coll_path, filenames)

        # now walk nested collections
        colls = self.test_coll.walk(topdown=False)
        for d in range(depth - 1, -2, -1):
            # get next result
            collection, subcollections, data_objects = colls.next()

            # check collection name
            if d >= 0:
                coll_name = 'sub' + str(d)
                self.assertEqual(collection.name, coll_name)
            else:
                # root collection
                self.assertEqual(collection.name, self.test_coll.name)

            # check subcollection name
            if d < depth - 1:
                self.assertEqual(sub_coll_name, subcollections[0].name)
            else:
                # last coll has no subcolls
                self.assertListEqual(subcollections, [])

            # check data object names
            for data_object in data_objects:
                self.assertIn(data_object.name, filenames)

            # iterate
            sub_coll_name = coll_name

        # that should be it
        with self.assertRaises(StopIteration):
            colls.next()

    def test_collection_metadata(self):
        self.assertIsInstance(self.test_coll.metadata, iRODSMetaCollection)

if __name__ == "__main__":
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
