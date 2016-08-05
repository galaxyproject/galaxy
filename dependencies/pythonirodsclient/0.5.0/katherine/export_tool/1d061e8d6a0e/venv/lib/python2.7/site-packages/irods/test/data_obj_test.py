#! /usr/bin/env python
import os
import sys
import socket
import unittest
from irods.models import Collection, DataObject
from irods.session import iRODSSession
from irods.exception import DataObjectDoesNotExist, CollectionDoesNotExist
from irods.column import Column, Criterion
import irods.test.config as config
import irods.test.helpers as helpers
import json
import errno
import hashlib
import base64


class TestDataObjOps(unittest.TestCase):

    def setUp(self):
        self.sess = iRODSSession(host=config.IRODS_SERVER_HOST,
                                 port=config.IRODS_SERVER_PORT,
                                 user=config.IRODS_USER_USERNAME,
                                 password=config.IRODS_USER_PASSWORD,
                                 zone=config.IRODS_SERVER_ZONE)

        # get server version
        with self.sess.pool.get_connection() as conn:
            self.server_version = tuple(int(token)
                                        for token in conn.server_version.replace('rods', '').split('.'))

        # Create dummy test collection
        self.coll_path = '/{0}/home/{1}/test_dir'.format(config.IRODS_SERVER_ZONE, config.IRODS_USER_USERNAME)
        self.coll = helpers.make_collection(self.sess, self.coll_path)

    def tearDown(self):
        '''Remove test data and close connections
        '''
        self.coll.remove(recurse=True, force=True)
        self.sess.cleanup()

    def make_new_server_config_json(self, server_config_filename):
        # load server_config.json to inject a new rule base
        with open(server_config_filename) as f:
            svr_cfg = json.load(f)

        # inject a new rule base into the native rule engine
        svr_cfg['rule_engines'][1]['plugin_specific_configuration'][
            're_rulebase_set'] = [{"filename": "test"}, {"filename": "core"}]

        # dump to a string to repave the existing server_config.json
        return json.dumps(svr_cfg, sort_keys=True, indent=4, separators=(',', ': '))

    def test_rename_obj(self):
        # test args
        collection = self.coll_path
        old_name = 'foo'
        new_name = 'bar'

        # make object in test collection
        path = "{collection}/{old_name}".format(**locals())
        obj = helpers.make_object(self.sess, path)

        # for coverage
        repr(obj)
        for replica in obj.replicas:
            repr(replica)

        # get object id
        saved_id = obj.id

        # rename object
        new_path = "{collection}/{new_name}".format(**locals())
        self.sess.data_objects.move(path, new_path)

        # get updated object
        obj = self.sess.data_objects.get(new_path)

        # compare ids
        self.assertEqual(obj.id, saved_id)

        # remove object
        self.sess.data_objects.unlink(new_path)

    def test_move_obj_to_coll(self):
        # test args
        collection = self.coll_path
        new_coll_name = 'my_coll'
        file_name = 'foo'

        # make object in test collection
        path = "{collection}/{file_name}".format(**locals())
        obj = helpers.make_object(self.sess, path)

        # get object id
        saved_id = obj.id

        # make new collection and move object to it
        new_coll_path = "{collection}/{new_coll_name}".format(**locals())
        new_coll = helpers.make_collection(self.sess, new_coll_path)
        self.sess.data_objects.move(path, new_coll_path)

        # get new object id
        new_path = "{collection}/{new_coll_name}/{file_name}".format(**locals())
        obj = self.sess.data_objects.get(new_path)

        # compare ids
        self.assertEqual(obj.id, saved_id)

        # remove new collection
        new_coll.remove(recurse=True, force=True)

    def test_invalid_get(self):
        # bad paths
        path_with_invalid_file = self.coll_path + '/hamsalad'
        path_with_invalid_coll = self.coll_path + '/hamsandwich/foo'

        with self.assertRaises(DataObjectDoesNotExist):
            obj = self.sess.data_objects.get(path_with_invalid_file)

        with self.assertRaises(DataObjectDoesNotExist):
            obj = self.sess.data_objects.get(path_with_invalid_coll)

    def test_force_unlink(self):
        collection = self.coll_path
        filename = 'test_force_unlink.txt'
        file_path = '{collection}/{filename}'.format(**locals())

        # make object
        obj = helpers.make_object(self.sess, file_path)

        # force remove object
        obj.unlink(force=True)

        # should be gone
        with self.assertRaises(DataObjectDoesNotExist):
            obj = self.sess.data_objects.get(file_path)

        # make sure it's not in the trash either
        conditions = [DataObject.name == filename,
                      Criterion('like', Collection.name, "/dev/trash/%%")]
        query = self.sess.query(
            DataObject.id, DataObject.name, Collection.name).filter(*conditions)
        results = query.all()
        self.assertEqual(len(results), 0)

    def test_obj_truncate(self):
        collection = self.coll_path
        filename = 'test_obj_truncate.txt'
        file_path = '{collection}/{filename}'.format(**locals())
        # random long content
        content = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'
        truncated_content = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

        # make object
        obj = helpers.make_object(self.sess, file_path, content)

        # truncate object
        obj.truncate(len(truncated_content))

        # read file
        obj = self.sess.data_objects.get(file_path)
        with obj.open('r') as f:
            self.assertEqual(f.read(), truncated_content)

    def test_multiple_reads(self):
        collection = self.coll_path

        # make files
        files = []
        for filename in ['foo', 'bar', 'baz']:
            path = '{collection}/{filename}'.format(**locals())
            helpers.make_object(self.sess, path=path, content=path)
            files.append(path)

        # read files
        for file in files:
            obj = self.sess.data_objects.get(file)
            with obj.open('r') as f:
                self.assertEqual(f.read(), obj.path)


    @unittest.skipIf(config.IRODS_SERVER_HOST != 'localhost' and config.IRODS_SERVER_HOST != socket.gethostname(),
                     "Cannot modify remote server configuration")
    def test_create_with_checksum(self):
        # skip if server is older than 4.2
        if self.server_version < (4, 2, 0):
            self.skipTest('Expects iRODS 4.2 server-side configuration')

        # server config
        server_config_dir = '/etc/irods'
        test_re_file = os.path.join(server_config_dir, 'test.re')
        server_config_file = os.path.join(
            server_config_dir, 'server_config.json')

        try:
            with helpers.file_backed_up(server_config_file):
                # make pep rule
                test_rule = "acPostProcForPut { msiDataObjChksum ($objPath, 'forceChksum=', *out )}"

                # write pep rule into test_re
                with open(test_re_file, 'w') as f:
                    f.write(test_rule)

                # make new server configuration with additional re file
                new_server_config = self.make_new_server_config_json(
                    server_config_file)

                # repave the existing server_config.json to add test_re
                with open(server_config_file, 'w') as f:
                    f.write(new_server_config)

                # must make a new connection for the agent to pick up the
                # updated configuration
                self.sess.cleanup()

                # test object
                collection = self.coll_path
                filename = 'checksum_test_file'
                obj_path = "{collection}/{filename}".format(**locals())
                contents = 'blah' * 100
                checksum = base64.b64encode(
                    hashlib.sha256(contents).digest()).decode()

                # make object in test collection
                obj = helpers.make_object(self.sess, obj_path, contents)

                # verify object's checksum
                self.assertEqual(
                    obj.checksum, "sha2:{checksum}".format(**locals()))

                # cleanup
                os.unlink(test_re_file)

        except IOError as e:
            # a likely fail scenario
            if e.errno == 13:
                self.fail("No permission to modify server configuration")
            raise
        except:
            raise


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
