"""
Provides mapping between extensions and datatypes, mime-types, etc.
"""
import os
import logging
import data, tabular, interval, images, sequence, qualityscore
import genetics # needed for rgenetics tools	
import galaxy.util
from galaxy.util.odict import odict

class Registry( object ):
    def __init__( self, datatypes=[], sniff_order=[] ):
        self.log = logging.getLogger(__name__)
        self.datatypes_by_extension = {}
        self.mimetypes_by_extension = {}
        self.datatype_converters = odict()
        self.upload_file_formats = []
        self.sniff_order = []
        for ext, kind in datatypes:
            # Data types are defined in the config like this:
            # #<file extension> = <data type class>,<mime type (optional)>,<display in upload select list (optional)>
            try:
                fields = kind.split(",")
                kind = fields[0].strip()
                mime_type = None
                display_in_upload = False
                # See if we have a mime type or a display_in_upload
                try:
                    ele = fields[1].strip()
                    if ele:
                        if ele == 'display_in_upload':
                            display_in_upload = True
                        else:
                            mime_type = ele
                except:
                    pass
                # See if we have a display_in_upload
                if not display_in_upload:
                    try:
                        ele = fields[2].strip()
                        if ele == 'display_in_upload':
                            display_in_upload = True
                    except:
                        pass
                if display_in_upload:
                    self.upload_file_formats.append( ext )
                fields = kind.split(":")
                datatype_module = fields[0]
                datatype_class = fields[1]
                fields = datatype_module.split(".")
                module = __import__( fields.pop(0) )
                for mod in fields:
                    module = getattr(module,mod)
                self.datatypes_by_extension[ext] = getattr(module, datatype_class)()
                if mime_type is None:
                    # Use default mime type as per datatype spec
                    mime_type = self.datatypes_by_extension[ext].get_mime()
                self.mimetypes_by_extension[ext] = mime_type
            except Exception, e:
                self.log.warning('error loading datatype "%s", problem: %s' % ( ext, str( e ) ) )
        #default values
        if len(self.datatypes_by_extension) < 1:
            self.datatypes_by_extension = { 
                'ab1'         : images.Ab1(),
                'axt'         : sequence.Axt(),
                'bed'         : interval.Bed(), 
                'binseq.zip'  : images.Binseq(),
                'customtrack' : interval.CustomTrack(),
                'fasta'       : sequence.Fasta(),
                'fastq'       : sequence.Fastq(),
                'gff'         : interval.Gff(),
                'gff3'        : interval.Gff3(),  
                'interval'    : interval.Interval(), 
                'laj'         : images.Laj(),
                'lav'         : sequence.Lav(),
                'maf'         : sequence.Maf(),
                'qual'        : qualityscore.QualityScore(),
                'scf'         : images.Scf(),
                'tabular'     : tabular.Tabular(),
                'taxonomy'    : tabular.Taxonomy(),
                'txt'         : data.Text(),
                'txtseq.zip'  : images.Txtseq(),
                'wig'         : interval.Wiggle()
            }
            self.mimetypes_by_extension = { 
                'ab1'         : 'application/octet-stream',
                'axt'         : 'text/plain',
                'bed'         : 'text/plain', 
                'binseq.zip'  : 'application/zip',
                'customtrack' : 'text/plain',
                'fasta'       : 'text/plain',
                'fastq'       : 'text/plain',
                'gff'         : 'text/plain',
                'gff3'        : 'text/plain',
                'interval'    : 'text/plain', 
                'laj'         : 'text/plain',
                'lav'         : 'text/plain',
                'maf'         : 'text/plain',
                'qual'        : 'text/plain',
                'scf'         : 'application/octet-stream',
                'tabular'     : 'text/plain',
                'taxonomy'    : 'text/plain',
                'txt'         : 'text/plain',
                'txtseq.zip'  : 'application/zip',
                'wig'         : 'text/plain'
            }
        """
        The order in which we attempt to determine data types is critical
        because some formats are much more flexibly defined than others.
        """
        sniff_order.sort()
        for ele in sniff_order:
            try:
                ord = ele[0]
                kind = ele[1]
                fields = kind.split( ":" )
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
            except Exception, exc:
                self.log.warning( 'error appending datatype: %s to sniff_order, error: %s' % ( str( kind ), str( exc ) ) )
        #default values
        if len(self.sniff_order) < 1:
            self.sniff_order = [
                sequence.Maf(),
                sequence.Lav(),
                sequence.Fasta(),
                interval.Wiggle(),
                images.Html(),
                sequence.Axt(),
                interval.Bed(), 
                interval.CustomTrack(),
                interval.Gff(),
                interval.Gff3(),
                interval.Interval()
            ]
        def append_to_sniff_order():
            """Just in case any supported data types are not included in the config's sniff_order section."""
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
    
    def get_mimetype_by_extension(self, ext ):
        """Returns a mimetype based on an extension"""
        try:
            mimetype = self.mimetypes_by_extension[ext]
        except KeyError:
            #datatype was never declared
            mimetype = 'application/octet-stream'
            self.log.warning('unkown mimetype in data factory %s' % ext)
        return mimetype
    
    def get_datatype_by_extension(self, ext ):
        """Returns a datatype based on an extension"""
        try:
            builder = self.datatypes_by_extension[ext]
        except KeyError:
            builder = data.Text()
            self.log.warning('unknown extension in data factory %s' % ext)
        return builder

    def change_datatype(self, data, ext ):
        data.extension = ext
        # call init_meta and copy metadata from itself.  The datatype
        # being converted *to* will handle any metadata copying and
        # initialization.
        if data.has_data():
            data.init_meta( copy_from=data )
            if isinstance( data.datatype, tabular.Tabular ):
                data.set_readonly_meta()
            data.set_peek()
        return data

    def old_change_datatype(self, data, ext):
        """Creates and returns a new datatype based on an existing data and an extension"""
        newdata = factory(ext)(id=data.id)
        for key, value in data.__dict__.items():
            setattr(newdata, key, value)
        newdata.ext = ext
        return newdata
        
    def load_datatype_converters(self, datatype_converters_config, datatype_converters_path, toolbox):
        """Loads datatype converters from a file, and adds to the toolbox"""
        self.datatype_converters = odict()        
        tree = galaxy.util.parse_xml( datatype_converters_config )
        root = tree.getroot()
        self.log.debug( "Loading converters from %s" % (datatype_converters_config) )
        for elem in root.findall("converter"):
            path = elem.get("file")
            source_datatype = elem.get("source_datatype").split(",")
            target_datatype = elem.get("target_datatype")
            converter = toolbox.load_tool( os.path.join( datatype_converters_path, path ) )
            self.log.debug( "Loaded converter: %s", converter.id )
            toolbox.tools_by_id[converter.id] = converter
            for source_d in source_datatype:
                if source_d not in self.datatype_converters:
                    self.datatype_converters[source_d] = odict()
                self.datatype_converters[source_d][target_datatype] = converter
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
