from galaxy.web.controllers.admin import *
import logging

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
    operations = [ grids.GridOperation( "Get updates",
                                        allow_multiple=False,
                                        condition=( lambda item: not item.deleted ),
                                        async_compatible=False ) ]
    standard_filters = []
    default_filter = dict( deleted="False" )
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def build_initial_query( self, trans, **kwd ):
        return trans.sa_session.query( self.model_class ) \
                               .filter( self.model_class.table.c.deleted == False )

class AdminToolshed( AdminGalaxy ):
    
    repository_list_grid = RepositoryListGrid()

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
        galaxy_url = url_for( '', qualified=True )
        url = '%s/repository/find_tools?galaxy_url=%s&webapp=galaxy' % ( tool_shed_url, galaxy_url )
        return trans.response.send_redirect( url )
    @web.expose
    @web.require_admin
    def find_workflows_in_tool_shed( self, trans, **kwd ):
        tool_shed_url = kwd[ 'tool_shed_url' ]
        galaxy_url = url_for( '', qualified=True )
        url = '%s/repository/find_workflows?galaxy_url=%s&webapp=galaxy' % ( tool_shed_url, galaxy_url )
        return trans.response.send_redirect( url )
    @web.expose
    @web.require_admin
    def browse_tool_shed( self, trans, **kwd ):
        tool_shed_url = kwd[ 'tool_shed_url' ]
        galaxy_url = url_for( '', qualified=True )
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
        if kwd.get( 'select_tool_panel_section_button', False ):
            shed_tool_conf = kwd[ 'shed_tool_conf' ]
            # Get the tool path.
            for k, tool_path in trans.app.toolbox.shed_tool_confs.items():
                if k == shed_tool_conf:
                    break
            if new_tool_panel_section or tool_panel_section:
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
                        tool_section = ToolSection( elem )
                        trans.app.toolbox.tool_panel[ new_section_key ] = tool_section
                else:
                    section_key = 'section_%s' % tool_panel_section
                    tool_section = trans.app.toolbox.tool_panel[ section_key ]
                # Decode the encoded repo_info_dict param value.
                repo_info_dict = tool_shed_decode( repo_info_dict )
                # Clone the repository to the configured location.
                current_working_dir = os.getcwd()
                installed_repository_names = []
                for name, repo_info_tuple in repo_info_dict.items():
                    metadata_dict = None
                    description, repository_clone_url, changeset_revision = repo_info_tuple
                    clone_dir = os.path.join( tool_path, self.__generate_tool_path( repository_clone_url, changeset_revision ) )
                    if os.path.exists( clone_dir ):
                        # Repository and revision has already been cloned.
                        # TODO: implement the ability to re-install or revert an existing repository.
                        message += 'Revision <b>%s</b> of repository <b>%s</b> was previously installed.<br/>' % ( changeset_revision, name )
                    else:
                        os.makedirs( clone_dir )
                        log.debug( 'Cloning %s...' % repository_clone_url )
                        cmd = 'hg clone %s' % repository_clone_url
                        tmp_name = tempfile.NamedTemporaryFile().name
                        tmp_stderr = open( tmp_name, 'wb' )
                        os.chdir( clone_dir )
                        proc = subprocess.Popen( args=cmd, shell=True, stderr=tmp_stderr.fileno() )
                        returncode = proc.wait()
                        os.chdir( current_working_dir )
                        tmp_stderr.close()
                        if returncode == 0:
                            # Update the cloned repository to changeset_revision.  It is imperative that the 
                            # installed repository is updated to the desired changeset_revision before metadata
                            # is set because the process for setting metadata uses the repository files on disk.
                            relative_install_dir = os.path.join( clone_dir, name )
                            log.debug( 'Updating cloned repository to revision "%s"...' % changeset_revision )
                            cmd = 'hg update -r %s' % changeset_revision
                            tmp_name = tempfile.NamedTemporaryFile().name
                            tmp_stderr = open( tmp_name, 'wb' )
                            os.chdir( relative_install_dir )
                            proc = subprocess.Popen( cmd, shell=True, stderr=tmp_stderr.fileno() )
                            returncode = proc.wait()
                            os.chdir( current_working_dir )
                            tmp_stderr.close()
                            if returncode == 0:
                                # Generate the metadata for the installed tool shed repository.  It is imperative that
                                # the installed repository is updated to the desired changeset_revision before metadata
                                # is set because the process for setting metadata uses the repository files on disk.
                                metadata_dict = generate_metadata( trans.app.toolbox, relative_install_dir, repository_clone_url )
                                if 'datatypes_config' in metadata_dict:
                                    datatypes_config = os.path.abspath( metadata_dict[ 'datatypes_config' ] )
                                    # Load data types required by tools.
                                    self.__load_datatypes( trans, datatypes_config, relative_install_dir )
                                if 'tools' in metadata_dict:
                                    repository_tools_tups = []
                                    for tool_dict in metadata_dict[ 'tools' ]:
                                        relative_path = tool_dict[ 'tool_config' ]
                                        guid = tool_dict[ 'guid' ]
                                        tool = trans.app.toolbox.load_tool( os.path.abspath( relative_path ) )
                                        repository_tools_tups.append( ( relative_path, guid, tool ) )
                                    if repository_tools_tups:
                                        sample_files = metadata_dict.get( 'sample_files', [] )
                                        # Handle missing data table entries for tool parameters that are dynamically generated select lists.
                                        repository_tools_tups = handle_missing_data_table_entry( trans.app, tool_path, sample_files, repository_tools_tups )
                                        # Handle missing index files for tool parameters that are dynamically generated select lists.
                                        repository_tools_tups = handle_missing_index_file( trans.app, tool_path, sample_files, repository_tools_tups )
                                        # Handle tools that use fabric scripts to install dependencies.
                                        handle_tool_dependencies( current_working_dir, relative_install_dir, repository_tools_tups )
                                        # Generate an in-memory tool conf section that includes the new tools.
                                        new_tool_section = generate_tool_panel_section( name,
                                                                                        repository_clone_url,
                                                                                        changeset_revision,
                                                                                        tool_section,
                                                                                        repository_tools_tups )
                                        # Create a temporary file to persist the in-memory tool section
                                        # TODO: Figure out how to do this in-memory using xml.etree.
                                        tmp_name = tempfile.NamedTemporaryFile().name
                                        persisted_new_tool_section = open( tmp_name, 'wb' )
                                        persisted_new_tool_section.write( new_tool_section )
                                        persisted_new_tool_section.close()
                                        # Parse the persisted tool panel section
                                        tree = parse_xml( tmp_name )
                                        root = tree.getroot()
                                        # Load the tools in the section into the tool panel.
                                        trans.app.toolbox.load_section_tag_set( root, trans.app.toolbox.tool_panel, tool_path )
                                        # Remove the temporary file
                                        try:
                                            os.unlink( tmp_name )
                                        except:
                                            pass
                                        # Append the new section to the shed_tool_config file.
                                        add_shed_tool_conf_entry( trans.app, shed_tool_conf, new_tool_section )
                                        if trans.app.toolbox_search.enabled:
                                            # If search support for tools is enabled, index the new installed tools.
                                            trans.app.toolbox_search = ToolBoxSearch( trans.app.toolbox )
                                # Add a new record to the tool_shed_repository table if one doesn't
                                # already exist.  If one exists but is marked deleted, undelete it.
                                create_or_undelete_tool_shed_repository( trans.app,
                                                                         name,
                                                                         description,
                                                                         changeset_revision,
                                                                         repository_clone_url,
                                                                         metadata_dict )
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
                    message += 'Installed %d %s and all tools were loaded into tool panel section <b>%s</b>:<br/>Installed repositories: ' % \
                        ( num_repositories_installed, inflector.cond_plural( num_repositories_installed, 'repository' ), tool_section.name )
                    for i, repo_name in enumerate( installed_repository_names ):
                        if i == len( installed_repository_names ) -1:
                            message += '%s.<br/>' % repo_name
                        else:
                            message += '%s, ' % repo_name
                return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                  action='browse_repositories',
                                                                  message=message,
                                                                  status=status ) )
            else:
                message = 'Choose the section in your tool panel to contain the installed tools.'
                status = 'error'
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
        relative_install_dir = self.__get_relative_install_dir( trans, repository )
        repo_files_dir = os.path.abspath( os.path.join( relative_install_dir, repository.name ) )
        if params.get( 'edit_repository_button', False ):
            if description != repository.description:
                repository.description = description
                trans.sa_session.add( repository )
                trans.sa_session.flush()
            message = "The repository information has been updated."
        elif params.get( 'set_metadata_button', False ):
            repository_clone_url = self.__generate_clone_url( trans, repository )
            metadata_dict = generate_metadata( trans.app.toolbox, relative_install_dir, repository_clone_url )
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
        tool_shed_url = get_url_from_repository_tool_shed( trans, repository )
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
                relative_install_dir = self.__get_relative_install_dir( trans, repository )
                if relative_install_dir:
                    # Update the cloned repository to changeset_revision.
                    repo_files_dir = os.path.join( relative_install_dir, name )
                    log.debug( "Updating cloned repository named '%s' from revision '%s' to revision '%s'..." % \
                        ( name, changeset_revision, latest_changeset_revision ) )
                    cmd = 'hg pull'
                    tmp_name = tempfile.NamedTemporaryFile().name
                    tmp_stderr = open( tmp_name, 'wb' )
                    os.chdir( repo_files_dir )
                    proc = subprocess.Popen( cmd, shell=True, stderr=tmp_stderr.fileno() )
                    returncode = proc.wait()
                    os.chdir( current_working_dir )
                    tmp_stderr.close()
                    if returncode == 0:
                        cmd = 'hg update -r %s' % latest_changeset_revision
                        tmp_name = tempfile.NamedTemporaryFile().name
                        tmp_stderr = open( tmp_name, 'wb' )
                        os.chdir( repo_files_dir )
                        proc = subprocess.Popen( cmd, shell=True, stderr=tmp_stderr.fileno() )
                        returncode = proc.wait()
                        os.chdir( current_working_dir )
                        tmp_stderr.close()
                        if returncode == 0:
                            # Update the repository changeset_revision in the database.
                            repository.changeset_revision = latest_changeset_revision
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
                    tool = trans.app.toolbox.load_tool( os.path.abspath( metadata[ 'tool_config' ] ) )
                    break
        return trans.fill_template( "/admin/tool_shed_repository/view_tool_metadata.mako",
                                    repository=repository,
                                    tool=tool,
                                    metadata=metadata,
                                    message=message,
                                    status=status )
    def __get_relative_install_dir( self, trans, repository ):
        # Get the directory where the repository is install.
        tool_shed = self.__clean_tool_shed_url( repository.tool_shed )
        partial_install_dir = '%s/repos/%s/%s/%s' % ( tool_shed, repository.owner, repository.name, repository.changeset_revision )
        # Get the relative tool installation paths from each of the shed tool configs.
        shed_tool_confs = trans.app.toolbox.shed_tool_confs
        relative_install_dir = None
        # The shed_tool_confs dictionary contains { shed_conf_filename : tool_path } pairs.
        for shed_conf_filename, tool_path in shed_tool_confs.items():
            relative_install_dir = os.path.join( tool_path, partial_install_dir )
            if os.path.isdir( relative_install_dir ):
                break
        return relative_install_dir
    def __load_datatypes( self, trans, datatypes_config, relative_intall_dir ):
        imported_module = None
        # Parse datatypes_config.
        tree = parse_xml( datatypes_config )
        datatypes_config_root = tree.getroot()
        relative_path_to_datatype_file_name = None
        datatype_files = datatypes_config_root.find( 'datatype_files' )
        # Currently only a single datatype_file is supported.  For example:
        # <datatype_files>
        #    <datatype_file name="gmap.py"/>
        # </datatype_files>
        for elem in datatype_files.findall( 'datatype_file' ):
            datatype_file_name = elem.get( 'name', None )
            if datatype_file_name:
                # Find the file in the installed repository.
                for root, dirs, files in os.walk( relative_intall_dir ):
                    if root.find( '.hg' ) < 0:
                        for name in files:
                            if name == datatype_file_name:
                                relative_path_to_datatype_file_name = os.path.join( root, name )
                                break
                break
        if relative_path_to_datatype_file_name:
            relative_head, relative_tail = os.path.split( relative_path_to_datatype_file_name )
            registration = datatypes_config_root.find( 'registration' )
            # Get the module by parsing the <datatype> tag.
            for elem in registration.findall( 'datatype' ):
                # A 'type' attribute is currently required.  The attribute
                # should be something like: type="gmap:GmapDB".
                dtype = elem.get( 'type', None )
                if dtype:
                    fields = dtype.split( ':' )
                    datatype_module = fields[0]
                    datatype_class_name = fields[1]
                    # Since we currently support only a single datatype_file,
                    #  we have what we need.
                    break
            try:
                sys.path.insert( 0, relative_head )
                imported_module = __import__( datatype_module )
                sys.path.pop( 0 )
            except Exception, e:
                log.debug( "Exception importing datatypes code file included in installed repository: %s" % str( e ) )
        trans.app.datatypes_registry.load_datatypes( root_dir=trans.app.config.root, config=datatypes_config, imported_module=imported_module )
    def __clean_tool_shed_url( self, tool_shed_url ):
        if tool_shed_url.find( ':' ) > 0:
            # Eliminate the port, if any, since it will result in an invalid directory name.
            return tool_shed_url.split( ':' )[ 0 ]
        return tool_shed_url.rstrip( '/' )
    def __generate_tool_path( self, repository_clone_url, changeset_revision ):
        """
        Generate a tool path that guarantees repositories with the same name will always be installed
        in different directories.  The tool path will be of the form:
        <tool shed url>/repos/<repository owner>/<repository name>/<changeset revision>
        http://test@bx.psu.edu:9009/repos/test/filter
        """
        tmp_url = clean_repository_clone_url( repository_clone_url )
        # Now tmp_url is something like: bx.psu.edu:9009/repos/some_username/column
        items = tmp_url.split( 'repos' )
        tool_shed_url = items[ 0 ]
        repo_path = items[ 1 ]
        tool_shed_url = self.__clean_tool_shed_url( tool_shed_url )
        return '%s/repos%s/%s' % ( tool_shed_url, repo_path, changeset_revision )
    def __generate_clone_url( self, trans, repository ):
        """Generate the URL for cloning a repository."""
        tool_shed_url = get_url_from_repository_tool_shed( trans, repository )
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
def get_repository_by_name_owner_changeset_revision( trans, name, owner, changeset_revision ):
    """Get a repository from the database via name owner and changeset_revision"""
    return trans.sa_session.query( trans.model.ToolShedRepository ) \
                             .filter( and_( trans.model.ToolShedRepository.table.c.name == name,
                                            trans.model.ToolShedRepository.table.c.owner == owner,
                                            trans.model.ToolShedRepository.table.c.changeset_revision == changeset_revision ) ) \
                             .first()
