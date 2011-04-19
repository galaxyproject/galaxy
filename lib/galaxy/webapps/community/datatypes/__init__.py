import sys, logging, tarfile
from galaxy.util import parse_xml
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
        if root_dir and config:
            # Parse datatypes_conf.xml
            tree = parse_xml( config )
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
    def get_datatype_by_extension( self, ext ):
        return self.datatypes_by_extension.get( ext, None )
    def get_datatype_extensions( self ):
        rval = []
        for ext, datatype in self.datatypes_by_extension.items():
            rval.append( ext )
        return rval

class Tool( object ):
    def __init__( self, model_object=None ):
        self.model_object = model_object
        self.label = 'Tool'
    def verify( self, f, xml_files=[], tool_tags={} ):
        # xml_files and tool_tags will only be received if we're called from the ToolSuite.verify() method.
        try:
            tar = tarfile.open( f.name )
        except tarfile.ReadError, e:
            raise DatatypeVerificationError( 'Error reading the archive, problem: %s' % str( e ) )
        if not xml_files:
            # Make sure we're not uploading a tool suite
            if filter( lambda x: x.lower().find( 'suite_config.xml' ) >= 0, tar.getnames() ):
                raise DatatypeVerificationError( 'The archive includes a suite_config.xml file, so set the upload type to "Tool Suite".' )
            xml_files = filter( lambda x: x.lower().endswith( '.xml' ), tar.getnames() )
            if not xml_files:
                raise DatatypeVerificationError( 'The archive does not contain any xml config files.' )
        for xml_file in xml_files:
            try:
                tree = ElementTree.parse( tar.extractfile( xml_file ) )
                root = tree.getroot()
            except Exception, e:
                raise DatatypeVerificationError( 'Error parsing file "%s", problem: %s' % ( str( xml_file ), str( e ) ) )
            if root.tag == 'tool':
                if 'id' not in root.keys():
                    raise DatatypeVerificationError( "Tool xml file (%s) does not include the required 'id' attribute in the &lt;tool&gt; tag" % str( xml_file ) )
                if 'name' not in root.keys():
                    raise DatatypeVerificationError( "Tool xml file (%s) does not include the required 'name' attribute in the &lt;tool&gt; tag" % str( xml_file ) )
                if 'version' not in root.keys():
                    raise DatatypeVerificationError( "Tool xml file (%s) does not include the required 'version' attribute in the &lt;tool&gt; tag" % str( xml_file ) )
                if tool_tags:
                    # We are verifying the tools inside a tool suite, so the current tag should have been found in the suite_config.xml
                    # file parsed in the ToolSuite verify() method.  The tool_tags dictionary should include a key matching the current
                    # tool Id, and a tuple value matching the tool name and version.
                    if root.attrib[ 'id' ] not in tool_tags:
                        raise DatatypeVerificationError( 'Tool Id (%s) is not included in the suite_config.xml file.' % \
                                                         ( str( root.attrib[ 'id' ] ) ) )
                    tup = tool_tags[ root.attrib[ 'id' ] ]
                    if root.attrib[ 'name' ] != tup[ 0 ]:
                        raise DatatypeVerificationError( 'Tool name (%s) differs between suite_config.xml and the tool config file for tool Id (%s).' % \
                                                         ( str( root.attrib[ 'name' ] ), str( root.attrib[ 'id' ] ) ) )
                    if root.attrib[ 'version' ] != tup[ 1 ]:
                        raise DatatypeVerificationError( 'Tool version (%s) differs between suite_config.xml and the tool config file for tool Id (%s).' % \
                                                         ( str( root.attrib[ 'version' ] ), str( root.attrib[ 'id' ] ) ) )
                else:
                    # We are not verifying a tool suite, so we'll create a bunch for returning to the caller.
                    tool_bunch = Bunch()
                    try:
                        tool_bunch.id = root.attrib['id']
                        tool_bunch.name = root.attrib['name']
                        tool_bunch.version = root.attrib['version']
                    except KeyError, e:
                        raise DatatypeVerificationError( 'Tool XML file does not conform to the specification.  Missing required &lt;tool&gt; tag attribute: %s' % str( e ) )
                    tool_bunch.description = ''
                    desc_tag = root.find( 'description' )
                    if desc_tag is not None:
                        description = desc_tag.text
                        if description:
                            tool_bunch.description = description.strip()
                    tool_bunch.message = 'Tool: %s %s, Version: %s, Id: %s' % \
                        ( str( tool_bunch.name ), str( tool_bunch.description ), str( tool_bunch.version ), str( tool_bunch.id ) )
                    return tool_bunch
            else:
                # TODO: should we verify files that are not tool configs?
                log.debug( "The file named (%s) is not a tool config, so skipping verification." % str( xml_file ) )
    def create_model_object( self, datatype_bunch ):
        if self.model_object is None:
            raise Exception( 'No model object configured for %s, check the datatype configuration file' % self.__class__.__name__ )
        if datatype_bunch is None:
            # TODO: do it automatically
            raise Exception( 'Unable to create %s model object without passing in data' % self.__class__.__name__ )
        o = self.model_object()
        o.create_from_datatype( datatype_bunch )
        return o

