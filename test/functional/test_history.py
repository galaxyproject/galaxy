from galaxy.test.base.twilltestcase import TwillTestCase
import sys, filecmp, string, os.path
from twill.commands import *

#
# the numbering of the tests is essential as they
# will be executed in order, sorted by name
#

class ToolTests(TwillTestCase):

    def test_00_upload(self): # this must run first
        "Clear history"
        self.clear_history()
        
	
    def test_history(self):
        """Test history """
        self.clear_history()

        # in range
        self.run_tool('ucsc_proxy')
        params = dict(
            hgta_regionType="range",
            hgta_outputType="primaryTable",
        )
        self.submit_form(1, button="hgta_doTopSubmit", **params)

        self.wait()
        self.check_data('ucsc_proxy_range.dat', hid=1)

        self.clear_history()
        if len(self.historyid()) > 0:
            raise AssertionError("Failure - clear history.")
        

        
