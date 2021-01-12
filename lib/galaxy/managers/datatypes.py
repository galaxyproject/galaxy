from typing import (
    Dict,
    List,
    Optional,
    Union,
)

from pydantic import (
    BaseModel,
    Field,
    HttpUrl
)

from galaxy.datatypes.data import Data
from galaxy.datatypes.registry import Registry


class CompositeFileInfo(BaseModel):
    name: str = Field(
        ...,  # Mark this field as required
        title="Name",
        description="The name of this composite file"
    )
    optional: bool = Field(
        title="Optional",
        description=""  # TODO add description
    )
    mimetype: Optional[str] = Field(
        title="MIME type",
        description="The MIME type of this file"
    )
    description: Optional[str] = Field(
        title="Description",
        description="Summary description of the purpouse of this file"
    )
    substitute_name_with_metadata: Optional[str] = Field(
        title="Substitute name with metadata",
        description=""  # TODO add description
    )
    is_binary: bool = Field(
        title="Is binary",
        description="Whether this file is a binary file"
    )
    to_posix_lines: bool = Field(
        title="To posix lines",
        description=""  # TODO add description
    )
    space_to_tab: bool = Field(
        title="Spaces to tabulation",
        description=""  # TODO add description
    )


class DatatypeDetails(BaseModel):
    extension: str = Field(
        ...,  # Mark this field as required
        title="Extension",
        description="The data type’s Dataset file extension",
        example="bed"
    )
    description: Optional[str] = Field(
        title="Description",
        description="A summary description for this data type"
    )
    description_url: Optional[HttpUrl] = Field(
        title="Description URL",
        description="The URL to a detailed description for this datatype",
        example="https://wiki.galaxyproject.org/Learn/Datatypes#Bed"
    )
    display_in_upload: bool = Field(
        default=False,
        title="Display in upload",
        description="If True, the associated file extension will be displayed in the `File Format` select list in the `Upload File from your computer` tool in the `Get Data` tool section of the tool panel"
    )
    composite_files: Optional[List[CompositeFileInfo]] = Field(
        default=None,
        title="Composite files",
        description="A collection of files composing this data type"
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
        example="bam",
    )
    target: str = Field(
        ...,  # Mark this field as required
        title="Target",
        description="Target type for conversion",
        example="bai",
    )
    tool_id: str = Field(
        ...,  # Mark this field as required
        title="Tool identifier",
        description="The converter tool identifier",
        example="CONVERTER_Bam_Bai_0",
    )


def view_index(
    datatypes_registry: Registry,
    extension_only: Optional[bool] = True,
    upload_only: Optional[bool] = True
) -> Union[List[DatatypeDetails], List[str]]:
    if extension_only:
        if upload_only:
            return datatypes_registry.upload_file_formats
        else:
            return [ext for ext in datatypes_registry.datatypes_by_extension]
    else:
        rval = []
        for datatype_info_dict in datatypes_registry.datatype_info_dicts:
            if upload_only and not datatype_info_dict.get('display_in_upload'):
                continue
            rval.append(datatype_info_dict)
        return rval


def view_mapping(datatypes_registry: Registry) -> DatatypesMap:
    ext_to_class_name: Dict[str, str] = {}
    classes = []
    for k, v in datatypes_registry.datatypes_by_extension.items():
        c = v.__class__
        ext_to_class_name[k] = f"{c.__module__}.{c.__name__}"
        classes.append(c)
    class_to_classes: Dict[str, Dict[str, bool]] = {}

    def visit_bases(types, cls):
        for base in cls.__bases__:
            if issubclass(base, Data):
                types.add(f"{base.__module__}.{base.__name__}")
            visit_bases(types, base)

    for c in classes:
        n = f"{c.__module__}.{c.__name__}"
        types = {n}
        visit_bases(types, c)
        class_to_classes[n] = {t: True for t in types}
    return DatatypesMap(ext_to_class_name=ext_to_class_name, class_to_classes=class_to_classes)


def view_types_and_mapping(
    datatypes_registry: Registry,
    extension_only: Optional[bool] = True,
    upload_only: Optional[bool] = True
) -> DatatypesCombinedMap:
    return DatatypesCombinedMap(
        datatypes=view_index(datatypes_registry, extension_only, upload_only),
        datatypes_mapping=view_mapping(datatypes_registry)
    )


def view_sniffers(datatypes_registry: Registry) -> List[str]:
    rval: List[str] = []
    for sniffer_elem in datatypes_registry.sniffer_elems:
        datatype = sniffer_elem.get('type')
        if datatype is not None:
            rval.append(datatype)
    return rval


def view_converters(datatypes_registry: Registry) -> List[DatatypeConverter]:
    converters: List[DatatypeConverter] = []
    for (source_type, targets) in datatypes_registry.datatype_converters.items():
        for target_type in targets:
            converters.append(DatatypeConverter(
                source=source_type,
                target=target_type,
                tool_id=targets[target_type].id,
            ))
    return converters


def view_edam_formats(datatypes_registry: Registry) -> Dict[str, str]:
    return datatypes_registry.edam_formats


def view_edam_data(datatypes_registry: Registry) -> Dict[str, str]:
    return datatypes_registry.edam_data