class ToolSuite( Tool ):
    def __init__( self, model_object=None ):
        self.model_object = model_object
        self.label = 'Tool Suite'
    def verify( self, f ):
        """
        A sample tool suite config:
        <suite id="onto_toolkit" name="ONTO Toolkit" version="1.0">
            <description>ONTO-Toolkit is a collection of Galaxy tools which support the manipulation of bio-ontologies.</description>
            <tool id="get_ancestor_terms" name="Get the ancestor terms of a given OBO term" version="1.0.0">
                <description>Collects the ancestor terms from a given term in the given OBO ontology</description>
            </tool>
            <tool id="get_child_terms" name="Get the child terms of a given OBO term" version="1.0.0">
                <description>Collects the child terms from a given term in the given OBO ontology</description>
            </tool>
        </suite>
        """
        try:
            tar = tarfile.open( f.name )
        except tarfile.ReadError:
            raise DatatypeVerificationError( 'The archive is not a readable tar file.' )
        suite_config = filter( lambda x: x.lower().find( 'suite_config.xml' ) >=0, tar.getnames() )
        if not suite_config:
            raise DatatypeVerificationError( 'The archive does not contain the required suite_config.xml config file.  If you are uploading a single tool archive, set the upload type to "Tool".' )
        suite_config = suite_config[ 0 ]
        # Parse and verify suite_config
        archive_ok = False
        try:
            tree = ElementTree.parse( tar.extractfile( suite_config ) )
            root = tree.getroot()
            archive_ok = True
        except:
            log.exception( 'fail:' )
        if archive_ok and root.tag == 'suite':
            suite_bunch = Bunch()
            try:
                suite_bunch.id = root.attrib['id']
                suite_bunch.name = root.attrib['name']
                suite_bunch.version = root.attrib['version']
            except KeyError, e:
                raise DatatypeVerificationError( 'The file named tool-suite.xml does not conform to the specification.  Missing required &lt;suite&gt; tag attribute: %s' % str( e ) )
            suite_bunch.description = ''
            desc_tag = root.find( 'description' )
            if desc_tag is not None:
                description = desc_tag.text
                if description:
                    suite_bunch.description = description.strip()
            suite_bunch.message = 'Tool suite: %s %s, Version: %s, Id: %s' % \
                ( str( suite_bunch.name ), str( suite_bunch.description ), str( suite_bunch.version ), str( suite_bunch.id ) )
            # Create a dictionary of the tools in the suite where the keys are tool_ids and the
            # values are tuples of tool name and version
            tool_tags = {}
            for elem in root.findall( 'tool' ):
                tool_tags[ elem.attrib['id'] ] = ( elem.attrib['name'], elem.attrib['version'] )
        else:
            raise DatatypeVerificationError( "The file named %s is not a valid tool suite config." % str( suite_config ) )
        # Verify all included tool config files
        xml_files = filter( lambda x: x.lower().endswith( '.xml' ) and x.lower() != 'suite_config.xml', tar.getnames() )
        if not xml_files:
            raise DatatypeVerificationError( 'The archive does not contain any tool config (xml) files.' )
        Tool.verify( self, f, xml_files=xml_files, tool_tags=tool_tags )
        return suite_bunch
