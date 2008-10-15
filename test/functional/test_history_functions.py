from base.twilltestcase import TwillTestCase

class TestHistory( TwillTestCase ):

    def test_00_history_options_when_not_logged_in( self ):
        """Testing history options when not logged in"""
        self.logout()    #Ensure we are not logged in
        self.history_options()
        self.check_page_for_string( 'logged in</a> to store or switch histories.' )
        self.login( email='test2@bx.psu.edu' ) #Just to make sure we have created this account since it is used to share histories
        self.logout()
    def test_05_new_history_then_delete( self ):
        """Testing creating a new history and then deleting it"""
        self.login()
        self.new_history()
        if len(self.get_history()) > 0:
            raise AssertionError("test_new_history_then_delete failed")
        self.delete_history()
        self.check_page_for_string( 'History deleted:' )
    def test_10_history_options_when_logged_in( self ):
        """Testing history options when logged in"""
        self.history_options()
        self.check_page_for_string( 'Rename</a> current history')
        self.check_page_for_string( 'List</a> previously stored histories')
        self.check_page_for_string( 'Share</a> current history')
        self.check_page_for_string( 'Delete</a> current history')
    def test_10_history_rename( self ):
        """Testing renaming a history"""
        id, old_name, new_name = self.rename_history()
        self.check_page_for_string( 'History: %s renamed to: %s' %(old_name, new_name) )
    def test_15_history_view( self ):
        """Testing viewing previously stored histories"""
        self.view_stored_histories()
        self.check_page_for_string( 'Stored Histories' )
        self.check_page_for_string( '<input type=checkbox name="id" value=' )
        self.check_page_for_string( 'history_rename?id' )
        self.check_page_for_string( 'history_switch?id' )
        self.check_page_for_string( 'history_delete?id' )
    def test_20_delete_history_item( self ):
        """Testing deleting history item"""
        self.upload_file('1.bed', dbkey='hg15')
        self.check_history_for_string('hg15 bed')
        self.assertEqual ( len(self.get_history()), 1)
        self.delete_history_item(1)
        self.check_history_for_string("Your history is empty")
        self.assertEqual ( len(self.get_history()), 0)
    def test_25_share_history( self ):
        """Testing sharing a history with another user"""
        self.upload_file('1.bed', dbkey='hg18')
        id, name, email = self.share_history()
        try:
            self.check_page_for_string( 'History (%s) has been shared with: %s' %(name, email) )
        except TwillAssertionError:
            self.check_page_for_string( "The history or histories you've chosen to share contain datasets that the user you're sharing with does not have permission to access." )
        self.logout()
        self.login( email='test2@bx.psu.edu' )
        self.view_stored_histories()
        self.check_page_for_string( 'Unnamed history from test@bx.psu.edu' )
        histories = self.get_histories()
        for history in histories:
            if history.get( 'name' ) == 'Unnamed history from test@bx.psu.edu':
                id = history.get( 'id' )
                break
        self.assertTrue( id )
        self.delete_history( id )
        self.logout()
        self.login( email='test@bx.psu.edu' )
    def test_9999_clean_up( self ):
        self.delete_history()
        self.logout()
