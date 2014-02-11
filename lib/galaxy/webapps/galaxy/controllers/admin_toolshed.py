import logging
import os
import shutil
from admin import AdminGalaxy
from galaxy import eggs
from galaxy import web
from galaxy import util
from galaxy.web.form_builder import CheckboxField
from galaxy.web.framework.helpers import grids
from galaxy.web.framework.helpers import iff
from galaxy.util import json
from galaxy.model.orm import or_
import tool_shed.util.shed_util_common as suc
from tool_shed.util import common_util
from tool_shed.util import common_install_util
from tool_shed.util import data_manager_util
from tool_shed.util import datatype_util
from tool_shed.util import encoding_util
from tool_shed.util import metadata_util
from tool_shed.util import readme_util
from tool_shed.util import repository_dependency_util
from tool_shed.util import tool_dependency_util
from tool_shed.util import tool_util
from tool_shed.util import workflow_util
from tool_shed.galaxy_install import repository_util
import tool_shed.galaxy_install.grids.admin_toolshed_grids as admin_toolshed_grids
import pkg_resources

eggs.require( 'mercurial' )
from mercurial import commands
from mercurial import hg
from mercurial import ui

pkg_resources.require( 'elementtree' )
from elementtree import ElementTree
from elementtree.ElementTree import Element

log = logging.getLogger( __name__ )


