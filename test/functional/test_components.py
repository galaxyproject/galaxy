from base.twilltestcase import TwillTestCase

class TestHistory( TwillTestCase ):

    def test_new_history( self ):
        """test_componments.test_new_history: Testing creating a new history"""
        self.new_history()
        if len(self.get_datasets_in_history()) > 0:
            raise AssertionError("test_framework.test_history failed")
    def test_delete_history_item( self ):
        """test_components.test_delete_history_item: Testing deleting history item"""
        self.new_history()
        self.upload_file('1.bed', dbkey='hg15')
        self.check_history_for_string('hg15 bed')
        self.assertEqual ( len(self.get_datasets_in_history()), 1)
        self.delete_history_item(1)
        self.check_history_for_string("Your history is empty")
        self.assertEqual ( len(self.get_datasets_in_history()), 0)

class TestBasicFunctions( TwillTestCase ):
    
    def test_home_page(self):
        """test_components.test_home_page: Testing home page"""
        self.home()

class TestMetadata( TwillTestCase ):

    def test_metadata_edit(self):
        """test_components.test_metadata_edit: Testing metadata editing"""
        self.new_history()
        self.upload_file('1.bed', dbkey='hg15')
        self.check_history_for_string('hg15 bed')
        self.edit_metadata(hid=1, dbkey='hg16', name='Testdata')
        self.check_history_for_string('hg16 Testdata bed')
        
        # test switching types
        # EDITED and changed by INS, 5/17/07
        # He who rejects change is the architect of decay - Harold Wilson
        #self.edit_metadata(hid=1, dbkey='hg16', chromCol='')
        #self.check_history_for_string('hg16 Testdata tabular')
        #
        #self.edit_metadata(hid=1, dbkey='hg15', chromCol='1', info='foo')
        #self.check_history_for_string('hg15 Testdata interval foo')
        """
        TODO: Ian make sure this test is functioning as you expect...
        """
        self.edit_metadata(hid=1, dbkey='hg16', is_strandCol="true")
        self.check_history_for_string('hg16 Testdata bed')
        
