"""
Galaxy Metadata
"""

import copy
import json
import logging
import os
import sys
import tempfile
import weakref
from collections import OrderedDict
from collections.abc import Mapping
from os.path import abspath
from typing import (
    Any,
    Iterator,
    Optional,
    TYPE_CHECKING,
    Union,
)

from sqlalchemy.orm import object_session
from sqlalchemy.orm.attributes import flag_modified

import galaxy.model
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.security.object_wrapper import sanitize_lists_to_string
from galaxy.util import (
    form_builder,
    listify,
    string_as_bool,
    stringify_dictionary_keys,
    unicodify,
)
from galaxy.util.json import safe_dumps

if TYPE_CHECKING:
    from galaxy.model import DatasetInstance
    from galaxy.model.none_like import NoneDataset
    from galaxy.model.store import SessionlessContext

log = logging.getLogger(__name__)

STATEMENTS = "__galaxy_statements__"  # this is the name of the property in a Datatype class where new metadata spec element Statements are stored


class Statement:
    """
    This class inserts its target into a list in the surrounding
    class.  the data.Data class has a metaclass which executes these
    statements.  This is how we shove the metadata element spec into
    the class.
    """

    def __init__(self, target):
        self.target = target

    def __call__(self, *args, **kwargs):
        # get the locals dictionary of the frame object one down in the call stack (i.e. the Datatype class calling MetadataElement)
        class_locals = sys._getframe(1).f_locals
        # get and set '__galaxy_statements__' to an empty list if not in locals dict
        statements = class_locals.setdefault(STATEMENTS, [])
        # add Statement containing info to populate a MetadataElementSpec
        statements.append((self, args, kwargs))

    @classmethod
    def process(cls, element):
        for statement, args, kwargs in getattr(element, STATEMENTS, []):
            statement.target(
                element, *args, **kwargs
            )  # statement.target is MetadataElementSpec, element is a Datatype class


