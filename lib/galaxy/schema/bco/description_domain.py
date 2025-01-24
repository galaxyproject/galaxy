# generated by datamodel-codegen:
#   filename:  https://opensource.ieee.org/2791-object/ieee-2791-schema/-/raw/master/description_domain.json
#   timestamp: 2022-09-13T23:51:48+00:00

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import (
    List,
    Optional,
)

from pydantic import (
    AnyUrl,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    RootModel,
)


class XrefItem(BaseModel):
    namespace: str = Field(..., description="External resource vendor prefix", examples=["pubchem.compound"])
    name: str = Field(..., description="Name of external reference", examples=["PubChem-compound"])
    ids: List[str] = Field(..., description="List of reference identifiers")
    access_time: datetime = Field(..., description="Date and time the external reference was accessed")


class Uri(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: Optional[str] = None
    uri: AnyUrl
    access_time: Optional[datetime] = Field(
        None, description="Time stamp of when the request for this data was submitted"
    )
    sha1_checksum: Optional[str] = Field(
        None, description="output of hash function that produces a message digest", pattern="[A-Za-z0-9]+"
    )


class ObjectId(RootModel):
    root: str = Field(
        ...,
        description="A unique identifier that should be applied to each IEEE-2791 Object instance, generated and assigned by a IEEE-2791 database engine. IDs should never be reused",
    )


class ContributionEnum(Enum):
    authoredBy = "authoredBy"
    contributedBy = "contributedBy"
    createdAt = "createdAt"
    createdBy = "createdBy"
    createdWith = "createdWith"
    curatedBy = "curatedBy"
    derivedFrom = "derivedFrom"
    importedBy = "importedBy"
    importedFrom = "importedFrom"
    providedBy = "providedBy"
    retrievedBy = "retrievedBy"
    retrievedFrom = "retrievedFrom"
    sourceAccessedBy = "sourceAccessedBy"


class Contributor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Name of contributor", examples=["Charles Darwin"])
    affiliation: Optional[str] = Field(
        None, description="Organization the particular contributor is affiliated with", examples=["HMS Beagle"]
    )
    email: Optional[EmailStr] = Field(
        None,
        description="electronic means for identification and communication purposes",
        examples=["name@example.edu"],
    )
    contribution: List[ContributionEnum] = Field(
        ..., description="type of contribution determined according to PAV ontology"
    )
    orcid: Optional[AnyUrl] = Field(
        None,
        description="Field to record author information. ORCID identifiers allow for the author to curate their information after submission. ORCID identifiers must be valid and must have the prefix ‘https://orcid.org/’",
        examples=["http://orcid.org/0000-0002-1825-0097"],
    )


class PrerequisiteItem(BaseModel):
    name: str = Field(
        ..., description="Public searchable name for reference or prereq.", examples=["Hepatitis C virus genotype 1"]
    )
    uri: Uri


class PipelineStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_number: int = Field(
        ...,
        description="Non-negative integer value representing the position of the tool in a one-dimensional representation of the pipeline.",
    )
    name: str = Field(..., description="This is a recognized name of the software tool", examples=["HIVE-hexagon"])
    description: str = Field(
        ..., description="Specific purpose of the tool.", examples=["Alignment of reads to a set of references"]
    )
    version: Optional[str] = Field(
        None,
        description="Version assigned to the instance of the tool used corresponding to the upstream release.",
        examples=["1.3"],
    )
    prerequisite: Optional[List[PrerequisiteItem]] = Field(None, description="Reference or required prereqs")
    input_list: List[Uri] = Field(..., description="URIs (expressed as a URN or URL) of the input files for each tool.")
    output_list: List[Uri] = Field(
        ..., description="URIs (expressed as a URN or URL) of the output files for each tool."
    )


class DescriptionDomain(BaseModel):
    keywords: List[str] = Field(..., description="Keywords to aid in search-ability and description of the object.")
    xref: Optional[List[XrefItem]] = Field(
        None, description="List of the databases or ontology IDs that are cross-referenced in the IEEE-2791 Object."
    )
    platform: Optional[List[str]] = Field(
        None,
        description="reference to a particular deployment of an existing platform where this IEEE-2791 Object can be reproduced.",
    )
    pipeline_steps: List[PipelineStep] = Field(
        ...,
        description="Each individual tool (or a well defined and reusable script) is represented as a step. Parallel processes are given the same step number.",
    )
