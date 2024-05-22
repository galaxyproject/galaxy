import copy
import os
from typing import (
    Any,
    Callable,
    cast,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    Union,
)

from typing_extensions import (
    get_args,
    Literal,
)

from galaxy.util import (
    asbool,
    xml_text,
)
from galaxy.util.oset import OrderedSet

DEFAULT_REQUIREMENT_TYPE = "package"
DEFAULT_REQUIREMENT_VERSION = None


class ToolRequirement:
    """
    Represents an external requirement that must be available for the tool to
    run (for example, a program, package, or library).  Requirements can
    optionally assert a specific version.
    """

    def __init__(
        self,
        name: str,
        type: Optional[str] = None,
        version: Optional[str] = None,
        specs: Optional[Iterable["RequirementSpecification"]] = None,
    ) -> None:
        if specs is None:
            specs = []
        self.name = name
        self.type = type
        self.version = version
        self.specs = specs

    def to_dict(self) -> Dict[str, Any]:
        specs = [s.to_dict() for s in self.specs]
        return dict(name=self.name, type=self.type, version=self.version, specs=specs)

    def copy(self) -> "ToolRequirement":
        return copy.deepcopy(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ToolRequirement":
        version = d.get("version")
        name = d["name"]
        type = d.get("type")
        specs = [RequirementSpecification.from_dict(s) for s in d.get("specs", [])]
        return cls(name=name, type=type, version=version, specs=specs)

    def __eq__(self, other: Any) -> bool:
        return (
            self.name == other.name
            and self.type == other.type
            and self.version == other.version
            and self.specs == other.specs
        )

    def __hash__(self) -> int:
        return hash((self.name, self.type, self.version, frozenset(self.specs)))

    def __str__(self) -> str:
        return f"ToolRequirement[{self.name},version={self.version},type={self.type},specs={self.specs}]"

    __repr__ = __str__


class RequirementSpecification:
    """Refine a requirement using a URI."""

    def __init__(self, uri: str, version: Optional[str] = None) -> None:
        self.uri = uri
        self.version = version

    @property
    def specifies_version(self) -> bool:
        return self.version is not None

    @property
    def short_name(self) -> str:
        return self.uri.split("/")[-1]

    def to_dict(self) -> Dict[str, Any]:
        return dict(uri=self.uri, version=self.version)

    @classmethod
    def from_dict(cls, dict: Dict) -> "RequirementSpecification":
        uri = dict["uri"]
        version = dict.get("version", None)
        return cls(uri=uri, version=version)

    def __eq__(self, other: Any) -> bool:
        return self.uri == other.uri and self.version == other.version

    def __hash__(self) -> int:
        return hash((self.uri, self.version))


class ToolRequirements:
    """
    Represents all requirements (packages, env vars) needed to run a tool.
    """

    def __init__(self, tool_requirements: Optional[List[Union[ToolRequirement, Dict[str, Any]]]] = None) -> None:
        if tool_requirements:
            if not isinstance(tool_requirements, list):
                raise ToolRequirementsException("ToolRequirements Constructor expects a list")
            self.tool_requirements = OrderedSet(
                r if isinstance(r, ToolRequirement) else ToolRequirement.from_dict(r) for r in tool_requirements
            )
        else:
            self.tool_requirements = OrderedSet()

    @classmethod
    def from_list(cls, requirements: List[Union[ToolRequirement, Dict[str, Any]]]) -> "ToolRequirements":
        return cls(requirements)

    @property
    def resolvable(self) -> "ToolRequirements":
        return ToolRequirements([r for r in self.tool_requirements if r.type in {"package", "set_environment"}])

    @property
    def packages(self) -> "ToolRequirements":
        return ToolRequirements([r for r in self.tool_requirements if r.type == "package"])

    def to_list(self):
        return [r.to_dict() for r in self.tool_requirements]

    def append(self, requirement: Union[ToolRequirement, Dict[str, Any]]) -> None:
        if not isinstance(requirement, ToolRequirement):
            requirement = ToolRequirement.from_dict(requirement)
        self.tool_requirements.add(requirement)

    def __eq__(self, other: Any) -> bool:
        return (
            len(self.tool_requirements & other.tool_requirements)
            == len(self.tool_requirements)
            == len(other.tool_requirements)
        )

    def __iter__(self) -> Iterator[ToolRequirement]:
        yield from self.tool_requirements

    def __getitem__(self, ii) -> ToolRequirement:
        return list(self.tool_requirements)[ii]

    def __len__(self) -> int:
        return len(self.tool_requirements)

    def __hash__(self) -> int:
        return sum(r.__hash__() for r in self.tool_requirements)

    def to_dict(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self.tool_requirements]


class ToolRequirementsException(Exception):
    pass


DEFAULT_CONTAINER_TYPE = "docker"
DEFAULT_CONTAINER_RESOLVE_DEPENDENCIES = False
DEFAULT_CONTAINER_SHELL = "/bin/sh"  # Galaxy assumes bash, but containers are usually thinner.


class ContainerDescription:
    def __init__(
        self,
        identifier: str,
        type: str = DEFAULT_CONTAINER_TYPE,
        resolve_dependencies: bool = DEFAULT_CONTAINER_RESOLVE_DEPENDENCIES,
        shell: str = DEFAULT_CONTAINER_SHELL,
    ) -> None:
        # Force to lowercase because container image names must be lowercase.
        # Cached singularity images include the path on disk, so only lowercase
        # the image identifier portion. Note, the tag can also contain upper case
        # letters.
        self.identifier = identifier
        if identifier:
            parts = identifier.rsplit(os.sep, 1)
            if ":" in parts[-1]:
                name, tag = parts[-1].rsplit(":", 1)
                parts[-1] = f"{name.lower()}:{tag}"
            else:
                parts[-1] = parts[-1].lower()

            self.identifier = os.sep.join(parts)
        self.type = type
        self.resolve_dependencies = resolve_dependencies
        self.shell = shell
        self.explicit = False

    def to_dict(self, *args, **kwds) -> Dict[str, Any]:
        return dict(
            identifier=self.identifier,
            type=self.type,
            resolve_dependencies=self.resolve_dependencies,
            shell=self.shell,
        )

    @classmethod
    def from_dict(cls, dict: Dict[str, Any]) -> "ContainerDescription":
        identifier = dict["identifier"]
        type = dict.get("type", DEFAULT_CONTAINER_TYPE)
        resolve_dependencies = dict.get("resolve_dependencies", DEFAULT_CONTAINER_RESOLVE_DEPENDENCIES)
        shell = dict.get("shell", DEFAULT_CONTAINER_SHELL)
        return cls(
            identifier=identifier,
            type=type,
            resolve_dependencies=resolve_dependencies,
            shell=shell,
        )

    def __str__(self) -> str:
        return f"ContainerDescription[identifier={self.identifier},type={self.type}]"


ResourceType = Literal[
    "cores_min",
    "cores_max",
    "ram_min",
    "ram_max",
    "tmpdir_min",
    "tmpdir_max",
    "cuda_version_min",
    "cuda_compute_capability",
    "gpu_memory_min",
    "cuda_device_count_min",
    "cuda_device_count_max",
    "shm_size",
]
VALID_RESOURCE_TYPES = get_args(ResourceType)


class ResourceRequirement:
    def __init__(self, value_or_expression: Union[int, float, str], resource_type: ResourceType) -> None:
        self.value_or_expression = value_or_expression
        if not resource_type:
            raise ValueError("Missing resource requirement type")
        if resource_type not in VALID_RESOURCE_TYPES:
            raise ValueError(f"Invalid resource requirement type '{resource_type}'")
        self.resource_type = resource_type
        try:
            float(self.value_or_expression)
            self.runtime_required = False
        except ValueError:
            self.runtime_required = True

    def to_dict(self) -> Dict[str, Any]:
        return {"resource_type": self.resource_type, "value_or_expression": self.value_or_expression}

    def get_value(self, runtime: Optional[Dict] = None, js_evaluator: Optional[Callable] = None) -> float:
        if self.runtime_required:
            # TODO: hook up evaluator
            # return js_evaluator(self.value_or_expression, runtime)
            raise NotImplementedError(
                f"{self.value_or_expression} is not an integer or float value, expressions currently not implemented"
            )
        return float(self.value_or_expression)


def resource_requirements_from_list(requirements: Iterable[Dict[str, Any]]) -> List[ResourceRequirement]:
    cwl_to_galaxy = {
        "coresMin": "cores_min",
        "coresMax": "cores_max",
        "ramMin": "ram_min",
        "ramMax": "ram_max",
        "tmpdirMin": "tmpdir_min",
        "tmpdirMax": "tmpdir_max",
        "cudaVersionMin": "cuda_version_min",
        "cudaComputeCapability": "cuda_compute_capability",
        "gpuMemoryMin": "gpu_memory_min",
        "cudaDeviceCountMin": "cuda_device_count_min",
        "cudaDeviceCountMax": "cuda_device_count_max",
        "ShmSize": "shm_size",
    }
    rr = []
    for r in requirements:
        if r.get("class") == "ResourceRequirement":
            valid_key_set = set(cwl_to_galaxy.keys())
        elif r.get("type") == "resource":
            valid_key_set = set(cwl_to_galaxy.values())
        else:
            continue
        for key in valid_key_set.intersection(set(r.keys())):
            value = r[key]
            key = cast(ResourceType, cwl_to_galaxy.get(key, key))
            rr.append(ResourceRequirement(value_or_expression=value, resource_type=key))
    return rr


def parse_requirements_from_lists(
    software_requirements: List[Union[ToolRequirement, Dict[str, Any]]],
    containers: Iterable[Dict[str, Any]],
    resource_requirements: Iterable[Dict[str, Any]],
) -> Tuple[ToolRequirements, List[ContainerDescription], List[ResourceRequirement]]:
    return (
        ToolRequirements.from_list(software_requirements),
        [ContainerDescription.from_dict(c) for c in containers],
        resource_requirements_from_list(resource_requirements),
    )


def parse_requirements_from_xml(xml_root, parse_resources: bool = False):
    """
    Parses requirements, containers and optionally resource requirements from Xml tree.

    >>> from galaxy.util import parse_xml_string
    >>> def load_requirements(contents, parse_resources=False):
    ...     contents_document = '''<tool><requirements>%s</requirements></tool>'''
    ...     root = parse_xml_string(contents_document % contents)
    ...     return parse_requirements_from_xml(root, parse_resources=parse_resources)
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
    requirements_elem = xml_root.find("requirements")

    requirement_elems = []
    if requirements_elem is not None:
        requirement_elems = requirements_elem.findall("requirement")

    requirements = ToolRequirements()
    for requirement_elem in requirement_elems:
        name = xml_text(requirement_elem)
        type = requirement_elem.get("type", DEFAULT_REQUIREMENT_TYPE)
        version = requirement_elem.get("version", DEFAULT_REQUIREMENT_VERSION)
        requirement = ToolRequirement(name=name, type=type, version=version)
        requirements.append(requirement)

    container_elems = []
    if requirements_elem is not None:
        container_elems = requirements_elem.findall("container")

    containers = [container_from_element(c) for c in container_elems]
    if parse_resources:
        resource_elems = requirements_elem.findall("resource") if requirements_elem is not None else []
        resources = [resource_from_element(r) for r in resource_elems]
        return requirements, containers, resources

    return requirements, containers


def resource_from_element(resource_elem) -> ResourceRequirement:
    value_or_expression = xml_text(resource_elem)
    resource_type = resource_elem.get("type")
    return ResourceRequirement(value_or_expression=value_or_expression, resource_type=resource_type)


def container_from_element(container_elem) -> ContainerDescription:
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
