from __future__ import print_function

import logging
import os
import time
import unittest
from json import loads

from galaxy.tools.verify import verify
from galaxy.tools.verify.test_data import TestDataResolver
from galaxy.web import security

from .driver_util import GalaxyTestDriver

log = logging.getLogger(__name__)

DEFAULT_TOOL_TEST_WAIT = os.environ.get("GALAXY_TEST_DEFAULT_WAIT", 86400)


class FunctionalTestCase(unittest.TestCase):

    def setUp(self):
        # Security helper
        self.security = security.SecurityHelper(id_secret='changethisinproductiontoo')
        self.history_id = os.environ.get('GALAXY_TEST_HISTORY_ID', None)
        self.host = os.environ.get('GALAXY_TEST_HOST')
        self.port = os.environ.get('GALAXY_TEST_PORT')
        default_url = "http://%s:%s" % (self.host, self.port)
        self.url = os.environ.get('GALAXY_TEST_EXTERNAL', default_url)
        self.test_data_resolver = TestDataResolver()
        tool_shed_test_file = os.environ.get('GALAXY_TOOL_SHED_TEST_FILE', None)
        if tool_shed_test_file:
            f = open(tool_shed_test_file, 'r')
            text = f.read()
            f.close()
            self.shed_tools_dict = loads(text)
        else:
            self.shed_tools_dict = {}
        self.keepOutdir = os.environ.get('GALAXY_TEST_SAVE', '')
        if self.keepOutdir > '':
            try:
                os.makedirs(self.keepOutdir)
            except:
                pass

    @classmethod
    def setUpClass(cls):
        """Configure and start Galaxy for a test."""
        cls._test_driver = None

        if not os.environ.get("GALAXY_TEST_ENVIRONMENT_CONFIGURED"):
            cls._test_driver = GalaxyTestDriver()
            cls._test_driver.setup(config_object=cls)

    @classmethod
    def tearDownClass(cls):
        """Shutdown Galaxy server and cleanup temp directory."""
        if cls._test_driver:
            cls._test_driver.tear_down()

    def get_filename(self, filename, shed_tool_id=None):
        # For tool tests override get_filename to point at an installed tool if shed_tool_id is set.
        if shed_tool_id and getattr(self, "shed_tools_dict", None):
            file_dir = self.shed_tools_dict[shed_tool_id]
            if file_dir:
                return os.path.abspath(os.path.join(file_dir, filename))
        return self.test_data_resolver.get_filename(filename)

    # TODO: Make this more generic, shouldn't be related to tool stuff I guess.
    def wait_for(self, func, **kwd):
        sleep_amount = 0.2
        slept = 0
        walltime_exceeded = kwd.get("maxseconds", None)
        if walltime_exceeded is None:
            walltime_exceeded = DEFAULT_TOOL_TEST_WAIT

        exceeded = True
        while slept <= walltime_exceeded:
            result = func()
            if result:
                time.sleep(sleep_amount)
                slept += sleep_amount
                sleep_amount *= 2
            else:
                exceeded = False
                break

        if exceeded:
            message = 'Tool test run exceeded walltime [total %s, max %s], terminating.' % (slept, walltime_exceeded)
            log.info(message)
            raise AssertionError(message)

    # TODO: Move verify_xxx into GalaxyInteractor or some relevant mixin.
    def verify_hid(self, filename, hda_id, attributes, shed_tool_id, hid="", dataset_fetcher=None):
        assert dataset_fetcher is not None

        def get_filename(test_filename):
            return self.get_filename(test_filename, shed_tool_id=shed_tool_id)

        def verify_extra_files(extra_files):
            self._verify_extra_files_content(extra_files, hda_id, shed_tool_id=shed_tool_id, dataset_fetcher=dataset_fetcher)

        data = dataset_fetcher(hda_id)
        item_label = "History item %s" % hid
        verify(
            item_label,
            data,
            attributes=attributes,
            filename=filename,
            get_filename=get_filename,
            keep_outputs_dir=self.keepOutdir,
            verify_extra_files=verify_extra_files,
        )

    def _verify_composite_datatype_file_content(self, file_name, hda_id, base_name=None, attributes=None, dataset_fetcher=None, shed_tool_id=None):
        assert dataset_fetcher is not None

        def get_filename(test_filename):
            return self.get_filename(test_filename, shed_tool_id=shed_tool_id)

        data = dataset_fetcher(hda_id, base_name)
        item_label = "History item %s" % hda_id
        try:
            verify(
                item_label,
                data,
                attributes=attributes,
                filename=file_name,
                get_filename=get_filename,
                keep_outputs_dir=self.keepOutdir,
            )
        except AssertionError as err:
            errmsg = 'Composite file (%s) of %s different than expected, difference:\n' % (base_name, item_label)
            errmsg += str(err)
            raise AssertionError(errmsg)

    def _verify_extra_files_content(self, extra_files, hda_id, dataset_fetcher, shed_tool_id=None):
        files_list = []
        for extra_type, extra_value, extra_name, extra_attributes in extra_files:
            if extra_type == 'file':
                files_list.append((extra_name, extra_value, extra_attributes))
            elif extra_type == 'directory':
                for filename in os.listdir(self.get_filename(extra_value, shed_tool_id=shed_tool_id)):
                    files_list.append((filename, os.path.join(extra_value, filename), extra_attributes))
            else:
                raise ValueError('unknown extra_files type: %s' % extra_type)
        for filename, filepath, attributes in files_list:
            self._verify_composite_datatype_file_content(filepath, hda_id, base_name=filename, attributes=attributes, dataset_fetcher=dataset_fetcher, shed_tool_id=shed_tool_id)
