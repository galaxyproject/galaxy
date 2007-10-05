from base.twilltestcase import TwillTestCase

class TestHistory( TwillTestCase ):

    def test_new_history( self ):
        """Testing creating a new history"""
        self.new_history()
        if len(self.get_datasets_in_history()) > 0:
            raise AssertionError("test_framework.test_new_history failed")
    def test_delete_history_item( self ):
        """Testing deleting history item"""
        self.new_history()
        self.upload_file('1.bed', dbkey='hg15')
        self.check_history_for_string('hg15 bed')
        self.assertEqual ( len(self.get_datasets_in_history()), 1)
        self.delete_history_item(1)
        self.check_history_for_string("Your history is empty")
        self.assertEqual ( len(self.get_datasets_in_history()), 0)
