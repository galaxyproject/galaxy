import pkg_resources
pkg_resources.require( "twill==0.9" )

import StringIO, os, sys, random, filecmp, time, unittest, urllib, logging, difflib, zipfile
from itertools import *

import twill
import twill.commands as tc
from twill.other_packages._mechanize_dist import ClientForm
pkg_resources.require( "elementtree" )
from elementtree import ElementTree
from galaxy.web import security

buffer = StringIO.StringIO()

#Force twill to log to a buffer -- FIXME: Should this go to stdout and be captured by nose?
twill.set_output(buffer)
tc.config('use_tidy', 0)

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
        self.file_dir = os.environ.get( 'GALAXY_TEST_FILE_DIR' )
        self.home()
        #self.set_history()

    # Functions associated with files
    def files_diff( self, file1, file2 ):
        """Checks the contents of 2 files for differences"""
        if not filecmp.cmp( file1, file2 ):
            files_differ = False
            local_file = open( file1, 'U' ).readlines()
            history_data = open( file2, 'U' ).readlines()
            if len( local_file ) == len( history_data ):
                for i in range( len( history_data ) ):
                    if local_file[i].rstrip( '\r\n' ) != history_data[i].rstrip( '\r\n' ):
                        files_differ = True
                        break
            else:
                files_differ = True
            if files_differ:
                diff = difflib.unified_diff( local_file, history_data, "local_file", "history_data" )
                diff_slice = list( islice( diff, 40 ) )
                if file1.endswith( '.pdf' ) or file2.endswith( '.pdf' ):
                    # PDF files contain both a creation and modification date, so we need to
                    # handle these differences.  As long as the rest of the PDF file does not differ,
                    # we're ok.
                    if len( diff_slice ) == 13 and \
                    diff_slice[6].startswith( '-/CreationDate' ) and diff_slice[7].startswith( '-/ModDate' ) \
                    and diff_slice[8].startswith( '+/CreationDate' ) and diff_slice[9].startswith( '+/ModDate' ):
                        return True
                raise AssertionError( "".join( diff_slice ) )
        return True

    def get_filename( self, filename ):
        full = os.path.join( self.file_dir, filename)
        return os.path.abspath(full)

    def save_log( *path ):
        """Saves the log to a file"""
        filename = os.path.join( *path )
        file(filename, 'wt').write(buffer.getvalue())

    def upload_file( self, filename, ftype='auto', dbkey='unspecified (?)' ):
        """Uploads a file"""
        filename = self.get_filename(filename)
        self.home()
        self.visit_page( "tool_runner/index?tool_id=upload1" )
        try: 
            tc.fv("1","file_type", ftype)
            tc.fv("1","dbkey", dbkey)
            tc.formfile("1","file_data", filename)
            tc.submit("runtool_btn")
            self.home()
        except AssertionError, err:
            errmsg = "The file (%s) doesn't exist." % filename
            errmsg += str( err )
            raise AssertionError( errmsg )
        # Make sure every history item has a valid hid
        hids = self.get_hids_in_history()
        for hid in hids:
            try:
                valid_hid = int( hid )
            except:
                raise AssertionError, "Invalid hid (%s) created when uploading file %s" % ( hid, filename )
    def upload_url_paste( self, url_paste, ftype='auto', dbkey='unspecified (?)' ):
        """Pasted data in the upload utility"""
        self.visit_page( "tool_runner/index?tool_id=upload1" )
        try: 
            tc.fv( "1", "file_type", ftype )
            tc.fv( "1", "dbkey", dbkey )
            tc.fv( "1", "url_paste", url_paste )
            tc.submit( "runtool_btn" )
            self.home()
        except Exception, e:
            errmsg = "Problem executing upload utility using url_paste: %s" % str( e )
            raise AssertionError( e )
        # Make sure every history item has a valid hid
        hids = self.get_hids_in_history()
        for hid in hids:
            try:
                valid_hid = int( hid )
            except:
                raise AssertionError, "Invalid hid (%s) created when pasting %s" % ( hid, url_paste )

    # Functions associated with histories
    def check_history_for_errors( self ):
        """Raises an exception if there are errors in a history"""
        self.home()
        self.visit_page( "history" )
        page = self.last_page()
        if page.find( 'error' ) > -1:
            raise AssertionError('Errors in the history for user %s' % self.user )
    def check_history_for_string( self, patt, show_deleted=False ):
        """Looks for 'string' in history page"""
        self.home()
        if show_deleted:
            self.visit_page( "history?show_deleted=True" )
        else:
            self.visit_page( "history" )
        for subpatt in patt.split():
            tc.find(subpatt)
        self.home()
    def clear_history( self ):
        """Empties a history of all datasets"""
        self.visit_page( "clear_history" )
        self.check_history_for_string( 'Your history is empty' )
        self.home()
    def delete_history( self, id ):
        """Deletes one or more histories"""
        history_list = self.get_histories_as_data_list()
        self.assertTrue( history_list )
        num_deleted = len( id.split( ',' ) )
        self.home()
        self.visit_page( "history/list?operation=delete&id=%s" % ( id ) )
        check_str = 'Deleted %d histories' % num_deleted
        self.check_page_for_string( check_str )
        self.home()
    def delete_current_history( self, check_str='' ):
        """Deletes the current history"""
        self.home()
        self.visit_page( "history/delete_current" )
        if check_str:
            self.check_page_for_string( check_str )
        self.home()
    def get_histories_as_data_list( self ):
        """Returns the data elements of all histories"""
        tree = self.histories_as_xml_tree()
        data_list = [ elem for elem in tree.findall("data") ]
        return data_list
    def get_history_as_data_list( self, show_deleted=False ):
        """Returns the data elements of a history"""
        tree = self.history_as_xml_tree( show_deleted=show_deleted )
        data_list = [ elem for elem in tree.findall("data") ]
        return data_list
    def history_as_xml_tree( self, show_deleted=False ):
        """Returns a parsed xml object of a history"""
        self.home()
        self.visit_page( 'history?as_xml=True&show_deleted=%s' % show_deleted )
        xml = self.last_page()
        tree = ElementTree.fromstring(xml)
        return tree
    def histories_as_xml_tree( self ):
        """Returns a parsed xml object of all histories"""
        self.home()
        self.visit_page( 'history/list_as_xml' )
        xml = self.last_page()
        tree = ElementTree.fromstring(xml)
        return tree
    def history_options( self, user=False, active_datasets=False, activatable_datasets=False, histories_shared_by_others=False ):
        """Mimics user clicking on history options link"""
        self.home()
        self.visit_page( "root/history_options" )
        if user:
            self.check_page_for_string( 'List</a> previously stored histories' )
            if active_datasets:
                self.check_page_for_string( 'Create</a> a new empty history' )
                self.check_page_for_string( 'Construct workflow</a> from current history' )
                self.check_page_for_string( 'Clone</a> current history' ) 
            self.check_page_for_string( 'Share</a> current history' )
            self.check_page_for_string( 'Change default permissions</a> for current history' )
            if histories_shared_by_others:
                self.check_page_for_string( 'List</a> histories shared with you by others' )
        if activatable_datasets:
            self.check_page_for_string( 'Show deleted</a> datasets in current history' )
        self.check_page_for_string( 'Rename</a> current history' )
        self.check_page_for_string( 'Delete</a> current history' )
        self.home()
    def new_history( self, name=None ):
        """Creates a new, empty history"""
        self.home()
        if name:
            self.visit_url( "%s/history_new?name=%s" % ( self.url, name ) )
        else:
            self.visit_url( "%s/history_new" % self.url )
        self.check_history_for_string('Your history is empty')
        self.home()
    def rename_history( self, id, old_name, new_name ):
        """Rename an existing history"""
        self.home()
        self.visit_page( "history/rename?id=%s&name=%s" %( id, new_name ) )
        check_str = 'History: %s renamed to: %s' % ( old_name, urllib.unquote( new_name ) )
        self.check_page_for_string( check_str )
        self.home()
    def set_history( self ):
        """Sets the history (stores the cookies for this run)"""
        if self.history_id:
            self.home()
            self.visit_page( "history?id=%s" % self.history_id )
        else:
            self.new_history()
        self.home()
    def share_current_history( self, email, check_str='', check_str_after_submit='', check_str_after_submit2='',
                               action='', action_check_str='', action_check_str_after_submit='' ):
        """Share the current history with different users"""
        self.visit_url( "%s/history/share" % self.url )
        if check_str:
            self.check_page_for_string( check_str )
        tc.fv( 'share', 'email', email )
        tc.submit( 'share_button' )
        if check_str_after_submit:
            self.check_page_for_string( check_str_after_submit )
        if check_str_after_submit2:
            self.check_page_for_string( check_str_after_submit2 )
        if action:
            # If we have an action, then we are sharing datasets with users that do not have access permissions on them
            if action_check_str:
                self.check_page_for_string( action_check_str )
            tc.fv( 'share_restricted', 'action', action )
            tc.submit( "share_restricted_button" )
            if action_check_str_after_submit:
                self.check_page_for_string( action_check_str_after_submit )
        self.home()
    def share_histories_with_users( self, ids, emails, check_str1='', check_str2='',
                                    check_str_after_submit='', action=None, action_check_str=None ):
        """Share one or more histories with one or more different users"""
        self.visit_url( "%s/history/list?id=%s&operation=Share" % ( self.url, ids ) )
        if check_str1:
            self.check_page_for_string( check_str1 )
        if check_str2:
            self.check_page_for_string( check_str2 )
        tc.fv( 'share', 'email', emails )
        tc.submit( 'share_button' )
        if check_str_after_submit:
            self.check_page_for_string( check_str_after_submit )
        if action:
            # If we have an action, then we are sharing datasets with users that do not have access permissions on them
            tc.fv( 'share_restricted', 'action', action )
            tc.submit( "share_restricted_button" )
            if action_check_str:
                self.check_page_for_string( action_check_str )
        self.home()
    def unshare_history( self, history_id, user_id, check_str1='', check_str2='', check_str_after_submit='' ):
        """Unshare a history that has been shared with another user"""
        self.visit_url( "%s/history/list?id=%s&operation=sharing" % ( self.url, history_id ) )
        if check_str1:
            self.check_page_for_string( check_str1 )
        if check_str2:
            self.check_page_for_string( check_str2 )
        self.visit_url( "%s/history/sharing?unshare_user=%s&id=%s" % ( self.url, user_id, history_id ) )
        self.home()
    def switch_history( self, id='', name='' ):
        """Switches to a history in the current list of histories"""
        self.visit_url( "%s/history/list?operation=switch&id=%s" % ( self.url, id ) )
        if name:
            self.check_history_for_string( name )
        self.home()
    def view_stored_active_histories( self, check_str='' ):
        self.home()
        self.visit_page( "history/list" )
        self.check_page_for_string( 'Stored histories' )
        self.check_page_for_string( '<input type="checkbox" name="id" value=' )
        self.check_page_for_string( 'operation=Rename&id' )
        self.check_page_for_string( 'operation=Switch&id' )
        self.check_page_for_string( 'operation=Delete&id' )
        if check_str:
            self.check_page_for_string( check_str )
        self.home()
    def view_stored_deleted_histories( self, check_str='' ):
        self.home()
        self.visit_page( "history/list?f-deleted=True" )
        self.check_page_for_string( 'Stored histories' )
        self.check_page_for_string( '<input type="checkbox" name="id" value=' )
        self.check_page_for_string( 'operation=Undelete&id' )
        if check_str:
            self.check_page_for_string( check_str )
        self.home()
    def view_shared_histories( self, check_str='', check_str2='' ):
        self.home()
        self.visit_page( "history/list_shared" )
        if check_str:
            self.check_page_for_string( check_str )
        if check_str2:
            self.check_page_for_string( check_str2 )
        self.home()
    def clone_history( self, history_id, clone_choice, check_str1='', check_str_after_submit='' ):
        self.home()
        self.visit_page( "history/clone?id=%s" % history_id )
        if check_str1:
            self.check_page_for_string( check_str1 )
        tc.fv( '1', 'clone_choice', clone_choice )
        tc.submit( 'clone_choice_button' )
        if check_str_after_submit:
            self.check_page_for_string( check_str_after_submit )
        self.home()
    def enable_import_via_link( self, history_id, check_str='', check_str_after_submit='' ):
        self.home()
        self.visit_page( "history/list?operation=sharing&id=%s" % history_id )
        if check_str:
            self.check_page_for_string( check_str )
        # twill barfs on this form, possibly because it contains no fields, but not sure.
        # In any case, we have to mimic the form submission
        self.home()
        self.visit_page( 'history/sharing?id=%s&enable_import_via_link=True' % history_id )
        if check_str_after_submit:
            self.check_page_for_string( check_str_after_submit )
        self.home()
    def disable_import_via_link( self, history_id, check_str='', check_str_after_submit='' ):
        self.home()
        self.visit_page( "history/list?operation=sharing&id=%s" % history_id )
        if check_str:
            self.check_page_for_string( check_str )
        # twill barfs on this form, possibly because it contains no fields, but not sure.
        # In any case, we have to mimic the form submission
        self.home()
        self.visit_page( 'history/sharing?id=%s&disable_import_via_link=True' % history_id )
        if check_str_after_submit:
            self.check_page_for_string( check_str_after_submit )
        self.home()
    def import_history_via_url( self, history_id, email, check_str_after_submit='' ):
        self.home()
        self.visit_page( "history/imp?&id=%s" % history_id )
        if check_str_after_submit:
            self.check_page_for_string( check_str_after_submit )
        self.home()

    # Functions associated with datasets (history items) and meta data
    def get_job_stderr( self, id ):
        self.visit_page( "dataset/stderr?id=%s" % id )
        return self.last_page()

    def _assert_dataset_state( self, elem, state ):
        if elem.get( 'state' ) != state:
            errmsg = "Expecting dataset state '%s', but state is '%s'. Dataset blurb: %s\n\n" % ( state, elem.get('state'), elem.text.strip() )
            errmsg += "---------------------- >> begin tool stderr << -----------------------\n"
            errmsg += self.get_job_stderr( elem.get( 'id' ) ) + "\n"
            errmsg += "----------------------- >> end tool stderr << ------------------------\n"
            raise AssertionError( errmsg )

    def check_metadata_for_string( self, patt, hid=None ):
        """Looks for 'patt' in the edit page when editing a dataset"""
        data_list = self.get_history_as_data_list()
        self.assertTrue( data_list )
        if hid is None: # take last hid
            elem = data_list[-1]
            hid = int( elem.get('hid') )
        self.assertTrue( hid )
        self.visit_page( "edit?hid=%d" % hid )
        for subpatt in patt.split():
            tc.find(subpatt)
    def delete_history_item( self, hda_id, check_str='' ):
        """Deletes an item from a history"""
        try:
            hda_id = int( hda_id )
        except:
            raise AssertionError, "Invalid hda_id '%s' - must be int" % hda_id
        self.visit_url( "%s/root/delete?show_deleted_on_refresh=False&id=%s" % ( self.url, hda_id ) )
        if check_str:
            self.check_page_for_string( check_str )
    def undelete_history_item( self, hda_id, check_str='' ):
        """Un-deletes a deleted item in a history"""
        try:
            hda_id = int( hda_id )
        except:
            raise AssertionError, "Invalid hda_id '%s' - must be int" % hda_id
        self.visit_url( "%s/dataset/undelete?id=%s" % ( self.url, hda_id ) )
        if check_str:
            self.check_page_for_string( check_str )
    def display_history_item( self, id, check_str='' ):
        """Displays a history item - simulates eye icon click"""
        self.visit_url( '%s/datasets/%s/display/index' % ( self.url, id ) )
        if check_str:
            self.check_page_for_string( check_str )
        self.home()
    def edit_hda_attribute_info( self, hda_id, new_name='', new_info='', new_dbkey='', new_startcol='' ):
        """Edit history_dataset_association attribute information"""
        self.home()
        self.visit_url( "%s/root/edit?id=%s" % ( self.url, hda_id ) )
        self.check_page_for_string( 'Edit Attributes' )
        if new_name:
            tc.fv( 'edit_attributes', 'name', new_name )
        if new_info:
            tc.fv( 'edit_attributes', 'info', new_info )
        if new_dbkey:
            tc.fv( 'edit_attributes', 'dbkey', new_dbkey )
        if new_startcol:
            tc.fv( 'edit_attributes', 'startCol', new_startcol )
        tc.submit( 'save' )
        self.check_page_for_string( 'Attributes updated' )
        self.home()
    def auto_detect_metadata( self, hda_id ):
        """Auto-detect history_dataset_association metadata"""
        self.home()
        self.visit_url( "%s/root/edit?id=%s" % ( self.url, hda_id ) )
        self.check_page_for_string( 'This will inspect the dataset and attempt' )
        tc.fv( 'auto_detect', 'id', hda_id )
        tc.submit( 'detect' )
        self.check_page_for_string( 'Attributes updated' )
        self.home()
    def convert_format( self, hda_id, target_type ):
        """Convert format of history_dataset_association"""
        self.home()
        self.visit_url( "%s/root/edit?id=%s" % ( self.url, hda_id ) )
        self.check_page_for_string( 'This will inspect the dataset and attempt' )
        tc.fv( 'convert_data', 'target_type', target_type )
        tc.submit( 'convert_data' )
        self.check_page_for_string( 'The file conversion of Convert BED to GFF on data' )
        self.home()
    def change_datatype( self, hda_id, datatype ):
        """Change format of history_dataset_association"""
        self.home()
        self.visit_url( "%s/root/edit?id=%s" % ( self.url, hda_id ) )
        self.check_page_for_string( 'This will change the datatype of the existing dataset but' )
        tc.fv( 'change_datatype', 'datatype', datatype )
        tc.submit( 'change' )
        self.check_page_for_string( 'Edit Attributes' )
        self.home()
    def copy_history_item( self, source_dataset_ids='', target_history_ids=[], all_target_history_ids=[],
                           deleted_history_ids=[] ):
        """Copy 1 or more history_dataset_associations to 1 or more histories"""
        self.home()
        self.visit_url( "%s/dataset/copy_datasets?source_dataset_ids=%s" % ( self.url, source_dataset_ids ) )
        self.check_page_for_string( 'Source History Items' )
        # Make sure all of users active histories are displayed
        for id in all_target_history_ids:
            self.check_page_for_string( id )
        # Make sure only active histories are displayed
        for id in deleted_history_ids:
            try:
                self.check_page_for_string( id )
                raise AssertionError, "deleted history id %d displayed in list of target histories" % id
            except:
                pass
        # Check each history to which we want to copy the item
        for id in target_history_ids:
            tc.fv( '1', 'target_history_ids', id )
        tc.submit( 'do_copy' )
        no_source_ids = len( source_dataset_ids.split( ',' ) )
        check_str = '%d datasets copied to %d histories.' % ( no_source_ids, len( target_history_ids ) )
        self.check_page_for_string( check_str )
        self.home()
    def get_hids_in_history( self ):
        """Returns the list of hid values for items in a history"""
        data_list = self.get_history_as_data_list()
        hids = []
        for elem in data_list:
            hid = elem.get('hid')
            hids.append(hid)
        return hids
    def get_hids_in_histories( self ):
        """Returns the list of hids values for items in all histories"""
        data_list = self.get_histories_as_data_list()
        hids = []
        for elem in data_list:
            hid = elem.get('hid')
            hids.append(hid)
        return hids
    def verify_dataset_correctness( self, filename, hid=None, wait=True ):
        """Verifies that the attributes and contents of a history item meet expectations"""
        if wait:
            self.wait() #wait for job to finish
        data_list = self.get_history_as_data_list()
        self.assertTrue( data_list )
        if hid is None: # take last hid
            elem = data_list[-1]
            hid = str( elem.get('hid') )
        else:
            hid = str( hid )
            elems = [ elem for elem in data_list if elem.get('hid') == hid ]
            self.assertTrue( len(elems) == 1 )
            elem = elems[0]
        self.assertTrue( hid )
        self._assert_dataset_state( elem, 'ok' )
        if self.is_zipped( filename ):
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
            local_name = self.get_filename( filename )
            temp_name = self.get_filename( 'temp_%s' % filename )
            self.home()
            self.visit_page( "display?hid=" + hid )
            data = self.last_page()
            file( temp_name, 'wb' ).write(data)
            try:
                self.files_diff( local_name, temp_name )
            except AssertionError, err:
                os.remove(temp_name)
                errmsg = 'History item %s different than expected, difference:\n' % hid
                errmsg += str( err )
                raise AssertionError( errmsg )
            os.remove(temp_name)

    def is_zipped( self, filename ):
        if not zipfile.is_zipfile( filename ):
            return False
        return True

    def is_binary( self, filename ):
        temp = open( temp_name, "U" )
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

    def verify_genome_build( self, dbkey='hg17' ):
        """Verifies that the last used genome_build at history id 'hid' is as expected"""
        data_list = self.get_history_as_data_list()
        self.assertTrue( data_list )
        elems = [ elem for elem in data_list ]
        elem = elems[-1]
        genome_build = elem.get('dbkey')
        self.assertTrue( genome_build == dbkey )

    # Functions associated with user accounts
    def create( self, email='test@bx.psu.edu', password='testuser' ):
        self.home()
        self.visit_page( "user/create?email=%s&password=%s&confirm=%s" % ( email, password, password ) )
        self.check_page_for_string( "Now logged in as %s" %email )
        self.home()
        # Make sure a new private role was created for the user
        self.visit_page( "user/set_default_permissions" )
        self.check_page_for_string( email )
        self.home()
    def user_set_default_permissions( self, permissions_out=[], permissions_in=[], role_id=2 ): # role.id = 2 is Private Role for test2@bx.psu.edu 
        # NOTE: Twill has a bug that requires the ~/user/permissions page to contain at least 1 option value 
        # in each select list or twill throws an exception, which is: ParseError: OPTION outside of SELECT
        # Due to this bug, we'll bypass visiting the page, and simply pass the permissions on to the 
        # /user/set_default_permissions method.
        url = "user/set_default_permissions?update_roles_button=Save&id=None"
        for po in permissions_out:
            key = '%s_out' % po
            url ="%s&%s=%s" % ( url, key, str( role_id ) )
        for pi in permissions_in:
            key = '%s_in' % pi
            url ="%s&%s=%s" % ( url, key, str( role_id ) )
        self.home()
        self.visit_url( "%s/%s" % ( self.url, url ) )
        self.last_page()
        self.check_page_for_string( 'Default new history permissions have been changed.' )
        self.home()
    def history_set_default_permissions( self, permissions_out=[], permissions_in=[], role_id=3 ): # role.id = 3 is Private Role for test3@bx.psu.edu 
        # NOTE: Twill has a bug that requires the ~/user/permissions page to contain at least 1 option value 
        # in each select list or twill throws an exception, which is: ParseError: OPTION outside of SELECT
        # Due to this bug, we'll bypass visiting the page, and simply pass the permissions on to the 
        # /user/set_default_permissions method.
        url = "root/history_set_default_permissions?update_roles_button=Save&id=None&dataset=True"
        for po in permissions_out:
            key = '%s_out' % po
            url ="%s&%s=%s" % ( url, key, str( role_id ) )
        for pi in permissions_in:
            key = '%s_in' % pi
            url ="%s&%s=%s" % ( url, key, str( role_id ) )
        self.home()
        self.visit_url( "%s/%s" % ( self.url, url ) )
        self.check_page_for_string( 'Default history permissions have been changed.' )
        self.home()
    def login( self, email='test@bx.psu.edu', password='testuser' ):
        # test@bx.psu.edu is configured as an admin user
        try:
            self.create( email=email, password=password )
        except:
            self.home()
            self.visit_page( "user/login?email=%s&password=%s" % ( email, password ) )
            self.check_page_for_string( "Now logged in as %s" %email )
            self.home()
    def logout( self ):
        self.home()
        self.visit_page( "user/logout" )
        self.check_page_for_string( "You are no longer logged in" )
        self.home()
    # Functions associated with browsers, cookies, HTML forms and page visits
    def check_page_for_string( self, patt ):
        """Looks for 'patt' in the current browser page"""
        page = self.last_page()
        for subpatt in patt.split():
            if page.find( patt ) == -1:
                errmsg = "TwillAssertionError: no match to '%s'" %patt
                raise AssertionError( errmsg )

    def clear_cookies( self ):
        tc.clear_cookies()

    def clear_form( self, form=0 ):
        """Clears a form"""
        tc.formclear(str(form))

    def home( self ):
        self.visit_url( self.url )

    def last_page( self ):
        return tc.browser.get_html()

    def load_cookies( self, file ):
        filename = self.get_filename(file)
        tc.load_cookies(filename)

    def reload_page( self ):
        tc.reload()
        tc.code(200)

    def show_cookies( self ):
        return tc.show_cookies()

    def showforms( self ):
        """Shows form, helpful for debugging new tests"""
        return tc.showforms()

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
        control_names = []
        for i, control in enumerate( f.controls ):
            print "control %d: %s" % ( i, str( control ) )
            try:
                #check if a repeat element needs to be added
                if control.name not in kwd and control.name.endswith( '_add' ):
                    #control name doesn't exist, could be repeat
                    repeat_startswith = control.name[0:-4]
                    if repeat_startswith and not [ c_name for c_name in control_names if c_name.startswith( repeat_startswith ) ] and [ c_name for c_name in kwd.keys() if c_name.startswith( repeat_startswith ) ]:
                        tc.submit( control.name )
                        return self.submit_form( form_no=form_no, button=button, **kwd )
                # Check for refresh_on_change attribute, submit a change if required
                if 'refresh_on_change' in control.attrs.keys():
                    changed = False
                    item_labels = [ item.attrs[ 'label' ] for item in control.get_items() if item.selected ] #For DataToolParameter, control.value is the HDA id, but kwd contains the filename.  This loop gets the filename/label for the selected values.
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
                        control = ClientForm.SubmitControl( 'SubmitControl', '___refresh_grouping___', {'name':'refresh_grouping'} )
                        control.add_to_form( f )
                        control.fixup()
                        # Submit for refresh
                        tc.submit( '___refresh_grouping___' )
                        return self.submit_form( form_no=form_no, button=button, **kwd )
            except Exception, e:
                log.debug( "In submit_form, continuing, but caught exception: %s" % str( e ) )
                continue
            control_names.append( control.name )
        # No refresh_on_change attribute found in current form, so process as usual
        for control_name, control_value in kwd.items():
            if not isinstance( control_value, list ):
                control_value = [ control_value ]
            try:
                control = f.find_control( name=control_name )
            except:
                # This assumes we always want the first control of the given name,
                # which may not be ideal...
                control = f.find_control( name=control_name, nr=0 )
            control.clear()
            if control.is_of_kind( "text" ):
                tc.fv( f.name, control.name, ",".join( control_value ) )
            elif control.is_of_kind( "list" ):
                try:
                    if control.is_of_kind( "multilist" ):
                        for elem in control_value:
                            control.get( name=elem ).selected = True
                    else: # control.is_of_kind( "singlelist" )
                        for elem in control_value:
                            tc.fv( f.name, control.name, str( elem ) )
                except Exception, exc:
                    errmsg = "Attempting to set field '%s' to value '%s' in form '%s' threw exception: %s\n" % ( control_name, str( control_value ), f.name, str( exc ) )
                    errmsg += "control: %s\n" % str( control )
                    errmsg += "If the above control is a DataToolparameter whose data type class does not include a sniff() method,\n"
                    errmsg += "make sure to include a proper 'ftype' attribute to the tag for the control within the <test> tag set.\n"
                    raise AssertionError( errmsg )
            else:
                # Add conditions for other control types here when necessary.
                pass
        tc.submit( button )

    def visit_page( self, page ):
        # tc.go("./%s" % page)
        if not page.startswith( "/" ):
            page = "/" + page 
        tc.go( self.url + page )
        tc.code( 200 )

    def visit_url( self, url ):
        tc.go("%s" % url)
        tc.code( 200 )

    """Functions associated with Galaxy tools"""
    def run_tool( self, tool_id, repeat_name=None, **kwd ):
        tool_id = tool_id.replace(" ", "+")
        """Runs the tool 'tool_id' and passes it the key/values from the *kwd"""
        self.visit_url( "%s/tool_runner/index?tool_id=%s" % (self.url, tool_id) )
        if repeat_name is not None:
            repeat_button = '%s_add' % repeat_name
            # Submit the "repeat" form button to add an input)
            tc.submit( repeat_button )
            print "button '%s' clicked" % repeat_button
        tc.find( 'runtool_btn' )
        self.submit_form( **kwd )

    def run_ucsc_main( self, track_params, output_params ):
        """Gets Data From UCSC"""
        tool_id = "ucsc_table_direct1"
        track_string = urllib.urlencode( track_params )
        galaxy_url = urllib.quote_plus( "%s/tool_runner/index?" % self.url )
        self.visit_url( "http://genome.ucsc.edu/cgi-bin/hgTables?GALAXY_URL=%s&hgta_compressType=none&tool_id=%s&%s" % ( galaxy_url, tool_id, track_string ) )
        tc.fv( "1","hgta_doTopSubmit", "get output" )
        self.submit_form( button="get output" )#, **track_params )
        tc.fv( "1","hgta_doGalaxyQuery", "Send query to Galaxy" )
        self.submit_form( button="Send query to Galaxy" )#, **output_params ) #AssertionError: Attempting to set field 'fbQual' to value '['whole']' in form 'None' threw exception: no matching forms! control: <RadioControl(fbQual=[whole, upstreamAll, endAll])>

    def wait( self, maxiter=20 ):
        """Waits for the tools to finish"""
        count = 0
        sleep_amount = 1
        self.home()
        while count < maxiter:
            count += 1
            self.visit_page( "history" )
            page = tc.browser.get_html()
            if page.find( '<!-- running: do not change this comment, used by TwillTestCase.wait -->' ) > -1:
                time.sleep( sleep_amount )
                sleep_amount += 1
            else:
                break
        self.assertNotEqual(count, maxiter)

    # Dataset Security stuff
    # Tests associated with users
    def create_new_account_as_admin( self, email='test4@bx.psu.edu', password='testuser' ):
        """Create a new account for another user"""
        self.home()
        self.visit_url( "%s/admin/create_new_user?email=%s&password=%s&confirm=%s&user_create_button=%s" \
                        % ( self.url, email, password, password, 'Create' ) )
        try:
            self.check_page_for_string( "Created new user account" )
            previously_created = False
        except:
            # May have created the account in a previous test run...
            self.check_page_for_string( "User with that email already exists" )
            previously_created = True
        self.home()
        return previously_created
    def reset_password_as_admin( self, user_id=4, password='testreset' ):
        """Reset a user password"""
        self.home()
        self.visit_url( "%s/admin/reset_user_password?user_id=%s" % ( self.url, str( user_id ) ) )
        tc.fv( "1", "password", password )
        tc.fv( "1", "confirm", password )
        tc.submit( "reset_user_password_button" )
        self.check_page_for_string( "Password reset" )
        self.home()
    def mark_user_deleted( self, user_id=4, email='' ):
        """Mark a user as deleted"""
        self.home()
        self.visit_url( "%s/admin/mark_user_deleted?user_id=%s" % ( self.url, str( user_id ) ) )
        check_str = "User '%s' has been marked as deleted." % email
        self.check_page_for_string( check_str )
        self.home()
    def undelete_user( self, user_id=4, email='' ):
        """Undelete a user"""
        self.home()
        self.visit_url( "%s/admin/undelete_user?user_id=%s" % ( self.url, user_id ) )
        check_str = "User '%s' has been marked as not deleted" % email
        self.check_page_for_string( check_str )
        self.home()
    def purge_user( self, user_id, email ):
        """Purge a user account"""
        self.home()
        self.visit_url( "%s/admin/purge_user?user_id=%s" % ( self.url, user_id ) )
        check_str = "User '%s' has been marked as purged." % email
        self.check_page_for_string( check_str )
        self.home()
    def associate_roles_and_groups_with_user( self, user_id, email,
                                              in_role_ids=[], out_role_ids=[],
                                              in_group_ids=[], out_group_ids=[],
                                              check_str='' ):
        self.home()
        url = "%s/admin/user?user_id=%s&user_roles_groups_edit_button=Save" % ( self.url, user_id )
        if in_role_ids:
            url += "&in_roles=%s" % ','.join( in_role_ids )
        if out_role_ids:
            url += "&out_roles=%s" % ','.join( out_role_ids )
        if in_group_ids:
            url += "&in_groups=%s" % ','.join( in_group_ids )
        if out_group_ids:
            url += "&out_groups=%s" % ','.join( out_group_ids )
        self.visit_url( url )
        if check_str:
            self.check_page_for_string( check_str )
        self.home()

    # Tests associated with roles
    def create_role( self, name='Role One', description="This is Role One", in_user_ids=[], in_group_ids=[], create_group_for_role='no', private_role='' ):
        """Create a new role"""
        url = "%s/admin/create_role?create_role_button=Save&name=%s&description=%s" % ( self.url, name.replace( ' ', '+' ), description.replace( ' ', '+' ) )
        if in_user_ids:
            url += "&in_users=%s" % ','.join( in_user_ids )
        if in_group_ids:
            url += "&in_groups=%s" % ','.join( in_group_ids )
        if create_group_for_role == 'yes':
            url += '&create_group_for_role=yes'
        self.home()
        self.visit_url( url )
        if create_group_for_role == 'yes':
            check_str = "Group '%s' has been created, and role '%s' has been created with %d associated users and %d associated groups" % \
                ( name, name, len( in_user_ids ), len( in_group_ids ) )
        else:
            check_str = "Role '%s' has been created with %d associated users and %d associated groups" % \
                ( name, len( in_user_ids ), len( in_group_ids ) ) 
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
        self.home()
        self.visit_url( "%s/admin/roles" % self.url )
        self.check_page_for_string( name )
        self.home()
    def rename_role( self, role_id, name='Role One Renamed', description='This is Role One Re-described' ):
        """Rename a role"""
        self.home()
        self.visit_url( "%s/admin/role?rename=True&role_id=%s" % ( self.url, role_id ) )
        self.check_page_for_string( 'Change role name and description' )
        tc.fv( "1", "name", name )
        tc.fv( "1", "description", description )
        tc.submit( "rename_role_button" )
        self.home()
    def mark_role_deleted( self, role_id, role_name ):
        """Mark a role as deleted"""
        self.home()
        self.visit_url( "%s/admin/mark_role_deleted?role_id=%s" % ( self.url, role_id ) )
        check_str = "Role '%s' has been marked as deleted" % role_name
        self.check_page_for_string( check_str )
        self.home()
    def undelete_role( self, role_id, role_name ):
        """Undelete an existing role"""
        self.home()
        self.visit_url( "%s/admin/undelete_role?role_id=%s" % ( self.url, role_id ) )
        check_str = "Role '%s' has been marked as not deleted" % role_name
        self.check_page_for_string( check_str )
        self.home()
    def purge_role( self, role_id, role_name ):
        """Purge an existing role"""
        self.home()
        self.visit_url( "%s/admin/purge_role?role_id=%s" % ( self.url, role_id ) )
        check_str = "The following have been purged from the database for role '%s': " % role_name
        check_str += "DefaultUserPermissions, DefaultHistoryPermissions, UserRoleAssociations, GroupRoleAssociations, DatasetPermissionss."
        self.check_page_for_string( check_str )
        self.home()
    def associate_users_and_groups_with_role( self, role_id, role_name, user_ids=[], group_ids=[] ):
        self.home()
        url = "%s/admin/role?role_id=%s&role_members_edit_button=Save" % ( self.url, role_id )
        if user_ids:
            url += "&in_users=%s" % ','.join( user_ids )
        if group_ids:
            url += "&in_groups=%s" % ','.join( group_ids )
        self.visit_url( url )
        check_str = "Role '%s' has been updated with %d associated users and %d associated groups" % ( role_name, len( user_ids ), len( group_ids ) )
        self.check_page_for_string( check_str )
        self.home()

    # Tests associated with groups
    def create_group( self, name='Group One', in_user_ids=[], in_role_ids=[] ):
        """Create a new group"""
        url = "%s/admin/create_group?create_group_button=Save&name=%s" % ( self.url, name.replace( ' ', '+' ) )
        if in_user_ids:
            url += "&in_users=%s" % ','.join( in_user_ids )
        if in_role_ids:
            url += "&in_roles=%s" % ','.join( in_role_ids )
        self.home()
        self.visit_url( url )
        check_str = "Group '%s' has been created with %d associated users and %d associated roles" % ( name, len( in_user_ids ), len( in_role_ids ) ) 
        self.check_page_for_string( check_str )
        self.home()
        self.visit_url( "%s/admin/groups" % self.url )
        self.check_page_for_string( name )
        self.home()
    def rename_group( self, group_id, name='Group One Renamed' ):
        """Rename a group"""
        self.home()
        self.visit_url( "%s/admin/group?rename=True&group_id=%s" % ( self.url, group_id ) )
        self.check_page_for_string( 'Change group name' )
        tc.fv( "1", "name", name )
        tc.submit( "rename_group_button" )
        self.home()
    def associate_users_and_roles_with_group( self, group_id, group_name, user_ids=[], role_ids=[] ):
        self.home()
        url = "%s/admin/group?group_id=%s&group_roles_users_edit_button=Save" % ( self.url, group_id )
        if user_ids:
            url += "&in_users=%s" % ','.join( user_ids )
        if role_ids:
            url += "&in_roles=%s" % ','.join( role_ids )
        self.visit_url( url )
        check_str = "Group '%s' has been updated with %d associated roles and %d associated users" % ( group_name, len( role_ids ), len( user_ids ) )
        self.check_page_for_string( check_str )
        self.home()
    def mark_group_deleted( self, group_id, group_name ):
        """Mark a group as deleted"""
        self.home()
        self.visit_url( "%s/admin/mark_group_deleted?group_id=%s" % ( self.url, group_id ) )
        check_str = "Group '%s' has been marked as deleted" % group_name
        self.check_page_for_string( check_str )
        self.home()
    def undelete_group( self, group_id, group_name ):
        """Undelete an existing group"""
        self.home()
        self.visit_url( "%s/admin/undelete_group?group_id=%s" % ( self.url, group_id ) )
        check_str = "Group '%s' has been marked as not deleted" % group_name
        self.check_page_for_string( check_str )
        self.home()
    def purge_group( self, group_id, group_name ):
        """Purge an existing group"""
        self.home()
        self.visit_url( "%s/admin/purge_group?group_id=%s" % ( self.url, group_id ) )
        check_str = "The following have been purged from the database for group '%s': UserGroupAssociations, GroupRoleAssociations." % group_name
        self.check_page_for_string( check_str )
        self.home()

    # Library stuff
    def create_library( self, name='Library One', description='This is Library One' ):
        """Create a new library"""
        self.home()
        self.visit_url( "%s/admin/library?new=True" % self.url )
        self.check_page_for_string( 'Create a new library' )
        tc.fv( "1", "1", name ) # form field 1 is the field named name...
        tc.fv( "1", "2", description ) # form field 1 is the field named name...
        tc.submit( "create_library_button" )
        self.home()
    def set_library_permissions( self, library_id, library_name, role_id, permissions_in, permissions_out ):
        url = "admin/library?id=%s&permissions=True&update_roles_button=Save" % ( library_id )
        for po in permissions_out:
            key = '%s_out' % po
            url ="%s&%s=%s" % ( url, key, str( role_id ) )
        for pi in permissions_in:
            key = '%s_in' % pi
            url ="%s&%s=%s" % ( url, key, str( role_id ) )
        self.home()
        self.visit_url( "%s/%s" % ( self.url, url ) )
        check_str = "Permissions updated for library '%s'" % library_name
        self.check_page_for_string( check_str )
        self.home()
    def rename_library( self, library_id, old_name, name='Library One Renamed', description='This is Library One Re-described' ):
        """Rename a library"""
        self.home()
        self.visit_url( "%s/admin/library?information=True&id=%s" % ( self.url, library_id ) )
        self.check_page_for_string( 'Change library name and description' )
        # Since twill barfs on the form submisson, we ar forced to simulate it
        url = "%s/admin/library?information=True&id=%s&rename_library_button=Save&description=%s&name=%s" % \
        ( self.url, library_id, description.replace( ' ', '+' ), name.replace( ' ', '+' ) )
        self.home()
        self.visit_url( url )
        check_str = "Library '%s' has been renamed to '%s'" % ( old_name, name )
        self.check_page_for_string( check_str )
        self.home()
    def add_library_info_template( self, library_id, library_name, num_fields='2', name='Library Template 1', ele_name_0='Foo', ele_name_1='Doh' ):
        """Add a new info template to a library"""
        self.home()
        url = "%s/admin/info_template?library_id=%s&new_template=True&num_fields=2&create_info_template_button=Go" % ( self.url, library_id )
        self.visit_url( url )
        check_str = "Create a new information template for library '%s'" % library_name
        self.check_page_for_string ( check_str )
        tc.fv( '1', 'library_id', library_id )
        tc.fv( '1', 'set_num_fields', num_fields )
        tc.fv( '1', 'name', name )
        tc.fv( '1', 'new_element_name_0', ele_name_0 )
        tc.fv( '1', 'new_element_name_1', ele_name_1 )
        tc.submit( 'new_info_template_button' )
        self.check_page_for_string( 'The new information template has been created.' )
        self.home()
    def add_library_info_template_element( self, library_id, template_id, template_name,
                                           ele_field_name_1, ele_name_1,
                                           ele_field_desc_1, ele_desc_1,
                                           ele_field_name_2, ele_name_2,
                                           ele_field_desc_2, ele_desc_2,
                                           new_ele_name='Fubar', new_ele_desc='This is the Fubar compnent' ):
        """Add a new element to an existing library info template"""
        self.home()
        url = "%s/admin/info_template?library_id=%s&id=%s&edit_template=True&num_fields=1&edit_info_template_button=Save" % \
            ( self.url, library_id, template_id )
        self.visit_url( url )
        check_str = "Edit template '%s'" % template_name
        self.check_page_for_string ( check_str )
        tc.fv( '1', 'id', template_id )
        tc.fv( '1', 'set_num_fields', '0' )
        tc.fv( '1', 'name', template_name )
        tc.fv( '1', ele_field_name_1, ele_name_1 )
        tc.fv( '1', ele_field_desc_1, ele_desc_1 )
        tc.fv( '1', ele_field_name_2, ele_name_2 )
        tc.fv( '1', ele_field_desc_2, ele_desc_2 )
        tc.fv( '1', 'new_element_name_0', new_ele_name )
        tc.fv( '1', 'new_element_description_0', new_ele_desc )
        tc.submit( 'edit_info_template_button' )
        check_str = "Information template '%s' has been updated" % template_name
        self.check_page_for_string( check_str )
        self.home()
    def edit_library_info( self, library_id, library_name, ele_1_field_name, ele_1_contents, ele_2_field_name, ele_2_contents ):
        """Add information to a library using an existing template with 2 elements"""
        self.home()
        self.visit_url( "%s/admin/library?information=True&id=%s" % ( self.url, library_id ) )
        check_str = 'Other information about library %s' % library_name
        self.check_page_for_string( check_str )
        tc.fv( '2', ele_1_field_name, ele_1_contents )
        tc.fv( '2', ele_2_field_name, ele_2_contents )
        tc.submit( 'create_new_info_button' )
        self.home()
    def edit_library_info_template( self, library_id, id, name, ele_name_1, name_1,
                                    ele_desc_1, desc_1, ele_name_2, name_2, ele_desc_2, desc_2 ):
        """Edit an existing library info template"""
        self.home()
        url = "%s/admin/info_template?library_id=%s&id=%s&edit_template=True" % ( self.url, library_id, id )
        self.visit_url( url )
        self.check_page_for_string ( 'Edit template' )
        tc.fv( '1', 'id', id )
        tc.fv( '1', 'set_num_fields', '0' )
        tc.fv( '1', 'name', name )
        tc.fv( '1', ele_name_1, name_1 )
        tc.fv( '1', ele_desc_1, desc_1 )
        tc.fv( '1', ele_name_2, name_2 )
        tc.fv( '1', ele_desc_2, desc_2 )
        tc.submit( 'edit_info_template_button' )
        check_str = "Information template '%s' has been updated" % name
        self.check_page_for_string( check_str )
        self.home()
    def add_folder_info_template( self, library_id, library_name, folder_id, folder_name, num_fields='2',
                                  name='Folder Template 1', ele_name_0='Fu', ele_help_0='', ele_name_1='Bar', ele_help_1='' ):
        """Add a new info template to a folder"""
        self.home()
        url = "%s/admin/info_template?library_id=%s&folder_id=%s&new_template=True&num_fields=2&create_info_template_button=Go" % \
            ( self.url, library_id, folder_id )
        self.home()
        self.visit_url( url )
        check_str = "Create a new information template for folder '%s'" % folder_name
        self.check_page_for_string ( check_str ) 
        tc.fv( '1', 'library_id', library_id )
        tc.fv( '1', 'folder_id', folder_id )
        tc.fv( '1', 'set_num_fields', num_fields )
        tc.fv( '1', 'name', name )
        tc.fv( '1', 'new_element_name_0', ele_name_0 )
        tc.fv( '1', 'new_element_description_0', ele_help_0.replace( '+', ' ' ) )
        tc.fv( '1', 'new_element_name_1', ele_name_1 )
        tc.fv( '1', 'new_element_description_1', ele_help_1.replace( '+', ' ' ) )
        tc.submit( 'new_info_template_button' )
        self.home()
    def add_folder( self, library_id, folder_id, name='Folder One', description='NThis is Folder One' ):
        """Create a new folder"""
        self.home()
        self.visit_url( "%s/admin/folder?library_id=%s&id=%s&new=True" % ( self.url, library_id, folder_id ) )
        self.check_page_for_string( 'Create a new folder' )
        tc.fv( "1", "name", name ) # form field 1 is the field named name...
        tc.fv( "1", "description", description ) # form field 2 is the field named description...
        tc.submit( "new_folder_button" )
        self.home()
    def rename_folder( self, library_id, folder_id, old_name, name='Folder One Renamed', description='This is Folder One Re-described' ):
        """Rename a Folder"""
        self.home()
        self.visit_url( "%s/admin/folder?library_id=%s&manage=True&id=%s" % ( self.url, library_id, folder_id ) )
        self.check_page_for_string( 'Edit folder name and description' )
        # Since twill barfs on the form submisson, we ar forced to simulate it
        url = "%s/admin/folder?library_id=%s&manage=True&id=%s&rename_folder_button=Save&description=%s&name=%s" % \
        ( self.url, library_id, folder_id, description.replace( ' ', '+' ), name.replace( ' ', '+' ) )
        self.home()
        self.visit_url( url )
        check_str = "Folder '%s' has been renamed to '%s'" % ( old_name, name )
        self.check_page_for_string( check_str )
        self.home()
    def add_library_dataset( self, filename, library_id, folder_id, folder_name, file_format='auto',
                             dbkey='hg18', roles=[], message='', root=False, check_template_str1='', check_template_str2='',
                             check_template_str3='' ):
        """Add a dataset to a folder"""
        filename = self.get_filename( filename )
        self.home()
        self.visit_url( "%s/admin/library_dataset_dataset_association?upload_option=upload_file&library_id=%s&folder_id=%s&message=%s" % \
                        ( self.url, library_id, folder_id, message ) )
        self.check_page_for_string( 'Upload files' )
        # If we've been sent some template labels, make sure they are included in the upload form
        if check_template_str1:
            self.check_page_for_string( check_template_str1 )
        if check_template_str2:
            self.check_page_for_string( check_template_str2 )
        if check_template_str3:
            self.check_page_for_string( check_template_str3 )
        tc.fv( "1", "folder_id", folder_id )
        tc.formfile( "1", "file_data", filename )
        tc.fv( "1", "file_format", file_format )
        tc.fv( "1", "dbkey", dbkey )
        tc.fv( "1", "message", message.replace( '+', ' ' ) )
        for role_id in roles:
            tc.fv( "1", "roles", role_id ) # form field 7 is the select list named out_groups, note the buttons...
        tc.submit( "new_dataset_button" )
        if root:
            check_str = "Added 1 datasets to the library '%s' ( each is selected )." % folder_name
        else:
            check_str = "Added 1 datasets to the folder '%s' ( each is selected )." % folder_name
        self.check_page_for_string( check_str )
        self.home()
    def set_library_dataset_permissions( self, library_id, folder_id, ldda_id, ldda_name, role_id, permissions_in, permissions_out ):
        url = "admin/library_dataset_dataset_association?library_id=%s&folder_id=%s&&id=%s&permissions=True&update_roles_button=Save" % \
            ( library_id, folder_id, ldda_id )
        #role_ids = util.listify( role_ids )
        #for role_id in role_ids:
        for po in permissions_out:
            key = '%s_out' % po
            url ="%s&%s=%s" % ( url, key, str( role_id ) )
        for pi in permissions_in:
            key = '%s_in' % pi
            url ="%s&%s=%s" % ( url, key, str( role_id ) )
        self.home()
        self.visit_url( "%s/%s" % ( self.url, url ) )
        check_str = "Permissions updated for dataset '%s'" % ldda_name
        self.check_page_for_string( check_str )
        self.home()
    def edit_ldda_template_element_info( self, library_id, folder_id, ldda_id, ldda_name, ele_1_field_name, 
                        ele_1_contents, ele_2_field_name, ele_2_contents, ele_1_help='', ele_2_help='',
                        ele_3_field_name='', ele_3_contents='', ele_3_help='' ):
        """Edit library_dataset_dataset_association template element information"""
        self.home()
        self.visit_url( "%s/admin/library_dataset_dataset_association?edit_info=True&library_id=%s&folder_id=%s&id=%s" % \
                        ( self.url, library_id, folder_id, ldda_id ) )        
        check_str = 'Edit attributes of %s' % ldda_name
        self.check_page_for_string( check_str )
        ele_1_contents = ele_1_contents.replace( '+', ' ' )
        ele_2_contents = ele_2_contents.replace( '+', ' ' )
        tc.fv( '4', ele_1_field_name, ele_1_contents )
        tc.fv( '4', ele_2_field_name, ele_2_contents.replace( '+', ' ' ) )
        if ele_3_field_name and ele_3_contents:
            ele_3_contents = ele_3_contents.replace( '+', ' ' )
            tc.fv( '4', ele_3_field_name, ele_3_contents )
        tc.submit( 'edit_info_button' )
        self.check_page_for_string( 'This is the latest version of this library dataset' )
        self.check_page_for_string( 'The information has been updated.' )
        self.check_page_for_string( ele_1_contents )
        self.check_page_for_string( ele_2_contents )
        if ele_3_field_name and ele_3_contents:
            self.check_page_for_string( ele_3_contents )
        if ele_1_help:
            check_str = ele_1_help.replace( '+', ' ' )
            self.check_page_for_string( check_str )
        self.check_page_for_string( ele_2_contents )
        if ele_2_help:
            check_str = ele_2_help.replace( '+', ' ' )
            self.check_page_for_string( check_str )
        if ele_2_help:
            check_str = ele_3_help.replace( '+', ' ' )
            self.check_page_for_string( check_str )
        self.home()
    def edit_ldda_attribute_info( self, library_id, folder_id, ldda_id, ldda_name, new_ldda_name ):
        """Edit library_dataset_dataset_association attribute information"""
        self.home()
        self.visit_url( "%s/admin/library_dataset_dataset_association?edit_info=True&library_id=%s&folder_id=%s&id=%s" % \
                        ( self.url, library_id, folder_id, ldda_id ) )
        check_str = 'Edit attributes of %s' % ldda_name
        self.check_page_for_string( check_str )
        tc.fv( '1', 'name', new_ldda_name )
        tc.submit( 'save' )
        check_str = 'Attributes updated for library dataset %s' % new_ldda_name
        self.check_page_for_string( check_str )
        check_str = 'Edit attributes of %s' % new_ldda_name
        self.check_page_for_string( check_str )
        self.home()
    def upload_new_dataset_version( self, filename, library_id, folder_id, folder_name, library_dataset_id, ldda_name, file_format='auto',
                                    dbkey='hg18', message='', check_template_str1='', check_template_str2='', check_template_str3='' ):
        """Upload new version(s) of a dataset"""
        self.home()
        filename = self.get_filename( filename )      
        self.visit_url( "%s/admin/library_dataset_dataset_association?upload_option=upload_file&library_id=%s&folder_id=%s&replace_id=%s&message=%s" % \
                        ( self.url, library_id, folder_id, library_dataset_id, message ) )
        self.check_page_for_string( 'Upload files' )
        self.check_page_for_string( 'You are currently selecting a new file to replace' )
        self.check_page_for_string( ldda_name )
        # If we've been sent some template labels, make sure they are included in the upload form
        if check_template_str1:
            self.check_page_for_string( check_template_str1 )
        if check_template_str2:
            self.check_page_for_string( check_template_str2 )
        if check_template_str3:
            self.check_page_for_string( check_template_str3 )
        tc.formfile( "1", "file_data", filename )
        tc.fv( "1", "file_format", file_format )
        tc.fv( "1", "dbkey", dbkey )
        tc.fv( "1", "message", message.replace( '+', ' ' ) )
        tc.submit( "new_dataset_button" )
        check_str = "Added 1 dataset versions to the library dataset '%s' in the folder '%s'." % ( ldda_name, folder_name )
        self.check_page_for_string( check_str )
        self.home()
    def upload_new_dataset_versions( self, library_id, folder_id, folder_name, library_dataset_id, ldda_name, file_format='auto',
                                    dbkey='hg18', message='', check_template_str1='', check_template_str2='', check_template_str3='' ):
        """Upload new version(s) of a dataset using a directory of files"""
        self.home()
        self.visit_url( "%s/admin/library_dataset_dataset_association?upload_option=upload_directory&library_id=%s&folder_id=%s&replace_id=%s" \
                        % ( self.url, library_id, folder_id, library_dataset_id ) )
        self.check_page_for_string( 'Upload a directory of files' )
        self.check_page_for_string( 'You are currently selecting a new file to replace' )
        # If we've been sent some template labels, make sure they are included in the upload form
        if check_template_str1:
            self.check_page_for_string( check_template_str1 )
        if check_template_str2:
            self.check_page_for_string( check_template_str2 )
        if check_template_str3:
            self.check_page_for_string( check_template_str3 )
        tc.fv( "1", "file_format", file_format )
        tc.fv( "1", "dbkey", dbkey )
        tc.fv( "1", "message", message.replace( '+', ' ' ) )
        tc.fv( "1", "server_dir", "library" )
        tc.submit( "new_dataset_button" )
        check_str = "Added 3 dataset versions to the library dataset '%s' in the folder '%s'." % ( ldda_name, folder_name )
        self.check_page_for_string( check_str )
        self.home()
    def add_history_datasets_to_library( self, library_id, folder_id, folder_name, hda_id, root=False ):
        """Copy a dataset from the current history to a library folder"""
        self.home()
        self.visit_url( "%s/admin/add_history_datasets_to_library?library_id=%s&folder_id=%s&hda_ids=%s&add_history_datasets_to_library_button=Add+selected+datasets" % \
                        ( self.url, library_id, folder_id, hda_id ) )
        if root:
            check_str = "Added 1 datasets to the library '%s' ( each is selected )." % folder_name
        else:
            check_str = "Added 1 datasets to the folder '%s' ( each is selected )." % folder_name
        self.check_page_for_string( check_str )
        self.home()
    def add_dir_of_files_from_admin_view( self, library_id, folder_id, file_format='auto', dbkey='hg18', roles_tuple=[],
                                          message='', check_str_after_submit='', check_str1='', check_str2='', check_str3='' ):
        """Add a directory of datasets to a folder"""
        # roles is a list of tuples: [ ( role_id, role_description ) ]
        self.home()
        self.visit_url( "%s/admin/library_dataset_dataset_association?upload_option=upload_directory&library_id=%s&folder_id=%s" % ( self.url, library_id, folder_id ) )
        self.check_page_for_string( 'Upload a directory of files' )
        # If we've been sent some template labels, make sure they are included in the upload form
        if check_str1:
            self.check_page_for_string( check_str1 )
        if check_str2:
            self.check_page_for_string( check_str2 )
        if check_str3:
            self.check_page_for_string( check_str3 )
        tc.fv( "1", "folder_id", folder_id )
        tc.fv( "1", "file_format", file_format )
        tc.fv( "1", "dbkey", dbkey )
        tc.fv( "1", "message", message.replace( '+', ' ' ) )
        tc.fv( "1", "server_dir", "library" )
        for role_tuple in roles_tuple:
            tc.fv( "1", "roles", role_tuple[1] ) # role_tuple[1] is the role name
        tc.submit( "new_dataset_button" )
        if check_str_after_submit:
            self.check_page_for_string( check_str_after_submit )
        self.home()
    def add_dir_of_files_from_libraries_view( self, library_id, folder_id, selected_dir, file_format='auto', dbkey='hg18', roles_tuple=[],
                                              message='', check_str_after_submit='', check_str1='', check_str2='', check_str3='' ):
        """Add a directory of datasets to a folder"""
        # roles is a list of tuples: [ ( role_id, role_description ) ]
        self.home()
        self.visit_url( "%s/library/library_dataset_dataset_association?upload_option=upload_directory&library_id=%s&folder_id=%s" % ( self.url, library_id, folder_id ) )
        self.check_page_for_string( 'Upload a directory of files' )
        # If we've been sent some template labels, make sure they are included in the upload form
        if check_str1:
            self.check_page_for_string( check_str1 )
        if check_str2:
            self.check_page_for_string( check_str2 )
        if check_str3:
            self.check_page_for_string( check_str3 )
        tc.fv( "1", "folder_id", folder_id )
        tc.fv( "1", "file_format", file_format )
        tc.fv( "1", "dbkey", dbkey )
        tc.fv( "1", "message", message.replace( '+', ' ' ) )
        tc.fv( "1", "server_dir", selected_dir )
        for role_tuple in roles_tuple:
            tc.fv( "1", "roles", role_tuple[1] ) # role_tuple[1] is the role name
        tc.submit( "new_dataset_button" )
        if check_str_after_submit:
            self.check_page_for_string( check_str_after_submit )
        self.home()
    def delete_library_item( self, library_id, library_item_id, library_item_name, library_item_type='library_dataset' ):
        """Mark a library item as deleted"""
        self.home()
        self.visit_url( "%s/admin/delete_library_item?library_id=%s&library_item_id=%s&library_item_type=%s" \
                        % ( self.url, library_id, library_item_id, library_item_type ) )
        if library_item_type == 'library_dataset':
            library_item_desc = 'Dataset'
        else:
            library_item_desc = library_item_type.capitalize()
        check_str = "%s '%s' has been marked deleted" % ( library_item_desc, library_item_name )
        self.check_page_for_string( check_str )
        self.home()
    def undelete_library_item( self, library_id, library_item_id, library_item_name, library_item_type='library_dataset' ):
        """Mark a library item as deleted"""
        self.home()
        self.visit_url( "%s/admin/undelete_library_item?library_id=%s&library_item_id=%s&library_item_type=%s" \
                        % ( self.url, library_id, library_item_id, library_item_type ) )
        if library_item_type == 'library_dataset':
            library_item_desc = 'Dataset'
        else:
            library_item_desc = library_item_type.capitalize()
        check_str = "%s '%s' has been marked undeleted" % ( library_item_desc, library_item_name )
        self.check_page_for_string( check_str )
        self.home()
    def purge_library( self, library_id, library_name ):
        """Purge a library"""
        self.home()
        self.visit_url( "%s/admin/purge_library?id=%s" % ( self.url, library_id ) )
        check_str = "Library '%s' and all of its contents have been purged" % library_name
        self.check_page_for_string( check_str )
        self.home()
