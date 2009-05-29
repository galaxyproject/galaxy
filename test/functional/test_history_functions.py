import galaxy.model
from galaxy.model.orm import *
from base.twilltestcase import *

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
        self.check_page_for_string( 'Deleted 1 histories' )
    def test_10_history_options_when_logged_in( self ):
        """Testing history options when logged in"""
        self.history_options()
        self.check_page_for_string( 'Rename</a> current history' )
        self.check_page_for_string( 'List</a> previously stored histories' )
        self.check_page_for_string( 'Construct workflow</a> from the current history' )
        self.check_page_for_string( 'Share</a> current history' )
        # Tests for changing default history permissions are done in test_security_and_libraries.py
        self.check_page_for_string( 'Change default permissions</a> for the current history' )
        self.check_page_for_string( 'Show deleted</a> datasets in history' )
        self.check_page_for_string( 'Delete</a> current history' )
        # Need to add a history item in order to create a new empty history
        try:
            self.check_page_for_string( 'Create</a> a new empty history' )
            raise AssertionError, "Incorrectly able to create a new empty history when the current history is empty."
        except:
            pass
        self.upload_file( '1.bed', dbkey='hg18' )
        self.history_options()
        self.check_page_for_string( 'Create</a> a new empty history' )
    def test_15_history_rename( self ):
        """Testing renaming a history"""
        id, old_name, new_name = self.rename_history()
        self.check_page_for_string( 'History: %s renamed to: %s' %(old_name, new_name) )
    def test_20_history_list( self ):
        """Testing viewing previously stored histories"""
        self.view_stored_histories()
        self.check_page_for_string( 'Stored histories' )
        self.check_page_for_string( '<input type="checkbox" name="id" value=' )
        self.check_page_for_string( 'operation=Rename&id' )
        self.check_page_for_string( 'operation=Switch&id' )
        self.check_page_for_string( 'operation=Delete&id' )
    def test_25_history_share( self ):
        """Testing sharing a history with another user"""
        self.upload_file('1.bed', dbkey='hg18')
        id, name, email = self.share_history()
        self.logout()
        self.login( email=email )
        self.home()
        check_str = 'Unnamed history from test@bx.psu.edu'
        self.view_stored_histories( check_str=check_str )
        histories = self.get_histories()
        for history in histories:
            if history.get( 'name' ) == 'Unnamed history from test@bx.psu.edu':
                id = history.get( 'id' )
                break
        self.assertTrue( id )
        self.delete_history( id )
        self.logout()
        self.login( email='test@bx.psu.edu' )
    def test_30_history_show_and_hide_deleted_datasets( self ):
        """Testing displaying deleted history items"""
        self.new_history()
        self.upload_file('1.bed', dbkey='hg18')
        latest_hda = galaxy.model.HistoryDatasetAssociation.query() \
            .order_by( desc( galaxy.model.HistoryDatasetAssociation.table.c.create_time ) ).first()
        self.home()
        self.visit_url( "%s/root/delete?show_deleted_on_refresh=False&id=%s" % ( self.url, str( latest_hda.id ) ) )
        self.check_history_for_string( 'Your history is empty' )
        self.home()
        self.visit_url( "%s/history/?show_deleted=True" % self.url )
        self.check_page_for_string( 'This dataset has been deleted.' )
        self.check_page_for_string( '1.bed' )
        self.home()
        self.visit_url( "%s/history/?show_deleted=False" % self.url )
        self.check_page_for_string( 'Your history is empty' )
    def test_35_deleting_and_undeleting_history_items( self ):
        """Testing deleting and un-deleting history items"""
        self.new_history()
        # Add a new history item
        self.upload_file( '1.bed', dbkey='hg15' )
        self.home()
        self.visit_url( "%s/history/?show_deleted=False" % self.url )
        self.check_page_for_string( '1.bed' )
        self.check_page_for_string( 'hg15' )
        self.assertEqual ( len( self.get_history() ), 1 )
        # Delete the history item
        self.delete_history_item( 1, check_str="Your history is empty" )
        self.assertEqual ( len( self.get_history() ), 0 )
        # Try deleting an invalid hid
        try:
            self.delete_history_item( 'XXX' )
            raise AssertionError, "Inproperly able to delete hid 'XXX' which is not an integer"
        except:
            pass
        # Undelete the history item
        self.undelete_history_item( 1, show_deleted=True )
        self.home()
        self.visit_url( "%s/history/?show_deleted=False" % self.url )
        self.check_page_for_string( '1.bed' )
        self.check_page_for_string( 'hg15' )
    def test_9999_clean_up( self ):
        self.delete_history()
        self.logout()
