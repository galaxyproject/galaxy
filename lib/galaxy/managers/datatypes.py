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


__all__ = (
    "DatatypeConverterList",
    "DatatypeDetails",
    "DatatypesCombinedMap",
    "DatatypesEDAMDetailsDict",
    "DatatypesMap",
    "view_index",
    "view_mapping",
    "view_types_and_mapping",
    "view_sniffers",
    "view_converters",
)