class MetadataCollection(Mapping):
    """
    MetadataCollection is not a collection at all, but rather a proxy
    to the real metadata which is stored as a Dictionary. This class
    handles processing the metadata elements when they are set and
    retrieved, returning default values in cases when metadata is not set.
    """

    def __init__(
        self,
        parent: Union["DatasetInstance", "NoneDataset"],
        session: Optional[Union[galaxy_scoped_session, "SessionlessContext"]] = None,
    ) -> None:
        self.parent = parent
        self._session = session
        # initialize dict if needed
        if self.parent._metadata is None:
            self.parent._metadata = {}

    def get_parent(self):
        if "_parent" in self.__dict__:
            return self.__dict__["_parent"]()
        return None

    def set_parent(self, parent):
        # use weakref to prevent a circular reference interfering with garbage
        # collection: hda/lda (parent) <--> MetadataCollection (self) ; needs to be
        # hashable, so cannot use proxy.
        self.__dict__["_parent"] = weakref.ref(parent)

    parent = property(get_parent, set_parent)

    @property
    def spec(self):
        return self.parent.datatype.metadata_spec

    def _object_session(self, item):
        return self._session if self._session else object_session(item)

    def __iter__(self) -> Iterator[Any]:
        yield from self.spec.keys()

    def __getitem__(self, key):
        try:
            self.__getattribute__(key)
        except AttributeError:
            try:
                return self.__getattr__(key)
            except Exception:
                raise KeyError
        # `key` is an attribute of this instance, not some metadata: raise
        # KeyError to prevent e.g. `'items' in dataset.metadata` from returning
        # True
        # Not doing this would also break Cheetah's NameMapper._valueForName()
        # since dataset.metadata['items'] would be None
        raise KeyError

    def __len__(self):
        return len(self.spec)

    def __str__(self):
        return dict(self.items()).__str__()

    def __bool__(self):
        return bool(self.parent._metadata)

    __nonzero__ = __bool__

    def __getattr__(self, name):
        if name in self.spec:
            if name in self.parent._metadata:
                return self.spec[name].wrap(self.parent._metadata[name], self._object_session(self.parent))
            return self.spec[name].wrap(self.spec[name].default, self._object_session(self.parent))
        if name in self.parent._metadata:
            return self.parent._metadata[name]
        # Instead of raising an AttributeError for non-existing metadata, we return None
        return None

    def __setattr__(self, name, value):
        if name == "parent":
            return self.set_parent(value)
        elif name == "_session":
            super().__setattr__(name, value)
        else:
            if name in self.spec:
                self.parent._metadata[name] = self.spec[name].unwrap(value)
            else:
                self.parent._metadata[name] = value
            flag_modified(self.parent, "_metadata")

    def remove_key(self, name):
        if name in self.parent._metadata:
            del self.parent._metadata[name]
        else:
            log.info(f"Attempted to delete invalid key '{name}' from MetadataCollection")

    def element_is_set(self, name) -> bool:
        """
        check if the meta data with the given name is set, i.e.

        - if the such a metadata actually exists and
        - if its value differs from no_value

        :param name: the name of the metadata element
        :returns: True if the value differes from the no_value
                  False if its equal of if no metadata with the name is specified
        """
        meta_val = self[name]
        try:
            meta_spec = self.parent.metadata.spec[name]
        except KeyError:
            log.debug(f"No metadata element with name '{name}' found")
            return False
        return meta_val != meta_spec.no_value

    def get_metadata_parameter(self, name, **kwd):
        if name in self.spec:
            field = self.spec[name].param.get_field(getattr(self, name), self, None, **kwd)
            field.value = getattr(self, name)
            return field

    def make_dict_copy(self, to_copy):
        """Makes a deep copy of input iterable to_copy according to self.spec"""
        rval = {}
        for key, value in to_copy.items():
            if key in self.spec:
                rval[key] = self.spec[key].param.make_copy(value, target_context=self, source_context=to_copy)
        return rval

    @property
    def requires_dataset_id(self):
        for key in self.spec:
            if isinstance(self.spec[key].param, FileParameter):
                return True

        return False

    def from_JSON_dict(self, filename=None, path_rewriter=None, json_dict=None):
        dataset = self.parent
        if filename is not None:
            log.debug(f"loading metadata from file for: {dataset.__class__.__name__} {dataset.id}")
            with open(filename) as fh:
                JSONified_dict = json.load(fh)
        elif json_dict is not None:
            log.debug(f"loading metadata from dict for: {dataset.__class__.__name__} {dataset.id}")
            if isinstance(json_dict, str):
                JSONified_dict = json.loads(json_dict)
            elif isinstance(json_dict, dict):
                JSONified_dict = json_dict
            else:
                raise ValueError(f"json_dict must be either a dictionary or a string, got {type(json_dict)}.")
        else:
            raise ValueError("You must provide either a filename or a json_dict")

        # We build a dictionary for metadata name / value pairs
        # because when we copy MetadataTempFile objects we flush the datasets'
        # session, but only include the newly created MetadataFile object.
        # If we were to set the metadata elements in the first for loop we'd
        # lose all previously set metadata elements
        metadata_name_value = {}
        for name, spec in self.spec.items():
            if name in JSONified_dict:
                from_ext_kwds = {}
                external_value = JSONified_dict[name]
                param = spec.param
                if isinstance(param, FileParameter):
                    from_ext_kwds["path_rewriter"] = path_rewriter
                value = param.from_external_value(external_value, dataset, **from_ext_kwds)
                metadata_name_value[name] = value
            elif name in dataset._metadata:
                # if the metadata value is not found in our externally set metadata but it has a value in the 'old'
                # metadata associated with our dataset, we'll delete it from our dataset's metadata dict
                del dataset._metadata[name]
        for name, value in metadata_name_value.items():
            dataset._metadata[name] = value
        if "__extension__" in JSONified_dict:
            dataset.extension = JSONified_dict["__extension__"]
        if "__validated_state__" in JSONified_dict:
            dataset.validated_state = JSONified_dict["__validated_state__"]
        if "__validated_state_message__" in JSONified_dict:
            dataset.validated_state_message = JSONified_dict["__validated_state_message__"]
        flag_modified(dataset, "_metadata")

    def to_JSON_dict(self, filename=None):
        meta_dict = {}
        dataset_meta_dict = self.parent._metadata
        for name, spec in self.spec.items():
            if name in dataset_meta_dict:
                meta_dict[name] = spec.param.to_external_value(dataset_meta_dict[name])
        if "__extension__" in dataset_meta_dict:
            meta_dict["__extension__"] = dataset_meta_dict["__extension__"]
        if "__validated_state__" in dataset_meta_dict:
            meta_dict["__validated_state__"] = dataset_meta_dict["__validated_state__"]
        if "__validated_state_message__" in dataset_meta_dict:
            meta_dict["__validated_state_message__"] = dataset_meta_dict["__validated_state_message__"]
        try:
            encoded_meta_dict = galaxy.model.custom_types.json_encoder.encode(meta_dict)
        except Exception as e:
            raise Exception(f"Failed encoding metadata dictionary: {meta_dict}") from e
        if filename is None:
            return encoded_meta_dict
        with open(filename, "wt+") as fh:
            fh.write(encoded_meta_dict)

    def __getstate__(self):
        # cannot pickle a weakref item (self._parent), when
        # data._metadata_collection is None, it will be recreated on demand
        return None


