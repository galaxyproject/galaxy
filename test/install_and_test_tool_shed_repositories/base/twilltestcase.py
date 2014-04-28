import logging
import os
import re
import test_db_util
import time

import galaxy.model as model
import galaxy.model.tool_shed_install as install_model
import galaxy.util

from galaxy.web import security
from base.twilltestcase import TwillTestCase
from base.tool_shed_util import repository_installation_timeout

from galaxy import eggs
eggs.require( 'twill' )

import twill.commands as tc

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

    def initiate_installation_process( self, install_tool_dependencies=False, install_repository_dependencies=True, no_changes=True,
                                       new_tool_panel_section_label=None ):
        html = self.last_page()
        # Since the installation process is by necessity asynchronous we have to get the parameters to 'manually' initiate the
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
            self.visit_url( url )
            return galaxy.util.listify( repository_ids )

    def install_repository( self, repository_info_dict, install_tool_dependencies=True, install_repository_dependencies=True,
                            strings_displayed=[], strings_not_displayed=[], preview_strings_displayed=[],
                            post_submit_strings_displayed=[], new_tool_panel_section_label=None, **kwd ):
        name = repository_info_dict[ 'name' ]
        owner = repository_info_dict[ 'owner' ]
        changeset_revision = repository_info_dict[ 'changeset_revision' ]
        encoded_repository_id = repository_info_dict[ 'repository_id' ]
        tool_shed_url = repository_info_dict[ 'tool_shed_url' ]
        # Pass galaxy_url to the tool shed in order to set cookies and redirects correctly.
        install_params = dict( repository_ids=encoded_repository_id,
                               changeset_revisions=changeset_revision,
                               galaxy_url=self.url )
        # If the tool shed does not have the same hostname as the Galaxy server being used for these tests,
        # twill will not carry over previously set cookies for the Galaxy server when following the
        # install_repositories_by_revision redirect, so we have to include 403 in the allowed HTTP
        # status codes and log in again.
        url = '%s/repository/install_repositories_by_revision' % tool_shed_url
        self.visit_url( url, params=install_params, allowed_codes=[ 200, 403 ] )
        self.logout()
        self.login( email='test@bx.psu.edu', username='test' )
        install_params = dict( repository_ids=encoded_repository_id,
                               changeset_revisions=changeset_revision,
                               tool_shed_url=tool_shed_url )
        url = '/admin_toolshed/prepare_for_install'
        self.visit_url( url, params=install_params )
        # This section is tricky, due to the way twill handles form submission. The tool dependency checkbox needs to
        # be hacked in through tc.browser, putting the form field in kwd doesn't work.
        form = tc.browser.get_form( 'select_tool_panel_section' )
        if form is None:
            form = tc.browser.get_form( 'select_shed_tool_panel_config' )
        assert form is not None, 'Could not find form select_shed_tool_panel_config or select_tool_panel_section.'
        kwd = self.set_form_value( form, kwd, 'install_tool_dependencies', install_tool_dependencies )
        kwd = self.set_form_value( form, kwd, 'install_repository_dependencies', install_repository_dependencies )
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
                log.debug( 'No field %s in form %s, discarding from return value.' % ( str( control ), str( form_id ) ) )
                del( kwd[ field_name ] )
        return kwd

    def wait_for_repository_installation( self, repository_ids ):
        final_states = [ install_model.ToolShedRepository.installation_status.ERROR,
                         install_model.ToolShedRepository.installation_status.INSTALLED ]
        # Wait until all repositories are in a final state before returning. This ensures that subsequent tests
        # are running against an installed repository, and not one that is still in the process of installing.
        if repository_ids:
            for repository_id in repository_ids:
                galaxy_repository = test_db_util.get_repository( self.security.decode_id( repository_id ) )
                log.debug( 'Repository %s with ID %s has initial state %s.' % \
                    ( str( galaxy_repository.name ), str( repository_id ), str( galaxy_repository.status ) ) )
                timeout_counter = 0
                while galaxy_repository.status not in final_states:
                    test_db_util.refresh( galaxy_repository )
                    log.debug( 'Repository %s with ID %s is in state %s, continuing to wait.' % \
                        ( str( galaxy_repository.name ), str( repository_id ), str( galaxy_repository.status ) ) )
                    timeout_counter = timeout_counter + 1
                    if timeout_counter % 10 == 0:
                        log.debug( 'Waited %d seconds for repository %s.' % ( timeout_counter, str( galaxy_repository.name ) ) )
                    # This timeout currently defaults to 10 minutes.
                    if timeout_counter > repository_installation_timeout:
                        raise AssertionError( 'Repository installation timed out after %d seconds, repository state is %s.' % \
                            ( timeout_counter, repository.status ) )
                        break
                    time.sleep( 1 )
            # Set all metadata on each installed repository.
            for repository_id in repository_ids:
                galaxy_repository = test_db_util.get_repository( self.security.decode_id( repository_id ) )
                if not galaxy_repository.metadata:
                    log.debug( 'Setting metadata on repository %s' % str( galaxy_repository.name ) )
                    timeout_counter = 0
                    url = '/admin_toolshed/reset_repository_metadata?id=%s' % repository_id
                    self.visit_url( url )
                    while not galaxy_repository.metadata:
                        test_db_util.refresh( galaxy_repository )
                        timeout_counter = timeout_counter + 1
                        if timeout_counter % 10 == 0:
                            log.debug( 'Waited %d seconds for repository %s.' % ( timeout_counter, str( galaxy_repository.name ) ) )
                        # This timeout currently defaults to 10 minutes.
                        if timeout_counter > repository_installation_timeout:
                            raise AssertionError( 'Repository installation timed out after %d seconds, repository state is %s.' % \
                                ( timeout_counter, galaxy_repository.status ) )
                            break
                        time.sleep( 1 )