def get_repository_by_shed_name_owner_changeset_revision( app, tool_shed, name, owner, changeset_revision ):
    # This method is used by the InstallManager, which does not have access to trans.
    sa_session = app.model.context.current
    if tool_shed.find( '//' ) > 0:
        tool_shed = tool_shed.split( '//' )[1]
    return sa_session.query( app.model.ToolShedRepository ) \
                     .filter( and_( app.model.ToolShedRepository.table.c.tool_shed == tool_shed,
                                    app.model.ToolShedRepository.table.c.name == name,
                                    app.model.ToolShedRepository.table.c.owner == owner,
                                    app.model.ToolShedRepository.table.c.changeset_revision == changeset_revision ) ) \
                     .first()
def get_url_from_repository_tool_shed( trans, repository ):
    # The stored value of repository.tool_shed is something like:
    # toolshed.g2.bx.psu.edu
    # We need the URL to this tool shed, which is something like:
    # http://toolshed.g2.bx.psu.edu/
    for shed_name, shed_url in trans.app.tool_shed_registry.tool_sheds.items():
        if shed_url.find( repository.tool_shed ) >= 0:
            if shed_url.endswith( '/' ):
                shed_url = shed_url.rstrip( '/' )
            return shed_url
    # The tool shed from which the repository was originally
    # installed must no longer be configured in tool_sheds_conf.xml.
    return None