class AdminToolshed( AdminGalaxy ):

    installed_repository_grid = admin_toolshed_grids.InstalledRepositoryGrid()
    repository_installation_grid = admin_toolshed_grids.RepositoryInstallationGrid()
    tool_dependency_grid = admin_toolshed_grids.ToolDependencyGrid()

    @web.expose
    @web.require_admin
    def activate_repository( self, trans, **kwd ):
        """Activate a repository that was deactivated but not uninstalled."""
        repository_id = kwd[ 'id' ]
        repository = suc.get_installed_tool_shed_repository( trans, repository_id )
        try:
            common_install_util.activate_repository( trans, repository )
        except Exception, e:
            error_message = "Error activating repository %s: %s" % ( repository.name, str( e ) )
            log.exception( error_message )
            message = '%s.<br/>You may be able to resolve this by uninstalling and then reinstalling the repository.  Click <a href="%s">here</a> to uninstall the repository.' \
                % ( error_message, web.url_for( controller='admin_toolshed', action='deactivate_or_uninstall_repository', id=trans.security.encode_id( repository.id ) ) )
            status = 'error'
            return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                              action='manage_repository',
                                                              id=repository_id,
                                                              message=message,
                                                              status=status ) )
        message = 'The <b>%s</b> repository has been activated.' % repository.name
        status = 'done'
        return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                          action='browse_repositories',
                                                          message=message,
                                                          status=status ) )

    @web.expose
    @web.require_admin
    def browse_repository( self, trans, **kwd ):
        message = kwd.get( 'message', ''  )
        status = kwd.get( 'status', 'done' )
        repository = suc.get_installed_tool_shed_repository( trans, kwd[ 'id' ] )
        return trans.fill_template( '/admin/tool_shed_repository/browse_repository.mako',
                                    repository=repository,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def browse_repositories( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd.pop( 'operation' ).lower()
            if operation == "manage_repository":
                return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                  action='manage_repository',
                                                                  **kwd ) )
            if operation == "get updates":
                return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                  action='check_for_updates',
                                                                  **kwd ) )
            if operation == "update tool shed status":
                return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                  action='update_tool_shed_status_for_installed_repository',
                                                                  **kwd ) )
            if operation == "reset to install":
                kwd[ 'reset_repository' ] = True
                return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                  action='reset_to_install',
                                                                  **kwd ) )
            if operation == "activate or reinstall":
                repository = suc.get_installed_tool_shed_repository( trans, kwd[ 'id' ] )
                if repository.uninstalled:
                    # Since we're reinstalling the repository we need to find the latest changeset revision to which it can
                    # be updated so that we can reset the metadata if necessary.  This will ensure that information about
                    # repository dependencies and tool dependencies will be current.  Only allow selecting a different section
                    # in the tool panel if the repository was uninstalled and it contained tools that should be displayed in
                    # the tool panel.
                    changeset_revision_dict = repository_util.get_update_to_changeset_revision_and_ctx_rev( trans, repository )
                    current_changeset_revision = changeset_revision_dict.get( 'changeset_revision', None )
                    current_ctx_rev = changeset_revision_dict.get( 'ctx_rev', None )
                    if current_changeset_revision and current_ctx_rev:
                        if current_ctx_rev == repository.ctx_rev:
                            # The uninstalled repository is current.
                            return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                              action='reselect_tool_panel_section',
                                                                              **kwd ) )
                        else:
                            # The uninstalled repository has updates available in the tool shed.
                            updated_repo_info_dict = \
                                self.get_updated_repository_information( trans=trans,
                                                                         repository_id=trans.security.encode_id( repository.id ),
                                                                         repository_name=repository.name,
                                                                         repository_owner=repository.owner,
                                                                         changeset_revision=current_changeset_revision )
                            json_repo_info_dict = json.to_json_string( updated_repo_info_dict )
                            encoded_repo_info_dict = encoding_util.tool_shed_encode( json_repo_info_dict )
                            kwd[ 'latest_changeset_revision' ] = current_changeset_revision
                            kwd[ 'latest_ctx_rev' ] = current_ctx_rev
                            kwd[ 'updated_repo_info_dict' ] = encoded_repo_info_dict
                            return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                              action='reselect_tool_panel_section',
                                                                              **kwd ) )
                    else:
                        message = "Unable to get latest revision for repository <b>%s</b> from the tool shed, so repository " % str( repository.name )
                        message += "reinstallation is not possible at this time."
                        status = "error"
                        return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                          action='browse_repositories',
                                                                          message=message,
                                                                          status=status ) )
                else:
                    return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                      action='activate_repository',
                                                                      **kwd ) )
            if operation == "deactivate or uninstall":
                return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                  action='deactivate_or_uninstall_repository',
                                                                  **kwd ) )
            if operation == "install latest revision":
                return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                  action='install_latest_repository_revision',
                                                                  **kwd ) )
        return self.installed_repository_grid( trans, **kwd )

    @web.expose
    @web.require_admin
    def browse_tool_dependency( self, trans, **kwd ):
        message = kwd.get( 'message', ''  )
        status = kwd.get( 'status', 'done' )
        tool_dependency_ids = tool_dependency_util.get_tool_dependency_ids( as_string=False, **kwd )
        tool_dependency = tool_dependency_util.get_tool_dependency( trans, tool_dependency_ids[ 0 ] )
        if tool_dependency.in_error_state:
            message = "This tool dependency is not installed correctly (see the <b>Tool dependency installation error</b> below).  "
            message += "Choose <b>Uninstall this tool dependency</b> from the <b>Repository Actions</b> menu, correct problems "
            message += "if necessary, and try installing the dependency again."
            status = "error"
        repository = tool_dependency.tool_shed_repository
        return trans.fill_template( '/admin/tool_shed_repository/browse_tool_dependency.mako',
                                    repository=repository,
                                    tool_dependency=tool_dependency,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def browse_tool_shed( self, trans, **kwd ):
        tool_shed_url = kwd[ 'tool_shed_url' ]
        galaxy_url = web.url_for( '/', qualified=True )
        url = suc.url_join( tool_shed_url, 'repository/browse_valid_categories?galaxy_url=%s' % ( galaxy_url ) )
        return trans.response.send_redirect( url )

    @web.expose
    @web.require_admin
    def browse_tool_sheds( self, trans, **kwd ):
        message = kwd.get( 'message', ''  )
        status = kwd.get( 'status', 'done' )
        return trans.fill_template( '/webapps/galaxy/admin/tool_sheds.mako',
                                    message=message,
                                    status='error' )

    @web.expose
    @web.require_admin
    def check_for_updates( self, trans, **kwd ):
        """Send a request to the relevant tool shed to see if there are any updates."""
        repository_id = kwd.get( 'id', None )
        repository = suc.get_installed_tool_shed_repository( trans, repository_id )
        tool_shed_url = suc.get_url_from_tool_shed( trans.app, repository.tool_shed )
        url = suc.url_join( tool_shed_url,
                            'repository/check_for_updates?galaxy_url=%s&name=%s&owner=%s&changeset_revision=%s' % \
                            ( web.url_for( '/', qualified=True ), repository.name, repository.owner, repository.changeset_revision ) )
        return trans.response.send_redirect( url )

    @web.expose
    @web.require_admin
    def deactivate_or_uninstall_repository( self, trans, **kwd ):
        """
        Handle all changes when a tool shed repository is being deactivated or uninstalled.  Notice that if the repository contents include
        a file named tool_data_table_conf.xml.sample, it's entries are not removed from the defined config.shed_tool_data_table_config.  This
        is because it becomes a bit complex to determine if other installed repositories include tools that require the same entry.  For now
        we'll never delete entries from config.shed_tool_data_table_config, but we may choose to do so in the future if it becomes necessary.
        """
        message = kwd.get( 'message', ''  )
        status = kwd.get( 'status', 'done' )
        remove_from_disk = kwd.get( 'remove_from_disk', '' )
        remove_from_disk_checked = CheckboxField.is_checked( remove_from_disk )
        tool_shed_repository = suc.get_installed_tool_shed_repository( trans, kwd[ 'id' ] )
        shed_tool_conf, tool_path, relative_install_dir = suc.get_tool_panel_config_tool_path_install_dir( trans.app, tool_shed_repository )
        if relative_install_dir:
            if tool_path:
                relative_install_dir = os.path.join( tool_path, relative_install_dir )
            repository_install_dir = os.path.abspath( relative_install_dir )
        else:
            repository_install_dir = None
        errors = ''
        if kwd.get( 'deactivate_or_uninstall_repository_button', False ):
            if tool_shed_repository.includes_tools_for_display_in_tool_panel:
                # Handle tool panel alterations.
                tool_util.remove_from_tool_panel( trans, tool_shed_repository, shed_tool_conf, uninstall=remove_from_disk_checked )
            if tool_shed_repository.includes_data_managers:
                data_manager_util.remove_from_data_manager( trans.app, tool_shed_repository )
            if tool_shed_repository.includes_datatypes:
                # Deactivate proprietary datatypes.
                installed_repository_dict = datatype_util.load_installed_datatypes( trans.app, tool_shed_repository, repository_install_dir, deactivate=True )
                if installed_repository_dict:
                    converter_path = installed_repository_dict.get( 'converter_path' )
                    if converter_path is not None:
                        datatype_util.load_installed_datatype_converters( trans.app, installed_repository_dict, deactivate=True )
                    display_path = installed_repository_dict.get( 'display_path' )
                    if display_path is not None:
                        datatype_util.load_installed_display_applications( trans.app, installed_repository_dict, deactivate=True )
            if remove_from_disk_checked:
                try:
                    # Remove the repository from disk.
                    shutil.rmtree( repository_install_dir )
                    log.debug( "Removed repository installation directory: %s" % str( repository_install_dir ) )
                    removed = True
                except Exception, e:
                    log.debug( "Error removing repository installation directory %s: %s" % ( str( repository_install_dir ), str( e ) ) )
                    if isinstance( e, OSError ) and not os.path.exists( repository_install_dir ):
                        removed = True
                        log.debug( "Repository directory does not exist on disk, marking as uninstalled." )
                    else:
                        removed = False
                if removed:
                    tool_shed_repository.uninstalled = True
                    # Remove all installed tool dependencies and tool dependencies stuck in the INSTALLING state, but don't touch any
                    # repository dependencies.
                    tool_dependencies_to_uninstall = tool_shed_repository.tool_dependencies_installed_or_in_error
                    tool_dependencies_to_uninstall.extend( tool_shed_repository.tool_dependencies_being_installed )
                    for tool_dependency in tool_dependencies_to_uninstall:
                        uninstalled, error_message = tool_dependency_util.remove_tool_dependency( trans.app, tool_dependency )
                        if error_message:
                            errors = '%s  %s' % ( errors, error_message )
            tool_shed_repository.deleted = True
            if remove_from_disk_checked:
                tool_shed_repository.status = trans.install_model.ToolShedRepository.installation_status.UNINSTALLED
                tool_shed_repository.error_message = None
                # Remove the uninstalled repository and any tool dependencies from the in-memory dictionaries in the
                # installed_repository_manager.
                trans.app.installed_repository_manager.handle_repository_uninstall( tool_shed_repository )
            else:
                tool_shed_repository.status = trans.install_model.ToolShedRepository.installation_status.DEACTIVATED
            trans.install_model.context.add( tool_shed_repository )
            trans.install_model.context.flush()
            if remove_from_disk_checked:
                message = 'The repository named <b>%s</b> has been uninstalled.  ' % tool_shed_repository.name
                if errors:
                    message += 'Attempting to uninstall tool dependencies resulted in errors: %s' % errors
                    status = 'error'
                else:
                    status = 'done'
            else:
                message = 'The repository named <b>%s</b> has been deactivated.  ' % tool_shed_repository.name
                status = 'done'
            return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                              action='browse_repositories',
                                                              message=message,
                                                              status=status ) )
        remove_from_disk_check_box = CheckboxField( 'remove_from_disk', checked=remove_from_disk_checked )
        return trans.fill_template( '/admin/tool_shed_repository/deactivate_or_uninstall_repository.mako',
                                    repository=tool_shed_repository,
                                    remove_from_disk_check_box=remove_from_disk_check_box,
                                    message=message,
                                    status=status )

    @web.expose
    def display_image_in_repository( self, trans, **kwd ):
        """
        Open an image file that is contained in an installed tool shed repository or that is referenced by a URL for display.  The
        image can be defined in either a README.rst file contained in the repository or the help section of a Galaxy tool config that
        is contained in the repository.  The following image definitions are all supported.  The former $PATH_TO_IMAGES is no longer
        required, and is now ignored.
        .. image:: https://raw.github.com/galaxy/some_image.png 
        .. image:: $PATH_TO_IMAGES/some_image.png
        .. image:: /static/images/some_image.gif
        .. image:: some_image.jpg
        .. image:: /deep/some_image.png
        """
        repository_id = kwd.get( 'repository_id', None )
        relative_path_to_image_file = kwd.get( 'image_file', None )
        if repository_id and relative_path_to_image_file:
            repository = suc.get_tool_shed_repository_by_id( trans, repository_id )
            if repository:
                repo_files_dir = repository.repo_files_directory( trans.app )
                path_to_file = suc.get_absolute_path_to_file_in_repository( repo_files_dir, relative_path_to_image_file )
                if os.path.exists( path_to_file ):
                    file_name = os.path.basename( relative_path_to_image_file )
                    try:
                        extension = file_name.split( '.' )[ -1 ]
                    except Exception, e:
                        extension = None
                    if extension:
                        mimetype = trans.app.datatypes_registry.get_mimetype_by_extension( extension )
                        if mimetype:
                            trans.response.set_content_type( mimetype )
                    return open( path_to_file, 'r' )
        return None

    @web.expose
    @web.require_admin
    def find_tools_in_tool_shed( self, trans, **kwd ):
        tool_shed_url = kwd[ 'tool_shed_url' ]
        galaxy_url = web.url_for( '/', qualified=True )
        url = suc.url_join( tool_shed_url, 'repository/find_tools?galaxy_url=%s' % galaxy_url )
        return trans.response.send_redirect( url )

    @web.expose
    @web.require_admin
    def find_workflows_in_tool_shed( self, trans, **kwd ):
        tool_shed_url = kwd[ 'tool_shed_url' ]
        galaxy_url = web.url_for( '/', qualified=True )
        url = suc.url_join( tool_shed_url, 'repository/find_workflows?galaxy_url=%s' % galaxy_url )
        return trans.response.send_redirect( url )

    @web.expose
    @web.require_admin
    def generate_workflow_image( self, trans, workflow_name, repository_id=None ):
        """Return an svg image representation of a workflow dictionary created when the workflow was exported."""
        return workflow_util.generate_workflow_image( trans, workflow_name, repository_metadata_id=None, repository_id=repository_id )

    @web.json
    @web.require_admin
    def get_file_contents( self, trans, file_path ):
        # Avoid caching
        trans.response.headers['Pragma'] = 'no-cache'
        trans.response.headers['Expires'] = '0'
        return suc.get_repository_file_contents( file_path )

    @web.expose
    @web.require_admin
    def get_tool_dependencies( self, trans, repository_id, repository_name, repository_owner, changeset_revision ):
        """
        Send a request to the appropriate tool shed to retrieve the dictionary of tool dependencies defined for the received repository name,
        owner and changeset revision.  The received repository_id is the encoded id of the installed tool shed repository in Galaxy.  We need
        it so that we can derive the tool shed from which it was installed.
        """
        repository = suc.get_installed_tool_shed_repository( trans, repository_id )
        tool_shed_url = suc.get_url_from_tool_shed( trans.app, repository.tool_shed )
        url = suc.url_join( tool_shed_url,
                            'repository/get_tool_dependencies?name=%s&owner=%s&changeset_revision=%s' % \
                            ( repository_name, repository_owner, changeset_revision ) )
        raw_text = common_util.tool_shed_get( trans.app, tool_shed_url, url )
        if len( raw_text ) > 2:
            encoded_text = json.from_json_string( raw_text )
            text = encoding_util.tool_shed_decode( encoded_text )
        else:
            text = ''
        return text

    @web.expose
    @web.require_admin
    def get_updated_repository_information( self, trans, repository_id, repository_name, repository_owner, changeset_revision ):
        """
        Send a request to the appropriate tool shed to retrieve the dictionary of information required to reinstall an updated revision of an
        uninstalled tool shed repository.
        """
        repository = suc.get_installed_tool_shed_repository( trans, repository_id )
        tool_shed_url = suc.get_url_from_tool_shed( trans.app, repository.tool_shed )
        url = suc.url_join( tool_shed_url,
                            'repository/get_updated_repository_information?name=%s&owner=%s&changeset_revision=%s' % \
                            ( repository_name, repository_owner, changeset_revision ) )
        raw_text = common_util.tool_shed_get( trans.app, tool_shed_url, url )
        repo_information_dict = json.from_json_string( raw_text )
        return repo_information_dict

    def get_versions_of_tool( self, app, guid ):
        tool_version = tool_util.get_tool_version( app, guid )
        return tool_version.get_version_ids( app, reverse=True )

    @web.expose
    @web.require_admin
    def import_workflow( self, trans, workflow_name, repository_id, **kwd ):
        """Import a workflow contained in an installed tool shed repository into Galaxy."""
        message = kwd.get( 'message', ''  )
        status = kwd.get( 'status', 'done' )
        if workflow_name:
            workflow_name = encoding_util.tool_shed_decode( workflow_name )
            repository = suc.get_tool_shed_repository_by_id( trans, repository_id )
            if repository:
                workflow, status, message = workflow_util.import_workflow( trans, repository, workflow_name )
                if workflow:
                    workflow_name = encoding_util.tool_shed_encode( str( workflow.name ) )
                else:
                    message += 'Unable to locate a workflow named <b>%s</b> within the installed tool shed repository named <b>%s</b>' % \
                        ( str( workflow_name ), str( repository.name ) )
                    status = 'error'
            else:
                message = 'Invalid repository id <b>%s</b> received.' % str( repository_id )
                status = 'error'
        else:
            message = 'The value of workflow_name is required, but was not received.'
            status = 'error'
        return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                          action='view_workflow',
                                                          workflow_name=workflow_name,
                                                          repository_id=repository_id,
                                                          message=message,
                                                          status=status ) )

    @web.expose
    @web.require_admin
    def initiate_tool_dependency_installation( self, trans, tool_dependencies ):
        """Install specified dependencies for repository tools."""
        # Get the tool_shed_repository from one of the tool_dependencies.
        message = ''
        tool_shed_repository = tool_dependencies[ 0 ].tool_shed_repository
        # Get the tool_dependencies.xml file from the repository.
        tool_dependencies_config = suc.get_config_from_disk( suc.TOOL_DEPENDENCY_DEFINITION_FILENAME, tool_shed_repository.repo_path( trans.app ) )
        installed_tool_dependencies = common_install_util.handle_tool_dependencies( app=trans.app,
                                                                                    tool_shed_repository=tool_shed_repository,
                                                                                    tool_dependencies_config=tool_dependencies_config,
                                                                                    tool_dependencies=tool_dependencies,
                                                                                    from_install_manager=False )
        for installed_tool_dependency in installed_tool_dependencies:
            if installed_tool_dependency.status == trans.app.install_model.ToolDependency.installation_status.ERROR:
                text = util.unicodify( installed_tool_dependency.error_message )
                if text is not None:
                    message += '  %s' % text
        tool_dependency_ids = [ trans.security.encode_id( td.id ) for td in tool_dependencies ]
        if message:
            status = 'error'
        else:
            message = "Installed tool dependencies: %s" % ','.join( td.name for td in installed_tool_dependencies )
            status = 'done'
        td_ids = [ trans.security.encode_id( td.id ) for td in tool_shed_repository.tool_dependencies ]
        return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                          action='manage_tool_dependencies',
                                                          tool_dependency_ids=td_ids,
                                                          message=message,
                                                          status=status ) )

    @web.expose
    @web.require_admin
    def install_latest_repository_revision( self, trans, **kwd ):
        """Install the latest installable revision of a repository that has been previously installed."""
        message = kwd.get( 'message', ''  )
        status = kwd.get( 'status', 'done' )
        repository_id = kwd.get( 'id', None )
        if repository_id is not None:
            repository = suc.get_installed_tool_shed_repository( trans, repository_id )
            if repository is not None:
                tool_shed_url = suc.get_url_from_tool_shed( trans.app, repository.tool_shed )
                name = str( repository.name )
                owner = str( repository.owner )
                url = suc.url_join( tool_shed_url,
                                    'repository/get_latest_downloadable_changeset_revision?galaxy_url=%s&name=%s&owner=%s' % \
                                    ( web.url_for( '/', qualified=True ), name, owner ) )
                raw_text = common_util.tool_shed_get( trans.app, tool_shed_url, url )
                latest_downloadable_revision = json.from_json_string( raw_text )
                if latest_downloadable_revision == suc.INITIAL_CHANGELOG_HASH:
                    message = 'Error retrieving the latest downloadable revision for this repository via the url <b>%s</b>.' % url
                    status = 'error'
                else:
                    # Make sure the latest changeset_revision of the repository has not already been installed.
                    # Updates to installed repository revisions may have occurred, so make sure to locate the
                    # appropriate repository revision if one exists.  We need to create a temporary repo_info_tuple
                    # with the following entries to handle this.
                    # ( description, clone_url, changeset_revision, ctx_rev, owner, repository_dependencies, tool_dependencies )
                    tmp_clone_url = suc.url_join( tool_shed_url, 'repos', owner, name )
                    tmp_repo_info_tuple = ( None, tmp_clone_url, latest_downloadable_revision, None, owner, None, None )
                    installed_repository, installed_changeset_revision = \
                        suc.repository_was_previously_installed( trans, tool_shed_url, name, tmp_repo_info_tuple )
                    if installed_repository:
                        current_changeset_revision = str( installed_repository.changeset_revision )
                        message = 'Revision <b>%s</b> of repository <b>%s</b> owned by <b>%s</b> has already been installed.' % \
                            ( latest_downloadable_revision, name, owner )
                        if current_changeset_revision != latest_downloadable_revision:
                            message += '  The current changeset revision is <b>%s</b>.' % current_changeset_revision
                        status = 'error'
                    else:
                        # Install the latest downloadable revision of the repository.
                        url = suc.url_join( tool_shed_url,
                                            'repository/install_repositories_by_revision?name=%s&owner=%s&changeset_revisions=%s&galaxy_url=%s' % \
                                            ( name, owner, latest_downloadable_revision, web.url_for( '/', qualified=True ) ) )
                        return trans.response.send_redirect( url )
            else:
                message = 'Cannot locate installed tool shed repository with encoded id <b>%s</b>.' % str( repository_id )
                status = 'error'
        else:
            message = 'The request parameters did not include the required encoded <b>id</b> of installed repository.'
            status = 'error'
        return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                          action='browse_repositories',
                                                          message=message,
                                                          status=status ) )


    @web.expose
    @web.require_admin
    def install_tool_dependencies( self, trans, **kwd ):
        message = kwd.get( 'message', ''  )
        status = kwd.get( 'status', 'done' )
        tool_dependency_ids = tool_dependency_util.get_tool_dependency_ids( as_string=False, **kwd )
        tool_dependencies = []
        for tool_dependency_id in tool_dependency_ids:
            tool_dependency = tool_dependency_util.get_tool_dependency( trans, tool_dependency_id )
            tool_dependencies.append( tool_dependency )
        if kwd.get( 'install_tool_dependencies_button', False ):
            # Filter tool dependencies to only those that are installed.
            tool_dependencies_for_installation = []
            for tool_dependency in tool_dependencies:
                if tool_dependency.status in [ trans.install_model.ToolDependency.installation_status.UNINSTALLED,
                                               trans.install_model.ToolDependency.installation_status.ERROR ]:
                    tool_dependencies_for_installation.append( tool_dependency )
            if tool_dependencies_for_installation:
                # Redirect back to the ToolDependencyGrid before initiating installation.
                encoded_tool_dependency_for_installation_ids = [ trans.security.encode_id( td.id ) for td in tool_dependencies_for_installation ]
                new_kwd = dict( action='manage_tool_dependencies',
                                operation='initiate_tool_dependency_installation',
                                tool_dependency_ids=encoded_tool_dependency_for_installation_ids,
                                message=message,
                                status=status )
                return self.tool_dependency_grid( trans, **new_kwd )
            else:
                message = 'All of the selected tool dependencies are already installed.'
                status = 'error'
                return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                  action='manage_repository_tool_dependencies',
                                                                  tool_dependency_ids=tool_dependency_ids,
                                                                  status=status,
                                                                  message=message ) )
        return trans.fill_template( '/admin/tool_shed_repository/install_tool_dependencies.mako',
                                    tool_dependencies=tool_dependencies,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def install_tool_shed_repositories( self, trans, tool_shed_repositories, reinstalling=False, **kwd  ):
        """Install specified tool shed repositories."""
        shed_tool_conf = kwd.get( 'shed_tool_conf', '' )
        tool_path = kwd[ 'tool_path' ]
        install_tool_dependencies = CheckboxField.is_checked( kwd.get( 'install_tool_dependencies', '' ) )
        # There must be a one-to-one mapping between items in the 3 lists: tool_shed_repositories, tool_panel_section_keys, repo_info_dicts.
        tool_panel_section_keys = util.listify( kwd[ 'tool_panel_section_keys' ] )
        repo_info_dicts = util.listify( kwd[ 'repo_info_dicts' ] )
        for index, tool_shed_repository in enumerate( tool_shed_repositories ):
            repo_info_dict = repo_info_dicts[ index ]
            tool_panel_section_key = tool_panel_section_keys[ index ]
            repository_util.install_tool_shed_repository( trans,
                                                          tool_shed_repository,
                                                          repo_info_dict,
                                                          tool_panel_section_key,
                                                          shed_tool_conf,
                                                          tool_path,
                                                          install_tool_dependencies,
                                                          reinstalling=reinstalling )
        tsr_ids_for_monitoring = [ trans.security.encode_id( tsr.id ) for tsr in tool_shed_repositories ]
        return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                          action='monitor_repository_installation',
                                                          tool_shed_repository_ids=tsr_ids_for_monitoring ) )

    @web.expose
    @web.require_admin
    def manage_repositories( self, trans, **kwd ):
        message = kwd.get( 'message', ''  )
        status = kwd.get( 'status', 'done' )
        tsridslist = repository_util.get_tool_shed_repository_ids( **kwd )
        if 'operation' in kwd:
            operation = kwd[ 'operation' ].lower()
            if not tsridslist:
                message = 'Select at least 1 tool shed repository to %s.' % operation
                kwd[ 'message' ] = message
                kwd[ 'status' ] = 'error'
                del kwd[ 'operation' ]
                return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                  action='manage_repositories',
                                                                  **kwd ) )
            if operation == 'browse':
                return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                  action='browse_repository',
                                                                  **kwd ) )
            elif operation == 'uninstall':
                # TODO: I believe this block should be removed, but make sure..
                repositories_for_uninstallation = []
                for repository_id in tsridslist:
                    repository = trans.install_model.context.query( trans.install_model.ToolShedRepository ).get( trans.security.decode_id( repository_id ) )
                    if repository.status in [ trans.install_model.ToolShedRepository.installation_status.INSTALLED,
                                              trans.install_model.ToolShedRepository.installation_status.ERROR ]:
                        repositories_for_uninstallation.append( repository )
                if repositories_for_uninstallation:
                    return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                      action='uninstall_repositories',
                                                                      **kwd ) )
                else:
                    kwd[ 'message' ] = 'All selected tool shed repositories are already uninstalled.'
                    kwd[ 'status' ] = 'error'
            elif operation == "install":
                reinstalling = util.string_as_bool( kwd.get( 'reinstalling', False ) )
                encoded_kwd = kwd[ 'encoded_kwd' ]
                decoded_kwd = encoding_util.tool_shed_decode( encoded_kwd )
                tsr_ids = decoded_kwd[ 'tool_shed_repository_ids' ]
                tool_panel_section_keys = decoded_kwd[ 'tool_panel_section_keys' ]
                repo_info_dicts = decoded_kwd[ 'repo_info_dicts' ]
                filtered_repo_info_dicts = []
                filtered_tool_panel_section_keys = []
                repositories_for_installation = []
                # Some repositories may have repository dependencies that are required to be installed before the dependent repository, so we'll
                # order the list of tsr_ids to ensure all repositories install in the required order.
                ordered_tsr_ids, ordered_repo_info_dicts, ordered_tool_panel_section_keys = \
                    repository_util.order_components_for_installation( trans,
                                                                       tsr_ids,
                                                                       repo_info_dicts,
                                                                       tool_panel_section_keys=tool_panel_section_keys )
                for tsr_id in ordered_tsr_ids:
                    repository = trans.install_model.context.query( trans.install_model.ToolShedRepository ).get( trans.security.decode_id( tsr_id ) )
                    if repository.status in [ trans.install_model.ToolShedRepository.installation_status.NEW,
                                              trans.install_model.ToolShedRepository.installation_status.UNINSTALLED ]:
                        repositories_for_installation.append( repository )
                        repo_info_dict, tool_panel_section_key = repository_util.get_repository_components_for_installation( tsr_id,
                                                                                                                             ordered_tsr_ids,
                                                                                                                             ordered_repo_info_dicts,
                                                                                                                             ordered_tool_panel_section_keys )
                        filtered_repo_info_dicts.append( repo_info_dict )
                        filtered_tool_panel_section_keys.append( tool_panel_section_key )
                if repositories_for_installation:
                    decoded_kwd[ 'repo_info_dicts' ] = filtered_repo_info_dicts
                    decoded_kwd[ 'tool_panel_section_keys' ] = filtered_tool_panel_section_keys
                    self.install_tool_shed_repositories( trans, repositories_for_installation, reinstalling=reinstalling, **decoded_kwd )
                else:
                    kwd[ 'message' ] = 'All selected tool shed repositories are already installed.'
                    kwd[ 'status' ] = 'error'
        return self.repository_installation_grid( trans, **kwd )

    @web.expose
    @web.require_admin
    def manage_repository( self, trans, **kwd ):
        message = kwd.get( 'message', ''  )
        status = kwd.get( 'status', 'done' )
        repository_id = kwd.get( 'id', None )
        if repository_id is None:
            return trans.show_error_message( 'Missing required encoded repository id.' )
        operation = kwd.get( 'operation', None )
        repository = suc.get_installed_tool_shed_repository( trans, repository_id )
        if repository is None:
            return trans.show_error_message( 'Invalid repository specified.' )
        tool_shed_url = suc.get_url_from_tool_shed( trans.app, repository.tool_shed )
        name = str( repository.name )
        owner = str( repository.owner )
        installed_changeset_revision = str( repository.installed_changeset_revision )
        if repository.status in [ trans.install_model.ToolShedRepository.installation_status.CLONING ]:
            tool_shed_repository_ids = [ repository_id ]
            return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                              action='monitor_repository_installation',
                                                              tool_shed_repository_ids=tool_shed_repository_ids ) )
        if repository.can_install and operation == 'install':
            # Send a request to the tool shed to install the repository.
            url = suc.url_join( tool_shed_url,
                                'repository/install_repositories_by_revision?name=%s&owner=%s&changeset_revisions=%s&galaxy_url=%s' % \
                                ( name, owner, installed_changeset_revision, ( web.url_for( '/', qualified=True ) ) ) )
            return trans.response.send_redirect( url )
        description = kwd.get( 'description', repository.description )
        shed_tool_conf, tool_path, relative_install_dir = suc.get_tool_panel_config_tool_path_install_dir( trans.app, repository )
        if relative_install_dir:
            repo_files_dir = os.path.abspath( os.path.join( tool_path, relative_install_dir, name ) )
        else:
            repo_files_dir = None
        if repository.in_error_state:
            message = "This repository is not installed correctly (see the <b>Repository installation error</b> below).  Choose "
            message += "<b>Reset to install</b> from the <b>Repository Actions</b> menu, correct problems if necessary and try "
            message += "installing the repository again."
            status = "error"
        elif repository.can_install:
            message = "This repository is not installed.  You can install it by choosing  <b>Install</b> from the <b>Repository Actions</b> menu."
            status = "error"
        elif kwd.get( 'edit_repository_button', False ):
            if description != repository.description:
                repository.description = description
                trans.install_model.context.add( repository )
                trans.install_model.context.flush()
            message = "The repository information has been updated."
        containers_dict = metadata_util.populate_containers_dict_from_repository_metadata( trans=trans,
                                                                                           tool_shed_url=tool_shed_url,
                                                                                           tool_path=tool_path,
                                                                                           repository=repository,
                                                                                           reinstalling=False,
                                                                                           required_repo_info_dicts=None )
        return trans.fill_template( '/admin/tool_shed_repository/manage_repository.mako',
                                    repository=repository,
                                    description=description,
                                    repo_files_dir=repo_files_dir,
                                    containers_dict=containers_dict,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def manage_repository_tool_dependencies( self, trans, **kwd ):
        message = kwd.get( 'message', ''  )
        status = kwd.get( 'status', 'done' )
        tool_dependency_ids = tool_dependency_util.get_tool_dependency_ids( as_string=False, **kwd )
        if tool_dependency_ids:
            # We need a tool_shed_repository, so get it from one of the tool_dependencies.
            tool_dependency = tool_dependency_util.get_tool_dependency( trans, tool_dependency_ids[ 0 ] )
            tool_shed_repository = tool_dependency.tool_shed_repository
        else:
            # The user must be on the manage_repository_tool_dependencies page and clicked the button to either install or uninstall a
            # tool dependency, but they didn't check any of the available tool dependencies on which to perform the action.
            repository_id = kwd.get( 'repository_id', None )
            tool_shed_repository = suc.get_tool_shed_repository_by_id( trans, repository_id )
        if 'operation' in kwd:
            operation = kwd[ 'operation' ].lower()
            if not tool_dependency_ids:
                message = 'Select at least 1 tool dependency to %s.' % operation
                kwd[ 'message' ] = message
                kwd[ 'status' ] = 'error'
                del kwd[ 'operation' ]
                return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                  action='manage_repository_tool_dependencies',
                                                                  **kwd ) )
            if operation == 'browse':
                return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                  action='browse_tool_dependency',
                                                                  **kwd ) )
            elif operation == 'uninstall':
                tool_dependencies_for_uninstallation = []
                for tool_dependency_id in tool_dependency_ids:
                    tool_dependency = tool_dependency_util.get_tool_dependency( trans, tool_dependency_id )
                    if tool_dependency.status in [ trans.install_model.ToolDependency.installation_status.INSTALLED,
                                                   trans.install_model.ToolDependency.installation_status.ERROR ]:
                        tool_dependencies_for_uninstallation.append( tool_dependency )
                if tool_dependencies_for_uninstallation:
                    return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                      action='uninstall_tool_dependencies',
                                                                      **kwd ) )
                else:
                    message = 'No selected tool dependencies can be uninstalled, you may need to use the <b>Repair repository</b> feature.'
                    status = 'error'
            elif operation == "install":
                if trans.app.config.tool_dependency_dir:
                    tool_dependencies_for_installation = []
                    for tool_dependency_id in tool_dependency_ids:
                        tool_dependency = tool_dependency_util.get_tool_dependency( trans, tool_dependency_id )
                        if tool_dependency.status in [ trans.install_model.ToolDependency.installation_status.NEVER_INSTALLED,
                                                       trans.install_model.ToolDependency.installation_status.UNINSTALLED ]:
                            tool_dependencies_for_installation.append( tool_dependency )
                    if tool_dependencies_for_installation:
                        self.initiate_tool_dependency_installation( trans, tool_dependencies_for_installation )
                    else:
                        message = 'All selected tool dependencies are already installed.'
                        status = 'error'
                else:
                        message = 'Set the value of your <b>tool_dependency_dir</b> setting in your Galaxy config file (universe_wsgi.ini) '
                        message += ' and restart your Galaxy server to install tool dependencies.'
                        status = 'error'
        installed_tool_dependencies_select_field = suc.build_tool_dependencies_select_field( trans,
                                                                                             tool_shed_repository=tool_shed_repository,
                                                                                             name='inst_td_ids',
                                                                                             uninstalled_only=False )
        uninstalled_tool_dependencies_select_field = suc.build_tool_dependencies_select_field( trans,
                                                                                               tool_shed_repository=tool_shed_repository,
                                                                                               name='uninstalled_tool_dependency_ids',
                                                                                               uninstalled_only=True )
        return trans.fill_template( '/admin/tool_shed_repository/manage_repository_tool_dependencies.mako',
                                    repository=tool_shed_repository,
                                    installed_tool_dependencies_select_field=installed_tool_dependencies_select_field,
                                    uninstalled_tool_dependencies_select_field=uninstalled_tool_dependencies_select_field,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def manage_tool_dependencies( self, trans, **kwd ):
        # This method is called when tool dependencies are being installed.  See the related manage_repository_tool_dependencies
        # method for managing the tool dependencies for a specified installed tool shed repository.
        message = kwd.get( 'message', ''  )
        status = kwd.get( 'status', 'done' )
        tool_dependency_ids = tool_dependency_util.get_tool_dependency_ids( as_string=False, **kwd )
        repository_id = kwd.get( 'repository_id', None )
        if tool_dependency_ids:
            # We need a tool_shed_repository, so get it from one of the tool_dependencies.
            tool_dependency = tool_dependency_util.get_tool_dependency( trans, tool_dependency_ids[ 0 ] )
            tool_shed_repository = tool_dependency.tool_shed_repository
        else:
            # The user must be on the manage_repository_tool_dependencies page and clicked the button to either install or uninstall a
            # tool dependency, but they didn't check any of the available tool dependencies on which to perform the action.
            tool_shed_repository = suc.get_tool_shed_repository_by_id( trans, repository_id )
        self.tool_dependency_grid.title = "Tool shed repository '%s' tool dependencies"  % tool_shed_repository.name
        if 'operation' in kwd:
            operation = kwd[ 'operation' ].lower()
            if not tool_dependency_ids:
                message = 'Select at least 1 tool dependency to %s.' % operation
                kwd[ 'message' ] = message
                kwd[ 'status' ] = 'error'
                del kwd[ 'operation' ]
                return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                  action='manage_tool_dependencies',
                                                                  **kwd ) )
            if operation == 'browse':
                return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                  action='browse_tool_dependency',
                                                                  **kwd ) )
            elif operation == "install":
                if trans.app.config.tool_dependency_dir:
                    tool_dependencies_for_installation = []
                    for tool_dependency_id in tool_dependency_ids:
                        tool_dependency = tool_dependency_util.get_tool_dependency( trans, tool_dependency_id )
                        if tool_dependency.status in [ trans.install_model.ToolDependency.installation_status.NEVER_INSTALLED,
                                                       trans.install_model.ToolDependency.installation_status.UNINSTALLED ]:
                            tool_dependencies_for_installation.append( tool_dependency )
                    if tool_dependencies_for_installation:
                        self.initiate_tool_dependency_installation( trans, tool_dependencies_for_installation )
                    else:
                        kwd[ 'message' ] = 'All selected tool dependencies are already installed.'
                        kwd[ 'status' ] = 'error'
                else:
                        message = 'Set the value of your <b>tool_dependency_dir</b> setting in your Galaxy config file (universe_wsgi.ini) '
                        message += ' and restart your Galaxy server to install tool dependencies.'
                        kwd[ 'message' ] = message
                        kwd[ 'status' ] = 'error'
        # Redirect if no tool dependencies are in the process of being installed.
        if tool_shed_repository.tool_dependencies_being_installed:
            return self.tool_dependency_grid( trans, **kwd )
        return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                          action='manage_repository_tool_dependencies',
                                                          tool_dependency_ids=tool_dependency_ids,
                                                          repository_id=repository_id,
                                                          message=message,
                                                          status=status ) )

    @web.expose
    @web.require_admin
    def monitor_repository_installation( self, trans, **kwd ):
        tsridslist = repository_util.get_tool_shed_repository_ids( **kwd )
        if not tsridslist:
            tsridslist = suc.get_ids_of_tool_shed_repositories_being_installed( trans, as_string=False )
        kwd[ 'tool_shed_repository_ids' ] = tsridslist
        return self.repository_installation_grid( trans, **kwd )

    @web.json
    @web.require_admin
    def open_folder( self, trans, folder_path ):
        # Avoid caching
        trans.response.headers['Pragma'] = 'no-cache'
        trans.response.headers['Expires'] = '0'
        return suc.open_repository_files_folder( trans, folder_path )

    @web.expose
    @web.require_admin
    def prepare_for_install( self, trans, **kwd ):
        if not suc.have_shed_tool_conf_for_install( trans ):
            message = 'The <b>tool_config_file</b> setting in <b>universe_wsgi.ini</b> must include at least one shed tool configuration file name with a '
            message += '<b>&lt;toolbox&gt;</b> tag that includes a <b>tool_path</b> attribute value which is a directory relative to the Galaxy installation '
            message += 'directory in order to automatically install tools from a Galaxy tool shed (e.g., the file name <b>shed_tool_conf.xml</b> whose '
            message += '<b>&lt;toolbox&gt;</b> tag is <b>&lt;toolbox tool_path="../shed_tools"&gt;</b>).<p/>See the '
            message += '<a href="http://wiki.g2.bx.psu.edu/InstallingRepositoriesToGalaxy" target="_blank">Installation of Galaxy tool shed repository tools '
            message += 'into a local Galaxy instance</a> section of the Galaxy tool shed wiki for all of the details.'
            return trans.show_error_message( message )
        message = kwd.get( 'message', ''  )
        status = kwd.get( 'status', 'done' )
        shed_tool_conf = kwd.get( 'shed_tool_conf', None )
        tool_shed_url = kwd.get( 'tool_shed_url', None )
        # Handle repository dependencies, which do not include those that are required only for compiling a dependent repository's tool dependencies.
        has_repository_dependencies = util.string_as_bool( kwd.get( 'has_repository_dependencies', False ) )
        install_repository_dependencies = kwd.get( 'install_repository_dependencies', '' )
        # Every repository will be installed into the same tool panel section or all will be installed outside of any sections.
        new_tool_panel_section_label = kwd.get( 'new_tool_panel_section_label', '' )
        tool_panel_section_id = kwd.get( 'tool_panel_section_id', '' )
        tool_panel_section_keys = []
        # One or more repositories may include tools, but not necessarily all of them.
        includes_tools = util.string_as_bool( kwd.get( 'includes_tools', False ) )
        # Some tools should not be displayed in the tool panel (e.g., DataManager tools and datatype converters).
        includes_tools_for_display_in_tool_panel = util.string_as_bool( kwd.get( 'includes_tools_for_display_in_tool_panel', False ) )
        includes_tool_dependencies = util.string_as_bool( kwd.get( 'includes_tool_dependencies', False ) )
        install_tool_dependencies = kwd.get( 'install_tool_dependencies', '' )
        encoded_repo_info_dicts = kwd.get( 'encoded_repo_info_dicts', '' )
        if encoded_repo_info_dicts:
            encoded_repo_info_dicts = encoded_repo_info_dicts.split( encoding_util.encoding_sep )
        if not encoded_repo_info_dicts:
            # The request originated in the tool shed via a tool search.
            repository_ids = kwd.get( 'repository_ids', None )
            changeset_revisions = kwd.get( 'changeset_revisions', None )
            # Get the information necessary to install each repository.
            url = suc.url_join( tool_shed_url,
                                'repository/get_repository_information?repository_ids=%s&changeset_revisions=%s' % \
                                ( str( repository_ids ), str( changeset_revisions ) ) )
            raw_text = common_util.tool_shed_get( trans.app, tool_shed_url, url )
            repo_information_dict = json.from_json_string( raw_text )
            for encoded_repo_info_dict in repo_information_dict.get( 'repo_info_dicts', [] ):
                decoded_repo_info_dict = encoding_util.tool_shed_decode( encoded_repo_info_dict )
                if not includes_tools:
                    includes_tools = util.string_as_bool( decoded_repo_info_dict.get( 'includes_tools', False ) )
                if not includes_tools_for_display_in_tool_panel:
                    includes_tools_for_display_in_tool_panel = util.string_as_bool( decoded_repo_info_dict.get( 'includes_tools_for_display_in_tool_panel', False ) )
                if not has_repository_dependencies:
                    has_repository_dependencies = util.string_as_bool( repo_information_dict.get( 'has_repository_dependencies', False ) )
                if not includes_tool_dependencies:
                    includes_tool_dependencies = util.string_as_bool( repo_information_dict.get( 'includes_tool_dependencies', False ) )
            encoded_repo_info_dicts = util.listify( repo_information_dict.get( 'repo_info_dicts', [] ) )
        repo_info_dicts = [ encoding_util.tool_shed_decode( encoded_repo_info_dict ) for encoded_repo_info_dict in encoded_repo_info_dicts ]
        if ( not includes_tools_for_display_in_tool_panel and kwd.get( 'select_shed_tool_panel_config_button', False ) ) or \
            ( includes_tools_for_display_in_tool_panel and kwd.get( 'select_tool_panel_section_button', False ) ):
            install_repository_dependencies = CheckboxField.is_checked( install_repository_dependencies )
            if includes_tool_dependencies:
                install_tool_dependencies = CheckboxField.is_checked( install_tool_dependencies )
            else:
                install_tool_dependencies = False
            tool_path = suc.get_tool_path_by_shed_tool_conf_filename( trans, shed_tool_conf )
            installation_dict = dict( install_repository_dependencies=install_repository_dependencies,
                                      new_tool_panel_section_label=new_tool_panel_section_label,
                                      no_changes_checked=False,
                                      repo_info_dicts=repo_info_dicts,
                                      tool_panel_section_id=tool_panel_section_id,
                                      tool_path=tool_path,
                                      tool_shed_url=tool_shed_url )
            created_or_updated_tool_shed_repositories, tool_panel_section_keys, repo_info_dicts, filtered_repo_info_dicts = \
                repository_util.handle_tool_shed_repositories( trans, installation_dict, using_api=False )
            if created_or_updated_tool_shed_repositories:
                installation_dict = dict( created_or_updated_tool_shed_repositories=created_or_updated_tool_shed_repositories,
                                          filtered_repo_info_dicts=filtered_repo_info_dicts,
                                          has_repository_dependencies=has_repository_dependencies,
                                          includes_tool_dependencies=includes_tool_dependencies,
                                          includes_tools=includes_tools,
                                          includes_tools_for_display_in_tool_panel=includes_tools_for_display_in_tool_panel,
                                          install_repository_dependencies=install_repository_dependencies,
                                          install_tool_dependencies=install_tool_dependencies,
                                          message=message,
                                          new_tool_panel_section_label=new_tool_panel_section_label,
                                          shed_tool_conf=shed_tool_conf,
                                          status=status,
                                          tool_panel_section_id=tool_panel_section_id,
                                          tool_panel_section_keys=tool_panel_section_keys,
                                          tool_path=tool_path,
                                          tool_shed_url=tool_shed_url )
                encoded_kwd, query, tool_shed_repositories, encoded_repository_ids = repository_util.initiate_repository_installation( trans, installation_dict )
                return trans.fill_template( 'admin/tool_shed_repository/initiate_repository_installation.mako',
                                            encoded_kwd=encoded_kwd,
                                            query=query,
                                            tool_shed_repositories=tool_shed_repositories,
                                            initiate_repository_installation_ids=encoded_repository_ids,
                                            reinstalling=False )
            else:
                kwd[ 'message' ] = message
                kwd[ 'status' ] = status
                return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                  action='manage_repositories',
                                                                  **kwd ) )
        shed_tool_conf_select_field = tool_util.build_shed_tool_conf_select_field( trans )
        tool_path = suc.get_tool_path_by_shed_tool_conf_filename( trans, shed_tool_conf )
        tool_panel_section_select_field = tool_util.build_tool_panel_section_select_field( trans )
        if len( repo_info_dicts ) == 1:
            # If we're installing a single repository, see if it contains a readme or dependencies that we can display.
            repo_info_dict = repo_info_dicts[ 0 ]
            dependencies_for_repository_dict = common_install_util.get_dependencies_for_repository( trans,
                                                                                                    tool_shed_url,
                                                                                                    repo_info_dict,
                                                                                                    includes_tool_dependencies )
            changeset_revision = dependencies_for_repository_dict.get( 'changeset_revision', None )
            if not has_repository_dependencies:
                has_repository_dependencies = dependencies_for_repository_dict.get( 'has_repository_dependencies', False )
            if not includes_tool_dependencies:
                includes_tool_dependencies = dependencies_for_repository_dict.get( 'includes_tool_dependencies', False )
            if not includes_tools:
                includes_tools = dependencies_for_repository_dict.get( 'includes_tools', False )
            if not includes_tools_for_display_in_tool_panel:
                includes_tools_for_display_in_tool_panel = dependencies_for_repository_dict.get( 'includes_tools_for_display_in_tool_panel', False )
            installed_repository_dependencies = dependencies_for_repository_dict.get( 'installed_repository_dependencies', None )
            installed_tool_dependencies = dependencies_for_repository_dict.get( 'installed_tool_dependencies', None )
            missing_repository_dependencies = dependencies_for_repository_dict.get( 'missing_repository_dependencies', None )
            missing_tool_dependencies = dependencies_for_repository_dict.get( 'missing_tool_dependencies', None )
            name = dependencies_for_repository_dict.get( 'name', None )
            repository_owner = dependencies_for_repository_dict.get( 'repository_owner', None )
            readme_files_dict = readme_util.get_readme_files_dict_for_display( trans, tool_shed_url, repo_info_dict )
            # We're handling 1 of 2 scenarios here: (1) we're installing a tool shed repository for the first time, so we've retrieved the list of installed
            # and missing repository dependencies from the database (2) we're handling the scenario where an error occurred during the installation process,
            # so we have a tool_shed_repository record in the database with associated repository dependency records.  Since we have the repository
            # dependencies in either case, we'll merge the list of missing repository dependencies into the list of installed repository dependencies since
            # each displayed repository dependency will display a status, whether installed or missing.
            containers_dict = repository_util.populate_containers_dict_for_new_install( trans=trans,
                                                                                        tool_shed_url=tool_shed_url,
                                                                                        tool_path=tool_path,
                                                                                        readme_files_dict=readme_files_dict,
                                                                                        installed_repository_dependencies=installed_repository_dependencies,
                                                                                        missing_repository_dependencies=missing_repository_dependencies,
                                                                                        installed_tool_dependencies=installed_tool_dependencies,
                                                                                        missing_tool_dependencies=missing_tool_dependencies )
        else:
            # We're installing a list of repositories, each of which may have tool dependencies or repository dependencies.
            containers_dicts = []
            for repo_info_dict in repo_info_dicts:
                dependencies_for_repository_dict = common_install_util.get_dependencies_for_repository( trans,
                                                                                                        tool_shed_url,
                                                                                                        repo_info_dict,
                                                                                                        includes_tool_dependencies )
                changeset_revision = dependencies_for_repository_dict.get( 'changeset_revision', None )
                if not has_repository_dependencies:
                    has_repository_dependencies = dependencies_for_repository_dict.get( 'has_repository_dependencies', False )
                if not includes_tool_dependencies:
                    includes_tool_dependencies = dependencies_for_repository_dict.get( 'includes_tool_dependencies', False )
                if not includes_tools:
                    includes_tools = dependencies_for_repository_dict.get( 'includes_tools', False )
                if not includes_tools_for_display_in_tool_panel:
                    includes_tools_for_display_in_tool_panel = dependencies_for_repository_dict.get( 'includes_tools_for_display_in_tool_panel', False )
                installed_repository_dependencies = dependencies_for_repository_dict.get( 'installed_repository_dependencies', None )
                installed_tool_dependencies = dependencies_for_repository_dict.get( 'installed_tool_dependencies', None )
                missing_repository_dependencies = dependencies_for_repository_dict.get( 'missing_repository_dependencies', None )
                missing_tool_dependencies = dependencies_for_repository_dict.get( 'missing_tool_dependencies', None )
                name = dependencies_for_repository_dict.get( 'name', None )
                repository_owner = dependencies_for_repository_dict.get( 'repository_owner', None )
                containers_dict = repository_util.populate_containers_dict_for_new_install( trans=trans,
                                                                                            tool_shed_url=tool_shed_url,
                                                                                            tool_path=tool_path,
                                                                                            readme_files_dict=None,
                                                                                            installed_repository_dependencies=installed_repository_dependencies,
                                                                                            missing_repository_dependencies=missing_repository_dependencies,
                                                                                            installed_tool_dependencies=installed_tool_dependencies,
                                                                                            missing_tool_dependencies=missing_tool_dependencies )
                containers_dicts.append( containers_dict )
            # Merge all containers into a single container.
            containers_dict = repository_util.merge_containers_dicts_for_new_install( containers_dicts )
        # Handle tool dependencies check box.
        if trans.app.config.tool_dependency_dir is None:
            if includes_tool_dependencies:
                message = "Tool dependencies defined in this repository can be automatically installed if you set the value of your <b>tool_dependency_dir</b> "
                message += "setting in your Galaxy config file (universe_wsgi.ini) and restart your Galaxy server before installing the repository."
                status = "warning"
            install_tool_dependencies_check_box_checked = False
        else:
            install_tool_dependencies_check_box_checked = True
        install_tool_dependencies_check_box = CheckboxField( 'install_tool_dependencies', checked=install_tool_dependencies_check_box_checked )
        # Handle repository dependencies check box.
        install_repository_dependencies_check_box = CheckboxField( 'install_repository_dependencies', checked=True )
        encoded_repo_info_dicts = encoding_util.encoding_sep.join( encoded_repo_info_dicts )
        tool_shed_url = kwd[ 'tool_shed_url' ]
        if includes_tools_for_display_in_tool_panel:
            return trans.fill_template( '/admin/tool_shed_repository/select_tool_panel_section.mako',
                                        encoded_repo_info_dicts=encoded_repo_info_dicts,
                                        includes_tools=includes_tools,
                                        includes_tools_for_display_in_tool_panel=includes_tools_for_display_in_tool_panel,
                                        includes_tool_dependencies=includes_tool_dependencies,
                                        install_tool_dependencies_check_box=install_tool_dependencies_check_box,
                                        has_repository_dependencies=has_repository_dependencies,
                                        install_repository_dependencies_check_box=install_repository_dependencies_check_box,
                                        new_tool_panel_section_label=new_tool_panel_section_label,
                                        containers_dict=containers_dict,
                                        shed_tool_conf=shed_tool_conf,
                                        shed_tool_conf_select_field=shed_tool_conf_select_field,
                                        tool_panel_section_select_field=tool_panel_section_select_field,
                                        tool_shed_url=tool_shed_url,
                                        message=message,
                                        status=status )
        else:
            # If installing repositories that includes no tools and has no repository dependencies, display a page allowing the Galaxy administrator to
            # select a shed-related tool panel configuration file whose tool_path setting will be the location the repositories will be installed.
            return trans.fill_template( '/admin/tool_shed_repository/select_shed_tool_panel_config.mako',
                                        encoded_repo_info_dicts=encoded_repo_info_dicts,
                                        includes_tools=includes_tools,
                                        includes_tools_for_display_in_tool_panel=includes_tools_for_display_in_tool_panel,
                                        includes_tool_dependencies=includes_tool_dependencies,
                                        install_tool_dependencies_check_box=install_tool_dependencies_check_box,
                                        has_repository_dependencies=has_repository_dependencies,
                                        install_repository_dependencies_check_box=install_repository_dependencies_check_box,
                                        new_tool_panel_section_label=new_tool_panel_section_label,
                                        containers_dict=containers_dict,
                                        shed_tool_conf=shed_tool_conf,
                                        shed_tool_conf_select_field=shed_tool_conf_select_field,
                                        tool_panel_section_select_field=tool_panel_section_select_field,
                                        tool_shed_url=tool_shed_url,
                                        message=message,
                                        status=status )

    @web.expose
    @web.require_admin
    def reinstall_repository( self, trans, **kwd ):
        """
        Reinstall a tool shed repository that has been previously uninstalled, making sure to handle all repository
        and tool dependencies of the repository.
        """
        message = kwd.get( 'message', '' )
        status = kwd.get( 'status', 'done' )
        repository_id = kwd[ 'id' ]
        tool_shed_repository = suc.get_installed_tool_shed_repository( trans, repository_id )
        no_changes = kwd.get( 'no_changes', '' )
        no_changes_checked = CheckboxField.is_checked( no_changes )
        install_repository_dependencies = CheckboxField.is_checked( kwd.get( 'install_repository_dependencies', '' ) )
        install_tool_dependencies = CheckboxField.is_checked( kwd.get( 'install_tool_dependencies', '' ) )
        shed_tool_conf, tool_path, relative_install_dir = suc.get_tool_panel_config_tool_path_install_dir( trans.app, tool_shed_repository )
        repository_clone_url = suc.generate_clone_url_for_installed_repository( trans.app, tool_shed_repository )
        clone_dir = os.path.join( tool_path, suc.generate_tool_shed_repository_install_dir( repository_clone_url,
                                                                                            tool_shed_repository.installed_changeset_revision ) )
        relative_install_dir = os.path.join( clone_dir, tool_shed_repository.name )
        tool_shed_url = suc.get_url_from_tool_shed( trans.app, tool_shed_repository.tool_shed )
        tool_section = None
        tool_panel_section_id = kwd.get( 'tool_panel_section_id', '' )
        new_tool_panel_section_label = kwd.get( 'new_tool_panel_section_label', '' )
        tool_panel_section_key = None
        tool_panel_section_keys = []
        metadata = tool_shed_repository.metadata
        # Keep track of tool dependencies defined for the current repository or those defined for any of it's repository dependencies.
        includes_tool_dependencies = tool_shed_repository.includes_tool_dependencies
        if tool_shed_repository.includes_tools_for_display_in_tool_panel:
            # Handle the selected tool panel location for loading tools included in the tool shed repository.
            tool_section, tool_panel_section_key = \
                tool_util.handle_tool_panel_selection( trans=trans,
                                                       metadata=metadata,
                                                       no_changes_checked=no_changes_checked,
                                                       tool_panel_section_id=tool_panel_section_id,
                                                       new_tool_panel_section_label=new_tool_panel_section_label )
            if tool_section is not None:
                # Just in case the tool_section.id differs from tool_panel_section_id, which it shouldn't...
                tool_panel_section_id = str( tool_section.id )
        if tool_shed_repository.status == trans.install_model.ToolShedRepository.installation_status.UNINSTALLED:
            # The repository's status must be updated from 'Uninstalled' to 'New' when initiating reinstall so the repository_installation_updater will function.
            tool_shed_repository = suc.create_or_update_tool_shed_repository( trans.app,
                                                                              tool_shed_repository.name,
                                                                              tool_shed_repository.description,
                                                                              tool_shed_repository.installed_changeset_revision,
                                                                              tool_shed_repository.ctx_rev,
                                                                              repository_clone_url,
                                                                              metadata,
                                                                              trans.install_model.ToolShedRepository.installation_status.NEW,
                                                                              tool_shed_repository.changeset_revision,
                                                                              tool_shed_repository.owner,
                                                                              tool_shed_repository.dist_to_shed )
        ctx_rev = suc.get_ctx_rev( trans.app,
                                   tool_shed_url,
                                   tool_shed_repository.name,
                                   tool_shed_repository.owner,
                                   tool_shed_repository.installed_changeset_revision )
        repo_info_dicts = []
        repo_info_dict = kwd.get( 'repo_info_dict', None )
        if repo_info_dict:
            if isinstance( repo_info_dict, basestring ):
                repo_info_dict = encoding_util.tool_shed_decode( repo_info_dict )
        else:
            # Entering this else block occurs only if the tool_shed_repository does not include any valid tools.
            if install_repository_dependencies:
                repository_dependencies = \
                    repository_dependency_util.get_repository_dependencies_for_installed_tool_shed_repository( trans, tool_shed_repository )
            else:
                repository_dependencies = None
            if metadata:
                tool_dependencies = metadata.get( 'tool_dependencies', None )
            else:
                tool_dependencies = None
            repo_info_dict = repository_util.create_repo_info_dict( trans=trans,
                                                                    repository_clone_url=repository_clone_url,
                                                                    changeset_revision=tool_shed_repository.changeset_revision,
                                                                    ctx_rev=ctx_rev,
                                                                    repository_owner=tool_shed_repository.owner,
                                                                    repository_name=tool_shed_repository.name,
                                                                    repository=None,
                                                                    repository_metadata=None,
                                                                    tool_dependencies=tool_dependencies,
                                                                    repository_dependencies=repository_dependencies )
        if repo_info_dict not in repo_info_dicts:
            repo_info_dicts.append( repo_info_dict )
        # Make sure all tool_shed_repository records exist.
        created_or_updated_tool_shed_repositories, tool_panel_section_keys, repo_info_dicts, filtered_repo_info_dicts = \
            repository_dependency_util.create_repository_dependency_objects( trans=trans,
                                                                             tool_path=tool_path,
                                                                             tool_shed_url=tool_shed_url,
                                                                             repo_info_dicts=repo_info_dicts,
                                                                             install_repository_dependencies=install_repository_dependencies,
                                                                             no_changes_checked=no_changes_checked,
                                                                             tool_panel_section_id=tool_panel_section_id )
        # Default the selected tool panel location for loading tools included in each newly installed required tool shed repository to the location
        # selected for the repository selected for reinstallation.
        for index, tps_key in enumerate( tool_panel_section_keys ):
            if tps_key is None:
                tool_panel_section_keys[ index ] = tool_panel_section_key
        encoded_repository_ids = [ trans.security.encode_id( r.id ) for r in created_or_updated_tool_shed_repositories ]
        new_kwd = dict( includes_tool_dependencies=includes_tool_dependencies,
                        includes_tools=tool_shed_repository.includes_tools,
                        includes_tools_for_display_in_tool_panel=tool_shed_repository.includes_tools_for_display_in_tool_panel,
                        install_tool_dependencies=install_tool_dependencies,
                        repo_info_dicts=filtered_repo_info_dicts,
                        message=message,
                        new_tool_panel_section_label=new_tool_panel_section_label,
                        shed_tool_conf=shed_tool_conf,
                        status=status,
                        tool_panel_section_id=tool_panel_section_id,
                        tool_path=tool_path,
                        tool_panel_section_keys=tool_panel_section_keys,
                        tool_shed_repository_ids=encoded_repository_ids,
                        tool_shed_url=tool_shed_url )
        encoded_kwd = encoding_util.tool_shed_encode( new_kwd )
        tsr_ids = [ r.id  for r in created_or_updated_tool_shed_repositories  ]
        tool_shed_repositories = []
        for tsr_id in tsr_ids:
            tsr = trans.install_model.context.query( trans.install_model.ToolShedRepository ).get( tsr_id )
            tool_shed_repositories.append( tsr )
        clause_list = []
        for tsr_id in tsr_ids:
            clause_list.append( trans.install_model.ToolShedRepository.table.c.id == tsr_id )
        query = trans.install_model.context.current.query( trans.install_model.ToolShedRepository ).filter( or_( *clause_list ) )
        return trans.fill_template( 'admin/tool_shed_repository/initiate_repository_installation.mako',
                                    encoded_kwd=encoded_kwd,
                                    query=query,
                                    tool_shed_repositories=tool_shed_repositories,
                                    initiate_repository_installation_ids=encoded_repository_ids,
                                    reinstalling=True )

    @web.expose
    @web.require_admin
    def repair_repository( self, trans, **kwd ):
        """
        Inspect the repository dependency hierarchy for a specified repository and attempt to make sure they are all properly installed as well as
        each repository's tool dependencies.
        """
        message = kwd.get( 'message', '' )
        status = kwd.get( 'status', 'done' )
        repository_id = kwd.get( 'id', None )
        if not repository_id:
            message = 'Invalid installed tool shed repository id %s received.' % str( repository_id )
            status = 'error'
            return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                              action='browse_repositories',
                                                              message=message,
                                                              status=status ) )
        tool_shed_repository = suc.get_installed_tool_shed_repository( trans, repository_id )
        if kwd.get( 'repair_repository_button', False ):
            encoded_repair_dict = kwd.get( 'repair_dict', None )
            if encoded_repair_dict:
                repair_dict = encoding_util.tool_shed_decode( encoded_repair_dict )
            else:
                repair_dict = None
            if not repair_dict:
                repair_dict = repository_util.get_repair_dict( trans, tool_shed_repository )
            ordered_tsr_ids = repair_dict.get( 'ordered_tsr_ids', [] )
            ordered_repo_info_dicts = repair_dict.get( 'ordered_repo_info_dicts', [] )
            if ordered_tsr_ids and ordered_repo_info_dicts:
                repositories_for_repair = []
                for tsr_id in ordered_tsr_ids:
                    repository = trans.install_model.context.query( trans.install_model.ToolShedRepository ).get( trans.security.decode_id( tsr_id ) )
                    repositories_for_repair.append( repository )
                return self.repair_tool_shed_repositories( trans, repositories_for_repair, ordered_repo_info_dicts )
        tool_shed_repository = suc.get_installed_tool_shed_repository( trans, repository_id )
        repair_dict = repository_util.get_repair_dict( trans, tool_shed_repository )
        encoded_repair_dict = encoding_util.tool_shed_encode( repair_dict )
        ordered_tsr_ids = repair_dict.get( 'ordered_tsr_ids', [] )
        ordered_repo_info_dicts = repair_dict.get( 'ordered_repo_info_dicts', [] )
        return trans.fill_template( 'admin/tool_shed_repository/repair_repository.mako',
                                    repository=tool_shed_repository,
                                    encoded_repair_dict=encoded_repair_dict,
                                    repair_dict=repair_dict,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def repair_tool_shed_repositories( self, trans, tool_shed_repositories, repo_info_dicts, **kwd  ):
        """Repair specified tool shed repositories."""
        # The received lists of tool_shed_repositories and repo_info_dicts are ordered.
        for index, tool_shed_repository in enumerate( tool_shed_repositories ):
            repo_info_dict = repo_info_dicts[ index ]
            repair_dict = repository_util.repair_tool_shed_repository( trans,
                                                                       tool_shed_repository,
                                                                       encoding_util.tool_shed_encode( repo_info_dict ) )
        tsr_ids_for_monitoring = [ trans.security.encode_id( tsr.id ) for tsr in tool_shed_repositories ]
        return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                          action='monitor_repository_installation',
                                                          tool_shed_repository_ids=tsr_ids_for_monitoring ) )

    @web.json
    def repository_installation_status_updates( self, trans, ids=None, status_list=None ):
        # Avoid caching
        trans.response.headers[ 'Pragma' ] = 'no-cache'
        trans.response.headers[ 'Expires' ] = '0'
        # Create new HTML for any ToolShedRepository records whose status that has changed.
        rval = []
        if ids is not None and status_list is not None:
            ids = util.listify( ids )
            status_list = util.listify( status_list )
            for tup in zip( ids, status_list ):
                id, status = tup
                repository = trans.install_model.context.query( trans.install_model.ToolShedRepository ).get( trans.security.decode_id( id ) )
                if repository.status != status:
                    rval.append( dict( id=id,
                                       status=repository.status,
                                       html_status=unicode( trans.fill_template( "admin/tool_shed_repository/repository_installation_status.mako",
                                                                                 repository=repository ),
                                                                                 'utf-8' ) ) )
        return rval

    @web.expose
    @web.require_admin
    def reselect_tool_panel_section( self, trans, **kwd ):
        """
        Select or change the tool panel section to contain the tools included in the tool shed repository being reinstalled.  If there are updates
        available for the repository in the tool shed, the tool_dependencies and repository_dependencies associated with the updated changeset revision
        will have been retrieved from the tool shed and passed in the received kwd.  In this case, the stored tool shed repository metadata from the
        Galaxy database will not be used since it is outdated.
        """
        message = ''
        status = 'done'
        repository_id = kwd.get( 'id', None )
        latest_changeset_revision = kwd.get( 'latest_changeset_revision', None )
        latest_ctx_rev = kwd.get( 'latest_ctx_rev', None )
        tool_shed_repository = suc.get_installed_tool_shed_repository( trans, repository_id )
        repository_clone_url = suc.generate_clone_url_for_installed_repository( trans.app, tool_shed_repository )
        metadata = tool_shed_repository.metadata
        tool_shed_url = suc.get_url_from_tool_shed( trans.app, tool_shed_repository.tool_shed )
        tool_path, relative_install_dir = tool_shed_repository.get_tool_relative_path( trans.app )
        if latest_changeset_revision and latest_ctx_rev:
            # There are updates available in the tool shed for the repository, so use the receieved dependency information which was retrieved from
            # the tool shed.
            encoded_updated_repo_info_dict = kwd.get( 'updated_repo_info_dict', None )
            updated_repo_info_dict = encoding_util.tool_shed_decode( encoded_updated_repo_info_dict )
            readme_files_dict = updated_repo_info_dict.get( 'readme_files_dict', None )
            includes_data_managers = updated_repo_info_dict.get( 'includes_data_managers', False )
            includes_datatypes = updated_repo_info_dict.get( 'includes_datatypes', False )
            includes_tools = updated_repo_info_dict.get( 'includes_tools', False )
            includes_tools_for_display_in_tool_panel = updated_repo_info_dict.get( 'includes_tools_for_display_in_tool_panel', False )
            includes_workflows = updated_repo_info_dict.get( 'includes_workflows', False )
            has_repository_dependencies = updated_repo_info_dict.get( 'has_repository_dependencies', False )
            includes_tool_dependencies = updated_repo_info_dict.get( 'includes_tool_dependencies', False )
            repo_info_dict = updated_repo_info_dict[ 'repo_info_dict' ]
        else:
            # There are no updates available from the tool shed for the repository, so use it's locally stored metadata.
            has_repository_dependencies = False
            includes_data_managers = False
            includes_datatypes = False
            includes_tool_dependencies = False
            includes_tools = False
            includes_tools_for_display_in_tool_panel = False
            includes_workflows = False
            readme_files_dict = None
            tool_dependencies = None
            if metadata:
                if 'data_manager' in metadata:
                    includes_data_managers = True
                if 'datatypes' in metadata:
                    includes_datatypes = True
                if 'tools' in metadata:
                    includes_tools = True
                    # Handle includes_tools_for_display_in_tool_panel.
                    tool_dicts = metadata[ 'tools' ]
                    for tool_dict in tool_dicts:
                        if tool_dict.get( 'add_to_tool_panel', True ):
                            includes_tools_for_display_in_tool_panel = True
                            break
                if 'tool_dependencies' in metadata:
                    includes_tool_dependencies = True
                if 'workflows' in metadata:
                    includes_workflows = True
                # Since we're reinstalling, we need to send a request to the tool shed to get the README files.
                url = suc.url_join( tool_shed_url,
                                    'repository/get_readme_files?name=%s&owner=%s&changeset_revision=%s' % \
                                    ( tool_shed_repository.name, tool_shed_repository.owner, tool_shed_repository.installed_changeset_revision ) )
                raw_text = common_util.tool_shed_get( trans.app, tool_shed_url, url )
                readme_files_dict = json.from_json_string( raw_text )
                tool_dependencies = metadata.get( 'tool_dependencies', None )
            repository_dependencies = repository_dependency_util.get_repository_dependencies_for_installed_tool_shed_repository( trans, tool_shed_repository )
            repo_info_dict = repository_util.create_repo_info_dict( trans=trans,
                                                                    repository_clone_url=repository_clone_url,
                                                                    changeset_revision=tool_shed_repository.changeset_revision,
                                                                    ctx_rev=tool_shed_repository.ctx_rev,
                                                                    repository_owner=tool_shed_repository.owner,
                                                                    repository_name=tool_shed_repository.name,
                                                                    repository=None,
                                                                    repository_metadata=None,
                                                                    tool_dependencies=tool_dependencies,
                                                                    repository_dependencies=repository_dependencies )
        dependencies_for_repository_dict = common_install_util.get_dependencies_for_repository( trans,
                                                                                                tool_shed_url,
                                                                                                repo_info_dict,
                                                                                                includes_tool_dependencies )
        changeset_revision = dependencies_for_repository_dict.get( 'changeset_revision', None )
        has_repository_dependencies = dependencies_for_repository_dict.get( 'has_repository_dependencies', False )
        includes_tool_dependencies = dependencies_for_repository_dict.get( 'includes_tool_dependencies', False )
        includes_tools = dependencies_for_repository_dict.get( 'includes_tools', False )
        includes_tools_for_display_in_tool_panel = dependencies_for_repository_dict.get( 'includes_tools_for_display_in_tool_panel', False )
        installed_repository_dependencies = dependencies_for_repository_dict.get( 'installed_repository_dependencies', None )
        installed_tool_dependencies = dependencies_for_repository_dict.get( 'installed_tool_dependencies', None )
        missing_repository_dependencies = dependencies_for_repository_dict.get( 'missing_repository_dependencies', None )
        missing_tool_dependencies = dependencies_for_repository_dict.get( 'missing_tool_dependencies', None )
        repository_name = dependencies_for_repository_dict.get( 'name', None )
        repository_owner = dependencies_for_repository_dict.get( 'repository_owner', None )
        if installed_repository_dependencies or missing_repository_dependencies:
            has_repository_dependencies = True
        else:
            has_repository_dependencies = False
        if includes_tools_for_display_in_tool_panel:
            # Get the location in the tool panel in which the tools were originally loaded.
            if 'tool_panel_section' in metadata:
                tool_panel_dict = metadata[ 'tool_panel_section' ]
                if tool_panel_dict:
                    if tool_util.panel_entry_per_tool( tool_panel_dict ):
                        # The following forces everything to be loaded into 1 section (or no section) in the tool panel.
                        tool_section_dicts = tool_panel_dict[ tool_panel_dict.keys()[ 0 ] ]
                        tool_section_dict = tool_section_dicts[ 0 ]
                        original_section_name = tool_section_dict[ 'name' ]
                    else:
                        original_section_name = tool_panel_dict[ 'name' ]
                else:
                    original_section_name = ''
            else:
                original_section_name = ''
            tool_panel_section_select_field = tool_util.build_tool_panel_section_select_field( trans )
            no_changes_check_box = CheckboxField( 'no_changes', checked=True )
            if original_section_name:
                message += "The tools contained in your <b>%s</b> repository were last loaded into the tool panel section <b>%s</b>.  " \
                    % ( tool_shed_repository.name, original_section_name )
                message += "Uncheck the <b>No changes</b> check box and select a different tool panel section to load the tools in a "
                message += "different section in the tool panel.  "
                status = 'warning'
            else:
                message += "The tools contained in your <b>%s</b> repository were last loaded into the tool panel outside of any sections.  " % tool_shed_repository.name
                message += "Uncheck the <b>No changes</b> check box and select a tool panel section to load the tools into that section.  "
                status = 'warning'
        else:
            no_changes_check_box = None
            original_section_name = ''
            tool_panel_section_select_field = None
        shed_tool_conf_select_field = tool_util.build_shed_tool_conf_select_field( trans )
        containers_dict = repository_util.populate_containers_dict_for_new_install( trans=trans,
                                                                                    tool_shed_url=tool_shed_url,
                                                                                    tool_path=tool_path,
                                                                                    readme_files_dict=readme_files_dict,
                                                                                    installed_repository_dependencies=installed_repository_dependencies,
                                                                                    missing_repository_dependencies=missing_repository_dependencies,
                                                                                    installed_tool_dependencies=installed_tool_dependencies,
                                                                                    missing_tool_dependencies=missing_tool_dependencies )
        # Since we're reinstalling we'll merge the list of missing repository dependencies into the list of installed repository dependencies since each displayed
        # repository dependency will display a status, whether installed or missing.
        containers_dict = repository_dependency_util.merge_missing_repository_dependencies_to_installed_container( containers_dict )
        # Handle repository dependencies check box.
        install_repository_dependencies_check_box = CheckboxField( 'install_repository_dependencies', checked=True )
        # Handle tool dependencies check box.
        if trans.app.config.tool_dependency_dir is None:
            if includes_tool_dependencies:
                message += "Tool dependencies defined in this repository can be automatically installed if you set the value of your <b>tool_dependency_dir</b> "
                message += "setting in your Galaxy config file (universe_wsgi.ini) and restart your Galaxy server before installing the repository.  "
                status = "warning"
            install_tool_dependencies_check_box_checked = False
        else:
            install_tool_dependencies_check_box_checked = True
        install_tool_dependencies_check_box = CheckboxField( 'install_tool_dependencies', checked=install_tool_dependencies_check_box_checked )
        return trans.fill_template( '/admin/tool_shed_repository/reselect_tool_panel_section.mako',
                                    repository=tool_shed_repository,
                                    no_changes_check_box=no_changes_check_box,
                                    original_section_name=original_section_name,
                                    includes_data_managers=includes_data_managers,
                                    includes_datatypes=includes_datatypes,
                                    includes_tools=includes_tools,
                                    includes_tools_for_display_in_tool_panel=includes_tools_for_display_in_tool_panel,
                                    includes_tool_dependencies=includes_tool_dependencies,
                                    includes_workflows=includes_workflows,
                                    has_repository_dependencies=has_repository_dependencies,
                                    install_repository_dependencies_check_box=install_repository_dependencies_check_box,
                                    install_tool_dependencies_check_box=install_tool_dependencies_check_box,
                                    containers_dict=containers_dict,
                                    tool_panel_section_select_field=tool_panel_section_select_field,
                                    shed_tool_conf_select_field=shed_tool_conf_select_field,
                                    encoded_repo_info_dict=encoding_util.tool_shed_encode( repo_info_dict ),
                                    repo_info_dict=repo_info_dict,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def reset_metadata_on_selected_installed_repositories( self, trans, **kwd ):
        if 'reset_metadata_on_selected_repositories_button' in kwd:
            message, status = metadata_util.reset_metadata_on_selected_repositories( trans, **kwd )
        else:
            message = kwd.get( 'message', ''  )
            status = kwd.get( 'status', 'done' )
        repositories_select_field = suc.build_repository_ids_select_field( trans )
        return trans.fill_template( '/admin/tool_shed_repository/reset_metadata_on_selected_repositories.mako',
                                    repositories_select_field=repositories_select_field,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def reset_repository_metadata( self, trans, id ):
        """Reset all metadata on a single installed tool shed repository."""
        repository = suc.get_installed_tool_shed_repository( trans, id )
        tool_shed_url = suc.get_url_from_tool_shed( trans.app, repository.tool_shed )
        repository_clone_url = suc.generate_clone_url_for_installed_repository( trans.app, repository )
        tool_path, relative_install_dir = repository.get_tool_relative_path( trans.app )
        if relative_install_dir:
            original_metadata_dict = repository.metadata
            metadata_dict, invalid_file_tups = \
                metadata_util.generate_metadata_for_changeset_revision( app=trans.app,
                                                                        repository=repository,
                                                                        changeset_revision=repository.changeset_revision,
                                                                        repository_clone_url=repository_clone_url,
                                                                        shed_config_dict = repository.get_shed_config_dict( trans.app ),
                                                                        relative_install_dir=relative_install_dir,
                                                                        repository_files_dir=None,
                                                                        resetting_all_metadata_on_repository=False,
                                                                        updating_installed_repository=False,
                                                                        persist=False )
            repository.metadata = metadata_dict
            if metadata_dict != original_metadata_dict:
                suc.update_in_shed_tool_config( trans.app, repository )
                trans.install_model.context.add( repository )
                trans.install_model.context.flush()
                message = 'Metadata has been reset on repository <b>%s</b>.' % repository.name
                status = 'done'
            else:
                message = 'Metadata did not need to be reset on repository <b>%s</b>.' % repository.name
                status = 'done'
        else:
            message = 'Error locating installation directory for repository <b>%s</b>.' % repository.name
            status = 'error'
        return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                          action='manage_repository',
                                                          id=id,
                                                          message=message,
                                                          status=status ) )

    @web.expose
    @web.require_admin
    def reset_to_install( self, trans, **kwd ):
        """An error occurred while cloning the repository, so reset everything necessary to enable another attempt."""
        repository = suc.get_installed_tool_shed_repository( trans, kwd[ 'id' ] )
        if kwd.get( 'reset_repository', False ):
            repository_util.set_repository_attributes( trans,
                                                       repository,
                                                       status=trans.install_model.ToolShedRepository.installation_status.NEW,
                                                       error_message=None,
                                                       deleted=False,
                                                       uninstalled=False,
                                                       remove_from_disk=True )
            new_kwd = {}
            new_kwd[ 'message' ] = "You can now attempt to install the repository named <b>%s</b> again." % repository.name
            new_kwd[ 'status' ] = "done"
            return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                              action='browse_repositories',
                                                              **new_kwd ) )
        return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                          action='manage_repository',
                                                          **kwd ) )

    @web.expose
    @web.require_admin
    def set_tool_versions( self, trans, **kwd ):
        """
        Get the tool_versions from the tool shed for each tool in the installed revision of a selected tool shed repository and update the
        metadata for the repository's revision in the Galaxy database.
        """
        repository = suc.get_installed_tool_shed_repository( trans, kwd[ 'id' ] )
        tool_shed_url = suc.get_url_from_tool_shed( trans.app, repository.tool_shed )
        url = suc.url_join( tool_shed_url,
                            'repository/get_tool_versions?name=%s&owner=%s&changeset_revision=%s' % \
                            ( repository.name, repository.owner, repository.changeset_revision ) )
        text = common_util.tool_shed_get( trans.app, tool_shed_url, url )
        if text:
            tool_version_dicts = json.from_json_string( text )
            tool_util.handle_tool_versions( trans.app, tool_version_dicts, repository )
            message = "Tool versions have been set for all included tools."
            status = 'done'
        else:
            message = "Version information for the tools included in the <b>%s</b> repository is missing.  " % repository.name
            message += "Reset all of this reppository's metadata in the tool shed, then set the installed tool versions "
            message ++ "from the installed repository's <b>Repository Actions</b> menu.  "
            status = 'error'
        shed_tool_conf, tool_path, relative_install_dir = suc.get_tool_panel_config_tool_path_install_dir( trans.app, repository )
        repo_files_dir = os.path.abspath( os.path.join( relative_install_dir, repository.name ) )
        containers_dict = metadata_util.populate_containers_dict_from_repository_metadata( trans=trans,
                                                                                           tool_shed_url=tool_shed_url,
                                                                                           tool_path=tool_path,
                                                                                           repository=repository,
                                                                                           reinstalling=False,
                                                                                           required_repo_info_dicts=None )
        return trans.fill_template( '/admin/tool_shed_repository/manage_repository.mako',
                                    repository=repository,
                                    description=repository.description,
                                    repo_files_dir=repo_files_dir,
                                    containers_dict=containers_dict,
                                    message=message,
                                    status=status )

    @web.json
    def tool_dependency_status_updates( self, trans, ids=None, status_list=None ):
        # Avoid caching
        trans.response.headers[ 'Pragma' ] = 'no-cache'
        trans.response.headers[ 'Expires' ] = '0'
        # Create new HTML for any ToolDependency records whose status that has changed.
        rval = []
        if ids is not None and status_list is not None:
            ids = util.listify( ids )
            status_list = util.listify( status_list )
            for tup in zip( ids, status_list ):
                id, status = tup
                tool_dependency = trans.install_model.context.query( trans.install_model.ToolDependency ).get( trans.security.decode_id( id ) )
                if tool_dependency.status != status:
                    rval.append( dict( id=id,
                                       status=tool_dependency.status,
                                       html_status=unicode( trans.fill_template( "admin/tool_shed_repository/tool_dependency_installation_status.mako",
                                                                                 tool_dependency=tool_dependency ),
                                                                                 'utf-8' ) ) )
        return rval

    @web.expose
    @web.require_admin
    def uninstall_tool_dependencies( self, trans, **kwd ):
        message = kwd.get( 'message', ''  )
        status = kwd.get( 'status', 'done' )
        tool_dependency_ids = tool_dependency_util.get_tool_dependency_ids( as_string=False, **kwd )
        if not tool_dependency_ids:
            tool_dependency_ids = util.listify( kwd.get( 'id', None ) )
        tool_dependencies = []
        for tool_dependency_id in tool_dependency_ids:
            tool_dependency = tool_dependency_util.get_tool_dependency( trans, tool_dependency_id )
            tool_dependencies.append( tool_dependency )
        tool_shed_repository = tool_dependencies[ 0 ].tool_shed_repository
        if kwd.get( 'uninstall_tool_dependencies_button', False ):
            errors = False
            # Filter tool dependencies to only those that are installed but in an error state.
            tool_dependencies_for_uninstallation = []
            for tool_dependency in tool_dependencies:
                if tool_dependency.can_uninstall:
                    tool_dependencies_for_uninstallation.append( tool_dependency )
            for tool_dependency in tool_dependencies_for_uninstallation:
                uninstalled, error_message = tool_dependency_util.remove_tool_dependency( trans.app, tool_dependency )
                if error_message:
                    errors = True
                    message = '%s  %s' % ( message, error_message )
            if errors:
                message = "Error attempting to uninstall tool dependencies: %s" % message
                status = 'error'
            else:
                message = "These tool dependencies have been uninstalled: %s" % ','.join( td.name for td in tool_dependencies_for_uninstallation )
            td_ids = [ trans.security.encode_id( td.id ) for td in tool_shed_repository.tool_dependencies ]
            return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                              action='manage_repository_tool_dependencies',
                                                              tool_dependency_ids=td_ids,
                                                              status=status,
                                                              message=message ) )
        return trans.fill_template( '/admin/tool_shed_repository/uninstall_tool_dependencies.mako',
                                    repository=tool_shed_repository,
                                    tool_dependency_ids=tool_dependency_ids,
                                    tool_dependencies=tool_dependencies,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def update_to_changeset_revision( self, trans, **kwd ):
        """Update a cloned repository to the latest revision possible."""
        message = kwd.get( 'message', ''  )
        status = kwd.get( 'status', 'done' )
        tool_shed_url = kwd[ 'tool_shed_url' ]
        name = kwd.get( 'name', None )
        owner = kwd.get( 'owner', None )
        changeset_revision = kwd.get( 'changeset_revision', None )
        latest_changeset_revision = kwd.get( 'latest_changeset_revision', None )
        latest_ctx_rev = kwd.get( 'latest_ctx_rev', None )
        repository = suc.get_tool_shed_repository_by_shed_name_owner_changeset_revision( trans.app,
                                                                                         tool_shed_url,
                                                                                         name,
                                                                                         owner,
                                                                                         changeset_revision )
        if changeset_revision and latest_changeset_revision and latest_ctx_rev:
            if changeset_revision == latest_changeset_revision:
                message = "The installed repository named '%s' is current, there are no updates available.  " % name
            else:
                shed_tool_conf, tool_path, relative_install_dir = suc.get_tool_panel_config_tool_path_install_dir( trans.app, repository )
                if relative_install_dir:
                    if tool_path:
                        repo_files_dir = os.path.abspath( os.path.join( tool_path, relative_install_dir, name ) )
                    else:
                        repo_files_dir = os.path.abspath( os.path.join( relative_install_dir, name ) )
                    repo = hg.repository( suc.get_configured_ui(), path=repo_files_dir )
                    repository_clone_url = os.path.join( tool_shed_url, 'repos', owner, name )
                    repository_util.pull_repository( repo, repository_clone_url, latest_ctx_rev )
                    suc.update_repository( repo, latest_ctx_rev )
                    tool_shed = suc.clean_tool_shed_url( tool_shed_url )
                    # Remove old Data Manager entries
                    if repository.includes_data_managers:
                        data_manager_util.remove_from_data_manager( trans.app, repository )
                    # Update the repository metadata.
                    metadata_dict, invalid_file_tups = \
                        metadata_util.generate_metadata_for_changeset_revision( app=trans.app,
                                                                                repository=repository,
                                                                                changeset_revision=latest_changeset_revision,
                                                                                repository_clone_url=repository_clone_url,
                                                                                shed_config_dict=repository.get_shed_config_dict( trans.app ),
                                                                                relative_install_dir=relative_install_dir,
                                                                                repository_files_dir=None,
                                                                                resetting_all_metadata_on_repository=False,
                                                                                updating_installed_repository=True,
                                                                                persist=True )
                    repository.metadata = metadata_dict
                    # Update the repository.changeset_revision column in the database.
                    repository.changeset_revision = latest_changeset_revision
                    repository.ctx_rev = latest_ctx_rev
                    # Update the repository.tool_shed_status column in the database.
                    tool_shed_status_dict = suc.get_tool_shed_status_for_installed_repository( trans.app, repository )
                    if tool_shed_status_dict:
                        repository.tool_shed_status = tool_shed_status_dict
                    else:
                        repository.tool_shed_status = None
                    trans.install_model.context.add( repository )
                    trans.install_model.context.flush()
                    if 'tools' in metadata_dict:
                        tool_panel_dict = metadata_dict.get( 'tool_panel_section', None )
                        if tool_panel_dict is None:
                            tool_panel_dict = suc.generate_tool_panel_dict_from_shed_tool_conf_entries( trans.app, repository )
                        repository_tools_tups = suc.get_repository_tools_tups( trans.app, metadata_dict )
                        tool_util.add_to_tool_panel( app=trans.app,
                                                     repository_name=repository.name,
                                                     repository_clone_url=repository_clone_url,
                                                     changeset_revision=repository.installed_changeset_revision,
                                                     repository_tools_tups=repository_tools_tups,
                                                     owner=repository.owner,
                                                     shed_tool_conf=shed_tool_conf,
                                                     tool_panel_dict=tool_panel_dict,
                                                     new_install=False )
                        # Add new Data Manager entries
                        if 'data_manager' in metadata_dict:
                            new_data_managers = data_manager_util.install_data_managers( trans.app,
                                                                                         trans.app.config.shed_data_manager_config_file,
                                                                                         metadata_dict,
                                                                                         repository.get_shed_config_dict( trans.app ),
                                                                                         os.path.join( relative_install_dir, name ),
                                                                                         repository,
                                                                                         repository_tools_tups )
                    # Create tool_dependency records if necessary.
                    if 'tool_dependencies' in metadata_dict:
                        tool_dependencies = tool_dependency_util.create_tool_dependency_objects( trans.app,
                                                                                                 repository,
                                                                                                 relative_install_dir,
                                                                                                 set_status=False )
                    message = "The installed repository named '%s' has been updated to change set revision '%s'.  " % \
                        ( name, latest_changeset_revision )
                    # See if any tool dependencies can be installed.
                    shed_tool_conf, tool_path, relative_install_dir = \
                        suc.get_tool_panel_config_tool_path_install_dir( trans.app, repository )
                    if repository.missing_tool_dependencies:
                        message += "Click the name of one of the missing tool dependencies listed below to install tool dependencies."
                else:
                    message = "The directory containing the installed repository named '%s' cannot be found.  " % name
                    status = 'error'
        else:
            message = "The latest changeset revision could not be retrieved for the installed repository named '%s'.  " % name
            status = 'error'
        return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                          action='manage_repository',
                                                          id=trans.security.encode_id( repository.id ),
                                                          message=message,
                                                          status=status ) )

    @web.expose
    @web.require_admin
    def update_tool_shed_status_for_installed_repository( self, trans, all_installed_repositories=False, **kwd ):
        message = kwd.get( 'message', ''  )
        status = kwd.get( 'status', 'done' )
        if all_installed_repositories:
            success_count = 0
            repository_names_not_updated = []
            updated_count = 0
            for repository in trans.install_model.context.query( trans.install_model.ToolShedRepository ) \
                                              .filter( trans.install_model.ToolShedRepository.table.c.deleted == False ):
                ok, updated = suc.check_or_update_tool_shed_status_for_installed_repository( trans, repository )
                if ok:
                    success_count += 1
                else:
                    repository_names_not_updated.append( '<b>%s</b>' % str( repository.name ) )
                if updated:
                    updated_count += 1
            message = "Checked the status in the tool shed for %d repositories.  " % success_count
            message += "Updated the tool shed status for %d repositories.  " % updated_count
            if repository_names_not_updated:
                message += "Unable to retrieve status from the tool shed for the following repositories:\n"
                message += ", ".join( repository_names_not_updated )
        else:
            repository_id = kwd.get( 'id', None )
            repository = suc.get_tool_shed_repository_by_id( trans, repository_id )
            ok, updated = suc.check_or_update_tool_shed_status_for_installed_repository( trans, repository )
            if ok:
                if updated:
                    message = "The tool shed status for repository <b>%s</b> has been updated." % str( repository.name )
                else:
                    message = "The status has not changed in the tool shed for repository <b>%s</b>." % str( repository.name )
            else:
                message = "Unable to retrieve status from the tool shed for repository <b>%s</b>." % str( repository.name )
                status = 'error'
        return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                          action='browse_repositories',
                                                          message=message,
                                                          status=status ) )

    @web.expose
    @web.require_admin
    def view_tool_metadata( self, trans, repository_id, tool_id, **kwd ):
        message = kwd.get( 'message', ''  )
        status = kwd.get( 'status', 'done' )
        repository = suc.get_installed_tool_shed_repository( trans, repository_id )
        repository_metadata = repository.metadata
        shed_config_dict = repository.get_shed_config_dict( trans.app )
        tool_metadata = {}
        tool_lineage = []
        tool = None
        if 'tools' in repository_metadata:
            for tool_metadata_dict in repository_metadata[ 'tools' ]:
                if tool_metadata_dict[ 'id' ] == tool_id:
                    tool_metadata = tool_metadata_dict
                    tool_config = tool_metadata[ 'tool_config' ]
                    if shed_config_dict and shed_config_dict.get( 'tool_path' ):
                        tool_config = os.path.join( shed_config_dict.get( 'tool_path' ), tool_config )
                    tool = trans.app.toolbox.load_tool( os.path.abspath( tool_config ), guid=tool_metadata[ 'guid' ] )
                    if tool:
                        tool_lineage = self.get_versions_of_tool( trans.app, tool.id )
                    break
        return trans.fill_template( "/admin/tool_shed_repository/view_tool_metadata.mako",
                                    repository=repository,
                                    repository_metadata=repository_metadata,
                                    tool=tool,
                                    tool_metadata=tool_metadata,
                                    tool_lineage=tool_lineage,
                                    message=message,
                                    status=status )

    @web.expose
    @web.require_admin
    def view_workflow( self, trans, workflow_name=None, repository_id=None, **kwd ):
        """Retrieve necessary information about a workflow from the database so that it can be displayed in an svg image."""
        message = kwd.get( 'message', ''  )
        status = kwd.get( 'status', 'done' )
        if workflow_name:
            workflow_name = encoding_util.tool_shed_decode( workflow_name )
        repository = suc.get_tool_shed_repository_by_id( trans, repository_id )
        changeset_revision = repository.changeset_revision
        metadata = repository.metadata
        return trans.fill_template( "/admin/tool_shed_repository/view_workflow.mako",
                                    repository=repository,
                                    changeset_revision=changeset_revision,
                                    repository_id=repository_id,
                                    workflow_name=workflow_name,
                                    metadata=metadata,
                                    message=message,
                                    status=status )
