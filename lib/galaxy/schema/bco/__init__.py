from typing import List

from pydantic import BaseModel
from typing_extensions import Literal

from .description_domain import (
    DescriptionDomain,
    PipelineStep,
    Uri as DescriptionDomainUri,
    XrefItem,
)
from .error_domain import ErrorDomain
from .execution_domain import (
    ExecutionDomain,
    ExternalDataEndpoint,
    ScriptItem,
    SoftwarePrerequisite,
    Uri as ExecutionDomainUri,
)
from .io_domain import (
    InputAndOutputDomain,
    InputSubdomainItem,
    OutputSubdomainItem,
    Uri as InputAndOutputDomainUri,
)
from .parametric_domain import (
    ParametricDomain,
    ParametricDomainItem,
)
from .provenance_domain import (
    ContributionEnum,
    Contributor,
    ProvenanceDomain,
)
from .usability_domain import UsabilityDomain

SPEC_VERSION = "https://w3id.org/ieee/ieee-2791-schema/2791object.json"


class GalaxyExtension(BaseModel):
    galaxy_url: str
    galaxy_version: str


class GalaxyExtensionDomain(BaseModel):
    extension_schema: Literal[
        "https://raw.githubusercontent.com/biocompute-objects/extension_domain/1.2.0/galaxy/galaxy_extension.json"
    ] = "https://raw.githubusercontent.com/biocompute-objects/extension_domain/1.2.0/galaxy/galaxy_extension.json"
    galaxy_extension: GalaxyExtension


class BioComputeObjectCore(BaseModel):
    """BioComputeObject pre-hash, used to generate etag."""

    description_domain: DescriptionDomain
    error_domain: ErrorDomain
    execution_domain: ExecutionDomain
    extension_domain: List[GalaxyExtensionDomain]
    io_domain: InputAndOutputDomain
    parametric_domain: ParametricDomain
    provenance_domain: ProvenanceDomain
    usability_domain: UsabilityDomain


class BioComputeObject(BioComputeObjectCore):
    object_id: str
    spec_version: str = SPEC_VERSION
    etag: str


__all__ = (
    "BioComputeObjectCore",
    "BioComputeObject",
    "Contributor",
    "ContributionEnum",
    "DescriptionDomain",
    "DescriptionDomainUri",
    "ErrorDomain",
    "ExecutionDomain",
    "ExecutionDomainUri",
    "ExternalDataEndpoint",
    "GalaxyExtension",
    "GalaxyExtensionDomain",
    "InputAndOutputDomain",
    "InputSubdomainItem",
    "OutputSubdomainItem",
    "InputAndOutputDomainUri",
    "ParametricDomain",
    "ParametricDomainItem",
    "PipelineStep",
    "ProvenanceDomain",
    "ScriptItem",
    "SoftwarePrerequisite",
    "SPEC_VERSION",
    "UsabilityDomain",
    "XrefItem",
)