def generate_tool_panel_section( repository_name, repository_clone_url, changeset_revision, tool_section, repository_tools_tups, owner='' ):
    """
    Write an in-memory tool panel section so we can load it into the tool panel and then
    append it to the appropriate shed tool config.
    TODO: re-write using ElementTree.
    """
    tmp_url = clean_repository_clone_url( repository_clone_url )
    if not owner:
        owner = get_repository_owner( tmp_url )
    section_str = ''
    section_str += '    <section name="%s" id="%s">\n' % ( tool_section.name, tool_section.id )
    for repository_tool_tup in repository_tools_tups:
        tool_file_path, guid, tool = repository_tool_tup
        section_str += '        <tool file="%s" guid="%s">\n' % ( tool_file_path, guid )
        section_str += '            <tool_shed>%s</tool_shed>\n' % tmp_url.split( 'repos' )[ 0 ].rstrip( '/' )
        section_str += '            <repository_name>%s</repository_name>\n' % repository_name
        section_str += '            <repository_owner>%s</repository_owner>\n' % owner
        section_str += '            <changeset_revision>%s</changeset_revision>\n' % changeset_revision
        section_str += '            <id>%s</id>\n' % tool.id
        section_str += '            <version>%s</version>\n' % tool.version
        section_str += '        </tool>\n'
    section_str += '    </section>\n'
    return section_str
