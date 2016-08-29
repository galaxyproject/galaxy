#! /usr/bin/env python
import os
import sys
import unittest
from irods.session import iRODSSession
from irods.exception import NetworkException
import irods.test.config as config


class TestPool(unittest.TestCase):

    def setUp(self):
        self.sess = iRODSSession(host=config.IRODS_SERVER_HOST,
                                 port=config.IRODS_SERVER_PORT,  # 4444: why?
                                 user=config.IRODS_USER_USERNAME,
                                 password=config.IRODS_USER_PASSWORD,
                                 zone=config.IRODS_SERVER_ZONE)

    def tearDown(self):
        '''Close connections
        '''
        self.sess.cleanup()

    def test_release_connection(self):
        with self.sess.pool.get_connection() as conn:
            self.assertEqual(1, len(self.sess.pool.active))
            self.assertEqual(0, len(self.sess.pool.idle))

        self.assertEqual(0, len(self.sess.pool.active))
        self.assertEqual(1, len(self.sess.pool.idle))

    def test_destroy_active(self):
        with self.sess.pool.get_connection() as conn:
            self.assertEqual(1, len(self.sess.pool.active))
            self.assertEqual(0, len(self.sess.pool.idle))
            conn.release(destroy=True)

        self.assertEqual(0, len(self.sess.pool.active))
        self.assertEqual(0, len(self.sess.pool.idle))

    def test_destroy_idle(self):
        with self.sess.pool.get_connection() as conn:
            self.assertEqual(1, len(self.sess.pool.active))
            self.assertEqual(0, len(self.sess.pool.idle))

        # cleanup all connections
        self.sess.cleanup()
        self.assertEqual(0, len(self.sess.pool.active))
        self.assertEqual(0, len(self.sess.pool.idle))

    def test_release_disconnected(self):
        with self.sess.pool.get_connection() as conn:
            self.assertEqual(1, len(self.sess.pool.active))
            self.assertEqual(0, len(self.sess.pool.idle))
            conn.disconnect()

        # even though disconnected, gets put into idle
        self.assertEqual(0, len(self.sess.pool.active))
        self.assertEqual(1, len(self.sess.pool.idle))

        # should remove all connections
        self.sess.cleanup()
        self.assertEqual(0, len(self.sess.pool.active))
        self.assertEqual(0, len(self.sess.pool.idle))


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
