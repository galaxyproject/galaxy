"""
API operations allowing clients to determine datatype supported by Galaxy.
"""
import logging
from typing import (
    Dict,
    List,
    Optional,
    Union,
)

from fastapi import (
    Depends,
    Query,
)
from fastapi.routing import APIRouter
from fastapi_utils.cbv import cbv


from galaxy.app import UniverseApplication
from galaxy.datatypes.data import Data
from galaxy.datatypes.registry import Registry
from galaxy.datatypes.schema import (
    DatatypeConverter,
    DatatypeDetails,
    DatatypesCombinedMap,
    DatatypesMap,
)
from galaxy.util import asbool
from galaxy.web import expose_api_anonymous_and_sessionless
from galaxy.webapps.base.controller import BaseAPIController

from . import get_app

log = logging.getLogger(__name__)

router = APIRouter(tags=['datatypes'])

ExtensionOnlyQueryParam : Optional[bool] = Query(
    default=True,
    title="Extension only",
    description="Whether to return only the datatype's extension rather than the datatype's details",
)

UploadOnlyQueryParam : Optional[bool] = Query(
    default=True,
    title="Upload only",
    description="Whether to return only datatypes which can be uploaded",
)


def get_datatypes_registry(app: UniverseApplication = Depends(get_app)) -> Registry:
    return app.datatypes_registry


@cbv(router)
class FastAPIDatatypes:
    datatypes_registry: Registry = Depends(get_datatypes_registry)

    @router.get('/api/datatypes',
        summary="Lists all available data types",
        response_model=Union[List[DatatypeDetails], List[str]],
        response_description="List of data types")
    async def index(self,
                    extension_only: Optional[bool] = ExtensionOnlyQueryParam,
                    upload_only: Optional[bool] = UploadOnlyQueryParam
                    ) -> Union[List[DatatypeDetails], List[str]]:
        """Gets the list of all available data types."""
        try:
            return self._index(extension_only, upload_only)
        except Exception as e:
            log.exception('Could not get datat ypes')
            raise e

    @router.get('/api/datatypes/mapping',
        summary="Returns mappings for data types and their implementing classes",
        response_model=DatatypesMap,
        response_description="Dictionary to map data types with their classes")
    async def mapping(self) -> DatatypesMap:
        """Gets mappings for data types."""
        try:
            return self._mapping()
        except Exception as e:
            log.exception('Could not get data type mapping')
            raise e

    @router.get('/api/datatypes/types_and_mapping',
        summary="Returns all the data types extensions and their mappings",
        response_model=DatatypesCombinedMap,
        response_description="Dictionary to map data types with their classes")
    async def types_and_mapping(self) -> DatatypesCombinedMap:
        """Combines the datatype information from (/api/datatypes) and the
        mapping information from (/api/datatypes/mapping) into a single
        response."""
        return DatatypesCombinedMap(datatypes=self._index(), datatypes_mapping=self._mapping())

    @router.get('/api/datatypes/sniffers',
        summary="Returns the list of all installed sniffers",
        response_model=List[str],
        response_description="List of datatype sniffers")
    async def sniffers(self) -> List[str]:
        """Gets the list of all installed data type sniffers."""
        try:
            return self._sniffers()
        except Exception as e:
            log.exception('Could not get sniffers')
            raise e

    @router.get('/api/datatypes/converters',
        summary="Returns the list of all installed converters",
        response_model=List[DatatypeConverter],
        response_description="List of all datatype converters")
    async def converters(self) -> List[DatatypeConverter]:
        """Gets the list of all installed converters."""
        try:
            return self._converters()
        except Exception as e:
            log.exception('Could not get converters')
            raise e

    @router.get('/api/datatypes/edam_formats',
        summary="Returns a dictionary/map of datatypes and EDAM formats",
        response_model=Dict[str, str],
        response_description="Dictionary/map of datatypes and EDAM formats")
    async def edam_formats(self) -> Dict[str, str]:
        """Gets a map of datatypes and their corresponding EDAM formats."""
        try:
            return self.datatypes_registry.edam_formats
        except Exception as e:
            log.exception('Could not get EDAM format mappings')
            raise e

    @router.get('/api/datatypes/edam_data',
        summary="Returns a dictionary/map of datatypes and EDAM data",
        response_model=Dict[str, str],
        response_description="Dictionary/map of datatypes and EDAM data")
    async def edam_data(self) -> Dict[str, str]:
        """Gets a map of datatypes and their corresponding EDAM data."""
        try:
            return self.datatypes_registry.edam_data
        except Exception as e:
            log.exception('Could not get EDAM data mappings')
            raise e

    def _index(self, extension_only: Optional[bool] = True, upload_only: Optional[bool] = True) -> Union[List[DatatypeDetails], List[str]]:
        if extension_only:
            if upload_only:
                return self.datatypes_registry.upload_file_formats
            else:
                return [ext for ext in self.datatypes_registry.datatypes_by_extension]
        else:
            rval = []
            for datatype_info_dict in self.datatypes_registry.datatype_info_dicts:
                if upload_only and not datatype_info_dict.get('display_in_upload'):
                    continue
                rval.append(datatype_info_dict)
            return rval

    def _mapping(self) -> DatatypesMap:
        ext_to_class_name: Dict[str, str] = {}
        classes = []
        for k, v in self.datatypes_registry.datatypes_by_extension.items():
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

    def _sniffers(self) -> List[str]:
        rval: List[str] = []
        for sniffer_elem in self.datatypes_registry.sniffer_elems:
            datatype = sniffer_elem.get('type')
            if datatype is not None:
                rval.append(datatype)
        return rval

    def _converters(self) -> List[DatatypeConverter]:
        converters: List[DatatypeConverter] = []
        for (source_type, targets) in self.datatypes_registry.datatype_converters.items():
            for target_type in targets:
                converters.append(DatatypeConverter(
                    source=source_type,
                    target=target_type,
                    tool_id=targets[target_type].id,
                ))
        return converters


