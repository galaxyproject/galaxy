from base.twilltestcase import TwillTestCase
import base.test_db_util as test_db_util


class TestDatasetFeatures( TwillTestCase ):

    def test_0000_initiate_users( self ):
        """Ensuring all required user accounts exist"""
        self.logout()
        self.login( email='test@bx.psu.edu', username='admin-user' )
        global admin_user
        admin_user = test_db_util.get_user( 'test@bx.psu.edu' )
        assert admin_user is not None, 'Problem retrieving user with email "test@bx.psu.edu" from the database'
        global admin_user_private_role
        admin_user_private_role = test_db_util.get_private_role( admin_user )
        latest_history = test_db_util.get_latest_history_for_user( admin_user )
        self.delete_history( id=self.security.encode_id( latest_history.id ) )
        self.new_history()
        latest_history = test_db_util.get_latest_history_for_user( admin_user )
        assert latest_history is not None, "Problem retrieving latest_history from database"

    def test_0005_initiate_data( self ):
        '''Ensure that data exists for this test suite.'''
        self.upload_file( '1.bed' )

    def test_0010_view_dataset_params( self ):
        '''Test viewing a dataset's parameters.'''
        hda = self.find_hda_by_dataset_name( '1.bed' )
        assert hda is not None, 'Could not retrieve latest hda from history API.'
        self.visit_url( '/datasets/%s/show_params' % hda[ 'id'] )
        self.check_for_strings( strings_displayed=[ '1.bed', 'uploaded' ] )

    def test_0015_report_dataset_error( self ):
        '''Load and submit the report error form. This should show an error message, as the functional test instance should not be configured for email.'''
        hda = test_db_util.get_latest_hda()
        self.visit_url( '/dataset/errors?id=%s' % self.security.encode_id( hda.hid ) )
        self.check_for_strings( strings_displayed=[ 'Report this error', 'Your email' ] )
        self.submit_form( button='submit_error_report', email='test@bx.psu.edu', message='This tool completed successfully, disregard.' )
        self.check_for_strings( strings_displayed=[ 'Mail is not configured' ] )
