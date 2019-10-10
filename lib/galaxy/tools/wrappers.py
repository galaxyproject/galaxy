import logging
import tempfile

from six import string_types, text_type
from six.moves import shlex_quote

from galaxy import exceptions
from galaxy.util import odict
from galaxy.util.none_like import NoneDataset
from galaxy.util.object_wrapper import wrap_with_safe_string

log = logging.getLogger(__name__)

# Fields in .log files corresponding to paths, must have one of the following
# field names and all such fields are assumed to be paths. This is to allow
# remote ComputeEnvironments (such as one used by Pulsar) determine what values to
# rewrite or transfer...
PATH_ATTRIBUTES = ["path"]


# ... by default though - don't rewrite anything (if no ComputeEnviornment
# defined or ComputeEnvironment doesn't supply a rewriter).
def DEFAULT_PATH_REWRITER(x):
    return x


class ToolParameterValueWrapper(object):
    """
    Base class for object that Wraps a Tool Parameter and Value.
    """

    def __bool__(self):
        return bool(self.value)
    __nonzero__ = __bool__

    def get_display_text(self, quote=True):
        """
        Returns a string containing the value that would be displayed to the user in the tool interface.
        When quote is True (default), the string is escaped for e.g. command-line usage.
        """
        rval = self.input.value_to_display_text(self.value) or ''
        if quote:
            return shlex_quote(rval)
        return rval


class RawObjectWrapper(ToolParameterValueWrapper):
    """
    Wraps an object so that __str__ returns module_name:class_name.
    """

    def __init__(self, obj):
        self.obj = obj

    def __bool__(self):
        return bool(self.obj)  # FIXME: would it be safe/backwards compatible to rename .obj to .value, so that we can just inherit this method?
    __nonzero__ = __bool__

    def __str__(self):
        try:
            return "%s:%s" % (self.obj.__module__, self.obj.__class__.__name__)
        except Exception:
            # Most likely None, which lacks __module__.
            return str(self.obj)

    def __getattr__(self, key):
        return getattr(self.obj, key)


class InputValueWrapper(ToolParameterValueWrapper):
    """
    Wraps an input so that __str__ gives the "param_dict" representation.
    """

    def __init__(self, input, value, other_values={}):
        self.input = input
        self.value = value
        self._other_values = other_values

    def __eq__(self, other):
        if isinstance(other, string_types):
            return str(self) == other
        elif isinstance(other, int):
            return int(self) == other
        elif isinstance(other, float):
            return float(self) == other
        else:
            return super(InputValueWrapper, self) == other

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        to_param_dict_string = self.input.to_param_dict_string(self.value, self._other_values)
        if isinstance(to_param_dict_string, list):
            return ','.join(to_param_dict_string)
        else:
            return to_param_dict_string

    def __iter__(self):
        to_param_dict_string = self.input.to_param_dict_string(self.value, self._other_values)
        if not isinstance(to_param_dict_string, list):
            return iter([to_param_dict_string])
        else:
            return iter(to_param_dict_string)

    def __getattr__(self, key):
        return getattr(self.value, key)

    def __int__(self):
        return int(str(self))

    def __float__(self):
        return float(str(self))


