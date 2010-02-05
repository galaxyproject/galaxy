import pkg_resources
pkg_resources.require( "twill==0.9" )

import StringIO, os, sys, random, filecmp, time, unittest, urllib, logging, difflib, tarfile, zipfile, tempfile, re, shutil
from itertools import *

import twill
import twill.commands as tc
from twill.other_packages._mechanize_dist import ClientForm
pkg_resources.require( "elementtree" )
from elementtree import ElementTree
from galaxy.web import security
from galaxy.web.framework.helpers import iff

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
    def files_diff( self, file1, file2, sort=False ):
        """Checks the contents of 2 files for differences"""
        if not filecmp.cmp( file1, file2 ):
            files_differ = False
            local_file = open( file1, 'U' ).readlines()
            history_data = open( file2, 'U' ).readlines()
            if sort:
                history_data.sort()
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
                    # PDF files contain creation dates, modification dates, ids and descriptions that change with each
                    # new file, so we need to handle these differences.  As long as the rest of the PDF file does
                    # not differ we're ok.
                    valid_diff_strs = [ 'description', 'createdate', 'creationdate', 'moddate', 'id' ]
                    valid_diff = False
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
                                # Print out diff_slice so we can see what failed
                                print "###### diff_slice ######"
                                raise AssertionError( "".join( diff_slice ) )
                                break
                else:
                    for line in diff_slice:
                        for char in line:
                            if ord( char ) > 128:
                                raise AssertionError( "Binary data detected, not displaying diff" )
                    raise AssertionError( "".join( diff_slice ) )

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
        self.visit_url( "%s/tool_runner?tool_id=upload1" % self.url )
        try: 
            tc.fv("1","file_type", ftype)
            tc.fv("1","dbkey", dbkey)
            tc.formfile("1","file_data", filename)
            tc.submit("runtool_btn")
            self.home()
        except AssertionError, err:
            errmsg = "Uploading file resulted in the following exception.  Make sure the file (%s) exists.  " % filename
            errmsg += str( err )
            raise AssertionError( errmsg )
        # Make sure every history item has a valid hid
        hids = self.get_hids_in_history()
        for hid in hids:
            try:
                valid_hid = int( hid )
            except:
                raise AssertionError, "Invalid hid (%s) created when uploading file %s" % ( hid, filename )
        # Wait for upload processing to finish (TODO: this should be done in each test case instead)
        self.wait()
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
        # Wait for upload processing to finish (TODO: this should be done in each test case instead)
        self.wait()
    def upload_composite_datatype_file( self, ftype, ped_file='', map_file='', bim_file='', bed_file='', fam_file='', dbkey='unspecified (?)', base_name='rgenetics' ):
        """Tests uploading either of 2 different composite data types ( lped and pbed )"""
        self.visit_url( "%s/tool_runner/index?tool_id=upload1" % self.url )
        # Handle refresh_on_change
        self.refresh_form( "file_type", ftype )
        tc.fv( "1", "dbkey", dbkey )
        tc.fv( "1", "files_metadata|base_name", base_name )
        if ftype == 'lped':
            # lped data types include a ped_file and a map_file
            ped_file = self.get_filename( ped_file )
            tc.formfile( "1", "files_0|file_data", ped_file )
            map_file = self.get_filename( map_file )
            tc.formfile( "1", "files_1|file_data", map_file )
        elif ftype == 'pbed':
            # pbed data types include a bim_file, a bed_file and a fam_file
            bim_file = self.get_filename( bim_file )
            tc.formfile( "1", "files_0|file_data", bim_file )
            bed_file = self.get_filename( bed_file )
            tc.formfile( "1", "files_1|file_data", bed_file )
            fam_file = self.get_filename( fam_file )
            tc.formfile( "1", "files_2|file_data", fam_file )
        else:
            raise AssertionError, "Unsupported composite data type (%s) received, currently only lped and pbed data types are supported." % ftype
        tc.submit( "runtool_btn" )
        self.check_page_for_string( 'The following job has been succesfully added to the queue:' )
        check_str = 'Uploaded Composite Dataset (%s)' % ftype
        self.check_page_for_string( check_str )
        # Wait for upload processing to finish (TODO: this should be done in each test case instead)
        self.wait()
        self.check_history_for_string( check_str )
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
        check_str = 'Deleted %d %s' % ( num_deleted, iff( num_deleted != 1, "histories","history") )
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
            self.check_page_for_string( 'Previously</a> stored histories' )
            if active_datasets:
                self.check_page_for_string( 'Create</a> a new empty history' )
                self.check_page_for_string( 'Construct workflow</a> from current history' )
                self.check_page_for_string( 'Clone</a> current history' ) 
            self.check_page_for_string( 'Share</a> current history' )
            self.check_page_for_string( 'Change default permissions</a> for current history' )
            if histories_shared_by_others:
                self.check_page_for_string( 'Histories</a> shared with you by others' )
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
        self.visit_url( "%s/history/list?id=%s&operation=share+or+publish" % ( self.url, history_id ) )
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
        self.check_page_for_string( 'Saved Histories' )
        self.check_page_for_string( '<input type="checkbox" name="id" value=' )
        self.check_page_for_string( 'operation=Rename' )
        self.check_page_for_string( 'operation=Switch' )
        self.check_page_for_string( 'operation=Delete' )
        if check_str:
            self.check_page_for_string( check_str )
        self.home()
    def view_stored_deleted_histories( self, check_str='' ):
        self.home()
        self.visit_page( "history/list?f-deleted=True" )
        self.check_page_for_string( 'Saved Histories' )
        self.check_page_for_string( '<input type="checkbox" name="id" value=' )
        self.check_page_for_string( 'operation=Undelete' )
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
    def make_accessible_via_link( self, history_id, check_str='', check_str_after_submit='' ):
        self.home()
        self.visit_page( "history/list?operation=share+or+publish&id=%s" % history_id )
        if check_str:
            self.check_page_for_string( check_str )
        # twill barfs on this form, possibly because it contains no fields, but not sure.
        # In any case, we have to mimic the form submission
        self.home()
        self.visit_page( 'history/sharing?id=%s&make_accessible_via_link=True' % history_id )
        if check_str_after_submit:
            self.check_page_for_string( check_str_after_submit )
        self.home()
    def disable_access_via_link( self, history_id, check_str='', check_str_after_submit='' ):
        self.home()
        self.visit_page( "history/list?operation=share+or+publish&id=%s" % history_id )
        if check_str:
            self.check_page_for_string( check_str )
        # twill barfs on this form, possibly because it contains no fields, but not sure.
        # In any case, we have to mimic the form submission
        self.home()
        self.visit_page( 'history/sharing?id=%s&disable_link_access=True' % history_id )
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
        self.visit_page( "edit?hid=%s" % hid )
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
    def display_history_item( self, hda_id, check_str='' ):
        """Displays a history item - simulates eye icon click"""
        self.visit_url( '%s/datasets/%s/display/' % ( self.url, self.security.encode_id( hda_id ) ) )
        if check_str:
            self.check_page_for_string( check_str )
        self.home()
    def view_history( self, history_id, check_str='' ):
        """Displays a history for viewing"""
        self.visit_url( '%s/history/view?id=%s' % ( self.url, self.security.encode_id( history_id ) ) )
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
        self.wait() #wait for the format convert tool to finish before returning
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
    def verify_dataset_correctness( self, filename, hid=None, wait=True, maxseconds=120, sort=False ):
        """Verifies that the attributes and contents of a history item meet expectations"""
        if wait:
            self.wait( maxseconds=maxseconds ) #wait for job to finish
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
                self.files_diff( local_name, temp_name, sort=sort )
            except AssertionError, err:
                os.remove(temp_name)
                errmsg = 'History item %s different than expected, difference:\n' % hid
                errmsg += str( err )
                raise AssertionError( errmsg )
            os.remove(temp_name)
    def verify_composite_datatype_file_content( self, file_name, hda_id ):
        local_name = self.get_filename( file_name )
        temp_name = self.get_filename( 'temp_%s' % file_name )
        self.visit_url( "%s/datasets/%s/display/%s" % ( self.url, self.security.encode_id( hda_id ), file_name ) )
        data = self.last_page()
        file( temp_name, 'wb' ).write( data )
        try:
            self.files_diff( local_name, temp_name )
        except AssertionError, err:
            os.remove( temp_name )
            errmsg = 'History item %s different than expected, difference:\n' % str( hda_id )
            errmsg += str( err )
            raise AssertionError( errmsg )
        os.remove( temp_name )
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
        # Create user, setting username to email.
        self.visit_page( "user/create?email=%s&username=%s&password=%s&confirm=%s&create_user_button=Submit" % ( email, email, password, password ) )
        self.check_page_for_string( "Now logged in as %s" %email )
        self.home()
        # Make sure a new private role was created for the user
        self.visit_page( "user/set_default_permissions" )
        self.check_page_for_string( email )
        self.home()
    def create_user_with_info( self, email, password, username, user_info_forms, user_info_form_id, user_info_values ):
        '''
        This method registers a new user and also provides use info
        '''
        self.home()
        if user_info_forms == 'multiple':
            self.visit_page( "user/create?user_info_select=%i&admin_view=False" % user_info_form_id )
        else:
            self.visit_page( "user/create?admin_view=False" )
        self.check_page_for_string( "Create account" )
        tc.fv( "1", "email", email )
        tc.fv( "1", "password", password )
        tc.fv( "1", "confirm", password )
        tc.fv( "1", "username", username )
        if user_info_forms == 'multiple':
            self.check_page_for_string( "User type" )
        for index, info_value in enumerate(user_info_values):
            tc.fv( "1", "field_%i" % index, info_value )
        tc.submit( "create_user_button" )
        self.check_page_for_string( "Now logged in as %s" % email )
    def create_user_with_info_as_admin( self, email, password, username, user_info_forms, user_info_form_id, user_info_values ):
        '''
        This method registers a new user and also provides use info as an admin
        '''
        self.home()
        if user_info_forms == 'multiple':
            self.visit_page( "admin/users?operation=create?user_info_select=%i&admin_view=False" % user_info_form_id )
        else:
            self.visit_page( "admin/users?operation=create" )
        self.check_page_for_string( "Create account" )
        tc.fv( "1", "email", email )
        tc.fv( "1", "password", password )
        tc.fv( "1", "confirm", password )
        tc.fv( "1", "username", username )
        if user_info_forms == 'multiple':
            self.check_page_for_string( "User type" )
        for index, info_value in enumerate(user_info_values):
            tc.fv( "1", "field_%i" % index, info_value )
        tc.submit( "create_user_button" )
        self.check_page_for_string( "Created new user account (%s)" % email )
    def edit_login_info( self, new_email, new_username ):
        self.home()
        self.visit_page( "user/show_info" )
        self.check_page_for_string( "Manage User Information" )
        tc.fv( "1", "email", new_email )
        tc.fv( "1", "username", new_username )
        tc.submit( "login_info_button" )
        self.check_page_for_string( 'The login information has been updated with the changes' )
        self.check_page_for_string( new_email )
        self.check_page_for_string( new_username )
    def change_password( self, password, new_password ):
        self.home()
        self.visit_page( "user/show_info" )
        self.check_page_for_string( "Manage User Information" )
        tc.fv( "2", "current", password )
        tc.fv( "2", "password", new_password )
        tc.fv( "2", "confirm", new_password )
        tc.submit( "change_password_button" )
        self.check_page_for_string( 'The password has been changed.' )
    def edit_user_info( self, info_values ):
        self.home()
        self.visit_page( "user/show_info" )
        self.check_page_for_string( "Manage User Information" )
        for index, info_value in enumerate(info_values):
            tc.fv( "3", "field_%i" % index, info_value )
        tc.submit( "edit_user_info_button" )
        self.check_page_for_string( "The user information has been updated with the changes." )
        for value in info_values:
            self.check_page_for_string( value )
    def user_set_default_permissions( self, permissions_out=[], permissions_in=[], role_id='2' ):
        # role.id = 2 is Private Role for test2@bx.psu.edu 
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
                fname = self.write_temp_file( page )
                errmsg = "no match to '%s'\npage content written to '%s'" % ( patt, fname )
                raise AssertionError( errmsg )
    
    def write_temp_file( self, content, suffix='.html' ):
        fd, fname = tempfile.mkstemp( suffix=suffix, prefix='twilltestcase-' )
        f = os.fdopen( fd, "w" )
        f.write( content )
        f.close()
        return fname

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
    def refresh_form( self, control_name, value, form_no=0, **kwd ):
        """Handles Galaxy's refresh_on_change for forms without ultimately submitting the form"""
        # control_name is the name of the form field that requires refresh_on_change, and value is
        # the value to which that field is being set.
        for i, f in enumerate( self.showforms() ):
            if i == form_no:
                break
        try:
            control = f.find_control( name=control_name )
        except:
            # This assumes we always want the first control of the given name, which may not be ideal...
            control = f.find_control( name=control_name, nr=0 )
        # Check for refresh_on_change attribute, submit a change if required
        if 'refresh_on_change' in control.attrs.keys():
            # Clear Control and set to proper value
            control.clear()
            tc.fv( f.name, control.name, value )
            # Create a new submit control, allows form to refresh, instead of going to next page
            control = ClientForm.SubmitControl( 'SubmitControl', '___refresh_grouping___', {'name':'refresh_grouping'} )
            control.add_to_form( f )
            control.fixup()
            # Submit for refresh
            tc.submit( '___refresh_grouping___' )
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

    def wait( self, maxseconds=120 ):
        """Waits for the tools to finish"""
        sleep_amount = 0.1
        slept = 0
        self.home()
        while slept <= maxseconds:
            self.visit_page( "history" )
            page = tc.browser.get_html()
            if page.find( '<!-- running: do not change this comment, used by TwillTestCase.wait -->' ) > -1:
                time.sleep( sleep_amount )
                slept += sleep_amount
                sleep_amount *= 2
                if slept + sleep_amount > maxseconds:
                    sleep_amount = maxseconds - slept # don't overshoot maxseconds
            else:
                break
        assert slept < maxseconds

    # Dataset Security stuff
    # Tests associated with users
    def create_new_account_as_admin( self, email='test4@bx.psu.edu', password='testuser' ):
        """Create a new account for another user"""
        # TODO: fix this so that it uses the form rather than the following URL.
        self.home()
        self.visit_url( "%s/user/create?admin_view=True&email=%s&password=%s&confirm=%s&create_user_button=Submit&subscribe=False" \
                        % ( self.url, email, password, password ) )
        try:
            self.check_page_for_string( "Created new user account" )
            previously_created = False
        except:
            # May have created the account in a previous test run...
            self.check_page_for_string( "User with that email already exists" )
            previously_created = True
        self.home()
        return previously_created
    def reset_password_as_admin( self, user_id, password='testreset' ):
        """Reset a user password"""
        self.home()
        self.visit_url( "%s/admin/reset_user_password?id=%s" % ( self.url, user_id ) )
        tc.fv( "1", "password", password )
        tc.fv( "1", "confirm", password )
        tc.submit( "reset_user_password_button" )
        self.check_page_for_string( "Passwords reset for 1 users" )
        self.home()
    def mark_user_deleted( self, user_id, email='' ):
        """Mark a user as deleted"""
        self.home()
        self.visit_url( "%s/admin/users?operation=delete&id=%s" % ( self.url, user_id ) )
        check_str = "Deleted 1 users"
        self.check_page_for_string( check_str )
        self.home()
    def undelete_user( self, user_id, email='' ):
        """Undelete a user"""
        self.home()
        self.visit_url( "%s/admin/users?operation=undelete&id=%s" % ( self.url, user_id ) )
        check_str = "Undeleted 1 users"
        self.check_page_for_string( check_str )
        self.home()
    def purge_user( self, user_id, email ):
        """Purge a user account"""
        self.home()
        self.visit_url( "%s/admin/users?operation=purge&id=%s" % ( self.url, user_id ) )
        check_str = "Purged 1 users"
        self.check_page_for_string( check_str )
        self.home()
    def associate_roles_and_groups_with_user( self, user_id, email,
                                              in_role_ids=[], out_role_ids=[],
                                              in_group_ids=[], out_group_ids=[],
                                              check_str='' ):
        self.home()
        url = "%s/admin/manage_roles_and_groups_for_user?id=%s&user_roles_groups_edit_button=Save" % ( self.url, user_id )
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
    def create_role( self,
                     name='Role One',
                     description="This is Role One",
                     in_user_ids=[],
                     in_group_ids=[],
                     create_group_for_role='no',
                     private_role='' ):
        """Create a new role"""
        url = "%s/admin/roles?operation=create&create_role_button=Save&name=%s&description=%s" % ( self.url, name.replace( ' ', '+' ), description.replace( ' ', '+' ) )
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
        self.visit_url( "%s/admin/roles?operation=rename&id=%s" % ( self.url, role_id ) )
        self.check_page_for_string( 'Change role name and description' )
        tc.fv( "1", "name", name )
        tc.fv( "1", "description", description )
        tc.submit( "rename_role_button" )
        self.home()
    def mark_role_deleted( self, role_id, role_name ):
        """Mark a role as deleted"""
        self.home()
        self.visit_url( "%s/admin/roles?operation=delete&id=%s" % ( self.url, role_id ) )
        check_str = "Role '%s' has been marked as deleted" % role_name
        self.check_page_for_string( check_str )
        self.home()
    def undelete_role( self, role_id, role_name ):
        """Undelete an existing role"""
        self.home()
        self.visit_url( "%s/admin/roles?operation=undelete&id=%s" % ( self.url, role_id ) )
        check_str = "Role '%s' has been marked as not deleted" % role_name
        self.check_page_for_string( check_str )
        self.home()
    def purge_role( self, role_id, role_name ):
        """Purge an existing role"""
        self.home()
        self.visit_url( "%s/admin/roles?operation=purge&id=%s" % ( self.url, role_id ) )
        check_str = "The following have been purged from the database for role '%s': " % role_name
        check_str += "DefaultUserPermissions, DefaultHistoryPermissions, UserRoleAssociations, GroupRoleAssociations, DatasetPermissionss."
        self.check_page_for_string( check_str )
        self.home()
    def associate_users_and_groups_with_role( self, role_id, role_name, user_ids=[], group_ids=[] ):
        self.home()
        url = "%s/admin/role?id=%s&role_members_edit_button=Save" % ( self.url, role_id )
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
        url = "%s/admin/groups?operation=create&create_group_button=Save&name=%s" % ( self.url, name.replace( ' ', '+' ) )
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
        self.visit_url( "%s/admin/groups?operation=rename&id=%s" % ( self.url, group_id ) )
        self.check_page_for_string( 'Change group name' )
        tc.fv( "1", "name", name )
        tc.submit( "rename_group_button" )
        self.home()
    def associate_users_and_roles_with_group( self, group_id, group_name, user_ids=[], role_ids=[] ):
        self.home()
        url = "%s/admin/manage_users_and_roles_for_group?id=%s&group_roles_users_edit_button=Save" % ( self.url, group_id )
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
        self.visit_url( "%s/admin/groups?operation=delete&id=%s" % ( self.url, group_id ) )
        check_str = "Group '%s' has been marked as deleted" % group_name
        self.check_page_for_string( check_str )
        self.home()
    def undelete_group( self, group_id, group_name ):
        """Undelete an existing group"""
        self.home()
        self.visit_url( "%s/admin/groups?operation=undelete&id=%s" % ( self.url, group_id ) )
        check_str = "Group '%s' has been marked as not deleted" % group_name
        self.check_page_for_string( check_str )
        self.home()
    def purge_group( self, group_id, group_name ):
        """Purge an existing group"""
        self.home()
        self.visit_url( "%s/admin/groups?operation=purge&id=%s" % ( self.url, group_id ) )
        check_str = "The following have been purged from the database for group '%s': UserGroupAssociations, GroupRoleAssociations." % group_name
        self.check_page_for_string( check_str )
        self.home()

    # Form stuff
    def create_form( self, name, desc, formtype, form_layout_name='', num_fields=1 ):
        """
        Create a new form definition.  Testing framework is still limited to only testing
        one instance for each repeat. This has to do with the 'flat' nature of defining
        test param values.  Using same-named parameters down different branches (having
        different scope in the tool) cannot be properly tested when they both exist at the
        same time.
        """
        self.home()
        self.visit_url( "%s/forms/new" % self.url )
        self.check_page_for_string( 'Create a new form definition' )
        tc.fv( "1", "name", name ) # form field 1 is the field named name...
        tc.fv( "1", "description", desc ) # form field 1 is the field named desc...
        tc.fv( "1", "form_type_selectbox", formtype )
        tc.submit( "create_form_button" )
        if formtype == "Sequencing Sample Form":
            tc.submit( "add_layout_grid" )
            tc.fv( "1", "grid_layout0", form_layout_name )
        for index in range( num_fields ):
            field_name = 'field_name_%i' % index
            field_contents = 'Field %i' % index
            field_help_name = 'field_helptext_%i' % index
            field_help_contents = 'Field %i help' % index
            tc.fv( "1", field_name, field_contents )
            tc.fv( "1", field_help_name, field_help_contents )
            tc.submit( "save_changes_button" )
        if num_fields:
            check_str = "The form '%s' has been updated with the changes." % name
            self.check_page_for_string( check_str )
        else:
            self.home()
            self.visit_url( "%s/forms/manage" % self.url )
            self.check_page_for_string( name )
            self.check_page_for_string( desc )
            self.check_page_for_string( formtype )
        self.home()
    def edit_form( self, form_current_id, form_name, new_form_name="Form One's Name (Renamed)", new_form_desc="This is Form One's description (Re-described)"):
        """
        Edit form details; name & description
        """
        self.home()
        self.visit_url( "%s/forms/manage?sort=create_time&f-name=All&f-desc=All&f-deleted=False&operation=Edit&id=%s" % ( self.url, self.security.encode_id(form_current_id) ) )
        self.check_page_for_string( 'Edit form definition "%s"' % form_name )
        tc.fv( "1", "name", new_form_name ) 
        tc.fv( "1", "description", new_form_desc ) 
        tc.submit( "save_changes_button" )
        self.check_page_for_string( "The form '%s' has been updated with the changes." % new_form_name )
        self.home()
    def form_add_field( self, form_current_id, form_name, form_desc, form_type, form_layout_name='', field_index=0, fields=None):
        """
        Add a new fields to the form definition
        """
        self.home()
        self.visit_url( "%s/forms/manage?sort=create_time&f-name=All&f-desc=All&f-deleted=False&operation=Edit&id=%s" % ( self.url, self.security.encode_id(form_current_id) ) )
        self.check_page_for_string( 'Edit form definition "%s"' % form_name)
        for i, field in enumerate(fields):
            index = i+field_index
            tc.submit( "add_field_button" )
            tc.fv( "1", "field_name_%i" % index, field['name'] )
            tc.fv( "1", "field_helptext_%i" % index, field['desc'] )
            tc.fv( "1", "field_type_%i" % index, field['type'] )
            tc.fv( "1", "field_required_%i" % index, field['required'] )
            if field['type'] == 'SelectField':
                options = ''
                for option_index, option in enumerate(field['selectlist']):
                    url_str = "%s/forms/manage?operation=Edit&description=%s&grid_layout0=%s&id=%s&form_type_selectbox=%s&addoption_%i=Add&name=%s&field_name_%i=%s&field_helptext_%i=%s&field_type_%i=%s" % \
                              (self.url, form_desc.replace(" ", "+"), form_layout_name.replace(" ", "+"), 
                               self.security.encode_id(form_current_id), form_type.replace(" ", "+"), 
                               index, form_name.replace(" ", "+"), index, field['name'].replace(" ", "+"), 
                               index, field['desc'].replace(" ", "+"), index, field['type'])
                    self.visit_url( url_str + options )
                    tc.fv( "1", "field_%i_option_%i" % (index, option_index), option )
                    options = options + "&field_%i_option_%i=%s" % (index, option_index, option)
        tc.submit( "save_changes_button" )
        check_str = "The form '%s' has been updated with the changes." % form_name
        self.check_page_for_string( check_str )
        self.home()
    def form_remove_field( self, form_id, form_name, field_name):
        """
        Remove a field from the form definition
        """
        self.home()
        self.visit_url( "%s/forms/manage?operation=Edit&form_id=%i&show_form=True" % (self.url, form_id) )
        self.check_page_for_string( 'Edit form definition "%s"' % form_name)
        tc.submit( "remove_button" )
        tc.submit( "save_changes_button" )
        check_str = "The form '%s' has been updated with the changes." % form_name
        self.check_page_for_string( check_str )
        self.home()
    # Requests stuff
    def check_request_grid(self, state, request_name, deleted=False):
        self.home()
        self.visit_url('%s/requests/list?sort=create_time&f-state=%s&f-deleted=%s' \
                       % (self.url, state, str(deleted)))
        self.check_page_for_string( request_name )
    def check_request_admin_grid(self, state, request_name, deleted=False):
        self.home()
        self.visit_url('%s/requests_admin/list?sort=create_time&f-state=%s&f-deleted=%s' \
                       % (self.url, state, str(deleted)))
        self.check_page_for_string( request_name )
    def create_request_type( self, name, desc, request_form_id, sample_form_id, states ):
        self.home()
        self.visit_url( "%s/requests_admin/create_request_type" % self.url )
        self.check_page_for_string( 'Create a new request type' )
        tc.fv( "1", "name", name )
        tc.fv( "1", "desc", desc )
        tc.fv( "1", "request_form_id", request_form_id )
        tc.fv( "1", "sample_form_id", sample_form_id )
        for index, state in enumerate(states):
            tc.submit( "add_state_button" )
            tc.fv("1", "state_name_%i" % index, state[0])
            tc.fv("1", "state_desc_%i" % index, state[1])
        tc.submit( "save_request_type" )
        self.check_page_for_string( "Request type <b>%s</b> has been created" % name )
    def create_request( self, request_type_id, name, desc, fields ):
        self.home()
        self.visit_url( "%s/requests/new?create=True&select_request_type=%i" % ( self.url, 
                                                                                 request_type_id ) )
        self.check_page_for_string( 'Add a new request' )
        tc.fv( "1", "name", name )
        tc.fv( "1", "desc", desc )
        for index, field_value in enumerate(fields):
            tc.fv( "1", "field_%i" % index, field_value )
        tc.submit( "create_request_button" )
        self.check_page_for_string( name )
        self.check_page_for_string( desc )
    def edit_request( self, request_id, name, new_name, new_desc, new_fields):
        self.home()
        self.visit_url( "%s/requests/list?operation=Edit&id=%s" % (self.url, self.security.encode_id(request_id) ) )
        self.check_page_for_string( 'Edit request "%s"' % name )
        tc.fv( "1", "name", new_name )
        tc.fv( "1", "desc", new_desc )
        for index, field_value in enumerate(new_fields):
            tc.fv( "1", "field_%i" % index, field_value )
        tc.submit( "save_changes_request_button" )
        self.check_page_for_string( new_name )
        self.check_page_for_string( new_desc )
    def add_samples( self, request_id, request_name, samples ):
        self.home()
        self.visit_url( "%s/requests/list?sort=-create_time&operation=show_request&id=%s" % ( self.url, self.security.encode_id( request_id ) ))
        self.check_page_for_string( 'Sequencing Request "%s"' % request_name )
        for sample_index, sample in enumerate(samples):
            tc.submit( "add_sample_button" )
            sample_name, fields = sample
            tc.fv( "1", "sample_%i_name" % sample_index, sample_name )
            for field_index, field_value in enumerate(fields):
                tc.fv( "1", "sample_%i_field_%i" % ( sample_index, field_index ), field_value )
        tc.submit( "save_samples_button" )
        for sample_name, fields in samples:
            self.check_page_for_string( sample_name )
            self.check_page_for_string( 'Unsubmitted' )
            for field_value in fields:
                self.check_page_for_string( field_value )
    def submit_request( self, request_id, request_name ):
        self.home()
        self.visit_url( "%s/requests/list?operation=Submit&id=%s" % ( self.url, self.security.encode_id( request_id ) ))
        self.check_page_for_string( 'The request <b>%s</b> has been submitted.' % request_name )
    def submit_request_as_admin( self, request_id, request_name ):
        self.home()
        self.visit_url( "%s/requests_admin/list?operation=Submit&id=%s" % ( self.url, self.security.encode_id( request_id ) ))
        self.check_page_for_string( 'The request <b>%s</b> has been submitted.' % request_name )
    def reject_request( self, request_id, request_name, comment ):
        self.home()
        self.visit_url( "%s/requests_admin/list?operation=Reject&id=%s" % ( self.url, self.security.encode_id( request_id ) ))
        self.check_page_for_string( 'Reject Sequencing Request "%s"' % request_name )
        tc.fv( "1", "comment", comment )
        tc.submit( "reject_button" )
        self.check_page_for_string( 'Request <b>%s</b> has been rejected.' % request_name )
        self.visit_url( "%s/requests/list?sort=-create_time&operation=show_request&id=%s" % ( self.url, self.security.encode_id( request_id ) ))
        self.check_page_for_string( comment )
    def add_bar_codes( self, request_id, request_name, bar_codes ):
        self.home()
        self.visit_url( "%s/requests_admin/bar_codes?request_id=%i" % (self.url, request_id) )
        self.check_page_for_string( 'Bar codes for Samples of Request "%s"' % request_name )
        for index, bar_code in enumerate(bar_codes):
            tc.fv( "1", "sample_%i_bar_code" % index, bar_code )
        tc.submit( "save_bar_codes" )
        self.check_page_for_string( 'Bar codes have been saved for this request' )
    def change_sample_state( self, sample_name, sample_id, new_state_id, new_state_name, comment='' ):
        self.home()
        self.visit_url( "%s/requests_admin/show_events?sample_id=%i" % (self.url, sample_id) )
        self.check_page_for_string( 'Events for Sample "%s"' % sample_name )
        tc.fv( "1", "select_state", str(new_state_id) )
        tc.fv( "1", "comment", comment )
        tc.submit( "add_event_button" )
        self.check_page_for_string( new_state_name )
    def add_user_address( self, user_id, address_dict ):
        self.home()
        self.visit_url( "%s/user/new_address?admin_view=False&user_id=%i" % ( self.url, user_id ) )
        self.check_page_for_string( 'New address' )
        for field_name, value in address_dict.items():
            tc.fv( "1", field_name, value )
        tc.submit( "save_new_address_button" )
        self.check_page_for_string( 'Address <b>%s</b> has been added' % address_dict[ 'short_desc' ] )
    def add_user_address_as_admin( self, user_id, address_dict ):
        self.home()
        self.visit_url( "%s/user/new_address?admin_view=True&user_id=%i" % ( self.url, user_id ) )
        self.check_page_for_string( 'New address' )
        for field_name, value in address_dict.items():
            tc.fv( "1", field_name, value )
        tc.submit( "save_new_address_button" )
        self.check_page_for_string( 'Address <b>%s</b> has been added' % address_dict[ 'short_desc' ] )
        
    # Library stuff
    def create_library( self, name='Library One', description='This is Library One' ):
        """Create a new library"""
        self.home()
        self.visit_url( "%s/library_admin/create_library" % self.url )
        self.check_page_for_string( 'Create a new data library' )
        tc.fv( "1", "1", name ) # form field 1 is the field named name...
        tc.fv( "1", "2", description ) # form field 1 is the field named name...
        tc.submit( "create_library_button" )
        self.home()
    def library_permissions( self, library_id, library_name, role_ids_str, permissions_in, permissions_out, cntrller='library_admin' ):
        # role_ids_str must be a comma-separated string of role ids
        url = "library_common/library_permissions?id=%s&cntrller=%slibrary_admin&update_roles_button=Save" % ( library_id, cntrller )
        for po in permissions_out:
            key = '%s_out' % po
            url ="%s&%s=%s" % ( url, key, role_ids_str )
        for pi in permissions_in:
            key = '%s_in' % pi
            url ="%s&%s=%s" % ( url, key, role_ids_str )
        self.home()
        self.visit_url( "%s/%s" % ( self.url, url ) )
        check_str = "Permissions updated for library '%s'" % library_name
        self.check_page_for_string( check_str )
        self.home()
    def rename_library( self, library_id, old_name, name='Library One Renamed', description='This is Library One Re-described', controller='library_admin' ):
        """Rename a library"""
        self.home()
        self.visit_url( "%s/library_common/library_info?id=%s&cntrller=%s" % ( self.url, library_id, controller ) )
        self.check_page_for_string( 'Change library name and description' )
        # Since twill barfs on the form submisson, we ar forced to simulate it
        url = "%s/library_common/library_info?id=%s&cntrller=%s&rename_library_button=Save&description=%s&name=%s" % \
        ( self.url, library_id, controller, description.replace( ' ', '+' ), name.replace( ' ', '+' ) )
        self.home()
        self.visit_url( url )
        check_str = "Library '%s' has been renamed to '%s'" % ( old_name, name )
        self.check_page_for_string( check_str )
        self.home()
    def add_info_template( self, cntrller, item_type, library_id, form_id, form_name, folder_id=None, ldda_id=None ):
        """Add a new info template to a library item"""
        self.home()
        if item_type == 'library':
            url = "%s/library_common/add_info_template?cntrller=%s&item_type=%s&library_id=%s" % ( self.url, cntrller, item_type, library_id )
        elif item_type == 'folder':
            url = "%s/library_common/add_info_template?cntrller=%s&item_type=%s&library_id=%s&folder_id=%s" % ( self.url, cntrller, item_type, library_id, folder_id )
        elif item_type == 'ldda':
            url = "%s/library_common/add_info_template?cntrller=%s&item_type=%s&library_id=%s&folder_id=%s&ldda_id=%s" % ( self.url, cntrller, item_type, library_id, folder_id, ldda_id )
        self.visit_url( url )
        self.check_page_for_string ( "Select a template for the" )
        tc.fv( '1', 'form_id', form_id )
        tc.submit( 'add_info_template_button' )
        self.check_page_for_string = 'A template based on the form "%s" has been added to this' % form_name
        self.home()
    def library_info( self, library_id, library_name, ele_1_field_name, ele_1_contents, ele_2_field_name, ele_2_contents, controller='library_admin' ):
        """Add information to a library using an existing template with 2 elements"""
        self.home()
        self.visit_url( "%s/library_common/library_info?id=%s&cntrller=%s" % ( self.url, library_id, controller ) )
        check_str = 'Other information about library %s' % library_name
        self.check_page_for_string( check_str )
        tc.fv( '2', ele_1_field_name, ele_1_contents )
        tc.fv( '2', ele_2_field_name, ele_2_contents )
        tc.submit( 'create_new_info_button' )
        self.home()
    def add_folder( self, controller, library_id, folder_id, name='Folder One', description='This is Folder One' ):
        """Create a new folder"""
        self.home()
        self.visit_url( "%s/library_common/create_folder?cntrller=%s&library_id=%s&parent_id=%s" % ( self.url, controller, library_id, folder_id ) )
        self.check_page_for_string( 'Create a new folder' )
        tc.fv( "1", "name", name ) # form field 1 is the field named name...
        tc.fv( "1", "description", description ) # form field 2 is the field named description...
        tc.submit( "new_folder_button" )
        self.home()
    def folder_info( self, controller, folder_id, library_id, name, new_name, description, contents='', field_name='' ):
        """Add information to a library using an existing template with 2 elements"""
        self.home()
        self.visit_url( "%s/library_common/folder_info?cntrller=%s&id=%s&library_id=%s" % \
                        ( self.url, controller, folder_id, library_id) )
        # Twill cannot handle the following call for some reason - it's buggy
        # self.check_page_for_string( "Edit folder name and description" )
        tc.fv( '1', "name", new_name )
        tc.fv( '1', "description", description )
        tc.submit( 'rename_folder_button' )
        # Twill cannot handle the following call for some reason - it's buggy
        # check_str = "Folder '%s' has been renamed to '%s'" % ( name, new_name )
        # self.check_page_for_string( check_str )
        if contents and field_name:
            # We have an information template associated with the folder, so
            # there are 2 forms on this page and the template is the 2nd form
            tc.fv( '2', field_name, contents )
            tc.submit( 'edit_info_button' )
            # Twill cannot handle the following call for some reason - it's buggy
            # self.check_page_for_string( 'The information has been updated.' )
        self.home()
    def add_library_dataset( self, cntrller, filename, library_id, folder_id, folder_name,
                             file_type='auto', dbkey='hg18', roles=[], message='', root=False,
                             template_field_name1='', template_field_contents1='' ):
        """Add a dataset to a folder"""
        filename = self.get_filename( filename )
        self.home()
        self.visit_url( "%s/library_common/upload_library_dataset?cntrller=%s&upload_option=upload_file&library_id=%s&folder_id=%s&message=%s" % \
                        ( self.url, cntrller, library_id, folder_id, message ) )
        self.check_page_for_string( 'Upload files' )
        tc.fv( "1", "folder_id", folder_id )
        tc.formfile( "1", "files_0|file_data", filename )
        tc.fv( "1", "file_type", file_type )
        tc.fv( "1", "dbkey", dbkey )
        tc.fv( "1", "message", message.replace( '+', ' ' ) )
        for role_id in roles:
            tc.fv( "1", "roles", role_id )
        # Add template field contents, if any...
        if template_field_name1:
            tc.fv( "1", template_field_name1, template_field_contents1 )
        tc.submit( "runtool_btn" )
        if root:
            check_str = "Added 1 datasets to the library '%s' (each is selected)." % folder_name
        else:
            check_str = "Added 1 datasets to the folder '%s' (each is selected)." % folder_name
        self.library_wait( library_id )
        self.home()
    def set_library_dataset_permissions( self, cntrller, library_id, folder_id, ldda_id, ldda_name, role_ids_str, permissions_in, permissions_out ):
        # role_ids_str must be a comma-separated string of role ids
        url = "library_common/ldda_permissions?cntrller=%s&library_id=%s&folder_id=%s&id=%s&update_roles_button=Save" % \
            ( cntrller, library_id, folder_id, ldda_id )
        for po in permissions_out:
            key = '%s_out' % po
            url ="%s&%s=%s" % ( url, key, role_ids_str )
        for pi in permissions_in:
            key = '%s_in' % pi
            url ="%s&%s=%s" % ( url, key, role_ids_str )
        self.home()
        self.visit_url( "%s/%s" % ( self.url, url ) )
        check_str = "Permissions have been updated on 1 datasets"
        self.check_page_for_string( check_str )
        self.home()
    def edit_ldda_template_element_info( self, library_id, folder_id, ldda_id, ldda_name, ele_1_field_name, 
                        ele_1_contents, ele_2_field_name, ele_2_contents, ele_1_help='', ele_2_help='',
                        ele_3_field_name='', ele_3_contents='', ele_3_help='' ):
        """Edit library_dataset_dataset_association template element information"""
        self.home()
        self.visit_url( "%s/library_common/ldda_edit_info?cntrller=library_admin&library_id=%s&folder_id=%s&id=%s" % \
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
    def edit_ldda_attribute_info( self, cntrller, library_id, folder_id, ldda_id, ldda_name, new_ldda_name ):
        """Edit library_dataset_dataset_association attribute information"""
        self.home()
        self.visit_url( "%s/library_common/ldda_edit_info?cntrller=%s&library_id=%s&folder_id=%s&id=%s" % \
                        ( self.url, cntrller, library_id, folder_id, ldda_id ) )
        check_str = 'Edit attributes of %s' % ldda_name
        self.check_page_for_string( check_str )
        tc.fv( '1', 'name', new_ldda_name )
        tc.submit( 'save' )
        check_str = 'Attributes updated for library dataset %s' % new_ldda_name
        self.check_page_for_string( check_str )
        check_str = 'Edit attributes of %s' % new_ldda_name
        self.check_page_for_string( check_str )
        self.home()
    def upload_new_dataset_version( self, cntrller, filename, library_id, folder_id, folder_name, library_dataset_id, ldda_name, file_type='auto',
                                    dbkey='hg18', message='', template_field_name1='', template_field_contents1='' ):
        """Upload new version(s) of a dataset"""
        self.home()
        filename = self.get_filename( filename )      
        self.visit_url( "%s/library_common/upload_library_dataset?cntrller=%s&upload_option=upload_file&library_id=%s&folder_id=%s&replace_id=%s&message=%s" % \
                        ( self.url, cntrller, library_id, folder_id, library_dataset_id, message ) )
        self.check_page_for_string( 'Upload files' )
        self.check_page_for_string( 'You are currently selecting a new file to replace' )
        self.check_page_for_string( ldda_name )
        tc.formfile( "1", "files_0|file_data", filename )
        tc.fv( "1", "file_type", file_type )
        tc.fv( "1", "dbkey", dbkey )
        tc.fv( "1", "message", message.replace( '+', ' ' ) )
        # Add template field contents, if any...
        if template_field_name1:
            tc.fv( "1", template_field_name1, template_field_contents1 )
        tc.submit( "runtool_btn" )
        check_str = "Added 1 dataset versions to the library dataset '%s' in the folder '%s'." % ( ldda_name, folder_name )
        self.check_page_for_string( check_str )
        self.library_wait( library_id )
        self.home()
    def add_history_datasets_to_library( self, cntrller, library_id, folder_id, folder_name, hda_id, root=False ):
        """Copy a dataset from the current history to a library folder"""
        self.home()
        self.visit_url( "%s/library_common/add_history_datasets_to_library?cntrller=%s&library_id=%s&folder_id=%s&hda_ids=%s&add_history_datasets_to_library_button=Add+selected+datasets" % \
                        ( self.url, cntrller, library_id, folder_id, hda_id ) )
        if root:
            check_str = "Added 1 datasets to the library '%s' (each is selected)." % folder_name
        else:
            check_str = "Added 1 datasets to the folder '%s' (each is selected)." % folder_name
        self.check_page_for_string( check_str )
        self.home()
    def add_dir_of_files_from_admin_view( self, library_id, folder_id, file_type='auto', dbkey='hg18', roles_tuple=[],
                                          message='', check_str_after_submit='', template_field_name1='', template_field_contents1='' ):
        """Add a directory of datasets to a folder"""
        # roles is a list of tuples: [ ( role_id, role_description ) ]
        self.home()
        self.visit_url( "%s/library_common/upload_library_dataset?cntrller=library_admin&upload_option=upload_directory&library_id=%s&folder_id=%s" % \
            ( self.url, library_id, folder_id ) )
        self.check_page_for_string( 'Upload a directory of files' )
        tc.fv( "1", "folder_id", folder_id )
        tc.fv( "1", "file_type", file_type )
        tc.fv( "1", "dbkey", dbkey )
        tc.fv( "1", "message", message.replace( '+', ' ' ) )
        tc.fv( "1", "server_dir", "library" )
        for role_tuple in roles_tuple:
            tc.fv( "1", "roles", role_tuple[1] ) # role_tuple[1] is the role name
        # Add template field contents, if any...
        if template_field_name1:
            tc.fv( "1", template_field_name1, template_field_contents1 )
        tc.submit( "runtool_btn" )
        if check_str_after_submit:
            self.check_page_for_string( check_str_after_submit )
        self.library_wait( library_id )
        self.home()
    def add_dir_of_files_from_libraries_view( self, library_id, folder_id, selected_dir, file_type='auto', dbkey='hg18', roles_tuple=[],
                                              message='', check_str_after_submit='', template_field_name1='', template_field_contents1='' ):
        """Add a directory of datasets to a folder"""
        # roles is a list of tuples: [ ( role_id, role_description ) ]
        self.home()
        self.visit_url( "%s/library_common/upload_library_dataset?cntrller=library&upload_option=upload_directory&library_id=%s&folder_id=%s" % \
            ( self.url, library_id, folder_id ) )
        self.check_page_for_string( 'Upload a directory of files' )
        tc.fv( "1", "folder_id", folder_id )
        tc.fv( "1", "file_type", file_type )
        tc.fv( "1", "dbkey", dbkey )
        tc.fv( "1", "message", message.replace( '+', ' ' ) )
        tc.fv( "1", "server_dir", selected_dir )
        for role_tuple in roles_tuple:
            tc.fv( "1", "roles", role_tuple[1] ) # role_tuple[1] is the role name
        # Add template field contents, if any...
        if template_field_name1:
            tc.fv( "1", template_field_name1, template_field_contents1 )
        tc.submit( "runtool_btn" )
        if check_str_after_submit:
            self.check_page_for_string( check_str_after_submit )
        self.library_wait( library_id, cntrller='library' )
        self.home()
    def download_archive_of_library_files( self, cntrller, library_id, ldda_ids, format ):
        self.home()
        self.visit_url( "%s/library_common/browse_library?cntrller=%s&id=%s" % ( self.url, cntrller, library_id ) )
        for ldda_id in ldda_ids:
            tc.fv( "1", "ldda_ids", ldda_id )
        tc.fv( "1", "do_action", format )
        tc.submit( "action_on_datasets_button" )
        tc.code( 200 )
        archive = self.write_temp_file( self.last_page(), suffix=format )
        self.home()
        return archive
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
    def delete_library_item( self, library_id, library_item_id, library_item_name, library_item_type='library_dataset' ):
        """Mark a library item as deleted"""
        self.home()
        self.visit_url( "%s/library_admin/delete_library_item?library_id=%s&library_item_id=%s&library_item_type=%s" \
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
        self.visit_url( "%s/library_admin/undelete_library_item?library_id=%s&library_item_id=%s&library_item_type=%s" \
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
        self.visit_url( "%s/library_admin/purge_library?id=%s" % ( self.url, library_id ) )
        check_str = "Library '%s' and all of its contents have been purged" % library_name
        self.check_page_for_string( check_str )
        self.home()
    def library_wait( self, library_id, cntrller='library_admin', maxiter=20 ):
        """Waits for the tools to finish"""
        count = 0
        sleep_amount = 1
        self.home()
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
