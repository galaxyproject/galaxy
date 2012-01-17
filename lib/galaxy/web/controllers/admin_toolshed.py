from galaxy.web.controllers.admin import *
from galaxy.util.shed_util import *
from galaxy import tools

log = logging.getLogger( __name__ )

class ToolIdGuidMapGrid( grids.Grid ):
    class ToolIdColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_id_guid_map ):
            return tool_id_guid_map.tool_id
    class ToolVersionColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_id_guid_map ):
            return tool_id_guid_map.tool_version
    class ToolGuidColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_id_guid_map ):
            return tool_id_guid_map.guid
    class ToolShedColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_id_guid_map ):
            return tool_id_guid_map.tool_shed
    class RepositoryNameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_id_guid_map ):
            return tool_id_guid_map.repository_name
    class RepositoryOwnerColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_id_guid_map ):
            return tool_id_guid_map.repository_owner
    # Grid definition
    title = "Map tool id to guid"
    model_class = model.ToolIdGuidMap
    template='/admin/tool_shed_repository/grid.mako'
    default_sort_key = "tool_id"
    columns = [
        ToolIdColumn( "Tool id" ),
        ToolVersionColumn( "Version" ),
        ToolGuidColumn( "Guid" ),
        ToolShedColumn( "Tool shed" ),
        RepositoryNameColumn( "Repository name" ),
        RepositoryOwnerColumn( "Repository owner" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search repository name", 
                                                cols_to_filter=[ columns[0], columns[2], columns[4], columns[5] ],
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    global_actions = [
        grids.GridAction( "Manage installed tool shed repositories", dict( controller='admin_toolshed', action='browse_repositories' ) )
    ]
    operations = []
    standard_filters = []
    default_filter = {}
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( self.model_class )

class RepositoryListGrid( grids.Grid ):
    class NameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, tool_shed_repository ):
            if tool_shed_repository.update_available:
                return '<div class="count-box state-color-error">%s</div>' % tool_shed_repository.name
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
    global_actions = [
        grids.GridAction( "View tool id guid map", dict( controller='admin_toolshed', action='browse_tool_id_guid_map' ) )
    ]
    operations = [ grids.GridOperation( "Get updates",
                                        allow_multiple=False,
                                        condition=( lambda item: not item.deleted ),
                                        async_compatible=False ),
                   grids.GridOperation( "Deactivate or uninstall",
                                        allow_multiple=False,
                                        condition=( lambda item: not item.deleted ),
                                        async_compatible=False ),
                   grids.GridOperation( "Activate or reinstall",
                                        allow_multiple=False,
                                        condition=( lambda item: item.deleted ),
                                        async_compatible=False ) ]
    standard_filters = []
    default_filter = dict( deleted="False" )
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( self.model_class )

class AdminToolshed( AdminGalaxy ):
    
    repository_list_grid = RepositoryListGrid()
    tool_id_guid_map_grid = ToolIdGuidMapGrid()

    @web.expose
    @web.require_admin
    def browse_tool_id_guid_map( self, trans, **kwd ):
        return self.tool_id_guid_map_grid( trans, **kwd )
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
                return self.activate_or_reinstall_repository( trans, **kwd )
            if operation == "deactivate or uninstall":
                return self.deactivate_or_uninstall_repository( trans, **kwd )
        if 'message' not in kwd or not kwd[ 'message' ]:
            kwd[ 'message' ] = 'Names of repositories for which updates are available are highlighted in red.'
        return self.repository_list_grid( trans, **kwd )
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
    def find_tools_in_tool_shed( self, trans, **kwd ):
        tool_shed_url = kwd[ 'tool_shed_url' ]
        galaxy_url = url_for( '/', qualified=True )
        url = '%s/repository/find_tools?galaxy_url=%s&webapp=galaxy' % ( tool_shed_url, galaxy_url )
        return trans.response.send_redirect( url )
    @web.expose
    @web.require_admin
    def find_workflows_in_tool_shed( self, trans, **kwd ):
        tool_shed_url = kwd[ 'tool_shed_url' ]
        galaxy_url = url_for( '/', qualified=True )
        url = '%s/repository/find_workflows?galaxy_url=%s&webapp=galaxy' % ( tool_shed_url, galaxy_url )
        return trans.response.send_redirect( url )
    @web.expose
    @web.require_admin
    def browse_tool_shed( self, trans, **kwd ):
        tool_shed_url = kwd[ 'tool_shed_url' ]
        galaxy_url = url_for( '/', qualified=True )
        url = '%s/repository/browse_valid_repositories?galaxy_url=%s&webapp=galaxy' % ( tool_shed_url, galaxy_url )
        return trans.response.send_redirect( url )
    @web.expose
    @web.require_admin
    def install_repository( self, trans, **kwd ):
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
        tool_shed_url = kwd[ 'tool_shed_url' ]
        repo_info_dict = kwd[ 'repo_info_dict' ]
        new_tool_panel_section = kwd.get( 'new_tool_panel_section', '' )
        tool_panel_section = kwd.get( 'tool_panel_section', '' )
        includes_tools = util.string_as_bool( kwd.get( 'includes_tools', False ) )
        if not includes_tools or ( includes_tools and kwd.get( 'select_tool_panel_section_button', False ) ):
            if includes_tools:
                shed_tool_conf = kwd[ 'shed_tool_conf' ]
            else:
                # If installing a repository that includes no tools, get the relative
                # tool_path from the file to which the install_tool_config_file config
                # setting points.
                shed_tool_conf = trans.app.config.install_tool_config
            # Get the tool path.
            for k, tool_path in trans.app.toolbox.shed_tool_confs.items():
                if k == shed_tool_conf:
                    break
            if includes_tools and ( new_tool_panel_section or tool_panel_section ):
                if new_tool_panel_section:
                    section_id = new_tool_panel_section.lower().replace( ' ', '_' )
                    new_section_key = 'section_%s' % str( section_id )
                    if new_section_key in trans.app.toolbox.tool_panel:
                        # Appending a tool to an existing section in trans.app.toolbox.tool_panel
                        log.debug( "Appending to tool panel section: %s" % new_tool_panel_section )
                        tool_section = trans.app.toolbox.tool_panel[ new_section_key ]
                    else:
                        # Appending a new section to trans.app.toolbox.tool_panel
                        log.debug( "Loading new tool panel section: %s" % new_tool_panel_section )
                        elem = Element( 'section' )
                        elem.attrib[ 'name' ] = new_tool_panel_section
                        elem.attrib[ 'id' ] = section_id
                        elem.attrib[ 'version' ] = ''
                        tool_section = tools.ToolSection( elem )
                        trans.app.toolbox.tool_panel[ new_section_key ] = tool_section
                else:
                    section_key = 'section_%s' % tool_panel_section
                    tool_section = trans.app.toolbox.tool_panel[ section_key ]
            else:
                tool_section = None
            # Decode the encoded repo_info_dict param value.
            repo_info_dict = tool_shed_decode( repo_info_dict )
            # Clone the repository to the configured location.
            current_working_dir = os.getcwd()
            installed_repository_names = []
            for name, repo_info_tuple in repo_info_dict.items():
                description, repository_clone_url, changeset_revision = repo_info_tuple
                clone_dir = os.path.join( tool_path, self.__generate_tool_path( repository_clone_url, changeset_revision ) )
                relative_install_dir = os.path.join( clone_dir, name )
                if os.path.exists( clone_dir ):
                    # Repository and revision has already been cloned.
                    # TODO: implement the ability to re-install or revert an existing repository.
                    message += 'Revision <b>%s</b> of repository <b>%s</b> was previously installed.<br/>' % ( changeset_revision, name )
                else:
                    returncode, tmp_name = clone_repository( name, clone_dir, current_working_dir, repository_clone_url )
                    if returncode == 0:
                        returncode, tmp_name = update_repository( current_working_dir, relative_install_dir, changeset_revision )
                        if returncode == 0:
                            owner = get_repository_owner( clean_repository_clone_url( repository_clone_url ) )
                            tool_shed = clean_tool_shed_url( tool_shed_url )
                            metadata_dict = load_repository_contents( app=trans.app,
                                                                      repository_name=name,
                                                                      description=description,
                                                                      owner=owner,
                                                                      changeset_revision=changeset_revision,
                                                                      tool_path=tool_path,
                                                                      repository_clone_url=repository_clone_url,
                                                                      relative_install_dir=relative_install_dir,
                                                                      current_working_dir=current_working_dir,
                                                                      tmp_name=tmp_name,
                                                                      tool_shed=tool_shed,
                                                                      tool_section=tool_section,
                                                                      shed_tool_conf=shed_tool_conf,
                                                                      new_install=True )
                            installed_repository_names.append( name )
                        else:
                            tmp_stderr = open( tmp_name, 'rb' )
                            message += '%s<br/>' % tmp_stderr.read()
                            tmp_stderr.close()
                            status = 'error'
                    else:
                        tmp_stderr = open( tmp_name, 'rb' )
                        message += '%s<br/>' % tmp_stderr.read()
                        tmp_stderr.close()
                        status = 'error'
            if installed_repository_names:
                installed_repository_names.sort()
                num_repositories_installed = len( installed_repository_names )
                if tool_section:
                    message += 'Installed %d %s and all tools were loaded into tool panel section <b>%s</b>:<br/>Installed repositories: ' % \
                        ( num_repositories_installed, inflector.cond_plural( num_repositories_installed, 'repository' ), tool_section.name )
                else:
                    message += 'Installed %d %s and all tools were loaded into the tool panel outside of any sections.<br/>Installed repositories: ' % \
                        ( num_repositories_installed, inflector.cond_plural( num_repositories_installed, 'repository' ) )
                for i, repo_name in enumerate( installed_repository_names ):
                    if i == len( installed_repository_names ) -1:
                        message += '%s.<br/>' % repo_name
                    else:
                        message += '%s, ' % repo_name
            return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                              action='browse_repositories',
                                                              message=message,
                                                              status=status ) )
        if len( trans.app.toolbox.shed_tool_confs.keys() ) > 1:
            shed_tool_conf_select_field = build_shed_tool_conf_select_field( trans )
            shed_tool_conf = None
        else:
            shed_tool_conf = trans.app.toolbox.shed_tool_confs.keys()[0].lstrip( './' )
            shed_tool_conf_select_field = None
        tool_panel_section_select_field = build_tool_panel_section_select_field( trans )
        return trans.fill_template( '/admin/tool_shed_repository/select_tool_panel_section.mako',
                                    tool_shed_url=tool_shed_url,
                                    repo_info_dict=repo_info_dict,
                                    shed_tool_conf=shed_tool_conf,
                                    includes_tools=includes_tools,
                                    shed_tool_conf_select_field=shed_tool_conf_select_field,
                                    tool_panel_section_select_field=tool_panel_section_select_field,
                                    new_tool_panel_section=new_tool_panel_section,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def deactivate_or_uninstall_repository( self, trans, **kwd ):
        # TODO: handle elimination of workflows loaded into the tool panel that are in the repository being deactivated.
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        remove_from_disk = params.get( 'remove_from_disk', '' )
        remove_from_disk_checked = CheckboxField.is_checked( remove_from_disk )
        repository = get_repository( trans, kwd[ 'id' ] )
        if params.get( 'deactivate_or_uninstall_repository_button', False ):
            # Deatcivate repository tools.
            shed_tool_conf, tool_path, relative_install_dir = self.__get_tool_path_and_relative_install_dir( trans, repository )
            metadata = repository.metadata
            repository_tools_tups = get_repository_tools_tups( trans.app, metadata )
            # Generate the list of tool panel keys derived from the tools included in the repository.
            repository_tool_panel_keys = []
            if repository_tools_tups:
                repository_tool_panel_keys = [ 'tool_%s' % repository_tools_tup[ 1 ] for repository_tools_tup in repository_tools_tups ]
            tool_panel_section = metadata[ 'tool_panel_section' ]
            section_id = tool_panel_section[ 'id' ]
            if section_id in [ '' ]:
                # If the repository includes tools, they were loaded into the tool panel outside of any sections.
                tool_section = None
                self.__deactivate( trans, repository_tool_panel_keys )
            else:
                # If the repository includes tools, they were loaded into the tool panel inside a section.
                section_key = 'section_%s' % str( section_id )
                if section_key in trans.app.toolbox.tool_panel:
                    tool_section = trans.app.toolbox.tool_panel[ section_key ]
                    self.__deactivate( trans, repository_tool_panel_keys, tool_section=tool_section, section_key=section_key )
                else:
                    # The tool panel section could not be found, so handle deactivating tools
                    # as if they were loaded into the tool panel outside of any sections.
                    tool_section = None
                    self.__deactivate( trans, repository_tool_panel_keys )
            repository.deleted = True
            trans.sa_session.add( repository )
            trans.sa_session.flush()
            repository_clone_url = self.__generate_clone_url( trans, repository )
            load_altered_part_of_tool_panel( app=trans.app,
                                             repository_name=repository.name,
                                             repository_clone_url=repository_clone_url,
                                             changeset_revision=repository.installed_changeset_revision,
                                             repository_tools_tups=repository_tools_tups,
                                             tool_section=tool_section,
                                             shed_tool_conf=shed_tool_conf,
                                             tool_path=tool_path,
                                             owner=repository.owner,
                                             add_to_config=False )
            # Deactivate proprietary datatypes.
            load_datatype_items( trans.app, repository, relative_install_dir, deactivate=True )
            if remove_from_disk_checked:
                # TODO: Remove repository from disk and alter the shed tool config.
                message = 'The repository named <b>%s</b> has been uninstalled.' % repository.name
            else:
                message = 'The repository named <b>%s</b> has been deactivated.' % repository.name
            status = 'done'
            return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                              action='browse_repositories',
                                                              message=message,
                                                              status=status ) )
        remove_from_disk_check_box = CheckboxField( 'remove_from_disk', checked=remove_from_disk_checked )
        return trans.fill_template( '/admin/tool_shed_repository/deactivate_or_uninstall_repository.mako',
                                    repository=repository,
                                    remove_from_disk_check_box=remove_from_disk_check_box,
                                    message=message,
                                    status=status )
    def __deactivate( self, trans, repository_tool_panel_keys, tool_section=None, section_key=None ):
        # Delete tools loaded into the tool panel.  If the tool_panel is received,
        # the tools were loaded into the tool panel outside of any sections.  If
        # the tool_section is received, all tools were loaded into that section.
        if tool_section:
            # The tool_section.elems dictionary looks something like:
            # {'tool_gvk.bx.psu.edu:9009/repos/test/filter/Filter1/1.0.1': <galaxy.tools.Tool instance at 0x10769ae60>}
            for item_id, item in tool_section.elems.items():
                if item_id in repository_tool_panel_keys:
                    del tool_section.elems[ item_id ]
            if not tool_section.elems:
                del trans.app.toolbox.tool_panel[ section_key ]
        else:
            # The tool panel looks something like:
            # {'tool_gvk.bx.psu.edu:9009/repos/test/blast2go/blast2go/0.0.2': <galaxy.tools.Tool instance at 0x1076a5f80>}
            for item_id, item in trans.app.toolbox.tool_panel.items():
                if item_id in repository_tool_panel_keys:
                    del trans.app.toolbox.tool_panel[ item_id ]
    @web.expose
    @web.require_admin
    def activate_or_reinstall_repository( self, trans, **kwd ):
        # TODO: handle re-introduction of workflows loaded into the tool panel that are in the repository being activated.
        repository = get_repository( trans, kwd[ 'id' ] )
        repository.deleted = False
        trans.sa_session.add( repository )
        trans.sa_session.flush()
        shed_tool_conf, tool_path, relative_install_dir = self.__get_tool_path_and_relative_install_dir( trans, repository )
        metadata = repository.metadata
        repository_tools_tups = get_repository_tools_tups( trans.app, metadata )
        tool_panel_section = metadata[ 'tool_panel_section' ]
        section_id = tool_panel_section[ 'id' ]
        if section_id in [ '' ]:
            # If the repository includes tools, reload them into the tool panel outside of any sections.
            self.__activate( trans, repository, repository_tools_tups, tool_section=None, section_key=None )
        else:
            # If the repository includes tools, reload them into the appropriate tool panel section.
            section_key = 'section_%s' % str( section_id )
            if section_key in trans.app.toolbox.tool_panel:
                # Load the repository tools into a section that still exists in the tool panel.
                tool_section = trans.app.toolbox.tool_panel[ section_key ]
                self.__activate( trans, repository, repository_tools_tups, tool_section=tool_section, section_key=section_key )
            else:
                # Load the repository tools into a section that no longer exists in the tool panel.
                # We first see if the section exists in the tool config, which will be the case if
                # the repository was only deactivated and not uninstalled.
                section_loaded = False
                for tcf in trans.app.config.tool_configs:
                    # Only inspect tool configs that contain installed tool shed repositories.
                    if tcf not in [ 'tool_conf.xml' ]:
                        log.info( "Parsing the tool configuration %s" % tcf )
                        tree = util.parse_xml( tcf )
                        root = tree.getroot()
                        tool_path = root.get( 'tool_path' )
                        if tool_path is not None:
                            # Tool configs that contain tools installed from tool shed repositories
                            # must have a tool_path attribute.
                            for elem in root:
                                if elem.tag == 'section':
                                    id_attr = elem.get( 'id' )
                                    if id_attr == section_id:
                                        tool_section = elem
                                        # Load the tools.
                                        trans.app.toolbox.load_section_tag_set( tool_section, trans.app.toolbox.tool_panel, tool_path )
                                        section_loaded = True
                                        break
                    if section_loaded:
                        break
                # Load proprietary datatypes.
                load_datatype_items( trans.app, repository, relative_install_dir )
        message = 'The repository named <b>%s</b> has been activated.' % repository.name
        status = 'done'
        return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                          action='browse_repositories',
                                                          message=message,
                                                          status=status ) )
    def __activate( self, trans, repository, repository_tools_tups, tool_section=None, section_key=None ):
        # Load tools.
        if tool_section:
            elems = tool_section.elems
        for repository_tools_tup in repository_tools_tups:
            relative_path, guid, tool = repository_tools_tup
            tool.tool_shed = repository.tool_shed
            tool.repository_name = repository.name
            tool.repository_owner = repository.owner
            tool.installed_changeset_revision = repository.installed_changeset_revision
            tool.guid = guid
            # Set the tool's old_id to the id used before the tool shed existed.
            tool.old_id = tool.id
            # Set the tool's id to the tool shed guid.
            tool.id = guid
            if tool_section:
                if tool.id not in elems:
                    elems[ 'tool_%s' % tool.id ] = tool
                    log.debug( "Reactivated tool id: %s, version: %s" % ( tool.id, tool.version ) )
            else:
                if tool.id not in trans.app.toolbox.tools_by_id:
                    # Allow for the same tool to be loaded into multiple places in the tool panel.
                    trans.app.toolbox.tools_by_id[ tool.id ] = tool
                trans.app.toolbox.tool_panel[ 'tool_%s' % tool.id ] = tool
                log.debug( "Reactivated tool id: %s, version: %s" % ( tool.id, tool.version ) )
        if tool_section:
            trans.app.toolbox.tool_panel[ section_key ] = tool_section
            log.debug( "Appended reactivated tool to section: %s" % tool_section.name )
        shed_tool_conf, tool_path, relative_install_dir = self.__get_tool_path_and_relative_install_dir( trans, repository )
        load_datatype_items( trans.app, repository, relative_install_dir )
    @web.expose
    @web.require_admin
    def manage_repository( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        repository = get_repository( trans, kwd[ 'id' ] )
        description = util.restore_text( params.get( 'description', repository.description ) )
        shed_tool_conf, tool_path, relative_install_dir = self.__get_tool_path_and_relative_install_dir( trans, repository )
        repo_files_dir = os.path.abspath( os.path.join( relative_install_dir, repository.name ) )
        if params.get( 'edit_repository_button', False ):
            if description != repository.description:
                repository.description = description
                trans.sa_session.add( repository )
                trans.sa_session.flush()
            message = "The repository information has been updated."
        elif params.get( 'set_metadata_button', False ):
            repository_clone_url = self.__generate_clone_url( trans, repository )
            # In case metadata was previously generated for this repository, we'll
            # check to see if it has information needed for the tool_section_dict.
            metadata = repository.metadata
            if 'tool_panel_section' in metadata:
                tool_section_dict = metadata[ 'tool_panel_section' ]
            metadata_dict = generate_metadata( trans.app.toolbox, relative_install_dir, repository_clone_url, tool_section_dict=tool_section_dict )
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
    def check_for_updates( self, trans, **kwd ):
        # Send a request to the relevant tool shed to see if there are any updates.
        repository = get_repository( trans, kwd[ 'id' ] )
        tool_shed_url = get_url_from_repository_tool_shed( trans.app, repository )
        url = '%s/repository/check_for_updates?galaxy_url=%s&name=%s&owner=%s&changeset_revision=%s&webapp=galaxy' % \
            ( tool_shed_url, url_for( '', qualified=True ), repository.name, repository.owner, repository.changeset_revision )
        return trans.response.send_redirect( url )
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
        repository = get_repository_by_shed_name_owner_changeset_revision( trans.app, tool_shed_url, name, owner, changeset_revision )
        if changeset_revision and latest_changeset_revision:
            if changeset_revision == latest_changeset_revision:
                message = "The cloned tool shed repository named '%s' is current (there are no updates available)." % name
            else:
                current_working_dir = os.getcwd()
                shed_tool_conf, tool_path, relative_install_dir = self.__get_tool_path_and_relative_install_dir( trans, repository )
                if relative_install_dir:
                    repo_files_dir = os.path.join( relative_install_dir, name )
                    returncode, tmp_name = pull_repository( current_working_dir, repo_files_dir, name )
                    if returncode == 0:
                        returncode, tmp_name = update_repository( current_working_dir, repo_files_dir, latest_changeset_revision )
                        if returncode == 0:
                            # Update the repository metadata.
                            repository_clone_url = os.path.join( tool_shed_url, 'repos', owner, name )
                            tool_shed = clean_tool_shed_url( tool_shed_url )
                            metadata_dict = load_repository_contents( app=trans.app,
                                                                      name=name,
                                                                      description=repository.description,
                                                                      owner=owner,
                                                                      changeset_revision=changeset_revision,
                                                                      tool_path=tool_path,
                                                                      repository_clone_url=repository_clone_url,
                                                                      relative_install_dir=relative_install_dir,
                                                                      current_working_dir=current_working_dir,
                                                                      tmp_name=tmp_name,
                                                                      tool_shed=tool_shed,
                                                                      tool_section=None,
                                                                      shed_tool_conf=None,
                                                                      new_install=False )
                            # Update the repository changeset_revision in the database.
                            repository.changeset_revision = latest_changeset_revision
                            repository.update_available = False
                            trans.sa_session.add( repository )
                            trans.sa_session.flush()
                            message = "The cloned repository named '%s' has been updated to change set revision '%s'." % \
                                ( name, latest_changeset_revision )
                        else:
                            tmp_stderr = open( tmp_name, 'rb' )
                            message = tmp_stderr.read()
                            tmp_stderr.close()
                            status = 'error'
                    else:
                        tmp_stderr = open( tmp_name, 'rb' )
                        message = tmp_stderr.read()
                        tmp_stderr.close()
                        status = 'error'
                else:
                    message = "The directory containing the cloned repository named '%s' cannot be found." % name
                    status = 'error'
        else:
            message = "The latest changeset revision could not be retrieved for the repository named '%s'." % name
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
        webapp = params.get( 'webapp', 'community' )
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
    def __get_tool_path_and_relative_install_dir( self, trans, repository ):
        # Return both the tool_path configured in the relative shed_tool_conf and
        # the relative path to the directory where the repository is installed.
        tool_shed = clean_tool_shed_url( repository.tool_shed )
        partial_install_dir = '%s/repos/%s/%s/%s' % ( tool_shed, repository.owner, repository.name, repository.installed_changeset_revision )
        # Get the relative tool installation paths from each of the shed tool configs.
        shed_tool_confs = trans.app.toolbox.shed_tool_confs
        relative_install_dir = None
        # The shed_tool_confs dictionary contains { shed_tool_conf : tool_path } pairs.
        for shed_tool_conf, tool_path in shed_tool_confs.items():
            relative_install_dir = os.path.join( tool_path, partial_install_dir )
            if os.path.isdir( relative_install_dir ):
                break
        return shed_tool_conf, tool_path, relative_install_dir
    def __generate_tool_path( self, repository_clone_url, changeset_revision ):
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
    def __generate_clone_url( self, trans, repository ):
        """Generate the URL for cloning a repository."""
        tool_shed_url = get_url_from_repository_tool_shed( trans.app, repository )
        return '%s/repos/%s/%s' % ( tool_shed_url, repository.owner, repository.name )

## ---- Utility methods -------------------------------------------------------

def build_shed_tool_conf_select_field( trans ):
    """Build a SelectField whose options are the keys in trans.app.toolbox.shed_tool_confs."""
    options = []
    for shed_tool_conf_filename, tool_path in trans.app.toolbox.shed_tool_confs.items():
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
    for k, tool_section in trans.app.toolbox.tool_panel.items():
        options.append( ( tool_section.name, tool_section.id ) )
    select_field = SelectField( name='tool_panel_section', display='radio' )
    for option_tup in options:
        select_field.add_option( option_tup[0], option_tup[1] )
    return select_field
def get_repository( trans, id ):
    """Get a tool_shed_repository from the database via id"""
    return trans.sa_session.query( trans.model.ToolShedRepository ).get( trans.security.decode_id( id ) )