class MetadataSpecCollection(OrderedDict):
    """
    A simple extension of OrderedDict which allows cleaner access to items
    and allows the values to be iterated over directly as if it were a
    list.  append() is also implemented for simplicity and does not
    "append".
    """

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)

    def append(self, item):
        self[item.name] = item

    def __getattr__(self, name):
        if name not in self:
            raise AttributeError
        return self.get(name)

    def __repr__(self):
        # force elements to draw with __str__ for sphinx-apidoc
        return ", ".join(item.__str__() for item in self.values())


class MetadataParameter:
    def __init__(self, spec):
        self.spec = spec

    def get_field(self, value=None, context=None, other_values=None, **kwd):
        context = context or {}
        other_values = other_values or {}
        return form_builder.TextField(self.spec.name, value=value)

    def to_string(self, value):
        return str(value)

    def to_safe_string(self, value):
        return sanitize_lists_to_string(self.to_string(value))

    def make_copy(self, value, target_context: MetadataCollection, source_context):
        return copy.deepcopy(value)

    @classmethod
    def marshal(cls, value):
        """
        This method should/can be overridden to convert the incoming
        value to whatever type it is supposed to be.
        """
        return value

    def validate(self, value):
        """
        Throw an exception if the value is invalid.
        """

    def unwrap(self, form_value):
        """
        Turns a value into its storable form.
        """
        value = self.marshal(form_value)
        self.validate(value)
        return value

    def wrap(self, value, session):
        """
        Turns a value into its usable form.
        """
        return value

    def from_external_value(self, value, parent):
        """
        Turns a value read from an external dict into its value to be pushed directly into the metadata dict.
        """
        return value

    def to_external_value(self, value):
        """
        Turns a value read from a metadata into its value to be pushed directly into the external dict.
        """
        return value