class SelectToolParameterWrapper(ToolParameterValueWrapper):
    """
    Wraps a SelectTooParameter so that __str__ returns the selected value, but all other
    attributes are accessible.
    """

    class SelectToolParameterFieldWrapper(object):
        """
        Provide access to any field by name or index for this particular value.
        Only applicable for dynamic_options selects, which have more than simple 'options' defined (name, value, selected).
        """

        def __init__(self, input, value, other_values, path_rewriter):
            self._input = input
            self._value = value
            self._other_values = other_values
            self._fields = {}
            self._path_rewriter = path_rewriter

        def __getattr__(self, name):
            if name not in self._fields:
                self._fields[name] = self._input.options.get_field_by_name_for_value(name, self._value, None, self._other_values)
            values = map(str, self._fields[name])
            if name in PATH_ATTRIBUTES:
                # If we infer this is a path, rewrite it if needed.
                values = map(self._path_rewriter, values)
            return self._input.separator.join(values)

    def __init__(self, input, value, other_values={}, path_rewriter=None):
        self.input = input
        self.value = value
        self.input.value_label = input.value_to_display_text(value)
        self._other_values = other_values
        self._path_rewriter = path_rewriter or DEFAULT_PATH_REWRITER
        self.fields = self.SelectToolParameterFieldWrapper(input, value, other_values, self._path_rewriter)

    def __eq__(self, other):
        if isinstance(other, string_types):
            return str(self) == other
        else:
            return super(SelectToolParameterWrapper, self) == other

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        # Assuming value is never a path - otherwise would need to pass
        # along following argument value_map=self._path_rewriter.
        return self.input.to_param_dict_string(self.value, other_values=self._other_values)

    def __add__(self, x):
        return '%s%s' % (self, x)

    def __getattr__(self, key):
        return getattr(self.input, key)

    def __iter__(self):
        if not self.input.multiple:
            raise Exception("Tried to iterate over a non-multiple parameter.")
        return self.value.__iter__()


class DatasetFilenameWrapper(ToolParameterValueWrapper):
    """
    Wraps a dataset so that __str__ returns the filename, but all other
    attributes are accessible.
    """

    class MetadataWrapper(object):
        """
        Wraps a Metadata Collection to return MetadataParameters wrapped
        according to the metadata spec. Methods implemented to match behavior
        of a Metadata Collection.
        """

        def __init__(self, metadata):
            self.metadata = metadata

        def __getattr__(self, name):
            rval = self.metadata.get(name, None)
            if name in self.metadata.spec:
                if rval is None:
                    rval = self.metadata.spec[name].no_value
                rval = self.metadata.spec[name].param.to_safe_string(rval)
                # Store this value, so we don't need to recalculate if needed
                # again
                setattr(self, name, rval)
            else:
                # escape string value of non-defined metadata value
                rval = wrap_with_safe_string(rval)
            return rval

        def __bool__(self):
            return self.metadata.__nonzero__()
        __nonzero__ = __bool__

        def __iter__(self):
            return self.metadata.__iter__()

        def get(self, key, default=None):
            try:
                return getattr(self, key)
            except Exception:
                return default

        def items(self):
            return iter((k, self.get(k)) for k, v in self.metadata.items())

    def __init__(self, dataset, datatypes_registry=None, tool=None, name=None, dataset_path=None, identifier=None):
        if not dataset:
            try:
                # TODO: allow this to work when working with grouping
                ext = tool.inputs[name].extensions[0]
            except Exception:
                ext = 'data'
            self.dataset = wrap_with_safe_string(NoneDataset(datatypes_registry=datatypes_registry, ext=ext), no_wrap_classes=ToolParameterValueWrapper)
        else:
            # Tool wrappers should not normally be accessing .dataset directly,
            # so we will wrap it and keep the original around for file paths
            # Should we name this .value to maintain consistency with most other ToolParameterValueWrapper?
            self.unsanitized = dataset
            self.dataset = wrap_with_safe_string(dataset, no_wrap_classes=ToolParameterValueWrapper)
            self.metadata = self.MetadataWrapper(dataset.metadata)
            if hasattr(dataset, 'tags'):
                self.groups = {tag.user_value.lower() for tag in dataset.tags if tag.user_tname == 'group'}
            else:
                # May be a 'FakeDatasetAssociation'
                self.groups = set()
        self.datatypes_registry = datatypes_registry
        self.false_path = getattr(dataset_path, "false_path", None)
        self.false_extra_files_path = getattr(dataset_path, "false_extra_files_path", None)
        self._element_identifier = identifier

    @property
    def element_identifier(self):
        identifier = self._element_identifier
        if identifier is None:
            identifier = self.name
        return identifier

    @property
    def is_collection(self):
        return False

    def is_of_type(self, *exts):
        datatypes = []
        for e in exts:
            datatype = self.datatypes_registry.get_datatype_by_extension(e)
            if datatype is not None:
                datatypes.append(datatype)
            else:
                log.warning("Datatype class not found for extension '%s', which is used as parameter of 'is_of_type()' method" % (e))
        return self.dataset.datatype.matches_any(datatypes)

    def __str__(self):
        if self.false_path is not None:
            return self.false_path
        else:
            return self.unsanitized.file_name

    def __getattr__(self, key):
        if self.false_path is not None and key == 'file_name':
            # Path to dataset was rewritten for this job.
            return self.false_path
        elif self.false_extra_files_path is not None and key == 'extra_files_path':
            # Path to extra files was rewritten for this job.
            return self.false_extra_files_path
        elif key == 'extra_files_path':
            try:
                # Assume it is an output and that this wrapper
                # will be set with correct "files_path" for this
                # job.
                return self.files_path
            except AttributeError:
                # Otherwise, we have an input - delegate to model and
                # object store to find the static location of this
                # directory.
                try:
                    return self.unsanitized.extra_files_path
                except exceptions.ObjectNotFound:
                    # NestedObjectstore raises an error here
                    # instead of just returning a non-existent
                    # path like DiskObjectStore.
                    raise
        else:
            return getattr(self.dataset, key)

    def __bool__(self):
        return bool(self.dataset)
    __nonzero__ = __bool__


