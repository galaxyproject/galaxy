import urllib2
from galaxy.web.controllers.admin import *
from galaxy.util.json import from_json_string, to_json_string
from galaxy.util.shed_util import *
from galaxy import tools

log = logging.getLogger( __name__ )

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
    global_actions = []
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

    @web.expose
    @web.require_admin
    def activate_repository( self, trans, **kwd ):
        """Activate a repository that was deactivated but not uninstalled."""
        repository = get_repository( trans, kwd[ 'id' ] )
        shed_tool_conf, tool_path, relative_install_dir = self.__get_tool_panel_config_tool_path_install_dir( trans, repository )
        repository_clone_url = self.__generate_clone_url( trans, repository )
        repository.deleted = False
        trans.sa_session.add( repository )
        trans.sa_session.flush()
        if repository.includes_tools:
            # Reload tools into the appropriate tool panel section.
            metadata = repository.metadata
            if 'tool_panel_section' in metadata:
                if panel_entry_per_tool( metadata[ 'tool_panel_section' ] ):
                    tool_panel_dict = metadata[ 'tool_panel_section' ]
                else:
                    # The value of tool_panel_section is the old dictionary type.
                    tool_section_dict = metadata[ 'tool_panel_section' ]
                    tool_panel_dict = generate_tool_panel_dict_for_repository_tools( metadata, tool_section_dict=tool_section_dict )
                    repository.metadata[ 'tool_panel_section' ] = tool_panel_dict
                    trans.sa_session.add( repository )
                    trans.sa_session.flush()
            else:
                # The tool_panel_section was introduced late, so set it's value if its missing in the metadata.
                tool_panel_dict = generate_tool_panel_dict_for_repository_tools( metadata )
                repository.metadata[ 'tool_panel_section' ] = tool_panel_dict
                trans.sa_session.add( repository )
                trans.sa_session.flush()
            repository_tools_tups = get_repository_tools_tups( trans.app, metadata )
            guids_to_activate = [ repository_tool_tup[1] for repository_tool_tup in repository_tools_tups ]
            # Make sure we have a tool_version for each guid.
            for guid_to_activate in guids_to_activate:
                if not get_tool_version( trans.app, guid_to_activate ):
                    # We're somehow missing a tool_version, so create a new one.
                    tool_version = trans.model.ToolVersion( tool_id=guid_to_activate, tool_shed_repository=repository )
                    trans.sa_session.add( tool_version )
                    trans.sa_session.flush()
        add_to_tool_panel( trans.app,
                           repository.name,
                           repository_clone_url,
                           repository.changeset_revision,
                           repository_tools_tups,
                           repository.owner,
                           shed_tool_conf,
                           tool_panel_dict,
                           new_install=False )
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
            kwd[ 'message' ] = 'Names of repositories for which updates are available are highlighted in red.'
        return self.repository_list_grid( trans, **kwd )
    @web.expose
    @web.require_admin
    def browse_tool_shed( self, trans, **kwd ):
        tool_shed_url = kwd[ 'tool_shed_url' ]
        galaxy_url = url_for( '/', qualified=True )
        url = '%s/repository/browse_valid_repositories?galaxy_url=%s&webapp=galaxy' % ( tool_shed_url, galaxy_url )
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
        url = '%s/repository/check_for_updates?galaxy_url=%s&name=%s&owner=%s&changeset_revision=%s&webapp=galaxy' % \
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
        repository = get_repository( trans, kwd[ 'id' ] )
        shed_tool_conf, tool_path, relative_install_dir = self.__get_tool_panel_config_tool_path_install_dir( trans, repository )
        if params.get( 'deactivate_or_uninstall_repository_button', False ):
            metadata = repository.metadata
            if repository.includes_tools:
                repository_tools_tups = get_repository_tools_tups( trans.app, metadata )
                # Generate the list of tool panel keys derived from the tools included in the repository.
                if repository_tools_tups:
                    repository_tool_panel_keys = [ 'tool_%s' % repository_tools_tup[ 1 ] for repository_tools_tup in repository_tools_tups ]
                else:
                    repository_tool_panel_keys = []
                if 'tool_panel_section' in metadata:
                    if panel_entry_per_tool( metadata[ 'tool_panel_section' ] ):
                        tool_panel_dict = metadata[ 'tool_panel_section' ]
                    else:
                        # The tool_panel_section dictionary is the old definition of the tool_panel_section, so update it to the current dictionary.
                        # All of the repository tools will be installed in the same section or outside of any sections.
                        tool_section_dict = metadata[ 'tool_panel_section' ]
                        tool_panel_dict = generate_tool_panel_dict_for_repository_tools( metadata, tool_section_dict=tool_section_dict )
                        repository.metadata[ 'tool_panel_section' ] = tool_panel_dict
                else:
                    # The tool_panel_section was introduced late, so set it's value if its missing in the metadata.
                    tool_panel_dict = generate_tool_panel_dict_for_repository_tools( metadata )
                    repository.metadata[ 'tool_panel_section' ] = tool_panel_dict
                repository_clone_url = generate_clone_url( trans, repository )
                # The repository is either being deactivated or uninstalled, so handle tool panel alterations accordingly.
                # If the repository is being uninstalled, the appropriate tools or tool sections will be removed from the
                # appropriate shed-related tool config file on disk.
                remove_from_tool_panel( app=trans.app,
                                        shed_tool_conf=shed_tool_conf,
                                        tool_panel_dict=tool_panel_dict,
                                        uninstall=remove_from_disk_checked )
            if repository.includes_datatypes:
                # Deactivate proprietary datatypes.
                load_datatype_items( trans.app, repository, relative_install_dir, deactivate=True )
            if remove_from_disk_checked:
                # Remove the repository from disk.
                try:
                    shutil.rmtree( relative_install_dir )
                    log.debug( "Removed repository installation directory: %s" % str( relative_install_dir ) )
                except Exception, e:
                    log.debug( "Error removing repository installation directory %s: %s" % ( str( relative_install_dir ), str( e ) ) )
                repository.uninstalled = True
            repository.deleted = True
            trans.sa_session.add( repository )
            trans.sa_session.flush()
            if remove_from_disk_checked:
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
                # If installing a repository that includes no tools, get the relative tool_path from the file
                # to which the migrated_tools_config setting points.
                shed_tool_conf = trans.app.config.migrated_tools_config
            # Get the tool path by searching the list of shed_tool_confs for the dictionary
            # that contains the information about shed_tool_conf.
            for shed_tool_conf_dict in trans.app.toolbox.shed_tool_confs:
                config_filename = shed_tool_conf_dict[ 'config_filename' ]
                if config_filename == shed_tool_conf:
                    tool_path = shed_tool_conf_dict[ 'tool_path' ]
                    break
                else:
                    head, tail = os.path.split( config_filename )
                    if tail == shed_tool_conf:
                        tool_path = shed_tool_conf_dict[ 'tool_path' ]
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
                    message += 'Revision <b>%s</b> of repository <b>%s</b> was previously installed.<br/>' % ( changeset_revision, name )
                else:
                    returncode, tmp_name = clone_repository( name, clone_dir, current_working_dir, repository_clone_url )
                    if returncode == 0:
                        returncode, tmp_name = update_repository( current_working_dir, relative_install_dir, changeset_revision )
                        if returncode == 0:
                            owner = get_repository_owner( clean_repository_clone_url( repository_clone_url ) )
                            tool_shed = clean_tool_shed_url( tool_shed_url )
                            tool_shed_repository, metadata_dict = load_repository_contents( trans,
                                                                                            repository_name=name,
                                                                                            description=description,
                                                                                            owner=owner,
                                                                                            changeset_revision=changeset_revision,
                                                                                            tool_path=tool_path,
                                                                                            repository_clone_url=repository_clone_url,
                                                                                            relative_install_dir=relative_install_dir,
                                                                                            current_working_dir=current_working_dir,
                                                                                            tmp_name=tmp_name,
                                                                                            tool_panel_dict=None,
                                                                                            tool_shed=tool_shed,
                                                                                            tool_section=tool_section,
                                                                                            shed_tool_conf=shed_tool_conf,
                                                                                            new_install=True )


                            if 'tools' in metadata_dict:
                                # Get the tool_versions from the tool shed for each tool in the installed change set.
                                url = '%s/repository/get_tool_versions?name=%s&owner=%s&changeset_revision=%s&webapp=galaxy' % \
                                    ( tool_shed_url, name, owner, changeset_revision )
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
        if len( trans.app.toolbox.shed_tool_confs ) > 1:
            shed_tool_conf_select_field = build_shed_tool_conf_select_field( trans )
            shed_tool_conf = None
        else:
            shed_tool_conf_dict = trans.app.toolbox.shed_tool_confs[0]
            shed_tool_conf = shed_tool_conf_dict[ 'config_filename' ]
            shed_tool_conf = shed_tool_conf.replace( './', '', 1 )
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
    def manage_repository( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        repository = get_repository( trans, kwd[ 'id' ] )
        description = util.restore_text( params.get( 'description', repository.description ) )
        shed_tool_conf, tool_path, relative_install_dir = self.__get_tool_panel_config_tool_path_install_dir( trans, repository )
        repo_files_dir = os.path.abspath( os.path.join( relative_install_dir, repository.name ) )
        if params.get( 'edit_repository_button', False ):
            if description != repository.description:
                repository.description = description
                trans.sa_session.add( repository )
                trans.sa_session.flush()
            message = "The repository information has been updated."
        elif params.get( 'set_metadata_button', False ):
            repository_clone_url = generate_clone_url( trans, repository )
            # In case metadata was previously generated for this repository, we'll check to see if it has information needed for the tool_section_dict.
            metadata = repository.metadata
            if 'tool_panel_section' in metadata:
                # For backward compatibility we have to handle 2 types of dictionaries.  In the past, all repository tools had to be installed into
                # a single ToolSection (or outside of any sections) in the tool panel.  In this case. the dictionary looks like this.
                # { id: <ToolSection id>, version : <ToolSection version>, name : <TooSection name>}
                # Later, each tool from a repository could be installed into the tool panel inside or outside a specified ToolSection in the tool panel.
                if panel_entry_per_tool( metadata[ 'tool_panel_section' ] ):
                    tool_panel_dict = metadata[ 'tool_panel_section' ]
                    metadata_dict = generate_metadata( trans.app.toolbox, relative_install_dir, repository_clone_url, tool_panel_dict=tool_panel_dict )
                else:
                    tool_section_dict = metadata[ 'tool_panel_section' ]
                    metadata_dict = generate_metadata( trans.app.toolbox, relative_install_dir, repository_clone_url, tool_section_dict=tool_section_dict )
            else:
                # Not sure if we'll ever reach here, but just in case...
                tool_section_dict = dict( id='', version='', name='' )
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
    def reinstall_repository( self, trans, **kwd ):
        repository = get_repository( trans, kwd[ 'id' ] )
        no_changes = kwd.get( 'no_changes', '' )
        no_changes_checked = CheckboxField.is_checked( no_changes )
        shed_tool_conf, tool_path, relative_install_dir = self.__get_tool_panel_config_tool_path_install_dir( trans, repository )
        current_working_dir = os.getcwd()
        repository_clone_url = generate_clone_url( trans, repository )
        clone_dir = os.path.join( tool_path, self.__generate_tool_path( repository_clone_url, repository.installed_changeset_revision ) )
        relative_install_dir = os.path.join( clone_dir, repository.name )
        returncode, tmp_name = clone_repository( repository.name, clone_dir, current_working_dir, repository_clone_url )
        if returncode == 0:
            returncode, tmp_name = update_repository( current_working_dir, relative_install_dir, repository.installed_changeset_revision )
            if returncode == 0:
                # Get the location in the tool panel in which the tool was originally loaded.
                metadata = repository.metadata
                if 'tool_panel_section' in metadata:
                    if panel_entry_per_tool( metadata[ 'tool_panel_section' ] ):
                        tool_panel_dict = metadata[ 'tool_panel_section' ]
                        # TODO: Fix this to handle the case where the tools are distributed across in more than 1 ToolSection.  The
                        # following assumes everything was loaded into 1 section (or no section) in the tool panel.
                        tool_section_dicts = tool_panel_dict[ tool_panel_dict.keys()[ 0 ] ]
                        tool_section_dict = tool_section_dicts[ 0 ]
                    else:
                        tool_section_dict = metadata[ 'tool_panel_section' ]
                        tool_section = generate_tool_section_element_from_dict( tool_section_dict )
                        tool_panel_dict = generate_tool_panel_dict_for_repository_tools( metadata, tool_section=tool_section )
                    original_section_id = tool_section_dict[ 'id' ]
                    original_section_name = tool_section_dict[ 'name' ]
                else:
                    tool_panel_dict = generate_tool_panel_dict_for_repository_tools( metadata )
                    original_section_id = ''
                    original_section_name = ''
                if no_changes_checked:
                    if original_section_id in [ '' ]:
                        tool_section = None
                    else:
                        section_key = 'section_%s' % str( original_section_id )
                        if section_key in trans.app.toolbox.tool_panel:
                            tool_section = trans.app.toolbox.tool_panel[ section_key ]
                        else:
                            # The section in which the tool was originally loaded used to be in the tool panel, but no longer is.
                            elem = Element( 'section' )
                            elem.attrib[ 'name' ] = original_section_name
                            elem.attrib[ 'id' ] = original_section_id
                            elem.attrib[ 'version' ] = ''
                            tool_section = tools.ToolSection( elem )
                            trans.app.toolbox.tool_panel[ section_key ] = tool_section
                else:
                    # The user elected to change the tool panel section to contain the tools.
                    new_tool_panel_section = kwd.get( 'new_tool_panel_section', '' )
                    tool_panel_section = kwd.get( 'tool_panel_section', '' )
                    if new_tool_panel_section:
                        section_id = new_tool_panel_section.lower().replace( ' ', '_' )
                        # Update each tool_section dictionary in tool_panel_dict with the new section attributes.
                        for guid, tool_section_dicts in tool_panel_dict.items():
                            for dict_index, tool_section_dict in enumerate( tool_section_dicts ):
                                tool_section_dict[ 'id' ] = section_id
                                tool_section_dict[ 'name' ] = new_tool_panel_section
                                tool_section_dict[ 'version' ] = ''
                                tool_section_dicts[ dict_index ] = tool_section_dict
                            tool_panel_dict[ guid ] = tool_section_dicts
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
                    elif tool_panel_section:
                        section_key = 'section_%s' % tool_panel_section
                        tool_section = trans.app.toolbox.tool_panel[ section_key ]
                    else:
                        # Update each tool_section dictionary in tool_panel_dict in case the tools used to be contained in a panel section
                        # but are now being moved outside of any panel sections.
                        for guid, tool_section_dicts in tool_panel_dict.items():
                            for dict_index, tool_section_dict in enumerate( tool_section_dicts ):
                                tool_section_dict[ 'id' ] = ''
                                tool_section_dict[ 'name' ] = ''
                                tool_section_dict[ 'version' ] = ''
                                tool_section_dicts[ dict_index ] = tool_section_dict
                            tool_panel_dict[ guid ] = tool_section_dicts
                        tool_section = None
                tool_shed_repository, metadata_dict = load_repository_contents( trans,
                                                                                repository_name=repository.name,
                                                                                description=repository.description,
                                                                                owner=repository.owner,
                                                                                changeset_revision=repository.installed_changeset_revision,
                                                                                tool_path=tool_path,
                                                                                repository_clone_url=repository_clone_url,
                                                                                relative_install_dir=relative_install_dir,
                                                                                current_working_dir=current_working_dir,
                                                                                tmp_name=tmp_name,
                                                                                tool_panel_dict=tool_panel_dict,
                                                                                tool_shed=repository.tool_shed,
                                                                                tool_section=tool_section,
                                                                                shed_tool_conf=shed_tool_conf,
                                                                                new_install=True )
                repository.uninstalled = False
        repository.deleted = False
        trans.sa_session.add( repository )
        trans.sa_session.flush()
        message = 'The <b>%s</b> repository has been reinstalled.' % repository.name
        status = 'done'
        return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                          action='browse_repositories',
                                                          message=message,
                                                          status=status ) )
    @web.expose
    @web.require_admin
    def reselect_tool_panel_section( self, trans, **kwd ):
        """
        INSIDE SECTION:
        "{"tool_panel_section": {"gvk.bx.psu.edu:9009/repos/test/grouping/Grouping1/1.9.0": {"id": "group", 
                                                                                             "name": "Group", 
                                                                                             "tool_config": "grouping.xml", 
                                                                                             "version": ""}},
          "tools": [{"description": "data by a column and perform aggregate operation on other columns.", 
                     "guid": "gvk.bx.psu.edu:9009/repos/test/grouping/Grouping1/1.9.0", 
                     "id": "Grouping1", 
                     "name": "Group", 
                     "requirements": [{"fabfile": null, "method": null, "name": "rpy", "type": "python-module", "version": null}], 
                     "tests": [{"inputs": [["input1", "1.bed", {"children": [], "value": "1.bed"}], ["groupcol", "1", {"children": [], "value": "1"}], ["ignorecase", "true", {"children": [], "value": "true"}], ["optype", "mean", {"children": [], "value": "mean"}], ["opcol", "2", {"children": [], "value": "2"}], ["opround", "no", {"children": [], "value": "no"}]], "name": "Test-1", "outputs": [["out_file1", "groupby_out1.dat", {"assert_list": null, "compare": "diff", "delta": 10000, "extra_files": [], "lines_diff": 0, "sort": false}]], "required_files": [["1.bed", {"children": [], "value": "1.bed"}]]}, {"inputs": [["input1", "1.tabular", {"children": [], "value": "1.tabular"}], ["groupcol", "1", {"children": [], "value": "1"}], ["ignorecase", "true", {"children": [], "value": "true"}], ["optype", "mean", {"children": [], "value": "mean"}], ["opcol", "2", {"children": [], "value": "2"}], ["opround", "no", {"children": [], "value": "no"}]], "name": "Test-2", "outputs": [["out_file1", "groupby_out2.dat", {"assert_list": null, "compare": "diff", "delta": 10000, "extra_files": [], "lines_diff": 0, "sort": false}]], "required_files": [["1.tabular", {"children": [], "value": "1.tabular"}]]}], 
                     "tool_config": "../shed_tools/gvk.bx.psu.edu/repos/test/grouping/935f00105de8/grouping/grouping.xml", 
                     "version": "1.9.0", 
                     "version_string_cmd": null}]}"
        OUTSIDE SECTION:
        "{"tool_panel_section": {"gvk.bx.psu.edu:9009/repos/test/filter/Filter1/1.0.1": {"id": "", 
                                                                                         "name": "", 
                                                                                         "tool_config": "filtering.xml", 
                                                                                         "version": ""}}, 
          "tools": [{"description": "data on any column using simple expressions", 
                     "guid": "gvk.bx.psu.edu:9009/repos/test/filter/Filter1/1.0.1", 
                     "id": "Filter1", 
                     "name": "Filter", 
                     "requirements": [], 
                     "tests": [{"inputs": [["input", "1.bed", {"children": [], "value": "1.bed"}], ["cond", "c1=='chr22'", {"children": [], "value": "c1=='chr22'"}]], "name": "Test-1", "outputs": [["out_file1", "filter1_test1.bed", {"assert_list": null, "compare": "diff", "delta": 10000, "extra_files": [], "lines_diff": 0, "sort": false}]], "required_files": [["1.bed", {"children": [], "value": "1.bed"}]]}, {"inputs": [["input", "7.bed", {"children": [], "value": "7.bed"}], ["cond", "c1=='chr1' and c3-c2>=2000 and c6=='+'", {"children": [], "value": "c1=='chr1' and c3-c2>=2000 and c6=='+'"}]], "name": "Test-2", "outputs": [["out_file1", "filter1_test2.bed", {"assert_list": null, "compare": "diff", "delta": 10000, "extra_files": [], "lines_diff": 0, "sort": false}]], "required_files": [["7.bed", {"children": [], "value": "7.bed"}]]}], 
                     "tool_config": "../shed_tools/gvk.bx.psu.edu/repos/test/filter/b2df18d723c5/filter/filtering.xml", 
                     "version": "1.0.1", 
                     "version_string_cmd": null}]}"
        """
        repository = get_repository( trans, kwd[ 'id' ] )
        # Get the location in the tool panel in which the tool was originally loaded.
        metadata = repository.metadata
        if 'tool_panel_section' in metadata:
            tool_panel_dict = metadata[ 'tool_panel_section' ]
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
        return trans.fill_template( '/admin/tool_shed_repository/reselect_tool_panel_section.mako',
                                    repository=repository,
                                    no_changes_check_box=no_changes_check_box,
                                    original_section_name=original_section_name,
                                    tool_panel_section_select_field=tool_panel_section_select_field,
                                    message=message,
                                    status=status )
    @web.expose
    @web.require_admin
    def set_tool_versions( self, trans, **kwd ):
        # Get the tool_versions from the tool shed for each tool in the installed change set.
        repository = get_repository( trans, kwd[ 'id' ] )
        tool_shed_url = get_url_from_repository_tool_shed( trans.app, repository )
        url = '%s/repository/get_tool_versions?name=%s&owner=%s&changeset_revision=%s&webapp=galaxy' % \
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
        shed_tool_conf, tool_path, relative_install_dir = self.__get_tool_panel_config_tool_path_install_dir( trans, repository )
        repo_files_dir = os.path.abspath( os.path.join( relative_install_dir, repository.name ) )
        return trans.fill_template( '/admin/tool_shed_repository/manage_repository.mako',
                                    repository=repository,
                                    description=repository.description,
                                    repo_files_dir=repo_files_dir,
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
        repository = get_repository_by_shed_name_owner_changeset_revision( trans.app, tool_shed_url, name, owner, changeset_revision )
        # Get the location in the tool panel in which the tool was originally loaded.
        metadata = repository.metadata
        if 'tool_panel_section' in metadata:
            if panel_entry_per_tool( metadata[ 'tool_panel_section' ] ):
                tool_panel_dict = metadata[ 'tool_panel_section' ]
            else:
                tool_section_dict = metadata[ 'tool_panel_section' ]
                tool_section = generate_tool_section_element_from_dict( tool_section_dict )
                tool_panel_dict = generate_tool_panel_dict_for_repository_tools( metadata, tool_section=tool_section )
        else:
            tool_panel_dict = generate_tool_panel_dict_for_repository_tools( metadata )
        if changeset_revision and latest_changeset_revision:
            if changeset_revision == latest_changeset_revision:
                message = "The cloned tool shed repository named '%s' is current (there are no updates available)." % name
            else:
                current_working_dir = os.getcwd()
                shed_tool_conf, tool_path, relative_install_dir = self.__get_tool_panel_config_tool_path_install_dir( trans, repository )
                if relative_install_dir:
                    repo_files_dir = os.path.join( relative_install_dir, name )
                    returncode, tmp_name = pull_repository( current_working_dir, repo_files_dir, name )
                    if returncode == 0:
                        returncode, tmp_name = update_repository( current_working_dir, repo_files_dir, latest_changeset_revision )
                        if returncode == 0:
                            # Update the repository metadata.
                            repository_clone_url = os.path.join( tool_shed_url, 'repos', owner, name )
                            tool_shed = clean_tool_shed_url( tool_shed_url )
                            tool_shed_repository, metadata_dict = load_repository_contents( trans,
                                                                                            repository_name=name,
                                                                                            description=repository.description,
                                                                                            owner=owner,
                                                                                            changeset_revision=changeset_revision,
                                                                                            tool_path=tool_path,
                                                                                            repository_clone_url=repository_clone_url,
                                                                                            relative_install_dir=relative_install_dir,
                                                                                            current_working_dir=current_working_dir,
                                                                                            tmp_name=tmp_name,
                                                                                            tool_panel_dict=tool_panel_dict,
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
    def __generate_clone_url( self, trans, repository ):
        """Generate the URL for cloning a repository."""
        tool_shed_url = get_url_from_repository_tool_shed( trans.app, repository )
        return '%s/repos/%s/%s' % ( tool_shed_url, repository.owner, repository.name )
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
    def __get_tool_panel_config_tool_path_install_dir( self, trans, repository ):
        # Return shed-related tool panel config, the tool_path configured in it, and the relative path to the directory where the
        # repository is installed.  This method assumes all repository tools are defined in a single shed-related tool panel config.
        tool_shed = clean_tool_shed_url( repository.tool_shed )
        partial_install_dir = '%s/repos/%s/%s/%s' % ( tool_shed, repository.owner, repository.name, repository.installed_changeset_revision )
        # Get the relative tool installation paths from each of the shed tool configs.
        relative_install_dir = None
        for shed_tool_conf_dict in trans.app.toolbox.shed_tool_confs:
            shed_tool_conf = shed_tool_conf_dict[ 'config_filename' ]
            if repository.dist_to_shed:
                # The repository is owned by devteam and contains tools migrated from the Galaxy distribution to the tool shed, so
                # the reserved tool panel config is migrated_tools_conf.xml, to which trans.app.config.migrated_tools_config refers.
                if shed_tool_conf == trans.app.config.migrated_tools_config:
                    tool_path = shed_tool_conf_dict[ 'tool_path' ]
                    relative_install_dir = os.path.join( tool_path, partial_install_dir )
                    if tool_path and relative_install_dir:
                        return shed_tool_conf, tool_path, relative_install_dir
            elif repository.uninstalled:
                # Since the repository is uninstalled we don't know what tool panel config was originally used to
                # define the tools in the repository, so we'll just make sure not to use the reserved migrated_tools_conf.xml.
                if shed_tool_conf != trans.app.config.migrated_tools_config:
                    tool_path = shed_tool_conf_dict[ 'tool_path' ]
                    relative_install_dir = os.path.join( tool_path, partial_install_dir )
                    if tool_path and relative_install_dir:
                        return shed_tool_conf, tool_path, relative_install_dir
            else:
                if repository.includes_tools:
                    # We'll check config_elems until we find an element that matches one of the tools in the repository's metadata.
                    metadata = repository.metadata
                    tool_dict = metadata[ 'tools' ][ 0 ]
                    config_elems = shed_tool_conf_dict[ 'config_elems' ]
                    if config_elems:
                        tool_path, relative_install_dir = self.__get_tool_path_install_dir( partial_install_dir,
                                                                                            shed_tool_conf_dict,
                                                                                            tool_dict,
                                                                                            config_elems )
                        if tool_path and relative_install_dir:
                            return shed_tool_conf, tool_path, relative_install_dir
                    else:
                        # Parse the tool panel config since we have no in-memory config_elems (not sure if this will ever occur).
                        tool_panel_config = shed_tool_conf_dict[ 'config_filename' ]
                        tree = util.parse_xml( tool_panel_config )
                        root = tree.getroot()
                        tool_path, relative_install_dir = self.__get_tool_path_install_dir( partial_install_dir,
                                                                                            shed_tool_conf_dict,
                                                                                            tool_dict,
                                                                                            root )
                        if tool_path and relative_install_dir:
                            return shed_tool_conf, tool_path, relative_install_dir
                else:
                    # Nothing will be loaded into the tool panel, so look for the installed repository on disk.
                    tool_path = shed_tool_conf_dict[ 'tool_path' ]
                    relative_install_dir = os.path.join( tool_path, partial_install_dir )
                    if tool_path and relative_install_dir and os.path.isdir( relative_install_dir ):
                        return shed_tool_conf, tool_path, relative_install_dir
        return None, None, None
    def __get_tool_path_install_dir( self, partial_install_dir, shed_tool_conf_dict, tool_dict, config_elems ):
        for elem in config_elems:
            if elem.tag == 'tool':
                if elem.get( 'guid' ) == tool_dict[ 'guid' ]:
                    tool_path = shed_tool_conf_dict[ 'tool_path' ]
                    relative_install_dir = os.path.join( tool_path, partial_install_dir )
                    return tool_path, relative_install_dir
            elif elem.tag == 'section':
                for section_elem in elem:
                    if section_elem.tag == 'tool':
                        if section_elem.get( 'guid' ) == tool_dict[ 'guid' ]:
                            tool_path = shed_tool_conf_dict[ 'tool_path' ]
                            relative_install_dir = os.path.join( tool_path, partial_install_dir )
                            return tool_path, relative_install_dir
        return None, None

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
