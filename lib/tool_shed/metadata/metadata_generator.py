import json
import logging
import os
import tempfile

from galaxy import util
from galaxy.datatypes import checkers
from galaxy.model.orm import and_
from galaxy.tools.data_manager.manager import DataManager
from galaxy.tools.test import TestCollectionDef
from galaxy.web import url_for

from tool_shed.repository_types import util as rt_util
from tool_shed.tools import tool_validator

from tool_shed.util import basic_util
from tool_shed.util import common_util
from tool_shed.util import hg_util
from tool_shed.util import readme_util
from tool_shed.util import shed_util_common as suc
from tool_shed.util import tool_dependency_util
from tool_shed.util import tool_util
from tool_shed.util import xml_util

log = logging.getLogger( __name__ )


class MetadataGenerator( object ):

    def __init__( self, app, repository=None, changeset_revision=None, repository_clone_url=None,
                  shed_config_dict=None, relative_install_dir=None, repository_files_dir=None,
                  resetting_all_metadata_on_repository=False, updating_installed_repository=False,
                  persist=False, metadata_dict=None, user=None ):
        self.app = app
        self.user = user
        self.repository = repository
        if self.app.name == 'galaxy':
            if changeset_revision is None and self.repository is not None:
                self.changeset_revision = self.repository.changeset_revision
            else:
                self.changeset_revision = changeset_revision
                
            if repository_clone_url is None and self.repository is not None:
                self.repository_clone_url = common_util.generate_clone_url_for_installed_repository( self.app, self.repository )
            else:
                self.repository_clone_url = repository_clone_url
            if shed_config_dict is None:
                if self.repository is not None:
                    self.shed_config_dict = self.repository.get_shed_config_dict( self.app )
                else:
                    self.shed_config_dict = {}
            else:
                self.shed_config_dict = shed_config_dict
            if relative_install_dir is None and self.repository is not None:
                tool_path, relative_install_dir = self.repository.get_tool_relative_path( self.app )
            if repository_files_dir is None and self.repository is not None:
                repository_files_dir = self.repository.repo_files_directory( self.app )
            if metadata_dict is None:
                # Shed related tool panel configs are only relevant to Galaxy.
                self.metadata_dict = { 'shed_config_filename' : self.shed_config_dict.get( 'config_filename', None ) }
            else:
                self.metadata_dict = metadata_dict
        else:
            # We're in the Tool Shed.
            if changeset_revision is None and self.repository is not None:
                self.changeset_revision = self.repository.tip( self.app )
            else:
                self.changeset_revision = changeset_revision
            if repository_clone_url is None and self.repository is not None:
                self.repository_clone_url = \
                    common_util.generate_clone_url_for_repository_in_tool_shed( self.user, self.repository )
            else:
                self.repository_clone_url = repository_clone_url
            if shed_config_dict is None:
                self.shed_config_dict = {}
            else:
                self.shed_config_dict = shed_config_dict
            if relative_install_dir is None and self.repository is not None:
                relative_install_dir = self.repository.repo_path( self.app )
            if repository_files_dir is None and self.repository is not None:
                repository_files_dir = self.repository.repo_path( self.app )
            if metadata_dict is None:
                self.metadata_dict = {}
            else:
                self.metadata_dict = metadata_dict
        self.relative_install_dir = relative_install_dir
        self.repository_files_dir = repository_files_dir
        self.resetting_all_metadata_on_repository = resetting_all_metadata_on_repository
        self.updating_installed_repository = updating_installed_repository
        self.persist = persist
        self.invalid_file_tups = []
        self.sa_session = app.model.context.current
        self.NOT_TOOL_CONFIGS = [ suc.DATATYPES_CONFIG_FILENAME,
                                  rt_util.REPOSITORY_DEPENDENCY_DEFINITION_FILENAME,
                                  rt_util.TOOL_DEPENDENCY_DEFINITION_FILENAME,
                                  suc.REPOSITORY_DATA_MANAGER_CONFIG_FILENAME ]

    def generate_data_manager_metadata( self, repo_dir, data_manager_config_filename, metadata_dict,
                                        shed_config_dict=None ):
        """
        Update the received metadata_dict with information from the parsed data_manager_config_filename.
        """
        if data_manager_config_filename is None:
            return metadata_dict
        repo_path = self.repository.repo_path( self.app )
        try:
            # Galaxy Side.
            repo_files_directory = self.repository.repo_files_directory( self.app )
            repo_dir = repo_files_directory
        except AttributeError:
            # Tool Shed side.
            repo_files_directory = repo_path
        relative_data_manager_dir = util.relpath( os.path.split( data_manager_config_filename )[0], repo_dir )
        rel_data_manager_config_filename = os.path.join( relative_data_manager_dir,
                                                         os.path.split( data_manager_config_filename )[1] )
        data_managers = {}
        invalid_data_managers = []
        data_manager_metadata = { 'config_filename': rel_data_manager_config_filename,
                                  'data_managers': data_managers,
                                  'invalid_data_managers': invalid_data_managers,
                                  'error_messages': [] }
        metadata_dict[ 'data_manager' ] = data_manager_metadata
        tree, error_message = xml_util.parse_xml( data_manager_config_filename )
        if tree is None:
            # We are not able to load any data managers.
            data_manager_metadata[ 'error_messages' ].append( error_message )
            return metadata_dict
        tool_path = None
        if shed_config_dict:
            tool_path = shed_config_dict.get( 'tool_path', None )
        tools = {}
        for tool in metadata_dict.get( 'tools', [] ):
            tool_conf_name = tool[ 'tool_config' ]
            if tool_path:
                tool_conf_name = os.path.join( tool_path, tool_conf_name )
            tools[ tool_conf_name ] = tool
        root = tree.getroot()
        data_manager_tool_path = root.get( 'tool_path', None )
        if data_manager_tool_path:
            relative_data_manager_dir = os.path.join( relative_data_manager_dir, data_manager_tool_path )
        for i, data_manager_elem in enumerate( root.findall( 'data_manager' ) ):
            tool_file = data_manager_elem.get( 'tool_file', None )
            data_manager_id = data_manager_elem.get( 'id', None )
            if data_manager_id is None:
                log.error( 'Data Manager entry is missing id attribute in "%s".' % ( data_manager_config_filename ) )
                invalid_data_managers.append( { 'index': i,
                                                'error_message': 'Data Manager entry is missing id attribute' } )
                continue
            # FIXME: default behavior is to fall back to tool.name.
            data_manager_name = data_manager_elem.get( 'name', data_manager_id )
            version = data_manager_elem.get( 'version', DataManager.DEFAULT_VERSION )
            guid = self.generate_guid_for_object( DataManager.GUID_TYPE, data_manager_id, version )
            data_tables = []
            if tool_file is None:
                log.error( 'Data Manager entry is missing tool_file attribute in "%s".' % ( data_manager_config_filename ) )
                invalid_data_managers.append( { 'index': i,
                                                'error_message': 'Data Manager entry is missing tool_file attribute' } )
                continue
            else:
                bad_data_table = False
                for data_table_elem in data_manager_elem.findall( 'data_table' ):
                    data_table_name = data_table_elem.get( 'name', None )
                    if data_table_name is None:
                        log.error( 'Data Manager data_table entry is missing name attribute in "%s".' % ( data_manager_config_filename ) )
                        invalid_data_managers.append( { 'index': i,
                                                        'error_message': 'Data Manager entry is missing name attribute' } )
                        bad_data_table = True
                        break
                    else:
                        data_tables.append( data_table_name )
                if bad_data_table:
                    continue
            data_manager_metadata_tool_file = os.path.normpath( os.path.join( relative_data_manager_dir, tool_file ) )
            tool_metadata_tool_file = os.path.join( repo_files_directory, data_manager_metadata_tool_file )
            tool = tools.get( tool_metadata_tool_file, None )
            if tool is None:
                log.error( "Unable to determine tools metadata for '%s'." % ( data_manager_metadata_tool_file ) )
                invalid_data_managers.append( { 'index': i,
                                                'error_message': 'Unable to determine tools metadata' } )
                continue
            data_managers[ data_manager_id ] = { 'id': data_manager_id,
                                                 'name': data_manager_name,
                                                 'guid': guid,
                                                 'version': version,
                                                 'tool_config_file': data_manager_metadata_tool_file,
                                                 'data_tables': data_tables,
                                                 'tool_guid': tool[ 'guid' ] }
            log.debug( 'Loaded Data Manager tool_files: %s' % ( tool_file ) )
        return metadata_dict

    def generate_datatypes_metadata( self, tv, repository_files_dir, datatypes_config, metadata_dict ):
        """Update the received metadata_dict with information from the parsed datatypes_config."""
        tree, error_message = xml_util.parse_xml( datatypes_config )
        if tree is None:
            return metadata_dict
        root = tree.getroot()
        repository_datatype_code_files = []
        datatype_files = root.find( 'datatype_files' )
        if datatype_files is not None:
            for elem in datatype_files.findall( 'datatype_file' ):
                name = elem.get( 'name', None )
                repository_datatype_code_files.append( name )
            metadata_dict[ 'datatype_files' ] = repository_datatype_code_files
        datatypes = []
        registration = root.find( 'registration' )
        if registration is not None:
            for elem in registration.findall( 'datatype' ):
                converters = []
                display_app_containers = []
                datatypes_dict = {}
                # Handle defined datatype attributes.
                display_in_upload = elem.get( 'display_in_upload', None )
                if display_in_upload:
                    datatypes_dict[ 'display_in_upload' ] = display_in_upload
                dtype = elem.get( 'type', None )
                if dtype:
                    datatypes_dict[ 'dtype' ] = dtype
                extension = elem.get( 'extension', None )
                if extension:
                    datatypes_dict[ 'extension' ] = extension
                max_optional_metadata_filesize = elem.get( 'max_optional_metadata_filesize', None )
                if max_optional_metadata_filesize:
                    datatypes_dict[ 'max_optional_metadata_filesize' ] = max_optional_metadata_filesize
                mimetype = elem.get( 'mimetype', None )
                if mimetype:
                    datatypes_dict[ 'mimetype' ] = mimetype
                subclass = elem.get( 'subclass', None )
                if subclass:
                    datatypes_dict[ 'subclass' ] = subclass
                # Handle defined datatype converters and display applications.
                for sub_elem in elem:
                    if sub_elem.tag == 'converter':
                        # <converter file="bed_to_gff_converter.xml" target_datatype="gff"/>
                        tool_config = sub_elem.attrib[ 'file' ]
                        target_datatype = sub_elem.attrib[ 'target_datatype' ]
                        # Parse the tool_config to get the guid.
                        tool_config_path = hg_util.get_config_from_disk( tool_config, repository_files_dir )
                        full_path = os.path.abspath( tool_config_path )
                        tool, valid, error_message = \
                            tv.load_tool_from_config( self.app.security.encode_id( self.repository.id ), full_path )
                        if tool is None:
                            guid = None
                        else:
                            guid = suc.generate_tool_guid( self.repository_clone_url, tool )
                        converter_dict = dict( tool_config=tool_config,
                                               guid=guid,
                                               target_datatype=target_datatype )
                        converters.append( converter_dict )
                    elif sub_elem.tag == 'display':
                        # <display file="ucsc/bigwig.xml" />
                        # Should we store more than this?
                        display_file = sub_elem.attrib[ 'file' ]
                        display_app_dict = dict( display_file=display_file )
                        display_app_containers.append( display_app_dict )
                if converters:
                    datatypes_dict[ 'converters' ] = converters
                if display_app_containers:
                    datatypes_dict[ 'display_app_containers' ] = display_app_containers
                if datatypes_dict:
                    datatypes.append( datatypes_dict )
            if datatypes:
                metadata_dict[ 'datatypes' ] = datatypes
        return metadata_dict

    def generate_environment_dependency_metadata( self, elem, valid_tool_dependencies_dict ):
        """
        The value of env_var_name must match the value of the "set_environment" type
        in the tool config's <requirements> tag set, or the tool dependency will be
        considered an orphan.
        """
        # The value of the received elem looks something like this:
        # <set_environment version="1.0">
        #    <environment_variable name="JAVA_JAR_PATH" action="set_to">$INSTALL_DIR</environment_variable>
        # </set_environment>
        for env_elem in elem:
            # <environment_variable name="JAVA_JAR_PATH" action="set_to">$INSTALL_DIR</environment_variable>
            env_name = env_elem.get( 'name', None )
            if env_name:
                requirements_dict = dict( name=env_name, type='set_environment' )
                if 'set_environment' in valid_tool_dependencies_dict:
                    valid_tool_dependencies_dict[ 'set_environment' ].append( requirements_dict )
                else:
                    valid_tool_dependencies_dict[ 'set_environment' ] = [ requirements_dict ]
        return valid_tool_dependencies_dict

    def generate_guid_for_object( self, guid_type, obj_id, version ):
        tmp_url = common_util.remove_protocol_and_user_from_clone_url( self.repository_clone_url )
        return '%s/%s/%s/%s' % ( tmp_url, guid_type, obj_id, version )

    def generate_metadata_for_changeset_revision( self ):
        """
        Generate metadata for a repository using its files on disk.  To generate metadata
        for changeset revisions older than the repository tip, the repository will have been
        cloned to a temporary location and updated to a specified changeset revision to access
        that changeset revision's disk files, so the value of self.repository_files_dir will not
        always be self.repository.repo_path( self.app ) (it could be an absolute path to a temporary
        directory containing a clone).  If it is an absolute path, the value of self.relative_install_dir
        must contain repository.repo_path( self.app ).
    
        The value of self.persist will be True when the installed repository contains a valid
        tool_data_table_conf.xml.sample file, in which case the entries should ultimately be
        persisted to the file referred to by self.app.config.shed_tool_data_table_config.
        """
        tv = tool_validator.ToolValidator( self.app )
        if self.shed_config_dict is None:
            self.shed_config_dict = {}
        if self.updating_installed_repository:
            # Keep the original tool shed repository metadata if setting metadata on a repository
            # installed into a local Galaxy instance for which we have pulled updates.
            original_repository_metadata = self.repository.metadata
        else:
            original_repository_metadata = None
        readme_file_names = readme_util.get_readme_file_names( str( self.repository.name ) )
        if self.app.name == 'galaxy':
            # Shed related tool panel configs are only relevant to Galaxy.
            metadata_dict = { 'shed_config_filename' : self.shed_config_dict.get( 'config_filename' ) }
        else:
            metadata_dict = {}
        readme_files = []
        invalid_tool_configs = []
        tool_dependencies_config = None
        original_tool_data_path = self.app.config.tool_data_path
        original_tool_data_table_config_path = self.app.config.tool_data_table_config_path
        if self.resetting_all_metadata_on_repository:
            if not self.relative_install_dir:
                raise Exception( "The value of self.repository.repo_path must be set when resetting all metadata on a repository." )
            # Keep track of the location where the repository is temporarily cloned so that we can
            # strip the path when setting metadata.  The value of self.repository_files_dir is the
            # full path to the temporary directory to which self.repository was cloned.
            work_dir = self.repository_files_dir
            files_dir = self.repository_files_dir
            # Since we're working from a temporary directory, we can safely copy sample files included
            # in the repository to the repository root.
            self.app.config.tool_data_path = self.repository_files_dir
            self.app.config.tool_data_table_config_path = self.repository_files_dir
        else:
            # Use a temporary working directory to copy all sample files.
            work_dir = tempfile.mkdtemp( prefix="tmp-toolshed-gmfcr" )
            # All other files are on disk in the repository's repo_path, which is the value of
            # self.relative_install_dir.
            files_dir = self.relative_install_dir
            if self.shed_config_dict.get( 'tool_path' ):
                files_dir = os.path.join( self.shed_config_dict[ 'tool_path' ], files_dir )
            self.app.config.tool_data_path = work_dir #FIXME: Thread safe?
            self.app.config.tool_data_table_config_path = work_dir
        # Handle proprietary datatypes, if any.
        datatypes_config = hg_util.get_config_from_disk( suc.DATATYPES_CONFIG_FILENAME, files_dir )
        if datatypes_config:
            metadata_dict = self.generate_datatypes_metadata( tv,
                                                              files_dir,
                                                              datatypes_config,
                                                              metadata_dict )
        # Get the relative path to all sample files included in the repository for storage in
        # the repository's metadata.
        sample_file_metadata_paths, sample_file_copy_paths = \
            self.get_sample_files_from_disk( repository_files_dir=files_dir,
                                             tool_path=self.shed_config_dict.get( 'tool_path' ),
                                             relative_install_dir=self.relative_install_dir )
        if sample_file_metadata_paths:
            metadata_dict[ 'sample_files' ] = sample_file_metadata_paths
        # Copy all sample files included in the repository to a single directory location so we
        # can load tools that depend on them.
        for sample_file in sample_file_copy_paths:
            tool_util.copy_sample_file( self.app, sample_file, dest_path=work_dir )
            # If the list of sample files includes a tool_data_table_conf.xml.sample file, load
            # its table elements into memory.
            relative_path, filename = os.path.split( sample_file )
            if filename == 'tool_data_table_conf.xml.sample':
                new_table_elems, error_message = \
                    self.app.tool_data_tables.add_new_entries_from_config_file( config_filename=sample_file,
                                                                                tool_data_path=self.app.config.tool_data_path,
                                                                                shed_tool_data_table_config=self.app.config.shed_tool_data_table_config,
                                                                                persist=False )
                if error_message:
                    self.invalid_file_tups.append( ( filename, error_message ) )
        for root, dirs, files in os.walk( files_dir ):
            if root.find( '.hg' ) < 0 and root.find( 'hgrc' ) < 0:
                if '.hg' in dirs:
                    dirs.remove( '.hg' )
                for name in files:
                    # See if we have a repository dependencies defined.
                    if name == rt_util.REPOSITORY_DEPENDENCY_DEFINITION_FILENAME:
                        path_to_repository_dependencies_config = os.path.join( root, name )
                        metadata_dict, error_message = \
                            self.generate_repository_dependency_metadata( path_to_repository_dependencies_config,
                                                                          metadata_dict )
                        if error_message:
                            self.invalid_file_tups.append( ( name, error_message ) )
                    # See if we have one or more READ_ME files.
                    elif name.lower() in readme_file_names:
                        relative_path_to_readme = self.get_relative_path_to_repository_file( root,
                                                                                             name,
                                                                                             self.relative_install_dir,
                                                                                             work_dir,
                                                                                             self.shed_config_dict )
                        readme_files.append( relative_path_to_readme )
                    # See if we have a tool config.
                    elif name not in self.NOT_TOOL_CONFIGS and name.endswith( '.xml' ):
                        full_path = str( os.path.abspath( os.path.join( root, name ) ) )
                        if os.path.getsize( full_path ) > 0:
                            if not ( checkers.check_binary( full_path ) or
                                     checkers.check_image( full_path ) or
                                     checkers.check_gzip( full_path )[ 0 ] or
                                     checkers.check_bz2( full_path )[ 0 ] or
                                     checkers.check_zip( full_path ) ):
                                # Make sure we're looking at a tool config and not a display application
                                # config or something else.
                                element_tree, error_message = xml_util.parse_xml( full_path )
                                if element_tree is None:
                                    is_tool = False
                                else:
                                    element_tree_root = element_tree.getroot()
                                    is_tool = element_tree_root.tag == 'tool'
                                if is_tool:
                                    tool, valid, error_message = \
                                        tv.load_tool_from_config( self.app.security.encode_id( self.repository.id ),
                                                                  full_path )
                                    if tool is None:
                                        if not valid:
                                            invalid_tool_configs.append( name )
                                            self.invalid_file_tups.append( ( name, error_message ) )
                                    else:
                                        invalid_files_and_errors_tups = \
                                            tv.check_tool_input_params( files_dir,
                                                                        name,
                                                                        tool,
                                                                        sample_file_copy_paths )
                                        can_set_metadata = True
                                        for tup in invalid_files_and_errors_tups:
                                            if name in tup:
                                                can_set_metadata = False
                                                invalid_tool_configs.append( name )
                                                break
                                        if can_set_metadata:
                                            relative_path_to_tool_config = \
                                                self.get_relative_path_to_repository_file( root,
                                                                                           name,
                                                                                           self.relative_install_dir,
                                                                                           work_dir,
                                                                                           self.shed_config_dict )
                                            metadata_dict = self.generate_tool_metadata( relative_path_to_tool_config,
                                                                                         tool,
                                                                                         metadata_dict )
                                        else:
                                            for tup in invalid_files_and_errors_tups:
                                                self.invalid_file_tups.append( tup )
                    # Find all exported workflows.
                    elif name.endswith( '.ga' ):
                        relative_path = os.path.join( root, name )
                        if os.path.getsize( os.path.abspath( relative_path ) ) > 0:
                            fp = open( relative_path, 'rb' )
                            workflow_text = fp.read()
                            fp.close()
                            if workflow_text:
                                valid_exported_galaxy_workflow = True
                                try:
                                    exported_workflow_dict = json.loads( workflow_text )
                                except Exception, e:
                                    log.exception( "Skipping file %s since it does not seem to be a valid exported Galaxy workflow: %s" \
                                                   % str( relative_path ), str( e ) )
                                    valid_exported_galaxy_workflow = False
                            if valid_exported_galaxy_workflow and \
                                'a_galaxy_workflow' in exported_workflow_dict and \
                                    exported_workflow_dict[ 'a_galaxy_workflow' ] == 'true':
                                metadata_dict = self.generate_workflow_metadata( relative_path,
                                                                                 exported_workflow_dict,
                                                                                 metadata_dict )
        # Handle any data manager entries
        data_manager_config = hg_util.get_config_from_disk( suc.REPOSITORY_DATA_MANAGER_CONFIG_FILENAME, files_dir )
        metadata_dict = self.generate_data_manager_metadata( files_dir,
                                                             data_manager_config,
                                                             metadata_dict,
                                                             shed_config_dict=self.shed_config_dict )
    
        if readme_files:
            metadata_dict[ 'readme_files' ] = readme_files
        # This step must be done after metadata for tools has been defined.
        tool_dependencies_config = hg_util.get_config_from_disk( rt_util.TOOL_DEPENDENCY_DEFINITION_FILENAME, files_dir )
        if tool_dependencies_config:
            metadata_dict, error_message = \
                self.generate_tool_dependency_metadata( tool_dependencies_config,
                                                        metadata_dict,
                                                        original_repository_metadata=original_repository_metadata )
            if error_message:
                self.invalid_file_tups.append( ( rt_util.TOOL_DEPENDENCY_DEFINITION_FILENAME, error_message ) )
        if invalid_tool_configs:
            metadata_dict [ 'invalid_tools' ] = invalid_tool_configs
        self.metadata_dict = metadata_dict
        # Reset the value of the app's tool_data_path  and tool_data_table_config_path to their respective original values.
        self.app.config.tool_data_path = original_tool_data_path
        self.app.config.tool_data_table_config_path = original_tool_data_table_config_path
        basic_util.remove_dir( work_dir )

    def generate_package_dependency_metadata( self, elem, valid_tool_dependencies_dict, invalid_tool_dependencies_dict ):
        """
        Generate the metadata for a tool dependencies package defined for a repository.  The
        value of package_name must match the value of the "package" type in the tool config's
        <requirements> tag set.
        """
        # TODO: make this function a class.
        repository_dependency_is_valid = True
        repository_dependency_tup = []
        requirements_dict = {}
        error_message = ''
        package_name = elem.get( 'name', None )
        package_version = elem.get( 'version', None )
        if package_name and package_version:
            requirements_dict[ 'name' ] = package_name
            requirements_dict[ 'version' ] = package_version
            requirements_dict[ 'type' ] = 'package'
            for sub_elem in elem:
                if sub_elem.tag == 'readme':
                    requirements_dict[ 'readme' ] = sub_elem.text
                elif sub_elem.tag == 'repository':
                    # We have a complex repository dependency.  If the returned value of repository_dependency_is_valid
                    # is True, the tool dependency definition will be set as invalid.  This is currently the only case
                    # where a tool dependency definition is considered invalid.
                    repository_dependency_tup, repository_dependency_is_valid, error_message = \
                        self.handle_repository_elem( repository_elem=sub_elem,
                                                     only_if_compiling_contained_td=False )
                elif sub_elem.tag == 'install':
                    package_install_version = sub_elem.get( 'version', '1.0' )
                    if package_install_version == '1.0':
                        # Complex repository dependencies can be defined within the last <actions> tag set contained in an
                        # <actions_group> tag set.  Comments, <repository> tag sets and <readme> tag sets will be skipped
                        # in tool_dependency_util.parse_package_elem().
                        actions_elem_tuples = tool_dependency_util.parse_package_elem( sub_elem,
                                                                                       platform_info_dict=None,
                                                                                       include_after_install_actions=False )
                        if actions_elem_tuples:
                            # We now have a list of a single tuple that looks something like:
                            # [(True, <Element 'actions' at 0x104017850>)]
                            actions_elem_tuple = actions_elem_tuples[ 0 ]
                            in_actions_group, actions_elem = actions_elem_tuple
                            if in_actions_group:
                                # Since we're inside an <actions_group> tag set, inspect the actions_elem to see if a complex
                                # repository dependency is defined.  By definition, complex repository dependency definitions
                                # contained within the last <actions> tag set within an <actions_group> tag set will have the
                                # value of "only_if_compiling_contained_td" set to True in 
                                for action_elem in actions_elem:
                                    if action_elem.tag == 'package':
                                        # <package name="libgtextutils" version="0.6">
                                        #    <repository name="package_libgtextutils_0_6" owner="test" prior_installation_required="True" />
                                        # </package>
                                        ae_package_name = action_elem.get( 'name', None )
                                        ae_package_version = action_elem.get( 'version', None )
                                        if ae_package_name and ae_package_version:
                                            for sub_action_elem in action_elem:
                                                if sub_action_elem.tag == 'repository':
                                                    # We have a complex repository dependency.
                                                    repository_dependency_tup, repository_dependency_is_valid, error_message = \
                                                        self.handle_repository_elem( repository_elem=sub_action_elem,
                                                                                     only_if_compiling_contained_td=True )
                                    elif action_elem.tag == 'action':
                                        # <action type="set_environment_for_install">
                                        #    <repository changeset_revision="b107b91b3574" name="package_readline_6_2" owner="devteam" prior_installation_required="True" toolshed="http://localhost:9009">
                                        #        <package name="readline" version="6.2" />
                                        #    </repository>
                                        # </action>
                                        for sub_action_elem in action_elem:
                                            if sub_action_elem.tag == 'repository':
                                                # We have a complex repository dependency.
                                                repository_dependency_tup, repository_dependency_is_valid, error_message = \
                                                    self.handle_repository_elem( repository_elem=sub_action_elem,
                                                                                 only_if_compiling_contained_td=True )
        if requirements_dict:
            dependency_key = '%s/%s' % ( package_name, package_version )
            if repository_dependency_is_valid:
                valid_tool_dependencies_dict[ dependency_key ] = requirements_dict
            else:
                # Append the error message to the requirements_dict.
                requirements_dict[ 'error' ] = error_message
                invalid_tool_dependencies_dict[ dependency_key ] = requirements_dict
        return valid_tool_dependencies_dict, \
            invalid_tool_dependencies_dict, \
            repository_dependency_tup, \
            repository_dependency_is_valid, \
            error_message

    def generate_repository_dependency_metadata( self, repository_dependencies_config, metadata_dict ):
        """
        Generate a repository dependencies dictionary based on valid information defined in the received
        repository_dependencies_config.  This method is called from the tool shed as well as from Galaxy.
        """
        error_message = ''
        # Make sure we're looking at a valid repository_dependencies.xml file.
        tree, error_message = xml_util.parse_xml( repository_dependencies_config )
        if tree is None:
            xml_is_valid = False
        else:
            root = tree.getroot()
            xml_is_valid = root.tag == 'repositories'
        if xml_is_valid:
            invalid_repository_dependencies_dict = dict( description=root.get( 'description' ) )
            invalid_repository_dependency_tups = []
            valid_repository_dependencies_dict = dict( description=root.get( 'description' ) )
            valid_repository_dependency_tups = []
            for repository_elem in root.findall( 'repository' ):
                repository_dependency_tup, repository_dependency_is_valid, err_msg = \
                    self.handle_repository_elem( repository_elem,
                                                 only_if_compiling_contained_td=False )
                if repository_dependency_is_valid:
                    valid_repository_dependency_tups.append( repository_dependency_tup )
                else:
                    # Append the error_message to the repository dependencies tuple.
                    toolshed, name, owner, changeset_revision, prior_installation_required, only_if_compiling_contained_td = \
                        repository_dependency_tup
                    repository_dependency_tup = ( toolshed,
                                                  name,
                                                  owner,
                                                  changeset_revision,
                                                  prior_installation_required,
                                                  only_if_compiling_contained_td,
                                                  err_msg )
                    invalid_repository_dependency_tups.append( repository_dependency_tup )
                    error_message += err_msg
            if invalid_repository_dependency_tups:
                invalid_repository_dependencies_dict[ 'repository_dependencies' ] = invalid_repository_dependency_tups
                metadata_dict[ 'invalid_repository_dependencies' ] = invalid_repository_dependencies_dict
            if valid_repository_dependency_tups:
                valid_repository_dependencies_dict[ 'repository_dependencies' ] = valid_repository_dependency_tups
                metadata_dict[ 'repository_dependencies' ] = valid_repository_dependencies_dict
        return metadata_dict, error_message

    def generate_tool_metadata( self, tool_config, tool, metadata_dict ):
        """Update the received metadata_dict with changes that have been applied to the received tool."""
        # Generate the guid.
        guid = suc.generate_tool_guid( self.repository_clone_url, tool )
        # Handle tool.requirements.
        tool_requirements = []
        for tool_requirement in tool.requirements:
            name = str( tool_requirement.name )
            type = str( tool_requirement.type )
            version = str( tool_requirement.version ) if tool_requirement.version else None
            requirement_dict = dict( name=name,
                                     type=type,
                                     version=version )
            tool_requirements.append( requirement_dict )
        # Handle tool.tests.
        tool_tests = []
        if tool.tests:
            for ttb in tool.tests:
                required_files = []
                for required_file in ttb.required_files:
                    value, extra = required_file
                    required_files.append( ( value ) )
                inputs = []
                for param_name, values in ttb.inputs.iteritems():
                    # Handle improperly defined or strange test parameters and values.
                    if param_name is not None:
                        if values is None:
                            # An example is the 3rd test in http://testtoolshed.g2.bx.psu.edu/view/devteam/samtools_rmdup
                            # which is defined as:
                            # <test>
                            #    <param name="input1" value="1.bam" ftype="bam" />
                            #    <param name="bam_paired_end_type_selector" value="PE" />
                            #    <param name="force_se" />
                            #    <output name="output1" file="1.bam" ftype="bam" sort="True" />
                            # </test>
                            inputs.append( ( param_name, values ) )
                        else:
                            if isinstance( values, TestCollectionDef ):
                                # Nested required files are being populated correctly,
                                # not sure we need the value here to be anything else?
                                collection_type = values.collection_type
                                metadata_display_value = "%s collection" % collection_type
                                inputs.append( ( param_name, metadata_display_value ) )
                            elif len( values ) == 1:
                                inputs.append( ( param_name, values[ 0 ] ) )
                            else:
                                inputs.append( ( param_name, values ) )
                outputs = []
                for output in ttb.outputs:
                    name, file_name, extra = output
                    outputs.append( ( name, basic_util.strip_path( file_name ) if file_name else None ) )
                    if file_name not in required_files and file_name is not None:
                        required_files.append( file_name )
                test_dict = dict( name=str( ttb.name ),
                                  required_files=required_files,
                                  inputs=inputs,
                                  outputs=outputs )
                tool_tests.append( test_dict )
        # Determine if the tool should be loaded into the tool panel.  Examples of valid tools that
        # should not be displayed in the tool panel are datatypes converters and DataManager tools
        # (which are of type 'manage_data').
        datatypes = metadata_dict.get( 'datatypes', None )
        add_to_tool_panel_attribute = self.set_add_to_tool_panel_attribute_for_tool( tool=tool,
                                                                                     guid=guid,
                                                                                     datatypes=datatypes )
        tool_dict = dict( id=tool.id,
                          guid=guid,
                          name=tool.name,
                          version=tool.version,
                          description=tool.description,
                          version_string_cmd = tool.version_string_cmd,
                          tool_config=tool_config,
                          tool_type=tool.tool_type,
                          requirements=tool_requirements,
                          tests=tool_tests,
                          add_to_tool_panel=add_to_tool_panel_attribute )
        if 'tools' in metadata_dict:
            metadata_dict[ 'tools' ].append( tool_dict )
        else:
            metadata_dict[ 'tools' ] = [ tool_dict ]
        return metadata_dict

    def generate_tool_dependency_metadata( self, tool_dependencies_config, metadata_dict, original_repository_metadata=None ):
        """
        If the combination of name, version and type of each element is defined in the <requirement> tag for
        at least one tool in self.repository, then update the received metadata_dict with information from the
        parsed tool_dependencies_config.
        """
        error_message = ''
        if original_repository_metadata:
            # Keep a copy of the original tool dependencies dictionary and the list of tool
            # dictionaries in the metadata.
            original_valid_tool_dependencies_dict = original_repository_metadata.get( 'tool_dependencies', None )
            original_invalid_tool_dependencies_dict = original_repository_metadata.get( 'invalid_tool_dependencies', None )
        else:
            original_valid_tool_dependencies_dict = None
            original_invalid_tool_dependencies_dict = None
        tree, error_message = xml_util.parse_xml( tool_dependencies_config )
        if tree is None:
            return metadata_dict, error_message
        root = tree.getroot()
        tool_dependency_is_valid = True
        valid_tool_dependencies_dict = {}
        invalid_tool_dependencies_dict = {}
        valid_repository_dependency_tups = []
        invalid_repository_dependency_tups = []
        tools_metadata = metadata_dict.get( 'tools', None )
        description = root.get( 'description' )
        for elem in root:
            if elem.tag == 'package':
                valid_tool_dependencies_dict, \
                invalid_tool_dependencies_dict, \
                repository_dependency_tup, \
                repository_dependency_is_valid, \
                message = self.generate_package_dependency_metadata( elem,
                                                                     valid_tool_dependencies_dict,
                                                                     invalid_tool_dependencies_dict )
                if repository_dependency_is_valid:
                    if repository_dependency_tup and repository_dependency_tup not in valid_repository_dependency_tups:
                        # We have a valid complex repository dependency.
                        valid_repository_dependency_tups.append( repository_dependency_tup )
                else:
                    if repository_dependency_tup and repository_dependency_tup not in invalid_repository_dependency_tups:
                        # We have an invalid complex repository dependency, so mark the tool dependency as invalid.
                        tool_dependency_is_valid = False
                        # Append the error message to the invalid repository dependency tuple.
                        toolshed, \
                        name, \
                        owner, \
                        changeset_revision, \
                        prior_installation_required, \
                        only_if_compiling_contained_td \
                            = repository_dependency_tup
                        repository_dependency_tup = \
                            ( toolshed, \
                              name, \
                              owner, \
                              changeset_revision, \
                              prior_installation_required, \
                              only_if_compiling_contained_td, \
                              message )
                        invalid_repository_dependency_tups.append( repository_dependency_tup )
                        error_message = '%s  %s' % ( error_message, message )
            elif elem.tag == 'set_environment':
                valid_tool_dependencies_dict = \
                    self.generate_environment_dependency_metadata( elem, valid_tool_dependencies_dict )
        if valid_tool_dependencies_dict:
            if original_valid_tool_dependencies_dict:
                # We're generating metadata on an update pulled to a tool shed repository installed
                # into a Galaxy instance, so handle changes to tool dependencies appropriately.
                irm = self.app.installed_repository_manager
                updated_tool_dependency_names, deleted_tool_dependency_names = \
                    irm.handle_existing_tool_dependencies_that_changed_in_update( self.repository,
                                                                                  original_valid_tool_dependencies_dict,
                                                                                  valid_tool_dependencies_dict )
            metadata_dict[ 'tool_dependencies' ] = valid_tool_dependencies_dict
        if invalid_tool_dependencies_dict:
            metadata_dict[ 'invalid_tool_dependencies' ] = invalid_tool_dependencies_dict
        if valid_repository_dependency_tups:
            metadata_dict = \
                self.update_repository_dependencies_metadata( metadata=metadata_dict,
                                                              repository_dependency_tups=valid_repository_dependency_tups,
                                                              is_valid=True,
                                                              description=description )
        if invalid_repository_dependency_tups:
            metadata_dict = \
                self.update_repository_dependencies_metadata( metadata=metadata_dict,
                                                              repository_dependency_tups=invalid_repository_dependency_tups,
                                                              is_valid=False,
                                                              description=description )
        return metadata_dict, error_message

    def generate_workflow_metadata( self, relative_path, exported_workflow_dict, metadata_dict ):
        """
        Update the received metadata_dict with changes that have been applied to the
        received exported_workflow_dict.
        """
        if 'workflows' in metadata_dict:
            metadata_dict[ 'workflows' ].append( ( relative_path, exported_workflow_dict ) )
        else:
            metadata_dict[ 'workflows' ] = [ ( relative_path, exported_workflow_dict ) ]
        return metadata_dict

    def get_invalid_file_tups( self ):
        return self.invalid_file_tups

    def get_metadata_dict( self ):
        return self.metadata_dict

    def get_relative_path_to_repository_file( self, root, name, relative_install_dir, work_dir, shed_config_dict ):
        if self.resetting_all_metadata_on_repository:
            full_path_to_file = os.path.join( root, name )
            stripped_path_to_file = full_path_to_file.replace( work_dir, '' )
            if stripped_path_to_file.startswith( '/' ):
                stripped_path_to_file = stripped_path_to_file[ 1: ]
            relative_path_to_file = os.path.join( relative_install_dir, stripped_path_to_file )
        else:
            relative_path_to_file = os.path.join( root, name )
            if relative_install_dir and \
                shed_config_dict.get( 'tool_path' ) and \
                    relative_path_to_file.startswith( os.path.join( shed_config_dict.get( 'tool_path' ), relative_install_dir ) ):
                relative_path_to_file = relative_path_to_file[ len( shed_config_dict.get( 'tool_path' ) ) + 1: ]
        return relative_path_to_file

    def get_sample_files_from_disk( self, repository_files_dir, tool_path=None, relative_install_dir=None ):
        if self.resetting_all_metadata_on_repository:
            # Keep track of the location where the repository is temporarily cloned so that we can strip
            # it when setting metadata.
            work_dir = repository_files_dir
        sample_file_metadata_paths = []
        sample_file_copy_paths = []
        for root, dirs, files in os.walk( repository_files_dir ):
            if root.find( '.hg' ) < 0:
                for name in files:
                    if name.endswith( '.sample' ):
                        if self.resetting_all_metadata_on_repository:
                            full_path_to_sample_file = os.path.join( root, name )
                            stripped_path_to_sample_file = full_path_to_sample_file.replace( work_dir, '' )
                            if stripped_path_to_sample_file.startswith( '/' ):
                                stripped_path_to_sample_file = stripped_path_to_sample_file[ 1: ]
                            relative_path_to_sample_file = os.path.join( relative_install_dir, stripped_path_to_sample_file )
                            if os.path.exists( relative_path_to_sample_file ):
                                sample_file_copy_paths.append( relative_path_to_sample_file )
                            else:
                                sample_file_copy_paths.append( full_path_to_sample_file )
                        else:
                            relative_path_to_sample_file = os.path.join( root, name )
                            sample_file_copy_paths.append( relative_path_to_sample_file )
                            if tool_path and relative_install_dir:
                                if relative_path_to_sample_file.startswith( os.path.join( tool_path, relative_install_dir ) ):
                                    relative_path_to_sample_file = relative_path_to_sample_file[ len( tool_path ) + 1 :]
                            sample_file_metadata_paths.append( relative_path_to_sample_file )
        return sample_file_metadata_paths, sample_file_copy_paths

    def handle_repository_elem( self, repository_elem, only_if_compiling_contained_td=False ):
        """
        Process the received repository_elem which is a <repository> tag either from a
        repository_dependencies.xml file or a tool_dependencies.xml file.  If the former,
        we're generating repository dependencies metadata for a repository in the Tool Shed.
        If the latter, we're generating package dependency metadata within Galaxy or the
        Tool Shed.
        """
        is_valid = True
        error_message = ''
        toolshed = repository_elem.get( 'toolshed', None )
        name = repository_elem.get( 'name', None )
        owner = repository_elem.get( 'owner', None )
        changeset_revision = repository_elem.get( 'changeset_revision', None )
        prior_installation_required = str( repository_elem.get( 'prior_installation_required', False ) )
        if self.app.name == 'galaxy':
            if self.updating_installed_repository:
                pass
            else:
                # We're installing a repository into Galaxy, so make sure its contained repository
                # dependency definition is valid.
                if toolshed is None or name is None or owner is None or changeset_revision is None:
                    # Raise an exception here instead of returning an error_message to keep the
                    # installation from proceeding.  Reaching here implies a bug in the Tool Shed
                    # framework.
                    error_message = 'Installation halted because the following repository dependency definition is invalid:\n'
                    error_message += xml_util.xml_to_string( repository_elem, use_indent=True )
                    raise Exception( error_message )
        if not toolshed:
            # Default to the current tool shed.
            toolshed = str( url_for( '/', qualified=True ) ).rstrip( '/' )
        repository_dependency_tup = [ toolshed,
                                      name,
                                      owner,
                                      changeset_revision,
                                      prior_installation_required,
                                      str( only_if_compiling_contained_td ) ]
        user = None
        repository = None
        toolshed = common_util.remove_protocol_from_tool_shed_url( toolshed )
        if self.app.name == 'galaxy':
            # We're in Galaxy.  We reach here when we're generating the metadata for a tool
            # dependencies package defined for a repository or when we're generating metadata
            # for an installed repository.  See if we can locate the installed repository via
            # the changeset_revision defined in the repository_elem (it may be outdated).  If
            # we're successful in locating an installed repository with the attributes defined
            # in the repository_elem, we know it is valid.
            repository = suc.get_repository_for_dependency_relationship( self.app,
                                                                         toolshed,
                                                                         name,
                                                                         owner,
                                                                         changeset_revision )
            if repository:
                return repository_dependency_tup, is_valid, error_message
            else:
                # Send a request to the tool shed to retrieve appropriate additional changeset
                # revisions with which the repository
                # may have been installed.
                text = suc.get_updated_changeset_revisions_from_tool_shed( self.app,
                                                                           toolshed,
                                                                           name,
                                                                           owner,
                                                                           changeset_revision )
                if text:
                    updated_changeset_revisions = util.listify( text )
                    for updated_changeset_revision in updated_changeset_revisions:
                        repository = suc.get_repository_for_dependency_relationship( self.app,
                                                                                     toolshed,
                                                                                     name,
                                                                                     owner,
                                                                                     updated_changeset_revision )
                        if repository:
                            return repository_dependency_tup, is_valid, error_message
                        if self.updating_installed_repository:
                            # The repository dependency was included in an update to the installed
                            # repository, so it will not yet be installed.  Return the tuple for later
                            # installation.
                            return repository_dependency_tup, is_valid, error_message
                if self.updating_installed_repository:
                    # The repository dependency was included in an update to the installed repository,
                    # so it will not yet be installed.  Return the tuple for later installation.
                    return repository_dependency_tup, is_valid, error_message
                # Don't generate an error message for missing repository dependencies that are required
                # only if compiling the dependent repository's tool dependency.
                if not only_if_compiling_contained_td:
                    # We'll currently default to setting the repository dependency definition as invalid
                    # if an installed repository cannot be found.  This may not be ideal because the tool
                    # shed may have simply been inaccessible when metadata was being generated for the
                    # installed tool shed repository.
                    error_message = "Ignoring invalid repository dependency definition for tool shed %s, name %s, owner %s, " % \
                        ( toolshed, name, owner )
                    error_message += "changeset revision %s." % changeset_revision
                    log.debug( error_message )
                    is_valid = False
                    return repository_dependency_tup, is_valid, error_message
        else:
            # We're in the tool shed.
            if suc.tool_shed_is_this_tool_shed( toolshed ):
                try:
                    user = self.sa_session.query( self.app.model.User ) \
                                          .filter( self.app.model.User.table.c.username == owner ) \
                                          .one()
                except Exception, e:
                    error_message = "Ignoring repository dependency definition for tool shed %s, name %s, owner %s, " % \
                        ( toolshed, name, owner )
                    error_message += "changeset revision %s because the owner is invalid.  " % changeset_revision
                    log.debug( error_message )
                    is_valid = False
                    return repository_dependency_tup, is_valid, error_message
                try:
                    repository = self.sa_session.query( self.app.model.Repository ) \
                                                 .filter( and_( self.app.model.Repository.table.c.name == name,
                                                                self.app.model.Repository.table.c.user_id == user.id ) ) \
                                                 .one()
                except:
                    error_message = "Ignoring repository dependency definition for tool shed %s, name %s, owner %s, " % \
                        ( toolshed, name, owner )
                    error_message += "changeset revision %s because the name is invalid.  " % changeset_revision
                    log.debug( error_message )
                    is_valid = False
                    return repository_dependency_tup, is_valid, error_message
                repo = hg_util.get_repo_for_repository( self.app, repository=repository, repo_path=None, create=False )
                
                # The received changeset_revision may be None since defining it in the dependency definition is optional.
                # If this is the case, the default will be to set its value to the repository dependency tip revision.
                # This probably occurs only when handling circular dependency definitions.
                tip_ctx = repo.changectx( repo.changelog.tip() )
                # Make sure the repo.changlog includes at least 1 revision.
                if changeset_revision is None and tip_ctx.rev() >= 0:
                    changeset_revision = str( tip_ctx )
                    repository_dependency_tup = [ toolshed,
                                                 name,
                                                 owner,
                                                 changeset_revision,
                                                 prior_installation_required,
                                                 str( only_if_compiling_contained_td ) ]
                    return repository_dependency_tup, is_valid, error_message
                else:
                    # Find the specified changeset revision in the repository's changelog to see if it's valid.
                    found = False
                    for changeset in repo.changelog:
                        changeset_hash = str( repo.changectx( changeset ) )
                        if changeset_hash == changeset_revision:
                            found = True
                            break
                    if not found:
                        error_message = "Ignoring repository dependency definition for tool shed %s, name %s, owner %s, " % \
                            ( toolshed, name, owner )
                        error_message += "changeset revision %s because the changeset revision is invalid.  " % changeset_revision
                        log.debug( error_message )
                        is_valid = False
                        return repository_dependency_tup, is_valid, error_message
            else:
                # Repository dependencies are currently supported within a single tool shed.
                error_message = "Repository dependencies are currently supported only within the same tool shed.  Ignoring "
                error_message += "repository dependency definition  for tool shed %s, name %s, owner %s, changeset revision %s.  " % \
                    ( toolshed, name, owner, changeset_revision )
                log.debug( error_message )
                is_valid = False
                return repository_dependency_tup, is_valid, error_message
        return repository_dependency_tup, is_valid, error_message

    def set_add_to_tool_panel_attribute_for_tool( self, tool, guid, datatypes ):
        """
        Determine if a tool should be loaded into the Galaxy tool panel.  Examples of valid tools that
        should not be displayed in the tool panel are datatypes converters and DataManager tools.
        """
        if hasattr( tool, 'tool_type' ):
            if tool.tool_type in [ 'manage_data' ]:
                # We have a DataManager tool.
                return False
        if datatypes:
            for datatype_dict in datatypes:
                converters = datatype_dict.get( 'converters', None )
                # [{"converters":
                #    [{"target_datatype": "gff",
                #      "tool_config": "bed_to_gff_converter.xml",
                #      "guid": "localhost:9009/repos/test/bed_to_gff_converter/CONVERTER_bed_to_gff_0/2.0.0"}],
                #   "display_in_upload": "true",
                #   "dtype": "galaxy.datatypes.interval:Bed",
                #   "extension": "bed"}]
                if converters:
                    for converter_dict in converters:
                        converter_guid = converter_dict.get( 'guid', None )
                        if converter_guid:
                            if converter_guid == guid:
                                # We have a datatypes converter.
                                return False
        return True

    def set_changeset_revision( self, changeset_revision ):
        self.changeset_revision = changeset_revision

    def set_relative_install_dir( self, relative_install_dir ):
        self.relative_install_dir = relative_install_dir

    def set_repository( self, repository, relative_install_dir=None, changeset_revision=None ):
        self.repository = repository
        # Shed related tool panel configs are only relevant to Galaxy.
        if self.app.name == 'galaxy':
            if relative_install_dir is None and self.repository is not None:
                tool_path, relative_install_dir = self.repository.get_tool_relative_path( self.app )
            if changeset_revision is None and self.repository is not None:
                self.set_changeset_revision( self.repository.changeset_revision )
            else:
                self.set_changeset_revision( changeset_revision )
            self.shed_config_dict = repository.get_shed_config_dict( self.app )
            self.metadata_dict = { 'shed_config_filename' : self.shed_config_dict.get( 'config_filename', None ) }
        else:
            if relative_install_dir is None and self.repository is not None:
                relative_install_dir = repository.repo_path( self.app )
            if changeset_revision is None and self.repository is not None:
                self.set_changeset_revision( self.repository.tip( self.app ) )
            else:
                self.set_changeset_revision( changeset_revision )
            self.shed_config_dict = {}
            self.metadata_dict = {}
        self.set_relative_install_dir( relative_install_dir )
        self.set_repository_files_dir()
        self.resetting_all_metadata_on_repository = False
        self.updating_installed_repository = False
        self.persist = False
        self.invalid_file_tups = []

    def set_repository_clone_url( self, repository_clone_url ):
        self.repository_clone_url = repository_clone_url

    def set_repository_files_dir( self, repository_files_dir=None ):
        self.repository_files_dir = repository_files_dir

    def update_repository_dependencies_metadata( self, metadata, repository_dependency_tups, is_valid, description ):
        if is_valid:
            repository_dependencies_dict = metadata.get( 'repository_dependencies', None )
        else:
            repository_dependencies_dict = metadata.get( 'invalid_repository_dependencies', None )
        for repository_dependency_tup in repository_dependency_tups:
            if is_valid:
                tool_shed, \
                name, \
                owner, \
                changeset_revision, \
                prior_installation_required, \
                only_if_compiling_contained_td \
                    = repository_dependency_tup
            else:
                tool_shed, \
                name, \
                owner, \
                changeset_revision, \
                prior_installation_required, \
                only_if_compiling_contained_td, \
                error_message \
                    = repository_dependency_tup
            if repository_dependencies_dict:
                repository_dependencies = repository_dependencies_dict.get( 'repository_dependencies', [] )
                for repository_dependency_tup in repository_dependency_tups:
                    if repository_dependency_tup not in repository_dependencies:
                        repository_dependencies.append( repository_dependency_tup )
                repository_dependencies_dict[ 'repository_dependencies' ] = repository_dependencies
            else:
                repository_dependencies_dict = dict( description=description,
                                                     repository_dependencies=repository_dependency_tups )
        if repository_dependencies_dict:
            if is_valid:
                metadata[ 'repository_dependencies' ] = repository_dependencies_dict
            else:
                metadata[ 'invalid_repository_dependencies' ] = repository_dependencies_dict
        return metadata
