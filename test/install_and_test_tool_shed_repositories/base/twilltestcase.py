import galaxy.model as model
import common, string, os, re, test_db_util, simplejson, logging, time, sys
import galaxy.util as util
from base.twilltestcase import tc, from_json_string, TwillTestCase, security, urllib
from galaxy.tool_shed.encoding_util import tool_shed_encode, tool_shed_decode

log = logging.getLogger( __name__ )

class InstallTestRepository( TwillTestCase ):
    def setUp( self ):
        # Security helper
        id_secret = os.environ.get( 'GALAXY_INSTALL_TEST_SECRET', 'changethisinproductiontoo' )
        self.security = security.SecurityHelper( id_secret=id_secret )
        self.history_id = None
        self.test_tmp_dir = os.environ.get( 'GALAXY_INSTALL_TEST_TMP_DIR', None)
        self.host = os.environ.get( 'GALAXY_INSTALL_TEST_HOST' )
        self.port = os.environ.get( 'GALAXY_INSTALL_TEST_PORT' )
        self.url = "http://%s:%s" % ( self.host, self.port )
        self.shed_tool_data_table_conf = os.environ.get( 'GALAXY_INSTALL_TEST_SHED_TOOL_DATA_TABLE_CONF' )
        self.file_dir = os.environ.get( 'GALAXY_INSTALL_TEST_FILE_DIR', None )
        self.tool_data_path = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_DATA_PATH' )
        self.shed_tool_conf = os.environ.get( 'GALAXY_INSTALL_TEST_SHED_TOOL_CONF' )
        # TODO: Figure out a way to alter these attributes during tests.
        self.galaxy_tool_dependency_dir = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_DEPENDENCY_DIR' )
        self.shed_tools_dict = {}
        self.home()
    def initiate_installation_process( self, 
                                       install_tool_dependencies=False, 
                                       install_repository_dependencies=True, 
                                       no_changes=True, 
                                       new_tool_panel_section=None ):
        html = self.last_page()
        # Since the installation process is by necessity asynchronous, we have to get the parameters to 'manually' initiate the 
        # installation process. This regex will return the tool shed repository IDs in group(1), the encoded_kwd parameter in 
        # group(2), and the reinstalling flag in group(3) and pass them to the manage_repositories method in the Galaxy 
        # admin_toolshed controller.
        install_parameters = re.search( 'initiate_repository_installation\( "([^"]+)", "([^"]+)", "([^"]+)" \);', html )
        if install_parameters:
            iri_ids = install_parameters.group(1)
            # In some cases, the returned iri_ids are of the form: "[u'<encoded id>', u'<encoded id>']"
            # This regex ensures that non-hex characters are stripped out of the list, so that util.listify/decode_id 
            # will handle them correctly. It's safe to pass the cleaned list to manage_repositories, because it can parse
            # comma-separated values.
            repository_ids = str( iri_ids )
            repository_ids = re.sub( '[^a-fA-F0-9,]+', '', repository_ids )
            encoded_kwd = install_parameters.group(2)
            reinstalling = install_parameters.group(3)
            url = '/admin_toolshed/manage_repositories?operation=install&tool_shed_repository_ids=%s&encoded_kwd=%s&reinstalling=%s' % \
                ( ','.join( util.listify( repository_ids ) ), encoded_kwd, reinstalling )
            self.visit_url( url )
            return util.listify( repository_ids )
    def install_repository( self, repository_info_dict, install_tool_dependencies=True, install_repository_dependencies=True, 
                            strings_displayed=[], strings_not_displayed=[], preview_strings_displayed=[], 
                            post_submit_strings_displayed=[], new_tool_panel_section=None, **kwd ):
        name = repository_info_dict[ 'name' ]
        owner = repository_info_dict[ 'owner' ]
        changeset_revision = repository_info_dict[ 'changeset_revision' ]
        encoded_repository_id = repository_info_dict[ 'encoded_repository_id' ]
        tool_shed_url = repository_info_dict[ 'tool_shed_url' ]
        preview_params = urllib.urlencode( dict( repository_id=encoded_repository_id, changeset_revision=changeset_revision ) )
        self.visit_url( '%s/repository/preview_tools_in_changeset?%s' % ( tool_shed_url, preview_params ) )
        install_params = urllib.urlencode( dict( repository_ids=encoded_repository_id, 
                                                 changeset_revisions=changeset_revision,
                                                 galaxy_url=self.url ) )
        # If the tool shed does not have the same hostname as the Galaxy server being used for these tests, 
        # twill will not carry over previously set cookies for the Galaxy server when following the 
        # install_repositories_by_revision redirect, so we have to include 403 in the allowed HTTP 
        # status codes and log in again.
        url = '%s/repository/install_repositories_by_revision?%s' % ( tool_shed_url, install_params )
        self.visit_url( url, allowed_codes=[ 200, 403 ] )
        self.logout()
        self.login( email='test@bx.psu.edu', username='test' )
        install_params = urllib.urlencode( dict( repository_ids=encoded_repository_id, 
                                                 changeset_revisions=changeset_revision,
                                                 tool_shed_url=tool_shed_url ) )
        url = '/admin_toolshed/prepare_for_install?%s' % install_params
        self.visit_url( url )
        # This section is tricky, due to the way twill handles form submission. The tool dependency checkbox needs to 
        # be hacked in through tc.browser, putting the form field in kwd doesn't work.
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
        if 'install_repository_dependencies' in self.last_page():
            kwd[ 'install_repository_dependencies' ] = str( install_repository_dependencies ).lower()
        if 'shed_tool_conf' not in kwd:
            kwd[ 'shed_tool_conf' ] = self.shed_tool_conf
        if new_tool_panel_section:
            kwd[ 'new_tool_panel_section' ] =  new_tool_panel_section
        self.submit_form( 1, 'select_tool_panel_section_button', **kwd )
        self.check_for_strings( post_submit_strings_displayed, strings_not_displayed )
        repository_ids = self.initiate_installation_process( new_tool_panel_section=new_tool_panel_section )
        self.wait_for_repository_installation( repository_ids )
    def visit_url( self, url, allowed_codes=[ 200 ] ):
        new_url = tc.go( url )
        return_code = tc.browser.get_code()
        assert return_code in allowed_codes, 'Invalid HTTP return code %s, allowed codes: %s' % \
            ( return_code, ', '.join( str( code ) for code in allowed_codes ) ) 
        return new_url
    def wait_for_repository_installation( self, repository_ids ):
        final_states = [ model.ToolShedRepository.installation_status.ERROR,
                         model.ToolShedRepository.installation_status.INSTALLED ]
        # Wait until all repositories are in a final state before returning. This ensures that subsequent tests
        # are running against an installed repository, and not one that is still in the process of installing.
        if repository_ids:
            for repository_id in repository_ids:
                galaxy_repository = test_db_util.get_repository( self.security.decode_id( repository_id ) )
                timeout_counter = 0
                while galaxy_repository.status not in final_states:
                    test_db_util.refresh( galaxy_repository )
                    timeout_counter = timeout_counter + 1
                    # This timeout currently defaults to 180 seconds, or 3 minutes.
                    if timeout_counter > common.repository_installation_timeout:
                        raise AssertionError( 'Repository installation timed out, %d seconds elapsed, repository state is %s.' % \
                                              ( timeout_counter, repository.status ) )
                        break
                    time.sleep( 1 )
    def uninstall_repository( self, installed_repository ):
        url = '/admin_toolshed/deactivate_or_uninstall_repository?id=%s' % self.security.encode_id( installed_repository.id )
        self.visit_url( url )
        tc.fv ( 1, "remove_from_disk", 'true' )
        tc.submit( 'deactivate_or_uninstall_repository_button' )
        strings_displayed = [ 'The repository named' ]
        strings_displayed.append( 'has been uninstalled' )
        self.check_for_strings( strings_displayed, strings_not_displayed=[] )

