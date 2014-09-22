import StringIO
import difflib
import filecmp
import logging
import os
import pprint
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
import unittest
import urllib
import zipfile

from base.asserts import verify_assertions
from galaxy.util import asbool
from galaxy.util.json import loads
from galaxy.web import security
from galaxy.web.framework.helpers import iff
from urlparse import urlparse

from galaxy import eggs
eggs.require( "elementtree" )
eggs.require( 'twill' )

from elementtree import ElementTree

import twill
import twill.commands as tc
from twill.other_packages._mechanize_dist import ClientForm

#Force twill to log to a buffer -- FIXME: Should this go to stdout and be captured by nose?
buffer = StringIO.StringIO()
twill.set_output( buffer )
tc.config( 'use_tidy', 0 )

# Dial ClientCookie logging down (very noisy)
logging.getLogger( "ClientCookie.cookies" ).setLevel( logging.WARNING )
log = logging.getLogger( __name__ )


class TwillTestCase( unittest.TestCase ):

    def setUp( self ):
        # Security helper
        self.security = security.SecurityHelper( id_secret='changethisinproductiontoo' )
        self.history_id = os.environ.get( 'GALAXY_TEST_HISTORY_ID', None )
        self.host = os.environ.get( 'GALAXY_TEST_HOST' )
        self.port = os.environ.get( 'GALAXY_TEST_PORT' )
        self.url = "http://%s:%s" % ( self.host, self.port )
        self.file_dir = os.environ.get( 'GALAXY_TEST_FILE_DIR', None )
        self.tool_shed_test_file = os.environ.get( 'GALAXY_TOOL_SHED_TEST_FILE', None )
        if self.tool_shed_test_file:
            f = open( self.tool_shed_test_file, 'r' )
            text = f.read()
            f.close()
            self.shed_tools_dict = loads( text )
        else:
            self.shed_tools_dict = {}
        self.keepOutdir = os.environ.get( 'GALAXY_TEST_SAVE', '' )
        if self.keepOutdir > '':
            try:
                os.makedirs(self.keepOutdir)
            except:
                pass

    def act_on_multiple_datasets( self, cntrller, library_id, do_action, ldda_ids='', strings_displayed=[] ):
        # Can't use the ~/library_admin/libraries form as twill barfs on it so we'll simulate the form submission
        # by going directly to the form action
        self.visit_url( '%s/library_common/act_on_multiple_datasets?cntrller=%s&library_id=%s&ldda_ids=%s&do_action=%s' \
                        % ( self.url, cntrller, library_id, ldda_ids, do_action ) )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )

    def add_bar_codes( self, cntrller, request_id, bar_codes, strings_displayed=[], strings_displayed_after_submit=[] ):
        url = "%s/requests_common/edit_samples?cntrller=%s&id=%s" % ( self.url, cntrller, request_id )
        self.visit_url( url )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        for sample_index, bar_code in enumerate( bar_codes ):
            tc.fv( "1", "sample_%i_bar_code" % sample_index, bar_code )
        tc.submit( "save_samples_button" )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )

    def add_datasets_to_sample( self, request_id, sample_id, external_service_id, sample_datasets, strings_displayed=[], strings_displayed_after_submit=[] ):
        # visit the dataset selection page
        url = "%s/requests_admin/select_datasets_to_transfer?cntrller=requests_admin&sample_id=%s&request_id=%s&external_service_id=%s" % \
            ( self.url, sample_id, request_id, external_service_id )
        self.visit_url( url )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        # Datasets are associated with the given by the building the appropriate url
        # and calling it as the dataset selection UI is a javascript dynatree
        url = "%s/requests_admin/select_datasets_to_transfer?cntrller=requests_admin&sample_id=%s&request_id=%s" % ( self.url, sample_id, request_id )
        url += '&select_datasets_to_transfer_button=Select%20datasets'
        url += '&selected_datasets_to_transfer=%s' % ','.join( sample_datasets )
        self.visit_url( url )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )

    def add_folder( self, cntrller, library_id, folder_id, name='Folder One', description='This is Folder One' ):
        """Create a new folder"""
        url = "%s/library_common/create_folder?cntrller=%s&library_id=%s&parent_id=%s" % ( self.url, cntrller, library_id, folder_id )
        self.visit_url( url )
        self.check_page_for_string( 'Create a new folder' )
        tc.fv( "1", "name", name )
        tc.fv( "1", "description", description )
        tc.submit( "new_folder_button" )
        check_str = "The new folder named '%s' has been added to the data library." % name
        self.check_page_for_string( check_str )

    def add_samples( self, cntrller, request_id, sample_value_tuples, folder_options=[], strings_displayed=[], strings_displayed_after_submit=[] ):
        url = "%s/requests_common/add_sample?cntrller=%s&request_id=%s&add_sample_button=Add+sample" % ( self.url, cntrller, request_id )
        self.visit_url( url )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        for sample_index, ( sample_name, target_library_info, sample_field_values ) in enumerate( sample_value_tuples ):
            tc.fv( "add_samples", "sample_%i_name" % sample_index, sample_name )
            if target_library_info[ 'library' ] is not None:
                tc.fv( "add_samples", "sample_%i_library_id" % sample_index, target_library_info[ 'library' ] )
                self.refresh_form( "sample_%i_library_id" % sample_index, target_library_info[ 'library' ] )
            # check if the folder selectfield has been correctly populated
            for check_str in folder_options:
                self.check_page_for_string( check_str )
            if target_library_info[ 'folder' ] is not None:
                tc.fv( "add_samples", "sample_%i_folder_id" % sample_index, target_library_info[ 'folder' ] )
            for field_index, field_value in enumerate( sample_field_values ):
                tc.fv( "add_samples", "sample_%i_field_%i" % ( sample_index, field_index ), field_value )
            # Do not click on Add sample button when all the sample have been added
            if sample_index < len( sample_value_tuples ) - 1:
                tc.submit( "add_sample_button" )
        # select the correct form before submitting it
        tc.fv( "add_samples", "copy_sample_index", "-1" )
        tc.submit( "save_samples_button" )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )

    def add_tag( self, item_id, item_class, context, new_tag ):
        self.visit_url( "%s/tag/add_tag_async?item_id=%s&item_class=%s&context=%s&new_tag=%s" % \
                        ( self.url, item_id, item_class, context, new_tag ) )

    def add_template( self, cntrller, item_type, form_type, form_id, form_name,
                      library_id=None, folder_id=None, ldda_id=None, request_type_id=None, sample_id=None ):
        """
        Add a new template to an item - for library items, the template will ALWAYS BE SET TO INHERITABLE here.  If you want to
        dis-inherit your template, call the manage_library_template_inheritance() below immediately after you call this
        method in your test code.  Templates added to Requesttype objects are always inherited to samples.
        """
        params = dict( cntrller=cntrller, item_type=item_type, form_type=form_type, library_id=library_id )
        url = "/library_common/add_template"
        if item_type == 'folder':
            params[ 'folder_id' ] = folder_id
        elif item_type == 'ldda':
            params[ 'ldda_id' ] = ldda_id
        self.visit_url( url, params )
        self.check_page_for_string ( "Select a template for the" )
        self.refresh_form( "form_id", form_id )
        # For some unknown reason, twill barfs if the form number ( 1 ) is used in the following
        # rather than the form anme ( select_template ), so we have to use the form name.
        tc.fv( "select_template", "inheritable", '1' )
        tc.submit( "add_template_button" )
        self.check_page_for_string = 'A template based on the form "%s" has been added to this' % form_name

    def add_user_address( self, user_id, address_dict ):
        self.visit_url( "%s/user/new_address?cntrller=user&user_id=%s" % ( self.url, user_id ) )
        self.check_page_for_string( 'Add new address' )
        for field_name, value in address_dict.items():
            tc.fv( "1", field_name, value )
        tc.submit( "new_address_button" )
        self.check_page_for_string( 'Address (%s) has been added' % address_dict[ 'short_desc' ] )

    def associate_users_and_groups_with_role( self, role_id, role_name, user_ids=[], group_ids=[] ):
        url = "%s/admin/role?id=%s&role_members_edit_button=Save" % ( self.url, role_id )
        if user_ids:
            url += "&in_users=%s" % ','.join( user_ids )
        if group_ids:
            url += "&in_groups=%s" % ','.join( group_ids )
        self.visit_url( url )
        check_str = "Role '%s' has been updated with %d associated users and %d associated groups" % ( role_name, len( user_ids ), len( group_ids ) )
        self.check_page_for_string( check_str )

    def associate_users_and_roles_with_group( self, group_id, group_name, user_ids=[], role_ids=[] ):
        url = "%s/admin/manage_users_and_roles_for_group?id=%s&group_roles_users_edit_button=Save" % ( self.url, group_id )
        if user_ids:
            url += "&in_users=%s" % ','.join( user_ids )
        if role_ids:
            url += "&in_roles=%s" % ','.join( role_ids )
        self.visit_url( url )
        check_str = "Group '%s' has been updated with %d associated roles and %d associated users" % ( group_name, len( role_ids ), len( user_ids ) )
        self.check_page_for_string( check_str )

    def auto_detect_metadata( self, hda_id ):
        """Auto-detect history_dataset_association metadata"""
        self.visit_url( "%s/datasets/%s/edit" % ( self.url, self.security.encode_id( hda_id ) ) )
        self.check_page_for_string( 'This will inspect the dataset and attempt' )
        tc.fv( 'auto_detect', 'detect', 'Auto-detect' )
        tc.submit( 'detect' )
        try:
            self.check_page_for_string( 'Attributes have been queued to be updated' )
            self.wait()
        except AssertionError:
            self.check_page_for_string( 'Attributes updated' )

    def browse_groups( self, strings_displayed=[] ):
        self.visit_url( '%s/admin/groups' % self.url )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )

    def browse_libraries_admin( self, deleted=False, strings_displayed=[], strings_not_displayed=[] ):
        self.visit_url( '%s/library_admin/browse_libraries?sort=name&f-description=All&f-name=All&f-deleted=%s' % ( self.url, str( deleted ) ) )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        for check_str in strings_not_displayed:
            try:
                self.check_page_for_string( check_str )
                raise AssertionError( "String (%s) incorrectly displayed when browing library." % check_str )
            except:
                pass

    def browse_libraries_regular_user( self, strings_displayed=[], strings_not_displayed=[] ):
        self.visit_url( '%s/library/browse_libraries' % self.url )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        for check_str in strings_not_displayed:
            try:
                self.check_page_for_string( check_str )
                raise AssertionError( "String (%s) incorrectly displayed when browing library." % check_str )
            except:
                pass

    def browse_library( self, cntrller, library_id, show_deleted=False, strings_displayed=[], strings_not_displayed=[] ):
        self.visit_url( '%s/library_common/browse_library?cntrller=%s&id=%s&show_deleted=%s' % ( self.url, cntrller, library_id, str( show_deleted ) ) )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        for check_str in strings_not_displayed:
            try:
                self.check_page_for_string( check_str )
                raise AssertionError( "String (%s) incorrectly displayed when browing library." % check_str )
            except:
                pass

    def browse_roles( self, strings_displayed=[] ):
        self.visit_url( '%s/admin/roles' % self.url )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )

    def change_sample_state( self, request_id, sample_ids, new_sample_state_id, comment='', strings_displayed=[], strings_displayed_after_submit=[] ):
        url = "%s/requests_common/edit_samples?cntrller=requests_admin&id=%s" % ( self.url, request_id )
        self.visit_url( url )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        for sample_id in sample_ids:
            tc.fv( "1", "select_sample_%i" % sample_id, True )
        tc.fv( "1", "sample_operation", 'Change state' )
        # refresh on change to show the sample states selectfield
        self.refresh_form( "sample_operation", 'Change state' )
        self.check_page_for_string( "Change current state" )
        tc.fv( "1", "sample_state_id", new_sample_state_id )
        tc.fv( "1", "sample_event_comment", comment )
        tc.submit( "save_samples_button" )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )

    def change_sample_target_data_library( self, cntrller, request_id, sample_ids, new_library_id, new_folder_id, folder_options=[], comment='', strings_displayed=[], strings_displayed_after_submit=[] ):
        url = "%s/requests_common/edit_samples?cntrller=%s&id=%s" % ( self.url, cntrller, request_id )
        self.visit_url( url )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        for sample_id in sample_ids:
            tc.fv( "edit_samples", "select_sample_%i" % sample_id, True )
        tc.fv( "edit_samples", "sample_operation", 'Select data library and folder' )
        # refresh on change to show the data libraries selectfield
        self.refresh_form( "sample_operation", 'Select data library and folder' )
        self.check_page_for_string( "Select data library:" )
        tc.fv( "1", "sample_operation_library_id", new_library_id )
        # refresh on change to show the selectfield with the list of
        # folders in the selected data library above
        self.refresh_form( "sample_operation_library_id", new_library_id )
        self.check_page_for_string( "Select folder:" )
        # check if the folder selectfield has been correctly populated
        for check_str in folder_options:
            self.check_page_for_string( check_str )
        tc.fv( "1", "sample_operation_folder_id", new_folder_id )
        tc.submit( "save_samples_button" )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )

    def change_datatype( self, hda_id, datatype ):
        """Change format of history_dataset_association"""
        self.visit_url( "%s/datasets/%s/edit" % ( self.url, self.security.encode_id( hda_id ) ) )
        self.check_page_for_string( 'This will change the datatype of the existing dataset but' )
        tc.fv( 'change_datatype', 'datatype', datatype )
        tc.submit( 'change' )
        self.check_page_for_string( 'Changed the type of dataset' )

    def check_archive_contents( self, archive, lddas ):
        def get_ldda_path( ldda ):
            path = ""
            parent_folder = ldda.library_dataset.folder
            while parent_folder is not None:
                if parent_folder.parent is None:
                    path = os.path.join( parent_folder.library_root[0].name, path )
                    break
                path = os.path.join( parent_folder.name, path )
                parent_folder = parent_folder.parent
            path += ldda.name
            return path
        def mkdir( file ):
            dir = os.path.join( tmpd, os.path.dirname( file ) )
            if not os.path.exists( dir ):
                os.makedirs( dir )
        tmpd = tempfile.mkdtemp()
        if tarfile.is_tarfile( archive ):
            t = tarfile.open( archive )
            for n in t.getnames():
                mkdir( n )
                t.extract( n, tmpd )
            t.close()
        elif zipfile.is_zipfile( archive ):
            z = zipfile.ZipFile( archive, 'r' )
            for n in z.namelist():
                mkdir( n )
                open( os.path.join( tmpd, n ), 'wb' ).write( z.read( n ) )
            z.close()
        else:
            raise Exception( 'Unable to read archive: %s' % archive )
        for ldda in lddas:
            orig_file = self.get_filename( ldda.name )
            downloaded_file = os.path.join( tmpd, get_ldda_path( ldda ) )
            assert os.path.exists( downloaded_file )
            try:
                self.files_diff( orig_file, downloaded_file )
            except AssertionError, err:
                errmsg = 'Library item %s different than expected, difference:\n' % ldda.name
                errmsg += str( err )
                errmsg += 'Unpacked archive remains in: %s\n' % tmpd
                raise AssertionError( errmsg )
        shutil.rmtree( tmpd )

    def check_for_strings( self, strings_displayed=[], strings_not_displayed=[] ):
        if strings_displayed:
            for string in strings_displayed:
                self.check_page_for_string( string )
        if strings_not_displayed:
            for string in strings_not_displayed:
                self.check_string_not_in_page( string )

    def check_hda_attribute_info( self, hda_id, strings_displayed=[] ):
        """Edit history_dataset_association attribute information"""
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )

    def check_hda_json_for_key_value( self, hda_id, key, value, use_string_contains=False ):
        """
        Uses the history API to determine whether the current history:
        (1) Has a history dataset with the required ID.
        (2) That dataset has the required key.
        (3) The contents of that key match the provided value.
        If use_string_contains=True, this will perform a substring match, otherwise an exact match.
        """
        #TODO: multi key, value
        hda = dict()
        for history_item in self.get_history_from_api():
            if history_item[ 'id' ] == hda_id:
                hda = self.json_from_url( history_item[ 'url' ] )
                break
        if hda:
            if key in hda:
                if use_string_contains:
                    return value in hda[ key ]
                else:
                    return value == hda[ key ]
        return False

    def check_history_for_errors( self ):
        """Raises an exception if there are errors in a history"""
        self.visit_url( "/history" )
        page = self.last_page()
        if page.find( 'error' ) > -1:
            raise AssertionError( 'Errors in the history for user %s' % self.user )

    def check_history_for_string( self, patt, show_deleted=False ):
        """Breaks patt on whitespace and searches for each element seperately in the history"""
        if show_deleted:
            params = dict( show_deleted=True )
            self.visit_url( "/history", params )
        else:
            self.visit_url( "/history" )
        for subpatt in patt.split():
            try:
                tc.find( subpatt )
            except:
                fname = self.write_temp_file( tc.browser.get_html() )
                errmsg = "no match to '%s'\npage content written to '%s'" % ( subpatt, fname )
                raise AssertionError( errmsg )

    def check_history_for_exact_string( self, string, show_deleted=False ):
        """Looks for exact match to 'string' in history page"""
        if show_deleted:
            self.visit_url( "/history?show_deleted=True" )
        else:
            self.visit_url( "/history" )
        try:
            tc.find( string )
        except:
            fname = self.write_temp_file( tc.browser.get_html() )
            errmsg = "no match to '%s'\npage content written to '%s'" % ( string, fname )
            raise AssertionError( errmsg )

    def check_history_json( self, check_fn, show_deleted=None ):
        """
        Tries to find a JSON string in the history page using the regex pattern,
        parse it, and assert check_fn returns True when called on that parsed
        data.
        """
        try:
            json_data = self.get_history_from_api( show_deleted=show_deleted, show_details=True )
            check_result = check_fn( json_data )
            assert check_result, 'failed check_fn: %s (got %s)' % ( check_fn.func_name, str( check_result ) )
        except Exception, e:
            log.exception( e )
            log.debug( 'json_data: %s', ( '\n' + pprint.pformat( json_data ) if json_data else '(no match)' ) )
            fname = self.write_temp_file( tc.browser.get_html() )
            errmsg = ( "json could not be read\npage content written to '%s'" % ( fname ) )
            raise AssertionError( errmsg )

    def check_metadata_for_string( self, patt, hid=None ):
        """Looks for 'patt' in the edit page when editing a dataset"""
        data_list = self.get_history_as_data_list()
        self.assertTrue( data_list )
        if hid is None:  # take last hid
            elem = data_list[-1]
            hid = int( elem.get('hid') )
        self.assertTrue( hid )
        self.visit_url( "/dataset/edit?hid=%s" % hid )
        for subpatt in patt.split():
            tc.find(subpatt)

    def check_page(self, strings_displayed, strings_displayed_count, strings_not_displayed):
        """Checks a page for strings displayed, not displayed and number of occurrences of a string"""
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        for check_str, count in strings_displayed_count:
            self.check_string_count_in_page( check_str, count )
        for check_str in strings_not_displayed:
            self.check_string_not_in_page( check_str )

    def check_page_for_string( self, patt ):
        """Looks for 'patt' in the current browser page"""
        page = self.last_page()
        if page.find( patt ) == -1:
            fname = self.write_temp_file( page )
            errmsg = "no match to '%s'\npage content written to '%s'" % ( patt, fname )
            raise AssertionError( errmsg )

    def check_request_grid( self, cntrller, state, deleted=False, strings_displayed=[] ):
        params = { 'f-state': state, 'f-deleted': deleted, 'sort': 'create_time' }
        self.visit_url( '/%s/browse_requests' % cntrller )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )

    def check_string_count_in_page( self, patt, min_count ):
        """Checks the number of 'patt' occurrences in the current browser page"""
        page = self.last_page()
        patt_count = page.count( patt )
        # The number of occurrences of patt in the page should be at least min_count
        # so show error if patt_count is less than min_count
        if patt_count < min_count:
            fname = self.write_temp_file( page )
            errmsg = "%i occurrences of '%s' found instead of %i.\npage content written to '%s' " % ( min_count, patt, patt_count, fname )
            raise AssertionError( errmsg )

    def check_string_not_in_page( self, patt ):
        """Checks to make sure 'patt' is NOT in the page."""
        page = self.last_page()
        if page.find( patt ) != -1:
            fname = self.write_temp_file( page )
            errmsg = "string (%s) incorrectly displayed in page.\npage content written to '%s'" % ( patt, fname )
            raise AssertionError( errmsg )

    def clear_cookies( self ):
        tc.clear_cookies()

    def clear_form( self, form=0 ):
        """Clears a form"""
        tc.formclear(str(form))

    def copy_history( self, history_id, copy_choice, strings_displayed=[], strings_displayed_after_submit=[] ):
        self.visit_url( "/history/copy?id=%s" % history_id )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        tc.fv( '1', 'copy_choice', copy_choice )
        tc.submit( 'copy_choice_button' )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )

    def convert_format( self, hda_id, target_type ):
        """Convert format of history_dataset_association"""
        self.visit_url( "%s/datasets/%s/edit" % ( self.url, self.security.encode_id( hda_id ) ) )
        self.check_page_for_string( 'This will inspect the dataset and attempt' )
        tc.fv( 'convert_data', 'target_type', target_type )
        tc.submit( 'convert_data' )
        self.check_page_for_string( 'The file conversion of Convert BED to GFF on data' )
        self.wait()  # wait for the format convert tool to finish before returning

    def copy_history_item( self, source_history_id=None, source_dataset_id=None, target_history_id=None, all_target_history_ids=[],
                           deleted_history_ids=[] ):
        """
        Copy 1 history_dataset_association to 1 history (Limited by twill since it doesn't support multiple
        field names, such as checkboxes
        """
        self.visit_url( "/dataset/copy_datasets" )
        self.check_page_for_string( 'Source History:' )
        # Make sure all of users active histories are displayed
        for id in all_target_history_ids:
            self.check_page_for_string( id )
        # Make sure only active histories are displayed
        for id in deleted_history_ids:
            try:
                self.check_page_for_string( id )
                raise AssertionError( "deleted history id %d displayed in list of target histories" % id )
            except:
                pass
        form_values = [ ( 'source_history', source_history_id ),
                        ( 'target_history_id', target_history_id ),
                        ( 'source_content_ids', 'dataset|%s' % source_dataset_id ),
                        ( 'do_copy', True ) ]
        self.visit_url( "/dataset/copy_datasets", params=form_values )
        check_str = '1 dataset copied to 1 history'
        self.check_page_for_string( check_str )

    # Functions associated with user accounts

    def create( self, cntrller='user', email='test@bx.psu.edu', password='testuser', username='admin-user', redirect='' ):
        # HACK: don't use panels because late_javascripts() messes up the twill browser and it
        # can't find form fields (and hence user can't be logged in).
        params = dict( cntrller=cntrller, use_panels=False )
        self.visit_url( "/user/create", params )
        tc.fv( 'registration', 'email', email )
        tc.fv( 'registration', 'redirect', redirect )
        tc.fv( 'registration', 'password', password )
        tc.fv( 'registration', 'confirm', password )
        tc.fv( 'registration', 'username', username )
        tc.submit( 'create_user_button' )
        previously_created = False
        username_taken = False
        invalid_username = False
        try:
            self.check_page_for_string( "Created new user account" )
        except:
            try:
                # May have created the account in a previous test run...
                self.check_page_for_string( "User with that email already exists" )
                previously_created = True
            except:
                try:
                    self.check_page_for_string( 'Public name is taken; please choose another' )
                    username_taken = True
                except:
                    try:
                        # Note that we're only checking if the usr name is >< 4 chars here...
                        self.check_page_for_string( 'Public name must be at least 4 characters in length' )
                        invalid_username = True
                    except:
                        pass
        return previously_created, username_taken, invalid_username

    def create_library( self, name='Library One', description='This is Library One', synopsis='Synopsis for Library One' ):
        """Create a new library"""
        self.visit_url( "%s/library_admin/create_library" % self.url )
        self.check_page_for_string( 'Create a new data library' )
        tc.fv( "1", "name", name )
        tc.fv( "1", "description", description )
        tc.fv( "1", "synopsis", synopsis )
        tc.submit( "create_library_button" )
        check_str = "The new library named '%s' has been created" % name
        self.check_page_for_string( check_str )

    def create_user_with_info( self, email, password, username, user_info_values, user_type_fd_id='', cntrller='user',
                               strings_displayed=[], strings_displayed_after_submit=[] ):
        # This method creates a new user with associated info
        self.visit_url( "%s/user/create?cntrller=%s&use_panels=False" % ( self.url, cntrller ) )
        tc.fv( "registration", "email", email )
        tc.fv( "registration", "password", password )
        tc.fv( "registration", "confirm", password )
        tc.fv( "registration", "username", username )
        if user_type_fd_id:
            # The user_type_fd_id SelectField requires a refresh_on_change
            self.refresh_form( 'user_type_fd_id', user_type_fd_id, form_id='registration' )
            tc.fv( "registration", "password", password )
            tc.fv( "registration", "confirm", password )
            for index, ( field_name, info_value ) in enumerate( user_info_values ):
                tc.fv( "registration", field_name, info_value )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str)
        tc.submit( "create_user_button" )

    def create_group( self, name='Group One', in_user_ids=[], in_role_ids=[], create_role_for_group=False, strings_displayed=[] ):
        """Create a new group"""
        url = "/admin/groups"
        params = dict( operation='create', create_group_button='Save', name=name )
        if in_user_ids:
            params [ 'in_users' ] = ','.join( in_user_ids )
        if in_role_ids:
            params[ 'in_roles' ] = ','.join( in_role_ids )
        if create_role_for_group:
            params[ 'create_role_for_group' ] = [ 'yes', 'yes' ]
            doseq = True
        else:
            params[ 'create_role_for_group' ] = 'no'
            doseq = False
        self.visit_url( url, params=params, doseq=doseq )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        self.visit_url( "/admin/groups" )
        self.check_page_for_string( name )

    def create_form( self, name, description, form_type, field_type='TextField', form_layout_name='',
                     num_fields=1, num_options=0, field_name='1_field_name', strings_displayed=[],
                     strings_displayed_after_submit=[] ):
        """Create a new form definition."""
        self.visit_url( "%s/forms/create_form_definition" % self.url )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        tc.fv( "create_form_definition", "name", name )
        tc.fv( "create_form_definition", "description", description )
        tc.fv( "create_form_definition", "form_type_select_field", form_type )
        tc.submit( "create_form_button" )
        if form_type == "Sequencing Sample Form":
            tc.submit( "add_layout_grid" )
            tc.fv( "edit_form_definition", "grid_layout0", form_layout_name )
        # if not adding any fields at this time, remove the default empty field
        if num_fields == 0:
            tc.submit( "remove_button" )
        # Add fields to the new form definition
        for index1 in range( num_fields ):
            field_label = 'field_label_%i' % index1
            field_contents = field_type
            field_help_name = 'field_helptext_%i' % index1
            field_help_contents = 'Field %i help' % index1
            field_default = 'field_default_0'
            field_default_contents = '%s default contents' % form_type
            tc.fv( "edit_form_definition", field_label, field_contents )
            tc.fv( "edit_form_definition", field_help_name, field_help_contents )
            if field_type == 'SelectField':
                # SelectField field_type requires a refresh_on_change
                self.refresh_form( 'field_type_0', field_type )
                # Add options so our select list is functional
                if num_options == 0:
                    # Default to 2 options
                    num_options = 2
                for index2 in range( 1, num_options + 1 ):
                    tc.submit( "addoption_0" )
                # Add contents to the new options fields
                for index2 in range( num_options ):
                    option_field_name = 'field_0_option_%i' % index2
                    option_field_value = 'Option%i' % index2
                    tc.fv( "edit_form_definition", option_field_name, option_field_value )
            else:
                tc.fv( "edit_form_definition", "field_type_0", field_type )
            tc.fv( "edit_form_definition", 'field_name_0', field_name )
            tc.fv( "edit_form_definition", field_default, field_default_contents )
        # All done... now save
        tc.submit( "save_changes_button" )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )

    def create_external_service( self, name, description, version, external_service_type_id, field_values={}, strings_displayed=[], strings_displayed_after_submit=[] ):
        self.visit_url( '%s/external_service/create_external_service' % self.url )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        tc.fv( "1", "name", name )
        tc.fv( "1", "description", description )
        tc.fv( "1", "version", version )
        self.refresh_form( "external_service_type_id", external_service_type_id )
        for field, value in field_values.items():
            tc.fv( "1", field, value )
        tc.submit( "create_external_service_button" )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )

    def create_new_account_as_admin( self, email='test4@bx.psu.edu', password='testuser',
                                     username='regular-user4', redirect='' ):
        """Create a new account for another user"""
        # HACK: don't use panels because late_javascripts() messes up the twill browser and it
        # can't find form fields (and hence user can't be logged in).
        self.visit_url( "%s/user/create?cntrller=admin" % self.url )
        self.submit_form( 1, 'create_user_button', email=email, redirect=redirect, password=password, confirm=password, username=username )
        previously_created = False
        username_taken = False
        invalid_username = False
        try:
            self.check_page_for_string( "Created new user account" )
        except:
            try:
                # May have created the account in a previous test run...
                self.check_page_for_string( "User with that email already exists" )
                previously_created = True
            except:
                try:
                    self.check_page_for_string( 'Public name is taken; please choose another' )
                    username_taken = True
                except:
                    try:
                        # Note that we're only checking if the usr name is >< 4 chars here...
                        self.check_page_for_string( 'Public name must be at least 4 characters in length' )
                        invalid_username = True
                    except:
                        pass
        return previously_created, username_taken, invalid_username

    def create_request_type( self, name, desc, request_form_id, sample_form_id, states, strings_displayed=[], strings_displayed_after_submit=[] ):
        self.visit_url( "%s/request_type/create_request_type" % self.url )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        tc.fv( "1", "name", name )
        tc.fv( "1", "desc", desc )
        tc.fv( "1", "request_form_id", request_form_id )
        tc.fv( "1", "sample_form_id", sample_form_id )
        for index, state in enumerate(states):
            tc.fv("1", "state_name_%i" % index, state[0])
            tc.fv("1", "state_desc_%i" % index, state[1])
            tc.submit( "add_state_button" )
        tc.submit( "create_request_type_button" )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )

    def create_request( self, cntrller, request_type_id, name, desc, field_value_tuples, other_users_id='',
                        strings_displayed=[], strings_displayed_after_submit=[] ):
        self.visit_url( "%s/requests_common/create_request?cntrller=%s" % ( self.url, cntrller ) )
        # The request_type SelectList requires a refresh_on_change
        self.refresh_form( 'request_type_id', request_type_id )
        if cntrller == 'requests_admin' and other_users_id:
            # The admin is creating a request on behalf of another user
            # The user_id SelectField requires a refresh_on_change so that the selected
            # user's addresses will be populated in the AddressField widget
            self.refresh_form( "user_id", other_users_id )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        tc.fv( "1", "name", name )
        tc.fv( "1", "desc", desc )
        for index, field_value_tuple in enumerate( field_value_tuples ):
            field_index = index + 1
            field_name, field_value, refresh_on_change = field_value_tuple
            if refresh_on_change:
                # Only the AddressField type has a refresh on change setup on selecting an option
                address_option = field_value[0]
                address_value = field_value[1]
                self.refresh_form( field_name, address_option )
                if address_option == 'new':
                    # handle new address
                    self.check_page_for_string( 'Short address description' )
                    for address_field, value in address_value.items():
                        tc.fv( "1", field_name+'_'+address_field, value )
                else:
                    # existing address
                    tc.fv( "1", field_name, address_value )
            else:
                tc.fv( "1", field_name, field_value )
        tc.submit( "create_request_button" )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )

    def create_role( self,
                     name='Role One',
                     description="This is Role One",
                     in_user_ids=[],
                     in_group_ids=[],
                     create_group_for_role='',
                     private_role='',
                     strings_displayed=[] ):
        """Create a new role"""
        url = "/admin/roles"
        url_params = dict( operation='create', create_role_button='Save', name=name, description=description )
        if in_user_ids:
            url_params[ 'in_users' ] = ','.join( in_user_ids )
        if in_group_ids:
            url_params[ 'in_groups' ] = ','.join( in_group_ids )
        if create_group_for_role == 'yes':
            url_params[ 'create_group_for_role' ] = [ 'yes', 'yes' ]
            doseq = True
        else:
            doseq=False
        self.visit_url( url, params=url_params, doseq=doseq )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        if private_role:
            # Make sure no private roles are displayed
            try:
                self.check_page_for_string( private_role )
                errmsg = 'Private role %s displayed on Roles page' % private_role
                raise AssertionError( errmsg )
            except AssertionError:
                # Reaching here is the behavior we want since no private roles should be displayed
                pass
        self.visit_url( "%s/admin/roles" % self.url )
        self.check_page_for_string( name )

    def delete_current_history( self, strings_displayed=[] ):
        """Deletes the current history"""
        self.visit_url( "/history/delete_current" )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )

    def delete_history( self, id ):
        """Deletes one or more histories"""
        history_ids = self.get_all_history_ids_from_api()
        self.assertTrue( history_ids )
        num_deleted = len( id.split( ',' ) )
        self.visit_url( "/history/list?operation=delete&id=%s" % ( id ) )
        check_str = 'Deleted %d %s' % ( num_deleted, iff( num_deleted != 1, "histories", "history" ) )
        self.check_page_for_string( check_str )

    def delete_history_item( self, hda_id, strings_displayed=[] ):
        """Deletes an item from a history"""
        try:
            hda_id = int( hda_id )
        except:
            raise AssertionError( "Invalid hda_id '%s' - must be int" % hda_id )
        self.visit_url( "%s/datasets/%s/delete?show_deleted_on_refresh=False" % ( self.url, self.security.encode_id( hda_id ) ) )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )

    def delete_library_item( self, cntrller, library_id, item_id, item_name, item_type='library_dataset' ):
        """Mark a library item as deleted"""
        params = dict( cntrller=cntrller, library_id=library_id, item_id=item_id, item_type=item_type )
        self.visit_url( "/library_common/delete_library_item", params )
        if item_type == 'library_dataset':
            item_desc = 'Dataset'
        else:
            item_desc = item_type.capitalize()
        check_str = "marked deleted"
        self.check_for_strings( strings_displayed=[ item_desc, check_str ] )

    def delete_sample_datasets( self, sample_id, sample_dataset_ids, strings_displayed=[], strings_displayed_after_submit=[], strings_not_displayed=[] ):
        url = '%s/requests_admin/manage_datasets?cntrller=requests_admin&sample_id=%s' % ( self.url, sample_id )
        self.visit_url( url )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        # simulate selecting datasets and clicking the delete button on the sample datasets grid
        sample_dataset_ids_string = ','.join( sample_dataset_ids )
        params = dict( operation='delete', id=sample_dataset_ids_string )
        url = "/requests_admin/manage_datasets"
        self.visit_url( url, params )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )
        for check_str in strings_not_displayed:
            self.check_string_not_in_page( check_str )

    def disable_access_via_link( self, history_id, strings_displayed=[], strings_displayed_after_submit=[] ):
        # twill barfs on this form, possibly because it contains no fields, but not sure.
        # In any case, we have to mimic the form submission
        self.visit_url( '/history/sharing', dict( id=history_id, disable_link_access=True ) )
        self.check_for_strings( strings_displayed=strings_displayed_after_submit )

    def display_history_item( self, hda_id, strings_displayed=[] ):
        """Displays a history item - simulates eye icon click"""
        self.visit_url( '%s/datasets/%s/display/' % ( self.url, self.security.encode_id( hda_id ) ) )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )

    def download_archive_of_library_files( self, cntrller, library_id, ldda_ids, format ):
        # Here it would be ideal to have twill set form values and submit the form, but
        # twill barfs on that due to the recently introduced page wrappers around the contents
        # of the browse_library.mako template which enable panel layout when visiting the
        # page from an external URL.  By "barfs", I mean that twill somehow loses hod on the
        # cntrller param.  We'll just simulate the form submission by building the URL manually.
        # Here's the old, better approach...
        #self.visit_url( "%s/library_common/browse_library?cntrller=%s&id=%s" % ( self.url, cntrller, library_id ) )
        #for ldda_id in ldda_ids:
        #    tc.fv( "1", "ldda_ids", ldda_id )
        #tc.fv( "1", "do_action", format )
        #tc.submit( "action_on_datasets_button" )
        # Here's the new approach...
        params = dict( cntrller=cntrller, library_id=library_id, do_action=format, ldda_ids=ldda_ids )
        url = "/library_common/act_on_multiple_datasets"
        self.visit_url( url, params, doseq=True )
        tc.code( 200 )
        archive = self.write_temp_file( self.last_page(), suffix='.' + format )
        return archive

    def edit_basic_request_info( self, cntrller, request_id, name, new_name='', new_desc='', new_fields=[],
                                 strings_displayed=[], strings_displayed_after_submit=[] ):
        params = dict( cntrller=cntrller, id=request_id )
        self.visit_url( "/requests_common/edit_basic_request_info", params )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        if new_name:
            tc.fv( "1", "name", new_name )
        if new_desc:
            tc.fv( "1", "desc", new_desc )
        for index, ( field_name, field_value ) in enumerate( new_fields ):
            field_name_index = index + 1
            tc.fv( "1", field_name, field_value )
        tc.submit( "edit_basic_request_info_button" )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )

    def edit_external_service( self, external_service_id, field_values={}, strings_displayed=[], strings_displayed_after_submit=[] ):
        self.visit_url( '%s/external_service/edit_external_service?id=%s' % ( self.url, external_service_id ) )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        for field, value in field_values.items():
            tc.fv( "1", field, value )
        tc.submit( "edit_external_service_button" )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )

    def edit_form( self, id, form_type='', new_form_name='', new_form_desc='', field_dicts=[], field_index=0,
                   strings_displayed=[], strings_not_displayed=[], strings_displayed_after_submit=[] ):
        """Edit form details; name and description"""
        self.visit_url( "/forms/edit_form_definition", params=dict( id=id ) )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        if new_form_name:
            tc.fv( "edit_form_definition", "name", new_form_name )
        if new_form_desc:
            tc.fv( "edit_form_definition", "description", new_form_desc )
        for i, field_dict in enumerate( field_dicts ):
            index = i + field_index
            tc.submit( "add_field_button" )
            field_label = "field_label_%i" % index
            field_label_value = field_dict[ 'label' ]
            field_help = "field_helptext_%i" % index
            field_help_value = field_dict[ 'desc' ]
            field_type = "field_type_%i" % index
            field_type_value = field_dict[ 'type' ]
            field_required = "field_required_%i" % index
            field_required_value = field_dict[ 'required' ]
            field_name = "field_name_%i" % index
            field_name_value = field_dict.get( 'name', '%i_field_name' % index )
            tc.fv( "edit_form_definition", field_label, field_label_value )
            tc.fv( "edit_form_definition", field_help, field_help_value )
            tc.fv( "edit_form_definition", field_required, field_required_value )
            tc.fv( "edit_form_definition", field_name, field_name_value )
            if field_type_value.lower() == 'selectfield':
                # SelectFields require a refresh_on_change
                self.refresh_form( field_type, field_type_value )
                for option_index, option in enumerate( field_dict[ 'selectlist' ] ):
                    tc.submit( "addoption_%i" % index )
                    tc.fv( "edit_form_definition", "field_%i_option_%i" % ( index, option_index ), option )
            else:
                tc.fv( "edit_form_definition", field_type, field_type_value )
        tc.submit( "save_changes_button" )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )

    def edit_hda_attribute_info( self, hda_id, new_name='', new_info='', new_dbkey='', new_startcol='',
                                 strings_displayed=[], strings_not_displayed=[] ):
        """Edit history_dataset_association attribute information"""
        self.visit_url( "/datasets/%s/edit" % self.security.encode_id( hda_id ) )
        submit_required = False
        self.check_page_for_string( 'Edit Attributes' )
        if new_name:
            tc.fv( 'edit_attributes', 'name', new_name )
            submit_required = True
        if new_info:
            tc.fv( 'edit_attributes', 'info', new_info )
            submit_required = True
        if new_dbkey:
            tc.fv( 'edit_attributes', 'dbkey', new_dbkey )
            submit_required = True
        if new_startcol:
            tc.fv( 'edit_attributes', 'startCol', new_startcol )
            submit_required = True
        if submit_required:
            tc.submit( 'save' )
            self.check_page_for_string( 'Attributes updated' )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        for check_str in strings_not_displayed:
            try:
                self.check_page_for_string( check_str )
                raise AssertionError( "String (%s) incorrectly displayed on Edit Attributes page." % check_str )
            except:
                pass

    def edit_request_email_settings( self, cntrller, request_id, check_request_owner=True, additional_emails='',
                                     check_sample_states=[], strings_displayed=[], strings_displayed_after_submit=[] ):
        self.visit_url( "/requests_common/edit_basic_request_info", params=dict( cntrller=cntrller, id=request_id ) )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        tc.fv( "2", "email_address", check_request_owner )
        tc.fv( "2", "additional_email_addresses", additional_emails )
        for state_name, state_id, is_checked in check_sample_states:
            tc.fv( "2", "sample_state_%i" % state_id, is_checked )
        tc.submit( "edit_email_settings_button" )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )

    def edit_samples( self, cntrller, request_id, sample_value_tuples, strings_displayed=[], strings_displayed_after_submit=[] ):
        params = dict( cntrller=cntrller, id=request_id )
        url = "/requests_common/edit_samples"
        self.visit_url( url, params=params )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        for sample_index, ( sample_name, target_library_info, sample_field_values ) in enumerate( sample_value_tuples ):
            tc.fv( "1", "sample_%i_name" % sample_index, sample_name )
            tc.fv( "1", "sample_%i_library_id" % sample_index, target_library_info[ 'library' ] )
            self.refresh_form( "sample_%i_library_id" % sample_index, target_library_info[ 'library' ] )
            tc.fv( "1", "sample_%i_folder_id" % sample_index, target_library_info[ 'folder' ] )
            for field_index, field_value in enumerate( sample_field_values ):
                tc.fv( "1", "sample_%i_field_%i" % ( sample_index, field_index ), field_value )
        tc.submit( "save_samples_button" )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )

    def edit_template( self, cntrller, item_type, form_type, library_id, field_type, field_label_1, field_helptext_1, field_default_1,
                       folder_id='', ldda_id='', action='add_field'  ):
        """Edit the form fields defining a library template"""
        params = dict( cntrller=cntrller, item_type=item_type, form_type=form_type, library_id=library_id )
        self.visit_url( "/library_common/edit_template", params=params )
        self.check_page_for_string( "Edit form definition" )
        if action == 'add_field':
            tc.submit( "add_field_button" )
            tc.fv( "edit_form", "field_label_1", field_label_1 )
            tc.fv( "edit_form", "field_helptext_1", field_helptext_1 )
            if field_type == 'SelectField':
                # Performs a refresh_on_change in this case
                self.refresh_form( "field_type_1", field_type )
            else:
                tc.fv( "edit_form", "field_type_1", field_type )
            tc.fv( "edit_form", "field_default_1", field_default_1 )
        tc.submit( 'save_changes_button' )
        self.check_page_for_string( "The template for this data library has been updated with your changes." )

    def edit_user_info( self, cntrller='user', id='', new_email='', new_username='', password='', new_password='',
                        info_values=[], strings_displayed=[], strings_displayed_after_submit=[] ):
        if cntrller == 'admin':
            url = "%s/admin/users?id=%s&operation=information" % ( self.url, id )
        else:  # cntrller == 'user:
            # The user is editing his own info, so the user id is gotten from trans.user.
            url = "%s/user/manage_user_info?cntrller=user" % self.url
        self.visit_url( url )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        if new_email or new_username:
            if new_email:
                tc.fv( "login_info", "email", new_email )
            if new_username:
                tc.fv( "login_info", "username", new_username )
            tc.submit( "login_info_button" )
        if password and new_password:
            tc.fv( "change_password", "current", password )
            tc.fv( "change_password", "password", new_password )
            tc.fv( "change_password", "confirm", new_password )
            tc.submit( "change_password_button" )
        if info_values:
            for index, ( field_name, info_value ) in enumerate( info_values ):
                tc.fv( "user_info", field_name, info_value )
            tc.submit( "edit_user_info_button" )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )

    def files_diff( self, file1, file2, attributes=None ):
        """Checks the contents of 2 files for differences"""
        def get_lines_diff( diff ):
            count = 0
            for line in diff:
                if ( line.startswith( '+' ) and not line.startswith( '+++' ) ) or ( line.startswith( '-' ) and not line.startswith( '---' ) ):
                    count += 1
            return count
        if not filecmp.cmp( file1, file2 ):
            files_differ = False
            local_file = open( file1, 'U' ).readlines()
            history_data = open( file2, 'U' ).readlines()
            if attributes is None:
                attributes = {}
            if attributes.get( 'sort', False ):
                history_data.sort()
            ##Why even bother with the check loop below, why not just use the diff output? This seems wasteful.
            if len( local_file ) == len( history_data ):
                for i in range( len( history_data ) ):
                    if local_file[i].rstrip( '\r\n' ) != history_data[i].rstrip( '\r\n' ):
                        files_differ = True
                        break
            else:
                files_differ = True
            if files_differ:
                allowed_diff_count = int(attributes.get( 'lines_diff', 0 ))
                diff = list( difflib.unified_diff( local_file, history_data, "local_file", "history_data" ) )
                diff_lines = get_lines_diff( diff )
                if diff_lines > allowed_diff_count:
                    if len(diff) < 60:
                        diff_slice = diff[0:40]
                    else:
                        diff_slice = diff[:25] + ["********\n", "*SNIP *\n", "********\n"] + diff[-25:]
                    #FIXME: This pdf stuff is rather special cased and has not been updated to consider lines_diff
                    #due to unknown desired behavior when used in conjunction with a non-zero lines_diff
                    #PDF forgiveness can probably be handled better by not special casing by __extension__ here
                    #and instead using lines_diff or a regular expression matching
                    #or by creating and using a specialized pdf comparison function
                    if file1.endswith( '.pdf' ) or file2.endswith( '.pdf' ):
                        # PDF files contain creation dates, modification dates, ids and descriptions that change with each
                        # new file, so we need to handle these differences.  As long as the rest of the PDF file does
                        # not differ we're ok.
                        valid_diff_strs = [ 'description', 'createdate', 'creationdate', 'moddate', 'id', 'producer', 'creator' ]
                        valid_diff = False
                        invalid_diff_lines = 0
                        for line in diff_slice:
                            # Make sure to lower case strings before checking.
                            line = line.lower()
                            # Diff lines will always start with a + or - character, but handle special cases: '--- local_file \n', '+++ history_data \n'
                            if ( line.startswith( '+' ) or line.startswith( '-' ) ) and line.find( 'local_file' ) < 0 and line.find( 'history_data' ) < 0:
                                for vdf in valid_diff_strs:
                                    if line.find( vdf ) < 0:
                                        valid_diff = False
                                    else:
                                        valid_diff = True
                                        # Stop checking as soon as we know we have a valid difference
                                        break
                                if not valid_diff:
                                    invalid_diff_lines += 1
                        log.info('## files diff on %s and %s lines_diff=%d, found diff = %d, found pdf invalid diff = %d' % (file1, file2, allowed_diff_count, diff_lines, invalid_diff_lines))
                        if invalid_diff_lines > allowed_diff_count:
                            # Print out diff_slice so we can see what failed
                            print "###### diff_slice ######"
                            raise AssertionError( "".join( diff_slice ) )
                    else:
                        log.info('## files diff on %s and %s lines_diff=%d, found diff = %d' % (file1, file2, allowed_diff_count, diff_lines))
                        for line in diff_slice:
                            for char in line:
                                if ord( char ) > 128:
                                    raise AssertionError( "Binary data detected, not displaying diff" )
                        raise AssertionError( "".join( diff_slice )  )

    def files_re_match( self, file1, file2, attributes=None ):
        """Checks the contents of 2 files for differences using re.match"""
        local_file = open( file1, 'U' ).readlines()  # regex file
        history_data = open( file2, 'U' ).readlines()
        assert len( local_file ) == len( history_data ), 'Data File and Regular Expression File contain a different number of lines (%s != %s)\nHistory Data (first 40 lines):\n%s' % ( len( local_file ), len( history_data ), ''.join( history_data[:40] ) )
        if attributes is None:
            attributes = {}
        if attributes.get( 'sort', False ):
            history_data.sort()
        lines_diff = int(attributes.get( 'lines_diff', 0 ))
        line_diff_count = 0
        diffs = []
        for i in range( len( history_data ) ):
            if not re.match( local_file[i].rstrip( '\r\n' ), history_data[i].rstrip( '\r\n' ) ):
                line_diff_count += 1
                diffs.append( 'Regular Expression: %s\nData file         : %s' % ( local_file[i].rstrip( '\r\n' ),  history_data[i].rstrip( '\r\n' ) ) )
            if line_diff_count > lines_diff:
                raise AssertionError( "Regular expression did not match data file (allowed variants=%i):\n%s" % ( lines_diff, "".join( diffs ) ) )

    def files_re_match_multiline( self, file1, file2, attributes=None ):
        """Checks the contents of 2 files for differences using re.match in multiline mode"""
        local_file = open( file1, 'U' ).read()  # regex file
        if attributes is None:
            attributes = {}
        if attributes.get( 'sort', False ):
            history_data = open( file2, 'U' ).readlines()
            history_data.sort()
            history_data = ''.join( history_data )
        else:
            history_data = open( file2, 'U' ).read()
        #lines_diff not applicable to multiline matching
        assert re.match( local_file, history_data, re.MULTILINE ), "Multiline Regular expression did not match data file"

    def files_contains( self, file1, file2, attributes=None ):
        """Checks the contents of file2 for substrings found in file1, on a per-line basis"""
        local_file = open( file1, 'U' ).readlines()  # regex file
        #TODO: allow forcing ordering of contains
        history_data = open( file2, 'U' ).read()
        lines_diff = int( attributes.get( 'lines_diff', 0 ) )
        line_diff_count = 0
        while local_file:
            contains = local_file.pop( 0 ).rstrip( '\n\r' )
            if contains not in history_data:
                line_diff_count += 1
            if line_diff_count > lines_diff:
                raise AssertionError( "Failed to find '%s' in history data. (lines_diff=%i):\n" % ( contains, lines_diff ) )

    def find_hda_by_dataset_name( self, name, history=None ):
        if history is None:
            history = self.get_history_from_api()
        for hda in history:
            if hda[ 'name' ] == name:
                return hda

    def folder_info( self, cntrller, folder_id, library_id, name='', new_name='', description='', template_refresh_field_name='1_field_name',
                     template_refresh_field_contents='', template_fields=[], strings_displayed=[], strings_not_displayed=[],
                     strings_displayed_after_submit=[], strings_not_displayed_after_submit=[] ):
        """Add information to a library using an existing template with 2 elements"""
        self.visit_url( "%s/library_common/folder_info?cntrller=%s&id=%s&library_id=%s" % \
                        ( self.url, cntrller, folder_id, library_id ) )
        if name and new_name and description:
            tc.fv( '1', "name", new_name )
            tc.fv( '1', "description", description )
            tc.submit( 'rename_folder_button' )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        for check_str in strings_not_displayed:
            try:
                self.check_page_for_string( check_str )
                raise AssertionError( "String (%s) incorrectly displayed." % check_str )
            except:
                pass
        if template_refresh_field_contents:
            # A template containing an AddressField is displayed on the form, so we need to refresh the form
            # with the received template_refresh_field_contents.  There are 2 forms on the folder_info page
            # when in edit mode, and the 2nd one is the one we want.
            self.refresh_form( template_refresh_field_name, template_refresh_field_contents, form_no=2 )
        if template_fields:
            # We have an information template associated with the folder, so
            # there are 2 forms on this page and the template is the 2nd form
            for field_name, field_value in template_fields:
                tc.fv( "edit_info", field_name, field_value )
            tc.submit( 'edit_info_button' )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )
        for check_str in strings_not_displayed_after_submit:
            try:
                self.check_page_for_string( check_str )
                raise AssertionError( "String (%s) incorrectly displayed." % check_str )
            except:
                pass

    def get_all_history_ids_from_api( self ):
        return [ history['id'] for history in self.json_from_url( '/api/histories' ) ]

    def get_filename( self, filename, shed_tool_id=None ):
        if shed_tool_id and self.shed_tools_dict:
            file_dir = self.shed_tools_dict[ shed_tool_id ]
            if not file_dir:
                file_dir = self.file_dir
        else:
            file_dir = self.file_dir
        return os.path.abspath( os.path.join( file_dir, filename ) )

    def get_form_controls( self, form ):
        formcontrols = []
        for i, control in enumerate( form.controls ):
            formcontrols.append( "control %d: %s" % ( i, str( control ) ) )
        return formcontrols

    def get_hids_in_history( self, history_id ):
        """Returns the list of hid values for items in a history"""
        hids = []
        api_url = '/api/histories/%s/contents' % history_id
        hids = [ history_item[ 'hid' ] for history_item in self.json_from_url( api_url ) ]
        return hids

    def get_hids_in_histories( self ):
        """Returns the list of hids values for items in all histories"""
        history_ids = self.get_all_history_ids_from_api()
        hids = []
        for history_id in history_ids:
            hids.extend( self.get_hids_in_history( history_id ) )
        return hids

    def get_history_as_data_list( self, show_deleted=False ):
        """Returns the data elements of a history"""
        tree = self.history_as_xml_tree( show_deleted=show_deleted )
        data_list = [ elem for elem in tree.findall("data") ]
        return data_list

    def get_history_from_api( self, encoded_history_id=None, show_deleted=None, show_details=False ):
        if encoded_history_id is None:
            history = self.get_latest_history()
            encoded_history_id = history[ 'id' ]
        params = dict()
        if show_deleted is not None:
            params[ 'deleted' ] = show_deleted
        api_url = '/api/histories/%s/contents' % encoded_history_id
        json_data = self.json_from_url( api_url, params=params )
        if show_deleted is not None:
            hdas = []
            for hda in json_data:
                if show_deleted:
                    hdas.append( hda )
                else:
                    if not hda[ 'deleted' ]:
                        hdas.append( hda )
            json_data = hdas
        if show_details:
            params[ 'details' ] = ','.join( [ hda[ 'id' ] for hda in json_data ] )
            api_url = '/api/histories/%s/contents' % encoded_history_id
            json_data = self.json_from_url( api_url, params=params )
        return json_data

    def get_job_stdout( self, hda_id, format=False ):
        return self._get_job_stream_output( hda_id, 'stdout', format )

    def get_job_stderr( self, hda_id, format=False ):
        return self._get_job_stream_output( hda_id, 'stderr', format )

    def get_latest_history( self ):
        return self.json_from_url( '/api/histories' )[ 0 ]

    def get_running_datasets( self ):
        self.visit_url( '/api/histories' )
        history_id = loads( self.last_page() )[0][ 'id' ]
        self.visit_url( '/api/histories/%s/contents' % history_id )
        jsondata = loads( self.last_page() )
        for history_item in jsondata:
            self.visit_url( history_item[ 'url' ] )
            item_json = loads( self.last_page() )
            if item_json[ 'state' ] in [ 'queued', 'running', 'paused' ]:
                return True
        return False

    def get_tags( self, item_id, item_class ):
        self.visit_url( "%s/tag/get_tagging_elt_async?item_id=%s&item_class=%s" % \
                        ( self.url, item_id, item_class ) )

    def history_as_xml_tree( self, show_deleted=False ):
        """Returns a parsed xml object of a history"""
        self.visit_url( '/history?as_xml=True&show_deleted=%s' % show_deleted )
        xml = self.last_page()
        tree = ElementTree.fromstring(xml)
        return tree

    def history_set_default_permissions( self, permissions_out=[], permissions_in=[], role_id=3 ):  # role.id = 3 is Private Role for test3@bx.psu.edu
        # NOTE: Twill has a bug that requires the ~/user/permissions page to contain at least 1 option value
        # in each select list or twill throws an exception, which is: ParseError: OPTION outside of SELECT
        # Due to this bug, we'll bypass visiting the page, and simply pass the permissions on to the
        # /user/set_default_permissions method.
        url = "root/history_set_default_permissions?update_roles_button=Save&id=None&dataset=True"
        for po in permissions_out:
            key = '%s_out' % po
            url = "%s&%s=%s" % ( url, key, str( role_id ) )
        for pi in permissions_in:
            key = '%s_in' % pi
            url = "%s&%s=%s" % ( url, key, str( role_id ) )
        self.visit_url( "%s/%s" % ( self.url, url ) )
        self.check_page_for_string( 'Default history permissions have been changed.' )

    def histories_as_xml_tree( self ):
        """Returns a parsed xml object of all histories"""
        self.visit_url( '/history/list_as_xml' )
        xml = self.last_page()
        tree = ElementTree.fromstring(xml)
        return tree

    def history_options( self, user=False, active_datasets=False, activatable_datasets=False, histories_shared_by_others=False ):
        """Mimics user clicking on history options link"""
        self.visit_url( "/root/history_options" )
        if user:
            self.check_page_for_string( 'Previously</a> stored histories' )
            if active_datasets:
                self.check_page_for_string( 'Create</a> a new empty history' )
                self.check_page_for_string( 'Construct workflow</a> from current history' )
                self.check_page_for_string( 'Copy</a> current history' )
            self.check_page_for_string( 'Share</a> current history' )
            self.check_page_for_string( 'Change default permissions</a> for current history' )
            if histories_shared_by_others:
                self.check_page_for_string( 'Histories</a> shared with you by others' )
        if activatable_datasets:
            self.check_page_for_string( 'Show deleted</a> datasets in current history' )
        self.check_page_for_string( 'Rename</a> current history' )
        self.check_page_for_string( 'Delete</a> current history' )

    def import_datasets_to_histories( self, cntrller, library_id, ldda_ids='', new_history_name='Unnamed history', strings_displayed=[] ):
        # Can't use the ~/library_admin/libraries form as twill barfs on it so we'll simulate the form submission
        # by going directly to the form action
        self.visit_url( '%s/library_common/import_datasets_to_histories?cntrller=%s&library_id=%s&ldda_ids=%s&new_history_name=%s&import_datasets_to_histories_button=Import+library+datasets' \
                        % ( self.url, cntrller, library_id, ldda_ids, new_history_name ) )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )

    def import_history_via_url( self, history_id, email, strings_displayed_after_submit=[] ):
        self.visit_url( "/history/imp", params=dict( id=history_id ) )
        self.check_for_strings( strings_displayed=strings_displayed_after_submit )

    def is_binary( self, filename ):
        temp = open( filename, "U" )
        lineno = 0
        for line in temp:
            lineno += 1
            line = line.strip()
            if line:
                for char in line:
                    if ord( char ) > 128:
                        return True
            if lineno > 10:
                break
        return False

    def is_history_empty( self ):
        """
        Uses history page JSON to determine whether this history is empty
        (i.e. has no undeleted datasets).
        """
        return len( self.get_history_from_api() ) == 0

    def is_zipped( self, filename ):
        if not zipfile.is_zipfile( filename ):
            return False
        return True

    def json_from_url( self, url, params={} ):
        self.visit_url( url, params )
        return loads( self.last_page() )

    def last_page( self ):
        return tc.browser.get_html()

    def last_url( self ):
        return tc.browser.get_url()

    def ldda_permissions( self, cntrller, library_id, folder_id, id, role_ids_str,
                          permissions_in=[], permissions_out=[], strings_displayed=[], ldda_name='' ):
        # role_ids_str must be a comma-separated string of role ids
        params = dict( cntrller=cntrller, library_id=library_id, folder_id=folder_id, id=id )
        url = "/library_common/ldda_permissions"
        for po in permissions_out:
            params[ '%s_out' % po ] = role_ids_str
        for pi in permissions_in:
            params[ '%s_in' % pi ] = role_ids_str
        if permissions_in or permissions_out:
            params[ 'update_roles_button' ] = 'Save'
            self.visit_url( url, params )
        if not strings_displayed:
            strings_displayed = [ "Permissions updated for dataset '%s'." % ldda_name ]
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )

    def ldda_info( self, cntrller, library_id, folder_id, ldda_id, strings_displayed=[], strings_not_displayed=[] ):
        """View library_dataset_dataset_association information"""
        self.visit_url( "%s/library_common/ldda_info?cntrller=%s&library_id=%s&folder_id=%s&id=%s" % \
                        ( self.url, cntrller, library_id, folder_id, ldda_id ) )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        for check_str in strings_not_displayed:
            try:
                self.check_page_for_string( check_str )
                raise AssertionError( "String (%s) should not have been displayed on ldda info page." % check_str )
            except:
                pass

    def ldda_edit_info( self, cntrller, library_id, folder_id, ldda_id, ldda_name, new_ldda_name='', template_refresh_field_name='1_field_name',
                        template_refresh_field_contents='', template_fields=[], strings_displayed=[], strings_not_displayed=[] ):
        """Edit library_dataset_dataset_association information, optionally template element information"""
        self.visit_url( "%s/library_common/ldda_edit_info?cntrller=%s&library_id=%s&folder_id=%s&id=%s" % \
                        ( self.url, cntrller, library_id, folder_id, ldda_id ) )
        check_str = 'Edit attributes of %s' % ldda_name
        self.check_page_for_string( check_str )
        if new_ldda_name:
            tc.fv( '1', 'name', new_ldda_name )
            tc.submit( 'save' )
            check_str = "Attributes updated for library dataset '%s'." % new_ldda_name
            self.check_page_for_string( check_str )
        if template_refresh_field_contents:
            # A template containing an AddressField is displayed on the upload form, so we need to refresh the form
            # with the received template_refresh_field_contents.  There are 4 forms on this page, and the template is
            # contained in the 4th form named "edit_info".
            self.refresh_form( template_refresh_field_name, template_refresh_field_contents, form_no=4 )
        if template_fields:
            # We have an information template associated with the folder, so
            # there are 2 forms on this page and the template is the 2nd form
            for field_name, field_value in template_fields:
                tc.fv( "edit_info", field_name, field_value )
            tc.submit( 'edit_info_button' )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        for check_str in strings_not_displayed:
            try:
                self.check_page_for_string( check_str )
                raise AssertionError( "String (%s) should not have been displayed on ldda Edit Attributes page." % check_str )
            except:
                pass

    def library_info( self, cntrller, library_id, library_name='', new_name='', new_description='', new_synopsis='',
                      template_fields=[], strings_displayed=[] ):
        """Edit information about a library, optionally using an existing template with up to 2 elements"""
        self.visit_url( "%s/library_common/library_info?cntrller=%s&id=%s" % ( self.url, cntrller, library_id ) )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        if new_name and new_description and new_synopsis:
            tc.fv( '1', 'name', new_name )
            tc.fv( '1', 'description', new_description )
            tc.fv( '1', 'synopsis', new_synopsis )
            tc.submit( 'library_info_button' )
            self.check_page_for_string( "Information updated for library" )
        if template_fields:
            for field_name, field_value in template_fields:
                # The 2nd form on the page contains the template, and the form is named edit_info.
                # Set the template field value
                tc.fv( "edit_info", field_name, field_value )
            tc.submit( 'edit_info_button' )

    def library_permissions( self, library_id, library_name, role_ids_str, permissions_in, permissions_out, cntrller='library_admin' ):
        # role_ids_str must be a comma-separated string of role ids
        url = "library_common/library_permissions?id=%s&cntrller=%s&update_roles_button=Save" % ( library_id, cntrller )
        for po in permissions_out:
            key = '%s_out' % po
            url = "%s&%s=%s" % ( url, key, role_ids_str )
        for pi in permissions_in:
            key = '%s_in' % pi
            url = "%s&%s=%s" % ( url, key, role_ids_str )
        self.visit_url( "%s/%s" % ( self.url, url ) )
        check_str = "Permissions updated for library '%s'." % library_name
        self.check_page_for_string( check_str )

    def library_wait( self, library_id, cntrller='library_admin', maxiter=90 ):
        """Waits for the tools to finish"""
        count = 0
        sleep_amount = 1
        while count < maxiter:
            count += 1
            self.visit_url( "%s/library_common/browse_library?cntrller=%s&id=%s" % ( self.url, cntrller, library_id ) )
            page = tc.browser.get_html()
            if page.find( '<!-- running: do not change this comment, used by TwillTestCase.library_wait -->' ) > -1:
                time.sleep( sleep_amount )
                sleep_amount += 1
            else:
                break
        self.assertNotEqual(count, maxiter)

    def load_cookies( self, file, shed_tool_id=None ):
        filename = self.get_filename( file, shed_tool_id=shed_tool_id )
        tc.load_cookies(filename)

    def login( self, email='test@bx.psu.edu', password='testuser', username='admin-user', redirect='' ):
        # test@bx.psu.edu is configured as an admin user
        previously_created, username_taken, invalid_username = \
            self.create( email=email, password=password, username=username, redirect=redirect )
        if previously_created:
            # The acount has previously been created, so just login.
            # HACK: don't use panels because late_javascripts() messes up the twill browser and it
            # can't find form fields (and hence user can't be logged in).
            self.visit_url( "/user/login?use_panels=False" )
            self.submit_form( 'login', 'login_button', email=email, redirect=redirect, password=password )

    def logout( self ):
        self.visit_url( "%s/user/logout" % self.url )
        self.check_page_for_string( "You have been logged out" )

    def make_accessible_via_link( self, history_id, strings_displayed=[], strings_displayed_after_submit=[] ):
        # twill barfs on this form, possibly because it contains no fields, but not sure.
        # In any case, we have to mimic the form submission
        self.visit_url( '/history/sharing', dict( id=history_id, make_accessible_via_link=True ) )
        self.check_for_strings( strings_displayed=strings_displayed_after_submit )

    def make_library_item_public( self, library_id, id, cntrller='library_admin', item_type='library',
                                  contents=False, library_name='', folder_name='', ldda_name='' ):
        url = "%s/library_common/make_library_item_public?cntrller=%s&library_id=%s&item_type=%s&id=%s&contents=%s" % \
            ( self.url, cntrller, library_id, item_type, id, str( contents ) )
        self.visit_url( url )
        if item_type == 'library':
            if contents:
                check_str = "The data library (%s) and all its contents have been made publicly accessible." % library_name
            else:
                check_str = "The data library (%s) has been made publicly accessible, but access to its contents has been left unchanged." % library_name
        elif item_type == 'folder':
            check_str = "All of the contents of folder (%s) have been made publicly accessible." % folder_name
        elif item_type == 'ldda':
            check_str = "The libary dataset (%s) has been made publicly accessible." % ldda_name
        self.check_page_for_string( check_str )

    def makeTfname(self, fname=None):
        """safe temp name - preserve the file extension for tools that interpret it"""
        suffix = os.path.split(fname)[-1]  # ignore full path
        fd, temp_prefix = tempfile.mkstemp(prefix='tmp', suffix=suffix)
        return temp_prefix

    def manage_library_template_inheritance( self, cntrller, item_type, library_id, folder_id=None, ldda_id=None, inheritable=True ):
        # If inheritable is True, the item is currently inheritable.
        if item_type == 'library':
            url = "%s/library_common/manage_template_inheritance?cntrller=%s&item_type=%s&library_id=%s" % \
            ( self.url, cntrller, item_type, library_id )
        elif item_type == 'folder':
            url = "%s/library_common/manage_template_inheritance?cntrller=%s&item_type=%s&library_id=%s&folder_id=%s" % \
            ( self.url, cntrller, item_type, library_id, folder_id )
        elif item_type == 'ldda':
            url = "%s/library_common/manage_template_inheritance?cntrller=%s&item_type=%s&library_id=%s&folder_id=%s&ldda_id=%s" % \
            ( self.url, cntrller, item_type, library_id, folder_id, ldda_id )
        self.visit_url( url )
        if inheritable:
            self.check_page_for_string = 'will no longer be inherited to contained folders and datasets'
        else:
            self.check_page_for_string = 'will now be inherited to contained folders and datasets'

    def manage_roles_and_groups_for_user( self, user_id, in_role_ids=[], out_role_ids=[],
                                          in_group_ids=[], out_group_ids=[], strings_displayed=[] ):
        url = "%s/admin/manage_roles_and_groups_for_user?id=%s" % ( self.url, user_id )
        if in_role_ids:
            url += "&in_roles=%s" % ','.join( in_role_ids )
        if out_role_ids:
            url += "&out_roles=%s" % ','.join( out_role_ids )
        if in_group_ids:
            url += "&in_groups=%s" % ','.join( in_group_ids )
        if out_group_ids:
            url += "&out_groups=%s" % ','.join( out_group_ids )
        if in_role_ids or out_role_ids or in_group_ids or out_group_ids:
            url += "&user_roles_groups_edit_button=Save"
        self.visit_url( url )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )

    def mark_form_deleted( self, form_id ):
        """Mark a form_definition as deleted"""
        url = "%s/forms/delete_form_definition?id=%s" % ( self.url, form_id )
        self.visit_url( url )
        check_str = "1 forms have been deleted."
        self.check_page_for_string( check_str )

    def mark_group_deleted( self, group_id, group_name ):
        """Mark a group as deleted"""
        self.visit_url( "%s/admin/groups?operation=delete&id=%s" % ( self.url, group_id ) )
        check_str = "Deleted 1 groups:  %s" % group_name
        self.check_page_for_string( check_str )

    def mark_role_deleted( self, role_id, role_name ):
        """Mark a role as deleted"""
        self.visit_url( "%s/admin/roles?operation=delete&id=%s" % ( self.url, role_id ) )
        check_str = "Deleted 1 roles:  %s" % role_name
        self.check_page_for_string( check_str )

    def mark_user_deleted( self, user_id, email='' ):
        """Mark a user as deleted"""
        self.visit_url( "%s/admin/users?operation=delete&id=%s" % ( self.url, user_id ) )
        check_str = "Deleted 1 users"
        self.check_page_for_string( check_str )

    def move_library_item( self, cntrller, item_type, item_id, source_library_id, make_target_current,
                           target_library_id=None, target_folder_id=None, strings_displayed=[], strings_displayed_after_submit=[] ):
        params = dict( cntrller=cntrller,
                       item_type=item_type,
                       item_id=item_id,
                       source_library_id=source_library_id,
                       make_target_current=make_target_current )
        if target_library_id is not None:
            params[ 'target_library_id' ] = target_library_id
        if target_folder_id is not None:
            params[ 'target_folder_id' ] = target_folder_id
        self.visit_url( "%s/library_common/move_library_item" % self.url, params=params )
        if target_library_id:
            self.refresh_form( 'target_library_id', target_library_id, form_name='move_library_item' )
        if target_folder_id:
            tc.fv( '1', 'target_folder_id', target_folder_id )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        tc.submit( 'move_library_item_button' )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )

    def new_history( self, name=None ):
        """Creates a new, empty history"""
        if name:
            self.visit_url( "%s/history_new?name=%s" % ( self.url, name ) )
        else:
            self.visit_url( "%s/history_new" % self.url )
        self.check_page_for_string( 'New history created' )
        assert self.is_history_empty(), 'Creating new history did not result in an empty history.'

    def purge_group( self, group_id, group_name ):
        """Purge an existing group"""
        self.visit_url( "%s/admin/groups?operation=purge&id=%s" % ( self.url, group_id ) )
        check_str = "Purged 1 groups:  %s" % group_name
        self.check_page_for_string( check_str )

    def purge_library( self, library_id, library_name ):
        """Purge a library"""
        params = dict( id=library_id )
        self.visit_url( "/library_admin/purge_library", params )
        check_str = "Library '%s' and all of its contents have been purged" % library_name
        self.check_page_for_string( check_str )

    def purge_role( self, role_id, role_name ):
        """Purge an existing role"""
        self.visit_url( "%s/admin/roles?operation=purge&id=%s" % ( self.url, role_id ) )
        check_str = "Purged 1 roles:  %s" % role_name
        self.check_page_for_string( check_str )

    def purge_user( self, user_id, email ):
        """Purge a user account"""
        self.visit_url( "%s/admin/users?operation=purge&id=%s" % ( self.url, user_id ) )
        check_str = "Purged 1 users"
        self.check_page_for_string( check_str )

    def refresh_form( self, control_name, value, form_no=0, form_id=None, form_name=None, **kwd ):
        """Handles Galaxy's refresh_on_change for forms without ultimately submitting the form"""
        # control_name is the name of the form field that requires refresh_on_change, and value is
        # the value to which that field is being set.
        for i, f in enumerate( self.showforms() ):
            if i == form_no or ( form_id is not None and f.id == form_id ) or ( form_name is not None and f.name == form_name ):
                break
        formcontrols = self.get_form_controls( f )
        try:
            control = f.find_control( name=control_name )
        except:
            log.debug( '\n'.join( formcontrols ) )
            # This assumes we always want the first control of the given name, which may not be ideal...
            control = f.find_control( name=control_name, nr=0 )
        # Check for refresh_on_change attribute, submit a change if required
        if 'refresh_on_change' in control.attrs.keys():
            # Clear Control and set to proper value
            control.clear()
            tc.fv( f.name, control.name, value )
            # Create a new submit control, allows form to refresh, instead of going to next page
            control = ClientForm.SubmitControl( 'SubmitControl', '___refresh_grouping___', {'name': 'refresh_grouping'} )
            control.add_to_form( f )
            control.fixup()
            # Submit for refresh
            tc.submit( '___refresh_grouping___' )

    def reject_request( self, request_id, request_name, comment, strings_displayed=[], strings_displayed_after_submit=[] ):
        self.visit_url( "%s/requests_admin/reject_request?id=%s" % ( self.url, request_id ) )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        tc.fv( "1", "comment", comment )
        tc.submit( "reject_button" )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )

    def reload_external_service( self, external_service_type_id, strings_displayed=[], strings_displayed_after_submit=[] ):
        self.visit_url( '%s/external_service/reload_external_service_types' % self.url )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        tc.fv( "1", "external_service_type_id", external_service_type_id )
        tc.submit( "reload_external_service_type_button" )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )

    def reload_page( self ):
        tc.reload()
        tc.code(200)

    def rename_role( self, role_id, name='Role One Renamed', description='This is Role One Re-described' ):
        """Rename a role"""
        self.visit_url( "%s/admin/roles?operation=rename&id=%s" % ( self.url, role_id ) )
        self.check_page_for_string( 'Change role name and description' )
        tc.fv( "1", "name", name )
        tc.fv( "1", "description", description )
        tc.submit( "rename_role_button" )

    def rename_group( self, group_id, name='Group One Renamed' ):
        """Rename a group"""
        self.visit_url( "%s/admin/groups?operation=rename&id=%s" % ( self.url, group_id ) )
        self.check_page_for_string( 'Change group name' )
        tc.fv( "1", "name", name )
        tc.submit( "rename_group_button" )

    def rename_history( self, id, old_name, new_name ):
        """Rename an existing history"""
        self.visit_url( "/history/rename", params=dict( id=id, name=new_name ) )
        check_str = 'History: %s renamed to: %s' % ( old_name, urllib.unquote( new_name ) )
        self.check_page_for_string( check_str )

    def rename_sample_datasets( self, sample_id, sample_dataset_ids, new_sample_dataset_names, strings_displayed=[], strings_displayed_after_submit=[] ):
        sample_dataset_ids_string = ','.join( sample_dataset_ids )
        url = "%s/requests_admin/manage_datasets?operation=rename&id=%s" % ( self.url, sample_dataset_ids_string )
        self.visit_url( url )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        for sample_dataset_id, ( prefix, new_name ) in zip( sample_dataset_ids, new_sample_dataset_names ):
            tc.fv( "1", 'rename_datasets_for_sample_%s' % sample_dataset_id, prefix )
            tc.fv( "1", 'new_name_%s' % sample_dataset_id, new_name )
        tc.submit( "rename_datasets_button" )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )

    def request_type_permissions( self, request_type_id, request_type_name, role_ids_str, permissions_in, permissions_out ):
        # role_ids_str must be a comma-separated string of role ids
        url = "request_type/request_type_permissions?id=%s&update_roles_button=Save" % ( request_type_id )
        for po in permissions_out:
            key = '%s_out' % po
            url = "%s&%s=%s" % ( url, key, role_ids_str )
        for pi in permissions_in:
            key = '%s_in' % pi
            url = "%s&%s=%s" % ( url, key, role_ids_str )
        self.visit_url( "%s/%s" % ( self.url, url ) )
        check_str = "Permissions updated for request type '%s'" % request_type_name
        self.check_page_for_string( check_str )

    def reset_password_as_admin( self, user_id, password='testreset' ):
        """Reset a user password"""
        self.visit_url( "%s/admin/reset_user_password?id=%s" % ( self.url, user_id ) )
        tc.fv( "1", "password", password )
        tc.fv( "1", "confirm", password )
        tc.submit( "reset_user_password_button" )
        self.check_page_for_string( "Passwords reset for 1 user." )

    def run_tool( self, tool_id, repeat_name=None, **kwd ):
        """Runs the tool 'tool_id' and passes it the key/values from the *kwd"""
        params = dict( tool_id=tool_id )
        self.visit_url( "/tool_runner/index", params )
        # Must click somewhere in tool_form, to disambiguate what form
        # is being targetted.
        tc.browser.clicked( tc.browser.get_form( 'tool_form' ), None )
        if repeat_name is not None:
            repeat_button = '%s_add' % repeat_name
            # Submit the "repeat" form button to add an input)
            tc.submit( repeat_button )
        tc.find( 'runtool_btn' )
        self.submit_form( **kwd )

    def run_ucsc_main( self, track_params, output_params ):
        """Gets Data From UCSC"""
        tool_id = "ucsc_table_direct1"
        galaxy_url = "%s/tool_runner/index?" % self.url
        track_params.update( dict( GALAXY_URL=galaxy_url, hgta_compressType='none', tool_id=tool_id ) )
        self.visit_url( "http://genome.ucsc.edu/cgi-bin/hgTables", params=track_params )
        tc.fv( 'mainForm', 'checkboxGalaxy', 'on' )
        tc.submit( 'hgta_doTopSubmit' )
        tc.fv( 2, "hgta_geneSeqType", "genomic" )
        tc.submit( 'hgta_doGenePredSequence' )
        tc.fv( 2, 'hgSeq.casing', 'upper' )
        tc.submit( 'hgta_doGalaxyQuery' )

    def save_log( *path ):
        """Saves the log to a file"""
        filename = os.path.join( *path )
        file(filename, 'wt').write(buffer.getvalue())

    def set_history( self ):
        """Sets the history (stores the cookies for this run)"""
        if self.history_id:
            self.visit_url( "/history", params=dict( id=self.history_id ) )
        else:
            self.new_history()

    def share_current_history( self, email, strings_displayed=[], strings_displayed_after_submit=[],
                               action='', action_strings_displayed=[], action_strings_displayed_after_submit=[] ):
        """Share the current history with different users"""
        self.visit_url( "%s/history/share" % self.url )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        tc.fv( 'share', 'email', email )
        tc.submit( 'share_button' )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )
        if action:
            # If we have an action, then we are sharing datasets with users that do not have access permissions on them
            for check_str in action_strings_displayed:
                self.check_page_for_string( check_str )
            tc.fv( 'share_restricted', 'action', action )

            tc.submit( "share_restricted_button" )
            for check_str in action_strings_displayed_after_submit:
                self.check_page_for_string( check_str )

    def share_histories_with_users( self, ids, emails, strings_displayed=[], strings_displayed_after_submit=[],
                                    action=None, action_strings_displayed=[] ):
        """Share one or more histories with one or more different users"""
        self.visit_url( "%s/history/list?id=%s&operation=Share" % ( self.url, ids ) )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        tc.fv( 'share', 'email', emails )
        tc.submit( 'share_button' )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )
        if action:
            # If we have an action, then we are sharing datasets with users that do not have access permissions on them
            tc.fv( 'share_restricted', 'action', action )
            tc.submit( "share_restricted_button" )

            for check_str in action_strings_displayed:
                self.check_page_for_string( check_str )

    def show_cookies( self ):
        return tc.show_cookies()

    def showforms( self ):
        """Shows form, helpful for debugging new tests"""
        return tc.showforms()

    def start_sample_datasets_transfer( self, sample_id, sample_dataset_ids, strings_displayed=[], strings_displayed_after_submit=[], strings_displayed_count=[], strings_not_displayed=[] ):
        url = '%s/requests_admin/manage_datasets?cntrller=requests_admin&sample_id=%s' % ( self.url, sample_id )
        self.visit_url( url )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        # simulate selecting datasets and clicking the transfer button on the sample datasets grid
        sample_dataset_ids_string = ','.join( sample_dataset_ids )
        url = "%s/requests_admin/manage_datasets?operation=transfer&id=%s" % ( self.url, sample_dataset_ids_string )
        self.visit_url( url )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )
        for check_str in strings_not_displayed:
            self.check_string_not_in_page( check_str )
        for check_str, count in strings_displayed_count:
            self.check_string_count_in_page( check_str, count )

    def submit_form( self, form_no=0, button="runtool_btn", **kwd ):
        """Populates and submits a form from the keyword arguments."""
        # An HTMLForm contains a sequence of Controls.  Supported control classes are:
        # TextControl, FileControl, ListControl, RadioControl, CheckboxControl, SelectControl,
        # SubmitControl, ImageControl
        for i, f in enumerate( self.showforms() ):
            if i == form_no:
                break
        # To help with debugging a tool, print out the form controls when the test fails
        print "form '%s' contains the following controls ( note the values )" % f.name
        controls = {}
        formcontrols = self.get_form_controls( f )
        hc_prefix = '<HiddenControl('
        for i, control in enumerate( f.controls ):
            if not hc_prefix in str( control ):
                try:
                    #check if a repeat element needs to be added
                    if control.name is not None:
                        if control.name not in kwd and control.name.endswith( '_add' ):
                            #control name doesn't exist, could be repeat
                            repeat_startswith = control.name[0:-4]
                            if repeat_startswith and not [ c_name for c_name in controls.keys() if c_name.startswith( repeat_startswith ) ] and [ c_name for c_name in kwd.keys() if c_name.startswith( repeat_startswith ) ]:
                                tc.browser.clicked( f, control )
                                tc.submit( control.name )
                                return self.submit_form( form_no=form_no, button=button, **kwd )
                    # Check for refresh_on_change attribute, submit a change if required
                    if hasattr( control, 'attrs' ) and 'refresh_on_change' in control.attrs.keys():
                        changed = False
                        # For DataToolParameter, control.value is the HDA id, but kwd contains the filename.
                        # This loop gets the filename/label for the selected values.
                        item_labels = [ item.attrs[ 'label' ] for item in control.get_items() if item.selected ]
                        for value in kwd[ control.name ]:
                            if value not in control.value and True not in [ value in item_label for item_label in item_labels ]:
                                changed = True
                                break
                        if changed:
                            # Clear Control and set to proper value
                            control.clear()
                            # kwd[control.name] should be a singlelist
                            for elem in kwd[ control.name ]:
                                tc.fv( f.name, control.name, str( elem ) )
                            # Create a new submit control, allows form to refresh, instead of going to next page
                            control = ClientForm.SubmitControl( 'SubmitControl', '___refresh_grouping___', {'name': 'refresh_grouping'} )
                            control.add_to_form( f )
                            control.fixup()
                            # Submit for refresh
                            tc.submit( '___refresh_grouping___' )
                            return self.submit_form( form_no=form_no, button=button, **kwd )
                except Exception:
                    log.exception( "In submit_form, continuing, but caught exception." )
                    for formcontrol in formcontrols:
                        log.debug( formcontrol )
                    continue
                controls[ control.name ] = control
        # No refresh_on_change attribute found in current form, so process as usual
        for control_name, control_value in kwd.items():
            if control_name not in controls:
                continue  # these cannot be handled safely - cause the test to barf out
            if not isinstance( control_value, list ):
                control_value = [ control_value ]
            control = controls[ control_name ]
            control.clear()
            if control.is_of_kind( "text" ):
                tc.fv( f.name, control.name, ",".join( control_value ) )
            elif control.is_of_kind( "list" ):
                try:
                    if control.is_of_kind( "multilist" ):
                        if control.type == "checkbox":
                            def is_checked( value ):
                                # Copied from form_builder.CheckboxField
                                if value == True:
                                    return True
                                if isinstance( value, list ):
                                    value = value[0]
                                return isinstance( value, basestring ) and value.lower() in ( "yes", "true", "on" )
                            try:
                                checkbox = control.get()
                                checkbox.selected = is_checked( control_value )
                            except Exception, e1:
                                print "Attempting to set checkbox selected value threw exception: ", e1
                                # if there's more than one checkbox, probably should use the behaviour for
                                # ClientForm.ListControl ( see twill code ), but this works for now...
                                for elem in control_value:
                                    control.get( name=elem ).selected = True
                        else:
                            for elem in control_value:
                                try:
                                    # Doubt this case would ever work, but want
                                    # to preserve backward compat.
                                    control.get( name=elem ).selected = True
                                except Exception:
                                    # ... anyway this is really what we want to
                                    # do, probably even want to try the len(
                                    # elem ) > 30 check below.
                                    control.get( label=elem ).selected = True
                    else:  # control.is_of_kind( "singlelist" )
                        for elem in control_value:
                            try:
                                tc.fv( f.name, control.name, str( elem ) )
                            except Exception:
                                try:
                                    # Galaxy truncates long file names in the dataset_collector in galaxy/tools/parameters/basic.py
                                    if len( elem ) > 30:
                                        elem_name = '%s..%s' % ( elem[:17], elem[-11:] )
                                        tc.fv( f.name, control.name, str( elem_name ) )
                                        pass
                                    else:
                                        raise
                                except Exception:
                                    raise
                            except Exception:
                                for formcontrol in formcontrols:
                                    log.debug( formcontrol )
                                log.exception( "Attempting to set control '%s' to value '%s' (also tried '%s') threw exception.", control.name, elem, elem_name )
                                pass
                except Exception, exc:
                    for formcontrol in formcontrols:
                        log.debug( formcontrol )
                    errmsg = "Attempting to set field '%s' to value '%s' in form '%s' threw exception: %s\n" % ( control_name, str( control_value ), f.name, str( exc ) )
                    errmsg += "control: %s\n" % str( control )
                    errmsg += "If the above control is a DataToolparameter whose data type class does not include a sniff() method,\n"
                    errmsg += "make sure to include a proper 'ftype' attribute to the tag for the control within the <test> tag set.\n"
                    raise AssertionError( errmsg )
            else:
                # Add conditions for other control types here when necessary.
                pass
        tc.submit( button )

    def submit_request( self, cntrller, request_id, request_name, strings_displayed_after_submit=[] ):
        self.visit_url( "%s/requests_common/submit_request?cntrller=%s&id=%s" % ( self.url, cntrller, request_id ) )
        for check_str in strings_displayed_after_submit:
            self.check_page_for_string( check_str )

    def switch_history( self, id='', name='' ):
        """Switches to a history in the current list of histories"""
        params = dict( operation='switch', id=id )
        self.visit_url( "/history/list", params )
        if name:
            self.check_history_for_exact_string( name )

    def undelete_group( self, group_id, group_name ):
        """Undelete an existing group"""
        self.visit_url( "%s/admin/groups?operation=undelete&id=%s" % ( self.url, group_id ) )
        check_str = "Undeleted 1 groups:  %s" % group_name
        self.check_page_for_string( check_str )

    def undelete_history_item( self, hda_id, strings_displayed=[] ):
        """Un-deletes a deleted item in a history"""
        try:
            hda_id = int( hda_id )
        except:
            raise AssertionError( "Invalid hda_id '%s' - must be int" % hda_id )
        self.visit_url( "%s/datasets/%s/undelete" % ( self.url, self.security.encode_id( hda_id ) ) )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )

    def undelete_library_item( self, cntrller, library_id, item_id, item_name, item_type='library_dataset' ):
        """Mark a library item as deleted"""
        params = dict( cntrller=cntrller, library_id=library_id, item_id=item_id, item_type=item_type )
        self.visit_url( "/library_common/undelete_library_item", params )
        if item_type == 'library_dataset':
            item_desc = 'Dataset'
        else:
            item_desc = item_type.capitalize()
        check_str = "marked undeleted"
        self.check_for_strings( strings_displayed=[ item_desc, check_str ] )

    def undelete_role( self, role_id, role_name ):
        """Undelete an existing role"""
        self.visit_url( "%s/admin/roles?operation=undelete&id=%s" % ( self.url, role_id ) )
        check_str = "Undeleted 1 roles:  %s" % role_name
        self.check_page_for_string( check_str )

    def undelete_user( self, user_id, email='' ):
        """Undelete a user"""
        self.visit_url( "%s/admin/users?operation=undelete&id=%s" % ( self.url, user_id ) )
        check_str = "Undeleted 1 users"
        self.check_page_for_string( check_str )

    def unshare_history( self, history_id, user_id, strings_displayed=[] ):
        """Unshare a history that has been shared with another user"""
        self.visit_url( "/history/sharing", params=dict( id=history_id ) )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )
        self.visit_url( "/history/sharing", params=dict( unshare_user=user_id, id=history_id ) )

    def upload_library_dataset( self, cntrller, library_id, folder_id, filename='', server_dir='', replace_id='',
                                upload_option='upload_file', file_type='auto', dbkey='hg18', space_to_tab='',
                                link_data_only='copy_files', preserve_dirs='Yes', filesystem_paths='', roles=[],
                                ldda_message='', hda_ids='', template_refresh_field_name='1_field_name',
                                template_refresh_field_contents='', template_fields=[], show_deleted='False', strings_displayed=[] ):
        """Add datasets to library using any upload_option"""
        # NOTE: due to the library_wait() method call at the end of this method, no tests should be done
        # for strings_displayed_after_submit.
        params = dict( cntrller=cntrller, library_id=library_id, folder_id=folder_id )
        url = "/library_common/upload_library_dataset"
        if replace_id:
            # If we're uploading a new version of a library dataset, we have to include the replace_id param in the
            # request because the form field named replace_id will not be displayed on the upload form if we dont.
            params[ 'replace_id' ] = replace_id
        self.visit_url( url, params=params )
        if template_refresh_field_contents:
            # A template containing an AddressField is displayed on the upload form, so we need to refresh the form
            # with the received template_refresh_field_contents.
            self.refresh_form( template_refresh_field_name, template_refresh_field_contents )
        for tup in template_fields:
            tc.fv( "1", tup[0], tup[1] )
        tc.fv( "upload_library_dataset", "library_id", library_id )
        tc.fv( "upload_library_dataset", "folder_id", folder_id )
        tc.fv( "upload_library_dataset", "show_deleted", show_deleted )
        tc.fv( "upload_library_dataset", "ldda_message", ldda_message )
        tc.fv( "upload_library_dataset", "file_type", file_type )
        tc.fv( "upload_library_dataset", "dbkey", dbkey )
        if space_to_tab:
            tc.fv( "upload_library_dataset", "space_to_tab", space_to_tab )
        for role_id in roles:
            tc.fv( "upload_library_dataset", "roles", role_id )
        # Refresh the form by selecting the upload_option - we do this here to ensure
        # all previously entered form contents are retained.
        self.refresh_form( 'upload_option', upload_option )
        if upload_option == 'import_from_history':
            for check_str in strings_displayed:
                self.check_page_for_string( check_str )
            if hda_ids:
                # Twill cannot handle multi-checkboxes, so the form can only have 1 hda_ids checkbox
                try:
                    tc.fv( "add_history_datasets_to_library", "hda_ids", hda_ids )
                except:
                    tc.fv( "add_history_datasets_to_library", "hda_ids", '1' )
            tc.submit( 'add_history_datasets_to_library_button' )
        else:
            if upload_option in [ 'upload_paths', 'upload_directory' ]:
                tc.fv( "upload_library_dataset", "link_data_only", link_data_only )
            if upload_option == 'upload_paths':
                tc.fv( "upload_library_dataset", "filesystem_paths", filesystem_paths )
            if upload_option == 'upload_directory' and server_dir:
                tc.fv( "upload_library_dataset", "server_dir", server_dir )
            if upload_option == 'upload_file':
                if filename:
                    filename = self.get_filename( filename )
                    tc.formfile( "upload_library_dataset", "files_0|file_data", filename )
            for check_str in strings_displayed:
                self.check_page_for_string( check_str )
            tc.submit( "runtool_btn" )
        # Give the files some time to finish uploading
        self.library_wait( library_id )

    def upload_file( self, filename, ftype='auto', dbkey='unspecified (?)', space_to_tab=False, metadata=None, composite_data=None, name=None, shed_tool_id=None, wait=True ):
        """
        Uploads a file.  If shed_tool_id has a value, we're testing tools migrated from the distribution to the tool shed,
        so the tool-data directory of test data files is contained in the installed tool shed repository.
        """
        self.visit_url( "%s/tool_runner?tool_id=upload1" % self.url )
        try:
            self.refresh_form( "file_type", ftype )  # Refresh, to support composite files
            tc.fv( "tool_form", "dbkey", dbkey )
            if metadata:
                for elem in metadata:
                    tc.fv( "tool_form", "files_metadata|%s" % elem.get( 'name' ), elem.get( 'value' ) )
            if composite_data:
                for i, composite_file in enumerate( composite_data ):
                    filename = self.get_filename( composite_file.get( 'value' ), shed_tool_id=shed_tool_id )
                    tc.formfile( "tool_form", "files_%i|file_data" % i, filename )
                    tc.fv( "tool_form", "files_%i|space_to_tab" % i, composite_file.get( 'space_to_tab', False ) )
            else:
                filename = self.get_filename( filename, shed_tool_id=shed_tool_id )
                tc.formfile( "tool_form", "file_data", filename )
                tc.fv( "tool_form", "space_to_tab", space_to_tab )
                if name:
                    # NAME is a hidden form element, so the following prop must
                    # set to use it.
                    tc.config("readonly_controls_writeable", 1)
                    tc.fv( "tool_form", "NAME", name )
            tc.submit( "runtool_btn" )
        except AssertionError, err:
            errmsg = "Uploading file resulted in the following exception.  Make sure the file (%s) exists.  " % filename
            errmsg += str( err )
            raise AssertionError( errmsg )
        if not wait:
            return
        # Make sure every history item has a valid hid
        hids = self.get_hids_in_history( self.get_latest_history()[ 'id' ] )
        for hid in hids:
            try:
                int( hid )
            except:
                raise AssertionError( "Invalid hid (%s) created when uploading file %s" % ( hid, filename ) )
        # Wait for upload processing to finish (TODO: this should be done in each test case instead)
        self.wait()

    def upload_url_paste( self, url_paste, ftype='auto', dbkey='unspecified (?)' ):
        """Pasted data in the upload utility"""
        self.visit_url( "/tool_runner/index?tool_id=upload1" )
        try:
            self.refresh_form( "file_type", ftype ) #Refresh, to support composite files
            tc.fv( "tool_form", "dbkey", dbkey )
            tc.fv( "tool_form", "url_paste", url_paste )
            tc.submit( "runtool_btn" )
        except Exception, e:
            errmsg = "Problem executing upload utility using url_paste: %s" % str( e )
            raise AssertionError( errmsg )
        # Make sure every history item has a valid hid
        hids = self.get_hids_in_history( self.get_latest_history()[ 'id' ] )
        for hid in hids:
            try:
                int( hid )
            except:
                raise AssertionError( "Invalid hid (%s) created when pasting %s" % ( hid, url_paste ) )
        # Wait for upload processing to finish (TODO: this should be done in each test case instead)
        self.wait()

    def user_set_default_permissions( self, cntrller='user', permissions_out=[], permissions_in=[], role_id='2' ):
        # role.id = 2 is Private Role for test2@bx.psu.edu
        # NOTE: Twill has a bug that requires the ~/user/permissions page to contain at least 1 option value
        # in each select list or twill throws an exception, which is: ParseError: OPTION outside of SELECT
        # Due to this bug, we'll bypass visiting the page, and simply pass the permissions on to the
        # /user/set_default_permissions method.
        url = "user/set_default_permissions?cntrller=%s&update_roles_button=Save&id=None" % cntrller
        for po in permissions_out:
            key = '%s_out' % po
            url = "%s&%s=%s" % ( url, key, str( role_id ) )
        for pi in permissions_in:
            key = '%s_in' % pi
            url = "%s&%s=%s" % ( url, key, str( role_id ) )
        self.visit_url( "%s/%s" % ( self.url, url ) )
        self.check_page_for_string( 'Default new history permissions have been changed.' )

    def verify_composite_datatype_file_content( self, file_name, hda_id, base_name=None, attributes=None, dataset_fetcher=None, shed_tool_id=None ):
        dataset_fetcher = dataset_fetcher or self.__default_dataset_fetcher()
        local_name = self.get_filename( file_name, shed_tool_id=shed_tool_id )
        if base_name is None:
            base_name = os.path.split(file_name)[-1]
        temp_name = self.makeTfname(fname=base_name)
        data = dataset_fetcher( hda_id, base_name )
        file( temp_name, 'wb' ).write( data )
        if self.keepOutdir > '':
            ofn = os.path.join(self.keepOutdir, base_name)
            shutil.copy(temp_name, ofn)
            log.debug('## GALAXY_TEST_SAVE=%s. saved %s' % (self.keepOutdir, ofn))
        try:
            if attributes is None:
                attributes = {}
            compare = attributes.get( 'compare', 'diff' )
            if compare == 'diff':
                self.files_diff( local_name, temp_name, attributes=attributes )
            elif compare == 're_match':
                self.files_re_match( local_name, temp_name, attributes=attributes )
            elif compare == 're_match_multiline':
                self.files_re_match_multiline( local_name, temp_name, attributes=attributes )
            elif compare == 'sim_size':
                delta = attributes.get('delta', '100')
                s1 = len(data)
                s2 = os.path.getsize(local_name)
                if abs(s1 - s2) > int(delta):
                    raise Exception( 'Files %s=%db but %s=%db - compare (delta=%s) failed' % (temp_name, s1, local_name, s2, delta) )
            else:
                raise Exception( 'Unimplemented Compare type: %s' % compare )
        except AssertionError, err:
            errmsg = 'Composite file (%s) of History item %s different than expected, difference (using %s):\n' % ( base_name, hda_id, compare )
            errmsg += str( err )
            raise AssertionError( errmsg )
        finally:
            if 'GALAXY_TEST_NO_CLEANUP' not in os.environ:
                os.remove( temp_name )

    def verify_dataset_correctness( self, filename, hid=None, wait=True, maxseconds=120, attributes=None, shed_tool_id=None ):
        """Verifies that the attributes and contents of a history item meet expectations"""
        if wait:
            self.wait( maxseconds=maxseconds )  # wait for job to finish
        data_list = self.get_history_from_api( encoded_history_id=None, show_deleted=False, show_details=False )
        self.assertTrue( data_list )
        if hid is None:  # take last hid
            dataset = data_list[-1]
            hid = str( dataset.get('hid') )
        else:
            datasets = [ dataset for dataset in data_list if str( dataset.get('hid') ) == str( hid ) ]
            self.assertTrue( len( datasets ) == 1 )
            dataset = datasets[0]
        self.assertTrue( hid )
        dataset = self.json_from_url( dataset[ 'url' ] )
        self._assert_dataset_state( dataset, 'ok' )
        if filename is not None and self.is_zipped( filename ):
            errmsg = 'History item %s is a zip archive which includes invalid files:\n' % hid
            zip_file = zipfile.ZipFile( filename, "r" )
            name = zip_file.namelist()[0]
            test_ext = name.split( "." )[1].strip().lower()
            if not ( test_ext == 'scf' or test_ext == 'ab1' or test_ext == 'txt' ):
                raise AssertionError( errmsg )
            for name in zip_file.namelist():
                ext = name.split( "." )[1].strip().lower()
                if ext != test_ext:
                    raise AssertionError( errmsg )
        else:
            # See not in controllers/root.py about encoded_id.
            hda_id = dataset.get( 'id' )
            self.verify_hid( filename, hid=hid, hda_id=hda_id, attributes=attributes, shed_tool_id=shed_tool_id)

    def verify_extra_files_content( self, extra_files, hda_id, dataset_fetcher, shed_tool_id=None ):
        files_list = []
        for extra_type, extra_value, extra_name, extra_attributes in extra_files:
            if extra_type == 'file':
                files_list.append( ( extra_name, extra_value, extra_attributes ) )
            elif extra_type == 'directory':
                for filename in os.listdir( self.get_filename( extra_value, shed_tool_id=shed_tool_id ) ):
                    files_list.append( ( filename, os.path.join( extra_value, filename ), extra_attributes ) )
            else:
                raise ValueError( 'unknown extra_files type: %s' % extra_type )
        for filename, filepath, attributes in files_list:
            self.verify_composite_datatype_file_content( filepath, hda_id, base_name=filename, attributes=attributes, dataset_fetcher=dataset_fetcher, shed_tool_id=shed_tool_id )

    def verify_hid( self, filename, hda_id, attributes, shed_tool_id, hid="", dataset_fetcher=None):
        dataset_fetcher = dataset_fetcher or self.__default_dataset_fetcher()
        data = dataset_fetcher( hda_id )
        if attributes is not None and attributes.get( "assert_list", None ) is not None:
            try:
                verify_assertions(data, attributes["assert_list"])
            except AssertionError, err:
                errmsg = 'History item %s different than expected\n' % (hid)
                errmsg += str( err )
                raise AssertionError( errmsg )
        if filename is not None:
            local_name = self.get_filename( filename, shed_tool_id=shed_tool_id )
            temp_name = self.makeTfname(fname=filename)
            file( temp_name, 'wb' ).write( data )

            # if the server's env has GALAXY_TEST_SAVE, save the output file to that dir
            if self.keepOutdir:
                ofn = os.path.join( self.keepOutdir, os.path.basename( local_name ) )
                log.debug( 'keepoutdir: %s, ofn: %s', self.keepOutdir, ofn )
                try:
                    shutil.copy( temp_name, ofn )
                except Exception, exc:
                    error_log_msg = ( 'TwillTestCase could not save output file %s to %s: ' % ( temp_name, ofn ) )
                    error_log_msg += str( exc )
                    log.error( error_log_msg, exc_info=True )
                else:
                    log.debug('## GALAXY_TEST_SAVE=%s. saved %s' % ( self.keepOutdir, ofn ) )
            try:
                if attributes is None:
                    attributes = {}
                compare = attributes.get( 'compare', 'diff' )
                if attributes.get( 'ftype', None ) == 'bam':
                    local_fh, temp_name = self._bam_to_sam( local_name, temp_name )
                    local_name = local_fh.name
                extra_files = attributes.get( 'extra_files', None )
                if compare == 'diff':
                    self.files_diff( local_name, temp_name, attributes=attributes )
                elif compare == 're_match':
                    self.files_re_match( local_name, temp_name, attributes=attributes )
                elif compare == 're_match_multiline':
                    self.files_re_match_multiline( local_name, temp_name, attributes=attributes )
                elif compare == 'sim_size':
                    delta = attributes.get('delta', '100')
                    s1 = len(data)
                    s2 = os.path.getsize(local_name)
                    if abs(s1 - s2) > int(delta):
                        raise Exception( 'Files %s=%db but %s=%db - compare (delta=%s) failed' % (temp_name, s1, local_name, s2, delta) )
                elif compare == "contains":
                    self.files_contains( local_name, temp_name, attributes=attributes )
                else:
                    raise Exception( 'Unimplemented Compare type: %s' % compare )
                if extra_files:
                    self.verify_extra_files_content( extra_files, hda_id, shed_tool_id=shed_tool_id, dataset_fetcher=dataset_fetcher )
            except AssertionError, err:
                errmsg = 'History item %s different than expected, difference (using %s):\n' % ( hid, compare )
                errmsg += "( %s v. %s )\n" % ( local_name, temp_name )
                errmsg += str( err )
                raise AssertionError( errmsg )
            finally:
                if 'GALAXY_TEST_NO_CLEANUP' not in os.environ:
                    os.remove( temp_name )

    def view_external_service( self, external_service_id, strings_displayed=[] ):
        self.visit_url( '%s/external_service/view_external_service?id=%s' % ( self.url, external_service_id ) )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )

    def view_form( self, id, form_type='', form_name='', form_desc='', form_layout_name='', field_dicts=[] ):
        '''View form details'''
        self.visit_url( "%s/forms/view_latest_form_definition?id=%s" % ( self.url, id ) )
        #self.check_page_for_string( form_type )
        self.check_page_for_string( form_name )
        #self.check_page_for_string( form_desc )
        self.check_page_for_string( form_layout_name )
        for i, field_dict in enumerate( field_dicts ):
            self.check_page_for_string( field_dict[ 'label' ] )
            self.check_page_for_string( field_dict[ 'desc' ] )
            self.check_page_for_string( field_dict[ 'type' ] )
            if field_dict[ 'type' ].lower() == 'selectfield':
                for option_index, option in enumerate( field_dict[ 'selectlist' ] ):
                    self.check_page_for_string( option )

    def view_history( self, history_id, strings_displayed=[] ):
        """Displays a history for viewing"""
        self.visit_url( '%s/history/view?id=%s' % ( self.url, self.security.encode_id( history_id ) ) )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )

    def view_request( self, cntrller, request_id, strings_displayed=[], strings_displayed_count=[], strings_not_displayed=[] ):
        self.visit_url( "%s/%s/browse_requests?operation=view_request&id=%s" % ( self.url, cntrller, request_id ) )
        self.check_page( strings_displayed, strings_displayed_count, strings_not_displayed )

    def view_request_history( self, cntrller, request_id, strings_displayed=[], strings_displayed_count=[], strings_not_displayed=[] ):
        self.visit_url( "%s/requests_common/view_request_history?cntrller=%s&id=%s" % ( self.url, cntrller, request_id ) )
        self.check_page( strings_displayed, strings_displayed_count, strings_not_displayed )

    def view_request_type( self, request_type_id, request_type_name, sample_states, strings_displayed=[] ):
        '''View request_type details'''
        self.visit_url( "%s/request_type/view_request_type?id=%s" % ( self.url, request_type_id ) )
        self.check_page_for_string( '"%s" request type' % request_type_name )
        for name, desc in sample_states:
            self.check_page_for_string( name )
            self.check_page_for_string( desc )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )

    def view_sample_dataset( self, sample_dataset_id, strings_displayed=[], strings_displayed_count=[], strings_not_displayed=[] ):
        self.visit_url( "%s/requests_admin/manage_datasets?operation=view&id=%s" % ( self.url, sample_dataset_id ) )
        self.check_page( strings_displayed, strings_displayed_count, strings_not_displayed )

    def view_sample_history( self, cntrller, sample_id, strings_displayed=[], strings_displayed_count=[], strings_not_displayed=[] ):
        self.visit_url( "%s/requests_common/view_sample_history?cntrller=%s&sample_id=%s" % ( self.url, cntrller, sample_id ) )
        self.check_page( strings_displayed, strings_displayed_count, strings_not_displayed )

    def view_shared_histories( self, strings_displayed=[] ):
        self.visit_url( "/history/list_shared" )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )

    def view_stored_active_histories( self, strings_displayed=[] ):
        self.visit_url( "/history/list" )
        self.check_page_for_string( 'Saved Histories' )
        self.check_page_for_string( 'operation=Rename' )
        self.check_page_for_string( 'operation=Switch' )
        self.check_page_for_string( 'operation=Delete' )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )

    def view_stored_deleted_histories( self, strings_displayed=[] ):
        self.visit_url( "/history/list?f-deleted=True" )
        self.check_page_for_string( 'Saved Histories' )
        self.check_page_for_string( 'operation=Undelete' )
        for check_str in strings_displayed:
            self.check_page_for_string( check_str )

    def visit_url( self, url, params=None, doseq=False, allowed_codes=[ 200 ] ):
        if params is None:
            params = dict()
        parsed_url = urlparse( url )
        if len( parsed_url.netloc ) == 0:
            url = 'http://%s:%s%s' % ( self.host, self.port, parsed_url.path )
        else:
            url = '%s://%s%s' % ( parsed_url.scheme, parsed_url.netloc, parsed_url.path )
        if parsed_url.query:
            for query_parameter in parsed_url.query.split( '&' ):
                key, value = query_parameter.split( '=' )
                params[ key ] = value
        if params:
            url += '?%s' % urllib.urlencode( params, doseq=doseq )
        new_url = tc.go( url )
        return_code = tc.browser.get_code()
        assert return_code in allowed_codes, 'Invalid HTTP return code %s, allowed codes: %s' % \
            ( return_code, ', '.join( str( code ) for code in allowed_codes ) )
        return new_url

    def wait( self, **kwds ):
        """Waits for the tools to finish"""
        return self.wait_for(lambda: self.get_running_datasets(), **kwds)

    def wait_for( self, func, **kwd ):
        sleep_amount = 0.1
        slept = 0
        walltime_exceeded = 86400
        while slept <= walltime_exceeded:
            result = func()
            if result:
                time.sleep( sleep_amount )
                slept += sleep_amount
                sleep_amount *= 2
                if slept + sleep_amount > walltime_exceeded:
                    sleep_amount = walltime_exceeded - slept  # don't overshoot maxseconds
            else:
                break
        assert slept < walltime_exceeded, 'Tool run exceeded reasonable walltime of 24 hours, terminating.'

    def write_temp_file( self, content, suffix='.html' ):
        fd, fname = tempfile.mkstemp( suffix=suffix, prefix='twilltestcase-' )
        f = os.fdopen( fd, "w" )
        f.write( content )
        f.close()
        return fname

    def _assert_dataset_state( self, dataset, state ):
        if dataset.get( 'state' ) != state:
            blurb = dataset.get( 'misc_blurb' )
            errmsg = "Expecting dataset state '%s', but state is '%s'. Dataset blurb: %s\n\n" % ( state, dataset.get('state'), blurb.strip() )
            errmsg += self.get_job_stderr( dataset.get( 'id' ), format=True )
            raise AssertionError( errmsg )

    def _bam_to_sam( self, local_name, temp_name ):
        temp_local = tempfile.NamedTemporaryFile( suffix='.sam', prefix='local_bam_converted_to_sam_' )
        fd, temp_temp = tempfile.mkstemp( suffix='.sam', prefix='history_bam_converted_to_sam_' )
        os.close( fd )
        p = subprocess.Popen( args='samtools view -h -o "%s" "%s"' % ( temp_local.name, local_name  ), shell=True )
        assert not p.wait(), 'Converting local (test-data) bam to sam failed'
        p = subprocess.Popen( args='samtools view -h -o "%s" "%s"' % ( temp_temp, temp_name  ), shell=True )
        assert not p.wait(), 'Converting history bam to sam failed'
        os.remove( temp_name )
        return temp_local, temp_temp

    def _format_stream( self, output, stream, format ):
        if format:
            msg = "---------------------- >> begin tool %s << -----------------------\n" % stream
            msg += output + "\n"
            msg += "----------------------- >> end tool %s << ------------------------\n" % stream
        else:
            msg = output
        return msg

    def _get_job_stream_output( self, hda_id, stream, format ):
        self.visit_url( "/datasets/%s/%s" % ( hda_id, stream ) )

        output = self.last_page()
        return self._format_stream( output, stream, format )

    def __default_dataset_fetcher( self ):
        def fetcher( hda_id, filename=None ):
            if filename is None:
                page_url = "/display?encoded_id=%s" % hda_id
            else:
                page_url = "/datasets/%s/display/%s" % ( hda_id, filename )
            self.visit_url( page_url )
            data = self.last_page()
            return data
        return fetcher
