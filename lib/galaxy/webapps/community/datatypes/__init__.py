import sys, logging, tarfile
import galaxy.util
from galaxy.util.bunch import Bunch

log = logging.getLogger( __name__ )

if sys.version_info[:2] == ( 2, 4 ):
    from galaxy import eggs
    eggs.require( 'ElementTree' )
    from elementtree import ElementTree
else:
    from xml.etree import ElementTree

class DatatypeVerificationError( Exception ):
    pass

class Registry( object ):
    def __init__( self, root_dir=None, config=None ):
        self.datatypes_by_extension = {}
        self.sniff_order = []
        if root_dir and config:
            # Parse datatypes_conf.xml
            tree = galaxy.util.parse_xml( config )
            root = tree.getroot()
            # Load datatypes and converters from config
            log.debug( 'Loading datatypes from %s' % config )
            registration = root.find( 'registration' )
            for elem in registration.findall( 'datatype' ):
                try:
                    extension = elem.get( 'extension', None )
                    dtype = elem.get( 'type', None )
                    model_object = elem.get( 'model', None )
                    if extension and dtype:
                        fields = dtype.split( ':' )
                        datatype_module = fields[0]
                        datatype_class = fields[1]
                        fields = datatype_module.split( '.' )
                        module = __import__( fields.pop(0) )
                        for mod in fields:
                            module = getattr( module, mod )
                        self.datatypes_by_extension[extension] = getattr( module, datatype_class )()
                        log.debug( 'Loaded datatype: %s' % dtype )
                    if model_object:
                        model_module, model_class = model_object.split( ':' )
                        fields = model_module.split( '.' )
                        module = __import__( fields.pop(0) )
                        for mod in fields:
                            module = getattr( module, mod )
                        self.datatypes_by_extension[extension].model_object = getattr( module, model_class )
                        log.debug( 'Added model class: %s to datatype: %s' % ( model_class, dtype ) )
                except Exception, e:
                    log.warning( 'Error loading datatype "%s", problem: %s' % ( extension, str( e ) ) )
            # Load datatype sniffers from the config
            sniff_order = []
            sniffers = root.find( 'sniffers' )
            for elem in sniffers.findall( 'sniffer' ):
                dtype = elem.get( 'type', None )
                if dtype:
                    sniff_order.append( dtype )
            for dtype in sniff_order:
                try:
                    fields = dtype.split( ":" )
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
                        log.debug( 'Loaded sniffer for datatype: %s' % dtype )
                except Exception, exc:
                    log.warning( 'Error appending datatype %s to sniff_order, problem: %s' % ( dtype, str( exc ) ) )
    def get_datatype_by_extension( self, ext ):
        return self.datatypes_by_extension.get( ext, None )
    def get_datatypes_for_select_list( self ):
        rval = []
        for ext, datatype in self.datatypes_by_extension.items():
            rval.append( ( ext, datatype.select_name ) )
        return rval
    def sniff( self, fname ):
        for datatype in sniff_order:
            try:
                datatype.sniff( fname )
                return datatype.file_ext
            except:
                pass

class Tool( object ):
    select_name = 'Tool'
    def __init__( self, model_object=None ):
        self.model_object = model_object
    def verify( self, file ):
        msg = ''
        try:
            tar = tarfile.TarFile( fileobj = file )
        except tarfile.ReadError:
            raise DatatypeVerificationError( 'The tool file is not a readable tar file' )
        xml_names = filter( lambda x: x.lower().endswith( '.xml' ), tar.getnames() )
        if not xml_names:
            raise DatatypeVerificationError( 'The tool file does not contain an XML file' )
        for xml_name in xml_names:
            try:
                tree = ElementTree.parse( tar.extractfile( xml_name ) )
                root = tree.getroot()
            except:
                log.exception( 'fail:' )
                continue
            if root.tag == 'tool':
                rval = Bunch()
                try:
                    rval.id = root.attrib['id']
                    rval.name = root.attrib['name']
                    rval.version = root.attrib['version']
                except KeyError, e:
                    raise DatatypeVerificationError( 'Tool XML file does not conform to the specification.  Missing required &lt;tool&gt; tag attribute: %s' % e )
                rval.description = None
                desc_tag = root.find( 'description' )
                if desc_tag is not None:
                    rval.description = desc_tag.text.strip()
                rval.message = 'Tool: %s %s, Version: %s, ID: %s' % ( rval.name, rval.description or '', rval.version, rval.id )
                return rval
        else:
            raise DatatypeVerificationError( 'Unable to find a properly formatted tool XML file' )
    def create_model_object( self, datatype_bunch ):
        if self.model_object is None:
            raise Exception( 'No model object configured for %s, please check the datatype configuration file' % self.__class__.__name__ )
        if datatype_bunch is None:
            # TODO: do it automatically
            raise Exception( 'Unable to create %s model object without passing in data' % self.__class__.__name__ )
        o = self.model_object()
        o.create_from_datatype( datatype_bunch )
        return o
    def sniff( self, fname ):
        try:
            self.verify( open( fname, 'r' ) )
            return True
        except:
            return False
