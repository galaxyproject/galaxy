#! /usr/bin/env python
import os
import sys
import unittest
from irods.session import iRODSSession
import irods.test.config as config


class TestFiles(unittest.TestCase):

    '''Suite of data object I/O unit tests
    '''
    test_coll_path = '/{0}/home/{1}/test_dir'.format(
        config.IRODS_SERVER_ZONE, config.IRODS_USER_USERNAME)
    test_obj_name = 'test1'
    content_str = 'blah'
    write_str = '0123456789'
    write_str1 = 'INTERRUPT'

    test_obj_path = test_coll_path + '/' + test_obj_name

    def setUp(self):
        self.sess = iRODSSession(host=config.IRODS_SERVER_HOST,
                                 port=config.IRODS_SERVER_PORT,  # 4444: why?
                                 user=config.IRODS_USER_USERNAME,
                                 password=config.IRODS_USER_PASSWORD,
                                 zone=config.IRODS_SERVER_ZONE)

        # Create test collection
        self.test_coll = self.sess.collections.create(self.test_coll_path)

        # Create test object and write to it
        self.test_obj = self.sess.data_objects.create(self.test_obj_path)
        with self.test_obj.open('r+') as f:
            f.write(self.content_str)

    def tearDown(self):
        '''Remove test data and close connections
        '''
        self.test_coll.remove(recurse=True, force=True)
        self.sess.cleanup()

    def test_file_get(self):
        # get object
        obj = self.sess.data_objects.get(self.test_obj_path)

        # assertions
        self.assertEqual(obj.size, len(self.content_str))

    def test_file_open(self):
        # from irods.models import Collection, User, DataObject

        obj = self.sess.data_objects.get(self.test_obj_path)
        f = obj.open('r+')
        f.seek(0, 0)  # what does this return?

        # for lack of anything better...
        assert f.tell() == 0

        # str1 = f.read()
        # self.assertTrue(expr, msg)
        f.close()

    def test_file_read(self):
        # from irods.models import Collection, User, DataObject

        obj = self.sess.data_objects.get(self.test_obj_path)
        f = obj.open('r+')
        str1 = f.read(1024)
        # self.assertTrue(expr, msg)

        # check content of test file
        assert str1 == self.content_str

        f.close()

    def test_file_write(self):
        # from irods.models import Collection, User, DataObject

        obj = self.sess.data_objects.get(self.test_obj_path)
        f = obj.open('w+')
        f.write(self.write_str)
        f.seek(-6, 2)
        f.write(self.write_str1)

        # reset stream position for reading
        f.seek(0, 0)

        # check new content of file after our write
        str1 = f.read(1024)
        assert str1 == (self.write_str[:-6] + self.write_str1)

        # self.assertTrue(expr, msg)
        f.close()


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
