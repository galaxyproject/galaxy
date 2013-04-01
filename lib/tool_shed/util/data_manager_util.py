import logging
import os
from galaxy import util
import tool_shed.util.shed_util_common as suc

log = logging.getLogger( __name__ )

def data_manager_config_elems_to_xml_file( app, config_elems, config_filename ):#, shed_tool_conf_filename ):
    # Persist the current in-memory list of config_elems to a file named by the value of config_filename.  
    fh = open( config_filename, 'wb' )
    fh.write( '<?xml version="1.0"?>\n<data_managers>\n' )#% ( shed_tool_conf_filename ))
    for elem in config_elems:
        fh.write( util.xml_to_string( elem, pretty=True ) )
    fh.write( '</data_managers>\n' )
    fh.close()

def install_data_managers( app, shed_data_manager_conf_filename, metadata_dict, shed_config_dict, relative_install_dir, repository, repository_tools_tups ):
    rval = []
    if 'data_manager' in metadata_dict:
        repository_tools_by_guid = {}
        for tool_tup in repository_tools_tups:
            repository_tools_by_guid[ tool_tup[ 1 ] ] = dict( tool_config_filename=tool_tup[ 0 ], tool=tool_tup[ 2 ] )
        # Load existing data managers.
        config_elems = [ elem for elem in util.parse_xml( shed_data_manager_conf_filename ).getroot() ]
        repo_data_manager_conf_filename = metadata_dict['data_manager'].get( 'config_filename', None )
        if repo_data_manager_conf_filename is None:
            log.debug( "No data_manager_conf.xml file has been defined." )
            return rval
        data_manager_config_has_changes = False
        relative_repo_data_manager_dir = os.path.join( shed_config_dict.get( 'tool_path', '' ), relative_install_dir )
        repo_data_manager_conf_filename = os.path.join( relative_repo_data_manager_dir, repo_data_manager_conf_filename )
        tree = util.parse_xml( repo_data_manager_conf_filename )
        root = tree.getroot()
        for elem in root:
            if elem.tag == 'data_manager':
                data_manager_id = elem.get( 'id', None )
                if data_manager_id is None:
                    log.error( "A data manager was defined that does not have an id and will not be installed:\n%s" % ( util.xml_to_string( elem ) ) )
                    continue
                data_manager_dict = metadata_dict['data_manager'].get( 'data_managers', {} ).get( data_manager_id, None )
                if data_manager_dict is None:
                    log.error( "Data manager metadata is not defined properly for '%s'." % ( data_manager_id ) )
                    continue
                guid = data_manager_dict.get( 'guid', None )
                if guid is None:
                    log.error( "Data manager guid '%s' is not set in metadata for '%s'." % ( guid, data_manager_id ) )
                    continue
                elem.set( 'guid', guid )
                tool_guid = data_manager_dict.get( 'tool_guid', None )
                if tool_guid is None:
                    log.error( "Data manager tool guid '%s' is not set in metadata for '%s'." % ( tool_guid, data_manager_id ) )
                    continue
                tool_dict = repository_tools_by_guid.get( tool_guid, None )
                if tool_dict is None:
                    log.error( "Data manager tool guid '%s' could not be found for '%s'. Perhaps the tool is invalid?" % ( tool_guid, data_manager_id ) )
                    continue
                tool = tool_dict.get( 'tool', None )
                if tool is None:
                    log.error( "Data manager tool with guid '%s' could not be found for '%s'. Perhaps the tool is invalid?" % ( tool_guid, data_manager_id ) )
                    continue
                tool_config_filename = tool_dict.get( 'tool_config_filename', None )
                if tool_config_filename is None:
                    log.error( "Data manager metadata is missing 'tool_config_file' for '%s'." % ( data_manager_id ) )
                    continue
                elem.set( 'shed_conf_file', shed_config_dict['config_filename'] )
                if elem.get( 'tool_file', None ) is not None:
                    del elem.attrib[ 'tool_file' ] #remove old tool_file info
                tool_elem = suc.generate_tool_elem( repository.tool_shed,
                                                    repository.name,
                                                    repository.installed_changeset_revision,
                                                    repository.owner,
                                                    tool_config_filename,
                                                    tool,
                                                    None )
                elem.insert( 0, tool_elem )
                data_manager = app.data_managers.load_manager_from_elem( elem, tool_path=shed_config_dict.get( 'tool_path', '' ), replace_existing=True )
                if data_manager:
                    rval.append( data_manager )
            else:
                log.warning( "Encountered unexpected element '%s':\n%s" % ( elem.tag, util.xml_to_string( elem ) ) )
            config_elems.append( elem )
            data_manager_config_has_changes = True
        # Persist the altered shed_data_manager_config file.
        if data_manager_config_has_changes:
            data_manager_config_elems_to_xml_file( app, config_elems, shed_data_manager_conf_filename  )
    return rval

def remove_from_data_manager( app, repository ):
    metadata_dict = repository.metadata
    if metadata_dict and 'data_manager' in metadata_dict:
        shed_data_manager_conf_filename = app.config.shed_data_manager_config_file
        tree = util.parse_xml( shed_data_manager_conf_filename )
        root = tree.getroot()
        assert root.tag == 'data_managers', 'The file provided (%s) for removing data managers from is not a valid data manager xml file.' % ( shed_data_manager_conf_filename )
        guids = [ data_manager_dict.get( 'guid' ) for data_manager_dict in metadata_dict.get( 'data_manager', {} ).get( 'data_managers', {} ).itervalues() if 'guid' in data_manager_dict ]
        load_old_data_managers_by_guid = {}
        data_manager_config_has_changes = False
        config_elems = []
        for elem in root:
            # Match Data Manager elements by guid and installed_changeset_revision
            elem_matches_removed_data_manager = False
            if elem.tag == 'data_manager':
                guid = elem.get( 'guid', None )
                if guid in guids:
                    tool_elem = elem.find( 'tool' )
                    if tool_elem is not None:
                        installed_changeset_revision_elem = tool_elem.find( 'installed_changeset_revision' )
                        if installed_changeset_revision_elem is not None:
                            if installed_changeset_revision_elem.text == repository.installed_changeset_revision:
                                elem_matches_removed_data_manager = True
                            else:
                                # This is a different version, which had been previously overridden
                                load_old_data_managers_by_guid[ guid ] = elem
            if elem_matches_removed_data_manager:
                data_manager_config_has_changes = True
            else:
                config_elems.append( elem )
        # Remove data managers from in memory
        app.data_managers.remove_manager( guids )
        # Load other versions of any now uninstalled data managers, if any
        for elem in load_old_data_managers_by_guid.itervalues():
            app.data_managers.load_manager_from_elem( elem )
        # Persist the altered shed_data_manager_config file.
        if data_manager_config_has_changes:
            data_manager_config_elems_to_xml_file( app, config_elems, shed_data_manager_conf_filename  )