def get_repository_owner( cleaned_repository_url ):
    items = cleaned_repository_url.split( 'repos' )
    repo_path = items[ 1 ]
    if repo_path.startswith( '/' ):
        repo_path = repo_path.replace( '/', '', 1 )
    return repo_path.lstrip( '/' ).split( '/' )[ 0 ]
def generate_tool_guid( repository_clone_url, tool ):
    """
    Generate a guid for the installed tool.  It is critical that this guid matches the guid for
    the tool in the Galaxy tool shed from which it is being installed.  The form of the guid is    
    <tool shed host>/repos/<repository owner>/<repository name>/<tool id>/<tool version>
    """
    tmp_url = clean_repository_clone_url( repository_clone_url )
    return '%s/%s/%s' % ( tmp_url, tool.id, tool.version )
def clean_repository_clone_url( repository_clone_url ):
    if repository_clone_url.find( '@' ) > 0:
        # We have an url that includes an authenticated user, something like:
        # http://test@bx.psu.edu:9009/repos/some_username/column
        items = repository_clone_url.split( '@' )
        tmp_url = items[ 1 ]
    elif repository_clone_url.find( '//' ) > 0:
        # We have an url that includes only a protocol, something like:
        # http://bx.psu.edu:9009/repos/some_username/column
        items = repository_clone_url.split( '//' )
        tmp_url = items[ 1 ]
    else:
        tmp_url = repository_clone_url
    return tmp_url