class MetadataElementSpec:
    """
    Defines a metadata element and adds it to the metadata_spec (which
    is a MetadataSpecCollection) of datatype.
    """

    def __init__(
        self,
        datatype,
        name=None,
        desc=None,
        param=MetadataParameter,
        default=None,
        no_value=None,
        visible=True,
        set_in_upload=False,
        **kwargs,
    ):
        self.name = name
        self.desc = desc or name
        self.default = default
        self.no_value = no_value
        self.visible = visible
        self.set_in_upload = set_in_upload
        # Catch-all, allows for extra attributes to be set
        self.__dict__.update(kwargs)
        # set up param last, as it uses values set above
        self.param = param(self)
        # add spec element to the spec
        datatype.metadata_spec.append(self)
        # Should we validate that non-optional elements have been set ?
        # (The answer is yes, but not all datatypes control optionality appropriately at this point.)
        # This allows us to check that inherited MetadataElement instances from datatypes that set
        # check_required_metadata have been reviewed and considered really required.
        self.check_required_metadata = datatype.__dict__.get("check_required_metadata", False)

    def get(self, name, default=None):
        return self.__dict__.get(name, default)

    def wrap(self, value, session):
        """
        Turns a stored value into its usable form.
        """
        return self.param.wrap(value, session)

    def unwrap(self, value):
        """
        Turns an incoming value into its storable form.
        """
        return self.param.unwrap(value)

    def __str__(self):
        # TODO??: assuming param is the class of this MetadataElementSpec - add the plain class name for that
        spec_dict = dict(param_class=self.param.__class__.__name__)
        spec_dict.update(self.__dict__)
        return "{name} ({param_class}): {desc}, defaults to '{default}'".format(**spec_dict)


# create a statement class that, when called,
#   will add a new MetadataElementSpec to a class's metadata_spec
MetadataElement = Statement(MetadataElementSpec)


"""
MetadataParameter sub-classes.
"""


class SelectParameter(MetadataParameter):
    def __init__(self, spec):
        MetadataParameter.__init__(self, spec)
        self.values = self.spec.get("values")
        self.multiple = string_as_bool(self.spec.get("multiple"))

    def to_string(self, value):
        if value in [None, []]:
            return str(self.spec.no_value)
        if not isinstance(value, list):
            value = [value]
        return ",".join(map(str, value))

    def get_field(self, value=None, context=None, other_values=None, values=None, **kwd):
        context = context or {}
        other_values = other_values or {}

        field = form_builder.SelectField(self.spec.name, multiple=self.multiple, display=self.spec.get("display"))
        if self.values:
            value_list = self.values
        elif values:
            value_list = values
        elif value:
            value_list = [(v, v) for v in listify(value)]
        else:
            value_list = []
        for val, label in value_list:
            try:
                if (self.multiple and val in value) or (not self.multiple and val == value):
                    field.add_option(label, val, selected=True)
                else:
                    field.add_option(label, val, selected=False)
            except TypeError:
                field.add_option(val, label, selected=False)
        return field

    def wrap(self, value, session):
        # do we really need this (wasteful)? - yes because we are not sure that
        # all existing selects have been stored previously as lists. Also this
        # will handle the case where defaults/no_values are specified and are
        # single non-list values.
        value = self.marshal(value)
        if self.multiple:
            return value
        elif value:
            return value[0]  # single select, only return the first value
        return None

    @classmethod
    def marshal(cls, value):
        # Store select as list, even if single item
        if value is None:
            return []
        if not isinstance(value, list):
            return [value]
        return value


class DBKeyParameter(SelectParameter):
    def get_field(self, value=None, context=None, other_values=None, values=None, **kwd):
        context = context or {}
        other_values = other_values or {}
        try:
            values = kwd["trans"].app.genome_builds.get_genome_build_names(kwd["trans"])
        except KeyError:
            pass
        return super().get_field(value, context, other_values, values, **kwd)

    def make_copy(self, value, target_context: MetadataCollection, source_context):
        value = listify(value)
        return super().make_copy(value, target_context, source_context)


class RangeParameter(SelectParameter):
    def __init__(self, spec):
        SelectParameter.__init__(self, spec)
        # The spec must be set with min and max values
        self.min = spec.get("min") or 1
        self.max = spec.get("max") or 1
        self.step = self.spec.get("step") or 1

    def get_field(self, value=None, context=None, other_values=None, values=None, **kwd):
        context = context or {}
        other_values = other_values or {}

        if values is None:
            values = list(zip(range(self.min, self.max, self.step), range(self.min, self.max, self.step)))
        return SelectParameter.get_field(
            self, value=value, context=context, other_values=other_values, values=values, **kwd
        )

    @classmethod
    def marshal(cls, value):
        value = SelectParameter.marshal(value)
        values = [int(x) for x in value]
        return values


