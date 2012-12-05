from base.twilltestcase import *
from galaxy.webapps.community.util.hgweb_config import *
from test_db_util import *
from common import *
import string 

from galaxy import eggs
eggs.require('mercurial')
from mercurial import hg, ui

class ShedTwillTestCase( TwillTestCase ):
    def setUp( self ):
        # Security helper
        self.security = security.SecurityHelper( id_secret='changethisinproductiontoo' )
        self.history_id = None
        self.hgweb_config_dir = os.environ.get( 'TEST_HG_WEB_CONFIG_DIR' )
        self.hgweb_config_manager = HgWebConfigManager()
        self.hgweb_config_manager.hgweb_config_dir = self.hgweb_config_dir
        self.host = os.environ.get( 'TOOL_SHED_TEST_HOST' )
        self.port = os.environ.get( 'TOOL_SHED_TEST_PORT' )
        self.url = "http://%s:%s" % ( self.host, self.port )
        self.file_dir = os.environ.get( 'TOOL_SHED_TEST_FILE_DIR', None )
        self.tool_shed_test_file = None
        self.shed_tools_dict = {}
        self.keepOutdir = os.environ.get( 'TOOL_SHED_TEST_SAVE', '' )
        if self.keepOutdir > '':
           try:
               os.makedirs( self.keepOutdir )
           except:
               pass
        self.home()
    def browse_repository( self, repository, strings_displayed=[], strings_not_displayed=[] ):
        url = '/repository/browse_repository?id=%s' % self.security.encode_id( repository.id )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def check_for_strings( self, strings_displayed=[], strings_not_displayed=[] ):
        if strings_displayed:
            for string in strings_displayed:
                self.check_page_for_string( string )
        if strings_not_displayed:
            for string in strings_not_displayed:
                self.check_string_not_in_page( string )
    def check_for_valid_tools( self, repository, strings_displayed=[], strings_not_displayed=[] ):
        strings_displayed.append( 'Valid tools' )
        self.display_manage_repository_page( repository, strings_displayed, strings_not_displayed )
    def check_count_of_metadata_revisions_associated_with_repository( self, repository, metadata_count ):
        self.check_repository_changelog( repository )
        self.check_string_count_in_page( 'Repository metadata is associated with this change set.', metadata_count )
    def check_repository_changelog( self, repository, strings_displayed=[], strings_not_displayed=[] ):
        url = '/repository/view_changelog?id=%s' % self.security.encode_id( repository.id )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def check_repository_metadata( self, repository, tip_only=True ):
        if tip_only:
            assert self.tip_has_metadata( repository ) and len( self.get_repository_metadata_revisions( repository ) ) == 1, \
                'Repository tip is not a metadata revision: Repository tip - %s, metadata revisions - %s.'
        else:
            assert len( self.get_repository_metadata_revisions( repository ) ) > 0, \
                   'Repository tip is not a metadata revision: Repository tip - %s, metadata revisions - %s.' % \
                   ( self.get_repository_tip( repository ), ', '.join( self.get_repository_metadata_revisions( repository ) ) )
    def check_repository_tools_for_changeset_revision( self, repository, changeset_revision ):
        '''
        Loop through each tool dictionary in the repository metadata associated with the received changeset_revision. 
        For each of these, check for a tools attribute, and load the tool metadata page if it exists, then display that tool's page.
        '''
        repository_metadata = get_repository_metadata_by_repository_id_changeset_revision( repository.id, changeset_revision )
        metadata = repository_metadata.metadata
        if 'tools' not in metadata:
            raise AssertionError( 'No tools in %s revision %s.' % ( repository.name, changeset_revision ) )
        for tool_dict in metadata[ 'tools' ]:
            metadata_strings_displayed = [ tool_dict[ 'guid' ], 
                                           tool_dict[ 'version' ], 
                                           tool_dict[ 'id' ], 
                                           tool_dict[ 'name' ], 
                                           tool_dict[ 'description' ],
                                           changeset_revision ]
            url = '/repository/view_tool_metadata?repository_id=%s&changeset_revision=%s&tool_id=%s' % \
                  ( self.security.encode_id( repository.id ), changeset_revision, tool_dict[ 'id' ] )
            self.visit_url( url )
            self.check_for_strings( metadata_strings_displayed )
            self.load_display_tool_page( repository, tool_xml_path=tool_dict[ 'tool_config' ],
                                         changeset_revision=changeset_revision,
                                         strings_displayed=[ '%s (version %s)' % ( tool_dict[ 'name' ], tool_dict[ 'version' ] ) ],
                                         strings_not_displayed=[] )
    def check_repository_invalid_tools_for_changeset_revision( self, repository, changeset_revision, strings_displayed=[], strings_not_displayed=[] ):
        '''Load the invalid tool page for each invalid tool associated with this changeset revision and verify the received error messages.'''
        repository_metadata = get_repository_metadata_by_repository_id_changeset_revision( repository.id, changeset_revision )
        metadata = repository_metadata.metadata
        if 'invalid_tools' not in metadata:
            return
        for tool_xml in metadata[ 'invalid_tools' ]:
            self.load_invalid_tool_page( repository, 
                                         tool_xml=tool_xml,
                                         changeset_revision=changeset_revision,
                                         strings_displayed=strings_displayed,
                                         strings_not_displayed=strings_not_displayed )
    def check_string_count_in_page( self, pattern, min_count, max_count=None ):
        """Checks the number of 'pattern' occurrences in the current browser page"""        
        page = self.last_page()
        pattern_count = page.count( pattern )
        if max_count is None:
            max_count = min_count
        # The number of occurrences of pattern in the page should be between min_count
        # and max_count, so show error if pattern_count is less than min_count or greater
        # than max_count.
        if pattern_count < min_count or pattern_count > max_count:
            fname = self.write_temp_file( page )
            errmsg = "%i occurrences of '%s' found (min. %i, max. %i).\npage content written to '%s' " % \
                     ( pattern_count, pattern, min_count, max_count, fname )
            raise AssertionError( errmsg )
    def create_category( self, category_name, category_description ):
        self.visit_url( '/admin/manage_categories?operation=create' )
        tc.fv( "1", "name", category_name )
        tc.fv( "1", "description", category_description )
        tc.submit( "create_category_button" )
    def create_repository( self, repository_name, repository_description, repository_long_description=None, categories=[], strings_displayed=[], strings_not_displayed=[] ):
        self.visit_url( '/repository/create_repository' )
        tc.fv( "1", "name", repository_name )
        tc.fv( "1", "description", repository_description )
        if repository_long_description is not None:
            tc.fv( "1", "long_description", repository_long_description )
        for category in categories:
            tc.fv( "1", "category_id", "+%s" % category )
        tc.submit( "create_repository_button" )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def delete_files_from_repository( self, repository, filenames=[], strings_displayed=[ 'were deleted from the repository' ], strings_not_displayed=[] ):
        files_to_delete = []
        basepath = self.get_repo_path( repository )
        repository_files = self.get_repository_file_list( base_path=basepath, current_path=None )
        # Verify that the files to delete actually exist in the repository.
        for filename in repository_files:
            if filename in filenames:
                files_to_delete.append( os.path.join( basepath, filename ) )
        self.browse_repository( repository )
        # Twill sets hidden form fields to read-only by default. We need to write to this field.
        form = tc.browser.get_form( 'select_files_to_delete' )
        form.find_control( "selected_files_to_delete" ).readonly = False
        tc.fv( "1", "selected_files_to_delete", ','.join( files_to_delete ) )
        tc.submit( 'select_files_to_delete_button' )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def display_manage_repository_page( self, repository, strings_displayed=[], strings_not_displayed=[] ):
        url = '/repository/manage_repository?id=%s' % self.security.encode_id( repository.id )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def display_repository_clone_page( self, owner_name, repository_name, strings_displayed=[], strings_not_displayed=[] ):
        url = '/repos/%s/%s' % ( owner_name, repository_name )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def display_repository_file_contents( self, repository, filename, filepath=None, strings_displayed=[], strings_not_displayed=[] ):
        '''Find a file in the repository and display the contents.'''
        basepath = self.get_repo_path( repository )
        repository_file_list = []
        if filepath:
            relative_path = os.path.join( basepath, filepath )
        else:
            relative_path = basepath
        repository_file_list = self.get_repository_file_list( base_path=relative_path, current_path=None )
        assert filename in repository_file_list, 'File %s not found in the repository under %s.' % ( filename, relative_path )
        url = '/repository/get_file_contents?file_path=%s' % os.path.join( relative_path, filename )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def edit_repository_categories( self, repository, categories_to_add=[], categories_to_remove=[], restore_original=True ):
        url = '/repository/manage_repository?id=%s' % self.security.encode_id( repository.id )
        self.visit_url( url )
        strings_displayed = []
        strings_not_displayed = []
        for category in categories_to_add:
            tc.fv( "2", "category_id", '+%s' % category)
            strings_displayed.append( "selected>%s" % category )
        for category in categories_to_remove:
            tc.fv( "2", "category_id", '-%s' % category)
            strings_not_displayed.append( "selected>%s" % category )
        tc.submit( "manage_categories_button" )
        self.check_for_strings( strings_displayed, strings_not_displayed )
        if restore_original:
            strings_displayed = []
            strings_not_displayed = []
            for category in categories_to_remove:
                tc.fv( "2", "category_id", '+%s' % category)
                strings_displayed.append( "selected>%s" % category )
            for category in categories_to_add:
                tc.fv( "2", "category_id", '-%s' % category)
                strings_not_displayed.append( "selected>%s" % category )
            tc.submit( "manage_categories_button" )
            self.check_for_strings( strings_displayed, strings_not_displayed )
    def edit_repository_information( self, repository, **kwd ):
        url = '/repository/manage_repository?id=%s' % self.security.encode_id( repository.id )
        self.visit_url( url )
        original_information = dict( repo_name=repository.name, description=repository.description, long_description=repository.long_description )
        strings_displayed = []
        strings_not_displayed = []
        for input_elem_name in [ 'repo_name', 'description', 'long_description' ]:
            if input_elem_name in kwd:
                tc.fv( "1", input_elem_name, kwd[ input_elem_name ] )
                strings_displayed.append( self.escape_html( kwd[ input_elem_name ] ) )
        tc.submit( "edit_repository_button" )
        self.check_for_strings( strings_displayed )
        strings_displayed = []
        for input_elem_name in [ 'repo_name', 'description', 'long_description' ]:
            tc.fv( "1", input_elem_name, original_information[ input_elem_name ] )
            strings_displayed.append( self.escape_html( original_information[ input_elem_name ] ) )
        tc.submit( "edit_repository_button" )
        self.check_for_strings( strings_displayed )
    def escape_html( self, string, unescape=False ):
        html_entities = [ ('&', 'X' ), ( "'", '&#39;' ), ( '"', '&#34;' ) ]
        for character, replacement in html_entities:
            if unescape:
                string = string.replace( replacement, character )
            else:
                string = string.replace( character, replacement )
        return string
    def generate_repository_dependency_xml( self, repository, xml_filename ):
        changeset_revision = self.get_repository_tip( repository )
        template_parser = string.Template( new_repository_dependencies_xml )
        repository_dependency_xml = template_parser.safe_substitute( toolshed_url=self.url,
                                                                     owner=repository.user.username,
                                                                     repository_name=repository.name,
                                                                     changeset_revision=changeset_revision )
        # Save the generated xml to test-data/emboss_5/repository_dependencies.xml.
        file( xml_filename, 'w' ).write( repository_dependency_xml )
    def get_latest_repository_metadata_for_repository( self, repository ):
        # TODO: This will not work as expected. Fix it.
        return repository.metadata_revisions[ 0 ]
    def get_repo_path( self, repository ):
        # An entry in the hgweb.config file looks something like: repos/test/mira_assembler = database/community_files/000/repo_123
        lhs = "repos/%s/%s" % ( repository.user.username, repository.name )
        try:
            return self.hgweb_config_manager.get_entry( lhs )
        except:
            raise Exception( "Entry for repository %s missing in hgweb config file %s." % ( lhs, self.hgweb_config_manager.hgweb_config ) )
    def get_repository_file_list( self, base_path, current_path=None ):
        '''Recursively load repository folder contents and append them to a list. Similar to os.walk but via /repository/open_folder.'''
        if current_path is None:
            request_param_path = base_path
        else:
            request_param_path = os.path.join( base_path, current_path )
        #request_param_path = request_param_path.replace( '/', '%2f' )
        # Get the current folder's contents.
        url = '/repository/open_folder?folder_path=%s' % request_param_path
        self.visit_url( url )
        file_list = from_json_string( self.last_page() )
        returned_file_list = []
        if current_path is not None:
            returned_file_list.append( current_path )
        # Loop through the json dict returned by /repository/open_folder.
        for file_dict in file_list:
            if file_dict[ 'isFolder' ]:
                # This is a folder. Get the contents of the folder and append it to the list, 
                # prefixed with the path relative to the repository root, if any.
                if current_path is None:
                    returned_file_list.extend( self.get_repository_file_list( base_path=base_path, current_path=file_dict[ 'title' ] ) )
                else:
                    sub_path = os.path.join( current_path, file_dict[ 'title' ] )
                    returned_file_list.extend( self.get_repository_file_list( base_path=base_path, current_path=sub_path ) )
            else:
                # This is a regular file, prefix the filename with the current path and append it to the list.
                if current_path is not None:
                    returned_file_list.append( os.path.join( current_path, file_dict[ 'title' ] ) )
                else:
                    returned_file_list.append( file_dict[ 'title' ] )
        return returned_file_list
    def get_repository_metadata( self, repository ):
        return [ metadata_revision for metadata_revision in repository.metadata_revisions ]
    def get_repository_metadata_revisions( self, repository ):
        return [ str( repository_metadata.changeset_revision ) for repository_metadata in repository.metadata_revisions ]
    def get_repository_tip( self, repository ):
        repo = hg.repository( ui.ui(), self.get_repo_path( repository ) )
        return str( repo.changectx( repo.changelog.tip() ) )
    def get_tools_from_repository_metadata( self, repository, include_invalid=False ):
        '''Get a list of valid and (optionally) invalid tool dicts from the repository metadata.'''
        valid_tools = []
        invalid_tools = []
        for repository_metadata in repository.metadata_revisions:
            if 'tools' in repository_metadata.metadata:
                valid_tools.append( dict( tools=repository_metadata.metadata[ 'tools' ], changeset_revision=repository_metadata.changeset_revision ) )
            if include_invalid and 'invalid_tools' in repository_metadata.metadata:
                invalid_tools.append( dict( tools=repository_metadata.metadata[ 'invalid_tools' ], changeset_revision=repository_metadata.changeset_revision ) )
        return valid_tools, invalid_tools
    def grant_write_access( self, repository, usernames=[], strings_displayed=[], strings_not_displayed=[] ):
        self.display_manage_repository_page( repository )
        tc.fv( "3", "allow_push", '-Select one' )
        for username in usernames:
            tc.fv( "3", "allow_push", '+%s' % username )
        tc.submit( 'user_access_button' )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def load_invalid_tool_page( self, repository, tool_xml, changeset_revision, strings_displayed=[], strings_not_displayed=[] ):
        url = '/repository/load_invalid_tool?repository_id=%s&tool_config=%s&changeset_revision=%s' % \
              ( self.security.encode_id( repository.id ), tool_xml, changeset_revision )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def load_display_tool_page( self, repository, tool_xml_path, changeset_revision, strings_displayed=[], strings_not_displayed=[] ):
        url = '/repository/display_tool?repository_id=%s&tool_config=%s&changeset_revision=%s' % \
              ( self.security.encode_id( repository.id ), tool_xml_path, changeset_revision )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def revoke_write_access( self, repository, username ):
        url = '/repository/manage_repository?user_access_button=Remove&id=%s&remove_auth=%s' % \
            ( self.security.encode_id( repository.id ), username )
        self.visit_url( url )
    def search_for_valid_tools( self, search_fields={}, exact_matches=False, strings_displayed=[], strings_not_displayed=[] ):
        for field_name, search_string in search_fields.items():
            url = '/repository/find_tools'
            self.visit_url( url )
            tc.fv( "1", "exact_matches", exact_matches )
            tc.fv( "1", field_name, search_string )
            tc.submit()
            self.check_for_strings( strings_displayed, strings_not_displayed ) 
    def set_repository_deprecated( self, repository, set_deprecated=True, strings_displayed=[], strings_not_displayed=[] ):
        url = '/repository/deprecate?id=%s&mark_deprecated=%s' % ( self.security.encode_id( repository.id ), set_deprecated )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def set_repository_malicious( self, repository, set_malicious=True, strings_displayed=[], strings_not_displayed=[] ):
        self.display_manage_repository_page( repository )
        tc.fv( "malicious", "malicious", set_malicious )
        tc.submit( "malicious_button" )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def tip_has_metadata( self, repository ):
        tip = self.get_repository_tip( repository )
        return get_repository_metadata_by_repository_id_changeset_revision( repository.id, tip )
    def upload_file( self, 
                     repository, 
                     filename, 
                     valid_tools_only=True, 
                     strings_displayed=[], 
                     strings_not_displayed=[],
                     **kwd ):
        self.visit_url( '/upload/upload?repository_id=%s' % self.security.encode_id( repository.id ) )
        if valid_tools_only:
            strings_displayed.append( "has been successfully uploaded to the repository." )
        for key in kwd:
            tc.fv( "1", key, kwd[ key ] )
        tc.formfile( "1", "file_data", self.get_filename( filename ) )
        tc.submit( "upload_button" )
        self.check_for_strings( strings_displayed, strings_not_displayed )
