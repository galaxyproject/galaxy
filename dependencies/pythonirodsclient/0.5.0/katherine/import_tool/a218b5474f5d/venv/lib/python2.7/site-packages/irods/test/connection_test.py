#! /usr/bin/env python
import os
import sys
import unittest
from irods.session import iRODSSession
from irods.exception import NetworkException
import irods.test.config as config


class TestConnections(unittest.TestCase):

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

    def test_connection(self):
        with self.sess.pool.get_connection() as conn:
            self.assertTrue(conn)

    def test_connection_destructor(self):
        conn = self.sess.pool.get_connection()
        conn.__del__()
        conn.release(destroy=True)

    def test_failed_connection(self):
        # mess with the account's port
        self.sess.pool.account.port = 6666

        # try connecting
        with self.assertRaises(NetworkException):
            self.sess.pool.get_connection()

        # set port back
        self.sess.pool.account.port = config.IRODS_SERVER_PORT

    def test_send_failure(self):
        with self.sess.pool.get_connection() as conn:
            # try to close connection twice, 2nd one should fail
            conn.disconnect()
            with self.assertRaises(NetworkException):
                conn.disconnect()

    def test_reply_failure(self):
        with self.sess.pool.get_connection() as conn:
            # close connection
            conn.disconnect()

            # try sending reply
            with self.assertRaises(NetworkException):
                conn.reply(0)
        
        
if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