def generate_metadata( toolbox, relative_install_dir, repository_clone_url ):
    """
    Browse the repository files on disk to generate metadata.  Since we are using disk files, it
    is imperative that the repository is updated to the desired change set revision before metadata
    is generated.  This method is used by the InstallManager, which does not have access to trans.
    """
    metadata_dict = {}
    sample_files = []
    datatypes_config = None
    # Find datatypes_conf.xml if it exists.
    for root, dirs, files in os.walk( relative_install_dir ):
        if root.find( '.hg' ) < 0:
            for name in files:
                if name == 'datatypes_conf.xml':
                    relative_path = os.path.join( root, name )
                    datatypes_config = os.path.abspath( relative_path )
                    break
    if datatypes_config:
        metadata_dict[ 'datatypes_config' ] = relative_path
        metadata_dict = generate_datatypes_metadata( datatypes_config, metadata_dict )
    # Find all special .sample files.
    for root, dirs, files in os.walk( relative_install_dir ):
        if root.find( '.hg' ) < 0:
            for name in files:
                if name.endswith( '.sample' ):
                    sample_files.append( os.path.join( root, name ) )
    if sample_files:
        metadata_dict[ 'sample_files' ] = sample_files
    # Find all tool configs and exported workflows.
    for root, dirs, files in os.walk( relative_install_dir ):
        if root.find( '.hg' ) < 0 and root.find( 'hgrc' ) < 0:
            if '.hg' in dirs:
                dirs.remove( '.hg' )
            for name in files:
                # Find all tool configs.
                if name != 'datatypes_conf.xml' and name.endswith( '.xml' ):
                    full_path = os.path.abspath( os.path.join( root, name ) )
                    try:
                        tool = toolbox.load_tool( full_path )
                    except Exception, e:
                        tool = None
                    if tool is not None:
                        tool_config = os.path.join( root, name )
                        metadata_dict = generate_tool_metadata( tool_config, tool, repository_clone_url, metadata_dict )
                # Find all exported workflows
                elif name.endswith( '.ga' ):
                    relative_path = os.path.join( root, name )
                    fp = open( relative_path, 'rb' )
                    workflow_text = fp.read()
                    fp.close()
                    exported_workflow_dict = from_json_string( workflow_text )
                    if 'a_galaxy_workflow' in exported_workflow_dict and exported_workflow_dict[ 'a_galaxy_workflow' ] == 'true':
                        metadata_dict = generate_workflow_metadata( relative_path, exported_workflow_dict, metadata_dict )
    return metadata_dict
