"""
API operations allowing clients to determine datatype supported by Galaxy.
"""
import logging

from galaxy.datatypes.data import Data
from galaxy.util import asbool
from galaxy.web import expose_api_anonymous_and_sessionless
from galaxy.webapps.base.controller import BaseAPIController

log = logging.getLogger(__name__)


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
