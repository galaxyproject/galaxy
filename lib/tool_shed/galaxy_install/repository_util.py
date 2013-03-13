import tool_shed.util.shed_util as shed_util
import tool_shed.util.shed_util_common as suc
import tool_shed.util.metadata_util as metadata_util

def handle_repository_contents( app, tool_shed_repository, tool_path, repository_clone_url, relative_install_dir, tool_shed=None, tool_section=None,
                                shed_tool_conf=None, reinstalling=False ):
    """
    Generate the metadata for the installed tool shed repository, among other things.  This method is called from Galaxy (never the tool shed)
    when an admin is installing a new repository or reinstalling an uninstalled repository.
    """
    sa_session = app.model.context.current
    shed_config_dict = app.toolbox.get_shed_config_dict_by_filename( shed_tool_conf )
    metadata_dict, invalid_file_tups = metadata_util.generate_metadata_for_changeset_revision( app=app,
                                                                                               repository=tool_shed_repository,
                                                                                               changeset_revision=tool_shed_repository.changeset_revision,
                                                                                               repository_clone_url=repository_clone_url,
                                                                                               shed_config_dict=shed_config_dict,
                                                                                               relative_install_dir=relative_install_dir,
                                                                                               repository_files_dir=None,
                                                                                               resetting_all_metadata_on_repository=False,
                                                                                               updating_installed_repository=False,
                                                                                               persist=True )
    tool_shed_repository.metadata = metadata_dict
    sa_session.add( tool_shed_repository )
    sa_session.flush()
    if 'tool_dependencies' in metadata_dict and not reinstalling:
        tool_dependencies = shed_util.create_tool_dependency_objects( app, tool_shed_repository, relative_install_dir, set_status=True )
    if 'tools' in metadata_dict:
        tool_panel_dict = shed_util.generate_tool_panel_dict_for_new_install( metadata_dict[ 'tools' ], tool_section )
        sample_files = metadata_dict.get( 'sample_files', [] )
        tool_index_sample_files = shed_util.get_tool_index_sample_files( sample_files )
        shed_util.copy_sample_files( self.app, tool_index_sample_files, tool_path=tool_path )
        sample_files_copied = [ str( s ) for s in tool_index_sample_files ]
        repository_tools_tups = suc.get_repository_tools_tups( app, metadata_dict )
        if repository_tools_tups:
            # Handle missing data table entries for tool parameters that are dynamically generated select lists.
            repository_tools_tups = shed_util.handle_missing_data_table_entry( app, relative_install_dir, tool_path, repository_tools_tups )
            # Handle missing index files for tool parameters that are dynamically generated select lists.
            repository_tools_tups, sample_files_copied = shed_util.handle_missing_index_file( app,
                                                                                              tool_path,
                                                                                              sample_files,
                                                                                              repository_tools_tups,
                                                                                              sample_files_copied )
            # Copy remaining sample files included in the repository to the ~/tool-data directory of the local Galaxy instance.
            shed_util.copy_sample_files( app, sample_files, tool_path=tool_path, sample_files_copied=sample_files_copied )
            shed_util.add_to_tool_panel( app=app,
                                         repository_name=tool_shed_repository.name,
                                         repository_clone_url=repository_clone_url,
                                         changeset_revision=tool_shed_repository.installed_changeset_revision,
                                         repository_tools_tups=repository_tools_tups,
                                         owner=tool_shed_repository.owner,
                                         shed_tool_conf=shed_tool_conf,
                                         tool_panel_dict=tool_panel_dict,
                                         new_install=True )
    if 'data_manager' in metadata_dict:
        new_data_managers = shed_util.install_data_managers( app,
                                                             app.config.shed_data_manager_config_file,
                                                             metadata_dict,
                                                             shed_config_dict,
                                                             relative_install_dir,
                                                             tool_shed_repository,
                                                             repository_tools_tups )
    if 'datatypes' in metadata_dict:
        tool_shed_repository.status = app.model.ToolShedRepository.installation_status.LOADING_PROPRIETARY_DATATYPES
        if not tool_shed_repository.includes_datatypes:
            tool_shed_repository.includes_datatypes = True
        sa_session.add( tool_shed_repository )
        sa_session.flush()
        files_dir = relative_install_dir
        if shed_config_dict.get( 'tool_path' ):
            files_dir = os.path.join( shed_config_dict['tool_path'], files_dir )
        datatypes_config = suc.get_config_from_disk( 'datatypes_conf.xml', files_dir )
        # Load data types required by tools.
        converter_path, display_path = shed_util.alter_config_and_load_prorietary_datatypes( app, datatypes_config, files_dir, override=False )
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
            app.datatypes_registry.load_datatype_converters( app.toolbox, installed_repository_dict=repository_dict )
        if display_path:
            # Load proprietary datatype display applications
            app.datatypes_registry.load_display_applications( installed_repository_dict=repository_dict )
