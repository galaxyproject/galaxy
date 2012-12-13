import galaxy.webapps.community.util.hgweb_config
import galaxy.model as galaxy_model
import common, string, os, re
from base.twilltestcase import tc, from_json_string, TwillTestCase, security, urllib
from test_db_util import get_repository_by_name_and_owner, get_repository_metadata_by_repository_id_changeset_revision, \
                         get_galaxy_repository_by_name_owner_changeset_revision, get_installed_repository_by_name_owner

from galaxy import eggs
eggs.require('mercurial')
from mercurial import hg, ui

class ShedTwillTestCase( TwillTestCase ):
    def setUp( self ):
        # Security helper
        self.security = security.SecurityHelper( id_secret='changethisinproductiontoo' )
        self.history_id = None
        self.hgweb_config_dir = os.environ.get( 'TEST_HG_WEB_CONFIG_DIR' )
        self.hgweb_config_manager = galaxy.webapps.community.util.hgweb_config.HgWebConfigManager()
        self.hgweb_config_manager.hgweb_config_dir = self.hgweb_config_dir
        self.tool_shed_test_tmp_dir = os.environ.get( 'TOOL_SHED_TEST_TMP_DIR', None)
        self.host = os.environ.get( 'TOOL_SHED_TEST_HOST' )
        self.port = os.environ.get( 'TOOL_SHED_TEST_PORT' )
        self.url = "http://%s:%s" % ( self.host, self.port )
        self.galaxy_host = os.environ.get( 'GALAXY_TEST_HOST' )
        self.galaxy_port = os.environ.get( 'GALAXY_TEST_PORT' )
        self.galaxy_url = "http://%s:%s" % ( self.galaxy_host, self.galaxy_port )
        self.file_dir = os.environ.get( 'TOOL_SHED_TEST_FILE_DIR', None )
        self.tool_shed_test_file = None
        self.shed_tools_dict = {}
        self.home()
    def browse_category( self, category, strings_displayed=[], strings_not_displayed=[] ):
        url = '/repository/browse_valid_categories?sort=name&operation=valid_repositories_by_category&id=%s' % \
              self.security.encode_id( category.id )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def browse_repository( self, repository, strings_displayed=[], strings_not_displayed=[] ):
        url = '/repository/browse_repository?id=%s' % self.security.encode_id( repository.id )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def browse_tool_shed( self, url, strings_displayed=[], strings_not_displayed=[] ):
        self.visit_galaxy_url( '/admin_toolshed/browse_tool_shed?tool_shed_url=%s' % url )
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
    def check_installed_repository_tool_dependencies( self, installed_repository, dependencies_installed=False ):
        strings_not_displayed = []
        strings_displayed = []
        for dependency in installed_repository.metadata[ 'tool_dependencies' ]:
            tool_dependency = installed_repository.metadata[ 'tool_dependencies' ][ dependency ]
            strings_displayed.extend( [ tool_dependency[ 'name' ], tool_dependency[ 'version' ], tool_dependency[ 'type' ] ] )
            if dependencies_installed:
                strings_displayed.append( 'Installed' )
            else:
                strings_displayed.append( 'Never installed' )
        url = '/admin_toolshed/manage_repository?id=%s' % self.security.encode_id( installed_repository.id )
        self.visit_galaxy_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def check_repository_changelog( self, repository, strings_displayed=[], strings_not_displayed=[] ):
        url = '/repository/view_changelog?id=%s' % self.security.encode_id( repository.id )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def check_repository_dependency( self, repository, depends_on_repository, depends_on_changeset_revision, changeset_revision=None ):
        if changeset_revision is None:
            changeset_revision = self.get_repository_tip( repository )
        strings_displayed = [ depends_on_repository.name, depends_on_repository.user.username, depends_on_changeset_revision  ]
        self.display_manage_repository_page( repository, changeset_revision=changeset_revision, strings_displayed=strings_displayed )
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
    def create_user_in_galaxy( self, cntrller='user', email='test@bx.psu.edu', password='testuser', username='admin-user', redirect='' ):
        self.visit_galaxy_url( "/user/create?cntrller=%s&use_panels=False" % cntrller )
        tc.fv( '1', 'email', email )
        tc.fv( '1', 'redirect', redirect )
        tc.fv( '1', 'password', password )
        tc.fv( '1', 'confirm', password )
        tc.fv( '1', 'username', username )
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
    def display_installed_repository_manage_page( self, installed_repository, strings_displayed=[], strings_not_displayed=[] ):
        url = '/admin_toolshed/manage_repository?id=%s' % self.security.encode_id( installed_repository.id )
        self.visit_galaxy_url( url )
        strings_displayed.extend( [ installed_repository.name, 
                                    installed_repository.description, 
                                    installed_repository.owner, 
                                    installed_repository.tool_shed, 
                                    installed_repository.installed_changeset_revision ] )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def display_manage_repository_page( self, repository, changeset_revision=None, strings_displayed=[], strings_not_displayed=[] ):
        base_url = '/repository/manage_repository?id=%s' % self.security.encode_id( repository.id )
        if changeset_revision is not None:
            url = '%s&changeset_revision=%s' % ( base_url, changeset_revision )
        else:
            url = base_url
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
    def galaxy_login( self, email='test@bx.psu.edu', password='testuser', username='admin-user', redirect='' ):
        previously_created, username_taken, invalid_username = \
            self.create_user_in_galaxy( email=email, password=password, username=username, redirect=redirect )
        if previously_created:
            self.visit_galaxy_url( "/user/login?use_panels=False" )
            tc.fv( '1', 'email', email )
            tc.fv( '1', 'redirect', redirect )
            tc.fv( '1', 'password', password )
            tc.submit( 'login_button' )
    def galaxy_logout( self ):
        self.home()
        self.visit_galaxy_url( "/user/logout" )
        self.check_page_for_string( "You have been logged out" )
        self.home()

    def generate_repository_dependency_xml( self, repositories, xml_filename, dependency_description='' ):
        file_path = os.path.split( xml_filename )[0]
        if not os.path.exists( file_path ):
            os.makedirs( file_path )
        dependency_entries = []
        for repository in repositories:
            changeset_revision = self.get_repository_tip( repository )
            template = string.Template( common.new_repository_dependencies_line )
            dependency_entries.append( template.safe_substitute( toolshed_url=self.url,
                                                                 owner=repository.user.username,
                                                                 repository_name=repository.name,
                                                                 changeset_revision=changeset_revision ) )
        if dependency_description:
            description = ' description="%s"' % dependency_description
        else:
            description = dependency_description
        template_parser = string.Template( common.new_repository_dependencies_xml )
        repository_dependency_xml = template_parser.safe_substitute( description=description, dependency_lines='\n'.join( dependency_entries ) )
        # Save the generated xml to the specified location.
        file( xml_filename, 'w' ).write( repository_dependency_xml )
    def generate_temp_path( self, test_script_path, additional_paths=[] ):
        return os.path.join( self.tool_shed_test_tmp_dir, test_script_path, os.sep.join( additional_paths ) )
    def get_filename( self, filename, filepath=None ):
        if filepath is not None:
            return os.path.abspath( os.path.join( filepath, filename ) )
        else:
            return os.path.abspath( os.path.join( self.file_dir, filename ) )
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
    def install_repository( self, name, owner, install_tool_dependencies=False, changeset_revision=None, strings_displayed=[], strings_not_displayed=[] ):
        repository = get_repository_by_name_and_owner( name, owner )
        repository_id = self.security.encode_id( repository.id )
        if changeset_revision is None:
            changeset_revision = self.get_repository_tip( repository )
        url = '/repository/install_repositories_by_revision?changeset_revisions=%s&repository_ids=%s&galaxy_url=%s' % \
              ( changeset_revision, repository_id, self.galaxy_url )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )
        if 'install_tool_dependencies' in self.last_page():
            if install_tool_dependencies:
                tc.fv( '1', 'install_tool_dependencies', True )
            else:
                tc.fv( '1', 'install_tool_dependencies', False )
        tc.submit( 'select_tool_panel_section_button' )
        html = self.last_page()
        # Since the installation process is by necessity asynchronous, we have to get the parameters to 'manually' initiate the 
        # installation process. This regex will return the tool shed repository IDs in group(1), the encoded_kwd parameter in 
        # group(2), and the reinstalling flag in group(3) and pass them to the manage_repositories method in the Galaxy 
        # admin_toolshed controller.
        install_parameters = re.search( 'initiate_repository_installation\( "([^"]+)", "([^"]+)", "([^"]+)" \);', html )
        iri_ids = install_parameters.group(1)
        encoded_kwd = install_parameters.group(2)
        reinstalling = install_parameters.group(3)
        url = '/admin_toolshed/manage_repositories?operation=install&tool_shed_repository_ids=%s&encoded_kwd=%s&reinstalling=%s' % \
            ( iri_ids, encoded_kwd, reinstalling )
        self.visit_galaxy_url( url )
        self.wait_for_repository_installation( repository, changeset_revision )
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
    def preview_repository_in_tool_shed( self, name, owner, changeset_revision=None, strings_displayed=[], strings_not_displayed=[] ):
        repository = get_repository_by_name_and_owner( name, owner )
        if changeset_revision is None:
            changeset_revision = self.get_repository_tip( repository )
        self.visit_url( '/repository/preview_tools_in_changeset?repository_id=%s&changeset_revision=%s' % \
                        ( self.security.encode_id( repository.id ), changeset_revision ) )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def repository_is_new( self, repository ):
        repo = hg.repository( ui.ui(), self.get_repo_path( repository ) )
        tip_ctx = repo.changectx( repo.changelog.tip() )
        return tip_ctx.rev() < 0
    def reset_repository_metadata( self, repository ):
        url = '/repository/reset_all_metadata?id=%s' % self.security.encode_id( repository.id )
        self.visit_url( url )
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
                     filepath=None,
                     valid_tools_only=True, 
                     strings_displayed=[], 
                     strings_not_displayed=[],
                     **kwd ):
        self.visit_url( '/upload/upload?repository_id=%s' % self.security.encode_id( repository.id ) )
        if valid_tools_only:
            strings_displayed.extend( [ 'has been successfully', 'uploaded to the repository.' ] )
        for key in kwd:
            tc.fv( "1", key, kwd[ key ] )
        tc.formfile( "1", "file_data", self.get_filename( filename, filepath ) )
        tc.submit( "upload_button" )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def verify_installed_repository_on_browse_page( self, installed_repository, strings_displayed=[], strings_not_displayed=[] ):
        url = '/admin_toolshed/browse_repositories'
        self.visit_galaxy_url( url )
        strings_displayed.extend( [ installed_repository.name, 
                                    installed_repository.description, 
                                    installed_repository.owner, 
                                    installed_repository.tool_shed, 
                                    installed_repository.installed_changeset_revision ] )
        self.check_for_strings( strings_displayed, strings_not_displayed )
    def verify_tool_metadata_for_installed_repository( self, installed_repository, strings_displayed=[], strings_not_displayed=[] ):
        repository_id = self.security.encode_id( installed_repository.id )
        for tool in installed_repository.metadata[ 'tools' ]:
            strings = list( strings_displayed )
            strings.extend( [ tool[ 'id' ], tool[ 'description' ], tool[ 'version' ], tool[ 'guid' ], tool[ 'name' ] ] )
            url = '/admin_toolshed/view_tool_metadata?repository_id=%s&tool_id=%s' % ( repository_id, urllib.quote_plus( tool[ 'id' ] ) )
            self.visit_galaxy_url( url )
            self.check_for_strings( strings, strings_not_displayed )
    def visit_galaxy_url( self, url ):
        url = '%s%s' % ( self.galaxy_url, url )
        self.visit_url( url )
    def wait_for_repository_installation( self, repository, changeset_revision ):
        final_states = [ galaxy_model.ToolShedRepository.installation_status.ERROR,
                         galaxy_model.ToolShedRepository.installation_status.INSTALLED, 
                         galaxy_model.ToolShedRepository.installation_status.UNINSTALLED,
                         galaxy_model.ToolShedRepository.installation_status.DEACTIVATED ]
        repository_name = repository.name
        owner = repository.user.username
        if changeset_revision is None:
            changeset_revision = self.get_repository_tip( repository )
        galaxy_repository = get_galaxy_repository_by_name_owner_changeset_revision( repository_name, owner, changeset_revision )
        timeout_counter = 0
        while galaxy_repository.status not in final_states:
            ga_refresh( galaxy_repository )
            timeout_counter = timeout_counter + 1
            if timeout_counter > common.repository_installation_timeout:
                raise AssertionError( 'Repository installation timed out, %d seconds elapsed, repository state is %s.' % \
                                      ( timeout_counter, repository.status ) )
                break
            time.sleep( 1 )