def generate_datatypes_metadata( datatypes_config, metadata_dict ):
    """
    Update the received metadata_dict with changes that have been applied
    to the received datatypes_config.  This method is used by the InstallManager,
    which does not have access to trans.
    """
    # Parse datatypes_config.
    tree = ElementTree.parse( datatypes_config )
    root = tree.getroot()
    ElementInclude.include( root )
    repository_datatype_code_files = []
    datatype_files = root.find( 'datatype_files' )
    if datatype_files:
        for elem in datatype_files.findall( 'datatype_file' ):
            name = elem.get( 'name', None )
            repository_datatype_code_files.append( name )
        metadata_dict[ 'datatype_files' ] = repository_datatype_code_files
    datatypes = []
    registration = root.find( 'registration' )
    if registration:
        for elem in registration.findall( 'datatype' ):
            extension = elem.get( 'extension', None ) 
            dtype = elem.get( 'type', None )
            mimetype = elem.get( 'mimetype', None )
            datatypes.append( dict( extension=extension,
                                    dtype=dtype,
                                    mimetype=mimetype ) )
        metadata_dict[ 'datatypes' ] = datatypes
    return metadata_dict
def generate_tool_metadata( tool_config, tool, repository_clone_url, metadata_dict ):
    """
    Update the received metadata_dict with changes that have been
    applied to the received tool.  This method is used by the InstallManager,
    which does not have access to trans.
    """
    # Generate the guid
    guid = generate_tool_guid( repository_clone_url, tool )
    # Handle tool.requirements.
    tool_requirements = []
    for tr in tool.requirements:
        name=tr.name
        type=tr.type
        if type == 'fabfile':
            version = None
            fabfile = tr.fabfile
            method = tr.method
        else:
            version = tr.version
            fabfile = None
            method = None
        requirement_dict = dict( name=name,
                                 type=type,
                                 version=version,
                                 fabfile=fabfile,
                                 method=method )
        tool_requirements.append( requirement_dict )
    # Handle tool.tests.
    tool_tests = []
    if tool.tests:
        for ttb in tool.tests:
            test_dict = dict( name=ttb.name,
                              required_files=ttb.required_files,
                              inputs=ttb.inputs,
                              outputs=ttb.outputs )
            tool_tests.append( test_dict )
    tool_dict = dict( id=tool.id,
                      guid=guid,
                      name=tool.name,
                      version=tool.version,
                      description=tool.description,
                      version_string_cmd = tool.version_string_cmd,
                      tool_config=tool_config,
                      requirements=tool_requirements,
                      tests=tool_tests )
    if 'tools' in metadata_dict:
        metadata_dict[ 'tools' ].append( tool_dict )
    else:
        metadata_dict[ 'tools' ] = [ tool_dict ]
    return metadata_dict
