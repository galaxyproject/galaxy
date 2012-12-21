import urllib2, tempfile
from admin import *
from galaxy.util.json import from_json_string, to_json_string
import galaxy.util.shed_util as shed_util
import galaxy.util.shed_util_common as suc
from galaxy.tool_shed import encoding_util
from galaxy.webapps.community.util import container_util
from galaxy import eggs, tools

eggs.require( 'mercurial' )
from mercurial import hg, ui, commands

log = logging.getLogger( __name__ )

class InstalledRepositoryGrid( grids.Grid ):
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_shed_repository ):
            if tool_shed_repository.update_available:
                return '<div class="count-box state-color-running">%s</div>' % tool_shed_repository.name
            return tool_shed_repository.name
    class DescriptionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_shed_repository ):
            return tool_shed_repository.description
    class OwnerColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_shed_repository ):
            return tool_shed_repository.owner
    class RevisionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_shed_repository ):
            return tool_shed_repository.changeset_revision
    class StatusColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_shed_repository ):
            status_label = tool_shed_repository.status
            if tool_shed_repository.status in [ trans.model.ToolShedRepository.installation_status.CLONING,
                                               trans.model.ToolShedRepository.installation_status.SETTING_TOOL_VERSIONS,
                                               trans.model.ToolShedRepository.installation_status.INSTALLING_TOOL_DEPENDENCIES,
                                               trans.model.ToolShedRepository.installation_status.LOADING_PROPRIETARY_DATATYPES ]:
                bgcolor = trans.model.ToolShedRepository.states.INSTALLING
            elif tool_shed_repository.status in [ trans.model.ToolShedRepository.installation_status.NEW,
                                                 trans.model.ToolShedRepository.installation_status.UNINSTALLED ]:
                bgcolor = trans.model.ToolShedRepository.states.UNINSTALLED
            elif tool_shed_repository.status in [ trans.model.ToolShedRepository.installation_status.ERROR ]:
                bgcolor = trans.model.ToolShedRepository.states.ERROR
            elif tool_shed_repository.status in [ trans.model.ToolShedRepository.installation_status.DEACTIVATED ]:
                bgcolor = trans.model.ToolShedRepository.states.WARNING
            elif tool_shed_repository.status in [ trans.model.ToolShedRepository.installation_status.INSTALLED ]:
                if tool_shed_repository.missing_tool_dependencies:
                    bgcolor = trans.model.ToolShedRepository.states.WARNING
                    status_label = '%s, missing dependencies' % status_label
                else:
                    bgcolor = trans.model.ToolShedRepository.states.OK
            else:
                bgcolor = trans.model.ToolShedRepository.states.ERROR
            rval = '<div class="count-box state-color-%s">%s</div>' % ( bgcolor, status_label )
            return rval
    class ToolShedColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_shed_repository ):
            return tool_shed_repository.tool_shed
    class DeletedColumn( grids.DeletedColumn ):
            def get_accepted_filters( self ):
                """ Returns a list of accepted filters for this column. """
                accepted_filter_labels_and_vals = { "Active" : "False", "Deactivated or uninstalled" : "True", "All": "All" }
                accepted_filters = []
                for label, val in accepted_filter_labels_and_vals.items():
                   args = { self.key: val }
                   accepted_filters.append( grids.GridColumnFilter( label, args) )
                return accepted_filters
    # Grid definition
    title = "Installed tool shed repositories"
    model_class = model.ToolShedRepository
    template='/admin/tool_shed_repository/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    key="name",
                    link=( lambda item: iff( item.status in [ model.ToolShedRepository.installation_status.CLONING ],
                                             None,
                                             dict( operation="manage_repository", id=item.id ) ) ),
                    attach_popup=True ),
        DescriptionColumn( "Description" ),
        OwnerColumn( "Owner" ),
        RevisionColumn( "Revision" ),
        StatusColumn( "Installation Status",
                      filterable="advanced" ),
        ToolShedColumn( "Tool shed" ),
        # Columns that are valid for filtering but are not visible.
        DeletedColumn( "Status",
                       key="deleted",
                       visible=False,
                       filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name", 
                                                cols_to_filter=[ columns[0] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    global_actions = []
    operations = [ grids.GridOperation( "Get updates",
                                        allow_multiple=False,
                                        condition=( lambda item: not item.deleted and item.status not in \
                                            [ model.ToolShedRepository.installation_status.ERROR, model.ToolShedRepository.installation_status.NEW ] ),
                                        async_compatible=False,
                                        url_args=dict( controller='admin_toolshed', action='browse_repositories', operation='get updates' ) ),
                   grids.GridOperation( "Install",
                                        allow_multiple=False,
                                        condition=( lambda item: not item.deleted and item.status == model.ToolShedRepository.installation_status.NEW ),
                                        async_compatible=False,
                                        url_args=dict( controller='admin_toolshed', action='manage_repository', operation='install' ) ),
                   grids.GridOperation( "Deactivate or uninstall",
                                        allow_multiple=False,
                                        condition=( lambda item: not item.deleted and item.status not in \
                                            [ model.ToolShedRepository.installation_status.ERROR, model.ToolShedRepository.installation_status.NEW ] ),
                                        async_compatible=False,
                                        url_args=dict( controller='admin_toolshed', action='browse_repositories', operation='deactivate or uninstall' ) ),
                   grids.GridOperation( "Reset to install",
                                        allow_multiple=False,
                                        condition=( lambda item: ( item.status == model.ToolShedRepository.installation_status.ERROR ) ),
                                        async_compatible=False,
                                        url_args=dict( controller='admin_toolshed', action='browse_repositories', operation='reset to install' ) ),
                   grids.GridOperation( "Activate or reinstall",
                                        allow_multiple=False,
                                        condition=( lambda item: item.deleted ),
                                        async_compatible=False,
                                        url_args=dict( controller='admin_toolshed', action='browse_repositories', operation='activate or reinstall' ) ) ]
    standard_filters = []
    default_filter = dict( deleted="False" )
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( self.model_class )

class RepositoryInstallationGrid( grids.Grid ):
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_shed_repository ):
            return tool_shed_repository.name
    class DescriptionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_shed_repository ):
            return tool_shed_repository.description
    class OwnerColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_shed_repository ):
            return tool_shed_repository.owner
    class RevisionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_shed_repository ):
            return tool_shed_repository.changeset_revision
    class StatusColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_shed_repository ):
            status_label = tool_shed_repository.status
            if tool_shed_repository.status in [ trans.model.ToolShedRepository.installation_status.CLONING,
                                                trans.model.ToolShedRepository.installation_status.SETTING_TOOL_VERSIONS,
                                                trans.model.ToolShedRepository.installation_status.INSTALLING_TOOL_DEPENDENCIES,
                                                trans.model.ToolShedRepository.installation_status.LOADING_PROPRIETARY_DATATYPES ]:
                bgcolor = trans.model.ToolShedRepository.states.INSTALLING
            elif tool_shed_repository.status in [ trans.model.ToolShedRepository.installation_status.NEW,
                                                 trans.model.ToolShedRepository.installation_status.UNINSTALLED ]:
                bgcolor = trans.model.ToolShedRepository.states.UNINSTALLED
            elif tool_shed_repository.status in [ trans.model.ToolShedRepository.installation_status.ERROR ]:
                bgcolor = trans.model.ToolShedRepository.states.ERROR
            elif tool_shed_repository.status in [ trans.model.ToolShedRepository.installation_status.DEACTIVATED ]:
                bgcolor = trans.model.ToolShedRepository.states.WARNING
            elif tool_shed_repository.status in [ trans.model.ToolShedRepository.installation_status.INSTALLED ]:
                if tool_shed_repository.missing_tool_dependencies:
                    bgcolor = trans.model.ToolShedRepository.states.WARNING
                    status_label = '%s, missing dependencies' % status_label
                else:
                    bgcolor = trans.model.ToolShedRepository.states.OK
            else:
                bgcolor = trans.model.ToolShedRepository.states.ERROR
            rval = '<div class="count-box state-color-%s" id="RepositoryStatus-%s">%s</div>' % \
                ( bgcolor, trans.security.encode_id( tool_shed_repository.id ), status_label )
            return rval

    title = "Monitor installing tool shed repositories"
    template = "admin/tool_shed_repository/repository_installation_grid.mako"
    model_class = model.ToolShedRepository
    default_sort_key = "-create_time"
    num_rows_per_page = 50
    preserve_state = True
    use_paging = False
    columns = [
        NameColumn( "Name",
                    link=( lambda item: iff( item.status in \
                                             [ model.ToolShedRepository.installation_status.NEW,
                                               model.ToolShedRepository.installation_status.CLONING,
                                               model.ToolShedRepository.installation_status.SETTING_TOOL_VERSIONS,
                                               model.ToolShedRepository.installation_status.INSTALLING_TOOL_DEPENDENCIES,
                                               model.ToolShedRepository.installation_status.LOADING_PROPRIETARY_DATATYPES,
                                               model.ToolShedRepository.installation_status.UNINSTALLED ], \
                                             None, dict( action="manage_repository", id=item.id ) ) ),
                    filterable="advanced" ),
        DescriptionColumn( "Description",
                    filterable="advanced" ),
        OwnerColumn( "Owner",
                    filterable="advanced" ),
        RevisionColumn( "Revision",
                    filterable="advanced" ),
        StatusColumn( "Installation Status",
                      filterable="advanced",
                      label_id_prefix="RepositoryStatus-" )
    ]
    operations = []
    def build_initial_query( self, trans, **kwd ):
        clause_list = []
        tool_shed_repository_ids = util.listify( kwd.get( 'tool_shed_repository_ids', None ) )
        if tool_shed_repository_ids:
            for tool_shed_repository_id in tool_shed_repository_ids:
                clause_list.append( self.model_class.table.c.id == trans.security.decode_id( tool_shed_repository_id ) )
            if clause_list:
                return trans.sa_session.query( self.model_class ) \
                                       .filter( or_( *clause_list ) )
        for tool_shed_repository in trans.sa_session.query( self.model_class ) \
                                                    .filter( self.model_class.table.c.deleted == False ):
            if tool_shed_repository.status in [ trans.model.ToolShedRepository.installation_status.NEW,
                                               trans.model.ToolShedRepository.installation_status.CLONING,
                                               trans.model.ToolShedRepository.installation_status.SETTING_TOOL_VERSIONS,
                                               trans.model.ToolShedRepository.installation_status.INSTALLING_TOOL_DEPENDENCIES,
                                               trans.model.ToolShedRepository.installation_status.LOADING_PROPRIETARY_DATATYPES ]:
                clause_list.append( self.model_class.table.c.id == trans.security.decode_id( tool_shed_repository.id ) )
        if clause_list:
            return trans.sa_session.query( self.model_class ) \
                           .filter( or_( *clause_list ) )
        return trans.sa_session.query( self.model_class ) \
                               .filter( self.model_class.table.c.status == trans.model.ToolShedRepository.installation_status.NEW )
    def apply_query_filter( self, trans, query, **kwd ):
        tool_shed_repository_id = kwd.get( 'tool_shed_repository_id', None )
        if tool_shed_repository_id:
            return query.filter_by( tool_shed_repository_id=trans.security.decode_id( tool_shed_repository_id ) )
        return query

