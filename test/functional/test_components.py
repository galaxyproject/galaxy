from base.twilltestcase import TwillTestCase

class TestHistory( TwillTestCase ):

    def test_clear_history( self ):
        """test_componments.test_clear_history: Testing clearing history"""
        self.clear_history()
        if len(self.historyid()) > 0:
            raise AssertionError("test_framework.test_history failed")
    def test_delete_history_item( self ):
        """test_components.test_delete_history_item: Testing deleting history item"""
        self.clear_history()
        self.upload_file('1.bed', dbkey='hg15')
        self.check_history('hg15 bed')
        self.assertEqual ( len(self.get_data_list()), 1)
        self.delete_data(1)
        self.check_history("Your history is empty")
        self.assertEqual ( len(self.get_data_list()), 0)

class TestBasicFunctions( TwillTestCase ):
    
    def test_home_page(self):
        """test_components.test_home_page: Testing home page"""
        self.home()

class TestMetadata( TwillTestCase ):

    def test_metadata_edit(self):
        """test_components.test_metadata_edit: Testing metadata editing"""
        self.clear_history()
        self.upload_file('1.bed', dbkey='hg15')
        self.check_history('hg15 bed')
        self.edit_data(hid=1, dbkey='hg16', name='Testdata')
        self.check_history('hg16 Testdata bed')
        
        # test switching types
        # EDITED and changed by INS, 5/17/07
        # He who rejects change is the architect of decay - Harold Wilson
        #self.edit_data(hid=1, dbkey='hg16', chromCol='')
        #self.check_history('hg16 Testdata tabular')
        #
        #self.edit_data(hid=1, dbkey='hg15', chromCol='1', info='foo')
        #self.check_history('hg15 Testdata interval foo')
        """
        TODO: Ian make sure this test is functioning as you expect...
        """
        self.edit_data(hid=1, dbkey='hg16', is_strandCol="true")
        self.check_history('hg16 Testdata bed')
        
