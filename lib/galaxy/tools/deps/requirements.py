import copy

import six

from galaxy.util import (
    asbool,
    xml_text,
)
from galaxy.util.oset import OrderedSet


DEFAULT_REQUIREMENT_TYPE = "package"
DEFAULT_REQUIREMENT_VERSION = None


@six.python_2_unicode_compatible
class ToolRequirement( object ):
    """
    Represents an external requirement that must be available for the tool to
    run (for example, a program, package, or library).  Requirements can
    optionally assert a specific version.
    """
    def __init__( self, name=None, type=None, version=None, specs=[] ):
        self.name = name
        self.type = type
        self.version = version
        self.specs = specs

    def to_dict( self ):
        specs = [s.to_dict() for s in self.specs]
        return dict(name=self.name, type=self.type, version=self.version, specs=specs)

    def copy( self ):
        return copy.deepcopy( self )

    @staticmethod
    def from_dict( dict ):
        version = dict.get( "version", None )
        name = dict.get("name", None)
        type = dict.get("type", None)
        specs = [RequirementSpecification.from_dict(s) for s in dict.get("specs", [])]
        return ToolRequirement( name=name, type=type, version=version, specs=specs )

    def __eq__(self, other):
        return self.name == other.name and self.type == other.type and self.version == other.version and self.specs == other.specs

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.name, self.type, self.version, frozenset(self.specs)))

    def __str__(self):
        return "ToolRequirement[%s,version=%s,type=%s,specs=%s]" % (self.name, self.version, self.type, self.specs)

    __repr__ = __str__


class RequirementSpecification(object):
    """Refine a requirement using a URI."""

    def __init__(self, uri, version=None):
        self.uri = uri
        self.version = version

    @property
    def specifies_version(self):
        return self.version is not None

    @property
    def short_name(self):
        return self.uri.split("/")[-1]

    def to_dict(self):
        return dict(uri=self.uri, version=self.version)

    @staticmethod
    def from_dict(dict):
        uri = dict.get["uri"]
        version = dict.get("version", None)
        return RequirementSpecification(uri=uri, version=version)

    def __eq__(self, other):
        return self.uri == other.uri and self.version == other.version

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self.uri, self.version))


class ToolRequirements(object):
    """
    Represents all requirements (packages, env vars) needed to run a tool.
    """
    def __init__(self, tool_requirements=None):
        if tool_requirements:
            if not isinstance(tool_requirements, list):
                raise ToolRequirementsException('ToolRequirements Constructor expects a list')
            self.tool_requirements = OrderedSet([r if isinstance(r, ToolRequirement) else ToolRequirement.from_dict(r) for r in tool_requirements])
        else:
            self.tool_requirements = OrderedSet()

    @staticmethod
    def from_list(requirements):
        return ToolRequirements(requirements)

    @property
    def resolvable(self):
        return ToolRequirements([r for r in self.tool_requirements if r.type in {'package', 'set_environment'}])

    @property
    def packages(self):
        return ToolRequirements([r for r in self.tool_requirements if r.type == 'package'])

    def to_list(self):
        return [r.to_dict() for r in self.tool_requirements]

    def append(self, requirement):
        if not isinstance(requirement, ToolRequirement):
            requirement = ToolRequirement.from_dict(requirement)
        self.tool_requirements.add(requirement)

    def __eq__(self, other):
        return len(self.tool_requirements & other.tool_requirements) == len(self.tool_requirements) == len(other.tool_requirements)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __iter__(self):
        for r in self.tool_requirements:
            yield r

    def __getitem__(self, ii):
        return list(self.tool_requirements)[ii]

    def __len__(self):
        return len(self.tool_requirements)

    def __hash__(self):
        return sum([r.__hash__() for r in self.tool_requirements])


class ToolRequirementsException(Exception):
    pass


DEFAULT_CONTAINER_TYPE = "docker"
DEFAULT_CONTAINER_RESOLVE_DEPENDENCIES = False
DEFAULT_CONTAINER_SHELL = "/bin/sh"  # Galaxy assumes bash, but containers are usually thinner.


@six.python_2_unicode_compatible
class ContainerDescription( object ):

    def __init__(
        self,
        identifier=None,
        type=DEFAULT_CONTAINER_TYPE,
        resolve_dependencies=DEFAULT_CONTAINER_RESOLVE_DEPENDENCIES,
        shell=DEFAULT_CONTAINER_SHELL,
    ):
        self.identifier = identifier
        self.type = type
        self.resolve_dependencies = resolve_dependencies
        self.shell = shell

    def to_dict( self ):
        return dict(
            identifier=self.identifier,
            type=self.type,
            resolve_dependencies=self.resolve_dependencies,
            shell=self.shell,
        )

    @staticmethod
    def from_dict( dict ):
        identifier = dict["identifier"]
        type = dict.get("type", DEFAULT_CONTAINER_TYPE)
        resolve_dependencies = dict.get("resolve_dependencies", DEFAULT_CONTAINER_RESOLVE_DEPENDENCIES)
        shell = dict.get("shell", DEFAULT_CONTAINER_SHELL)
        return ContainerDescription(
            identifier=identifier,
            type=type,
            resolve_dependencies=resolve_dependencies,
            shell=shell,
        )

    def __str__(self):
        return "ContainerDescription[identifier=%s,type=%s]" % (self.identifier, self.type)


def parse_requirements_from_dict( root_dict ):
    requirements = root_dict.get("requirements", [])
    containers = root_dict.get("containers", [])
    return ToolRequirements.from_list(requirements), map(ContainerDescription.from_dict, containers)


def parse_requirements_from_xml( xml_root ):
    """

    >>> from xml.etree import ElementTree
    >>> def load_requirements( contents ):
    ...     contents_document = '''<tool><requirements>%s</requirements></tool>'''
    ...     root = ElementTree.fromstring( contents_document % contents )
    ...     return parse_requirements_from_xml( root )
    >>> reqs, containers = load_requirements('''<requirement>bwa</requirement>''')
    >>> reqs[0].name
    'bwa'
    >>> reqs[0].version is None
    True
    >>> reqs[0].type
    'package'
    >>> reqs, containers = load_requirements('''<requirement type="binary" version="1.3.3">cufflinks</requirement>''')
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

    requirements = ToolRequirements()
    for requirement_elem in requirement_elems:
        name = xml_text( requirement_elem )
        type = requirement_elem.get( "type", DEFAULT_REQUIREMENT_TYPE )
        version = requirement_elem.get( "version", DEFAULT_REQUIREMENT_VERSION )
        requirement = ToolRequirement( name=name, type=type, version=version )
        requirements.append( requirement )

    container_elems = []
    if requirements_elem is not None:
        container_elems = requirements_elem.findall( 'container' )

    containers = map(container_from_element, container_elems)

    return requirements, containers


def container_from_element(container_elem):
    identifier = xml_text(container_elem)
    type = container_elem.get("type", DEFAULT_CONTAINER_TYPE)
    resolve_dependencies = asbool(container_elem.get("resolve_dependencies", DEFAULT_CONTAINER_RESOLVE_DEPENDENCIES))
    shell = container_elem.get("shell", DEFAULT_CONTAINER_SHELL)
    container = ContainerDescription(
        identifier=identifier,
        type=type,
        resolve_dependencies=resolve_dependencies,
        shell=shell,
    )
    return container