class ToolDependencyGrid( grids.Grid ):
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_dependency ):
            return tool_dependency.name
    class VersionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_dependency ):
            return tool_dependency.version
    class TypeColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_dependency ):
            return tool_dependency.type
    class StatusColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_dependency ):
            if tool_dependency.status in [ trans.model.ToolDependency.installation_status.INSTALLING ]:
                bgcolor = trans.model.ToolDependency.states.INSTALLING
            elif tool_dependency.status in [ trans.model.ToolDependency.installation_status.NEVER_INSTALLED,
                                             trans.model.ToolDependency.installation_status.UNINSTALLED ]:
                bgcolor = trans.model.ToolDependency.states.UNINSTALLED
            elif tool_dependency.status in [ trans.model.ToolDependency.installation_status.ERROR ]:
                bgcolor = trans.model.ToolDependency.states.ERROR
            elif tool_dependency.status in [ trans.model.ToolDependency.installation_status.INSTALLED ]:
                bgcolor = trans.model.ToolDependency.states.OK
            rval = '<div class="count-box state-color-%s" id="ToolDependencyStatus-%s">%s</div>' % \
                ( bgcolor, trans.security.encode_id( tool_dependency.id ), tool_dependency.status )
            return rval

    title = "Tool Dependencies"
    template = "admin/tool_shed_repository/tool_dependencies_grid.mako"
    model_class = model.ToolDependency
    default_sort_key = "-create_time"
    num_rows_per_page = 50
    preserve_state = True
    use_paging = False
    columns = [
        NameColumn( "Name",
                    link=( lambda item: iff( item.status in \
                                             [ model.ToolDependency.installation_status.NEVER_INSTALLED,
                                               model.ToolDependency.installation_status.INSTALLING,
                                               model.ToolDependency.installation_status.UNINSTALLED ], \
                                             None, dict( action="manage_tool_dependencies", operation='browse', id=item.id ) ) ),
                    filterable="advanced" ),
        VersionColumn( "Version",
                       filterable="advanced" ),
        TypeColumn( "Type",
                    filterable="advanced" ),
        StatusColumn( "Installation Status",
                      filterable="advanced" ),
    ]
    operations = [
        grids.GridOperation( "Install",
                             allow_multiple=True,
                             condition=( lambda item: item.status in [ model.ToolDependency.installation_status.NEVER_INSTALLED,
                                                                       model.ToolDependency.installation_status.UNINSTALLED ] ) ),
        grids.GridOperation( "Uninstall",
                             allow_multiple=True,
                             allow_popup=False,
                             condition=( lambda item: item.status in [ model.ToolDependency.installation_status.INSTALLED,
                                                                       model.ToolDependency.installation_status.ERROR ] ) )
    ]
    def build_initial_query( self, trans, **kwd ):
        tool_dependency_ids = shed_util.get_tool_dependency_ids( as_string=False, **kwd )
        if tool_dependency_ids:
            clause_list = []
            for tool_dependency_id in tool_dependency_ids:
                clause_list.append( self.model_class.table.c.id == trans.security.decode_id( tool_dependency_id ) )
            return trans.sa_session.query( self.model_class ) \
                                   .filter( or_( *clause_list ) )
        return trans.sa_session.query( self.model_class )
    def apply_query_filter( self, trans, query, **kwd ):
        tool_dependency_id = kwd.get( 'tool_dependency_id', None )
        if tool_dependency_id:
            return query.filter_by( tool_dependency_id=trans.security.decode_id( tool_dependency_id ) )
        return query

