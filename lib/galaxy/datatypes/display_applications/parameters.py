# Contains parameters that are used in Display Applications
import mimetypes
from dataclasses import dataclass
from typing import (
    Callable,
    Optional,
    TYPE_CHECKING,
    Union,
)
from urllib.parse import quote_plus

from galaxy.datatypes.data import Data
from galaxy.model import DatasetInstance
from galaxy.schema.schema import DatasetState
from galaxy.util import string_as_bool
from galaxy.util.template import fill_template

if TYPE_CHECKING:
    from galaxy.datatypes.registry import Registry
DEFAULT_DATASET_NAME = "dataset"


class DisplayApplicationParameter:
    """Abstract Class for Display Application Parameters"""

    type: Optional[str] = None

    @classmethod
    def from_elem(cls, elem, link):
        param_type = elem.get("type", None)
        assert param_type, "DisplayApplicationParameter requires a type"
        return parameter_type_to_class[param_type](elem, link)

    def __init__(self, elem, link):
        self.name = elem.get("name", None)
        assert self.name, "DisplayApplicationParameter requires a name"
        self.link = link
        self.url = elem.get(
            "url", self.name
        )  # name used in url for display purposes defaults to name; e.g. want the form of file.ext, where a '.' is not allowed as python variable name/keyword
        self.mime_type = elem.get("mimetype", None)
        self.guess_mime_type = string_as_bool(elem.get("guess_mimetype", "False"))
        self.viewable = string_as_bool(
            elem.get("viewable", "False")
        )  # only allow these to be viewed via direct url when explicitly set to viewable
        self.strip = string_as_bool(elem.get("strip", "False"))
        self.strip_https = string_as_bool(elem.get("strip_https", "False"))
        self.allow_override = string_as_bool(
            elem.get("allow_override", "False")
        )  # Passing query param app_<name>=<value> to dataset controller allows override if this is true.
        self.allow_cors = string_as_bool(elem.get("allow_cors", "False"))

    def get_value(self, other_values, dataset_hash, user_hash, trans):
        raise Exception("get_value() is unimplemented for DisplayApplicationDataParameter")

    def prepare(self, other_values, dataset_hash, user_hash, trans):
        return self.get_value(other_values, dataset_hash, user_hash, trans)

    def ready(self, other_values):
        return True

    def is_preparing(self, other_values):
        return False

    def build_url(self, other_values):
        return fill_template(self.url, context=other_values)


@dataclass
class DatasetLikeObject:
    get_file_name: Callable
    state: DatasetState
    extension: str
    name: str
    dbkey: Optional[str]
    datatype: Data


class DisplayApplicationDataParameter(DisplayApplicationParameter):
    """Parameter that returns a file_name containing the requested content"""

    type = "data"

    def __init__(self, elem, link):
        DisplayApplicationParameter.__init__(self, elem, link)
        self.extensions = elem.get("format", None)
        if self.extensions:
            self.extensions = self.extensions.split(",")
        self.metadata = elem.get("metadata", None)
        self.allow_extra_files_access = string_as_bool(elem.get("allow_extra_files_access", "False"))
        self.dataset = elem.get(
            "dataset", DEFAULT_DATASET_NAME
        )  # 'dataset' is default name assigned to dataset to be displayed
        assert not (
            self.extensions and self.metadata
        ), "A format or a metadata can be defined for a DisplayApplicationParameter, but not both."
        assert not (
            self.allow_extra_files_access and self.metadata
        ), "allow_extra_files_access or metadata can be defined for a DisplayApplicationParameter, but not both."
        self.viewable = string_as_bool(elem.get("viewable", "True"))  # data params should be viewable
        self.force_url_param = string_as_bool(elem.get("force_url_param", "False"))
        self.force_conversion = string_as_bool(elem.get("force_conversion", "False"))

    @property
    def datatypes_registry(self) -> "Registry":
        return self.link.display_application.app.datatypes_registry

    @property
    def formats(self):
        if self.extensions:
            return tuple(
                map(
                    type,
                    map(self.datatypes_registry.get_datatype_by_extension, self.extensions),
                )
            )
        return None

    def _get_dataset_like_object(self, other_values) -> Optional[Union[DatasetLikeObject, DatasetInstance]]:
        data = other_values.get(self.dataset, None)
        assert data, "Base dataset could not be found in values provided to DisplayApplicationDataParameter"
        if isinstance(data, DisplayDataValueWrapper):
            data = data.value
        if data.state != DatasetState.OK:
            return None
        if self.metadata:
            rval = getattr(data.metadata, self.metadata, None)
            if not rval:
                # May have to look at converted datasets
                for converted_dataset_association in data.implicitly_converted_datasets:
                    converted_dataset = converted_dataset_association.dataset
                    if converted_dataset.state != DatasetState.OK:
                        return None
                    rval = getattr(converted_dataset.metadata, self.metadata, None)
                    if rval:
                        data = converted_dataset
                        break
            assert rval, f'Unknown metadata name "{self.metadata}" provided for dataset type "{data.ext}".'
            return DatasetLikeObject(
                get_file_name=rval.get_file_name,
                state=data.state,
                extension="data",
                dbkey=data.dbkey,
                name=data.name,
                datatype=data.datatype,
            )
        elif (
            self.formats and self.extensions and (self.force_conversion or not isinstance(data.datatype, self.formats))
        ):
            for ext in self.extensions:
                rval = data.get_converted_files_by_type(ext)
                if rval:
                    return rval
            direct_match, target_ext, _ = self.datatypes_registry.find_conversion_destination_for_dataset_by_extensions(
                data.extension, self.extensions
            )
            assert direct_match or target_ext is not None, f"No conversion path found for data param: {self.name}"
            return None
        return data

    def get_value(self, other_values, dataset_hash, user_hash, trans):
        if data := self._get_dataset_like_object(other_values):
            return DisplayDataValueWrapper(data, self, other_values, dataset_hash, user_hash, trans)
        return None

    def prepare(self, other_values, dataset_hash, user_hash, trans):
        data = self._get_dataset_like_object(other_values)
        if not data and self.formats:
            data = other_values.get(self.dataset, None)
            # start conversion
            # FIXME: Much of this is copied (more than once...); should be some abstract method elsewhere called from here
            # find target ext
            (
                direct_match,
                target_ext,
                converted_dataset,
            ) = self.datatypes_registry.find_conversion_destination_for_dataset_by_extensions(
                data.extension, self.extensions
            )
            if not direct_match:
                if target_ext and not converted_dataset:
                    if isinstance(data, DisplayDataValueWrapper):
                        data = data.value
                    data.datatype.convert_dataset(trans, data, target_ext, return_output=True, visible=False)
                elif converted_dataset and converted_dataset.state == DatasetState.ERROR:
                    raise Exception(f"Dataset conversion failed for data parameter: {self.name}")
        return self.get_value(other_values, dataset_hash, user_hash, trans)

    def is_preparing(self, other_values):
        value = self._get_dataset_like_object(other_values)
        if value and value.state in (DatasetState.NEW, DatasetState.UPLOAD, DatasetState.QUEUED, DatasetState.RUNNING):
            return True
        return False

    def ready(self, other_values):
        if value := self._get_dataset_like_object(other_values):
            if value.state == DatasetState.OK:
                return True
            elif value.state == DatasetState.ERROR:
                raise Exception(f"A data display parameter is in the error state: {self.name}")
        return False