class HasDatasets(object):

    def _dataset_wrapper(self, dataset, dataset_paths, **kwargs):
        wrapper_kwds = kwargs.copy()
        if dataset:
            real_path = dataset.file_name
            if real_path in dataset_paths:
                wrapper_kwds["dataset_path"] = dataset_paths[real_path]
        return DatasetFilenameWrapper(dataset, **wrapper_kwds)

    def paths_as_file(self, sep="\n"):
        contents = sep.join(map(str, self))
        with tempfile.NamedTemporaryFile(mode='w+', prefix="gx_file_list", dir=self.job_working_directory, delete=False) as fh:
            fh.write(contents)
            filepath = fh.name
        return filepath


class DatasetListWrapper(list, ToolParameterValueWrapper, HasDatasets):
    """
    """

    def __init__(self, job_working_directory, datasets, dataset_paths=[], **kwargs):
        self._dataset_elements_cache = {}
        if not isinstance(datasets, list):
            datasets = [datasets]

        def to_wrapper(dataset):
            if hasattr(dataset, "dataset_instance"):
                element = dataset
                dataset = element.dataset_instance
                kwargs["identifier"] = element.element_identifier
            return self._dataset_wrapper(dataset, dataset_paths, **kwargs)

        list.__init__(self, map(to_wrapper, datasets))
        self.job_working_directory = job_working_directory

    @staticmethod
    def to_dataset_instances(dataset_instance_sources):
        dataset_instances = []
        if not isinstance(dataset_instance_sources, list):
            dataset_instance_sources = [dataset_instance_sources]
        for dataset_instance_source in dataset_instance_sources:
            if dataset_instance_source is None:
                dataset_instances.append(dataset_instance_source)
            elif getattr(dataset_instance_source, "history_content_type", None) == "dataset":
                dataset_instances.append(dataset_instance_source)
            elif hasattr(dataset_instance_source, "child_collection"):
                dataset_instances.extend(dataset_instance_source.child_collection.dataset_elements)
            else:
                dataset_instances.extend(dataset_instance_source.collection.dataset_elements)
        return dataset_instances

    def get_datasets_for_group(self, group):
        group = text_type(group).lower()
        if not self._dataset_elements_cache.get(group):
            wrappers = []
            for element in self:
                if any([t for t in element.tags if t.user_tname.lower() == 'group' and t.value.lower() == group]):
                    wrappers.append(element)
            self._dataset_elements_cache[group] = wrappers
        return self._dataset_elements_cache[group]

    def __str__(self):
        return ','.join(map(str, self))

    def __bool__(self):
        # Fail `#if $param` checks in cheetah if optional input is not provided
        return any(self)
    __nonzero__ = __bool__


