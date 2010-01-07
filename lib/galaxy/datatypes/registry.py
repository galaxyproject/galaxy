"""
Provides mapping between extensions and datatypes, mime-types, etc.
"""
import os, tempfile
import logging
import data, tabular, interval, images, sequence, qualityscore, genetics, xml, coverage, tracks, chrominfo, binary
import galaxy.util
from galaxy.util.odict import odict

class ConfigurationError( Exception ):
    pass

class Registry( object ):
    def __init__( self, root_dir=None, config=None ):
        self.log = logging.getLogger(__name__)
        self.datatypes_by_extension = {}
        self.mimetypes_by_extension = {}
        self.datatype_converters = odict()
        self.datatype_indexers = odict()
        self.converters = []
        self.available_tracks = []
        self.set_external_metadata_tool = None
        self.indexers = []
        self.sniff_order = []
        self.upload_file_formats = []
        if root_dir and config:
            # Parse datatypes_conf.xml
            tree = galaxy.util.parse_xml( config )
            root = tree.getroot()
            # Load datatypes and converters from config
            self.log.debug( 'Loading datatypes from %s' % config )
            registration = root.find( 'registration' )
            self.datatype_converters_path = os.path.join( root_dir, registration.get( 'converters_path', 'lib/galaxy/datatypes/converters' ) )
            self.datatype_indexers_path = os.path.join( root_dir, registration.get( 'indexers_path', 'lib/galaxy/datatypes/indexers' ) )
            if not os.path.isdir( self.datatype_converters_path ):
                raise ConfigurationError( "Directory does not exist: %s" % self.datatype_converters_path )
            if not os.path.isdir( self.datatype_indexers_path ):
                raise ConfigurationError( "Directory does not exist: %s" % self.datatype_indexers_path )                
            for elem in registration.findall( 'datatype' ):
                try:
                    extension = elem.get( 'extension', None ) 
                    type = elem.get( 'type', None )
                    mimetype = elem.get( 'mimetype', None )
                    display_in_upload = elem.get( 'display_in_upload', False )
                    if extension and type:
                        fields = type.split( ':' )
                        datatype_module = fields[0]
                        datatype_class = fields[1]
                        fields = datatype_module.split( '.' )
                        module = __import__( fields.pop(0) )
                        for mod in fields:
                            module = getattr( module, mod )
                        self.datatypes_by_extension[extension] = getattr( module, datatype_class )()
                        if mimetype is None:
                            # Use default mime type as per datatype spec
                            mimetype = self.datatypes_by_extension[extension].get_mime()
                        self.mimetypes_by_extension[extension] = mimetype
                        if hasattr( getattr( module, datatype_class ), "get_track_type" ):
                            self.available_tracks.append( extension )
                        if display_in_upload:
                            self.upload_file_formats.append( extension )
                        for converter in elem.findall( 'converter' ):
                            # Build the list of datatype converters which will later be loaded 
                            # into the calling app's toolbox.
                            converter_config = converter.get( 'file', None )
                            target_datatype = converter.get( 'target_datatype', None )
                            if converter_config and target_datatype:
                                self.converters.append( ( converter_config, extension, target_datatype ) )
                        for indexer in elem.findall( 'indexer' ):
                            # Build the list of datatype indexers for track building
                            indexer_config = indexer.get( 'file', None )
                            if indexer_config:
                                self.indexers.append( (indexer_config, extension) )
                        for composite_file in elem.findall( 'composite_file' ):
                            # add composite files
                            name = composite_file.get( 'name', None )
                            if name is None:
                                self.log.warning( "You must provide a name for your composite_file (%s)." % composite_file )
                            optional = composite_file.get( 'optional', False )
                            mimetype = composite_file.get( 'mimetype', None )
                            self.datatypes_by_extension[extension].add_composite_file( name, optional=optional, mimetype=mimetype )
                            
                except Exception, e:
                    self.log.warning( 'Error loading datatype "%s", problem: %s' % ( extension, str( e ) ) )
            # Load datatype sniffers from the config
            sniff_order = []
            sniffers = root.find( 'sniffers' )
            for elem in sniffers.findall( 'sniffer' ):
                type = elem.get( 'type', None )
                if type:
                    sniff_order.append( type )
            for type in sniff_order:
                try:
                    fields = type.split( ":" )
                    datatype_module = fields[0]
                    datatype_class = fields[1]
                    fields = datatype_module.split( "." )
                    module = __import__( fields.pop(0) )
                    for mod in fields:
                        module = getattr( module, mod )
                    aclass = getattr( module, datatype_class )() 
                    included = False
                    for atype in self.sniff_order:
                        if not issubclass( atype.__class__, aclass.__class__ ) and isinstance( atype, aclass.__class__ ):
                            included = True
                            break
                    if not included:
                        self.sniff_order.append( aclass )
                        self.log.debug( 'Loaded sniffer for datatype: %s' % type )
                except Exception, exc:
                    self.log.warning( 'Error appending datatype %s to sniff_order, problem: %s' % ( type, str( exc ) ) )
        #default values
        if len(self.datatypes_by_extension) < 1:
            self.datatypes_by_extension = { 
                'ab1'         : binary.Ab1(),
                'axt'         : sequence.Axt(),
                'bam'         : binary.Bam(),
                'bed'         : interval.Bed(), 
                'binseq.zip'  : binary.Binseq(),
                'blastxml'    : xml.BlastXml(),
                'coverage'    : coverage.LastzCoverage(),
                'customtrack' : interval.CustomTrack(),
                'csfasta'     : sequence.csFasta(),
                'fasta'       : sequence.Fasta(),
                'fastq'       : sequence.Fastq(),
                'fastqsanger' : sequence.FastqSanger(),
                'gff'         : interval.Gff(),
                'gff3'        : interval.Gff3(),
                'genetrack'   : tracks.GeneTrack(),
                'interval'    : interval.Interval(), 
                'laj'         : images.Laj(),
                'lav'         : sequence.Lav(),
                'maf'         : sequence.Maf(),
                'qualsolid'   : qualityscore.QualityScoreSOLiD(),
                'qualsolexa'  : qualityscore.QualityScoreSolexa(),
                'qual454'     : qualityscore.QualityScore454(),
                'sam'         : tabular.Sam(), 
                'scf'         : binary.Scf(),
                'sff'         : binary.Sff(),
                'tabular'     : tabular.Tabular(),
                'taxonomy'    : tabular.Taxonomy(),
                'txt'         : data.Text(),
                'txtseq.zip'  : data.Txtseq(),
                'wig'         : interval.Wiggle()
            }
            self.mimetypes_by_extension = { 
                'ab1'         : 'application/octet-stream',
                'axt'         : 'text/plain',
                'bam'         : 'application/octet-stream',
                'bed'         : 'text/plain', 
                'binseq.zip'  : 'application/zip',
                'blastxml'    : 'text/plain', 
                'customtrack' : 'text/plain',
                'csfasta'     : 'text/plain',
                'fasta'       : 'text/plain',
                'fastq'       : 'text/plain',
                'fastqsanger' : 'text/plain',
                'gff'         : 'text/plain',
                'gff3'        : 'text/plain',
                'interval'    : 'text/plain', 
                'laj'         : 'text/plain',
                'lav'         : 'text/plain',
                'maf'         : 'text/plain',
                'qualsolid'   : 'text/plain',
                'qualsolexa'  : 'text/plain',
                'qual454'     : 'text/plain',
                'sam'         : 'text/plain',
                'scf'         : 'application/octet-stream',
                'sff'         : 'application/octet-stream',
                'tabular'     : 'text/plain',
                'taxonomy'    : 'text/plain',
                'txt'         : 'text/plain',
                'txtseq.zip'  : 'application/zip',
                'wig'         : 'text/plain'
            }
        # Default values - the order in which we attempt to determine data types is critical
        # because some formats are much more flexibly defined than others.
        if len(self.sniff_order) < 1:
            self.sniff_order = [
                binary.Bam(),
                binary.Sff(),
                xml.BlastXml(),
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
                interval.Gff(),
                interval.Gff3(),
                interval.Interval(),
                tabular.Sam()
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
        
    def get_mimetype_by_extension(self, ext ):
        """Returns a mimetype based on an extension"""
        try:
            mimetype = self.mimetypes_by_extension[ext]
        except KeyError:
            #datatype was never declared
            mimetype = 'application/octet-stream'
            self.log.warning('unknown mimetype in data factory %s' % ext)
        return mimetype
    
    def get_datatype_by_extension(self, ext ):
        """Returns a datatype based on an extension"""
        try:
            builder = self.datatypes_by_extension[ext]
        except KeyError:
            builder = data.Text()
        return builder

    def change_datatype(self, data, ext ):
        data.extension = ext
        # call init_meta and copy metadata from itself.  The datatype
        # being converted *to* will handle any metadata copying and
        # initialization.
        if data.has_data():
            data.set_size()
            data.init_meta( copy_from=data )
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

    def load_datatype_converters( self, toolbox ):
        """Adds datatype converters from self.converters to the calling app's toolbox"""     
        for elem in self.converters:
            tool_config = elem[0]
            source_datatype = elem[1]
            target_datatype = elem[2]
            converter = toolbox.load_tool( os.path.join( self.datatype_converters_path, tool_config ) )
            toolbox.tools_by_id[converter.id] = converter
            if source_datatype not in self.datatype_converters:
                self.datatype_converters[source_datatype] = odict()
            self.datatype_converters[source_datatype][target_datatype] = converter
            self.log.debug( "Loaded converter: %s", converter.id )

    def load_external_metadata_tool( self, toolbox ):
        """Adds a tool which is used to set external metadata"""
        #we need to be able to add a job to the queue to set metadata. The queue will currently only accept jobs with an associated tool.
        #We'll create a special tool to be used for Auto-Detecting metadata; this is less than ideal, but effective
        #Properly building a tool without relying on parsing an XML file is near impossible...so we'll create a temporary file 
        tool_xml_text = """
            <tool id="__SET_METADATA__" name="Set External Metadata" version="1.0.0" tool_type="set_metadata">
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
        
    def load_datatype_indexers( self, toolbox ):
        """Adds indexers from self.indexers to the toolbox from app"""
        for elem in self.indexers:
            tool_config = elem[0]
            datatype = elem[1]
            indexer = toolbox.load_tool( os.path.join( self.datatype_indexers_path, tool_config ) )
            toolbox.tools_by_id[indexer.id] = indexer
            self.datatype_indexers[datatype] = indexer
            self.log.debug( "Loaded indexer: %s", indexer.id )
            
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

    def get_indexers_by_datatype( self, ext ):
        """Returns indexers based on datatype"""
        class_chain = list()
        source_datatype = type(self.get_datatype_by_extension(ext))
        for ext_spec in self.datatype_indexers.keys():
            datatype = type(self.get_datatype_by_extension(ext_spec))
            if issubclass( source_datatype, datatype ):
                class_chain.append( ext_spec )
        # Prioritize based on class chain
        ext2type = lambda x: self.get_datatype_by_extension(x)
        class_chain = sorted(class_chain, lambda x,y: issubclass(ext2type(x),ext2type(y)) and -1 or 1)
        return [self.datatype_indexers[x] for x in class_chain]
    
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
                datasets = dataset.get_converted_files_by_type( convert_ext )
                if datasets:
                    ret_data = datasets[0]
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