class AdminToolshed( AdminGalaxy ):

    installed_repository_grid = InstalledRepositoryGrid()
    repository_installation_grid = RepositoryInstallationGrid()
    tool_dependency_grid = ToolDependencyGrid()

    @web.expose
    @web.require_admin
    def activate_repository( self, trans, **kwd ):
        """Activate a repository that was deactivated but not uninstalled."""
        repository = suc.get_installed_tool_shed_repository( trans, kwd[ 'id' ] )
        shed_tool_conf, tool_path, relative_install_dir = suc.get_tool_panel_config_tool_path_install_dir( trans.app, repository )
        repository_clone_url = suc.generate_clone_url_for_installed_repository( trans.app, repository )
        repository.deleted = False
        repository.status = trans.model.ToolShedRepository.installation_status.INSTALLED
        if repository.includes_tools:
            metadata = repository.metadata
            try:
                repository_tools_tups = suc.get_repository_tools_tups( trans.app, metadata )
            except Exception, e:
                error = "Error activating repository %s: %s" % ( repository.name, str( e ) )
                log.debug( error )
                return trans.show_error_message( '%s.<br/>You may be able to resolve this by uninstalling and then reinstalling the repository.  Click <a href="%s">here</a> to uninstall the repository.' 
                                                 % ( error, web.url_for( controller='admin_toolshed', action='deactivate_or_uninstall_repository', id=trans.security.encode_id( repository.id ) ) ) )
            # Reload tools into the appropriate tool panel section.
            tool_panel_dict = repository.metadata[ 'tool_panel_section' ]
            shed_util.add_to_tool_panel( trans.app,
                                         repository.name,
                                         repository_clone_url,
                                         repository.installed_changeset_revision,
                                         repository_tools_tups,
                                         repository.owner,
                                         shed_tool_conf,
                                         tool_panel_dict,
                                         new_install=False )
        trans.sa_session.add( repository )
        trans.sa_session.flush()
        if repository.includes_datatypes:
            repository_install_dir = os.path.abspath ( relative_install_dir )
            # Deactivate proprietary datatypes.
            installed_repository_dict = shed_util.load_installed_datatypes( trans.app, repository, repository_install_dir, deactivate=False )
            if installed_repository_dict and 'converter_path' in installed_repository_dict:
                shed_util.load_installed_datatype_converters( trans.app, installed_repository_dict, deactivate=False )
            if installed_repository_dict and 'display_path' in installed_repository_dict:
                shed_util.load_installed_display_applications( trans.app, installed_repository_dict, deactivate=False )
        message = 'The <b>%s</b> repository has been activated.' % repository.name
        status = 'done'
        return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                          action='browse_repositories',
                                                          message=message,
                                                          status=status ) )
    @web.expose
    @web.require_admin
    def browse_repository( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
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
            if operation == "reset to install":
                kwd[ 'reset_repository' ] = True
                return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                  action='reset_to_install',
                                                                  **kwd ) )
            if operation == "activate or reinstall":
                repository = suc.get_installed_tool_shed_repository( trans, kwd[ 'id' ] )
                if repository.uninstalled:
                    if repository.includes_tools:
                        # Only allow selecting a different section in the tool panel if the repository was uninstalled.
                        return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                          action='reselect_tool_panel_section',
                                                                          **kwd ) )
                    else:
                        return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                          action='reinstall_repository',
                                                                          **kwd ) )
                else:
                    return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                      action='activate_repository',
                                                                      **kwd ) )
            if operation == "deactivate or uninstall":
                return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                  action='deactivate_or_uninstall_repository',
                                                                  **kwd ) )
        if 'message' not in kwd or not kwd[ 'message' ]:
            kwd[ 'message' ] = 'Names of repositories for which updates are available are highlighted in yellow.'
        return self.installed_repository_grid( trans, **kwd )
    @web.expose
    @web.require_admin
    def browse_tool_dependency( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        tool_dependency = shed_util.get_tool_dependency( trans, kwd[ 'id' ] )
        if tool_dependency.in_error_state:
            message = "This tool dependency is not installed correctly (see the <b>Tool dependency installation error</b> below).  "
            message += "Choose <b>Uninstall this tool dependency</b> from the <b>Repository Actions</b> menu, correct problems "
            message += "if necessary, and try installing the dependency again."
            status = "error"
        tool_shed_repository = tool_dependency.tool_shed_repository
        tool_dependency.name = suc.to_safe_string( tool_dependency.name )
        tool_dependency.version = suc.to_safe_string( tool_dependency.version )
        tool_dependency.type = suc.to_safe_string( tool_dependency.type )
        tool_dependency.status = suc.to_safe_string( tool_dependency.status )
        tool_dependency.error_message = suc.to_safe_string( tool_dependency.error_message )
        return trans.fill_template( '/admin/tool_shed_repository/browse_tool_dependency.mako',
                                    repository=tool_shed_repository,
                                    tool_dependency=tool_dependency,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def browse_tool_shed( self, trans, **kwd ):
        tool_shed_url = kwd[ 'tool_shed_url' ]
        galaxy_url = url_for( '/', qualified=True )
        url = suc.url_join( tool_shed_url, 'repository/browse_valid_categories?galaxy_url=%s' % ( galaxy_url ) )
        return trans.response.send_redirect( url )
    @web.expose
    @web.require_admin
    def browse_tool_sheds( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        return trans.fill_template( '/webapps/galaxy/admin/tool_sheds.mako',
                                    message=message,
                                    status='error' )
    @web.expose
    @web.require_admin
    def check_for_updates( self, trans, **kwd ):
        # Send a request to the relevant tool shed to see if there are any updates.
        repository = suc.get_installed_tool_shed_repository( trans, kwd[ 'id' ] )
        tool_shed_url = suc.get_url_from_repository_tool_shed( trans.app, repository )
        url = suc.url_join( tool_shed_url,
                            'repository/check_for_updates?galaxy_url=%s&name=%s&owner=%s&changeset_revision=%s' % \
                            ( url_for( '/', qualified=True ), repository.name, repository.owner, repository.changeset_revision ) )
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
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        remove_from_disk = params.get( 'remove_from_disk', '' )
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
        if params.get( 'deactivate_or_uninstall_repository_button', False ):
            if tool_shed_repository.includes_tools:
                # Handle tool panel alterations.
                shed_util.remove_from_tool_panel( trans, tool_shed_repository, shed_tool_conf, uninstall=remove_from_disk_checked )
            if tool_shed_repository.includes_datatypes:
                # Deactivate proprietary datatypes.
                installed_repository_dict = shed_util.load_installed_datatypes( trans.app, tool_shed_repository, repository_install_dir, deactivate=True )
                if installed_repository_dict and 'converter_path' in installed_repository_dict:
                    shed_util.load_installed_datatype_converters( trans.app, installed_repository_dict, deactivate=True )
                if installed_repository_dict and 'display_path' in installed_repository_dict:
                    shed_util.load_installed_display_applications( trans.app, installed_repository_dict, deactivate=True )
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
                    # Remove all installed tool dependencies.
                    for tool_dependency in tool_shed_repository.installed_tool_dependencies:
                        uninstalled, error_message = shed_util.remove_tool_dependency( trans, tool_dependency )
                        if error_message:
                            errors = '%s  %s' % ( errors, error_message )
            tool_shed_repository.deleted = True
            if remove_from_disk_checked:
                tool_shed_repository.status = trans.model.ToolShedRepository.installation_status.UNINSTALLED
                tool_shed_repository.error_message = None
            else:
                tool_shed_repository.status = trans.model.ToolShedRepository.installation_status.DEACTIVATED
            trans.sa_session.add( tool_shed_repository )
            trans.sa_session.flush()
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
    @web.require_admin
    def find_tools_in_tool_shed( self, trans, **kwd ):
        tool_shed_url = kwd[ 'tool_shed_url' ]
        galaxy_url = url_for( '/', qualified=True )
        url = suc.url_join( tool_shed_url, 'repository/find_tools?galaxy_url=%s' % galaxy_url )
        return trans.response.send_redirect( url )
    @web.expose
    @web.require_admin
    def find_workflows_in_tool_shed( self, trans, **kwd ):
        tool_shed_url = kwd[ 'tool_shed_url' ]
        galaxy_url = url_for( '/', qualified=True )
        url = suc.url_join( tool_shed_url, 'repository/find_workflows?galaxy_url=%s' % galaxy_url )
        return trans.response.send_redirect( url )
    @web.json
    @web.require_admin
    def get_file_contents( self, trans, file_path ):
        # Avoid caching
        trans.response.headers['Pragma'] = 'no-cache'
        trans.response.headers['Expires'] = '0'
        return suc.get_repository_file_contents( file_path )
    @web.expose
    @web.require_admin
    def get_repository_dependencies( self, trans, repository_id, repository_name, repository_owner, changeset_revision ):
        """
        Send a request to the appropriate tool shed to retrieve the dictionary of repository dependencies defined for the received repository
        name, owner and changeset revision.  The received repository_id is the encoded id of the installed tool shed repository in Galaxy.  We
        need it so that we can derive the tool shed from which it was installed.
        """
        repository = suc.get_installed_tool_shed_repository( trans, repository_id )
        tool_shed_url = suc.get_url_from_repository_tool_shed( trans.app, repository )
        url = suc.url_join( tool_shed_url,
                            'repository/get_repository_dependencies?name=%s&owner=%s&changeset_revision=%s' % \
                            ( repository_name, repository_owner, changeset_revision ) )
        response = urllib2.urlopen( url )
        raw_text = response.read()
        response.close()
        if len( raw_text ) > 2:
            encoded_text = from_json_string( raw_text )
            text = encoding_util.tool_shed_decode( encoded_text )
        else:
            text = ''
        return text
    def get_versions_of_tool( self, app, guid ):
        tool_version = shed_util.get_tool_version( app, guid )
        return tool_version.get_version_ids( app, reverse=True )
    @web.expose
    @web.require_admin
    def initiate_repository_installation( self, trans, shed_repository_ids, encoded_kwd, reinstalling=False ):
        tsr_ids = util.listify( shed_repository_ids )
        tool_shed_repositories = []
        for tsr_id in tsr_ids:
            tsr = trans.sa_session.query( trans.model.ToolShedRepository ).get( trans.security.decode_id( tsr_id ) )
            tool_shed_repositories.append( tsr )
        clause_list = []
        for tsr_id in tsr_ids:
            clause_list.append( trans.model.ToolShedRepository.table.c.id == trans.security.decode_id( tsr_id ) )
        query = trans.sa_session.query( trans.model.ToolShedRepository ).filter( or_( *clause_list ) )
        return trans.fill_template( 'admin/tool_shed_repository/initiate_repository_installation.mako',
                                    encoded_kwd=encoded_kwd,
                                    query=query,
                                    tool_shed_repositories=tool_shed_repositories,
                                    initiate_repository_installation_ids=shed_repository_ids,
                                    reinstalling=reinstalling )
    @web.expose
    @web.require_admin
    def initiate_tool_dependency_installation( self, trans, tool_dependencies ):
        """Install specified dependencies for repository tools."""
        # Get the tool_shed_repository from one of the tool_dependencies.
        message = ''
        tool_shed_repository = tool_dependencies[ 0 ].tool_shed_repository
        # Get the tool_dependencies.xml file from the repository.
        tool_dependencies_config = suc.get_config_from_disk( 'tool_dependencies.xml', tool_shed_repository.repo_path( trans.app ) )
        installed_tool_dependencies = shed_util.handle_tool_dependencies( app=trans.app,
                                                                          tool_shed_repository=tool_shed_repository,
                                                                          tool_dependencies_config=tool_dependencies_config,
                                                                          tool_dependencies=tool_dependencies )
        for installed_tool_dependency in installed_tool_dependencies:
            if installed_tool_dependency.status == trans.app.model.ToolDependency.installation_status.ERROR:
                message += '  %s' % suc.to_safe_string( installed_tool_dependency.error_message )
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
    def install_tool_dependencies( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        tool_dependency_ids = util.listify( params.get( 'tool_dependency_ids', None ) )
        if not tool_dependency_ids:
            tool_dependency_ids = util.listify( params.get( 'id', None ) )
        tool_dependencies = []
        for tool_dependency_id in tool_dependency_ids:
            tool_dependency = shed_util.get_tool_dependency( trans, tool_dependency_id )
            tool_dependencies.append( tool_dependency )
        if kwd.get( 'install_tool_dependencies_button', False ):
            # Filter tool dependencies to only those that are installed.
            tool_dependencies_for_installation = []
            for tool_dependency in tool_dependencies:
                if tool_dependency.status in [ trans.model.ToolDependency.installation_status.UNINSTALLED,
                                               trans.model.ToolDependency.installation_status.ERROR ]:
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
                                                                  action='manage_tool_dependencies',
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
        repo_info_dicts = util.listify( kwd[ 'repo_info_dicts' ] )
        tool_path = kwd[ 'tool_path' ]
        includes_tool_dependencies = util.string_as_bool( kwd[ 'includes_tool_dependencies' ] )
        install_tool_dependencies = CheckboxField.is_checked( kwd.get( 'install_tool_dependencies', '' ) )
        tool_panel_section_key = kwd.get( 'tool_panel_section_key', None )
        if tool_panel_section_key:
            tool_section = trans.app.toolbox.tool_panel[ tool_panel_section_key ]
        else:
            tool_section = None
        for tup in zip( tool_shed_repositories, repo_info_dicts ):
            tool_shed_repository, repo_info_dict = tup
            repo_info_dict = encoding_util.tool_shed_decode( repo_info_dict )
            # Clone each repository to the configured location.
            shed_util.update_tool_shed_repository_status( trans.app, tool_shed_repository, trans.model.ToolShedRepository.installation_status.CLONING )
            repo_info_tuple = repo_info_dict[ tool_shed_repository.name ]
            description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies = repo_info_tuple
            relative_clone_dir = shed_util.generate_tool_path( repository_clone_url, tool_shed_repository.installed_changeset_revision )
            clone_dir = os.path.join( tool_path, relative_clone_dir )
            relative_install_dir = os.path.join( relative_clone_dir, tool_shed_repository.name )
            install_dir = os.path.join( tool_path, relative_install_dir )
            cloned_ok, error_message = suc.clone_repository( repository_clone_url, os.path.abspath( install_dir ), ctx_rev )
            if cloned_ok:
                if reinstalling:
                    # Since we're reinstalling the repository we need to find the latest changeset revision to which is can be updated.
                    current_changeset_revision, current_ctx_rev = shed_util.get_update_to_changeset_revision_and_ctx_rev( trans, tool_shed_repository )
                    if current_ctx_rev != ctx_rev:
                        repo = hg.repository( suc.get_configured_ui(), path=os.path.abspath( install_dir ) )
                        shed_util.pull_repository( repo, repository_clone_url, current_changeset_revision )
                        suc.update_repository( repo, ctx_rev=current_ctx_rev )
                self.handle_repository_contents( trans,
                                                 tool_shed_repository=tool_shed_repository,
                                                 tool_path=tool_path,
                                                 repository_clone_url=repository_clone_url,
                                                 relative_install_dir=relative_install_dir,
                                                 tool_shed=tool_shed_repository.tool_shed,
                                                 tool_section=tool_section,
                                                 shed_tool_conf=kwd.get( 'shed_tool_conf', '' ),
                                                 reinstalling=reinstalling )
                trans.sa_session.refresh( tool_shed_repository )
                metadata = tool_shed_repository.metadata
                if 'tools' in metadata:
                    # Get the tool_versions from the tool shed for each tool in the installed change set.
                    shed_util.update_tool_shed_repository_status( trans.app,
                                                                  tool_shed_repository,
                                                                  trans.model.ToolShedRepository.installation_status.SETTING_TOOL_VERSIONS )
                    tool_shed_url = suc.get_url_from_repository_tool_shed( trans.app, tool_shed_repository )
                    url = suc.url_join( tool_shed_url,
                                        '/repository/get_tool_versions?name=%s&owner=%s&changeset_revision=%s' % \
                                        ( tool_shed_repository.name, tool_shed_repository.owner, tool_shed_repository.changeset_revision ) )
                    response = urllib2.urlopen( url )
                    text = response.read()
                    response.close()
                    if text:
                        tool_version_dicts = from_json_string( text )
                        shed_util.handle_tool_versions( trans.app, tool_version_dicts, tool_shed_repository )
                    else:
                        message += "Version information for the tools included in the <b>%s</b> repository is missing.  " % name
                        message += "Reset all of this repository's metadata in the tool shed, then set the installed tool versions "
                        message += "from the installed repository's <b>Repository Actions</b> menu.  "
                        status = 'error'
                if install_tool_dependencies and tool_shed_repository.tool_dependencies and 'tool_dependencies' in metadata:
                    work_dir = tempfile.mkdtemp()
                    # Install tool dependencies.
                    shed_util.update_tool_shed_repository_status( trans.app,
                                                                  tool_shed_repository,
                                                                  trans.model.ToolShedRepository.installation_status.INSTALLING_TOOL_DEPENDENCIES )
                    # Get the tool_dependencies.xml file from the repository.
                    tool_dependencies_config = suc.get_config_from_disk( 'tool_dependencies.xml', install_dir )#relative_install_dir )
                    installed_tool_dependencies = shed_util.handle_tool_dependencies( app=trans.app,
                                                                                      tool_shed_repository=tool_shed_repository,
                                                                                      tool_dependencies_config=tool_dependencies_config,
                                                                                      tool_dependencies=tool_shed_repository.tool_dependencies )
                    try:
                        shutil.rmtree( work_dir )
                    except:
                        pass
                shed_util.update_tool_shed_repository_status( trans.app, tool_shed_repository, trans.model.ToolShedRepository.installation_status.INSTALLED )
            else:
                # An error occurred while cloning the repository, so reset everything necessary to enable another attempt.
                self.set_repository_attributes( trans,
                                                tool_shed_repository,
                                                status=trans.model.ToolShedRepository.installation_status.ERROR,
                                                error_message=error_message,
                                                deleted=False,
                                                uninstalled=False,
                                                remove_from_disk=True )
        tsr_ids_for_monitoring = [ trans.security.encode_id( tsr.id ) for tsr in tool_shed_repositories ]
        return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                          action='monitor_repository_installation',
                                                          tool_shed_repository_ids=tsr_ids_for_monitoring ) )
    def handle_repository_contents( self, trans, tool_shed_repository, tool_path, repository_clone_url, relative_install_dir, tool_shed=None,
                                    tool_section=None, shed_tool_conf=None, reinstalling=False ):
        """
        Generate the metadata for the installed tool shed repository, among other things.  This method is called from Galaxy (never the tool shed)
        when an admin is installing a new repository or reinstalling an uninstalled repository.
        """
        shed_config_dict = trans.app.toolbox.get_shed_config_dict_by_filename( shed_tool_conf )
        metadata_dict, invalid_file_tups = suc.generate_metadata_for_changeset_revision( app=trans.app,
                                                                                         repository=tool_shed_repository,
                                                                                         repository_clone_url=repository_clone_url,
                                                                                         shed_config_dict=shed_config_dict,
                                                                                         relative_install_dir=relative_install_dir,
                                                                                         repository_files_dir=None,
                                                                                         resetting_all_metadata_on_repository=False,
                                                                                         updating_installed_repository=False,
                                                                                         persist=True )
        tool_shed_repository.metadata = metadata_dict
        trans.sa_session.add( tool_shed_repository )
        trans.sa_session.flush()
        if 'tool_dependencies' in metadata_dict and not reinstalling:
            tool_dependencies = shed_util.create_tool_dependency_objects( trans.app, tool_shed_repository, relative_install_dir, set_status=True )
        if 'tools' in metadata_dict:
            tool_panel_dict = shed_util.generate_tool_panel_dict_for_new_install( metadata_dict[ 'tools' ], tool_section )
            sample_files = metadata_dict.get( 'sample_files', [] )
            tool_index_sample_files = shed_util.get_tool_index_sample_files( sample_files )
            shed_util.copy_sample_files( self.app, tool_index_sample_files, tool_path=tool_path )
            sample_files_copied = [ str( s ) for s in tool_index_sample_files ]
            repository_tools_tups = suc.get_repository_tools_tups( trans.app, metadata_dict )
            if repository_tools_tups:
                # Handle missing data table entries for tool parameters that are dynamically generated select lists.
                repository_tools_tups = shed_util.handle_missing_data_table_entry( trans.app, relative_install_dir, tool_path, repository_tools_tups )
                # Handle missing index files for tool parameters that are dynamically generated select lists.
                repository_tools_tups, sample_files_copied = shed_util.handle_missing_index_file( trans.app,
                                                                                                  tool_path,
                                                                                                  sample_files,
                                                                                                  repository_tools_tups,
                                                                                                  sample_files_copied )
                # Copy remaining sample files included in the repository to the ~/tool-data directory of the local Galaxy instance.
                shed_util.copy_sample_files( trans.app, sample_files, tool_path=tool_path, sample_files_copied=sample_files_copied )
                shed_util.add_to_tool_panel( app=trans.app,
                                             repository_name=tool_shed_repository.name,
                                             repository_clone_url=repository_clone_url,
                                             changeset_revision=tool_shed_repository.installed_changeset_revision,
                                             repository_tools_tups=repository_tools_tups,
                                             owner=tool_shed_repository.owner,
                                             shed_tool_conf=shed_tool_conf,
                                             tool_panel_dict=tool_panel_dict,
                                             new_install=True )
        if 'datatypes' in metadata_dict:
            tool_shed_repository.status = trans.model.ToolShedRepository.installation_status.LOADING_PROPRIETARY_DATATYPES
            if not tool_shed_repository.includes_datatypes:
                tool_shed_repository.includes_datatypes = True
            trans.sa_session.add( tool_shed_repository )
            trans.sa_session.flush()
            files_dir = relative_install_dir
            if shed_config_dict.get( 'tool_path' ):
                files_dir = os.path.join( shed_config_dict['tool_path'], files_dir )
            datatypes_config = suc.get_config_from_disk( 'datatypes_conf.xml', files_dir )
            # Load data types required by tools.
            converter_path, display_path = shed_util.alter_config_and_load_prorietary_datatypes( trans.app, datatypes_config, files_dir, override=False )
            if converter_path or display_path:
                # Create a dictionary of tool shed repository related information.
                repository_dict = shed_util.create_repository_dict_for_proprietary_datatypes( tool_shed=tool_shed,
                                                                                              name=tool_shed_repository.name,
                                                                                              owner=tool_shed_repository.owner,
                                                                                              installed_changeset_revision=tool_shed_repository.installed_changeset_revision,
                                                                                              tool_dicts=metadata_dict.get( 'tools', [] ),
                                                                                              converter_path=converter_path,
                                                                                              display_path=display_path )
            if converter_path:
                # Load proprietary datatype converters
                trans.app.datatypes_registry.load_datatype_converters( trans.app.toolbox, installed_repository_dict=repository_dict )
            if display_path:
                # Load proprietary datatype display applications
                trans.app.datatypes_registry.load_display_applications( installed_repository_dict=repository_dict )
    @web.expose
    @web.require_admin
    def manage_repository( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        repository_id = kwd[ 'id' ]
        operation = kwd.get( 'operation', None )
        repository = suc.get_installed_tool_shed_repository( trans, repository_id )
        if not repository:
            return trans.show_error_message( 'Invalid repository specified.' )
        tool_shed_url = suc.get_url_from_repository_tool_shed( trans.app, repository )
        if repository.status in [ trans.model.ToolShedRepository.installation_status.CLONING ]:
            return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                              action='monitor_repository_installation',
                                                              **kwd ) )
        if repository.can_install and operation == 'install':
            # Send a request to the tool shed to install the repository.
            url = suc.url_join( tool_shed_url,
                                'repository/install_repositories_by_revision?name=%s&owner=%s&changeset_revisions=%s&galaxy_url=%s' % \
                                ( repository.name, repository.owner, repository.installed_changeset_revision, ( url_for( '/', qualified=True ) ) ) )
            return trans.response.send_redirect( url )
        description = util.restore_text( params.get( 'description', repository.description ) )
        shed_tool_conf, tool_path, relative_install_dir = suc.get_tool_panel_config_tool_path_install_dir( trans.app, repository )
        if relative_install_dir:
            repo_files_dir = os.path.abspath( os.path.join( tool_path, relative_install_dir, repository.name ) )
        else:
            repo_files_dir = None
        if repository.in_error_state:
            message = "This repository is not installed correctly (see the <b>Repository installation error</b> below).  Choose "
            message += "<b>Reset to install</b> from the <b>Repository Actions</b> menu, correct problems if necessary, and try "
            message += "installing the repository again."
            status = "error"
        elif repository.can_install:
            message = "This repository is not installed.  You can install it by choosing  <b>Install</b> from the <b>Repository Actions</b> menu."
            status = "error"
        elif params.get( 'edit_repository_button', False ):
            if description != repository.description:
                repository.description = description
                trans.sa_session.add( repository )
                trans.sa_session.flush()
            message = "The repository information has been updated."
        containers_dict = shed_util.populate_containers_dict_from_repository_metadata( trans, tool_shed_url, tool_path, repository )
        return trans.fill_template( '/admin/tool_shed_repository/manage_repository.mako',
                                    repository=repository,
                                    description=description,
                                    repo_files_dir=repo_files_dir,
                                    containers_dict=containers_dict,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def manage_repositories( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        tsrid = params.get( 'tool_shed_repository_id', None )
        tsridslist = util.listify( params.get( 'tool_shed_repository_ids', None ) )
        if not tsridslist:
            tsridslist = util.listify( params.get( 'id', None ) )
        if tsrid and tsrid not in tsridslist:
            tsridslist.append( tsrid )
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
                repositories_for_uninstallation = []
                for repository_id in tool_shed_repository_id:
                    repository = trans.sa_session.query( trans.model.ToolShedRepository ).get( trans.security.decode_id( repository_id ) )
                    if repository.status in [ trans.model.ToolShedRepository.installation_status.INSTALLED,
                                              trans.model.ToolShedRepository.installation_status.ERROR ]:
                        repositories_for_uninstallation.append( repository )
                if repositories_for_uninstallation:
                    return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                      action='uninstall_repositories',
                                                                      **kwd ) )
                else:
                    kwd[ 'message' ] = 'All selected tool shed repositories are already uninstalled.'
                    kwd[ 'status' ] = 'error'
            elif operation == "install":
                reinstalling = util.string_as_bool( params.get( 'reinstalling', False ) )
                encoded_kwd = kwd[ 'encoded_kwd' ]
                decoded_kwd = encoding_util.tool_shed_decode( encoded_kwd )
                tsr_ids = decoded_kwd[ 'tool_shed_repository_ids' ]
                repositories_for_installation = []
                for tsr_id in tsr_ids:
                    repository = trans.sa_session.query( trans.model.ToolShedRepository ).get( trans.security.decode_id( tsr_id ) )
                    if repository.status in [ trans.model.ToolShedRepository.installation_status.NEW,
                                              trans.model.ToolShedRepository.installation_status.UNINSTALLED ]:
                        repositories_for_installation.append( repository )
                if repositories_for_installation:
                    self.install_tool_shed_repositories( trans, repositories_for_installation, reinstalling=reinstalling, **decoded_kwd )
                else:
                    kwd[ 'message' ] = 'All selected tool shed repositories are already installed.'
                    kwd[ 'status' ] = 'error'
        return self.repository_installation_grid( trans, **kwd )
    @web.expose
    @web.require_admin
    def manage_tool_dependencies( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        tool_dependency_ids = shed_util.get_tool_dependency_ids( as_string=False, **kwd )
        # We need a tool_shed_repository, so get it from one of the tool_dependencies.
        tool_dependency = shed_util.get_tool_dependency( trans, tool_dependency_ids[ 0 ] )
        tool_shed_repository = tool_dependency.tool_shed_repository
        self.tool_dependency_grid.title = "Tool shed repository '%s' tool dependencies"  % tool_shed_repository.name
        self.tool_dependency_grid.global_actions = \
            [ grids.GridAction( label='Manage repository', 
                                url_args=dict( controller='admin_toolshed', 
                                               action='manage_repository', 
                                               id=trans.security.encode_id( tool_shed_repository.id ) ) ),
              grids.GridAction( label='Browse repository', 
                                url_args=dict( controller='admin_toolshed', 
                                               action='browse_repository', 
                                               id=trans.security.encode_id( tool_shed_repository.id ) ) ),
              grids.GridAction( label='Get repository updates', 
                                url_args=dict( controller='admin_toolshed', 
                                               action='check_for_updates', 
                                               id=trans.security.encode_id( tool_shed_repository.id ) ) ),
              grids.GridAction( label='Set tool versions', 
                                url_args=dict( controller='admin_toolshed', 
                                               action='set_tool_versions', 
                                               id=trans.security.encode_id( tool_shed_repository.id ) ) ),
              grids.GridAction( label='Deactivate or uninstall repository', 
                                url_args=dict( controller='admin_toolshed', 
                                               action='deactivate_or_uninstall_repository', 
                                               id=trans.security.encode_id( tool_shed_repository.id ) ) ) ]
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
            elif operation == 'uninstall':
                tool_dependencies_for_uninstallation = []
                for tool_dependency_id in tool_dependency_ids:
                    tool_dependency = shed_util.get_tool_dependency( trans, tool_dependency_id )
                    if tool_dependency.status in [ trans.model.ToolDependency.installation_status.INSTALLED,
                                                   trans.model.ToolDependency.installation_status.ERROR ]:
                        tool_dependencies_for_uninstallation.append( tool_dependency )
                if tool_dependencies_for_uninstallation:
                    return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                      action='uninstall_tool_dependencies',
                                                                      **kwd ) )
                else:
                    kwd[ 'message' ] = 'All selected tool dependencies are already uninstalled.'
                    kwd[ 'status' ] = 'error'
            elif operation == "install":
                if trans.app.config.tool_dependency_dir:
                    tool_dependencies_for_installation = []
                    for tool_dependency_id in tool_dependency_ids:
                        tool_dependency = shed_util.get_tool_dependency( trans, tool_dependency_id )
                        if tool_dependency.status in [ trans.model.ToolDependency.installation_status.NEVER_INSTALLED,
                                                       trans.model.ToolDependency.installation_status.UNINSTALLED ]:
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
        return self.tool_dependency_grid( trans, **kwd )
    @web.expose
    @web.require_admin
    def monitor_repository_installation( self, trans, **kwd ):
        params = util.Params( kwd )
        tsrid = params.get( 'tool_shed_repository_id', None )
        tsridslist = util.listify( params.get( 'tool_shed_repository_ids', None ) )
        if not tsridslist:
            tsridslist = util.listify( params.get( 'id', None ) )
        if tsrid and tsrid not in tsridslist:
            tsridslist.append( tsrid )
        if not tsridslist:
            tsridslist = get_ids_of_tool_shed_repositories_being_installed( trans, as_string=False )
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
        if not have_shed_tool_conf_for_install( trans ):
            message = 'The <b>tool_config_file</b> setting in <b>universe_wsgi.ini</b> must include at least one shed tool configuration file name with a '
            message += '<b>&lt;toolbox&gt;</b> tag that includes a <b>tool_path</b> attribute value which is a directory relative to the Galaxy installation '
            message += 'directory in order to automatically install tools from a Galaxy tool shed (e.g., the file name <b>shed_tool_conf.xml</b> whose '
            message += '<b>&lt;toolbox&gt;</b> tag is <b>&lt;toolbox tool_path="../shed_tools"&gt;</b>).<p/>See the '
            message += '<a href="http://wiki.g2.bx.psu.edu/InstallingRepositoriesToGalaxy" target="_blank">Installation of Galaxy tool shed repository tools '
            message += 'into a local Galaxy instance</a> section of the Galaxy tool shed wiki for all of the details.'
            return trans.show_error_message( message )
        message = kwd.get( 'message', ''  )
        status = kwd.get( 'status', 'done' )
        includes_tools = util.string_as_bool( kwd.get( 'includes_tools', False ) )
        tool_shed_url = kwd[ 'tool_shed_url' ]
        # Handle repository dependencies.
        includes_repository_dependencies = util.string_as_bool( kwd.get( 'includes_repository_dependencies', False ) )
        install_repository_dependencies = kwd.get( 'install_repository_dependencies', '' )
        # Every repository will be installed into the same tool panel section or all will be installed outside of any sections.
        new_tool_panel_section = kwd.get( 'new_tool_panel_section', '' )
        tool_panel_section = kwd.get( 'tool_panel_section', '' )
        # One or more repositories may include tools, but not necessarily all of them.
        includes_tools = util.string_as_bool( kwd.get( 'includes_tools', False ) )
        includes_tool_dependencies = util.string_as_bool( kwd.get( 'includes_tool_dependencies', False ) )
        install_tool_dependencies = kwd.get( 'install_tool_dependencies', '' )
        encoded_repo_info_dicts = util.listify( kwd.get( 'encoded_repo_info_dicts', None ) )
        if not encoded_repo_info_dicts:
            # The request originated in the tool shed.
            repository_ids = kwd.get( 'repository_ids', None )
            changeset_revisions = kwd.get( 'changeset_revisions', None )
            # Get the information necessary to install each repository.
            url = suc.url_join( tool_shed_url,
                                'repository/get_repository_information?repository_ids=%s&changeset_revisions=%s' % \
                                ( repository_ids, changeset_revisions ) )
            response = urllib2.urlopen( url )
            raw_text = response.read()
            response.close()
            repo_information_dict = from_json_string( raw_text )
            includes_tools = util.string_as_bool( repo_information_dict.get( 'includes_tools', False ) )
            includes_repository_dependencies = util.string_as_bool( repo_information_dict.get( 'includes_repository_dependencies', False ) )
            includes_tool_dependencies = util.string_as_bool( repo_information_dict.get( 'includes_tool_dependencies', False ) )
            encoded_repo_info_dicts = util.listify( repo_information_dict.get( 'repo_info_dicts', [] ) )
        repo_info_dicts = [ encoding_util.tool_shed_decode( encoded_repo_info_dict ) for encoded_repo_info_dict in encoded_repo_info_dicts ]
        if ( not includes_tools and not includes_repository_dependencies ) or \
            ( ( includes_tools or includes_repository_dependencies ) and kwd.get( 'select_tool_panel_section_button', False ) ):
            install_repository_dependencies = CheckboxField.is_checked( install_repository_dependencies )
            if includes_tool_dependencies:
                install_tool_dependencies = CheckboxField.is_checked( install_tool_dependencies )
                shed_tool_conf = kwd[ 'shed_tool_conf' ]
            else:
                install_tool_dependencies = False
                # If installing a repository that includes no tools, get the relative tool_path from the file to which the migrated_tools_config
                # setting points.
                shed_tool_conf = trans.app.config.migrated_tools_config
            tool_path = suc.get_tool_path_by_shed_tool_conf_filename( trans, shed_tool_conf )
            created_or_updated_tool_shed_repositories, repo_info_dicts, filtered_repo_info_dicts, message = \
                shed_util.create_repository_dependency_objects( trans, tool_path, tool_shed_url, repo_info_dicts, reinstalling=False )
            if message and len( repo_info_dicts ) == 1:
                installed_tool_shed_repository = created_or_updated_tool_shed_repositories[ 0 ]
                message+= 'Click <a href="%s">here</a> to manage the repository.  ' % \
                    ( web.url_for( controller='admin_toolshed', action='manage_repository', id=trans.security.encode_id( installed_tool_shed_repository.id ) ) )
                return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                  action='browse_repositories',
                                                                  message=message,
                                                                  status='error' ) )
            if created_or_updated_tool_shed_repositories:
                if install_repository_dependencies:
                    # Build repository dependency relationships.
                    suc.build_repository_dependency_relationships( trans, repo_info_dicts, created_or_updated_tool_shed_repositories )
                # Handle contained tools.
                if includes_tools and ( new_tool_panel_section or tool_panel_section ):
                    if new_tool_panel_section:
                        section_id = new_tool_panel_section.lower().replace( ' ', '_' )
                        tool_panel_section_key = 'section_%s' % str( section_id )
                        if tool_panel_section_key in trans.app.toolbox.tool_panel:
                            # Appending a tool to an existing section in trans.app.toolbox.tool_panel
                            log.debug( "Appending to tool panel section: %s" % new_tool_panel_section )
                            tool_section = trans.app.toolbox.tool_panel[ tool_panel_section_key ]
                        else:
                            # Appending a new section to trans.app.toolbox.tool_panel
                            log.debug( "Loading new tool panel section: %s" % new_tool_panel_section )
                            elem = Element( 'section' )
                            elem.attrib[ 'name' ] = new_tool_panel_section
                            elem.attrib[ 'id' ] = section_id
                            elem.attrib[ 'version' ] = ''
                            tool_section = tools.ToolSection( elem )
                            trans.app.toolbox.tool_panel[ tool_panel_section_key ] = tool_section
                    else:
                        tool_panel_section_key = 'section_%s' % tool_panel_section
                        tool_section = trans.app.toolbox.tool_panel[ tool_panel_section_key ]
                else:
                    tool_panel_section_key = None
                    tool_section = None
                tsrids_list = [ trans.security.encode_id( tsr.id ) for tsr in created_or_updated_tool_shed_repositories ]
                new_kwd = dict( includes_tools=includes_tools,
                                includes_repository_dependencies=includes_repository_dependencies,
                                install_repository_dependencies=install_repository_dependencies,
                                includes_tool_dependencies=includes_tool_dependencies,
                                install_tool_dependencies=install_tool_dependencies,
                                message=message,
                                repo_info_dicts=filtered_repo_info_dicts,
                                shed_tool_conf=shed_tool_conf,
                                status=status,
                                tool_path=tool_path,
                                tool_panel_section_key=tool_panel_section_key,
                                tool_shed_repository_ids=tsrids_list,
                                tool_shed_url=tool_shed_url )
                encoded_kwd = encoding_util.tool_shed_encode( new_kwd )
                tsrids_str = ','.join( tsrids_list )
                return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                  action='initiate_repository_installation',
                                                                  shed_repository_ids=tsrids_str,
                                                                  encoded_kwd=encoded_kwd,
                                                                  reinstalling=False ) )
            else:
                kwd[ 'message' ] = message
                kwd[ 'status' ] = status
                return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                  action='manage_repositories',
                                                                  **kwd ) )
        if len( trans.app.toolbox.shed_tool_confs ) > 1:
            shed_tool_conf_select_field = build_shed_tool_conf_select_field( trans )
            shed_tool_conf = None
        else:
            shed_tool_conf_dict = trans.app.toolbox.shed_tool_confs[0]
            shed_tool_conf = shed_tool_conf_dict[ 'config_filename' ]
            shed_tool_conf = shed_tool_conf.replace( './', '', 1 )
            shed_tool_conf_select_field = None
        tool_panel_section_select_field = build_tool_panel_section_select_field( trans )
        if len( repo_info_dicts ) == 1:
            # If we're installing a single repository, see if it contains a readme or dependencies that we can display.
            repo_info_dict = repo_info_dicts[ 0 ]
            name = repo_info_dict.keys()[ 0 ]
            repo_info_tuple = repo_info_dict[ name ]
            description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies = \
                suc.get_repo_info_tuple_contents( repo_info_tuple )
            url = suc.url_join( tool_shed_url,
                                'repository/get_readme_files?name=%s&owner=%s&changeset_revision=%s' % \
                                ( name, repository_owner, changeset_revision ) )
            response = urllib2.urlopen( url )
            raw_text = response.read()
            response.close()
            readme_files_dict = from_json_string( raw_text )
            # Since we are installing a new repository, no tool dependencies will be considered "missing".  Most of the repository contents
            # are set to None since we don't yet know what they are.
            containers_dict = suc.build_repository_containers_for_galaxy( trans=trans,
                                                                          toolshed_base_url=tool_shed_url,
                                                                          repository_name=name,
                                                                          repository_owner=repository_owner,
                                                                          changeset_revision=changeset_revision,
                                                                          repository=None,
                                                                          datatypes=None,
                                                                          invalid_tools=None,
                                                                          missing_tool_dependencies=None,
                                                                          readme_files_dict=readme_files_dict,
                                                                          repository_dependencies=repository_dependencies,
                                                                          tool_dependencies=tool_dependencies,
                                                                          valid_tools=None,
                                                                          workflows=None )
        else:
            containers_dict = dict( datatypes=None,
                                    invalid_tools=None,
                                    readme_files_dict=None,
                                    repository_dependencies=None,
                                    tool_dependencies=None,
                                    valid_tools=None,
                                    workflows=None )
        # Handle tool dependencies chack box.
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
        return trans.fill_template( '/admin/tool_shed_repository/select_tool_panel_section.mako',
                                    encoded_repo_info_dicts=encoded_repo_info_dicts,
                                    includes_tools=includes_tools,
                                    includes_tool_dependencies=includes_tool_dependencies,
                                    install_tool_dependencies_check_box=install_tool_dependencies_check_box,
                                    includes_repository_dependencies=includes_repository_dependencies,
                                    install_repository_dependencies_check_box=install_repository_dependencies_check_box,
                                    new_tool_panel_section=new_tool_panel_section,
                                    containers_dict=containers_dict,
                                    shed_tool_conf=shed_tool_conf,
                                    shed_tool_conf_select_field=shed_tool_conf_select_field,
                                    tool_panel_section_select_field=tool_panel_section_select_field,
                                    tool_shed_url=kwd[ 'tool_shed_url' ],
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def reinstall_repository( self, trans, **kwd ):
        """
        Reinstall a tool shed repository that has been previously uninstalled, making sure to handle all repository and tool dependencies of the
        repository.
        """
        message = kwd.get( 'message', '' )
        status = kwd.get( 'status', 'done' )
        repository_id = kwd[ 'id' ]
        tool_shed_repository = suc.get_installed_tool_shed_repository( trans, repository_id )
        no_changes = kwd.get( 'no_changes', '' )
        no_changes_checked = CheckboxField.is_checked( no_changes )
        install_repository_dependencies = CheckboxField.is_checked( kwd.get( 'install_repository_dependencies', '' ) )
        install_tool_dependencies = CheckboxField.is_checked( kwd.get( 'install_tool_dependencies', '' ) )
        new_tool_panel_section = kwd.get( 'new_tool_panel_section', '' )
        tool_panel_section = kwd.get( 'tool_panel_section', '' )
        shed_tool_conf, tool_path, relative_install_dir = suc.get_tool_panel_config_tool_path_install_dir( trans.app, tool_shed_repository )
        repository_clone_url = suc.generate_clone_url_for_installed_repository( trans.app, tool_shed_repository )
        clone_dir = os.path.join( tool_path, shed_util.generate_tool_path( repository_clone_url, tool_shed_repository.installed_changeset_revision ) )
        relative_install_dir = os.path.join( clone_dir, tool_shed_repository.name )
        tool_shed_url = suc.get_url_from_repository_tool_shed( trans.app, tool_shed_repository )
        tool_section = None
        tool_panel_section_key = None
        metadata = tool_shed_repository.metadata
        if tool_shed_repository.includes_tools:
            # Get the location in the tool panel in which each tool was originally loaded.
            if 'tool_panel_section' in metadata:
                tool_panel_dict = metadata[ 'tool_panel_section' ]
                if not tool_panel_dict:
                    tool_panel_dict = shed_util.generate_tool_panel_dict_for_new_install( metadata[ 'tools' ] )
            else:
                tool_panel_dict = shed_util.generate_tool_panel_dict_for_new_install( metadata[ 'tools' ] )
            # Fix this to handle the case where the tools are distributed across in more than 1 ToolSection - this assumes everything was loaded into 1
            # section (or no section) in the tool panel.
            tool_section_dicts = tool_panel_dict[ tool_panel_dict.keys()[ 0 ] ]
            tool_section_dict = tool_section_dicts[ 0 ]
            original_section_id = tool_section_dict[ 'id' ]
            original_section_name = tool_section_dict[ 'name' ]
            if no_changes_checked:
                if original_section_id:
                    tool_panel_section_key = 'section_%s' % str( original_section_id )
                    if tool_panel_section_key in trans.app.toolbox.tool_panel:
                        tool_section = trans.app.toolbox.tool_panel[ tool_panel_section_key ]
                    else:
                        # The section in which the tool was originally loaded used to be in the tool panel, but no longer is.
                        elem = Element( 'section' )
                        elem.attrib[ 'name' ] = original_section_name
                        elem.attrib[ 'id' ] = original_section_id
                        elem.attrib[ 'version' ] = ''
                        tool_section = tools.ToolSection( elem )
                        trans.app.toolbox.tool_panel[ tool_panel_section_key ] = tool_section
            else:
                # The user elected to change the tool panel section to contain the tools.
                if new_tool_panel_section:
                    section_id = new_tool_panel_section.lower().replace( ' ', '_' )
                    tool_panel_section_key = 'section_%s' % str( section_id )
                    if tool_panel_section_key in trans.app.toolbox.tool_panel:
                        # Appending a tool to an existing section in trans.app.toolbox.tool_panel
                        log.debug( "Appending to tool panel section: %s" % new_tool_panel_section )
                        tool_section = trans.app.toolbox.tool_panel[ tool_panel_section_key ]
                    else:
                        # Appending a new section to trans.app.toolbox.tool_panel
                        log.debug( "Loading new tool panel section: %s" % new_tool_panel_section )
                        elem = Element( 'section' )
                        elem.attrib[ 'name' ] = new_tool_panel_section
                        elem.attrib[ 'id' ] = section_id
                        elem.attrib[ 'version' ] = ''
                        tool_section = tools.ToolSection( elem )
                        trans.app.toolbox.tool_panel[ tool_panel_section_key ] = tool_section
                elif tool_panel_section:
                    tool_panel_section_key = 'section_%s' % tool_panel_section
                    tool_section = trans.app.toolbox.tool_panel[ tool_panel_section_key ]
                else:
                    tool_section = None
        # The repository's status must be updated from 'Uninstall' to 'New' when initiating reinstall so the repository_installation_updater will function.
        tool_shed_repository = suc.create_or_update_tool_shed_repository( trans.app,
                                                                          tool_shed_repository.name,
                                                                          tool_shed_repository.description,
                                                                          tool_shed_repository.installed_changeset_revision,
                                                                          tool_shed_repository.ctx_rev,
                                                                          repository_clone_url,
                                                                          tool_shed_repository.metadata,
                                                                          trans.model.ToolShedRepository.installation_status.NEW,
                                                                          tool_shed_repository.installed_changeset_revision,
                                                                          tool_shed_repository.owner,
                                                                          tool_shed_repository.dist_to_shed )
        ctx_rev = suc.get_ctx_rev( tool_shed_url, tool_shed_repository.name, tool_shed_repository.owner, tool_shed_repository.installed_changeset_revision )
        repo_info_dicts = []
        repo_info_dict = kwd.get( 'repo_info_dict', None )
        if not repo_info_dict:
            # Entering this if block used to happen only if the tool_shed_repository does not include any valid tools.  After repository dependencies
            # were introduced, it may never happen, but we'll keep the block just in case.
            if install_repository_dependencies:
                repository_dependencies = self.get_repository_dependencies( trans=trans,
                                                                            repository_id=repository_id,
                                                                            repository_name=tool_shed_repository.name,
                                                                            repository_owner=tool_shed_repository.owner,
                                                                            changeset_revision=tool_shed_repository.installed_changeset_revision )
            else:
                repository_dependencies = None
            repo_info_dict = suc.create_repo_info_dict( trans=trans,
                                                        repository_clone_url=repository_clone_url,
                                                        changeset_revision=tool_shed_repository.installed_changeset_revision,
                                                        ctx_rev=ctx_rev,
                                                        repository_owner=tool_shed_repository.owner,
                                                        repository_name=tool_shed_repository.name,
                                                        repository=None,
                                                        repository_metadata=None,
                                                        metadata=metadata,
                                                        repository_dependencies=repository_dependencies )
            repo_info_dict = encoding_util.tool_shed_encode( repo_info_dict )
        repo_info_dicts.append( repo_info_dict )
        # Make sure all tool_shed_repository records exist.
        created_or_updated_tool_shed_repositories = [ tool_shed_repository ]
        if install_repository_dependencies:
            created_or_updated_tool_shed_repositories, repo_info_dicts, filtered_repo_info_dicts = \
                shed_util.create_repository_dependency_objects( trans, tool_path, tool_shed_url, repo_info_dicts, reinstalling=True )
            if len( created_or_updated_tool_shed_repositories ) > 1:
                # Build repository dependency relationships.
                suc.build_repository_dependency_relationships( trans, filtered_repo_info_dicts, created_or_updated_tool_shed_repositories )
        encoded_repository_ids = [ trans.security.encode_id( r.id ) for r in created_or_updated_tool_shed_repositories ]
        new_kwd = dict( includes_tool_dependencies=tool_shed_repository.includes_tool_dependencies,
                        includes_tools=tool_shed_repository.includes_tools,
                        install_tool_dependencies=install_tool_dependencies,
                        repo_info_dicts=util.listify( repo_info_dict ),
                        message=message,
                        new_tool_panel_section=new_tool_panel_section,
                        shed_tool_conf=shed_tool_conf,
                        status=status,
                        tool_panel_section=tool_panel_section,
                        tool_path=tool_path,
                        tool_panel_section_key=tool_panel_section_key,
                        tool_shed_repository_ids=encoded_repository_ids,
                        tool_shed_url=tool_shed_url )
        encoded_kwd = encoding_util.tool_shed_encode( new_kwd )
        return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                          action='initiate_repository_installation',
                                                          shed_repository_ids=encoded_repository_ids,
                                                          encoded_kwd=encoded_kwd,
                                                          reinstalling=True ) )
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
                repository = trans.sa_session.query( trans.model.ToolShedRepository ).get( trans.security.decode_id( id ) )
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
        message = ''
        repository_id = kwd[ 'id' ]
        tool_shed_repository = suc.get_installed_tool_shed_repository( trans, repository_id )
        metadata = tool_shed_repository.metadata
        tool_shed_url = suc.get_url_from_repository_tool_shed( trans.app, tool_shed_repository )
        ctx_rev = suc.get_ctx_rev( tool_shed_url, tool_shed_repository.name, tool_shed_repository.owner, tool_shed_repository.installed_changeset_revision )
        repository_clone_url = suc.generate_clone_url_for_installed_repository( trans.app, tool_shed_repository )
        repository_dependencies = self.get_repository_dependencies( trans=trans,
                                                                    repository_id=repository_id,
                                                                    repository_name=tool_shed_repository.name,
                                                                    repository_owner=tool_shed_repository.owner,
                                                                    changeset_revision=tool_shed_repository.installed_changeset_revision )
        if repository_dependencies:
            includes_repository_dependencies = True
        else:
            includes_repository_dependencies = False
        includes_tool_dependencies = tool_shed_repository.includes_tool_dependencies
        repo_info_dict = suc.create_repo_info_dict( trans=trans,
                                                    repository_clone_url=repository_clone_url,
                                                    changeset_revision=tool_shed_repository.installed_changeset_revision,
                                                    ctx_rev=ctx_rev,
                                                    repository_owner=tool_shed_repository.owner,
                                                    repository_name=tool_shed_repository.name,
                                                    repository=None,
                                                    repository_metadata=None,
                                                    metadata=metadata,
                                                    repository_dependencies=repository_dependencies )
        # Get the location in the tool panel in which the tool was originally loaded.
        if 'tool_panel_section' in metadata:
            tool_panel_dict = metadata[ 'tool_panel_section' ]
            if tool_panel_dict:
                if shed_util.panel_entry_per_tool( tool_panel_dict ):
                    # TODO: Fix this to handle the case where the tools are distributed across in more than 1 ToolSection.  The
                    # following assumes everything was loaded into 1 section (or no section) in the tool panel.
                    tool_section_dicts = tool_panel_dict[ tool_panel_dict.keys()[ 0 ] ]
                    tool_section_dict = tool_section_dicts[ 0 ]
                    original_section_name = tool_section_dict[ 'name' ]
                else:
                    original_section_name = tool_panel_dict[ 'name' ]
            else:
                original_section_name = ''
        else:
            original_section_name = ''
        tool_panel_section_select_field = build_tool_panel_section_select_field( trans )
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
        if metadata:
            datatypes = metadata.get( 'datatypes', None )
            invalid_tools = metadata.get( 'invalid_tools', None )
            if tool_shed_repository.has_readme_files:
                url = suc.url_join( tool_shed_url,
                                    'repository/get_readme_files?name=%s&owner=%s&changeset_revision=%s' % \
                                    ( tool_shed_repository.name, tool_shed_repository.owner, tool_shed_repository.installed_changeset_revision ) )
                response = urllib2.urlopen( url )
                raw_text = response.read()
                response.close()
                readme_files_dict = from_json_string( raw_text )
            else:
                readme_files_dict = None
            repository_dependencies = metadata.get( 'repository_dependencies', None )
            repository_dependencies_dict_for_display = {}
            if repository_dependencies:
                # We need to add a root_key entry to the repository_dependencies dictionary since it will not be included in the installed tool
                # shed repository metadata.
                root_key = container_util.generate_repository_dependencies_key_for_repository( tool_shed_repository.tool_shed,
                                                                                               tool_shed_repository.name,
                                                                                               tool_shed_repository.owner,
                                                                                               tool_shed_repository.installed_changeset_revision )
                rd_tups_for_display = []
                rd_tups = repository_dependencies[ 'repository_dependencies' ]
                repository_dependencies_dict_for_display[ 'root_key' ] = root_key
                repository_dependencies_dict_for_display[ root_key ] = rd_tups
                repository_dependencies_dict_for_display[ 'description' ] = repository_dependencies[ 'description' ]
            all_tool_dependencies = metadata.get( 'tool_dependencies', None )            
            tool_dependencies, missing_tool_dependencies = shed_util.get_installed_and_missing_tool_dependencies( trans, 
                                                                                                                  tool_shed_repository, 
                                                                                                                  all_tool_dependencies )
            valid_tools = metadata.get( 'tools', None )
            workflows = metadata.get( 'workflows', None )
            # All tool dependencies will be considered missing since we are reinstalling the repository.
            if tool_dependencies:
                for td in tool_dependencies:
                    missing_tool_dependencies.append( td )
                tool_dependencies = None
            containers_dict = suc.build_repository_containers_for_galaxy( trans=trans,
                                                                          toolshed_base_url=tool_shed_url,
                                                                          repository_name=tool_shed_repository.name,
                                                                          repository_owner=tool_shed_repository.owner,
                                                                          changeset_revision=tool_shed_repository.installed_changeset_revision,
                                                                          repository=tool_shed_repository,
                                                                          datatypes=datatypes,
                                                                          invalid_tools=invalid_tools,
                                                                          missing_tool_dependencies=missing_tool_dependencies,
                                                                          readme_files_dict=readme_files_dict,
                                                                          repository_dependencies=repository_dependencies,
                                                                          tool_dependencies=missing_tool_dependencies,
                                                                          valid_tools=valid_tools,
                                                                          workflows=workflows )
        else:
            containers_dict = dict( datatypes=None,
                                    invalid_tools=None,
                                    readme_files_dict=None,
                                    repository_dependencies=None,
                                    tool_dependencies=None,
                                    valid_tools=None,
                                    workflows=None )
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
                                    includes_tool_dependencies=tool_shed_repository.includes_tool_dependencies,
                                    includes_repository_dependencies=includes_repository_dependencies,
                                    install_repository_dependencies_check_box=install_repository_dependencies_check_box,
                                    install_tool_dependencies_check_box=install_tool_dependencies_check_box,
                                    containers_dict=containers_dict,
                                    tool_panel_section_select_field=tool_panel_section_select_field,
                                    encoded_repo_info_dict=encoding_util.tool_shed_encode( repo_info_dict ),
                                    repo_info_dict=repo_info_dict,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def reset_metadata_on_selected_installed_repositories( self, trans, **kwd ):
        if 'reset_metadata_on_selected_repositories_button' in kwd:
            kwd[ 'CONTROLLER' ] = suc.GALAXY_ADMIN_TOOL_SHED_CONTROLLER
            message, status = suc.reset_metadata_on_selected_repositories( trans, **kwd )
        else:
            message = util.restore_text( kwd.get( 'message', ''  ) )
            status = kwd.get( 'status', 'done' )
        repositories_select_field = suc.build_repository_ids_select_field( trans, suc.GALAXY_ADMIN_TOOL_SHED_CONTROLLER )
        return trans.fill_template( '/admin/tool_shed_repository/reset_metadata_on_selected_repositories.mako',
                                    repositories_select_field=repositories_select_field,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def reset_repository_metadata( self, trans, id ):
        """Reset all metadata on a single installed tool shed repository."""
        repository = suc.get_installed_tool_shed_repository( trans, id )
        tool_shed_url = suc.get_url_from_repository_tool_shed( trans.app, repository )
        repository_clone_url = suc.generate_clone_url_for_installed_repository( trans.app, repository )
        tool_path, relative_install_dir = repository.get_tool_relative_path( trans.app )
        if relative_install_dir:
            original_metadata_dict = repository.metadata
            metadata_dict, invalid_file_tups = suc.generate_metadata_for_changeset_revision( app=trans.app,
                                                                                             repository=repository,
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
                trans.sa_session.add( repository )
                trans.sa_session.flush()
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
            self.set_repository_attributes( trans,
                                            repository,
                                            status=trans.model.ToolShedRepository.installation_status.NEW,
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
    def set_repository_attributes( self, trans, repository, status, error_message, deleted, uninstalled, remove_from_disk=False ):
        if remove_from_disk:
            relative_install_dir = repository.repo_path( trans.app )
            if relative_install_dir:
                clone_dir = os.path.abspath( relative_install_dir )
                shutil.rmtree( clone_dir )
                log.debug( "Removed repository installation directory: %s" % str( clone_dir ) )
        repository.error_message = error_message
        repository.status = status
        repository.deleted = deleted
        repository.uninstalled = uninstalled
        trans.sa_session.add( repository )
        trans.sa_session.flush()
    @web.expose
    @web.require_admin
    def set_tool_versions( self, trans, **kwd ):
        """
        Get the tool_versions from the tool shed for each tool in the installed revision of a selected tool shed repository and update the
        metadata for the repository's revision in the Galaxy database.
        """
        repository = suc.get_installed_tool_shed_repository( trans, kwd[ 'id' ] )
        tool_shed_url = suc.get_url_from_repository_tool_shed( trans.app, repository )
        url = suc.url_join( tool_shed_url,
                            'repository/get_tool_versions?name=%s&owner=%s&changeset_revision=%s' % \
                            ( repository.name, repository.owner, repository.changeset_revision ) )
        response = urllib2.urlopen( url )
        text = response.read()
        response.close()
        if text:
            tool_version_dicts = from_json_string( text )
            shed_util.handle_tool_versions( trans.app, tool_version_dicts, repository )
            message = "Tool versions have been set for all included tools."
            status = 'done'
        else:
            message = "Version information for the tools included in the <b>%s</b> repository is missing.  " % repository.name
            message += "Reset all of this reppository's metadata in the tool shed, then set the installed tool versions "
            message ++ "from the installed repository's <b>Repository Actions</b> menu.  "
            status = 'error'
        shed_tool_conf, tool_path, relative_install_dir = suc.get_tool_panel_config_tool_path_install_dir( trans.app, repository )
        repo_files_dir = os.path.abspath( os.path.join( relative_install_dir, repository.name ) )
        containers_dict = shed_util.populate_containers_dict_from_repository_metadata( trans, tool_shed_url, tool_path, repository )
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
                tool_dependency = trans.sa_session.query( trans.model.ToolDependency ).get( trans.security.decode_id( id ) )
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
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        tool_dependency_ids = util.listify( params.get( 'tool_dependency_ids', None ) )
        if not tool_dependency_ids:
            tool_dependency_ids = util.listify( params.get( 'id', None ) )
        tool_dependencies = []
        for tool_dependency_id in tool_dependency_ids:
            tool_dependency = shed_util.get_tool_dependency( trans, tool_dependency_id )
            tool_dependencies.append( tool_dependency )
        tool_shed_repository = tool_dependencies[ 0 ].tool_shed_repository
        if kwd.get( 'uninstall_tool_dependencies_button', False ):
            errors = False
            # Filter tool dependencies to only those that are installed.
            tool_dependencies_for_uninstallation = []
            for tool_dependency in tool_dependencies:
                if tool_dependency.can_uninstall:
                    tool_dependencies_for_uninstallation.append( tool_dependency )
            for tool_dependency in tool_dependencies_for_uninstallation:
                uninstalled, error_message = shed_util.remove_tool_dependency( trans, tool_dependency )
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
                                                              action='manage_tool_dependencies',
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
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        tool_shed_url = kwd[ 'tool_shed_url' ]
        name = params.get( 'name', None )
        owner = params.get( 'owner', None )
        changeset_revision = params.get( 'changeset_revision', None )
        latest_changeset_revision = params.get( 'latest_changeset_revision', None )
        latest_ctx_rev = params.get( 'latest_ctx_rev', None )
        repository = suc.get_tool_shed_repository_by_shed_name_owner_changeset_revision( trans.app, tool_shed_url, name, owner, changeset_revision )
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
                    shed_util.pull_repository( repo, repository_clone_url, latest_ctx_rev )
                    suc.update_repository( repo, latest_ctx_rev )
                    tool_shed = suc.clean_tool_shed_url( tool_shed_url )
                    # Update the repository metadata.
                    metadata_dict, invalid_file_tups = suc.generate_metadata_for_changeset_revision( app=trans.app,
                                                                                                     repository=repository,
                                                                                                     repository_clone_url=repository_clone_url,
                                                                                                     shed_config_dict = repository.get_shed_config_dict( trans.app ),
                                                                                                     relative_install_dir=relative_install_dir,
                                                                                                     repository_files_dir=None,
                                                                                                     resetting_all_metadata_on_repository=False,
                                                                                                     updating_installed_repository=True,
                                                                                                     persist=True )
                    repository.metadata = metadata_dict
                    # Update the repository changeset_revision in the database.
                    repository.changeset_revision = latest_changeset_revision
                    repository.ctx_rev = latest_ctx_rev
                    repository.update_available = False
                    trans.sa_session.add( repository )
                    trans.sa_session.flush()
                    if 'tools' in metadata_dict:
                        tool_panel_dict = metadata_dict.get( 'tool_panel_section', None )
                        if tool_panel_dict is None:
                            tool_panel_dict = suc.generate_tool_panel_dict_from_shed_tool_conf_entries( trans.app, repository )
                        repository_tools_tups = suc.get_repository_tools_tups( trans.app, metadata_dict )
                        shed_util.add_to_tool_panel( app=trans.app,
                                                     repository_name=repository.name,
                                                     repository_clone_url=repository_clone_url,
                                                     changeset_revision=repository.installed_changeset_revision,
                                                     repository_tools_tups=repository_tools_tups,
                                                     owner=repository.owner,
                                                     shed_tool_conf=shed_tool_conf,
                                                     tool_panel_dict=tool_panel_dict,
                                                     new_install=False )
                    # Create tool_dependency records if necessary.
                    if 'tool_dependencies' in metadata_dict:
                        tool_dependencies = shed_util.create_tool_dependency_objects( trans.app, repository, relative_install_dir, set_status=False )
                    message = "The installed repository named '%s' has been updated to change set revision '%s'.  " % ( name, latest_changeset_revision )
                    # See if any tool dependencies can be installed.
                    shed_tool_conf, tool_path, relative_install_dir = suc.get_tool_panel_config_tool_path_install_dir( trans.app, repository )
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
    def view_tool_metadata( self, trans, repository_id, tool_id, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
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

## ---- Utility methods -------------------------------------------------------

def build_shed_tool_conf_select_field( trans ):
    """Build a SelectField whose options are the keys in trans.app.toolbox.shed_tool_confs."""
    options = []
    for shed_tool_conf_dict in trans.app.toolbox.shed_tool_confs:
        shed_tool_conf_filename = shed_tool_conf_dict[ 'config_filename' ]
        if shed_tool_conf_filename != trans.app.config.migrated_tools_config:
            if shed_tool_conf_filename.startswith( './' ):
                option_label = shed_tool_conf_filename.replace( './', '', 1 )
            else:
                option_label = shed_tool_conf_filename
            options.append( ( option_label, shed_tool_conf_filename ) )
    select_field = SelectField( name='shed_tool_conf' )
    for option_tup in options:
        select_field.add_option( option_tup[0], option_tup[1] )
    return select_field
def build_tool_panel_section_select_field( trans ):
    """Build a SelectField whose options are the sections of the current in-memory toolbox."""
    options = []
    for k, v in trans.app.toolbox.tool_panel.items():
        if isinstance( v, tools.ToolSection ):
            options.append( ( v.name, v.id ) )
    select_field = SelectField( name='tool_panel_section', display='radio' )
    for option_tup in options:
        select_field.add_option( option_tup[0], option_tup[1] )
    return select_field
def get_tool_dependency( trans, id ):
    """Get a tool_dependency from the database via id"""
    return trans.sa_session.query( trans.model.ToolDependency ).get( trans.security.decode_id( id ) )
def have_shed_tool_conf_for_install( trans ):
    if not trans.app.toolbox.shed_tool_confs:
        return False
    migrated_tools_conf_path, migrated_tools_conf_name = os.path.split( trans.app.config.migrated_tools_config )
    for shed_tool_conf_dict in trans.app.toolbox.shed_tool_confs:
        shed_tool_conf = shed_tool_conf_dict[ 'config_filename' ]
        shed_tool_conf_path, shed_tool_conf_name = os.path.split( shed_tool_conf )
        if shed_tool_conf_name != migrated_tools_conf_name:
            return True
    return False