class ColumnParameter(RangeParameter):
    def get_field(self, value=None, context=None, other_values=None, values=None, **kwd):
        context = context or {}
        other_values = other_values or {}

        if values is None and context:
            column_range = range(1, (context.columns or 0) + 1, 1)
            values = list(zip(column_range, column_range))
        return RangeParameter.get_field(
            self, value=value, context=context, other_values=other_values, values=values, **kwd
        )


class ColumnTypesParameter(MetadataParameter):
    def to_string(self, value):
        return ",".join(map(str, value))


class ListParameter(MetadataParameter):
    def to_string(self, value):
        return ",".join(str(x) for x in value)


class DictParameter(MetadataParameter):
    def to_string(self, value):
        return json.dumps(value)

    def to_safe_string(self, value):
        # We do not sanitize json dicts
        return safe_dumps(value)


class PythonObjectParameter(MetadataParameter):
    def to_string(self, value):
        if not value:
            return self.spec._to_string(self.spec.no_value)
        return self.spec._to_string(value)

    def get_field(self, value=None, context=None, other_values=None, **kwd):
        context = context or {}
        other_values = other_values or {}
        return form_builder.TextField(self.spec.name, value=self._to_string(value))

    @classmethod
    def marshal(cls, value):
        return value


class FileParameter(MetadataParameter):
    def to_string(self, value):
        if not value:
            return str(self.spec.no_value)
        return value.file_name

    def to_safe_string(self, value):
        # We do not sanitize file names
        return self.to_string(value)

    def get_field(self, value=None, context=None, other_values=None, **kwd):
        context = context or {}
        other_values = other_values or {}
        return form_builder.TextField(self.spec.name, value=str(value.id))

    def wrap(self, value, session):
        if value is None:
            return None
        if isinstance(value, galaxy.model.MetadataFile) or isinstance(value, MetadataTempFile):
            return value
        if isinstance(value, int):
            return session.query(galaxy.model.MetadataFile).get(value)
        else:
            return session.query(galaxy.model.MetadataFile).filter_by(uuid=value).one()

    def make_copy(self, value, target_context: MetadataCollection, source_context):
        session = target_context._object_session(target_context.parent)
        value = self.wrap(value, session=session)
        target_dataset = target_context.parent.dataset
        if value and not value.id:
            # This is a new MetadataFile object, we're not copying to another dataset.
            # Just use it.
            return self.unwrap(value)
        if value and target_dataset.object_store.exists(target_dataset):
            # Only copy MetadataFile if the target dataset has been created in an object store.
            # All current datatypes re-generate MetadataFile objects when setting metadata,
            # so this would ultimately get overwritten anyway.
            new_value = galaxy.model.MetadataFile(dataset=target_context.parent, name=self.spec.name)
            session.add(new_value)
            try:
                new_value.update_from_file(value.file_name)
            except AssertionError:
                session(target_context.parent).flush()
                new_value.update_from_file(value.file_name)
            return self.unwrap(new_value)
        return None

    @classmethod
    def marshal(cls, value):
        if isinstance(value, galaxy.model.MetadataFile):
            # We want to push value.id to the database, but need to skip this when no session is available,
            # as in extended_metadata mode, so there we just accept MetadataFile.
            # We will only serialize MetadataFile in this mode and not push to the database, so this is OK.
            value = value.id or value
            if not isinstance(value, int) and object_session(value):
                value = str(value.uuid)
        return value

    def from_external_value(self, value, parent, path_rewriter=None):
        """
        Turns a value read from a external dict into its value to be pushed directly into the metadata dict.
        """
        if MetadataTempFile.is_JSONified_value(value):
            value = MetadataTempFile.from_JSON(value)
        if isinstance(value, MetadataTempFile):
            mf = parent.metadata.get(self.spec.name, None)
            if mf is None:
                mf = self.new_file(dataset=parent, **value.kwds)
            # Ensure the metadata file gets updated with content
            file_name = value.file_name
            if path_rewriter:
                # Job may have run with a different (non-local) tmp/working
                # directory. Correct.
                file_name = path_rewriter(file_name)
            mf.update_from_file(file_name)
            os.unlink(file_name)
            value = mf.id
        return value

    def to_external_value(self, value):
        """
        Turns a value read from a metadata into its value to be pushed directly into the external dict.
        """
        if isinstance(value, galaxy.model.MetadataFile):
            value = value.id
        elif isinstance(value, MetadataTempFile):
            value = MetadataTempFile.to_JSON(value)
        return value

    def new_file(self, dataset=None, **kwds):
        # If there is a place to store the file (i.e. an object_store has been bound to
        # Dataset) then use a MetadataFile and assume it is accessible. Otherwise use
        # a MetadataTempFile.
        if getattr(dataset.dataset, "object_store", False):
            mf = galaxy.model.MetadataFile(name=self.spec.name, dataset=dataset, **kwds)
            sa_session = object_session(dataset)
            if sa_session:
                sa_session.add(mf)
                sa_session.flush()  # flush to assign id
            return mf
        else:
            # we need to make a tmp file that is accessable to the head node,
            # we will be copying its contents into the MetadataFile objects filename after restoring from JSON
            # we do not include 'dataset' in the kwds passed, as from_JSON_value() will handle this for us
            return MetadataTempFile(**kwds)


