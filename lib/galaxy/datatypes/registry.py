"""
Provides mapping between extensions and datatypes, mime-types, etc.
"""
from __future__ import absolute_import

import os
import tempfile
import logging
import imp
from . import data
from . import tabular
from . import interval
from . import images
from . import sequence
from . import qualityscore
from . import xml
from . import coverage
from . import tracks
from . import binary
from . import text
import galaxy.util
from galaxy.util.odict import odict
from .display_applications.application import DisplayApplication


class ConfigurationError( Exception ):
    pass


class Registry( object ):

    def __init__( self ):
        self.log = logging.getLogger(__name__)
        self.log.addHandler( logging.NullHandler() )
        self.datatypes_by_extension = {}
        self.mimetypes_by_extension = {}
        self.datatype_converters = odict()
        # Converters defined in local datatypes_conf.xml
        self.converters = []
        # Converters defined in datatypes_conf.xml included in installed tool shed repositories.
        self.proprietary_converters = []
        self.converter_deps = {}
        self.available_tracks = []
        self.set_external_metadata_tool = None
        self.sniff_order = []
        self.upload_file_formats = []
        # Datatype elements defined in local datatypes_conf.xml that contain display applications.
        self.display_app_containers = []
        # Datatype elements in datatypes_conf.xml included in installed
        # tool shed repositories that contain display applications.
        self.proprietary_display_app_containers = []
        # Map a display application id to a display application
        self.display_applications = odict()
        # The following 2 attributes are used in the to_xml_file()
        # method to persist the current state into an xml file.
        self.display_path_attr = None
        self.converters_path_attr = None
        # The 'default' converters_path defined in local datatypes_conf.xml
        self.converters_path = None
        # The 'default' display_path defined in local datatypes_conf.xml
        self.display_applications_path = None
        self.inherit_display_application_by_class = []
        # Keep a list of imported proprietary datatype class modules.
        self.imported_modules = []
        self.datatype_elems = []
        self.sniffer_elems = []
        self.xml_filename = None
        # Build sites
        self.build_sites = {}
        self.display_sites = {}
        self.legacy_build_sites = {}

    def load_datatypes( self, root_dir=None, config=None, deactivate=False, override=True ):
        """
        Parse a datatypes XML file located at root_dir/config (if processing the Galaxy distributed config) or contained within
        an installed Tool Shed repository.  If deactivate is True, an installed Tool Shed repository that includes custom datatypes
        is being deactivated or uninstalled, so appropriate loaded datatypes will be removed from the registry.  The value of
        override will be False when a Tool Shed repository is being installed.  Since installation is occurring after the datatypes
        registry has been initialized at server startup, its contents cannot be overridden by newly introduced conflicting data types.
        """

        def __import_module( full_path, datatype_module, datatype_class_name ):
            open_file_obj, file_name, description = imp.find_module( datatype_module, [ full_path ] )
            imported_module = imp.load_module( datatype_class_name, open_file_obj, file_name, description )
            return imported_module

        if root_dir and config:
            # If handling_proprietary_datatypes is determined as True below, we'll have an elem that looks something like this:
            # <datatype display_in_upload="true"
            #           extension="blastxml"
            #           mimetype="application/xml"
            #           proprietary_datatype_module="blast"
            #           proprietary_path="[cloned repository path]"
            #           type="galaxy.datatypes.blast:BlastXml" />
            handling_proprietary_datatypes = False
            # Parse datatypes_conf.xml
            tree = galaxy.util.parse_xml( config )
            root = tree.getroot()
            # Load datatypes and converters from config
            if deactivate:
                self.log.debug( 'Deactivating datatypes from %s' % config )
            else:
                self.log.debug( 'Loading datatypes from %s' % config )
            registration = root.find( 'registration' )
            # Set default paths defined in local datatypes_conf.xml.
            if not self.converters_path:
                self.converters_path_attr = registration.get( 'converters_path', 'lib/galaxy/datatypes/converters' )
                self.converters_path = os.path.join( root_dir, self.converters_path_attr )
                if not os.path.isdir( self.converters_path ):
                    raise ConfigurationError( "Directory does not exist: %s" % self.converters_path )
            if not self.display_applications_path:
                self.display_path_attr = registration.get( 'display_path', 'display_applications' )
                self.display_applications_path = os.path.join( root_dir, self.display_path_attr )
            # Proprietary datatype's <registration> tag may have special attributes, proprietary_converter_path and proprietary_display_path.
            proprietary_converter_path = registration.get( 'proprietary_converter_path', None )
            proprietary_display_path = registration.get( 'proprietary_display_path', None )
            if proprietary_converter_path is not None or proprietary_display_path is not None and not handling_proprietary_datatypes:
                handling_proprietary_datatypes = True
            for elem in registration.findall( 'datatype' ):
                # Keep a status of the process steps to enable stopping the process of handling the datatype if necessary.
                ok = True
                extension = self.get_extension( elem )
                dtype = elem.get( 'type', None )
                type_extension = elem.get( 'type_extension', None )
                mimetype = elem.get( 'mimetype', None )
                display_in_upload = galaxy.util.string_as_bool( elem.get( 'display_in_upload', False ) )
                # If make_subclass is True, it does not necessarily imply that we are subclassing a datatype that is contained
                # in the distribution.
                make_subclass = galaxy.util.string_as_bool( elem.get( 'subclass', False ) )
                edam_format = elem.get( 'edam_format', None )
                if edam_format and not make_subclass:
                    self.log.warning("Cannot specify edam_format without setting subclass to True, skipping datatype.")
                    continue
                edam_data = elem.get( 'edam_data', None )
                if edam_data and not make_subclass:
                    self.log.warning("Cannot specify edam_data without setting subclass to True, skipping datatype.")
                    continue
                # Proprietary datatypes included in installed tool shed repositories will include two special attributes
                # (proprietary_path and proprietary_datatype_module) if they depend on proprietary datatypes classes.
                # The value of proprietary_path is the path to the cloned location of the tool shed repository's contained
                # datatypes_conf.xml file.
                proprietary_path = elem.get( 'proprietary_path', None )
                proprietary_datatype_module = elem.get( 'proprietary_datatype_module', None )
                if proprietary_path is not None or proprietary_datatype_module is not None and not handling_proprietary_datatypes:
                    handling_proprietary_datatypes = True
                if deactivate:
                    # We are deactivating or uninstalling an installed tool shed repository, so eliminate the datatype
                    # elem from the in-memory list of datatype elems.
                    for in_memory_elem in self.datatype_elems:
                        in_memory_extension = in_memory_elem.get( 'extension', None )
                        if in_memory_extension == extension:
                            in_memory_dtype = elem.get( 'type', None )
                            in_memory_type_extension = elem.get( 'type_extension', None )
                            in_memory_mimetype = elem.get( 'mimetype', None )
                            in_memory_display_in_upload = galaxy.util.string_as_bool( elem.get( 'display_in_upload', False ) )
                            in_memory_make_subclass = galaxy.util.string_as_bool( elem.get( 'subclass', False ) )
                            if in_memory_dtype == dtype and \
                                    in_memory_type_extension == type_extension and \
                                    in_memory_mimetype == mimetype and \
                                    in_memory_display_in_upload == display_in_upload and \
                                    in_memory_make_subclass == make_subclass:
                                self.datatype_elems.remove( in_memory_elem )
                    if extension is not None and extension in self.datatypes_by_extension:
                        # We are deactivating or uninstalling an installed tool shed repository, so eliminate the datatype
                        # from the registry.  TODO: Handle deactivating datatype converters, etc before removing from
                        # self.datatypes_by_extension.
                        del self.datatypes_by_extension[ extension ]
                        if extension in self.upload_file_formats:
                            self.upload_file_formats.remove( extension )
                        self.log.debug( "Removed datatype with extension '%s' from the registry." % extension )
                else:
                    # We are loading new datatype, so we'll make sure it is correctly defined before proceeding.
                    can_process_datatype = False
                    if extension is not None:
                        if dtype is not None or type_extension is not None:
                            if override or extension not in self.datatypes_by_extension:
                                can_process_datatype = True
                    if can_process_datatype:
                        if dtype is not None:
                            try:
                                fields = dtype.split( ':' )
                                datatype_module = fields[ 0 ]
                                datatype_class_name = fields[ 1 ]
                            except Exception as e:
                                self.log.exception( 'Error parsing datatype definition for dtype %s: %s' % ( str( dtype ), str( e ) ) )
                                ok = False
                            if ok:
                                datatype_class = None
                                if proprietary_path and proprietary_datatype_module and datatype_class_name:
                                    # TODO: previously comments suggested this needs to be locked because it modifys
                                    # the sys.path, probably true but the previous lock wasn't doing that.
                                    try:
                                        imported_module = __import_module( proprietary_path,
                                                                           proprietary_datatype_module,
                                                                           datatype_class_name )
                                        if imported_module not in self.imported_modules:
                                            self.imported_modules.append( imported_module )
                                        if hasattr( imported_module, datatype_class_name ):
                                            datatype_class = getattr( imported_module, datatype_class_name )
                                    except Exception as e:
                                        full_path = os.path.join( proprietary_path, proprietary_datatype_module )
                                        self.log.debug( "Exception importing proprietary code file %s: %s" % ( str( full_path ), str( e ) ) )
                                # Either the above exception was thrown because the proprietary_datatype_module is not derived from a class
                                # in the repository, or we are loading Galaxy's datatypes. In either case we'll look in the registry.
                                if datatype_class is None:
                                    try:
                                        # The datatype class name must be contained in one of the datatype modules in the Galaxy distribution.
                                        fields = datatype_module.split( '.' )[1:]
                                        module = __import__( datatype_module )
                                        for mod in fields:
                                            module = getattr( module, mod )
                                        datatype_class = getattr( module, datatype_class_name )
                                        self.log.debug( 'Retrieved datatype module %s:%s from the datatype registry.' % ( str( datatype_module ), datatype_class_name ) )
                                    except Exception as e:
                                        self.log.exception( 'Error importing datatype module %s: %s' % ( str( datatype_module ), str( e ) ) )
                                        ok = False
                        elif type_extension is not None:
                            try:
                                datatype_class = self.datatypes_by_extension[ type_extension ].__class__
                            except Exception as e:
                                self.log.exception( 'Error determining datatype_class for type_extension %s: %s' % ( str( type_extension ), str( e ) ) )
                                ok = False
                        if ok:
                            if not deactivate:
                                # A new tool shed repository that contains custom datatypes is being installed, and since installation is
                                # occurring after the datatypes registry has been initialized at server startup, its contents cannot be
                                # overridden by new introduced conflicting data types unless the value of override is True.
                                if extension in self.datatypes_by_extension:
                                    # Because of the way that the value of can_process_datatype was set above, we know that the value of
                                    # override is True.
                                    self.log.debug( "Overriding conflicting datatype with extension '%s', using datatype from %s." %
                                                    ( str( extension ), str( config ) ) )
                                if make_subclass:
                                    datatype_class = type( datatype_class_name, ( datatype_class, ), {} )
                                    if edam_format:
                                        datatype_class.edam_format = edam_format
                                    if edam_data:
                                        datatype_class.edam_data = edam_data
                                self.datatypes_by_extension[ extension ] = datatype_class()
                                if mimetype is None:
                                    # Use default mimetype per datatype specification.
                                    mimetype = self.datatypes_by_extension[ extension ].get_mime()
                                self.mimetypes_by_extension[ extension ] = mimetype
                                if datatype_class.track_type:
                                    self.available_tracks.append( extension )
                                if display_in_upload and extension not in self.upload_file_formats:
                                    self.upload_file_formats.append( extension )
                                # Max file size cut off for setting optional metadata.
                                self.datatypes_by_extension[ extension ].max_optional_metadata_filesize = elem.get( 'max_optional_metadata_filesize', None )
                                for converter in elem.findall( 'converter' ):
                                    # Build the list of datatype converters which will later be loaded into the calling app's toolbox.
                                    converter_config = converter.get( 'file', None )
                                    target_datatype = converter.get( 'target_datatype', None )
                                    depends_on = converter.get( 'depends_on', None )
                                    if depends_on is not None and target_datatype is not None:
                                        if extension not in self.converter_deps:
                                            self.converter_deps[ extension ] = {}
                                        self.converter_deps[ extension ][ target_datatype ] = depends_on.split( ',' )
                                    if converter_config and target_datatype:
                                        if proprietary_converter_path:
                                            self.proprietary_converters.append( ( converter_config, extension, target_datatype ) )
                                        else:
                                            self.converters.append( ( converter_config, extension, target_datatype ) )
                                # Add composite files.
                                for composite_file in elem.findall( 'composite_file' ):
                                    name = composite_file.get( 'name', None )
                                    if name is None:
                                        self.log.warning( "You must provide a name for your composite_file (%s)." % composite_file )
                                    optional = composite_file.get( 'optional', False )
                                    mimetype = composite_file.get( 'mimetype', None )
                                    self.datatypes_by_extension[ extension ].add_composite_file( name, optional=optional, mimetype=mimetype )
                                for display_app in elem.findall( 'display' ):
                                    if proprietary_display_path:
                                        if elem not in self.proprietary_display_app_containers:
                                            self.proprietary_display_app_containers.append( elem )
                                    else:
                                        if elem not in self.display_app_containers:
                                            self.display_app_containers.append( elem )
                                # Processing the new datatype elem is now complete, so make sure the element defining it is retained by appending
                                # the new datatype to the in-memory list of datatype elems to enable persistence.
                                self.datatype_elems.append( elem )
                    else:
                        if extension is not None:
                            if dtype is not None or type_extension is not None:
                                if extension in self.datatypes_by_extension:
                                    if not override:
                                        # Do not load the datatype since it conflicts with an existing datatype which we are not supposed
                                        # to override.
                                        self.log.debug( "Ignoring conflicting datatype with extension '%s' from %s." % ( extension, config ) )
            # Load datatype sniffers from the config - we'll do this even if one or more datatypes were not properly processed in the config
            # since sniffers are not tightly coupled with datatypes.
            self.load_datatype_sniffers( root,
                                         deactivate=deactivate,
                                         handling_proprietary_datatypes=handling_proprietary_datatypes,
                                         override=override )
            self.upload_file_formats.sort()
            # Load build sites
            self.load_build_sites( root )
            # Persist the xml form of the registry into a temporary file so that it can be loaded from the command line by tools and
            # set_metadata processing.
            self.to_xml_file()
        self.set_default_values()

        def append_to_sniff_order():
            # Just in case any supported data types are not included in the config's sniff_order section.
            for ext in self.datatypes_by_extension:
                datatype = self.datatypes_by_extension[ ext ]
                included = False
                for atype in self.sniff_order:
                    if isinstance( atype, datatype.__class__ ):
                        included = True
                        break
                if not included:
                    self.sniff_order.append( datatype )
        append_to_sniff_order()

    def load_build_sites( self, root ):
        if root.find( 'build_sites' ) is not None:
            for elem in root.find( 'build_sites' ).findall( 'site' ):
                if not (elem.get( 'type' ) and elem.get( 'file' )):
                    self.log.exception( "Site is missing required 'type' and 'file' attributes: %s" )
                else:
                    site_type = elem.get( 'type' )
                    file = elem.get( 'file' )
                    self.build_sites[site_type] = file
                    if site_type in ('ucsc', 'gbrowse'):
                        self.legacy_build_sites[site_type] = galaxy.util.read_build_sites( file )
                    if elem.get( 'display', None ):
                        display = elem.get( 'display' )
                        self.display_sites[site_type] = [ x.strip() for x in display.lower().split( ',' ) ]
                        self.log.debug( "Loaded build site '%s': %s with display sites: %s", site_type, file, display )
                    else:
                        self.log.debug( "Loaded build site '%s': %s", site_type, file )

    def get_legacy_sites_by_build( self, site_type, build ):
        sites = []
        for site in self.legacy_build_sites.get(site_type, []):
            if build in site['builds']:
                sites.append((site['name'], site['url']))
        return sites

    def get_display_sites( self, site_type ):
        return self.display_sites.get( site_type, [] )

    def load_datatype_sniffers( self, root, deactivate=False, handling_proprietary_datatypes=False, override=False ):
        """
        Process the sniffers element from a parsed a datatypes XML file located at root_dir/config (if processing the Galaxy
        distributed config) or contained within an installed Tool Shed repository.  If deactivate is True, an installed Tool
        Shed repository that includes custom sniffers is being deactivated or uninstalled, so appropriate loaded sniffers will
        be removed from the registry.  The value of override will be False when a Tool Shed repository is being installed.
        Since installation is occurring after the datatypes registry has been initialized at server startup, its contents
        cannot be overridden by newly introduced conflicting sniffers.
        """
        sniffer_elem_classes = [ e.attrib[ 'type' ] for e in self.sniffer_elems ]
        sniffers = root.find( 'sniffers' )
        if sniffers is not None:
            for elem in sniffers.findall( 'sniffer' ):
                # Keep a status of the process steps to enable stopping the process of handling the sniffer if necessary.
                ok = True
                dtype = elem.get( 'type', None )
                if dtype is not None:
                    try:
                        fields = dtype.split( ":" )
                        datatype_module = fields[ 0 ]
                        datatype_class_name = fields[ 1 ]
                        module = None
                    except Exception as e:
                        self.log.exception( 'Error determining datatype class or module for dtype %s: %s' % ( str( dtype ), str( e ) ) )
                        ok = False
                    if ok:
                        if handling_proprietary_datatypes:
                            # See if one of the imported modules contains the datatype class name.
                            for imported_module in self.imported_modules:
                                if hasattr( imported_module, datatype_class_name ):
                                    module = imported_module
                                    break
                        if module is None:
                            try:
                                # The datatype class name must be contained in one of the datatype modules in the Galaxy distribution.
                                module = __import__( datatype_module )
                                for comp in datatype_module.split( '.' )[ 1: ]:
                                    module = getattr( module, comp )
                            except Exception as e:
                                self.log.exception( "Error importing datatype class for '%s': %s" % ( str( dtype ), str( e ) ) )
                                ok = False
                        if ok:
                            try:
                                aclass = getattr( module, datatype_class_name )()
                            except Exception as e:
                                self.log.exception( 'Error calling method %s from class %s: %s', str( datatype_class_name ), str( module ), str( e ) )
                                ok = False
                            if ok:
                                if deactivate:
                                    # We are deactivating or uninstalling an installed Tool Shed repository, so eliminate the appropriate sniffers.
                                    sniffer_class = elem.get( 'type', None )
                                    if sniffer_class is not None:
                                        for index, s_e_c in enumerate( sniffer_elem_classes ):
                                            if sniffer_class == s_e_c:
                                                del self.sniffer_elems[ index ]
                                                sniffer_elem_classes = [ elem.attrib[ 'type' ] for elem in self.sniffer_elems ]
                                                self.log.debug( "Removed sniffer element for datatype '%s'" % str( dtype ) )
                                                break
                                        for sniffer_class in self.sniff_order:
                                            if sniffer_class.__class__ == aclass.__class__:
                                                self.sniff_order.remove( sniffer_class )
                                                self.log.debug( "Removed sniffer class for datatype '%s' from sniff order" % str( dtype ) )
                                                break
                                else:
                                    # We are loading new sniffer, so see if we have a conflicting sniffer already loaded.
                                    conflict = False
                                    for conflict_loc, sniffer_class in enumerate( self.sniff_order ):
                                        if sniffer_class.__class__ == aclass.__class__:
                                            # We have a conflicting sniffer, so replace the one previously loaded.
                                            conflict = True
                                            if override:
                                                del self.sniff_order[ conflict_loc ]
                                                self.log.debug( "Removed conflicting sniffer for datatype '%s'" % dtype )
                                            break
                                    if conflict:
                                        if override:
                                            self.sniff_order.append( aclass )
                                            self.log.debug( "Loaded sniffer for datatype '%s'" % dtype )
                                    else:
                                        self.sniff_order.append( aclass )
                                        self.log.debug( "Loaded sniffer for datatype '%s'" % dtype )
                                    # Processing the new sniffer elem is now complete, so make sure the element defining it is loaded if necessary.
                                    sniffer_class = elem.get( 'type', None )
                                    if sniffer_class is not None:
                                        if sniffer_class not in sniffer_elem_classes:
                                            self.sniffer_elems.append( elem )

    def get_datatype_class_by_name( self, name ):
        """
        Return the datatype class where the datatype's `type` attribute
        (as defined in the datatype_conf.xml file) contains `name`.
        """
        # TODO: obviously not ideal but some of these base classes that are useful for testing datatypes
        # aren't loaded into the datatypes registry, so we'd need to test for them here
        if name == 'images.Image':
            return images.Image

        # TODO: too inefficient - would be better to generate this once as a map and store in this object
        for ext, datatype_obj in self.datatypes_by_extension.items():
            datatype_obj_class = datatype_obj.__class__
            datatype_obj_class_str = str( datatype_obj_class )
            if name in datatype_obj_class_str:
                return datatype_obj_class
        return None

    def get_available_tracks( self ):
        return self.available_tracks

    def get_mimetype_by_extension( self, ext, default='application/octet-stream' ):
        """Returns a mimetype based on an extension"""
        try:
            mimetype = self.mimetypes_by_extension[ ext ]
        except KeyError:
            # datatype was never declared
            mimetype = default
            self.log.warning( 'unknown mimetype in data factory %s' % str( ext ) )
        return mimetype

    def get_datatype_by_extension( self, ext ):
        """Returns a datatype based on an extension"""
        try:
            builder = self.datatypes_by_extension[ ext ]
        except KeyError:
            builder = data.Text()
        return builder

    def change_datatype( self, data, ext ):
        data.extension = ext
        # call init_meta and copy metadata from itself.  The datatype
        # being converted *to* will handle any metadata copying and
        # initialization.
        if data.has_data():
            data.set_size()
            data.init_meta( copy_from=data )
        return data

    def load_datatype_converters( self, toolbox, installed_repository_dict=None, deactivate=False ):
        """
        If deactivate is False, add datatype converters from self.converters or self.proprietary_converters
        to the calling app's toolbox.  If deactivate is True, eliminates relevant converters from the calling
        app's toolbox.
        """
        if installed_repository_dict:
            # Load converters defined by datatypes_conf.xml included in installed tool shed repository.
            converters = self.proprietary_converters
        else:
            # Load converters defined by local datatypes_conf.xml.
            converters = self.converters
        for elem in converters:
            tool_config = elem[ 0 ]
            source_datatype = elem[ 1 ]
            target_datatype = elem[ 2 ]
            if installed_repository_dict:
                converter_path = installed_repository_dict[ 'converter_path' ]
            else:
                converter_path = self.converters_path
            try:
                config_path = os.path.join( converter_path, tool_config )
                converter = toolbox.load_tool( config_path )
                if installed_repository_dict:
                    # If the converter is included in an installed tool shed repository, set the tool
                    # shed related tool attributes.
                    converter.tool_shed = installed_repository_dict[ 'tool_shed' ]
                    converter.repository_name = installed_repository_dict[ 'repository_name' ]
                    converter.repository_owner = installed_repository_dict[ 'repository_owner' ]
                    converter.installed_changeset_revision = installed_repository_dict[ 'installed_changeset_revision' ]
                    converter.old_id = converter.id
                    # The converter should be included in the list of tools defined in tool_dicts.
                    tool_dicts = installed_repository_dict[ 'tool_dicts' ]
                    for tool_dict in tool_dicts:
                        if tool_dict[ 'id' ] == converter.id:
                            converter.guid = tool_dict[ 'guid' ]
                            converter.id = tool_dict[ 'guid' ]
                            break
                if deactivate:
                    toolbox.remove_tool_by_id( converter.id, remove_from_panel=False )
                    if source_datatype in self.datatype_converters:
                        if target_datatype in self.datatype_converters[ source_datatype ]:
                            del self.datatype_converters[ source_datatype ][ target_datatype ]
                    self.log.debug( "Deactivated converter: %s", converter.id )
                else:
                    toolbox.register_tool( converter )
                    if source_datatype not in self.datatype_converters:
                        self.datatype_converters[ source_datatype ] = odict()
                    self.datatype_converters[ source_datatype ][ target_datatype ] = converter
                    self.log.debug( "Loaded converter: %s", converter.id )
            except Exception as e:
                if deactivate:
                    self.log.exception( "Error deactivating converter from (%s): %s" % ( converter_path, str( e ) ) )
                else:
                    self.log.exception( "Error loading converter (%s): %s" % ( converter_path, str( e ) ) )

    def load_display_applications( self, app, installed_repository_dict=None, deactivate=False ):
        """
        If deactivate is False, add display applications from self.display_app_containers or
        self.proprietary_display_app_containers to appropriate datatypes.  If deactivate is
        True, eliminates relevant display applications from appropriate datatypes.
        """
        if installed_repository_dict:
            # Load display applications defined by datatypes_conf.xml included in installed tool shed repository.
            datatype_elems = self.proprietary_display_app_containers
        else:
            # Load display applications defined by local datatypes_conf.xml.
            datatype_elems = self.display_app_containers
        for elem in datatype_elems:
            extension = self.get_extension( elem )
            for display_app in elem.findall( 'display' ):
                display_file = display_app.get( 'file', None )
                if installed_repository_dict:
                    display_path = installed_repository_dict[ 'display_path' ]
                    display_file_head, display_file_tail = os.path.split( display_file )
                    config_path = os.path.join( display_path, display_file_tail )
                else:
                    config_path = os.path.join( self.display_applications_path, display_file )
                try:
                    inherit = galaxy.util.string_as_bool( display_app.get( 'inherit', 'False' ) )
                    display_app = DisplayApplication.from_file( config_path, app )
                    if display_app:
                        if display_app.id in self.display_applications:
                            if deactivate:
                                del self.display_applications[ display_app.id ]
                            else:
                                # If we already loaded this display application, we'll use the first one loaded.
                                display_app = self.display_applications[ display_app.id ]
                        elif installed_repository_dict:
                            # If the display application is included in an installed tool shed repository,
                            # set the tool shed related tool attributes.
                            display_app.tool_shed = installed_repository_dict[ 'tool_shed' ]
                            display_app.repository_name = installed_repository_dict[ 'repository_name' ]
                            display_app.repository_owner = installed_repository_dict[ 'repository_owner' ]
                            display_app.installed_changeset_revision = installed_repository_dict[ 'installed_changeset_revision' ]
                            display_app.old_id = display_app.id
                            # The display application should be included in the list of tools defined in tool_dicts.
                            tool_dicts = installed_repository_dict[ 'tool_dicts' ]
                            for tool_dict in tool_dicts:
                                if tool_dict[ 'id' ] == display_app.id:
                                    display_app.guid = tool_dict[ 'guid' ]
                                    display_app.id = tool_dict[ 'guid' ]
                                    break
                        if deactivate:
                            if display_app.id in self.display_applications:
                                del self.display_applications[ display_app.id ]
                            if extension in self.datatypes_by_extension:
                                if display_app.id in self.datatypes_by_extension[ extension ].display_applications:
                                    del self.datatypes_by_extension[ extension ].display_applications[ display_app.id ]
                            if inherit and ( self.datatypes_by_extension[ extension ], display_app ) in self.inherit_display_application_by_class:
                                self.inherit_display_application_by_class.remove( ( self.datatypes_by_extension[ extension ], display_app ) )
                            self.log.debug( "Deactivated display application '%s' for datatype '%s'." % ( display_app.id, extension ) )
                        else:
                            self.display_applications[ display_app.id ] = display_app
                            self.datatypes_by_extension[ extension ].add_display_application( display_app )
                            if inherit and ( self.datatypes_by_extension[ extension ], display_app ) not in self.inherit_display_application_by_class:
                                self.inherit_display_application_by_class.append( ( self.datatypes_by_extension[ extension ], display_app ) )
                            self.log.debug( "Loaded display application '%s' for datatype '%s', inherit=%s." % ( display_app.id, extension, inherit ) )
                except Exception as e:
                    if deactivate:
                        self.log.exception( "Error deactivating display application (%s): %s" % ( config_path, str( e ) ) )
                    else:
                        self.log.exception( "Error loading display application (%s): %s" % ( config_path, str( e ) ) )
        # Handle display_application subclass inheritance.
        for extension, d_type1 in self.datatypes_by_extension.iteritems():
            for d_type2, display_app in self.inherit_display_application_by_class:
                current_app = d_type1.get_display_application( display_app.id, None )
                if current_app is None and isinstance( d_type1, type( d_type2 ) ):
                    self.log.debug( "Adding inherited display application '%s' to datatype '%s'" % ( display_app.id, extension ) )
                    d_type1.add_display_application( display_app )

    def reload_display_applications( self, display_application_ids=None ):
        """
        Reloads display applications: by id, or all if no ids provided
        Returns tuple( [reloaded_ids], [failed_ids] )
        """
        if not display_application_ids:
            display_application_ids = self.display_applications.keys()
        elif not isinstance( display_application_ids, list ):
            display_application_ids = [ display_application_ids ]
        reloaded = []
        failed = []
        for display_application_id in display_application_ids:
            try:
                self.display_applications[ display_application_id ].reload()
                reloaded.append( display_application_id )
            except Exception as e:
                self.log.debug( 'Requested to reload display application "%s", but failed: %s.', display_application_id, e  )
                failed.append( display_application_id )
        return ( reloaded, failed )

    def load_external_metadata_tool( self, toolbox ):
        """Adds a tool which is used to set external metadata"""
        # We need to be able to add a job to the queue to set metadata. The queue will currently only accept jobs with an associated
        # tool.  We'll load a special tool to be used for Auto-Detecting metadata; this is less than ideal, but effective
        # Properly building a tool without relying on parsing an XML file is near difficult...so we bundle with Galaxy.
        set_meta_tool = toolbox.load_hidden_lib_tool( "galaxy/datatypes/set_metadata_tool.xml" )
        self.set_external_metadata_tool = set_meta_tool
        self.log.debug( "Loaded external metadata tool: %s", self.set_external_metadata_tool.id )

    def set_default_values( self ):
        # Default values.
        if not self.datatypes_by_extension:
            self.datatypes_by_extension = {
                'ab1'           : binary.Ab1(),
                'axt'           : sequence.Axt(),
                'bam'           : binary.Bam(),
                'bed'           : interval.Bed(),
                'coverage'      : coverage.LastzCoverage(),
                'customtrack'   : interval.CustomTrack(),
                'csfasta'       : sequence.csFasta(),
                'db3'           : binary.SQlite(),
                'fasta'         : sequence.Fasta(),
                'eland'         : tabular.Eland(),
                'fastq'         : sequence.Fastq(),
                'fastqsanger'   : sequence.FastqSanger(),
                'gemini.sqlite' : binary.GeminiSQLite(),
                'gtf'           : interval.Gtf(),
                'gff'           : interval.Gff(),
                'gff3'          : interval.Gff3(),
                'genetrack'     : tracks.GeneTrack(),
                'h5'            : binary.H5(),
                'idpdb'         : binary.IdpDB(),
                'interval'      : interval.Interval(),
                'laj'           : images.Laj(),
                'lav'           : sequence.Lav(),
                'maf'           : sequence.Maf(),
                'mz.sqlite'     : binary.MzSQlite(),
                'pileup'        : tabular.Pileup(),
                'qualsolid'     : qualityscore.QualityScoreSOLiD(),
                'qualsolexa'    : qualityscore.QualityScoreSolexa(),
                'qual454'       : qualityscore.QualityScore454(),
                'sam'           : tabular.Sam(),
                'scf'           : binary.Scf(),
                'sff'           : binary.Sff(),
                'tabular'       : tabular.Tabular(),
                'csv'           : tabular.CSV(),
                'taxonomy'      : tabular.Taxonomy(),
                'txt'           : data.Text(),
                'wig'           : interval.Wiggle(),
                'xml'           : xml.GenericXml(),
            }
            self.mimetypes_by_extension = {
                'ab1'           : 'application/octet-stream',
                'axt'           : 'text/plain',
                'bam'           : 'application/octet-stream',
                'bed'           : 'text/plain',
                'customtrack'   : 'text/plain',
                'csfasta'       : 'text/plain',
                'db3'           : 'application/octet-stream',
                'eland'         : 'application/octet-stream',
                'fasta'         : 'text/plain',
                'fastq'         : 'text/plain',
                'fastqsanger'   : 'text/plain',
                'gemini.sqlite' : 'application/octet-stream',
                'gtf'           : 'text/plain',
                'gff'           : 'text/plain',
                'gff3'          : 'text/plain',
                'h5'            : 'application/octet-stream',
                'idpdb'         : 'application/octet-stream',
                'interval'      : 'text/plain',
                'laj'           : 'text/plain',
                'lav'           : 'text/plain',
                'maf'           : 'text/plain',
                'memexml'       : 'application/xml',
                'mz.sqlite'     : 'application/octet-stream',
                'pileup'        : 'text/plain',
                'qualsolid'     : 'text/plain',
                'qualsolexa'    : 'text/plain',
                'qual454'       : 'text/plain',
                'sam'           : 'text/plain',
                'scf'           : 'application/octet-stream',
                'sff'           : 'application/octet-stream',
                'tabular'       : 'text/plain',
                'csv'           : 'text/plain',
                'taxonomy'      : 'text/plain',
                'txt'           : 'text/plain',
                'wig'           : 'text/plain',
                'xml'           : 'application/xml',
            }
        # super supertype fix for input steps in workflows.
        if 'data' not in self.datatypes_by_extension:
            self.datatypes_by_extension[ 'data' ] = data.Data()
            self.mimetypes_by_extension[ 'data' ] = 'application/octet-stream'
        # Default values - the order in which we attempt to determine data types is critical
        # because some formats are much more flexibly defined than others.
        if len( self.sniff_order ) < 1:
            self.sniff_order = [
                binary.Bam(),
                binary.Sff(),
                binary.H5(),
                binary.GeminiSQLite(),
                binary.MzSQlite(),
                binary.IdpDB(),
                binary.SQlite(),
                xml.GenericXml(),
                sequence.Maf(),
                sequence.Lav(),
                sequence.csFasta(),
                qualityscore.QualityScoreSOLiD(),
                qualityscore.QualityScore454(),
                sequence.Fasta(),
                sequence.Fastq(),
                interval.Wiggle(),
                text.Html(),
                sequence.Axt(),
                interval.Bed(),
                interval.CustomTrack(),
                interval.Gtf(),
                interval.Gff(),
                interval.Gff3(),
                tabular.Pileup(),
                interval.Interval(),
                tabular.Sam(),
                tabular.Eland(),
                tabular.CSV()
            ]

    def get_converters_by_datatype( self, ext ):
        """Returns available converters by source type"""
        converters = odict()
        source_datatype = type( self.get_datatype_by_extension( ext ) )
        for ext2, dict in self.datatype_converters.items():
            converter_datatype = type( self.get_datatype_by_extension( ext2 ) )
            if issubclass( source_datatype, converter_datatype ):
                converters.update( dict )
        # Ensure ext-level converters are present
        if ext in self.datatype_converters.keys():
            converters.update( self.datatype_converters[ ext ] )
        return converters

    def get_converter_by_target_type( self, source_ext, target_ext ):
        """Returns a converter based on source and target datatypes"""
        converters = self.get_converters_by_datatype( source_ext )
        if target_ext in converters.keys():
            return converters[ target_ext ]
        return None

    def find_conversion_destination_for_dataset_by_extensions( self, dataset, accepted_formats, converter_safe=True ):
        """Returns ( target_ext, existing converted dataset )"""
        for convert_ext in self.get_converters_by_datatype( dataset.ext ):
            if self.get_datatype_by_extension( convert_ext ).matches_any( accepted_formats ):
                converted_dataset = dataset.get_converted_files_by_type( convert_ext )
                if converted_dataset:
                    ret_data = converted_dataset
                elif not converter_safe:
                    continue
                else:
                    ret_data = None
                return ( convert_ext, ret_data )
        return ( None, None )

    def get_composite_extensions( self ):
        return [ ext for ( ext, d_type ) in self.datatypes_by_extension.iteritems() if d_type.composite_type is not None ]

    def get_upload_metadata_params( self, context, group, tool ):
        """Returns dict of case value:inputs for metadata conditional for upload tool"""
        rval = {}
        for ext, d_type in self.datatypes_by_extension.iteritems():
            inputs = []
            for meta_name, meta_spec in d_type.metadata_spec.iteritems():
                if meta_spec.set_in_upload:
                    help_txt = meta_spec.desc
                    if not help_txt or help_txt == meta_name:
                        help_txt = ""
                    inputs.append( '<param type="text" name="%s" label="Set metadata value for &quot;%s&quot;" value="%s" help="%s"/>' % ( meta_name, meta_name, meta_spec.default, help_txt ) )
            rval[ ext ] = "\n".join( inputs )
        if 'auto' not in rval and 'txt' in rval:  # need to manually add 'auto' datatype
            rval[ 'auto' ] = rval[ 'txt' ]
        return rval

    @property
    def edam_formats( self ):
        """
        """
        mapping = dict((k, v.edam_format) for k, v in self.datatypes_by_extension.items())
        return mapping

    @property
    def edam_data( self ):
        """
        """
        mapping = dict((k, v.edam_data) for k, v in self.datatypes_by_extension.items())
        return mapping

    @property
    def integrated_datatypes_configs( self ):
        if self.xml_filename and os.path.isfile( self.xml_filename ):
            return self.xml_filename
        self.to_xml_file()
        return self.xml_filename

    def to_xml_file( self ):
        if self.xml_filename is not None:
            # If persisted previously, attempt to remove the temporary file in which we were written.
            try:
                os.unlink( self.xml_filename )
            except:
                pass
            self.xml_filename = None
        fd, filename = tempfile.mkstemp()
        self.xml_filename = os.path.abspath( filename )
        if self.converters_path_attr:
            converters_path_str = ' converters_path="%s"' % self.converters_path_attr
        else:
            converters_path_str = ''
        if self.display_path_attr:
            display_path_str = ' display_path="%s"' % self.display_path_attr
        else:
            display_path_str = ''
        os.write( fd, '<?xml version="1.0"?>\n' )
        os.write( fd, '<datatypes>\n' )
        os.write( fd, '<registration%s%s>\n' % ( converters_path_str, display_path_str ) )
        for elem in self.datatype_elems:
            os.write( fd, '%s' % galaxy.util.xml_to_string( elem ) )
        os.write( fd, '</registration>\n' )
        os.write( fd, '<sniffers>\n' )
        for elem in self.sniffer_elems:
            os.write( fd, '%s' % galaxy.util.xml_to_string( elem ) )
        os.write( fd, '</sniffers>\n' )
        os.write( fd, '</datatypes>\n' )
        os.close( fd )
        os.chmod( self.xml_filename, 0o644 )

    def get_extension( self, elem ):
        """
        Function which returns the extension lowercased
        :param elem:
        :return extension:
        """
        extension = elem.get('extension', None)
        # If extension is not None and is uppercase or mixed case, we need to lowercase it
        if extension is not None and not extension.islower():
            self.log.debug( "%s is not lower case, that could cause troubles in the future. \
            Please change it to lower case" % extension )
            extension = extension.lower()
        return extension
