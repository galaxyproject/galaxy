import logging
import os
import re
import shutil
import string
import tarfile
import tempfile
import time
from json import loads

import twill.commands as tc
from mercurial import commands, hg, ui
from six.moves.urllib.parse import quote_plus, urlencode

import galaxy.model.tool_shed_install as galaxy_model
import galaxy.util
import galaxy.webapps.tool_shed.util.hgweb_config
from base.tool_shed_util import repository_installation_timeout
from base.twilltestcase import TwillTestCase
from galaxy.web import security
from tool_shed.util import hg_util, xml_util
from tool_shed.util.encoding_util import tool_shed_encode

from . import common, test_db_util

log = logging.getLogger( __name__ )


class ShedTwillTestCase( TwillTestCase ):

    def setUp( self ):
        # Security helper
        self.security = security.SecurityHelper( id_secret='changethisinproductiontoo' )
        self.history_id = None
        self.hgweb_config_dir = os.environ.get( 'TEST_HG_WEB_CONFIG_DIR' )
        self.hgweb_config_manager = galaxy.webapps.tool_shed.util.hgweb_config.HgWebConfigManager()
        self.hgweb_config_manager.hgweb_config_dir = self.hgweb_config_dir
        self.tool_shed_test_tmp_dir = os.environ.get( 'TOOL_SHED_TEST_TMP_DIR', None)
        self.host = os.environ.get( 'TOOL_SHED_TEST_HOST' )
        self.port = os.environ.get( 'TOOL_SHED_TEST_PORT' )
        self.url = "http://%s:%s" % ( self.host, self.port )
        self.galaxy_host = os.environ.get( 'GALAXY_TEST_HOST' )
        self.galaxy_port = os.environ.get( 'GALAXY_TEST_PORT' )
        self.galaxy_url = "http://%s:%s" % ( self.galaxy_host, self.galaxy_port )
        self.shed_tool_data_table_conf = os.environ.get( 'TOOL_SHED_TEST_TOOL_DATA_TABLE_CONF' )
        self.file_dir = os.environ.get( 'TOOL_SHED_TEST_FILE_DIR', None )
        self.tool_data_path = os.environ.get( 'GALAXY_TEST_TOOL_DATA_PATH' )
        self.shed_tool_conf = os.environ.get( 'GALAXY_TEST_SHED_TOOL_CONF' )
        self.test_db_util = test_db_util
        # TODO: Figure out a way to alter these attributes during tests.
        self.galaxy_tool_dependency_dir = os.environ.get( 'GALAXY_TEST_TOOL_DEPENDENCY_DIR' )

    def add_repository_review_component( self, **kwd ):
        url = '/repository_review/create_component?operation=create'
        self.visit_url( url )
        self.submit_form( 1, 'create_component_button', **kwd )

    def assign_admin_role( self, repository, user ):
        # As elsewhere, twill limits the possibility of submitting the form, this time due to not executing the javascript
        # attached to the role selection form. Visit the action url directly with the necessary parameters.
        url = '/repository/manage_repository_admins?id=%s&in_users=%d&manage_role_associations_button=Save' % \
            ( self.security.encode_id( repository.id ), user.id )
        self.visit_url( url )
        self.check_for_strings( strings_displayed=[ 'Role', 'has been associated' ] )

    def browse_category( self, category, strings_displayed=None, strings_not_displayed=None ):
        url = '/repository/browse_valid_categories?sort=name&operation=valid_repositories_by_category&id=%s' % \
              self.security.encode_id( category.id )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def browse_component_review( self, review, strings_displayed=None, strings_not_displayed=None ):
        url = '/repository_review/browse_review?id=%s' % self.security.encode_id( review.id )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def browse_custom_datatypes( self, strings_displayed=None, strings_not_displayed=None ):
        url = '/repository/browse_datatypes'
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def browse_repository( self, repository, strings_displayed=None, strings_not_displayed=None ):
        url = '/repository/browse_repository?id=%s' % self.security.encode_id( repository.id )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def browse_repository_dependencies( self, strings_displayed=None, strings_not_displayed=None ):
        url = '/repository/browse_repository_dependencies'
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def browse_tool_shed( self, url, strings_displayed=None, strings_not_displayed=None ):
        self.visit_galaxy_url( '/admin_toolshed/browse_tool_shed?tool_shed_url=%s' % url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def browse_tool_dependencies( self, strings_displayed=None, strings_not_displayed=None ):
        url = '/repository/browse_tool_dependencies'
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def browse_tools( self, strings_displayed=None, strings_not_displayed=None ):
        url = '/repository/browse_tools'
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def check_count_of_metadata_revisions_associated_with_repository( self, repository, metadata_count ):
        self.check_repository_changelog( repository )
        self.check_string_count_in_page( 'Repository metadata is associated with this change set.', metadata_count )

    def check_exported_repository_dependency( self, dependency_filename, repository_name, repository_owner ):
        root, error_message = xml_util.parse_xml( dependency_filename )
        for elem in root.findall( 'repository' ):
            if 'changeset_revision' in elem:
                raise AssertionError( 'Exported repository %s with owner %s has a dependency with a defined changeset revision.' %
                                      ( repository_name, repository_owner ) )
            if 'toolshed' in elem:
                raise AssertionError( 'Exported repository %s with owner %s has a dependency with a defined tool shed.' %
                                      ( repository_name, repository_owner ) )

    def check_for_valid_tools( self, repository, strings_displayed=None, strings_not_displayed=None ):
        if strings_displayed is None:
            strings_displayed = [ 'Valid tools' ]
        else:
            strings_displayed.append( 'Valid tools' )
        self.display_manage_repository_page( repository, strings_displayed, strings_not_displayed )

    def check_galaxy_repository_db_status( self, repository_name, owner, expected_status ):
        installed_repository = test_db_util.get_installed_repository_by_name_owner( repository_name, owner )
        assert installed_repository.status == expected_status, 'Status in database is %s, expected %s' % \
            ( installed_repository.status, expected_status )

    def check_galaxy_repository_tool_panel_section( self, repository, expected_tool_panel_section ):
        metadata = repository.metadata
        assert 'tools' in metadata, 'Tools not found in repository metadata: %s' % metadata
        # If integrated_tool_panel.xml is to be tested, this test method will need to be enhanced to handle tools
        # from the same repository in different tool panel sections. Getting the first tool guid is ok, because
        # currently all tools contained in a single repository will be loaded into the same tool panel section.
        if repository.status in [ galaxy_model.ToolShedRepository.installation_status.UNINSTALLED,
                                  galaxy_model.ToolShedRepository.installation_status.DEACTIVATED ]:
            tool_panel_section = self.get_tool_panel_section_from_repository_metadata( metadata )
        else:
            tool_panel_section = self.get_tool_panel_section_from_api( metadata )
        assert tool_panel_section == expected_tool_panel_section, 'Expected to find tool panel section *%s*, but instead found *%s*\nMetadata: %s\n' % \
            ( expected_tool_panel_section, tool_panel_section, metadata )

    def check_installed_repository_tool_dependencies( self,
                                                      installed_repository,
                                                      strings_displayed=None,
                                                      strings_not_displayed=None,
                                                      dependencies_installed=False ):
        # Tool dependencies are not being installed in these functional tests. If this is changed, the test method will also need to be updated.
        if not dependencies_installed:
            strings_displayed.append( 'Missing tool dependencies' )
        else:
            strings_displayed.append( 'Tool dependencies' )
        if dependencies_installed:
            strings_displayed.append( 'Installed' )
        else:
            strings_displayed.append( 'Never installed' )
        url = '/admin_toolshed/manage_repository?id=%s' % self.security.encode_id( installed_repository.id )
        self.visit_galaxy_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def check_manifest( self, manifest_filepath, owner=None ):
        root, error_message = xml_util.parse_xml( manifest_filepath )
        for elem in root.findall( 'repository' ):
            repository_name = elem.get( 'name' )
            manifest_owner = elem.get( 'username' )
            if owner is not None:
                assert manifest_owner == owner, 'Expected repository %s to be owned by %s, but found %s' % \
                    ( elem.get( 'name' ), owner, manifest_owner )
            toolshed = elem.get( 'toolshed' )
            changeset_revision = elem.get( 'changeset_revision' )
            assert toolshed is None, 'Repository definition %s has a tool shed attribute %s.' % ( repository_name, toolshed )
            assert changeset_revision is None, 'Repository definition %s specifies a changeset revision %s.' % \
                ( repository_name, changeset_revision )
            repository_archive = elem.find( 'archive' ).text
            filepath, filename = os.path.split( manifest_filepath )
            repository_path = os.path.join( filepath, repository_archive )
            self.verify_repository_in_capsule( repository_path, repository_name, owner )

    def check_repository_changelog( self, repository, strings_displayed=None, strings_not_displayed=None ):
        url = '/repository/view_changelog?id=%s' % self.security.encode_id( repository.id )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def check_repository_dependency( self, repository, depends_on_repository, depends_on_changeset_revision=None, changeset_revision=None ):
        strings_displayed = [ depends_on_repository.name, depends_on_repository.user.username  ]
        if depends_on_changeset_revision:
            strings_displayed.append( depends_on_changeset_revision )
        self.display_manage_repository_page( repository, changeset_revision=changeset_revision, strings_displayed=strings_displayed )

    def check_repository_metadata( self, repository, tip_only=True ):
        if tip_only:
            assert self.tip_has_metadata( repository ) and len( self.get_repository_metadata_revisions( repository ) ) == 1, \
                'Repository tip is not a metadata revision: Repository tip - %s, metadata revisions - %s.'
        else:
            assert len( self.get_repository_metadata_revisions( repository ) ) > 0, \
                'Repository tip is not a metadata revision: Repository tip - %s, metadata revisions - %s.' % \
                ( self.get_repository_tip( repository ), ', '.join( self.get_repository_metadata_revisions( repository ) ) )

    def check_repository_tools_for_changeset_revision( self, repository, changeset_revision, tool_metadata_strings_displayed=None, tool_page_strings_displayed=None ):
        '''
        Loop through each tool dictionary in the repository metadata associated with the received changeset_revision.
        For each of these, check for a tools attribute, and load the tool metadata page if it exists, then display that tool's page.
        '''
        test_db_util.refresh( repository )
        repository_metadata = self.get_repository_metadata_by_changeset_revision( repository, changeset_revision )
        metadata = repository_metadata.metadata
        if 'tools' not in metadata:
            raise AssertionError( 'No tools in %s revision %s.' % ( repository.name, changeset_revision ) )
        for tool_dict in metadata[ 'tools' ]:
            tool_id = tool_dict[ 'id' ]
            tool_xml = tool_dict[ 'tool_config' ]
            url = '/repository/view_tool_metadata?repository_id=%s&changeset_revision=%s&tool_id=%s' % \
                  ( self.security.encode_id( repository.id ), changeset_revision, tool_id )
            self.visit_url( url )
            self.check_for_strings( tool_metadata_strings_displayed )
            self.load_display_tool_page( repository, tool_xml_path=tool_xml,
                                         changeset_revision=changeset_revision,
                                         strings_displayed=tool_page_strings_displayed,
                                         strings_not_displayed=None )

    def check_repository_invalid_tools_for_changeset_revision( self, repository, changeset_revision, strings_displayed=None, strings_not_displayed=None ):
        '''Load the invalid tool page for each invalid tool associated with this changeset revision and verify the received error messages.'''
        repository_metadata = self.get_repository_metadata_by_changeset_revision( repository, changeset_revision )
        metadata = repository_metadata.metadata
        assert 'invalid_tools' in metadata, 'Metadata for changeset revision %s does not define invalid tools' % changeset_revision
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

    def clone_repository( self, repository, destination_path ):
        url = '%s/repos/%s/%s' % ( self.url, repository.user.username, repository.name )
        success, message = hg_util.clone_repository( url, destination_path, self.get_repository_tip( repository ) )
        assert success is True, message

    def commit_and_push( self, repository, hgrepo, options, username, password ):
        url = 'http://%s:%s@%s:%s/repos/%s/%s' % ( username, password, self.host, self.port, repository.user.username, repository.name )
        commands.commit( ui.ui(), hgrepo, **options )
        #  Try pushing multiple times as it transiently fails on Jenkins.
        #  TODO: Figure out why that happens
        for i in range(5):
            try:
                commands.push( ui.ui(), hgrepo, dest=url )
            except Exception as e:
                if str(e).find('Pushing to Tool Shed is disabled') != -1:
                    return False
            else:
                return True
        raise

    def create_category( self, **kwd ):
        category = test_db_util.get_category_by_name( kwd[ 'name' ] )
        if category is None:
            self.visit_url( '/admin/manage_categories?operation=create' )
            self.submit_form( form_no=1, button="create_category_button", **kwd )
            category = test_db_util.get_category_by_name( kwd[ 'name' ] )
        return category

    def create_repository_dependency( self,
                                      repository=None,
                                      repository_tuples=[],
                                      filepath=None,
                                      prior_installation_required=False,
                                      complex=False,
                                      package=None,
                                      version=None,
                                      strings_displayed=None,
                                      strings_not_displayed=None ):
        repository_names = []
        if complex:
            filename = 'tool_dependencies.xml'
            self.generate_complex_dependency_xml( filename=filename, filepath=filepath, repository_tuples=repository_tuples, package=package, version=version )
        else:
            for toolshed_url, name, owner, changeset_revision in repository_tuples:
                repository_names.append( name )
            dependency_description = '%s depends on %s.' % ( repository.name, ', '.join( repository_names ) )
            filename = 'repository_dependencies.xml'
            self.generate_simple_dependency_xml( repository_tuples=repository_tuples,
                                                 filename=filename,
                                                 filepath=filepath,
                                                 dependency_description=dependency_description,
                                                 prior_installation_required=prior_installation_required )
        self.upload_file( repository,
                          filename=filename,
                          filepath=filepath,
                          valid_tools_only=False,
                          uncompress_file=False,
                          remove_repo_files_not_in_tar=False,
                          commit_message='Uploaded dependency on %s.' % ', '.join( repository_names ),
                          strings_displayed=None,
                          strings_not_displayed=None )

    def create_repository_review( self, repository, review_contents_dict, changeset_revision=None, copy_from=None):
        strings_displayed = []
        if not copy_from:
            strings_displayed.append( 'Begin your review' )
        strings_not_displayed = []
        if not changeset_revision:
            changeset_revision = self.get_repository_tip( repository )
        url = '/repository_review/create_review?changeset_revision=%s&id=%s' % ( changeset_revision, self.security.encode_id( repository.id ) )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )
        strings_displayed = []
        if copy_from:
            old_changeset_revision, review_id = copy_from
            strings_displayed = [ 'You have elected to create a new review', 'Select previous revision', changeset_revision ]
            self.check_for_strings( strings_displayed )
            strings_displayed = []
            url = '/repository_review/create_review?changeset_revision=%s&id=%s&previous_review_id=%s' % \
                ( self.get_repository_tip( repository ), self.security.encode_id( repository.id ), self.security.encode_id( review_id ) )
            self.visit_url( url )
        self.fill_review_form( review_contents_dict, strings_displayed, strings_not_displayed )

    def create_user_in_galaxy( self, cntrller='user', email='test@bx.psu.edu', password='testuser', username='admin-user', redirect='' ):
        self.visit_galaxy_url( "/user/create?cntrller=%s&use_panels=False" % cntrller )
        self.submit_form( '1', 'create_user_button', email=email, password=password, confirm=password, username=username, redirect=redirect )
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

    def deactivate_repository( self, installed_repository, strings_displayed=None, strings_not_displayed=None ):
        url = '/admin_toolshed/deactivate_or_uninstall_repository?id=%s' % self.security.encode_id( installed_repository.id )
        self.visit_galaxy_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )
        form = tc.browser.get_form( 'deactivate_or_uninstall_repository' )
        self.set_form_value( form, {}, 'remove_from_disk', False )
        tc.submit( 'deactivate_or_uninstall_repository_button' )
        strings_displayed = [ 'The repository named', 'has been deactivated' ]
        self.check_for_strings( strings_displayed, strings_not_displayed=None )

    def delete_files_from_repository( self, repository, filenames=[], strings_displayed=[ 'were deleted from the repository' ], strings_not_displayed=None ):
        files_to_delete = []
        basepath = self.get_repo_path( repository )
        repository_files = self.get_repository_file_list( repository=repository, base_path=basepath, current_path=None )
        # Verify that the files to delete actually exist in the repository.
        for filename in repository_files:
            if filename in filenames:
                files_to_delete.append( os.path.join( basepath, filename ) )
        self.browse_repository( repository )
        # Twill sets hidden form fields to read-only by default. We need to write to this field.
        form = tc.browser.get_form( 'select_files_to_delete' )
        form.find_control( "selected_files_to_delete" ).readonly = False
        tc.fv( "2", "selected_files_to_delete", ','.join( files_to_delete ) )
        tc.submit( 'select_files_to_delete_button' )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def delete_repository( self, repository ):
        repository_id = self.security.encode_id( repository.id )
        self.visit_url( '/admin/browse_repositories' )
        url = '/admin/browse_repositories?operation=Delete&id=%s' % repository_id
        strings_displayed = [ 'Deleted 1 repository', repository.name ]
        strings_not_displayed = []
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def display_all_workflows( self, strings_displayed=None, strings_not_displayed=None ):
        url = '/workflow'
        self.visit_galaxy_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def display_galaxy_browse_repositories_page( self, strings_displayed=None, strings_not_displayed=None ):
        url = '/admin_toolshed/browse_repositories'
        self.visit_galaxy_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def display_installed_manage_data_manager_page( self, installed_repository, data_manager_names=None, strings_displayed=None, strings_not_displayed=None ):
        data_managers = installed_repository.metadata.get( 'data_manager', {} ).get( 'data_managers', {} )
        if data_manager_names:
            if not isinstance( data_manager_names, list ):
                data_manager_names = [data_manager_names]
            for data_manager_name in data_manager_names:
                assert data_manager_name in data_managers, "The requested Data Manager '%s' was not found in repository metadata." % data_manager_name
        else:
            data_manager_name = list(data_managers.keys())
        for data_manager_name in data_manager_names:
            url = '/data_manager/manage_data_manager?id=%s' % data_managers[data_manager_name]['guid']
            self.visit_galaxy_url( url )
            self.check_for_strings( strings_displayed, strings_not_displayed )

    def display_installed_repository_manage_page( self, installed_repository, strings_displayed=None, strings_not_displayed=None ):
        if strings_displayed is None:
            strings_displayed = []
        if strings_not_displayed is None:
            strings_not_displayed = []
        url = '/admin_toolshed/manage_repository?id=%s' % self.security.encode_id( installed_repository.id )
        self.visit_galaxy_url( url )
        strings_displayed.append( str( installed_repository.installed_changeset_revision ) )
        # Every place Galaxy's XXXX tool appears in attribute - need to quote.
        strings_displayed = [x.replace("'", "&#39;") for x in strings_displayed]
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def display_installed_workflow_image( self, repository, workflow_name, strings_displayed=None, strings_not_displayed=None ):
        url = '/admin_toolshed/generate_workflow_image?repository_id=%s&workflow_name=%s' % \
              ( self.security.encode_id( repository.id ), tool_shed_encode( workflow_name ) )
        self.visit_galaxy_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def display_manage_repository_page( self, repository, changeset_revision=None, strings_displayed=None, strings_not_displayed=None ):
        base_url = '/repository/manage_repository?id=%s' % self.security.encode_id( repository.id )
        if changeset_revision:
            url = '%s&changeset_revision=%s' % ( base_url, changeset_revision )
        else:
            changeset_revision = self.get_repository_tip( repository )
            url = base_url
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def display_repository_clone_page( self, owner_name, repository_name, strings_displayed=None, strings_not_displayed=None ):
        url = '/repos/%s/%s' % ( owner_name, repository_name )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def display_repository_file_contents( self, repository, filename, filepath=None, strings_displayed=None, strings_not_displayed=None ):
        '''Find a file in the repository and display the contents.'''
        basepath = self.get_repo_path( repository )
        repository_file_list = []
        if filepath:
            relative_path = os.path.join( basepath, filepath )
        else:
            relative_path = basepath
        repository_file_list = self.get_repository_file_list( repository=repository, base_path=relative_path, current_path=None )
        assert filename in repository_file_list, 'File %s not found in the repository under %s.' % ( filename, relative_path )
        params = dict( file_path=os.path.join( relative_path, filename ), repository_id=self.security.encode_id( repository.id ) )
        url = '/repository/get_file_contents'
        self.visit_url( url, params=params )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def display_reviewed_repositories_owned_by_user( self, strings_displayed=None, strings_not_displayed=None ):
        url = '/repository_review/reviewed_repositories_i_own'
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def display_repository_reviews_by_user( self, user, strings_displayed=None, strings_not_displayed=None ):
        url = '/repository_review/repository_reviews_by_user?id=%s' % self.security.encode_id( user.id )
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

    def edit_repository_information( self, repository, revert=True, **kwd ):
        url = '/repository/manage_repository?id=%s' % self.security.encode_id( repository.id )
        self.visit_url( url )
        original_information = dict( repo_name=repository.name, description=repository.description, long_description=repository.long_description )
        strings_displayed = []
        for input_elem_name in [ 'repo_name', 'description', 'long_description', 'repository_type' ]:
            if input_elem_name in kwd:
                tc.fv( "edit_repository", input_elem_name, kwd[ input_elem_name ] )
                strings_displayed.append( self.escape_html( kwd[ input_elem_name ] ) )
        tc.submit( "edit_repository_button" )
        self.check_for_strings( strings_displayed )
        if revert:
            strings_displayed = []
            for input_elem_name in [ 'repo_name', 'description', 'long_description' ]:
                tc.fv( "edit_repository", input_elem_name, original_information[ input_elem_name ] )
                strings_displayed.append( self.escape_html( original_information[ input_elem_name ] ) )
            tc.submit( "edit_repository_button" )
            self.check_for_strings( strings_displayed )

    def enable_email_alerts( self, repository, strings_displayed=None, strings_not_displayed=None ):
        repository_id = self.security.encode_id( repository.id )
        params = dict( operation='Receive email alerts', id=repository_id )
        self.visit_url( '/repository/browse_repositories', params )
        self.check_for_strings( strings_displayed )

    def escape_html( self, string, unescape=False ):
        html_entities = [ ('&', 'X' ), ( "'", '&#39;' ), ( '"', '&#34;' ) ]
        for character, replacement in html_entities:
            if unescape:
                string = string.replace( replacement, character )
            else:
                string = string.replace( character, replacement )
        return string

    def expect_repo_created_strings( self, name ):
        return [
            'Repository <b>%s</b>' % name,
            'Repository <b>%s</b> has been created' % name,
        ]

    def export_capsule( self, repository, aggressive=True, includes_dependencies=None ):
        # TODO: Remove this method and restore _exort_capsule as export_capsule
        # after transient problem is fixed.
        if not aggressive:
            return self._export_capsule(repository, includes_dependencies=includes_dependencies)
        else:
            try:
                return self._export_capsule(repository, includes_dependencies=includes_dependencies)
            except Exception:
                # Empirically this fails occasionally, we don't know
                # why however.
                time.sleep(1)
                return self._export_capsule( repository, includes_dependencies=includes_dependencies)

    def _export_capsule( self, repository, includes_dependencies=None ):
        url = '/repository/export?repository_id=%s&changeset_revision=%s' % \
            ( self.security.encode_id( repository.id ), self.get_repository_tip( repository ) )
        self.visit_url( url )
        log.info( "Visited url %s looking for export capsule button" % url )
        self.check_page_for_string( "Repository '" )
        self.check_page_for_string( "Export" )
        # Explicit check for True/False since None means we don't know if this
        # includes dependencies and so we skip both checks...
        if includes_dependencies is True:
            self.check_page_for_string( "Export repository dependencies?" )
        elif includes_dependencies is False:
            self.check_page_for_string( "No repository dependencies are defined for revision" )
        self.submit_form( 'export_repository', 'export_repository_button' )
        fd, capsule_filename = tempfile.mkstemp()
        os.close( fd )
        with open( capsule_filename, 'w' ) as f:
            f.write( self.last_page() )
        return capsule_filename

    def fetch_repository_metadata( self, repository, strings_displayed=None, strings_not_displayed=None ):
        url = '/api/repositories/%s/metadata' % self.security.encode_id( repository.id )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def fill_review_form( self, review_contents_dict, strings_displayed=None, strings_not_displayed=None ):
        kwd = dict()
        changed = False
        for label, contents in review_contents_dict.items():
            if contents:
                changed = True
                kwd[ '%s__ESEP__comment' % label ] = contents[ 'comment' ]
                kwd[ '%s__ESEP__rating' % label ] = contents[ 'rating' ]
                if 'private' in contents:
                    kwd[ '%s__ESEP__private' % label ] = contents[ 'private' ]
                kwd[ '%s__ESEP__approved' % label ] = contents[ 'approved' ]
            else:
                kwd[ '%s__ESEP__approved' % label ] = 'not_applicable'
        self.check_for_strings( strings_displayed, strings_not_displayed )
        self.submit_form( 1, 'Workflows__ESEP__review_button', **kwd )
        if changed:
            strings_displayed.append( 'Reviews were saved' )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def galaxy_login( self, email='test@bx.psu.edu', password='testuser', username='admin-user', redirect='', logout_first=True ):
        if logout_first:
            self.galaxy_logout()
        previously_created, username_taken, invalid_username = \
            self.create_user_in_galaxy( email=email, password=password, username=username, redirect=redirect )
        if previously_created:
            self.visit_galaxy_url( "/user/login?use_panels=False" )
            self.submit_form( '1', 'login_button', login=email, redirect=redirect, password=password )

    def galaxy_logout( self ):
        self.visit_galaxy_url( "/user/logout" )
        self.check_page_for_string( "You have been logged out" )
        tc.browser.cj.clear()

    def generate_complex_dependency_xml( self, filename, filepath, repository_tuples, package, version ):
        file_path = os.path.join( filepath, filename )
        dependency_entries = []
        template = string.Template( common.new_repository_dependencies_line )
        for toolshed_url, name, owner, changeset_revision in repository_tuples:
            dependency_entries.append( template.safe_substitute( toolshed_url=toolshed_url,
                                                                 owner=owner,
                                                                 repository_name=name,
                                                                 changeset_revision=changeset_revision,
                                                                 prior_installation_required='' ) )
        if not os.path.exists( filepath ):
            os.makedirs( filepath )
        dependency_template = string.Template( common.complex_repository_dependency_template )
        repository_dependency_xml = dependency_template.safe_substitute( package=package, version=version, dependency_lines='\n'.join( dependency_entries ) )
        # Save the generated xml to the specified location.
        open( file_path, 'w' ).write( repository_dependency_xml )

    def generate_simple_dependency_xml( self,
                                        repository_tuples,
                                        filename,
                                        filepath,
                                        dependency_description='',
                                        complex=False,
                                        package=None,
                                        version=None,
                                        prior_installation_required=False ):
        if not os.path.exists( filepath ):
            os.makedirs( filepath )
        dependency_entries = []
        if prior_installation_required:
            prior_installation_value = ' prior_installation_required="True"'
        else:
            prior_installation_value = ''
        for toolshed_url, name, owner, changeset_revision in repository_tuples:
            template = string.Template( common.new_repository_dependencies_line )
            dependency_entries.append( template.safe_substitute( toolshed_url=toolshed_url,
                                                                 owner=owner,
                                                                 repository_name=name,
                                                                 changeset_revision=changeset_revision,
                                                                 prior_installation_required=prior_installation_value ) )
        if dependency_description:
            description = ' description="%s"' % dependency_description
        else:
            description = dependency_description
        template_parser = string.Template( common.new_repository_dependencies_xml )
        repository_dependency_xml = template_parser.safe_substitute( description=description, dependency_lines='\n'.join( dependency_entries ) )
        # Save the generated xml to the specified location.
        full_path = os.path.join( filepath, filename )
        open( full_path, 'w' ).write( repository_dependency_xml )

    def generate_temp_path( self, test_script_path, additional_paths=[] ):
        temp_path = os.path.join( self.tool_shed_test_tmp_dir, test_script_path, os.sep.join( additional_paths ) )
        if not os.path.exists( temp_path ):
            os.makedirs( temp_path )
        return temp_path

    def get_datatypes_count( self ):
        url = '/api/datatypes?upload_only=false'
        self.visit_galaxy_url( url )
        html = self.last_page()
        datatypes = loads( html )
        return len( datatypes )

    def get_env_sh_path( self, tool_dependency_name, tool_dependency_version, repository ):
        '''Return the absolute path to an installed repository's env.sh file.'''
        env_sh_path = os.path.join( self.get_tool_dependency_path( tool_dependency_name, tool_dependency_version, repository ),
                                    'env.sh' )
        return env_sh_path

    def get_filename( self, filename, filepath=None ):
        if filepath is not None:
            return os.path.abspath( os.path.join( filepath, filename ) )
        else:
            return os.path.abspath( os.path.join( self.file_dir, filename ) )

    def get_hg_repo( self, path ):
        return hg.repository( ui.ui(), path )

    def get_last_reviewed_revision_by_user( self, user, repository ):
        changelog_tuples = self.get_repository_changelog_tuples( repository )
        reviews = test_db_util.get_reviews_ordered_by_changeset_revision( repository.id, changelog_tuples, reviewer_user_id=user.id )
        if reviews:
            last_review = reviews[ -1 ]
        else:
            last_review = None
        return last_review

    def get_repositories_category_api( self, categories, strings_displayed=None, strings_not_displayed=None ):
        for category in categories:
            url = '/api/categories/%s/repositories' % self.security.encode_id( category.id )
            self.visit_url( url )
            self.check_for_strings( strings_displayed, strings_not_displayed )

    def get_tool_dependency_path( self, tool_dependency_name, tool_dependency_version, repository ):
        '''Return the absolute path for an installed tool dependency.'''
        return os.path.join( self.galaxy_tool_dependency_dir,
                             tool_dependency_name,
                             tool_dependency_version,
                             repository.owner,
                             repository.name,
                             repository.installed_changeset_revision )

    def get_or_create_repository( self, owner=None, strings_displayed=None, strings_not_displayed=None, **kwd ):
        # If not checking for a specific string, it should be safe to assume that
        # we expect repository creation to be successful.
        if strings_displayed is None:
            strings_displayed = [ 'Repository', kwd[ 'name' ], 'has been created' ]
        if strings_not_displayed is None:
            strings_not_displayed = []
        repository = test_db_util.get_repository_by_name_and_owner( kwd[ 'name' ], owner )
        if repository is None:
            self.visit_url( '/repository/create_repository' )
            self.submit_form( 1, 'create_repository_button', **kwd )
            self.check_for_strings( strings_displayed, strings_not_displayed )
            repository = test_db_util.get_repository_by_name_and_owner( kwd[ 'name' ], owner )
        return repository

    def get_repo_path( self, repository ):
        # An entry in the hgweb.config file looks something like: repos/test/mira_assembler = database/community_files/000/repo_123
        lhs = "repos/%s/%s" % ( repository.user.username, repository.name )
        try:
            return self.hgweb_config_manager.get_entry( lhs )
        except:
            raise Exception( "Entry for repository %s missing in hgweb config file %s." % ( lhs, self.hgweb_config_manager.hgweb_config ) )

    def get_repository_changelog_tuples( self, repository ):
        repo = self.get_hg_repo( self.get_repo_path( repository ) )
        changelog_tuples = []
        for changeset in repo.changelog:
            ctx = repo.changectx( changeset )
            changelog_tuples.append( ( ctx.rev(), repo.changectx( changeset ) ) )
        return changelog_tuples

    def get_repository_datatypes_count( self, repository ):
        metadata = self.get_repository_metadata( repository )[0].metadata
        if 'datatypes' not in metadata:
            return 0
        else:
            return len( metadata[ 'datatypes' ] )

    def get_repository_file_list( self, repository, base_path, current_path=None ):
        '''Recursively load repository folder contents and append them to a list. Similar to os.walk but via /repository/open_folder.'''
        if current_path is None:
            request_param_path = base_path
        else:
            request_param_path = os.path.join( base_path, current_path )
        # Get the current folder's contents.
        params = dict( folder_path=request_param_path, repository_id=self.security.encode_id( repository.id ) )
        url = '/repository/open_folder'
        self.visit_url( url, params=params )
        file_list = loads( self.last_page() )
        returned_file_list = []
        if current_path is not None:
            returned_file_list.append( current_path )
        # Loop through the json dict returned by /repository/open_folder.
        for file_dict in file_list:
            if file_dict[ 'isFolder' ]:
                # This is a folder. Get the contents of the folder and append it to the list,
                # prefixed with the path relative to the repository root, if any.
                if current_path is None:
                    returned_file_list.extend( self.get_repository_file_list( repository=repository, base_path=base_path, current_path=file_dict[ 'title' ] ) )
                else:
                    sub_path = os.path.join( current_path, file_dict[ 'title' ] )
                    returned_file_list.extend( self.get_repository_file_list( repository=repository, base_path=base_path, current_path=sub_path ) )
            else:
                # This is a regular file, prefix the filename with the current path and append it to the list.
                if current_path is not None:
                    returned_file_list.append( os.path.join( current_path, file_dict[ 'title' ] ) )
                else:
                    returned_file_list.append( file_dict[ 'title' ] )
        return returned_file_list

    def get_repository_metadata( self, repository ):
        return [ metadata_revision for metadata_revision in repository.metadata_revisions ]

    def get_repository_metadata_by_changeset_revision( self, repository, changeset_revision ):
        return test_db_util.get_repository_metadata_for_changeset_revision( repository.id, changeset_revision )

    def get_repository_metadata_revisions( self, repository ):
        return [ str( repository_metadata.changeset_revision ) for repository_metadata in repository.metadata_revisions ]

    def get_repository_tip( self, repository ):
        repo = self.get_hg_repo( self.get_repo_path( repository ) )
        return str( repo.changectx( repo.changelog.tip() ) )

    def get_sniffers_count( self ):
        url = '/api/datatypes/sniffers'
        self.visit_galaxy_url( url )
        html = self.last_page()
        sniffers = loads( html )
        return len( sniffers )

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

    def get_tool_panel_section_from_api( self, metadata ):
        tool_metadata = metadata[ 'tools' ]
        tool_guid = quote_plus( tool_metadata[ 0 ][ 'guid' ], safe='' )
        api_url = '/%s' % '/'.join( [ 'api', 'tools', tool_guid ] )
        self.visit_galaxy_url( api_url )
        tool_dict = loads( self.last_page() )
        tool_panel_section = tool_dict[ 'panel_section_name' ]
        return tool_panel_section

    def get_tool_panel_section_from_repository_metadata( self, metadata ):
        tool_metadata = metadata[ 'tools' ]
        tool_guid = tool_metadata[ 0 ][ 'guid' ]
        assert 'tool_panel_section' in metadata, 'Tool panel section not found in metadata: %s' % metadata
        tool_panel_section_metadata = metadata[ 'tool_panel_section' ]
        # tool_section_dict = dict( tool_config=guids_and_configs[ guid ],
        #                           id=section_id,
        #                           name=section_name,
        #                           version=section_version )
        # This dict is appended to tool_panel_section_metadata[ tool_guid ]
        tool_panel_section = tool_panel_section_metadata[ tool_guid ][ 0 ][ 'name' ]
        return tool_panel_section

    def grant_role_to_user( self, user, role ):
        strings_displayed = [ self.security.encode_id( role.id ), role.name ]
        strings_not_displayed = []
        self.visit_url( '/admin/roles' )
        self.check_for_strings( strings_displayed, strings_not_displayed )
        params = dict( operation='manage users and groups', id=self.security.encode_id( role.id ) )
        url = '/admin/roles'
        self.visit_url( url, params )
        strings_displayed = [ common.test_user_1_email, common.test_user_2_email ]
        self.check_for_strings( strings_displayed, strings_not_displayed )
        # As elsewhere, twill limits the possibility of submitting the form, this time due to not executing the javascript
        # attached to the role selection form. Visit the action url directly with the necessary parameters.
        params = dict( id=self.security.encode_id( role.id ),
                       in_users=user.id,
                       operation='manage users and groups',
                       role_members_edit_button='Save' )
        url = '/admin/manage_users_and_groups_for_role'
        self.visit_url( url, params )
        strings_displayed = [ "Role '%s' has been updated" % role.name ]
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def grant_write_access( self,
                            repository,
                            usernames=[],
                            strings_displayed=None,
                            strings_not_displayed=None,
                            post_submit_strings_displayed=None,
                            post_submit_strings_not_displayed=None ):
        self.display_manage_repository_page( repository )
        self.check_for_strings( strings_displayed, strings_not_displayed )
        for username in usernames:
            tc.fv( "user_access", "allow_push", '+%s' % username )
        tc.submit( 'user_access_button' )
        self.check_for_strings( post_submit_strings_displayed, post_submit_strings_not_displayed )

    def import_capsule( self, filename, strings_displayed=None, strings_not_displayed=None,
                        strings_displayed_after_submit=[], strings_not_displayed_after_submit=[] ):
        url = '/repository/upload_capsule'
        self.visit_url( url )
        tc.formfile( 'upload_capsule', 'file_data', filename )
        tc.submit( 'upload_capsule_button' )
        self.check_for_strings( strings_displayed, strings_not_displayed )
        self.submit_form( 'import_capsule', 'import_capsule_button' )
        self.check_for_strings( strings_displayed_after_submit, strings_not_displayed_after_submit )

    def import_workflow( self, repository, workflow_name, strings_displayed=None, strings_not_displayed=None ):
        if strings_displayed is None:
            strings_displayed = []
        if strings_not_displayed is None:
            strings_not_displayed = []
        url = '/admin_toolshed/import_workflow?repository_id=%s&workflow_name=%s' % \
            ( self.security.encode_id( repository.id ), tool_shed_encode( workflow_name ) )
        self.visit_galaxy_url( url )
        if workflow_name not in strings_displayed:
            strings_displayed.append( workflow_name )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def initiate_installation_process( self,
                                       install_tool_dependencies=False,
                                       install_repository_dependencies=True,
                                       no_changes=True,
                                       new_tool_panel_section_label=None ):
        html = self.last_page()
        # Since the installation process is by necessity asynchronous, we have to get the parameters to 'manually' initiate the
        # installation process. This regex will return the tool shed repository IDs in group(1), the encoded_kwd parameter in
        # group(2), and the reinstalling flag in group(3) and pass them to the manage_repositories method in the Galaxy
        # admin_toolshed controller.
        install_parameters = re.search( 'initiate_repository_installation\( "([^"]+)", "([^"]+)", "([^"]+)" \);', html )
        if install_parameters:
            iri_ids = install_parameters.group(1)
            # In some cases, the returned iri_ids are of the form: "[u'<encoded id>', u'<encoded id>']"
            # This regex ensures that non-hex characters are stripped out of the list, so that galaxy.util.listify/decode_id
            # will handle them correctly. It's safe to pass the cleaned list to manage_repositories, because it can parse
            # comma-separated values.
            repository_ids = str( iri_ids )
            repository_ids = re.sub( '[^a-fA-F0-9,]+', '', repository_ids )
            encoded_kwd = install_parameters.group(2)
            reinstalling = install_parameters.group(3)
            url = '/admin_toolshed/manage_repositories?operation=install&tool_shed_repository_ids=%s&encoded_kwd=%s&reinstalling=%s' % \
                ( ','.join( galaxy.util.listify( repository_ids ) ), encoded_kwd, reinstalling )
            self.visit_galaxy_url( url )
            return galaxy.util.listify( repository_ids )

    def install_repositories_from_search_results( self, repositories, install_tool_dependencies=False,
                                                  strings_displayed=None, strings_not_displayed=None, **kwd ):
        '''
        Normally, it would be possible to check the appropriate boxes in the search results, and click the install button. This works
        in a browser, but Twill manages to lose the 'toolshedgalaxyurl' cookie between one page and the next, so it's necessary to work
        around this by explicitly visiting the prepare_for_install method on the Galaxy side.
        '''
        url = '/admin_toolshed/prepare_for_install?tool_shed_url=%s&repository_ids=%s&changeset_revisions=%s' % \
            ( self.url, ','.join( self.security.encode_id( repository.id ) for repository in repositories ),
              ','.join( self.get_repository_tip( repository ) for repository in repositories ) )
        self.visit_galaxy_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )
        if 'install_tool_dependencies' in self.last_page():
            form = tc.browser.get_form( 'select_tool_panel_section' )
            checkbox = form.find_control( id="install_tool_dependencies" )
            checkbox.disabled = False
            if install_tool_dependencies:
                checkbox.selected = True
                kwd[ 'install_tool_dependencies' ] = 'True'
            else:
                checkbox.selected = False
                kwd[ 'install_tool_dependencies' ] = 'False'
        self.submit_form( 1, 'select_tool_panel_section_button', **kwd )
        repository_ids = self.initiate_installation_process()
        self.wait_for_repository_installation( repository_ids )

    def install_repository( self, name, owner, category_name, install_resolver_dependencies=False, install_tool_dependencies=False,
                            install_repository_dependencies=True, changeset_revision=None,
                            strings_displayed=None, strings_not_displayed=None, preview_strings_displayed=None,
                            post_submit_strings_displayed=None, new_tool_panel_section_label=None, includes_tools_for_display_in_tool_panel=True,
                            **kwd ):
        self.browse_tool_shed( url=self.url )
        self.browse_category( test_db_util.get_category_by_name( category_name ) )
        self.preview_repository_in_tool_shed( name, owner, strings_displayed=preview_strings_displayed )
        repository = test_db_util.get_repository_by_name_and_owner( name, owner )
        repository_id = self.security.encode_id( repository.id )
        if changeset_revision is None:
            changeset_revision = self.get_repository_tip( repository )
        url = '/repository/install_repositories_by_revision?changeset_revisions=%s&repository_ids=%s&galaxy_url=%s' % \
              ( changeset_revision, repository_id, self.galaxy_url )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )
        # This section is tricky, due to the way twill handles form submission. The tool dependency checkbox needs to
        # be hacked in through tc.browser, putting the form field in kwd doesn't work.
        form = tc.browser.get_form( 'select_tool_panel_section' )
        if form is None:
            form = tc.browser.get_form( 'select_shed_tool_panel_config' )
        assert form is not None, 'Could not find form select_shed_tool_panel_config or select_tool_panel_section.'
        kwd = self.set_form_value( form, kwd, 'install_tool_dependencies', install_tool_dependencies )
        kwd = self.set_form_value( form, kwd, 'install_repository_dependencies', install_repository_dependencies )
        kwd = self.set_form_value( form, kwd, 'install_resolver_dependencies', install_resolver_dependencies )
        kwd = self.set_form_value( form, kwd, 'shed_tool_conf', self.shed_tool_conf )
        if new_tool_panel_section_label is not None:
            kwd = self.set_form_value( form, kwd, 'new_tool_panel_section_label', new_tool_panel_section_label )
        submit_button_control = form.find_control( type='submit' )
        assert submit_button_control is not None, 'No submit button found for form %s.' % form.attrs.get( 'id' )
        self.submit_form( form.attrs.get( 'id' ), str( submit_button_control.name ), **kwd )
        self.check_for_strings( post_submit_strings_displayed, strings_not_displayed )
        repository_ids = self.initiate_installation_process( new_tool_panel_section_label=new_tool_panel_section_label )
        log.debug( 'Waiting for the installation of repository IDs: %s' % str( repository_ids ) )
        self.wait_for_repository_installation( repository_ids )

    def load_citable_url( self,
                          username,
                          repository_name,
                          changeset_revision,
                          encoded_user_id,
                          encoded_repository_id,
                          strings_displayed=None,
                          strings_not_displayed=None,
                          strings_displayed_in_iframe=[],
                          strings_not_displayed_in_iframe=[] ):
        url = '%s/view/%s' % ( self.url, username )
        # If repository name is passed in, append that to the url.
        if repository_name:
            url += '/%s' % repository_name
        if changeset_revision:
            # Changeset revision should never be provided unless repository name also is.
            assert repository_name is not None, 'Changeset revision is present, but repository name is not - aborting.'
            url += '/%s' % changeset_revision
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )
        # Now load the page that should be displayed inside the iframe and check for strings.
        if encoded_repository_id:
            url = '/repository/view_repository?id=%s&operation=view_or_manage_repository' % encoded_repository_id
            if changeset_revision:
                url += '&changeset_revision=%s' % changeset_revision
            self.visit_url( url )
            self.check_for_strings( strings_displayed_in_iframe, strings_not_displayed_in_iframe )
        elif encoded_user_id:
            url = '/repository/browse_repositories?user_id=%s&operation=repositories_by_user' % encoded_user_id
            self.visit_url( url )
            self.check_for_strings( strings_displayed_in_iframe, strings_not_displayed_in_iframe )

    def load_changeset_in_tool_shed( self, repository_id, changeset_revision, strings_displayed=None, strings_not_displayed=None ):
        url = '/repository/view_changeset?ctx_str=%s&id=%s' % ( changeset_revision, repository_id )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def load_checkable_revisions( self, strings_displayed=None, strings_not_displayed=None ):
        params = urlencode( dict( do_not_test='false',
                                  downloadable='true',
                                  includes_tools='true',
                                  malicious='false',
                                  missing_test_components='false',
                                  skip_tool_test='false' ) )
        api_url = '%s?%s' % ( '/'.join( [ self.url, 'api', 'repository_revisions' ] ), params )
        self.visit_url( api_url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def load_display_tool_page( self, repository, tool_xml_path, changeset_revision, strings_displayed=None, strings_not_displayed=None ):
        url = '/repository/display_tool?repository_id=%s&tool_config=%s&changeset_revision=%s' % \
              ( self.security.encode_id( repository.id ), tool_xml_path, changeset_revision )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def load_galaxy_tool_migrations_page( self, strings_displayed=None, strings_not_displayed=None ):
        url = '/admin/review_tool_migration_stages'
        self.visit_galaxy_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def load_invalid_tool_page( self, repository, tool_xml, changeset_revision, strings_displayed=None, strings_not_displayed=None ):
        url = '/repository/load_invalid_tool?repository_id=%s&tool_config=%s&changeset_revision=%s' % \
              ( self.security.encode_id( repository.id ), tool_xml, changeset_revision )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def load_page_for_installed_tool( self, tool_guid, strings_displayed=None, strings_not_displayed=None ):
        url = '/tool_runner?tool_id=%s' % tool_guid
        self.visit_galaxy_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def load_workflow_image_in_tool_shed( self, repository, workflow_name, changeset_revision=None, strings_displayed=None, strings_not_displayed=None ):
        if not changeset_revision:
            changeset_revision = self.get_repository_tip( repository )
        metadata = self.get_repository_metadata_by_changeset_revision( repository, changeset_revision )
        if not metadata:
            raise AssertionError( 'Metadata not found for changeset revision %s.' % changeset_revision )
        url = '/repository/generate_workflow_image?repository_metadata_id=%s&workflow_name=%s' % \
              ( self.security.encode_id( metadata.id ), tool_shed_encode( workflow_name ) )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def manage_review_components( self, strings_displayed=None, strings_not_displayed=None ):
        url = '/repository_review/manage_components'
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def preview_repository_in_tool_shed( self, name, owner, changeset_revision=None, strings_displayed=None, strings_not_displayed=None ):
        repository = test_db_util.get_repository_by_name_and_owner( name, owner )
        if not changeset_revision:
            changeset_revision = self.get_repository_tip( repository )
        self.visit_url( '/repository/preview_tools_in_changeset?repository_id=%s&changeset_revision=%s' %
                        ( self.security.encode_id( repository.id ), changeset_revision ) )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def preview_workflow_in_tool_shed( self, repository_name, owner, workflow_name, strings_displayed=None, strings_not_displayed=None ):
        repository = test_db_util.get_repository_by_name_and_owner( repository_name, owner )
        metadata = self.get_repository_metadata( repository )
        url = '/repository/view_workflow?workflow_name=%s&repository_metadata_id=%s' % \
              ( tool_shed_encode( workflow_name ), self.security.encode_id( metadata[0].id ) )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def reactivate_repository( self, installed_repository ):
        params = dict( operation='activate or reinstall', id=self.security.encode_id( installed_repository.id ) )
        url = '/admin_toolshed/browse_repositories'
        self.visit_galaxy_url( url, params )
        strings_displayed = [ installed_repository.name, 'repository has been activated' ]
        self.check_for_strings( strings_displayed, [] )

    def reinstall_repository( self,
                              installed_repository,
                              install_repository_dependencies=True,
                              install_tool_dependencies=False,
                              no_changes=True,
                              new_tool_panel_section_label='',
                              strings_displayed=None,
                              strings_not_displayed=None ):
        url = '/admin_toolshed/reselect_tool_panel_section?id=%s' % self.security.encode_id( installed_repository.id )
        self.visit_galaxy_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed=None )
        # Build the url that will simulate a filled-out form being submitted. Due to a limitation in twill, the reselect_tool_panel_section
        # form doesn't get parsed correctly.
        encoded_repository_id = self.security.encode_id( installed_repository.id )
        params = dict( id=encoded_repository_id, no_changes=no_changes, new_tool_panel_section_label=new_tool_panel_section_label )
        doseq = False
        if install_repository_dependencies:
            params[ 'install_repository_dependencies' ] = [ 'True', 'True' ]
            doseq = True
        else:
            params[ 'install_repository_dependencies' ] = False
        if install_tool_dependencies:
            params[ 'install_tool_dependencies' ] = [ 'True', 'True' ]
            doseq = True
        else:
            params[ 'install_tool_dependencies' ] = False
        url = '/admin_toolshed/reinstall_repository'
        self.visit_galaxy_url( url, params=params, doseq=doseq )
        # Manually initiate the install process, as with installing a repository. See comments in the
        # initiate_installation_process method for details.
        repository_ids = self.initiate_installation_process( install_tool_dependencies,
                                                             install_repository_dependencies,
                                                             no_changes,
                                                             new_tool_panel_section_label )
        # Finally, wait until all repositories are in a final state (either Error or Installed) before returning.
        self.wait_for_repository_installation( repository_ids )

    def repository_is_new( self, repository ):
        repo = self.get_hg_repo( self.get_repo_path( repository ) )
        tip_ctx = repo.changectx( repo.changelog.tip() )
        return tip_ctx.rev() < 0

    def reset_installed_repository_metadata( self, repository ):
        url = '/admin_toolshed/reset_repository_metadata?id=%s' % self.security.encode_id( repository.id )
        self.visit_galaxy_url( url )
        self.check_for_strings( [ 'Metadata has been reset' ] )

    def reset_metadata_on_selected_repositories( self, repository_ids ):
        self.visit_url( '/admin/reset_metadata_on_selected_repositories_in_tool_shed' )
        kwd = dict( repository_ids=repository_ids )
        self.submit_form( form_no=1, button="reset_metadata_on_selected_repositories_button", **kwd )

    def reset_metadata_on_selected_installed_repositories( self, repository_ids ):
        self.visit_galaxy_url( '/admin_toolshed/reset_metadata_on_selected_installed_repositories' )
        kwd = dict( repository_ids=repository_ids )
        self.submit_form( form_no=1, button="reset_metadata_on_selected_repositories_button", **kwd )

    def reset_repository_metadata( self, repository ):
        url = '/repository/reset_all_metadata?id=%s' % self.security.encode_id( repository.id )
        self.visit_url( url )
        self.check_for_strings( [ 'All repository metadata has been reset.' ] )

    def repair_installed_repository( self, repository ):
        repository_id = self.security.encode_id( repository.id )
        url = '/admin_toolshed/repair_repository?id=%s' % repository_id
        self.visit_galaxy_url( url )
        self.submit_form( 'repair_repository', 'repair_repository_button' )

    def review_repository( self, repository, review_contents_dict, user=None, changeset_revision=None ):
        strings_displayed = []
        strings_not_displayed = []
        if not changeset_revision:
            changeset_revision = self.get_repository_tip( repository )
        if user:
            review = test_db_util.get_repository_review_by_user_id_changeset_revision( user.id, repository.id, changeset_revision )
        url = '/repository_review/edit_review?id=%s' % self.security.encode_id( review.id )
        self.visit_url( url )
        self.fill_review_form( review_contents_dict, strings_displayed, strings_not_displayed )

    def revoke_write_access( self, repository, username ):
        url = '/repository/manage_repository?user_access_button=Remove&id=%s&remove_auth=%s' % \
            ( self.security.encode_id( repository.id ), username )
        self.visit_url( url )

    def search_for_valid_tools( self, search_fields={}, exact_matches=False, strings_displayed=None, strings_not_displayed=None, from_galaxy=False ):
        if from_galaxy:
            galaxy_url = '?galaxy_url=%s' % self.galaxy_url
        else:
            galaxy_url = ''
        for field_name, search_string in search_fields.items():
            url = '/repository/find_tools%s' % galaxy_url
            self.visit_url( url )
            tc.fv( "1", "exact_matches", exact_matches )
            tc.fv( "1", field_name, search_string )
            tc.submit()
            self.check_for_strings( strings_displayed, strings_not_displayed )

    def send_message_to_repository_owner( self,
                                          repository,
                                          message,
                                          strings_displayed=None,
                                          strings_not_displayed=None,
                                          post_submit_strings_displayed=None,
                                          post_submit_strings_not_displayed=None ):
        url = '/repository/contact_owner?id=%s' % self.security.encode_id( repository.id )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )
        tc.fv( 1, 'message', message )
        tc.submit()
        self.check_for_strings( post_submit_strings_displayed, post_submit_strings_not_displayed )

    def set_form_value( self, form, kwd, field_name, field_value ):
        '''
        Set the form field field_name to field_value if it exists, and return the provided dict containing that value. If
        the field does not exist in the provided form, return a dict without that index.
        '''
        form_id = form.attrs.get( 'id' )
        controls = [ control for control in form.controls if str( control.name ) == field_name ]
        if len( controls ) > 0:
            log.debug( 'Setting field %s of form %s to %s.' % ( field_name, form_id, str( field_value ) ) )
            tc.formvalue( form_id, field_name, str( field_value ) )
            kwd[ field_name ] = str( field_value )
        else:
            if field_name in kwd:
                log.debug( 'No field %s in form %s, discarding from return value.', field_name, form_id )
                del( kwd[ field_name ] )
        return kwd

    def set_repository_deprecated( self, repository, set_deprecated=True, strings_displayed=None, strings_not_displayed=None ):
        url = '/repository/deprecate?id=%s&mark_deprecated=%s' % ( self.security.encode_id( repository.id ), set_deprecated )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def set_repository_malicious( self, repository, set_malicious=True, strings_displayed=None, strings_not_displayed=None ):
        self.display_manage_repository_page( repository )
        tc.fv( "malicious", "malicious", set_malicious )
        tc.submit( "malicious_button" )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def set_skip_tool_tsts_flag( self, repository, flag_value, reason, changeset_revision=None ):
        if changeset_revision is None:
            changeset_revision = self.get_repository_tip( repository )
        self.display_manage_repository_page( repository, changeset_revision=changeset_revision )
        form = tc.browser.get_form( 'skip_tool_tests' )
        assert form is not None, 'Could not find form skip_tool_tests.'
        for control in form.controls:
            control_name = str( control.name )
            if control_name == 'skip_tool_tests' and control.type == 'checkbox':
                checkbox = control.get()
                checkbox.selected = flag_value
            elif control_name == 'skip_tool_tests_comment':
                tc.browser.clicked( form, control )
                tc.formvalue( 'skip_tool_tests', control_name, reason )
        kwd = dict()
        self.submit_form( 'skip_tool_tests', 'skip_tool_tests_button', **kwd )
        if flag_value is True:
            self.check_for_strings( strings_displayed=[ 'Tools in this revision will not be tested by the automated test framework' ] )
        else:
            self.check_for_strings( strings_displayed=[ 'Tools in this revision will be tested by the automated test framework' ] )

    def tip_has_metadata( self, repository ):
        tip = self.get_repository_tip( repository )
        return test_db_util.get_repository_metadata_by_repository_id_changeset_revision( repository.id, tip )

    def undelete_repository( self, repository ):
        repository_id = self.security.encode_id( repository.id )
        url = '/admin/browse_repositories?operation=Undelete&id=%s' % repository_id
        strings_displayed = [ 'Undeleted 1 repository', repository.name ]
        strings_not_displayed = []
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def uninstall_repository( self, installed_repository, strings_displayed=None, strings_not_displayed=None ):
        url = '/admin_toolshed/deactivate_or_uninstall_repository?id=%s' % self.security.encode_id( installed_repository.id )
        self.visit_galaxy_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )
        form = tc.browser.get_form( 'deactivate_or_uninstall_repository' )
        self.set_form_value( form, {}, 'remove_from_disk', True )
        tc.submit( 'deactivate_or_uninstall_repository_button' )
        strings_displayed = [ 'The repository named', 'has been uninstalled' ]
        self.check_for_strings( strings_displayed, strings_not_displayed=None )

    def update_installed_repository( self, installed_repository, strings_displayed=None, strings_not_displayed=None ):
        url = '/repository/check_for_updates?name=%s&owner=%s&changeset_revision=%s&galaxy_url=%s' % ( installed_repository.name,
            installed_repository.owner, installed_repository.installed_changeset_revision, self.galaxy_url )
        self.visit_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def update_tool_shed_status( self ):
        url = '/admin_toolshed/update_tool_shed_status_for_installed_repository?all_installed_repositories=True'
        self.visit_galaxy_url( url )

    def upload_file( self,
                     repository,
                     filename,
                     filepath,
                     valid_tools_only,
                     uncompress_file,
                     remove_repo_files_not_in_tar,
                     commit_message,
                     strings_displayed=None,
                     strings_not_displayed=None ):
        if strings_displayed is None:
            strings_displayed = []
        if strings_not_displayed is None:
            strings_not_displayed = []
        removed_message = 'files were removed from the repository'
        if remove_repo_files_not_in_tar:
            if not self.repository_is_new( repository ):
                if removed_message not in strings_displayed:
                    strings_displayed.append( removed_message )
        else:
            if removed_message not in strings_not_displayed:
                strings_not_displayed.append( removed_message )
        self.visit_url( '/upload/upload?repository_id=%s' % self.security.encode_id( repository.id ) )
        if valid_tools_only:
            strings_displayed.extend( [ 'has been successfully', 'uploaded to the repository.' ] )
        tc.formfile( "1", "file_data", self.get_filename( filename, filepath ) )
        if uncompress_file:
            tc.fv( 1, 'uncompress_file', 'Yes' )
        else:
            tc.fv( 1, 'uncompress_file', 'No' )
        if not self.repository_is_new( repository ):
            if remove_repo_files_not_in_tar:
                tc.fv( 1, 'remove_repo_files_not_in_tar', 'Yes' )
            else:
                tc.fv( 1, 'remove_repo_files_not_in_tar', 'No' )
        tc.fv( 1, 'commit_message', commit_message )
        tc.submit( "upload_button" )
        self.check_for_strings( strings_displayed, strings_not_displayed )
        # Uncomment this if it becomes necessary to wait for an asynchronous process to complete after submitting an upload.
        # for i in range( 5 ):
        #    try:
        #        self.check_for_strings( strings_displayed, strings_not_displayed )
        #        break
        #    except Exception as e:
        #        if i == 4:
        #            raise e
        #        else:
        #            time.sleep( 1 )
        #            continue

    def upload_url( self,
                    repository,
                    url,
                    filepath,
                    valid_tools_only,
                    uncompress_file,
                    remove_repo_files_not_in_tar,
                    commit_message,
                    strings_displayed=None,
                    strings_not_displayed=None ):
        removed_message = 'files were removed from the repository'
        if remove_repo_files_not_in_tar:
            if not self.repository_is_new( repository ):
                if removed_message not in strings_displayed:
                    strings_displayed.append( removed_message )
        else:
            if removed_message not in strings_not_displayed:
                strings_not_displayed.append( removed_message )
        self.visit_url( '/upload/upload?repository_id=%s' % self.security.encode_id( repository.id ) )
        if valid_tools_only:
            strings_displayed.extend( [ 'has been successfully', 'uploaded to the repository.' ] )
        tc.fv( "1", "url", url )
        if uncompress_file:
            tc.fv( 1, 'uncompress_file', 'Yes' )
        else:
            tc.fv( 1, 'uncompress_file', 'No' )
        if not self.repository_is_new( repository ):
            if remove_repo_files_not_in_tar:
                tc.fv( 1, 'remove_repo_files_not_in_tar', 'Yes' )
            else:
                tc.fv( 1, 'remove_repo_files_not_in_tar', 'No' )
        tc.fv( 1, 'commit_message', commit_message )
        tc.submit( "upload_button" )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def verify_capsule_contents( self, capsule_filepath, owner ):
        tar_object = tarfile.open( capsule_filepath, 'r:*' )
        extraction_path = tempfile.mkdtemp()
        tar_object.extractall( extraction_path )
        for root, dirs, files in os.walk( extraction_path ):
            if 'manifest.xml' in files:
                self.check_manifest( os.path.join( root, 'manifest.xml' ), owner=owner )
        shutil.rmtree( extraction_path )

    def verify_installed_repositories( self, installed_repositories=[], uninstalled_repositories=[] ):
        for repository_name, repository_owner in installed_repositories:
            galaxy_repository = test_db_util.get_installed_repository_by_name_owner( repository_name, repository_owner )
            if galaxy_repository:
                assert galaxy_repository.status == 'Installed', \
                    'Repository %s should be installed, but is %s' % ( repository_name, galaxy_repository.status )

    def verify_installed_repository_metadata_unchanged( self, name, owner ):
        installed_repository = test_db_util.get_installed_repository_by_name_owner( name, owner )
        metadata = installed_repository.metadata
        self.reset_installed_repository_metadata( installed_repository )
        new_metadata = installed_repository.metadata
        assert metadata == new_metadata, 'Metadata for installed repository %s differs after metadata reset.' % name

    def verify_installed_repository_no_tool_panel_section( self, repository ):
        '''Verify that there is no 'tool_panel_section' entry in the repository metadata.'''
        metadata = repository.metadata
        assert 'tool_panel_section' not in metadata, 'Tool panel section incorrectly found in metadata: %s' % metadata

    def verify_installed_repository_data_table_entries( self, required_data_table_entries ):
        # The value of the received required_data_table_entries will be something like: [ 'sam_fa_indexes' ]
        data_tables, error_message = xml_util.parse_xml( self.shed_tool_data_table_conf )
        found = False
        # With the tool shed, the "path" attribute that is hard-coded into the tool_data_tble_conf.xml
        # file is ignored.  This is because the tool shed requires the directory location to which this
        # path points to be empty except when a specific tool is loaded.  The default location for this
        # directory configured for the tool shed is <Galaxy root>/shed-tool-data.  When a tool is loaded
        # in the tool shed, all contained .loc.sample files are copied to this directory and the
        # ToolDataTableManager parses and loads the files in the same way that Galaxy does with a very
        # important exception.  When the tool shed loads a tool and parses and loads the copied ,loc.sample
        # files, the ToolDataTableManager is already instantiated, and so its add_new_entries_from_config_file()
        # method is called and the tool_data_path parameter is used to over-ride the hard-coded "tool-data"
        # directory that Galaxy always uses.
        #
        # Tool data table xml structure:
        # <tables>
        #     <table comment_char="#" name="sam_fa_indexes">
        #        <columns>line_type, value, path</columns>
        #        <file path="tool-data/sam_fa_indices.loc" />
        #     </table>
        # </tables>
        required_data_table_entry = None
        for table_elem in data_tables.findall( 'table' ):
            # The value of table_elem will be something like: <table comment_char="#" name="sam_fa_indexes">
            for required_data_table_entry in required_data_table_entries:
                # The value of required_data_table_entry will be something like: 'sam_fa_indexes'
                if 'name' in table_elem.attrib and table_elem.attrib[ 'name' ] == required_data_table_entry:
                    found = True
                    # We're processing something like: sam_fa_indexes
                    file_elem = table_elem.find( 'file' )
                    # We have something like: <file path="tool-data/sam_fa_indices.loc" />
                    # The "path" attribute of the "file" tag is the location that Galaxy always uses because the
                    # Galaxy ToolDataTableManager was implemented in such a way that the hard-coded path is used
                    # rather than allowing the location to be a configurable setting like the tool shed requires.
                    file_path = file_elem.get( 'path', None )
                    # The value of file_path will be something like: "tool-data/all_fasta.loc"
                    assert file_path is not None, 'The "path" attribute is missing for the %s entry.' % required_data_table_entry
                    # The following test is probably not necesary, but the tool-data directory should exist!
                    galaxy_tool_data_dir, loc_file_name = os.path.split( file_path )
                    assert galaxy_tool_data_dir is not None, 'The hard-coded Galaxy tool-data directory is missing for the %s entry.' % required_data_table_entry
                    assert os.path.exists( galaxy_tool_data_dir ), 'The Galaxy tool-data directory does not exist.'
                    # Make sure the loc_file_name was correctly copied into the configured directory location.
                    configured_file_location = os.path.join( self.tool_data_path, loc_file_name )
                    assert os.path.isfile( configured_file_location ), 'The expected copied file "%s" is missing.' % configured_file_location
                    # We've found the value of the required_data_table_entry in data_tables, which is the parsed
                    # shed_tool_data_table_conf.xml, so all is well!
                    break
            if found:
                break
        # We better have an entry like: <table comment_char="#" name="sam_fa_indexes"> in our parsed data_tables
        # or we know that the repository was not correctly installed!
        assert found, 'No entry for %s in %s.' % ( required_data_table_entry, self.shed_tool_data_table_conf )

    def verify_repository_in_capsule( self, repository_archive, repository_name, repository_owner ):
        repository_extraction_dir = tempfile.mkdtemp()
        repository_tar_object = tarfile.open( repository_archive, 'r:*' )
        repository_tar_object.extractall( repository_extraction_dir )
        for root, dirs, files in os.walk( repository_extraction_dir ):
            for filename in files:
                if filename in [ 'tool_dependencies.xml', 'repository_dependencies.xml' ]:
                    dependency_filepath = os.path.join( root, filename )
                    self.check_exported_repository_dependency( dependency_filepath, repository_name, repository_owner )
        shutil.rmtree( repository_extraction_dir )

    def verify_repository_reviews( self, repository, reviewer=None, strings_displayed=None, strings_not_displayed=None ):
        changeset_revision = self.get_repository_tip( repository )
        # Verify that the currently logged in user has a repository review for the specified repository, reviewer, and changeset revision.
        strings_displayed = [ repository.name, reviewer.username ]
        self.display_reviewed_repositories_owned_by_user( strings_displayed=strings_displayed )
        # Verify that the reviewer has reviewed the specified repository's changeset revision.
        strings_displayed = [ repository.name, repository.description ]
        self.display_repository_reviews_by_user( reviewer, strings_displayed=strings_displayed )
        # Load the review and check for the components passed in strings_displayed.
        review = test_db_util.get_repository_review_by_user_id_changeset_revision( reviewer.id, repository.id, changeset_revision )
        self.browse_component_review( review, strings_displayed=strings_displayed )

    def verify_tool_metadata_for_installed_repository( self, installed_repository, strings_displayed=None, strings_not_displayed=None ):
        if strings_displayed is None:
            strings_displayed = []
        if strings_not_displayed is None:
            strings_not_displayed = []
        repository_id = self.security.encode_id( installed_repository.id )
        for tool in installed_repository.metadata[ 'tools' ]:
            strings = list( strings_displayed )
            strings.extend( [ tool[ 'id' ], tool[ 'description' ], tool[ 'version' ], tool[ 'guid' ], tool[ 'name' ] ] )
            params = dict( repository_id=repository_id, tool_id=tool[ 'id' ] )
            url = '/admin_toolshed/view_tool_metadata'
            self.visit_galaxy_url( url, params )
            self.check_for_strings( strings, strings_not_displayed )

    def verify_unchanged_repository_metadata( self, repository ):
        old_metadata = dict()
        new_metadata = dict()
        for metadata in self.get_repository_metadata( repository ):
            old_metadata[ metadata.changeset_revision ] = metadata.metadata
        self.reset_repository_metadata( repository )
        for metadata in self.get_repository_metadata( repository ):
            new_metadata[ metadata.changeset_revision ] = metadata.metadata
        # Python's dict comparison recursively compares sorted key => value pairs and returns true if any key or value differs,
        # or if the number of keys differs.
        assert old_metadata == new_metadata, 'Metadata changed after reset on repository %s.' % repository.name

    def view_installed_workflow( self, repository, workflow_name, strings_displayed=None, strings_not_displayed=None ):
        url = '/admin_toolshed/view_workflow?repository_id=%s&workflow_name=%s' % \
            ( self.security.encode_id( repository.id ), tool_shed_encode( workflow_name ) )
        self.visit_galaxy_url( url )
        self.check_for_strings( strings_displayed, strings_not_displayed )

    def visit_galaxy_url( self, url, params=None, doseq=False ):
        url = '%s%s' % ( self.galaxy_url, url )
        self.visit_url( url, params=params, doseq=doseq )

    def wait_for_repository_installation( self, repository_ids ):
        final_states = [ galaxy_model.ToolShedRepository.installation_status.ERROR,
                         galaxy_model.ToolShedRepository.installation_status.INSTALLED ]
        # Wait until all repositories are in a final state before returning. This ensures that subsequent tests
        # are running against an installed repository, and not one that is still in the process of installing.
        if repository_ids:
            for repository_id in repository_ids:
                galaxy_repository = test_db_util.get_installed_repository_by_id( self.security.decode_id( repository_id ) )
                timeout_counter = 0
                while galaxy_repository.status not in final_states:
                    test_db_util.ga_refresh( galaxy_repository )
                    timeout_counter = timeout_counter + 1
                    # This timeout currently defaults to 10 minutes.
                    if timeout_counter > repository_installation_timeout:
                        raise AssertionError( 'Repository installation timed out, %d seconds elapsed, repository state is %s.' %
                                              ( timeout_counter, galaxy_repository.status ) )
                        break
                    time.sleep( 1 )
