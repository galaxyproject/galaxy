from galaxy.util import xml_text

DEFAULT_REQUIREMENT_TYPE = "package"
DEFAULT_REQUIREMENT_VERSION = None


class ToolRequirement( object ):
    """
    Represents an external requirement that must be available for the tool to
    run (for example, a program, package, or library).  Requirements can
    optionally assert a specific version.
    """
    def __init__( self, name=None, type=None, version=None ):
        self.name = name
        self.type = type
        self.version = version

    def to_dict( self ):
        return dict(name=self.name, type=self.type, version=self.version)

    @staticmethod
    def from_dict( dict ):
        version = dict.get( "version", None )
        name = dict.get("name", None)
        type = dict.get("type", None)
        return ToolRequirement( name=name, type=type, version=version )


def parse_requirements_from_xml( xml_root ):
    """

    >>> from xml.etree import ElementTree
    >>> def load_requirements( contents ):
    ...     contents_document = '''<tool><requirements>%s</requirements></tool>'''
    ...     root = ElementTree.fromstring( contents_document % contents )
    ...     return parse_requirements_from_xml( root )
    >>> reqs = load_requirements('''<requirement>bwa</requirement>''')
    >>> reqs[0].name
    'bwa'
    >>> reqs[0].version is None
    True
    >>> reqs[0].type
    'package'
    >>> reqs = load_requirements('''<requirement type="binary" version="1.3.3">cufflinks</requirement>''')
    >>> reqs[0].name
    'cufflinks'
    >>> reqs[0].version
    '1.3.3'
    >>> reqs[0].type
    'binary'
    """
    requirements_elem = xml_root.find( "requirements" )

    requirement_elems = []
    if requirements_elem is not None:
        requirement_elems = requirements_elem.findall( 'requirement' )

    requirements = []
    for requirement_elem in requirement_elems:
        name = xml_text( requirement_elem )
        type = requirement_elem.get( "type", DEFAULT_REQUIREMENT_TYPE )
        version = requirement_elem.get( "version", DEFAULT_REQUIREMENT_VERSION )
        requirement = ToolRequirement( name=name, type=type, version=version )
        requirements.append( requirement )

    return requirements
