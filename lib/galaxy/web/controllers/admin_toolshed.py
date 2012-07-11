import urllib2
from galaxy.web.controllers.admin import *
from galaxy.util.json import from_json_string, to_json_string
from galaxy.util.shed_util import *
from galaxy.tool_shed.tool_dependencies.install_util import get_tool_dependency_install_dir
from galaxy.tool_shed.encoding_util import *
from galaxy import eggs, tools

eggs.require( 'mercurial' )
from mercurial import hg, ui, commands

log = logging.getLogger( __name__ )

MAX_CONTENT_SIZE = 32768

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
    # Grid definition
    title = "Installed tool shed repositories"
    model_class = model.ToolShedRepository
    template='/admin/tool_shed_repository/grid.mako'
    default_sort_key = "name"
    columns = [
        NameColumn( "Name",
                    key="name",
                    link=( lambda item: dict( operation="manage_repository", id=item.id, webapp="galaxy" ) ),
                    attach_popup=True ),
        DescriptionColumn( "Description" ),
        OwnerColumn( "Owner" ),
        RevisionColumn( "Revision" ),
        StatusColumn( "Installation Status",
                      filterable="advanced" ),
        ToolShedColumn( "Tool shed" ),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn( "Deleted",
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
                                        condition=( lambda item: not item.deleted ),
                                        async_compatible=False,
                                        url_args=dict( controller='admin_toolshed', action='browse_repositories', operation='get updates' ) ),
                   grids.GridOperation( "Deactivate or uninstall",
                                        allow_multiple=False,
                                        condition=( lambda item: not item.deleted ),
                                        async_compatible=False,
                                        url_args=dict( controller='admin_toolshed', action='browse_repositories', operation='deactivate or uninstall' ) ),
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
        tool_dependency_ids = get_tool_dependency_ids( as_string=False, **kwd )
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
        repository = get_repository( trans, kwd[ 'id' ] )
        shed_tool_conf, tool_path, relative_install_dir = get_tool_panel_config_tool_path_install_dir( trans.app, repository )
        repository_clone_url = self.__generate_clone_url( trans, repository )
        repository.deleted = False
        repository.status = trans.model.ToolShedRepository.installation_status.INSTALLED
        trans.sa_session.add( repository )
        trans.sa_session.flush()
        if repository.includes_tools:
            metadata = repository.metadata
            repository_tools_tups = get_repository_tools_tups( trans.app, metadata )
            # Reload tools into the appropriate tool panel section.
            tool_panel_dict = repository.metadata[ 'tool_panel_section' ]
            add_to_tool_panel( trans.app,
                               repository.name,
                               repository_clone_url,
                               repository.changeset_revision,
                               repository_tools_tups,
                               repository.owner,
                               shed_tool_conf,
                               tool_panel_dict,
                               new_install=False )
        if repository.includes_datatypes:
            repository_install_dir = os.path.abspath ( relative_install_dir )
            # Deactivate proprietary datatypes.
            installed_repository_dict = load_installed_datatypes( trans.app, repository, repository_install_dir, deactivate=False )
            if installed_repository_dict and 'converter_path' in installed_repository_dict:
                load_installed_datatype_converters( trans.app, installed_repository_dict, deactivate=False )
            if installed_repository_dict and 'display_path' in installed_repository_dict:
                load_installed_display_applications( trans.app, installed_repository_dict, deactivate=False )
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
        repository = get_repository( trans, kwd[ 'id' ] )
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
                return self.manage_repository( trans, **kwd )
            if operation == "get updates":
                return self.check_for_updates( trans, **kwd )
            if operation == "activate or reinstall":
                repository = get_repository( trans, kwd[ 'id' ] )
                if repository.uninstalled:
                    if repository.includes_tools:
                        # Only allow selecting a different section in the tool panel if the repository was uninstalled.
                        return self.reselect_tool_panel_section( trans, **kwd )
                    else:
                        return self.reinstall_repository( trans, **kwd )
                else:
                    return self.activate_repository( trans, **kwd )
            if operation == "deactivate or uninstall":
                return self.deactivate_or_uninstall_repository( trans, **kwd )
        if 'message' not in kwd or not kwd[ 'message' ]:
            kwd[ 'message' ] = 'Names of repositories for which updates are available are highlighted in yellow.'
        return self.installed_repository_grid( trans, **kwd )
    @web.expose
    @web.require_admin
    def browse_tool_dependency( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        tool_dependency = get_tool_dependency( trans, kwd[ 'id' ] )
        return trans.fill_template( '/admin/tool_shed_repository/browse_tool_dependency.mako',
                                    repository=tool_dependency.tool_shed_repository,
                                    tool_dependency=tool_dependency,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def browse_tool_shed( self, trans, **kwd ):
        tool_shed_url = kwd[ 'tool_shed_url' ]
        galaxy_url = url_for( '/', qualified=True )
        url = '%srepository/browse_valid_categories?galaxy_url=%s&webapp=galaxy&no_reset=true' % ( tool_shed_url, galaxy_url )
        return trans.response.send_redirect( url )
    @web.expose
    @web.require_admin
    def browse_tool_sheds( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        return trans.fill_template( '/webapps/galaxy/admin/tool_sheds.mako',
                                    webapp='galaxy',
                                    message=message,
                                    status='error' )
    @web.expose
    @web.require_admin
    def check_for_updates( self, trans, **kwd ):
        # Send a request to the relevant tool shed to see if there are any updates.
        repository = get_repository( trans, kwd[ 'id' ] )
        tool_shed_url = get_url_from_repository_tool_shed( trans.app, repository )
        url = '%s/repository/check_for_updates?galaxy_url=%s&name=%s&owner=%s&changeset_revision=%s&webapp=galaxy&no_reset=true' % \
            ( tool_shed_url, url_for( '/', qualified=True ), repository.name, repository.owner, repository.changeset_revision )
        return trans.response.send_redirect( url )
    @web.expose
    @web.require_admin
    def deactivate_or_uninstall_repository( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        remove_from_disk = params.get( 'remove_from_disk', '' )
        remove_from_disk_checked = CheckboxField.is_checked( remove_from_disk )
        tool_shed_repository = get_repository( trans, kwd[ 'id' ] )
        shed_tool_conf, tool_path, relative_install_dir = get_tool_panel_config_tool_path_install_dir( trans.app, tool_shed_repository )
        repository_install_dir = os.path.abspath ( relative_install_dir )
        errors = ''
        if params.get( 'deactivate_or_uninstall_repository_button', False ):
            if tool_shed_repository.includes_tools:
                # Handle tool panel alterations.
                remove_from_tool_panel( trans, tool_shed_repository, shed_tool_conf, uninstall=remove_from_disk_checked )
            if tool_shed_repository.includes_datatypes:
                # Deactivate proprietary datatypes.
                installed_repository_dict = load_installed_datatypes( trans.app, tool_shed_repository, repository_install_dir, deactivate=True )
                if installed_repository_dict and 'converter_path' in installed_repository_dict:
                    load_installed_datatype_converters( trans.app, installed_repository_dict, deactivate=True )
                if installed_repository_dict and 'display_path' in installed_repository_dict:
                    load_installed_display_applications( trans.app, installed_repository_dict, deactivate=True )
            if remove_from_disk_checked:
                try:
                    # Remove the repository from disk.
                    shutil.rmtree( repository_install_dir )
                    log.debug( "Removed repository installation directory: %s" % str( repository_install_dir ) )
                    removed = True
                except Exception, e:
                    log.debug( "Error removing repository installation directory %s: %s" % ( str( repository_install_dir ), str( e ) ) )
                    removed = False
                if removed:
                    tool_shed_repository.uninstalled = True
                    # Remove all installed tool dependencies.
                    for tool_dependency in tool_shed_repository.installed_tool_dependencies:
                        uninstalled, error_message = remove_tool_dependency( trans, tool_dependency )
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
        url = '%srepository/find_tools?galaxy_url=%s&webapp=galaxy&no_reset=true' % ( tool_shed_url, galaxy_url )
        return trans.response.send_redirect( url )
    @web.expose
    @web.require_admin
    def find_workflows_in_tool_shed( self, trans, **kwd ):
        tool_shed_url = kwd[ 'tool_shed_url' ]
        galaxy_url = url_for( '/', qualified=True )
        url = '%srepository/find_workflows?galaxy_url=%s&webapp=galaxy&no_reset=true' % ( tool_shed_url, galaxy_url )
        return trans.response.send_redirect( url )
    def generate_tool_path( self, repository_clone_url, changeset_revision ):
        """
        Generate a tool path that guarantees repositories with the same name will always be installed
        in different directories.  The tool path will be of the form:
        <tool shed url>/repos/<repository owner>/<repository name>/<installed changeset revision>
        http://test@bx.psu.edu:9009/repos/test/filter
        """
        tmp_url = clean_repository_clone_url( repository_clone_url )
        # Now tmp_url is something like: bx.psu.edu:9009/repos/some_username/column
        items = tmp_url.split( 'repos' )
        tool_shed_url = items[ 0 ]
        repo_path = items[ 1 ]
        tool_shed_url = clean_tool_shed_url( tool_shed_url )
        return '%s/repos%s/%s' % ( tool_shed_url, repo_path, changeset_revision )
    @web.json
    @web.require_admin
    def get_file_contents( self, trans, file_path ):
        # Avoid caching
        trans.response.headers['Pragma'] = 'no-cache'
        trans.response.headers['Expires'] = '0'
        return get_repository_file_contents( file_path )
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
        work_dir = make_tmp_directory()
        # Get the tool_dependencies.xml file from the repository.
        tool_dependencies_config = get_config_from_repository( trans.app,
                                                               'tool_dependencies.xml',
                                                               tool_shed_repository,
                                                               tool_shed_repository.changeset_revision,
                                                               work_dir )
        installed_tool_dependencies = handle_tool_dependencies( app=trans.app,
                                                                tool_shed_repository=tool_shed_repository,
                                                                tool_dependencies_config=tool_dependencies_config,
                                                                tool_dependencies=tool_dependencies )
        for installed_tool_dependency in installed_tool_dependencies:
            if installed_tool_dependency.status == trans.app.model.ToolDependency.installation_status.ERROR:
                message += '  %s' % installed_tool_dependency.error_message
        try:
            shutil.rmtree( work_dir )
        except:
            pass
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
            tool_dependency = get_tool_dependency( trans, tool_dependency_id )
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
            # Clone each repository to the configured location.
            update_tool_shed_repository_status( trans.app, tool_shed_repository, trans.model.ToolShedRepository.installation_status.CLONING )
            repo_info_tuple = repo_info_dict[ tool_shed_repository.name ]
            description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, tool_dependencies = repo_info_tuple
            clone_dir = os.path.join( tool_path, self.generate_tool_path( repository_clone_url, tool_shed_repository.installed_changeset_revision ) )
            relative_install_dir = os.path.join( clone_dir, tool_shed_repository.name )
            clone_repository( repository_clone_url, os.path.abspath( relative_install_dir ), ctx_rev )
            if reinstalling:
                # Since we're reinstalling the repository we need to find the latest changeset revision to which is can be updated.
                current_changeset_revision, current_ctx_rev = get_update_to_changeset_revision_and_ctx_rev( trans, tool_shed_repository )
                if current_ctx_rev != ctx_rev:
                    repo = hg.repository( get_configured_ui(), path=os.path.abspath( relative_install_dir ) )
                    pull_repository( repo, repository_clone_url, current_changeset_revision )
                    update_repository( repo, ctx_rev=current_ctx_rev )
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
                update_tool_shed_repository_status( trans.app,
                                                    tool_shed_repository,
                                                    trans.model.ToolShedRepository.installation_status.SETTING_TOOL_VERSIONS )
                tool_shed_url = get_url_from_repository_tool_shed( trans.app, tool_shed_repository )
                url = '%s/repository/get_tool_versions?name=%s&owner=%s&changeset_revision=%s&webapp=galaxy&no_reset=true' % \
                    ( tool_shed_url, tool_shed_repository.name, tool_shed_repository.owner, tool_shed_repository.changeset_revision )
                response = urllib2.urlopen( url )
                text = response.read()
                response.close()
                if text:
                    tool_version_dicts = from_json_string( text )
                    handle_tool_versions( trans.app, tool_version_dicts, tool_shed_repository )
                else:
                    message += "Version information for the tools included in the <b>%s</b> repository is missing.  " % name
                    message += "Reset all of this repository's metadata in the tool shed, then set the installed tool versions "
                    message += "from the installed repository's <b>Repository Actions</b> menu.  "
                    status = 'error'
            if install_tool_dependencies and tool_shed_repository.tool_dependencies and 'tool_dependencies' in metadata:
                work_dir = make_tmp_directory()
                # Install tool dependencies.
                update_tool_shed_repository_status( trans.app,
                                                    tool_shed_repository,
                                                    trans.model.ToolShedRepository.installation_status.INSTALLING_TOOL_DEPENDENCIES )
                # Get the tool_dependencies.xml file from the repository.
                tool_dependencies_config = get_config_from_repository( trans.app,
                                                                       'tool_dependencies.xml',
                                                                       tool_shed_repository,
                                                                       tool_shed_repository.installed_changeset_revision,
                                                                       work_dir )
                installed_tool_dependencies = handle_tool_dependencies( app=trans.app,
                                                                        tool_shed_repository=tool_shed_repository,
                                                                        tool_dependencies_config=tool_dependencies_config,
                                                                        tool_dependencies=tool_shed_repository.tool_dependencies )
                try:
                    shutil.rmtree( work_dir )
                except:
                    pass
            update_tool_shed_repository_status( trans.app, tool_shed_repository, trans.model.ToolShedRepository.installation_status.INSTALLED )
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
        metadata_dict = generate_metadata_using_disk_files( trans.app.toolbox, relative_install_dir, repository_clone_url )
        tool_shed_repository.metadata = metadata_dict
        trans.sa_session.add( tool_shed_repository )
        trans.sa_session.flush()
        if 'tool_dependencies' in metadata_dict and not reinstalling:
            tool_dependencies = create_tool_dependency_objects( trans.app, tool_shed_repository, tool_shed_repository.installed_changeset_revision )
        if 'tools' in metadata_dict:
            tool_panel_dict = generate_tool_panel_dict_for_new_install( metadata_dict[ 'tools' ], tool_section )
            repository_tools_tups = get_repository_tools_tups( trans.app, metadata_dict )
            if repository_tools_tups:
                # Handle missing data table entries for tool parameters that are dynamically generated select lists.
                work_dir = make_tmp_directory()
                repository_tools_tups = handle_missing_data_table_entry( trans.app,
                                                                         tool_shed_repository,
                                                                         tool_shed_repository.changeset_revision,
                                                                         tool_path,
                                                                         repository_tools_tups,
                                                                         work_dir )
                # Handle missing index files for tool parameters that are dynamically generated select lists.
                sample_files = metadata_dict.get( 'sample_files', [] )
                repository_tools_tups, sample_files_copied = handle_missing_index_file( trans.app, tool_path, sample_files, repository_tools_tups )
                # Copy remaining sample files included in the repository to the ~/tool-data directory of the local Galaxy instance.
                copy_sample_files( trans.app, sample_files, sample_files_copied=sample_files_copied )
                add_to_tool_panel( app=trans.app,
                                   repository_name=tool_shed_repository.name,
                                   repository_clone_url=repository_clone_url,
                                   changeset_revision=tool_shed_repository.changeset_revision,
                                   repository_tools_tups=repository_tools_tups,
                                   owner=tool_shed_repository.owner,
                                   shed_tool_conf=shed_tool_conf,
                                   tool_panel_dict=tool_panel_dict,
                                   new_install=True )
                try:
                    shutil.rmtree( work_dir )
                except:
                    pass
        if 'datatypes' in metadata_dict:
            tool_shed_repository.status = trans.model.ToolShedRepository.installation_status.LOADING_PROPRIETARY_DATATYPES
            if not tool_shed_repository.includes_datatypes:
                tool_shed_repository.includes_datatypes = True
            trans.sa_session.add( tool_shed_repository )
            trans.sa_session.flush()
            work_dir = make_tmp_directory()
            datatypes_config = get_config_from_repository( trans.app,
                                                           'datatypes_conf.xml',
                                                           tool_shed_repository,
                                                           tool_shed_repository.changeset_revision,
                                                           work_dir )
            # Load data types required by tools.
            converter_path, display_path = alter_config_and_load_prorietary_datatypes( trans.app, datatypes_config, relative_install_dir, override=False )
            if converter_path or display_path:
                # Create a dictionary of tool shed repository related information.
                repository_dict = create_repository_dict_for_proprietary_datatypes( tool_shed=tool_shed,
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
            try:
                shutil.rmtree( work_dir )
            except:
                pass
    @web.expose
    @web.require_admin
    def manage_repository( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        repository_id = kwd[ 'id' ]
        repository = get_repository( trans, repository_id )
        if repository.status in [ trans.model.ToolShedRepository.installation_status.NEW,
                                  trans.model.ToolShedRepository.installation_status.CLONING ]:
            message = "The repository '%s' is not yet cloned, please try again..."
            status = 'warning'
            return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                              action='monitor_repository_installation',
                                                              **kwd ) )
        description = util.restore_text( params.get( 'description', repository.description ) )
        shed_tool_conf, tool_path, relative_install_dir = get_tool_panel_config_tool_path_install_dir( trans.app, repository )
        repo_files_dir = os.path.abspath( os.path.join( relative_install_dir, repository.name ) )
        if params.get( 'edit_repository_button', False ):
            if description != repository.description:
                repository.description = description
                trans.sa_session.add( repository )
                trans.sa_session.flush()
            message = "The repository information has been updated."
        elif params.get( 'set_metadata_button', False ):
            repository_clone_url = generate_clone_url( trans, repository )
            metadata_dict = generate_metadata_using_disk_files( trans.app.toolbox, relative_install_dir, repository_clone_url )
            if metadata_dict:
                repository.metadata = metadata_dict
                trans.sa_session.add( repository )
                trans.sa_session.flush()
            message = "Repository metadata has been reset."
        return trans.fill_template( '/admin/tool_shed_repository/manage_repository.mako',
                                    repository=repository,
                                    description=description,
                                    repo_files_dir=repo_files_dir,
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
                decoded_kwd = tool_shed_decode( encoded_kwd )
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
        tool_dependency_ids = get_tool_dependency_ids( as_string=False, **kwd )
        # We need a tool_shed_repository, so get it from one of the tool_dependencies.
        tool_dependency = get_tool_dependency( trans, tool_dependency_ids[ 0 ] )
        tool_shed_repository = tool_dependency.tool_shed_repository
        self.tool_dependency_grid.title = "Tool shed repository '%s' tool dependencies"  % tool_shed_repository.name
        self.tool_dependency_grid.global_actions = \
            [ grids.GridAction( label='Browse repository', 
                                url_args=dict( controller='admin_toolshed', 
                                               action='browse_repository', 
                                               id=trans.security.encode_id( tool_shed_repository.id ) ) ),
              grids.GridAction( label='Manage repository', 
                                url_args=dict( controller='admin_toolshed', 
                                               action='manage_repository', 
                                               id=trans.security.encode_id( tool_shed_repository.id ) ) ),
              grids.GridAction( label='Get updates', 
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
                    tool_dependency = get_tool_dependency( trans, tool_dependency_id )
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
                tool_dependencies_for_installation = []
                for tool_dependency_id in tool_dependency_ids:
                    tool_dependency = get_tool_dependency( trans, tool_dependency_id )
                    if tool_dependency.status in [ trans.model.ToolDependency.installation_status.NEVER_INSTALLED,
                                                   trans.model.ToolDependency.installation_status.UNINSTALLED ]:
                        tool_dependencies_for_installation.append( tool_dependency )
                if tool_dependencies_for_installation:
                    self.initiate_tool_dependency_installation( trans, tool_dependencies_for_installation )
                else:
                    kwd[ 'message' ] = 'All selected tool dependencies are already installed.'
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
        return open_repository_files_folder( trans, folder_path )
    @web.expose
    @web.require_admin
    def prepare_for_install( self, trans, **kwd ):
        if not trans.app.toolbox.shed_tool_confs:
            message = 'The <b>tool_config_file</b> setting in <b>universe_wsgi.ini</b> must include at least one shed tool configuration file name with a '
            message += '<b>&lt;toolbox&gt;</b> tag that includes a <b>tool_path</b> attribute value which is a directory relative to the Galaxy installation '
            message += 'directory in order to automatically install tools from a Galaxy tool shed (e.g., the file name <b>shed_tool_conf.xml</b> whose '
            message += '<b>&lt;toolbox&gt;</b> tag is <b>&lt;toolbox tool_path="../shed_tools"&gt;</b>).<p/>See the '
            message += '<a href="http://wiki.g2.bx.psu.edu/Tool%20Shed#Automatic_installation_of_Galaxy_tool_shed_repository_tools_into_a_local_Galaxy_instance" '
            message += 'target="_blank">Automatic installation of Galaxy tool shed repository tools into a local Galaxy instance</a> section of the '
            message += '<a href="http://wiki.g2.bx.psu.edu/Tool%20Shed" target="_blank">Galaxy tool shed wiki</a> for all of the details.'
            return trans.show_error_message( message )
        message = kwd.get( 'message', ''  )
        status = kwd.get( 'status', 'done' )
        includes_tools = util.string_as_bool( kwd.get( 'includes_tools', False ) )
        tool_shed_url = kwd[ 'tool_shed_url' ]
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
            url = '%srepository/get_repository_information?repository_ids=%s&changeset_revisions=%s&webapp=galaxy' % ( tool_shed_url, repository_ids, changeset_revisions )
            response = urllib2.urlopen( url )
            raw_text = response.read()
            response.close()
            repo_information_dict = from_json_string( raw_text )
            includes_tools = util.string_as_bool( repo_information_dict[ 'includes_tools' ] )
            includes_tool_dependencies = util.string_as_bool( repo_information_dict[ 'includes_tool_dependencies' ] )
            encoded_repo_info_dicts = util.listify( repo_information_dict[ 'repo_info_dicts' ] )
        repo_info_dicts = [ tool_shed_decode( encoded_repo_info_dict ) for encoded_repo_info_dict in encoded_repo_info_dicts ]
        if not includes_tools or ( includes_tools and kwd.get( 'select_tool_panel_section_button', False ) ):
            if includes_tools:
                install_tool_dependencies = CheckboxField.is_checked( install_tool_dependencies )
                shed_tool_conf = kwd[ 'shed_tool_conf' ]
            else:
                install_tool_dependencies = False
                # If installing a repository that includes no tools, get the relative tool_path from the file to which the
                # migrated_tools_config setting points.
                shed_tool_conf = trans.app.config.migrated_tools_config
            # Get the tool path by searching the list of shed_tool_confs for the dictionary that contains the information about shed_tool_conf.
            for shed_tool_conf_dict in trans.app.toolbox.shed_tool_confs:
                config_filename = shed_tool_conf_dict[ 'config_filename' ]
                if config_filename == shed_tool_conf:
                    tool_path = shed_tool_conf_dict[ 'tool_path' ]
                    break
                else:
                    file_name = strip_path( config_filename )
                    if file_name == shed_tool_conf:
                        tool_path = shed_tool_conf_dict[ 'tool_path' ]
                        break
            # Make sure all tool_shed_repository records exist.
            created_or_updated_tool_shed_repositories = []
            # Repositories will be filtered (e.g., if already installed, etc), so filter the associated repo_info_dicts accordingly.
            filtered_repo_info_dicts = []
            for repo_info_dict in repo_info_dicts:
                for name, repo_info_tuple in repo_info_dict.items():
                    description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, tool_dependencies = repo_info_tuple
                    clone_dir = os.path.join( tool_path, self.generate_tool_path( repository_clone_url, changeset_revision ) )
                    relative_install_dir = os.path.join( clone_dir, name )
                    owner = get_repository_owner( clean_repository_clone_url( repository_clone_url ) )
                    # Make sure the repository was not already installed.
                    installed_tool_shed_repository, installed_changeset_revision = self.repository_was_previously_installed( trans,
                                                                                                                             tool_shed_url,
                                                                                                                             name,
                                                                                                                             repo_info_tuple,
                                                                                                                             clone_dir )
                    if installed_tool_shed_repository:
                        message += "The tool shed repository <b>%s</b> with owner <b>%s</b> and changeset revision <b>%s</b> " % ( name, owner, changeset_revision )
                        if installed_changeset_revision != changeset_revision:
                            message += "was previously installed using changeset revision <b>%s</b>.  " % installed_changeset_revision
                        else:
                            message += "was previously installed.  "
                        if installed_tool_shed_repository.uninstalled:
                            message += "The repository has been uninstalled, however, so reinstall the original repository instead of installing it again.  "
                        elif installed_tool_shed_repository.deleted:
                            message += "The repository has been deactivated, however, so activate the original repository instead of installing it again.  "
                        if installed_changeset_revision != changeset_revision:
                            message += "You can get the latest updates for the repository using the <b>Get updates</b> option from the repository's "
                            message += "<b>Repository Actions</b> pop-up menu.  "
                        status = 'error'
                        if len( repo_info_dicts ) == 1:
                            new_kwd = dict( message=message, status=status )
                            return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                              action='browse_repositories',
                                                                              **new_kwd ) )
                    else:
                        print "Adding new row (or updating an existing row) for repository '%s' in the tool_shed_repository table." % name
                        tool_shed_repository = create_or_update_tool_shed_repository( app=trans.app,
                                                                                      name=name,
                                                                                      description=description,
                                                                                      installed_changeset_revision=changeset_revision,
                                                                                      ctx_rev=ctx_rev,
                                                                                      repository_clone_url=repository_clone_url,
                                                                                      metadata_dict={},
                                                                                      status=trans.model.ToolShedRepository.installation_status.NEW,
                                                                                      current_changeset_revision=changeset_revision,
                                                                                      owner=owner,
                                                                                      dist_to_shed=False )
                        created_or_updated_tool_shed_repositories.append( tool_shed_repository )
                        filtered_repo_info_dicts.append( repo_info_dict )
            if created_or_updated_tool_shed_repositories:
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
                encoded_kwd = tool_shed_encode( new_kwd )
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
        if includes_tools and len( repo_info_dicts ) == 1:
            # If we're installing a single repository, see if it contains a readme file tha twe can display.
            repo_info_dict = repo_info_dicts[ 0 ]
            name = repo_info_dict.keys()[ 0 ]
            repo_info_tuple = repo_info_dict[ name ]
            description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, tool_dependencies = repo_info_tuple
            url = '%srepository/get_readme?name=%s&owner=%s&changeset_revision=%s&webapp=galaxy&no_reset=true' % \
                ( tool_shed_url, name, repository_owner, changeset_revision )
            response = urllib2.urlopen( url )
            raw_text = response.read()
            response.close()
            readme_text = ''
            for i, line in enumerate( raw_text ):
                readme_text = '%s%s' % ( readme_text, to_html_str( line ) )
                if len( readme_text ) > MAX_CONTENT_SIZE:
                    large_str = '\nFile contents truncated because file size is larger than maximum viewing size of %s\n' % util.nice_size( MAX_CONTENT_SIZE )
                    readme_text = '%s%s' % ( readme_text, to_html_str( large_str ) )
                    break
        else:
            readme_text = '' 
        install_tool_dependencies_check_box = CheckboxField( 'install_tool_dependencies', checked=True )
        return trans.fill_template( '/admin/tool_shed_repository/select_tool_panel_section.mako',
                                    encoded_repo_info_dicts=encoded_repo_info_dicts,
                                    includes_tools=includes_tools,
                                    includes_tool_dependencies=includes_tool_dependencies,
                                    install_tool_dependencies_check_box=install_tool_dependencies_check_box,
                                    new_tool_panel_section=new_tool_panel_section,
                                    repo_info_dicts=repo_info_dicts,
                                    shed_tool_conf=shed_tool_conf,
                                    shed_tool_conf_select_field=shed_tool_conf_select_field,
                                    tool_panel_section_select_field=tool_panel_section_select_field,
                                    tool_shed_url=kwd[ 'tool_shed_url' ],
                                    readme_text=readme_text,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def reinstall_repository( self, trans, **kwd ):
        message = kwd.get( 'message', '' )
        status = kwd.get( 'status', 'done' )
        repository_id = kwd[ 'id' ]
        tool_shed_repository = get_repository( trans, repository_id )
        no_changes = kwd.get( 'no_changes', '' )
        no_changes_checked = CheckboxField.is_checked( no_changes )
        install_tool_dependencies = CheckboxField.is_checked( kwd.get( 'install_tool_dependencies', '' ) )
        new_tool_panel_section = kwd.get( 'new_tool_panel_section', '' )
        tool_panel_section = kwd.get( 'tool_panel_section', '' )
        shed_tool_conf, tool_path, relative_install_dir = get_tool_panel_config_tool_path_install_dir( trans.app, tool_shed_repository )
        repository_clone_url = generate_clone_url( trans, tool_shed_repository )
        clone_dir = os.path.join( tool_path, self.generate_tool_path( repository_clone_url, tool_shed_repository.installed_changeset_revision ) )
        relative_install_dir = os.path.join( clone_dir, tool_shed_repository.name )
        tool_shed_url = get_url_from_repository_tool_shed( trans.app, tool_shed_repository )
        tool_section = None
        tool_panel_section_key = None
        metadata = tool_shed_repository.metadata
        if tool_shed_repository.includes_tools:
            # Get the location in the tool panel in which each tool was originally loaded.
            if 'tool_panel_section' in metadata:
                tool_panel_dict = metadata[ 'tool_panel_section' ]
                if not tool_panel_dict:
                    tool_panel_dict = generate_tool_panel_dict_for_new_install( metadata[ 'tools' ] )
            else:
                tool_panel_dict = generate_tool_panel_dict_for_new_install( metadata[ 'tools' ] )
            # TODO: Fix this to handle the case where the tools are distributed across in more than 1 ToolSection.  The
            # following assumes everything was loaded into 1 section (or no section) in the tool panel.
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
        tool_shed_repository = create_or_update_tool_shed_repository( trans.app,
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
        ctx_rev = get_ctx_rev( tool_shed_url, tool_shed_repository.name, tool_shed_repository.owner, tool_shed_repository.installed_changeset_revision )
        repo_info_dict = kwd.get( 'repo_info_dict', None )
        if not repo_info_dict:
            # This should only happen if the tool_shed_repository does not include any valid tools.
            repo_info_dict = create_repo_info_dict( tool_shed_repository,
                                                    tool_shed_repository.owner,
                                                    repository_clone_url,
                                                    tool_shed_repository.installed_changeset_revision,
                                                    ctx_rev,
                                                    metadata )
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
                        tool_shed_repository_ids=[ repository_id ],
                        tool_shed_url=tool_shed_url )
        encoded_kwd = tool_shed_encode( new_kwd )
        return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                          action='initiate_repository_installation',
                                                          shed_repository_ids=repository_id,
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
    def repository_was_previously_installed( self, trans, tool_shed_url, repository_name, repo_info_tuple, clone_dir ):
        # Handle case where the repository was previously installed using an older changeset_revsion, but later the repository was updated
        # in the tool shed and now we're trying to install the latest changeset revision of the same repository instead of updating the one
        # that was previously installed.  We'll look in the database instead of on disk since the repository may be uninstalled.
        description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, tool_dependencies = repo_info_tuple
        tool_shed = get_tool_shed_from_clone_url( repository_clone_url )
        # Get all previous change set revisions from the tool shed for the repository back to, but excluding, the previous valid changeset
        # revision to see if it was previously installed using one of them.
        url = '%s/repository/previous_changeset_revisions?galaxy_url=%s&name=%s&owner=%s&changeset_revision=%s&webapp=galaxy&no_reset=true' % \
            ( tool_shed_url, url_for( '/', qualified=True ), repository_name, repository_owner, changeset_revision )
        response = urllib2.urlopen( url )
        text = response.read()
        response.close()
        if text:
            #clone_path, clone_directory = os.path.split( clone_dir )
            changeset_revisions = util.listify( text )
            for previous_changeset_revision in changeset_revisions:
                tool_shed_repository = get_tool_shed_repository_by_shed_name_owner_installed_changeset_revision( trans.app,
                                                                                                                 tool_shed,
                                                                                                                 repository_name,
                                                                                                                 repository_owner,
                                                                                                                 previous_changeset_revision )
                if tool_shed_repository and tool_shed_repository.status not in [ trans.model.ToolShedRepository.installation_status.NEW ]:
                    return tool_shed_repository, previous_changeset_revision
        return None, None
    @web.expose
    @web.require_admin
    def reselect_tool_panel_section( self, trans, **kwd ):
        repository = get_repository( trans, kwd[ 'id' ] )
        metadata = repository.metadata
        tool_shed_url = get_url_from_repository_tool_shed( trans.app, repository )
        ctx_rev = get_ctx_rev( tool_shed_url, repository.name, repository.owner, repository.installed_changeset_revision )
        repository_clone_url = generate_clone_url( trans, repository )
        repo_info_dict = create_repo_info_dict( repository,
                                                repository.owner,
                                                repository_clone_url,
                                                repository.installed_changeset_revision,
                                                ctx_rev,
                                                metadata )
        # Get the location in the tool panel in which the tool was originally loaded.
        if 'tool_panel_section' in metadata:
            tool_panel_dict = metadata[ 'tool_panel_section' ]
            if tool_panel_dict:
                if panel_entry_per_tool( tool_panel_dict ):
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
            message = "The tools contained in your <b>%s</b> repository were last loaded into the tool panel section <b>%s</b>.  " \
                % ( repository.name, original_section_name )
            message += "Uncheck the <b>No changes</b> check box and select a different tool panel section to load the tools in a "
            message += "different section in the tool panel."
        else:
            message = "The tools contained in your <b>%s</b> repository were last loaded into the tool panel outside of any sections.  " % repository.name
            message += "Uncheck the <b>No changes</b> check box and select a tool panel section to load the tools into that section."
        status = 'done'
        install_tool_dependencies_check_box = CheckboxField( 'install_tool_dependencies', checked=True )
        return trans.fill_template( '/admin/tool_shed_repository/reselect_tool_panel_section.mako',
                                    repository=repository,
                                    no_changes_check_box=no_changes_check_box,
                                    original_section_name=original_section_name,
                                    install_tool_dependencies_check_box=install_tool_dependencies_check_box,
                                    tool_panel_section_select_field=tool_panel_section_select_field,
                                    repo_info_dict=tool_shed_encode( repo_info_dict ),
                                    includes_tool_dependencies=includes_tool_dependencies,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def set_tool_versions( self, trans, **kwd ):
        # Get the tool_versions from the tool shed for each tool in the installed change set.
        repository = get_repository( trans, kwd[ 'id' ] )
        tool_shed_url = get_url_from_repository_tool_shed( trans.app, repository )
        url = '%s/repository/get_tool_versions?name=%s&owner=%s&changeset_revision=%s&webapp=galaxy&no_reset=true' % \
            ( tool_shed_url, repository.name, repository.owner, repository.changeset_revision )
        response = urllib2.urlopen( url )
        text = response.read()
        response.close()
        if text:
            tool_version_dicts = from_json_string( text )
            handle_tool_versions( trans.app, tool_version_dicts, repository )
            message = "Tool versions have been set for all included tools."
            status = 'done'
        else:
            message = "Version information for the tools included in the <b>%s</b> repository is missing.  " % repository.name
            message += "Reset all of this reppository's metadata in the tool shed, then set the installed tool versions "
            message ++ "from the installed repository's <b>Repository Actions</b> menu.  "
            status = 'error'
        shed_tool_conf, tool_path, relative_install_dir = get_tool_panel_config_tool_path_install_dir( trans.app, repository )
        repo_files_dir = os.path.abspath( os.path.join( relative_install_dir, repository.name ) )
        return trans.fill_template( '/admin/tool_shed_repository/manage_repository.mako',
                                    repository=repository,
                                    description=repository.description,
                                    repo_files_dir=repo_files_dir,
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
            tool_dependency = get_tool_dependency( trans, tool_dependency_id )
            tool_dependencies.append( tool_dependency )
        if kwd.get( 'uninstall_tool_dependencies_button', False ):
            errors = False
            # Filter tool dependencies to only those that are installed.
            tool_dependencies_for_uninstallation = []
            for tool_dependency in tool_dependencies:
                if tool_dependency.status in [ trans.model.ToolDependency.installation_status.INSTALLED,
                                               trans.model.ToolDependency.installation_status.ERROR ]:
                    tool_dependencies_for_uninstallation.append( tool_dependency )
            for tool_dependency in tool_dependencies_for_uninstallation:
                uninstalled, error_message = remove_tool_dependency( trans, tool_dependency )
                if error_message:
                    errors = True
                    message = '%s  %s' % ( message, error_message )
            if errors:
                message = "Error attempting to uninstall tool dependencies: %s" % message
                status = 'error'
            else:
                message = "These tool dependencies have been uninstalled: %s" % ','.join( td.name for td in tool_dependencies_for_uninstallation )
            tool_shed_repository = tool_dependencies[ 0 ].tool_shed_repository
            td_ids = [ trans.security.encode_id( td.id ) for td in tool_shed_repository.tool_dependencies ]
            return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                              action='manage_tool_dependencies',
                                                              tool_dependency_ids=td_ids,
                                                              status=status,
                                                              message=message ) )
        return trans.fill_template( '/admin/tool_shed_repository/uninstall_tool_dependencies.mako',
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
        repository = get_tool_shed_repository_by_shed_name_owner_changeset_revision( trans.app, tool_shed_url, name, owner, changeset_revision )
        if changeset_revision and latest_changeset_revision and latest_ctx_rev:
            if changeset_revision == latest_changeset_revision:
                message = "The installed repository named '%s' is current, there are no updates available.  " % name
            else:
                shed_tool_conf, tool_path, relative_install_dir = get_tool_panel_config_tool_path_install_dir( trans.app, repository )
                if relative_install_dir:
                    repo_files_dir = os.path.abspath( os.path.join( relative_install_dir, name ) )
                    repo = hg.repository( get_configured_ui(), path=repo_files_dir )
                    repository_clone_url = os.path.join( tool_shed_url, 'repos', owner, name )
                    pull_repository( repo, repository_clone_url, latest_ctx_rev )
                    update_repository( repo, latest_ctx_rev )
                    # Update the repository metadata.
                    tool_shed = clean_tool_shed_url( tool_shed_url )
                    metadata_dict = generate_metadata_using_disk_files( trans.app.toolbox, relative_install_dir, repository_clone_url )
                    repository.metadata = metadata_dict
                    # Update the repository changeset_revision in the database.
                    repository.changeset_revision = latest_changeset_revision
                    repository.ctx_rev = latest_ctx_rev
                    repository.update_available = False
                    trans.sa_session.add( repository )
                    trans.sa_session.flush()
                    # Create tool_dependency records if necessary.
                    if 'tool_dependencies' in metadata_dict:
                        tool_dependencies = create_tool_dependency_objects( trans.app, repository, repository.changeset_revision )
                    message = "The installed repository named '%s' has been updated to change set revision '%s'.  " % ( name, latest_changeset_revision )
                    # See if any tool dependencies can be installed.
                    shed_tool_conf, tool_path, relative_install_dir = get_tool_panel_config_tool_path_install_dir( trans.app, repository )
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
        webapp = get_webapp( trans, **kwd )
        repository = get_repository( trans, repository_id )
        metadata = {}
        tool = None
        if 'tools' in repository.metadata:
            for tool_metadata_dict in repository.metadata[ 'tools' ]:
                if tool_metadata_dict[ 'id' ] == tool_id:
                    metadata = tool_metadata_dict
                    tool = trans.app.toolbox.load_tool( os.path.abspath( metadata[ 'tool_config' ] ), guid=metadata[ 'guid' ] )
                    break
        return trans.fill_template( "/admin/tool_shed_repository/view_tool_metadata.mako",
                                    repository=repository,
                                    tool=tool,
                                    metadata=metadata,
                                    message=message,
                                    status=status )
    def __generate_clone_url( self, trans, repository ):
        """Generate the URL for cloning a repository."""
        tool_shed_url = get_url_from_repository_tool_shed( trans.app, repository )
        return '%s/repos/%s/%s' % ( tool_shed_url, repository.owner, repository.name )

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
def get_repository( trans, id ):
    """Get a tool_shed_repository from the database via id"""
    return trans.sa_session.query( trans.model.ToolShedRepository ).get( trans.security.decode_id( id ) )
def get_tool_dependency( trans, id ):
    """Get a tool_dependency from the database via id"""
    return trans.sa_session.query( trans.model.ToolDependency ).get( trans.security.decode_id( id ) )