def generate_workflow_metadata( relative_path, exported_workflow_dict, metadata_dict ):
    """
    Update the received metadata_dict with changes that have been applied
    to the received exported_workflow_dict.  Store everything in the database.
    This method is used by the InstallManager, which does not have access to trans.
    """
    if 'workflows' in metadata_dict:
        metadata_dict[ 'workflows' ].append( ( relative_path, exported_workflow_dict ) )
    else:
        metadata_dict[ 'workflows' ] = [ ( relative_path, exported_workflow_dict ) ]
    return metadata_dict
def handle_missing_data_table_entry( app, tool_path, sample_files, repository_tools_tups ):
    """
    Inspect each tool to see if any have input parameters that are dynamically
    generated select lists that require entries in the tool_data_table_conf.xml file.
    This method is used by the InstallManager, which does not have access to trans.
    """
    missing_data_table_entry = False
    for index, repository_tools_tup in enumerate( repository_tools_tups ):
        tup_path, guid, repository_tool = repository_tools_tup
        if repository_tool.params_with_missing_data_table_entry:
            missing_data_table_entry = True
            break
    if missing_data_table_entry:
        # The repository must contain a tool_data_table_conf.xml.sample file that includes
        # all required entries for all tools in the repository.
        for sample_file in sample_files:
            head, tail = os.path.split( sample_file )
            if tail == 'tool_data_table_conf.xml.sample':
                break
        error, correction_msg = handle_sample_tool_data_table_conf_file( app, sample_file )
        if error:
            # TODO: Do more here than logging an exception.
            log.debug( exception_msg )
        # Reload the tool into the local list of repository_tools_tups.
        repository_tool = app.toolbox.load_tool( os.path.join( tool_path, tup_path ) )
        repository_tools_tups[ index ] = ( tup_path, repository_tool )
    return repository_tools_tups
def handle_missing_index_file( app, tool_path, sample_files, repository_tools_tups ):
    """
    Inspect each tool to see if it has any input parameters that
    are dynamically generated select lists that depend on a .loc file.
    This method is used by the InstallManager, which does not have access to trans.
    """
    missing_files_handled = []
    for index, repository_tools_tup in enumerate( repository_tools_tups ):
        tup_path, guid, repository_tool = repository_tools_tup
        params_with_missing_index_file = repository_tool.params_with_missing_index_file
        for param in params_with_missing_index_file:
            options = param.options
            missing_head, missing_tail = os.path.split( options.missing_index_file )
            if missing_tail not in missing_files_handled:
                # The repository must contain the required xxx.loc.sample file.
                for sample_file in sample_files:
                    sample_head, sample_tail = os.path.split( sample_file )
                    if sample_tail == '%s.sample' % missing_tail:
                        copy_sample_loc_file( app, sample_file )
                        if options.tool_data_table and options.tool_data_table.missing_index_file:
                            options.tool_data_table.handle_found_index_file( options.missing_index_file )
                        missing_files_handled.append( missing_tail )
                        break
        # Reload the tool into the local list of repository_tools_tups.
        repository_tool = app.toolbox.load_tool( os.path.join( tool_path, tup_path ) )
        repository_tools_tups[ index ] = ( tup_path, guid, repository_tool )
    return repository_tools_tups