class DisplayApplicationTemplateParameter(DisplayApplicationParameter):
    """Parameter that returns a string containing the requested content"""

    type = "template"

    def __init__(self, elem, link):
        DisplayApplicationParameter.__init__(self, elem, link)
        self.text = elem.text or ""

    def get_value(self, other_values, dataset_hash, user_hash, trans):
        value = fill_template(self.text, context=other_values)
        if self.strip:
            value = value.strip()
        return DisplayParameterValueWrapper(value, self, other_values, dataset_hash, user_hash, trans)


parameter_type_to_class = {
    DisplayApplicationDataParameter.type: DisplayApplicationDataParameter,
    DisplayApplicationTemplateParameter.type: DisplayApplicationTemplateParameter,
}


class DisplayParameterValueWrapper:
    ACTION_NAME = "param"

    def __init__(self, value, parameter, other_values, dataset_hash, user_hash, trans):
        self.value = value
        self.parameter = parameter
        self.other_values = other_values
        self.trans = trans
        self._dataset_hash = dataset_hash
        self._user_hash = user_hash
        self._url = self.parameter.build_url(self.other_values)

    def __str__(self):
        return str(self.value)

    def mime_type(self, action_param_extra=None):
        if self.parameter.mime_type is not None:
            return self.parameter.mime_type
        if self.parameter.guess_mime_type:
            mime, encoding = mimetypes.guess_type(self._url)
            if not mime:
                mime = self.trans.app.datatypes_registry.get_mimetype_by_extension(self._url.split(".")[-1], None)
            if mime:
                return mime
        return "text/plain"

    @property
    def url(self):
        base_url = self.trans.request.base
        if self.parameter.strip_https and base_url[:5].lower() == "https":
            base_url = f"http{base_url[5:]}"
        return "{}{}".format(
            base_url,
            self.trans.app.url_for(
                controller="dataset",
                action="display_application",
                dataset_id=self._dataset_hash,
                user_id=self._user_hash,
                app_name=quote_plus(self.parameter.link.display_application.id),
                link_name=quote_plus(self.parameter.link.id),
                app_action=self.action_name,
                action_param=self._url,
            ),
        )

    @property
    def action_name(self):
        return self.ACTION_NAME

    @property
    def qp(self):
        # returns quoted str contents
        return self.other_values["qp"](str(self))

    def __getattr__(self, key):
        return getattr(self.value, key)


class DisplayDataValueWrapper(DisplayParameterValueWrapper):
    ACTION_NAME = "data"

    def __str__(self):
        # string of data param is filename
        return str(self.value.get_file_name())

    def mime_type(self, action_param_extra=None):
        if self.parameter.mime_type is not None:
            return self.parameter.mime_type
        if self.parameter.guess_mime_type:
            if action_param_extra:
                mime, encoding = mimetypes.guess_type(action_param_extra)
            else:
                mime, encoding = mimetypes.guess_type(self._url)
            if not mime:
                if action_param_extra:
                    mime = self.trans.app.datatypes_registry.get_mimetype_by_extension(
                        action_param_extra.split(".")[-1], None
                    )
                if not mime:
                    mime = self.trans.app.datatypes_registry.get_mimetype_by_extension(self._url.split(".")[-1], None)
            if mime:
                return mime
        if hasattr(self.value, "get_mime"):
            return self.value.get_mime()
        return self.other_values[DEFAULT_DATASET_NAME].get_mime()

    @property
    def action_name(self):
        if self.parameter.force_url_param:
            return super(DisplayParameterValueWrapper, self).action_name
        return self.ACTION_NAME

    @property
    def qp(self):
        # returns quoted url contents
        return self.other_values["qp"](self.url)
