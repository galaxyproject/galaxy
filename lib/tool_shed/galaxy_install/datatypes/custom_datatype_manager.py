import logging
import os
import tempfile

from galaxy.util import asbool

from tool_shed.util import basic_util
from tool_shed.util import hg_util
from tool_shed.util import tool_util
from tool_shed.util import shed_util_common as suc
from tool_shed.util import xml_util

log = logging.getLogger( __name__ )


class CustomDatatypeLoader( object ):

    def __init__( self, app ):
        self.app = app

    def alter_config_and_load_prorietary_datatypes( self, datatypes_config, relative_install_dir,
                                                    deactivate=False, override=True ):
        """
        Parse a custom datatypes config (a datatypes_conf.xml file included in an installed
        tool shed repository) and add information to appropriate element attributes that will
        enable custom datatype class modules, datatypes converters and display applications
        to be discovered and properly imported by the datatypes registry.  The value of override
        will be False when a tool shed repository is being installed.  Since installation is
        occurring after the datatypes registry has been initialized, the registry's contents
        cannot be overridden by conflicting data types.
        """
        tree, error_message = xml_util.parse_xml( datatypes_config )
        if tree is None:
            return None, None
        datatypes_config_root = tree.getroot()
        registration = datatypes_config_root.find( 'registration' )
        if registration is None:
            # We have valid XML, but not a valid custom datatypes definition.
            return None, None
        sniffers = datatypes_config_root.find( 'sniffers' )
        converter_path, display_path = self.get_converter_and_display_paths( registration,
                                                                             relative_install_dir )
        if converter_path:
             # Path to datatype converters
            registration.attrib[ 'proprietary_converter_path' ] = converter_path
        if display_path:
            # Path to datatype display applications
            registration.attrib[ 'proprietary_display_path' ] = display_path
        relative_path_to_datatype_file_name = None
        datatype_files = datatypes_config_root.find( 'datatype_files' )
        datatype_class_modules = []
        if datatype_files is not None:
            # The <datatype_files> tag set contains any number of <datatype_file> tags.
            # <datatype_files>
            #    <datatype_file name="gmap.py"/>
            #    <datatype_file name="metagenomics.py"/>
            # </datatype_files>
            # We'll add attributes to the datatype tag sets so that the modules can be properly imported
            # by the datatypes registry.
            for elem in datatype_files.findall( 'datatype_file' ):
                datatype_file_name = elem.get( 'name', None )
                if datatype_file_name:
                    # Find the file in the installed repository.
                    for root, dirs, files in os.walk( relative_install_dir ):
                        if root.find( '.hg' ) < 0:
                            for name in files:
                                if name == datatype_file_name:
                                    datatype_class_modules.append( os.path.join( root, name ) )
                                    break
                    break
            if datatype_class_modules:
                for relative_path_to_datatype_file_name in datatype_class_modules:
                    datatype_file_name_path, datatype_file_name = os.path.split( relative_path_to_datatype_file_name )
                    for elem in registration.findall( 'datatype' ):
                        # Handle 'type' attribute which should be something like one of the following:
                        # type="gmap:GmapDB"
                        # type="galaxy.datatypes.gmap:GmapDB"
                        dtype = elem.get( 'type', None )
                        if dtype:
                            fields = dtype.split( ':' )
                            proprietary_datatype_module = fields[ 0 ]
                            if proprietary_datatype_module.find( '.' ) >= 0:
                                # Handle the case where datatype_module is "galaxy.datatypes.gmap".
                                proprietary_datatype_module = proprietary_datatype_module.split( '.' )[ -1 ]
                            # The value of proprietary_path must be an absolute path due to job_working_directory.
                            elem.attrib[ 'proprietary_path' ] = os.path.abspath( datatype_file_name_path )
                            elem.attrib[ 'proprietary_datatype_module' ] = proprietary_datatype_module
        # Temporarily persist the custom datatypes configuration file so it can be loaded into the
        # datatypes registry.
        fd, proprietary_datatypes_config = tempfile.mkstemp( prefix="tmp-toolshed-acalpd" )
        os.write( fd, '<?xml version="1.0"?>\n' )
        os.write( fd, '<datatypes>\n' )
        os.write( fd, '%s' % xml_util.xml_to_string( registration ) )
        if sniffers is not None:
            os.write( fd, '%s' % xml_util.xml_to_string( sniffers ) )
        os.write( fd, '</datatypes>\n' )
        os.close( fd )
        os.chmod( proprietary_datatypes_config, 0644 )
        # Load custom datatypes
        self.app.datatypes_registry.load_datatypes( root_dir=self.app.config.root,
                                                    config=proprietary_datatypes_config,
                                                    deactivate=deactivate,
                                                    override=override )
        if deactivate:
            # Reload the upload tool to eliminate deactivated datatype extensions from the file_type
            # select list.
            tool_util.reload_upload_tools( self.app )
        else:
            self.append_to_datatypes_registry_upload_file_formats( registration )
            tool_util.reload_upload_tools( self.app )
        if datatype_files is not None:
            try:
                os.unlink( proprietary_datatypes_config )
            except:
                pass
        return converter_path, display_path

    def append_to_datatypes_registry_upload_file_formats( self, elem ):
        # See if we have any datatypes that should be displayed in the upload tool's file_type select list.
        for datatype_elem in elem.findall( 'datatype' ):
            extension = datatype_elem.get( 'extension', None )
            display_in_upload = datatype_elem.get( 'display_in_upload', None )
            if extension is not None and display_in_upload is not None:
                display_in_upload = asbool( str( display_in_upload ) )
                if display_in_upload and extension not in self.app.datatypes_registry.upload_file_formats:
                    self.app.datatypes_registry.upload_file_formats.append( extension )

    def create_repository_dict_for_proprietary_datatypes( self, tool_shed, name, owner, installed_changeset_revision,
                                                          tool_dicts, converter_path=None, display_path=None ):
        return dict( tool_shed=tool_shed,
                     repository_name=name,
                     repository_owner=owner,
                     installed_changeset_revision=installed_changeset_revision,
                     tool_dicts=tool_dicts,
                     converter_path=converter_path,
                     display_path=display_path )

    def get_converter_and_display_paths( self, registration_elem, relative_install_dir ):
        """
        Find the relative path to data type converters and display applications included
        in installed tool shed repositories.
        """
        converter_path = None
        display_path = None
        for elem in registration_elem.findall( 'datatype' ):
            if not converter_path:
                # If any of the <datatype> tag sets contain <converter> tags, set the converter_path
                # if it is not already set.  This requires developers to place all converters in the
                # same subdirectory within the repository hierarchy.
                for converter in elem.findall( 'converter' ):
                    converter_config = converter.get( 'file', None )
                    if converter_config:
                        converter_config_file_name = basic_util.strip_path( converter_config )
                        for root, dirs, files in os.walk( relative_install_dir ):
                            if root.find( '.hg' ) < 0:
                                for name in files:
                                    if name == converter_config_file_name:
                                        # The value of converter_path must be absolute due to job_working_directory.
                                        converter_path = os.path.abspath( root )
                                        break
                    if converter_path:
                        break
            if not display_path:
                # If any of the <datatype> tag sets contain <display> tags, set the display_path
                # if it is not already set.  This requires developers to place all display acpplications
                # in the same subdirectory within the repository hierarchy.
                for display_app in elem.findall( 'display' ):
                    display_config = display_app.get( 'file', None )
                    if display_config:
                        display_config_file_name = basic_util.strip_path( display_config )
                        for root, dirs, files in os.walk( relative_install_dir ):
                            if root.find( '.hg' ) < 0:
                                for name in files:
                                    if name == display_config_file_name:
                                        # The value of display_path must be absolute due to job_working_directory.
                                        display_path = os.path.abspath( root )
                                        break
                    if display_path:
                        break
            if converter_path and display_path:
                break
        return converter_path, display_path

    def load_installed_datatype_converters( self, installed_repository_dict, deactivate=False ):
        """Load or deactivate proprietary datatype converters."""
        self.app.datatypes_registry.load_datatype_converters( self.app.toolbox,
                                                              installed_repository_dict=installed_repository_dict,
                                                              deactivate=deactivate )

    def load_installed_datatypes( self, repository, relative_install_dir, deactivate=False ):
        """
        Load proprietary datatypes and return information needed for loading custom
        datatypes converters and display applications later.
        """
        metadata = repository.metadata
        repository_dict = None
        datatypes_config = hg_util.get_config_from_disk( suc.DATATYPES_CONFIG_FILENAME, relative_install_dir )
        if datatypes_config:
            converter_path, display_path = \
                self.alter_config_and_load_prorietary_datatypes( datatypes_config,
                                                                 relative_install_dir,
                                                                 deactivate=deactivate )
            if converter_path or display_path:
                # Create a dictionary of tool shed repository related information.
                repository_dict = \
                    self.create_repository_dict_for_proprietary_datatypes( tool_shed=repository.tool_shed,
                                                                           name=repository.name,
                                                                           owner=repository.owner,
                                                                           installed_changeset_revision=repository.installed_changeset_revision,
                                                                           tool_dicts=metadata.get( 'tools', [] ),
                                                                           converter_path=converter_path,
                                                                           display_path=display_path )
        return repository_dict

    def load_installed_display_applications( self, installed_repository_dict, deactivate=False ):
        """Load or deactivate custom datatype display applications."""
        self.app.datatypes_registry.load_display_applications( installed_repository_dict=installed_repository_dict,
                                                               deactivate=deactivate )
