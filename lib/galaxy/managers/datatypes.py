from typing import (
    Dict,
    List,
    Optional,
    Union,
)

from pydantic.tools import parse_obj_as

from galaxy.datatypes._schema import (
    DatatypeConverterList,
    DatatypeDetails,
    DatatypesCombinedMap,
    DatatypesEDAMDetailsDict,
    DatatypesMap,
    DatatypeVisualizationMapping,
    DatatypeVisualizationMappingsList,
)
from galaxy.datatypes.data import Data
from galaxy.datatypes.registry import Registry


def view_index(
    datatypes_registry: Registry, extension_only: Optional[bool] = True, upload_only: Optional[bool] = True
) -> Union[List[DatatypeDetails], List[str]]:
    if extension_only:
        if upload_only:
            return datatypes_registry.upload_file_formats
        else:
            return list(datatypes_registry.datatypes_by_extension)
    else:
        rval = []
        for datatype_info_dict in datatypes_registry.datatype_info_dicts:
            if upload_only and not datatype_info_dict.get("display_in_upload"):
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
        class_to_classes[n] = dict.fromkeys(types, True)
    return DatatypesMap(ext_to_class_name=ext_to_class_name, class_to_classes=class_to_classes)


def view_types_and_mapping(
    datatypes_registry: Registry, extension_only: Optional[bool] = True, upload_only: Optional[bool] = True
) -> DatatypesCombinedMap:
    return DatatypesCombinedMap(
        datatypes=view_index(datatypes_registry, extension_only, upload_only),
        datatypes_mapping=view_mapping(datatypes_registry),
    )


def view_sniffers(datatypes_registry: Registry) -> List[str]:
    rval: List[str] = []
    for sniffer_elem in datatypes_registry.sniffer_elems:
        datatype = sniffer_elem.get("type")
        if datatype is not None:
            rval.append(datatype)
    return rval


def view_converters(datatypes_registry: Registry) -> DatatypeConverterList:
    converters = []
    for source_type, targets in datatypes_registry.datatype_converters.items():
        for target_type in targets:
            converters.append(
                {
                    "source": source_type,
                    "target": target_type,
                    "tool_id": targets[target_type].id,
                }
            )
    return parse_obj_as(DatatypeConverterList, converters)


def _get_edam_details(datatypes_registry: Registry, edam_ids: Dict[str, str]) -> Dict[str, Dict]:
    details_dict = {}
    for format, edam_iri in edam_ids.items():
        edam_details = datatypes_registry.edam.get(edam_iri, {})

        details_dict[format] = {
            "prefix_IRI": edam_iri,
            "label": edam_details.get("label", None),
            "definition": edam_details.get("definition", None),
        }

    return details_dict


def view_edam_formats(
    datatypes_registry: Registry, detailed: Optional[bool] = False
) -> Union[Dict[str, str], Dict[str, Dict[str, str]]]:
    if detailed:
        return _get_edam_details(datatypes_registry, datatypes_registry.edam_formats)
    else:
        return datatypes_registry.edam_formats


def view_edam_data(
    datatypes_registry: Registry, detailed: Optional[bool] = False
) -> Union[Dict[str, str], Dict[str, Dict[str, str]]]:
    if detailed:
        return _get_edam_details(datatypes_registry, datatypes_registry.edam_data)
    else:
        return datatypes_registry.edam_data


def view_visualization_mappings(
    datatypes_registry: Registry, datatype: Optional[str] = None
) -> DatatypeVisualizationMappingsList:
    """
    Get datatype visualization mappings from the registry.

    Args:
        datatypes_registry: The datatypes registry
        datatype: If provided, return only the mapping for this datatype extension

    Returns:
        A list of datatype visualization mappings
    """
    mappings = []

    # Get all mappings
    all_mappings = datatypes_registry.get_all_visualization_mappings()

    # Filter for a specific datatype if requested
    if datatype and datatype in all_mappings:
        mapping_info = all_mappings[datatype]
        mappings.append(
            {
                "datatype": datatype,
                "visualization": mapping_info["visualization"],
            }
        )
    elif not datatype:
        for dt, mapping_info in all_mappings.items():
            mappings.append(
                {
                    "datatype": dt,
                    "visualization": mapping_info["visualization"],
                }
            )

    return parse_obj_as(DatatypeVisualizationMappingsList, mappings)


def get_preferred_visualization(datatypes_registry: Registry, datatype_extension: str) -> Optional[Dict[str, str]]:
    """
    Get the preferred visualization mapping for a specific datatype extension.
    Returns a dictionary with 'visualization' and 'default_params' keys, or None if no mapping exists.

    Preferred visualizations are defined inline within each datatype definition in the
    datatypes_conf.xml configuration file. These mappings determine which visualization plugin
    should be used by default when viewing datasets of a specific type.

    If no direct mapping exists for the extension, this method will walk up the inheritance
    chain to find a preferred visualization from a parent datatype class.

    Example configuration:
    <datatype extension="bam" type="galaxy.datatypes.binary:Bam" mimetype="application/octet-stream" display_in_upload="true">
        <visualization plugin="igv" />
    </datatype>
    """
    direct_mapping = datatypes_registry.visualization_mappings.get(datatype_extension)
    if direct_mapping:
        return direct_mapping

    current_datatype = datatypes_registry.get_datatype_by_extension(datatype_extension)
    if not current_datatype:
        return None

    # Use the same mapping approach as the datatypes API for consistency
    mapping_data = view_mapping(datatypes_registry)

    current_class_name = mapping_data.ext_to_class_name.get(datatype_extension)
    if not current_class_name:
        return None

    current_class_mappings = mapping_data.class_to_classes.get(current_class_name, {})

    for ext, visualization_mapping in datatypes_registry.visualization_mappings.items():
        if ext == datatype_extension:
            continue

        parent_class_name = mapping_data.ext_to_class_name.get(ext)
        if parent_class_name and parent_class_name in current_class_mappings:
            return visualization_mapping

    return None


__all__ = (
    "DatatypeConverterList",
    "DatatypeDetails",
    "DatatypesCombinedMap",
    "DatatypesEDAMDetailsDict",
    "DatatypesMap",
    "DatatypeVisualizationMapping",
    "DatatypeVisualizationMappingsList",
    "view_index",
    "view_mapping",
    "view_types_and_mapping",
    "view_sniffers",
    "view_converters",
    "view_edam_formats",
    "view_edam_data",
    "view_visualization_mappings",
    "get_preferred_visualization",
)