# This class is used when a database file connection is not available
class MetadataTempFile:
    tmp_dir = "database/tmp"  # this should be overwritten as necessary in calling scripts

    def __init__(self, **kwds):
        self.kwds = kwds
        self._filename = None

    @property
    def file_name(self):
        if self._filename is None:
            # we need to create a tmp file, accessable across all nodes/heads, save the name, and return it
            self._filename = abspath(tempfile.NamedTemporaryFile(dir=self.tmp_dir, prefix="metadata_temp_file_").name)
            open(self._filename, "wb+")  # create an empty file, so it can't be reused using tempfile
        return self._filename

    def to_JSON(self):
        return {"__class__": self.__class__.__name__, "filename": self.file_name, "kwds": self.kwds}

    @classmethod
    def from_JSON(cls, json_dict):
        # need to ensure our keywords are not unicode
        rval = cls(**stringify_dictionary_keys(json_dict["kwds"]))
        rval._filename = json_dict["filename"]
        return rval

    @classmethod
    def is_JSONified_value(cls, value):
        return isinstance(value, dict) and value.get("__class__", None) == cls.__name__

    @classmethod
    def cleanup_from_JSON_dict_filename(cls, filename):
        try:
            with open(filename) as fh:
                for value in json.load(fh).values():
                    if cls.is_JSONified_value(value):
                        value = cls.from_JSON(value)
                    if isinstance(value, cls) and os.path.exists(value.file_name):
                        log.debug("Cleaning up abandoned MetadataTempFile file: %s", value.file_name)
                        os.unlink(value.file_name)
        except Exception as e:
            log.debug("Failed to cleanup MetadataTempFile temp files from %s: %s", filename, unicodify(e))


__all__ = (
    "Statement",
    "MetadataElement",
    "MetadataCollection",
    "MetadataSpecCollection",
    "MetadataParameter",
    "MetadataElementSpec",
    "SelectParameter",
    "DBKeyParameter",
    "RangeParameter",
    "ColumnParameter",
    "ColumnTypesParameter",
    "ListParameter",
    "DictParameter",
    "PythonObjectParameter",
    "FileParameter",
    "MetadataTempFile",
)
