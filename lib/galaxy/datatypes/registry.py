"""
Provides mapping between extensions and datatypes, mime-types, etc.
"""
import os, sys, tempfile, threading, logging
import data, tabular, interval, images, sequence, qualityscore, genetics, xml, coverage, tracks, chrominfo, binary, assembly, ngsindex
import galaxy.util
from galaxy.util.odict import odict
from display_applications.application import DisplayApplication

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
    def load_datatypes( self, root_dir=None, config=None, deactivate=False, override=True ):
        """
        Parse a datatypes XML file located at root_dir/config.  If deactivate is True, an installed tool shed
        repository that includes proprietary datatypes is being deactivated, so appropriate loaded datatypes
        will be removed from the registry.  The value of override will be False when a tool shed repository is
        being installed.  Since installation is occurring after the datatypes registry has been initialized, its
        contents cannot be overridden by new introduced conflicting data types.
        """
        def __import_module( full_path, datatype_module ):
            sys.path.insert( 0, full_path )
            imported_module = __import__( datatype_module )
            sys.path.pop( 0 )
            return imported_module
        if root_dir and config:
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
            if proprietary_converter_path or proprietary_display_path and not handling_proprietary_datatypes:
                handling_proprietary_datatypes = True
            for elem in registration.findall( 'datatype' ):
                try:
                    extension = elem.get( 'extension', None )
                    dtype = elem.get( 'type', None )
                    type_extension = elem.get( 'type_extension', None )
                    mimetype = elem.get( 'mimetype', None )
                    display_in_upload = elem.get( 'display_in_upload', False )
                    make_subclass = galaxy.util.string_as_bool( elem.get( 'subclass', False ) )
                    # Proprietary datatypes included in installed tool shed repositories will include two special attributes
                    # (proprietary_path and proprietary_datatype_module) if they depend on proprietary datatypes classes.
                    proprietary_path = elem.get( 'proprietary_path', None )
                    proprietary_datatype_module = elem.get( 'proprietary_datatype_module', None )
                    if proprietary_path or proprietary_datatype_module and not handling_proprietary_datatypes:
                        handling_proprietary_datatypes = True
                    if deactivate:
                        # We are deactivating an installed tool shed repository, so eliminate the
                        # datatype elem from the in-memory list of datatype elems.
                        for in_memory_elem in self.datatype_elems:
                            in_memory_extension = in_memory_elem.get( 'extension', None )
                            if in_memory_extension == extension:
                                in_memory_dtype = elem.get( 'type', None )
                                in_memory_type_extension = elem.get( 'type_extension', None )
                                in_memory_mimetype = elem.get( 'mimetype', None )
                                in_memory_display_in_upload = elem.get( 'display_in_upload', False )
                                in_memory_make_subclass = galaxy.util.string_as_bool( elem.get( 'subclass', False ) )
                                if in_memory_dtype == dtype and in_memory_type_extension == type_extension and in_memory_mimetype == mimetype \
                                    and in_memory_display_in_upload == display_in_upload and in_memory_make_subclass == make_subclass:
                                    self.datatype_elems.remove( in_memory_elem )
                    else:
                        # Keep an in-memory list of datatype elems to enable persistence.
                        self.datatype_elems.append( elem )
                    if extension and extension in self.datatypes_by_extension and deactivate:
                        # We are deactivating an installed tool shed repository, so eliminate the datatype from the registry.
                        # TODO: Handle deactivating datatype converters, etc before removing from self.datatypes_by_extension.
                        self.log.debug( "Removing datatype with extension '%s' from the registry." % extension )
                        del self.datatypes_by_extension[ extension ]
                        can_process_datatype = False
                    else:
                        can_process_datatype = ( extension and ( dtype or type_extension ) ) and ( extension not in self.datatypes_by_extension or override )
                    if can_process_datatype:
                        if dtype:
                            fields = dtype.split( ':' )
                            datatype_module = fields[0]
                            datatype_class_name = fields[1]
                            datatype_class = None
                            if proprietary_path and proprietary_datatype_module:
                                # We need to change the value of sys.path, so do it in a way that is thread-safe.
                                lock = threading.Lock()
                                lock.acquire( True )
                                try:
                                    imported_module = __import_module( proprietary_path, proprietary_datatype_module )
                                    if imported_module not in self.imported_modules:
                                        self.imported_modules.append( imported_module )
                                    if hasattr( imported_module, datatype_class_name ):
                                        datatype_class = getattr( imported_module, datatype_class_name )
                                except Exception, e:
                                    full_path = os.path.join( proprietary_path, proprietary_datatype_module )
                                    self.log.debug( "Exception importing proprietary code file %s: %s" % ( str( full_path ), str( e ) ) )
                                finally:
                                    lock.release()
                            if datatype_class is None:
                                # The datatype class name must be contained in one of the datatype modules in the Galaxy distribution.
                                fields = datatype_module.split( '.' )
                                module = __import__( fields.pop(0) )
                                for mod in fields:
                                    module = getattr( module, mod )
                                datatype_class = getattr( module, datatype_class_name )
                        elif type_extension:
                            datatype_class = self.datatypes_by_extension[type_extension].__class__
                        if make_subclass:
                            datatype_class = type( datatype_class_name, (datatype_class,), {} )
                        if extension in self.datatypes_by_extension:
                            self.log.warning( "Overriding conflicting datatype with extension '%s', using datatype from %s." % ( extension, config ) )
                        self.datatypes_by_extension[ extension ] = datatype_class()
                        if mimetype is None:
                            # Use default mime type as per datatype spec
                            mimetype = self.datatypes_by_extension[ extension ].get_mime()
                        self.mimetypes_by_extension[ extension ] = mimetype
                        if hasattr( datatype_class, "get_track_type" ):
                            self.available_tracks.append( extension )
                        if display_in_upload:
                            self.upload_file_formats.append( extension )
                        # Max file size cut off for setting optional metadata
                        self.datatypes_by_extension[ extension ].max_optional_metadata_filesize = elem.get( 'max_optional_metadata_filesize', None )
                        for converter in elem.findall( 'converter' ):
                            # Build the list of datatype converters which will later be loaded into the calling app's toolbox.
                            converter_config = converter.get( 'file', None )
                            target_datatype = converter.get( 'target_datatype', None )
                            depends_on = converter.get( 'depends_on', None )
                            if depends_on and target_datatype:
                                if extension not in self.converter_deps:
                                    self.converter_deps[extension] = {}
                                self.converter_deps[extension][target_datatype] = depends_on.split(',')
                            if converter_config and target_datatype:
                                #if imported_modules:
                                if proprietary_converter_path:
                                    self.proprietary_converters.append( ( converter_config, extension, target_datatype ) )
                                else:
                                    self.converters.append( ( converter_config, extension, target_datatype ) )
                        for composite_file in elem.findall( 'composite_file' ):
                            # add composite files
                            name = composite_file.get( 'name', None )
                            if name is None:
                                self.log.warning( "You must provide a name for your composite_file (%s)." % composite_file )
                            optional = composite_file.get( 'optional', False )
                            mimetype = composite_file.get( 'mimetype', None )
                            self.datatypes_by_extension[extension].add_composite_file( name, optional=optional, mimetype=mimetype )
                        for display_app in elem.findall( 'display' ):
                            #if imported_modules:
                            if proprietary_display_path:
                                if elem not in self.proprietary_display_app_containers:
                                    self.proprietary_display_app_containers.append( elem )
                            else:
                                if elem not in self.display_app_containers:
                                    self.display_app_containers.append( elem )
                    elif not deactivate:
                        # A new tool shed repository that contains proprietary datatypes is being installed, and since installation
                        # is occurring after the datatypes registry has been initialized, its contents cannot be overridden by new
                        # introduced conflicting data types.
                        self.log.warning( "Ignoring conflicting datatype with extension '%s' from %s." % ( extension, config ) )
                except Exception, e:
                    if deactivate:
                        self.log.warning( "Error deactivating datatype with extension '%s': %s" % ( extension, str( e ) ) )
                    else:
                        self.log.warning( "Error loading datatype with extension '%s': %s" % ( extension, str( e ) ) )
            # Load datatype sniffers from the config
            sniffers = root.find( 'sniffers' )
            if sniffers:
                for elem in sniffers.findall( 'sniffer' ):
                    # Keep an in-memory list of sniffer elems to enable persistence.
                    self.sniffer_elems.append( elem )
                    dtype = elem.get( 'type', None )
                    if dtype:
                        try:
                            fields = dtype.split( ":" )
                            datatype_module = fields[0]
                            datatype_class_name = fields[1]
                            module = None
                            #if imported_modules:
                            if handling_proprietary_datatypes:
                                # See if one of the imported modules contains the datatype class name.
                                for imported_module in self.imported_modules:
                                    if hasattr( imported_module, datatype_class_name ):
                                        module = imported_module
                                        break
                            if module is None:
                                # The datatype class name must be contained in one of the datatype modules in the Galaxy distribution.
                                module = __import__( datatype_module )
                                for comp in datatype_module.split( '.' )[ 1: ]:
                                    module = getattr( module, comp )
                            aclass = getattr( module, datatype_class_name )()
                            if deactivate:
                                for sniffer_class in self.sniff_order:
                                    if sniffer_class.__class__ == aclass.__class__:
                                        self.sniff_order.remove( sniffer_class )
                                        break
                                self.log.debug( "Deactivated sniffer for datatype '%s'" % dtype )
                            else:
                                # See if we have a conflicting sniffer already loaded.
                                conflict = False
                                for conflict_loc, sniffer_class in enumerate( self.sniff_order ):
                                    if sniffer_class.__class__ == aclass.__class__:
                                        # We have a conflicting sniffer, so replace the one previously loaded.
                                        conflict = True
                                        if override:
                                            del self.sniff_order[ conflict_loc ]
                                            self.log.debug( "Replaced conflicting sniffer for datatype '%s'" % dtype )
                                        break
                                if conflict:
                                    if override:
                                        self.sniff_order.append( aclass )
                                        self.log.debug( "Loaded sniffer for datatype '%s'" % dtype )
                                else:
                                    self.sniff_order.append( aclass )
                                    self.log.debug( "Loaded sniffer for datatype '%s'" % dtype )
                        except Exception, exc:
                            if deactivate:
                                self.log.warning( "Error deactivating sniffer for datatype '%s': %s" % ( dtype, str( exc ) ) )
                            else:
                                self.log.warning( "Error appending sniffer for datatype '%s' to sniff_order: %s" % ( dtype, str( exc ) ) )
            self.upload_file_formats.sort()
            # Persist the xml form of the registry into a temporary file so that it
            # can be loaded from the command line by tools and set_metadata processing.
            self.to_xml_file()
        # Default values.
        if not self.datatypes_by_extension:
            self.datatypes_by_extension = { 
                'ab1'         : binary.Ab1(),
                'axt'         : sequence.Axt(),
                'bam'         : binary.Bam(),
                'bed'         : interval.Bed(), 
                'blastxml'    : xml.BlastXml(),
                'coverage'    : coverage.LastzCoverage(),
                'customtrack' : interval.CustomTrack(),
                'csfasta'     : sequence.csFasta(),
                'fasta'       : sequence.Fasta(),
                'eland'       : tabular.Eland(),
                'fastq'       : sequence.Fastq(),
                'fastqsanger' : sequence.FastqSanger(),
                'gtf'         : interval.Gtf(),
                'gff'         : interval.Gff(),
                'gff3'        : interval.Gff3(),
                'genetrack'   : tracks.GeneTrack(),
                'interval'    : interval.Interval(), 
                'laj'         : images.Laj(),
                'lav'         : sequence.Lav(),
                'maf'         : sequence.Maf(),
                'pileup'      : tabular.Pileup(),
                'qualsolid'   : qualityscore.QualityScoreSOLiD(),
                'qualsolexa'  : qualityscore.QualityScoreSolexa(),
                'qual454'     : qualityscore.QualityScore454(),
                'sam'         : tabular.Sam(), 
                'scf'         : binary.Scf(),
                'sff'         : binary.Sff(),
                'tabular'     : tabular.Tabular(),
                'taxonomy'    : tabular.Taxonomy(),
                'txt'         : data.Text(),
                'wig'         : interval.Wiggle(),
                'xml'         : xml.GenericXml(),
            }
            self.mimetypes_by_extension = { 
                'ab1'         : 'application/octet-stream',
                'axt'         : 'text/plain',
                'bam'         : 'application/octet-stream',
                'bed'         : 'text/plain', 
                'blastxml'    : 'application/xml', 
                'customtrack' : 'text/plain',
                'csfasta'     : 'text/plain',
                'eland'       : 'application/octet-stream',
                'fasta'       : 'text/plain',
                'fastq'       : 'text/plain',
                'fastqsanger' : 'text/plain',
                'gtf'         : 'text/plain',
                'gff'         : 'text/plain',
                'gff3'        : 'text/plain',
                'interval'    : 'text/plain', 
                'laj'         : 'text/plain',
                'lav'         : 'text/plain',
                'maf'         : 'text/plain',
                'memexml'     : 'application/xml',
                'pileup'      : 'text/plain',
                'qualsolid'   : 'text/plain',
                'qualsolexa'  : 'text/plain',
                'qual454'     : 'text/plain',
                'sam'         : 'text/plain',
                'scf'         : 'application/octet-stream',
                'sff'         : 'application/octet-stream',
                'tabular'     : 'text/plain',
                'taxonomy'    : 'text/plain',
                'txt'         : 'text/plain',
                'wig'         : 'text/plain',
                'xml'         : 'application/xml',
            }
        # super supertype fix for input steps in workflows.
        if 'data' not in self.datatypes_by_extension:
            self.datatypes_by_extension['data'] = data.Data()
            self.mimetypes_by_extension['data'] = 'application/octet-stream'
        # Default values - the order in which we attempt to determine data types is critical
        # because some formats are much more flexibly defined than others.
        if len(self.sniff_order) < 1:
            self.sniff_order = [
                binary.Bam(),
                binary.Sff(),
                xml.BlastXml(),
                xml.GenericXml(),
                sequence.Maf(),
                sequence.Lav(),
                sequence.csFasta(),
                qualityscore.QualityScoreSOLiD(),
                qualityscore.QualityScore454(),
                sequence.Fasta(),
                sequence.Fastq(),
                interval.Wiggle(),
                images.Html(),
                sequence.Axt(),
                interval.Bed(), 
                interval.CustomTrack(),
                interval.Gtf(),
                interval.Gff(),
                interval.Gff3(),
                tabular.Pileup(),
                interval.Interval(),
                tabular.Sam(),
                tabular.Eland()
            ]
        def append_to_sniff_order():
            # Just in case any supported data types are not included in the config's sniff_order section.
            for ext in self.datatypes_by_extension:
                datatype = self.datatypes_by_extension[ext]
                included = False
                for atype in self.sniff_order:
                    if isinstance(atype, datatype.__class__):
                        included = True
                        break
                if not included:
                    self.sniff_order.append(datatype)
        append_to_sniff_order()
    def get_available_tracks(self):
        return self.available_tracks
    def get_mimetype_by_extension(self, ext, default = 'application/octet-stream' ):
        """Returns a mimetype based on an extension"""
        try:
            mimetype = self.mimetypes_by_extension[ext]
        except KeyError:
            #datatype was never declared
            mimetype = default
            self.log.warning('unknown mimetype in data factory %s' % ext)
        return mimetype
    def get_datatype_by_extension(self, ext ):
        """Returns a datatype based on an extension"""
        try:
            builder = self.datatypes_by_extension[ext]
        except KeyError:
            builder = data.Text()
        return builder
    def change_datatype(self, data, ext, set_meta = True ):
        data.extension = ext
        # call init_meta and copy metadata from itself.  The datatype
        # being converted *to* will handle any metadata copying and
        # initialization.
        if data.has_data():
            data.set_size()
            data.init_meta( copy_from=data )
            if set_meta:
                #metadata is being set internally
                data.set_meta( overwrite = False )
                data.set_peek()
        return data
    def old_change_datatype(self, data, ext):
        """Creates and returns a new datatype based on an existing data and an extension"""
        newdata = factory(ext)(id=data.id)
        for key, value in data.__dict__.items():
            setattr(newdata, key, value)
        newdata.ext = ext
        return newdata
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
            tool_config = elem[0]
            source_datatype = elem[1]
            target_datatype = elem[2]
            if installed_repository_dict:
                converter_path = installed_repository_dict[ 'converter_path' ]
                config_path = os.path.join( converter_path, tool_config )
            else:
                config_path = os.path.join( self.converters_path, tool_config )
            try:
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
                    del toolbox.tools_by_id[ converter.id ]
                    if source_datatype in self.datatype_converters:
                        del self.datatype_converters[ source_datatype ][ target_datatype ]
                    self.log.debug( "Deactivated converter: %s", converter.id )
                else:
                    toolbox.tools_by_id[ converter.id ] = converter
                    if source_datatype not in self.datatype_converters:
                        self.datatype_converters[ source_datatype ] = odict()
                    self.datatype_converters[ source_datatype ][ target_datatype ] = converter
                    self.log.debug( "Loaded converter: %s", converter.id )
            except Exception, e:
                if deactivate:
                    self.log.exception( "Error deactivating converter (%s): %s" % ( config_path, str( e ) ) )
                else:
                    self.log.exception( "Error loading converter (%s): %s" % ( config_path, str( e ) ) )
    def load_display_applications( self, installed_repository_dict=None, deactivate=False ):
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
            extension = elem.get( 'extension', None )
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
                    display_app = DisplayApplication.from_file( config_path, self )
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
                            del self.display_applications[ display_app.id ]
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
                except Exception, e:
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
    def load_external_metadata_tool( self, toolbox ):
        """Adds a tool which is used to set external metadata"""
        # We need to be able to add a job to the queue to set metadata. The queue will currently only accept jobs with an associated
        # tool.  We'll create a special tool to be used for Auto-Detecting metadata; this is less than ideal, but effective
        # Properly building a tool without relying on parsing an XML file is near impossible...so we'll create a temporary file 
        tool_xml_text = """
            <tool id="__SET_METADATA__" name="Set External Metadata" version="1.0.1" tool_type="set_metadata">
              <type class="SetMetadataTool" module="galaxy.tools"/>
              <action module="galaxy.tools.actions.metadata" class="SetMetadataToolAction"/>
              <command>$__SET_EXTERNAL_METADATA_COMMAND_LINE__</command>
              <inputs>
                <param format="data" name="input1" type="data" label="File to set metadata on."/>
                <param name="__ORIGINAL_DATASET_STATE__" type="hidden" value=""/>
                <param name="__SET_EXTERNAL_METADATA_COMMAND_LINE__" type="hidden" value=""/>
              </inputs>
            </tool>
            """
        tmp_name = tempfile.NamedTemporaryFile()
        tmp_name.write( tool_xml_text )
        tmp_name.flush()
        set_meta_tool = toolbox.load_tool( tmp_name.name )
        toolbox.tools_by_id[ set_meta_tool.id ] = set_meta_tool
        self.set_external_metadata_tool = set_meta_tool
        self.log.debug( "Loaded external metadata tool: %s", self.set_external_metadata_tool.id )
    def get_converters_by_datatype(self, ext):
        """Returns available converters by source type"""
        converters = odict()
        source_datatype = type(self.get_datatype_by_extension(ext))
        for ext2, dict in self.datatype_converters.items():
            converter_datatype = type(self.get_datatype_by_extension(ext2))
            if issubclass(source_datatype, converter_datatype):
                converters.update(dict)
        #Ensure ext-level converters are present
        if ext in self.datatype_converters.keys():
            converters.update(self.datatype_converters[ext])
        return converters
    def get_converter_by_target_type(self, source_ext, target_ext):
        """Returns a converter based on source and target datatypes"""
        converters = self.get_converters_by_datatype(source_ext)
        if target_ext in converters.keys():
            return converters[target_ext]
        return None
    def find_conversion_destination_for_dataset_by_extensions( self, dataset, accepted_formats, converter_safe = True ):
        """Returns ( target_ext, existing converted dataset )"""
        for convert_ext in self.get_converters_by_datatype( dataset.ext ):
            if isinstance( self.get_datatype_by_extension( convert_ext ), accepted_formats ):
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
        if 'auto' not in rval and 'txt' in rval: #need to manually add 'auto' datatype
            rval[ 'auto' ] = rval[ 'txt' ]
        return rval
    @property
    def integrated_datatypes_configs( self ):
        if self.xml_filename and os.path.isfile( self.xml_filename ):
            return self.xml_filename
        self.to_xml_file()
        return self.xml_filename
    def to_xml_file( self ):
        if self.xml_filename is not None:
            # If persisted previously, attempt to remove
            # the temporary file in which we were written.
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
        os.chmod( self.xml_filename, 0644 )
