#! /usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import unittest
from irods.models import Collection, DataObject
from irods.session import iRODSSession
import irods.test.config as config
import xml.etree.ElementTree as ET
import logging
import irods.test.helpers as helpers

logger = logging.getLogger(__name__)

UNICODE_TEST_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'unicode_sampler.xml')


def parse_xml_file(path):
    # parse xml document
    parser = ET.XMLParser(encoding='utf-8')
    tree = ET.parse(path, parser)

    # default namespace
    nsmap = {'ns': 'http://www.w3.org/1999/xhtml'}

    # get table body
    table = tree.find('.//ns:tbody', nsmap)

    # extract values from table
    unicode_strings = set()
    for row in table:
        values = [column.text for column in row]

        # split strings in 3rd column
        for token in values[2].split():
            unicode_strings.add(token.strip('()'))

        # split strings in 4th column
        for token in values[3].split():
            unicode_strings.add(token.strip('()'))

    # fyi
    for string in unicode_strings:
        logger.info(string.encode('utf-8'))

    return unicode_strings


class TestUnicodeNames(unittest.TestCase):
    # test data
    coll_path = '/{0}/home/{1}/test_dir'.format(
        config.IRODS_SERVER_ZONE, config.IRODS_USER_USERNAME)

    def setUp(self):
        self.sess = iRODSSession(host=config.IRODS_SERVER_HOST,
                                 port=config.IRODS_SERVER_PORT,
                                 user=config.IRODS_USER_USERNAME,
                                 password=config.IRODS_USER_PASSWORD,
                                 zone=config.IRODS_SERVER_ZONE)

        # make list of unicode filenames, from file
        self.names = parse_xml_file(UNICODE_TEST_FILE)

        # Create dummy test collection
        self.coll = helpers.make_collection(
            self.sess, self.coll_path, self.names)

    def tearDown(self):
        '''Remove test data and close connections
        '''
        self.coll.remove(recurse=True, force=True)
        self.sess.cleanup()

    def test_files(self):
        # Query for all files in test collection
        query = self.sess.query(DataObject.name, Collection.name).filter(
            Collection.name == self.coll_path)

        for result in query.get_results():
            # check that we got back one of our original names
            assert result[DataObject.name] in self.names

            # fyi
            logger.info(
                u"{0}/{1}".format(result[Collection.name], result[DataObject.name]).encode('utf-8'))

            # remove from set
            self.names.remove(result[DataObject.name])

        # make sure we got all of them
        self.assertEqual(0, len(self.names))


if __name__ == '__main__':
    # let the tests find the parent irods lib
    sys.path.insert(0, os.path.abspath('../..'))
    unittest.main()