def handle_tool_dependencies( current_working_dir, repo_files_dir, repository_tools_tups ):
    """
    Inspect each tool to see if it includes a "requirement" that refers to a fabric
    script.  For those that do, execute the fabric script to install tool dependencies.
    This method is used by the InstallManager, which does not have access to trans.
    """
    for index, repository_tools_tup in enumerate( repository_tools_tups ):
        tup_path, guid, repository_tool = repository_tools_tup
        for requirement in repository_tool.requirements:
            if requirement.type == 'fabfile':
                log.debug( 'Executing fabric script to install dependencies for tool "%s"...' % repository_tool.name )
                fabfile = requirement.fabfile
                method = requirement.method
                # Find the relative path to the fabfile.
                relative_fabfile_path = None
                for root, dirs, files in os.walk( repo_files_dir ):
                    for name in files:
                        if name == fabfile:
                            relative_fabfile_path = os.path.join( root, name )
                            break
                if relative_fabfile_path:
                    # cmd will look something like: fab -f fabfile.py install_bowtie
                    cmd = 'fab -f %s %s' % ( relative_fabfile_path, method )
                    tmp_name = tempfile.NamedTemporaryFile().name
                    tmp_stderr = open( tmp_name, 'wb' )
                    os.chdir( repo_files_dir )
                    proc = subprocess.Popen( cmd, shell=True, stderr=tmp_stderr.fileno() )
                    returncode = proc.wait()
                    os.chdir( current_working_dir )
                    tmp_stderr.close()
                    if returncode != 0:
                        # TODO: do something more here than logging the problem.
                        tmp_stderr = open( tmp_name, 'rb' )
                        error = tmp_stderr.read()
                        tmp_stderr.close()
                        log.debug( 'Problem installing dependencies for tool "%s"\n%s' % ( repository_tool.name, error ) )
def add_shed_tool_conf_entry( app, shed_tool_conf, new_tool_section ):
    """
    Add an entry in the shed_tool_conf file. An entry looks something like:
    <section name="Filter and Sort" id="filter">
        <tool file="filter/filtering.xml" guid="toolshed.g2.bx.psu.edu/repos/test/filter/1.0.2"/>
    </section>
    This method is used by the InstallManager, which does not have access to trans.
    """
    # Make a backup of the hgweb.config file since we're going to be changing it.
    if not os.path.exists( shed_tool_conf ):
        output = open( shed_tool_conf, 'w' )
        output.write( '<?xml version="1.0"?>\n' )
        output.write( '<toolbox tool_path="%s">\n' % tool_path )
        output.write( '</toolbox>\n' )
        output.close()
    # Make a backup of the shed_tool_conf file.
    today = date.today()
    backup_date = today.strftime( "%Y_%m_%d" )
    shed_tool_conf_copy = '%s/%s_%s_backup' % ( app.config.root, shed_tool_conf, backup_date )
    shutil.copy( os.path.abspath( shed_tool_conf ), os.path.abspath( shed_tool_conf_copy ) )
    tmp_fd, tmp_fname = tempfile.mkstemp()
    new_shed_tool_conf = open( tmp_fname, 'wb' )
    for i, line in enumerate( open( shed_tool_conf ) ):
        if line.startswith( '</toolbox>' ):
            # We're at the end of the original config file, so add our entry.
            new_shed_tool_conf.write( new_tool_section )
            new_shed_tool_conf.write( line )
        else:
            new_shed_tool_conf.write( line )
    new_shed_tool_conf.close()
    shutil.move( tmp_fname, os.path.abspath( shed_tool_conf ) )
def create_or_undelete_tool_shed_repository( app, name, description, changeset_revision, repository_clone_url, metadata_dict, owner='' ):
    # This method is used by the InstallManager, which does not have access to trans.
    sa_session = app.model.context.current
    tmp_url = clean_repository_clone_url( repository_clone_url )
    tool_shed = tmp_url.split( 'repos' )[ 0 ].rstrip( '/' )
    if not owner:
        owner = get_repository_owner( tmp_url )
    includes_datatypes = 'datatypes_config' in metadata_dict
    flush_needed = False
    tool_shed_repository = get_repository_by_shed_name_owner_changeset_revision( app, tool_shed, name, owner, changeset_revision )
    if tool_shed_repository:
        if tool_shed_repository.deleted:
            tool_shed_repository.deleted = False
            # Reset includes_datatypes in case metadata changed since last installed.
            tool_shed_repository.includes_datatypes = includes_datatypes
            flush_needed = True
    else:
        tool_shed_repository = app.model.ToolShedRepository( tool_shed=tool_shed,
                                                             name=name,
                                                             description=description,
                                                             owner=owner,
                                                             changeset_revision=changeset_revision,
                                                             metadata=metadata_dict,
                                                             includes_datatypes=includes_datatypes )
        flush_needed = True
    if flush_needed:
        sa_session.add( tool_shed_repository )
        sa_session.flush()
