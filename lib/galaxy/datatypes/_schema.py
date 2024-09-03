from typing import (
    Dict,
    List,
    Optional,
)

from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    RootModel,
)


class CompositeFileInfo(BaseModel):
    name: str = Field(..., title="Name", description="The name of this composite file")  # Mark this field as required
    optional: bool = Field(title="Optional", description="")  # TODO add description
    mimetype: Optional[str] = Field(title="MIME type", description="The MIME type of this file")
    description: Optional[str] = Field(
        title="Description", description="Summary description of the purpouse of this file"
    )
    substitute_name_with_metadata: Optional[str] = Field(
        title="Substitute name with metadata", description=""  # TODO add description
    )
    is_binary: bool = Field(title="Is binary", description="Whether this file is a binary file")
    to_posix_lines: bool = Field(title="To posix lines", description="")  # TODO add description
    space_to_tab: bool = Field(title="Spaces to tabulation", description="")  # TODO add description


class DatatypeDetails(BaseModel):
    extension: str = Field(
        ...,  # Mark this field as required
        title="Extension",
        description="The data type’s Dataset file extension",
        examples=["bed"],
    )
    description: Optional[str] = Field(title="Description", description="A summary description for this data type")
    description_url: Optional[HttpUrl] = Field(
        title="Description URL",
        description="The URL to a detailed description for this datatype",
        examples=["https://wiki.galaxyproject.org/Learn/Datatypes#Bed"],
    )
    display_in_upload: bool = Field(
        default=False,
        title="Display in upload",
        description="If True, the associated file extension will be displayed in the `File Format` select list in the `Upload File from your computer` tool in the `Get Data` tool section of the tool panel",
    )
    composite_files: Optional[List[CompositeFileInfo]] = Field(
        default=None, title="Composite files", description="A collection of files composing this data type"
    )
    upload_warning: Optional[str] = Field(
        default=None,
        title="Upload warning",
        description="End-user information regarding potential pitfalls with this upload type.",
    )


class DatatypesMap(BaseModel):
    ext_to_class_name: Dict[str, str] = Field(
        ...,  # Mark this field as required
        title="Extension Map",
        description="Dictionary mapping datatype's extensions with implementation classes",
    )
    class_to_classes: Dict[str, Dict[str, bool]] = Field(
        ...,  # Mark this field as required
        title="Classes Map",
        description="Dictionary mapping datatype's classes with their base classes",
    )


class DatatypesCombinedMap(BaseModel):
    datatypes: List[str] = Field(
        ...,  # Mark this field as required
        title="Datatypes",
        description="List of datatypes extensions",
    )
    datatypes_mapping: DatatypesMap = Field(
        ...,  # Mark this field as required
        title="Datatypes Mapping",
        description="Dictionaries for mapping datatype's extensions/classes with their implementation classes",
    )


class DatatypeConverter(BaseModel):
    source: str = Field(
        ...,  # Mark this field as required
        title="Source",
        description="Source type for conversion",
        examples=["bam"],
    )
    target: str = Field(
        ...,  # Mark this field as required
        title="Target",
        description="Target type for conversion",
        examples=["bai"],
    )
    tool_id: str = Field(
        ...,  # Mark this field as required
        title="Tool identifier",
        description="The converter tool identifier",
        examples=["CONVERTER_Bam_Bai_0"],
    )


class DatatypeConverterList(RootModel):
    root: List[DatatypeConverter] = Field(title="List of data type converters", default=[])


class DatatypeEDAMDetails(BaseModel):
    prefix_IRI: str = Field(
        ...,  # Mark this field as required
        title="Prefix IRI",
        description="The EDAM prefixed Resource Identifier",
        examples=["format_1782"],
    )
    label: Optional[str] = Field(
        title="Label",
        description="The EDAM label",
        examples=["NCBI gene report format"],
    )
    definition: Optional[str] = Field(
        title="Definition",
        description="The EDAM definition",
        examples=["Entry (gene) format of the NCBI database."],
    )


class DatatypesEDAMDetailsDict(RootModel):
    root: Dict[str, DatatypeEDAMDetails] = Field(
        title="Dict of EDAM details for formats",
        default={},
    )
