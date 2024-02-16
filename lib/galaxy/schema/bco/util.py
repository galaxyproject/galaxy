"""Utilities for working with BCO models.

We don't have a lot of functional code in this schema module so this may belong
somewhere else in another galaxy-data package.
"""

import hashlib
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from galaxy.schema.bco import (
    BioComputeObject,
    BioComputeObjectCore,
    ContributionEnum,
    Contributor,
    ExecutionDomain,
    ExternalDataEndpoint,
    GalaxyExtension,
    GalaxyExtensionDomain,
    SoftwarePrerequisite,
)
from galaxy.schema.bco.execution_domain import (
    ScriptItem,
    Uri as ExecutionUri,
)
from galaxy.util.path import StrOrBytesPath


def _galaxy_script_item(galaxy_url: str) -> ScriptItem:
    """Convert a Galaxy URL into a 'ScriptItem'."""
    return ScriptItem(uri=ExecutionUri(uri=galaxy_url))


def extension_domains(galaxy_url: str, galaxy_version: str) -> List[GalaxyExtensionDomain]:
    galaxy_extension = GalaxyExtension(
        galaxy_url=galaxy_url,
        galaxy_version=galaxy_version,
    )
    return [GalaxyExtensionDomain(galaxy_extension=galaxy_extension)]


def galaxy_execution_domain(
    url: str,
    workflow_url: str,
    software_prerequisites: Optional[List[SoftwarePrerequisite]] = None,
    environment_variables: Optional[Dict[str, str]] = None,
) -> ExecutionDomain:
    data_endpoint = ExternalDataEndpoint(
        name="Access to Galaxy",
        url=url,
    )
    execution_domain = ExecutionDomain(
        script=[_galaxy_script_item(workflow_url)],
        script_driver="Galaxy",
        software_prerequisites=software_prerequisites or [],
        external_data_endpoints=[data_endpoint],
        environment_variables=environment_variables or {},
    )
    return execution_domain


def write_to_file(object_id: str, core_object: BioComputeObjectCore, output: StrOrBytesPath) -> None:
    # core_dict = core_object.dict()
    etag = hashlib.sha256(core_object.model_dump_json(indent=4).encode()).hexdigest()
    object = BioComputeObject(object_id=object_id, etag=etag, **core_object.model_dump())
    with open(output, "w") as f:
        f.write(object.model_dump_json(indent=4, exclude_none=True))


def get_contributors(creator_metadata: Optional[List[Dict[str, Any]]]):
    contributors: List[Contributor] = []
    if creator_metadata:
        for creator in creator_metadata:
            name = None
            email = None
            orcid = None

            if creator["class"] == "Person":
                if "name" in creator:
                    name = creator["name"]
                if "email" in creator:
                    email = creator["email"]
                if "identifier" in creator and "://" in creator["identifier"]:  # Must be an URL
                    orcid = creator["identifier"]

            if name:
                contributors.append(
                    Contributor(
                        contribution=[ContributionEnum.contributedBy],
                        name=name,
                        email=email,
                        orcid=orcid,
                    )
                )
    return contributors