class DatatypesController(BaseAPIController):

    @expose_api_anonymous_and_sessionless
    def index(self, trans, **kwd):
        """
        GET /api/datatypes
        Return an object containing upload datatypes.
        """
        try:
            return self._index(trans, **kwd)
        except Exception as e:
            log.exception('Could not get datatypes')
            raise e

    def _index(self, trans, **kwd):
        datatypes_registry = self._datatypes_registry
        extension_only = asbool(kwd.get('extension_only', True))
        upload_only = asbool(kwd.get('upload_only', True))
        if extension_only:
            if upload_only:
                return datatypes_registry.upload_file_formats
            else:
                return [ext for ext in datatypes_registry.datatypes_by_extension]
        else:
            rval = []
            for datatype_info_dict in datatypes_registry.datatype_info_dicts:
                if not datatype_info_dict.get('display_in_upload') and upload_only:
                    continue
                rval.append(datatype_info_dict)
            return rval

    @expose_api_anonymous_and_sessionless
    def mapping(self, trans, **kwd):
        '''
        GET /api/datatypes/mapping
        Return a dictionary of class to class mappings.
        '''
        try:
            return self._mapping()
        except Exception as e:
            log.exception('Could not get datatype mapping')
            raise e

    def _mapping(self):
        ext_to_class_name = dict()
        classes = []
        for k, v in self._datatypes_registry.datatypes_by_extension.items():
            c = v.__class__
            ext_to_class_name[k] = c.__module__ + "." + c.__name__
            classes.append(c)
        class_to_classes = dict()

        def visit_bases(types, cls):
            for base in cls.__bases__:
                if issubclass(base, Data):
                    types.add(base.__module__ + "." + base.__name__)
                visit_bases(types, base)
        for c in classes:
            n = c.__module__ + "." + c.__name__
            types = {n}
            visit_bases(types, c)
            class_to_classes[n] = {t: True for t in types}
        return dict(ext_to_class_name=ext_to_class_name, class_to_classes=class_to_classes)

    @expose_api_anonymous_and_sessionless
    def types_and_mapping(self, trans, **kwd):
        """
        GET /api/datatypes/types_and_mapping

        Combine the datatype information from (/api/datatypes) and the
        mapping information from (/api/datatypes/mapping) into a single
        response.
        """
        return {
            "datatypes": self._index(trans, **kwd),
            "datatypes_mapping": self._mapping(),
        }

    @expose_api_anonymous_and_sessionless
    def sniffers(self, trans, **kwd):
        '''
        GET /api/datatypes/sniffers
        Return a list of sniffers.
        '''
        try:
            rval = []
            for sniffer_elem in self._datatypes_registry.sniffer_elems:
                datatype = sniffer_elem.get('type')
                if datatype is not None:
                    rval.append(datatype)
            return rval
        except Exception as e:
            log.exception('Could not get datatypes')
            raise e

    @expose_api_anonymous_and_sessionless
    def converters(self, trans, **kwd):
        converters = []
        for (source_type, targets) in self._datatypes_registry.datatype_converters.items():
            for target_type in targets:
                converters.append({
                    'source': source_type,
                    'target': target_type,
                    'tool_id': targets[target_type].id,
                })

        return converters

    @expose_api_anonymous_and_sessionless
    def edam_formats(self, trans, **kwds):
        return self._datatypes_registry.edam_formats

    @expose_api_anonymous_and_sessionless
    def edam_data(self, trans, **kwds):
        return self._datatypes_registry.edam_data

    @property
    def _datatypes_registry(self):
        return self.app.datatypes_registry