class DatasetCollectionWrapper(ToolParameterValueWrapper, HasDatasets):

    def __init__(self, job_working_directory, has_collection, dataset_paths=[], **kwargs):
        super(DatasetCollectionWrapper, self).__init__()
        self.job_working_directory = job_working_directory
        self._dataset_elements_cache = {}
        self.dataset_paths = dataset_paths
        self.kwargs = kwargs

        if has_collection is None:
            self.__input_supplied = False
            return
        else:
            self.__input_supplied = True

        if hasattr(has_collection, "name"):
            # It is a HistoryDatasetCollectionAssociation
            collection = has_collection.collection
            self.name = has_collection.name
        elif hasattr(has_collection, "child_collection"):
            # It is a DatasetCollectionElement instance referencing another collection
            collection = has_collection.child_collection
            self.name = has_collection.element_identifier
        else:
            collection = has_collection
            self.name = None
        self.collection = collection

        elements = collection.elements
        element_instances = odict.odict()

        element_instance_list = []
        for dataset_collection_element in elements:
            element_object = dataset_collection_element.element_object
            element_identifier = dataset_collection_element.element_identifier

            if dataset_collection_element.is_collection:
                element_wrapper = DatasetCollectionWrapper(job_working_directory, dataset_collection_element, dataset_paths, **kwargs)
            else:
                element_wrapper = self._dataset_wrapper(element_object, dataset_paths, identifier=element_identifier, **kwargs)

            element_instances[element_identifier] = element_wrapper
            element_instance_list.append(element_wrapper)

        self.__element_instances = element_instances
        self.__element_instance_list = element_instance_list

    def get_datasets_for_group(self, group):
        group = text_type(group).lower()
        if not self._dataset_elements_cache.get(group):
            wrappers = []
            for element in self.collection.dataset_elements:
                if any([t for t in element.dataset_instance.tags if t.user_tname.lower() == 'group' and t.value.lower() == group]):
                    wrappers.append(self._dataset_wrapper(element.element_object, self.dataset_paths, identifier=element.element_identifier, **self.kwargs))
            self._dataset_elements_cache[group] = wrappers
        return self._dataset_elements_cache[group]

    def keys(self):
        if not self.__input_supplied:
            return []
        return self.__element_instances.keys()

    @property
    def is_collection(self):
        return True

    @property
    def element_identifier(self):
        return self.name

    @property
    def is_input_supplied(self):
        return self.__input_supplied

    def __getitem__(self, key):
        if not self.__input_supplied:
            return None
        if isinstance(key, int):
            return self.__element_instance_list[key]
        else:
            return self.__element_instances[key]

    def __getattr__(self, key):
        if not self.__input_supplied:
            return None
        try:
            return self.__element_instances[key]
        except KeyError:
            raise AttributeError()

    def __iter__(self):
        if not self.__input_supplied:
            return [].__iter__()
        return self.__element_instance_list.__iter__()

    def __bool__(self):
        # Fail `#if $param` checks in cheetah is optional input
        # not specified or if resulting collection is empty.
        return self.__input_supplied and bool(self.__element_instance_list)
    __nonzero__ = __bool__


class ElementIdentifierMapper(object):
    """Track mapping of dataset collection elements datasets to element identifiers."""

    def __init__(self, input_datasets=None):
        if input_datasets is not None:
            self.identifier_key_dict = dict((v, "%s|__identifier__" % k) for k, v in input_datasets.items())
        else:
            self.identifier_key_dict = {}

    def identifier(self, dataset_value, input_values):
        identifier_key = self.identifier_key_dict.get(dataset_value, None)
        element_identifier = None
        if identifier_key:
            element_identifier = input_values.get(identifier_key, None)

        return element_identifier
