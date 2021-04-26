from typing import (
    Dict,
    List,
    Optional,
    Union,
)

from pydantic.tools import parse_obj_as

from galaxy import model
from galaxy.datatypes._schema import (
    DatatypeConverterList,
    DatatypeDetails,
    DatatypesCombinedMap,
    DatatypesMap,
)
from galaxy.datatypes.data import Data
from galaxy.datatypes.registry import Registry
from galaxy.managers.collections import DatasetCollectionManager


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


def view_converters(datatypes_registry: Registry) -> DatatypeConverterList:
    converters = []
    for (source_type, targets) in datatypes_registry.datatype_converters.items():
        for target_type in targets:
            converters.append({
                'source': source_type,
                'target': target_type,
                'tool_id': targets[target_type].id,
            })
    return parse_obj_as(DatatypeConverterList, converters)

def get_converters_for_collection(trans, id, datatypes_registry: Registry, collection_manager: DatasetCollectionManager, instance_type="history"):
    dataset_collection_instance = collection_manager.get_dataset_collection_instance(
            trans,
            id=id,
            instance_type=instance_type,
            check_ownership=True
        )
    dbkeys_and_extensions = dataset_collection_instance.dataset_dbkeys_and_extensions_summary
    print("********************************************************** " + str(dbkeys_and_extenions))
    suitable_converters = []
    # TODO error checking
    for datatype in dbkeys_and_extensions[0]:
        new_converters = []
        new_converters = datatypes_registry.get_converters_by_datatype(datatype)
        print("********************************************************************" + str(new_converters))
    return suitable_converters

def view_edam_formats(datatypes_registry: Registry) -> Dict[str, str]:
    return datatypes_registry.edam_formats


def view_edam_data(datatypes_registry: Registry) -> Dict[str, str]:
    return datatypes_registry.edam_data
