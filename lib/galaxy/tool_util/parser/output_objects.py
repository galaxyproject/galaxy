from typing import List

from galaxy.util.dictifiable import Dictifiable
from .output_actions import ToolOutputActionGroup
from .output_collection_def import dataset_collector_descriptions_from_output_dict, DatasetCollectionDescription


class ToolOutputBase(Dictifiable):

    def __init__(self, name, label=None, filters=None, hidden=False, from_expression=None):
        super().__init__()
        self.name = name
        self.label = label
        self.filters = filters or []
        self.hidden = hidden
        self.collection = False
        self.from_expression = from_expression

    def to_dict(self, view='collection', value_mapper=None, app=None):
        return super().to_dict(view=view, value_mapper=value_mapper)

    @property
    def output_discover_patterns(self) -> List[str]:
        return []


class ToolOutput(ToolOutputBase):
    """
    Represents an output datasets produced by a tool. For backward
    compatibility this behaves as if it were the tuple::

    (format, metadata_source, parent)
    """

    dict_collection_visible_keys = ['name', 'format', 'label', 'hidden', 'output_type', 'format_source',
                                    'default_identifier_source', 'metadata_source', 'parent', 'count', 'from_work_dir']

    def __init__(self, name, format=None, format_source=None, metadata_source=None,
                 parent=None, label=None, filters=None, actions=None, hidden=False,
                 implicit=False, from_expression=None):
        super().__init__(name, label=label, filters=filters, hidden=hidden, from_expression=from_expression)
        self.output_type = "data"
        self.format = format
        self.format_source = format_source
        self.metadata_source = metadata_source
        self.parent = parent
        self.actions = actions

        # Initialize default values
        self.change_format = []
        self.implicit = implicit
        self.from_work_dir = None
        self.dataset_collector_descriptions: List[DatasetCollectionDescription] = []

    # Tuple emulation

    def __len__(self):
        return 3

    def __getitem__(self, index):
        if index == 0:
            return self.format
        elif index == 1:
            return self.metadata_source
        elif index == 2:
            return self.parent
        else:
            raise IndexError(index)

    def __iter__(self):
        return iter((self.format, self.metadata_source, self.parent))

    def to_dict(self, view='collection', value_mapper=None, app=None):
        as_dict = super().to_dict(view=view, value_mapper=value_mapper, app=app)
        format = self.format
        if format and format != "input" and app:
            edam_format = app.datatypes_registry.edam_formats.get(self.format)
            as_dict["edam_format"] = edam_format
            edam_data = app.datatypes_registry.edam_data.get(self.format)
            as_dict["edam_data"] = edam_data
        as_dict['discover_datasets'] = list(map(lambda d: d.to_dict(), self.dataset_collector_descriptions))
        return as_dict

    @staticmethod
    def from_dict(name, output_dict, tool=None):
        output = ToolOutput(name)
        output.format = output_dict.get("format", "data")
        output.change_format = []
        output.format_source = output_dict.get("format_source", None)
        output.default_identifier_source = output_dict.get("default_identifier_source", None)
        output.metadata_source = output_dict.get("metadata_source", "")
        output.parent = output_dict.get("parent", None)
        output.label = output_dict.get("label", None)
        output.count = output_dict.get("count", 1)
        output.filters = []
        output.tool = tool
        output.from_work_dir = output_dict.get("from_work_dir", None)
        output.hidden = output_dict.get("hidden", "")
        # TODO: implement tool output action group fixes
        output.actions = ToolOutputActionGroup(output, None)
        output.dataset_collector_descriptions = dataset_collector_descriptions_from_output_dict(output_dict)
        return output

    @property
    def output_discover_patterns(self) -> List[str]:
        return _merge_dataset_collector_descriptions_patterns(self.dataset_collector_descriptions)


class ToolExpressionOutput(ToolOutputBase):
    dict_collection_visible_keys = ('name', 'format', 'label', 'hidden', 'output_type')

    def __init__(self, name, output_type, from_expression,
                 label=None, filters=None, actions=None, hidden=False):
        super().__init__(name, label=label, filters=filters, hidden=hidden)
        self.output_type = output_type  # JSON type...
        self.from_expression = from_expression
        self.format = "expression.json"  # galaxy.datatypes.text.ExpressionJson.file_ext

        self.format_source = None
        self.metadata_source = None
        self.parent = None
        self.actions = actions

        # Initialize default values
        self.change_format = []
        self.implicit = False
        self.from_work_dir = None


class ToolOutputCollection(ToolOutputBase):
    """
    Represents a HistoryDatasetCollectionAssociation of output datasets produced
    by a tool.

    .. code-block::

        <outputs>
        <collection type="list" label="${tool.name} on ${on_string} fasta">
            <discover_datasets pattern="__name__" ext="fasta" visible="True" directory="outputFiles" />
        </collection>
        <collection type="paired" label="${tool.name} on ${on_string} paired reads">
            <data name="forward" format="fastqsanger" />
            <data name="reverse" format="fastqsanger"/>
        </collection>
        <outputs>
    """
    dict_collection_visible_keys = ['name', 'format', 'label', 'hidden', 'output_type', 'default_format',
                                    'default_format_source', 'default_metadata_source', 'inherit_format', 'inherit_metadata']

    def __init__(
        self,
        name,
        structure,
        label=None,
        filters=None,
        hidden=False,
        default_format="data",
        default_format_source=None,
        default_metadata_source=None,
        inherit_format=False,
        inherit_metadata=False
    ):
        super().__init__(name, label=label, filters=filters, hidden=hidden)
        self.output_type = "collection"
        self.collection = True
        self.default_format = default_format
        self.structure = structure
        self.outputs = {}

        self.inherit_format = inherit_format
        self.inherit_metadata = inherit_metadata

        self.metadata_source = default_metadata_source
        self.format_source = default_format_source
        self.change_format = []  # TODO

    def known_outputs(self, inputs, type_registry):
        if self.dynamic_structure:
            return []

        # This line is probably not right - should verify structured_like
        # or have outputs and all outputs have name.
        if len(self.outputs) > 1:
            output_parts = [ToolOutputCollectionPart(self, k, v) for k, v in self.outputs.items()]
        else:
            collection_prototype = self.structure.collection_prototype(inputs, type_registry)

            def prototype_dataset_element_to_output(element, parent_ids=None):
                parent_ids = parent_ids or []
                name = element.element_identifier
                format = self.default_format
                if self.inherit_format:
                    format = element.dataset_instance.ext
                output = ToolOutput(
                    name,
                    format=format,
                    format_source=self.format_source,
                    metadata_source=self.metadata_source,
                    implicit=True,
                )
                if self.inherit_metadata:
                    output.metadata_source = element.dataset_instance
                return ToolOutputCollectionPart(
                    self,
                    element.element_identifier,
                    output,
                    parent_ids=parent_ids,
                )

            def prototype_collection_to_output(collection_prototype, parent_ids=None):
                parent_ids = parent_ids or []
                output_parts = []
                for element in collection_prototype.elements:
                    element_parts = []
                    if not element.is_collection:
                        element_parts.append(prototype_dataset_element_to_output(element, parent_ids))
                    else:
                        new_parent_ids = parent_ids[:] + [element.element_identifier]
                        element_parts.extend(prototype_collection_to_output(element.element_object, new_parent_ids))
                    output_parts.extend(element_parts)

                return output_parts

            output_parts = prototype_collection_to_output(collection_prototype)

        return output_parts

    @property
    def dynamic_structure(self):
        return self.structure.dynamic

    @property
    def dataset_collector_descriptions(self):
        if not self.dynamic_structure:
            raise Exception("dataset_collector_descriptions called for output collection with static structure")
        return self.structure.dataset_collector_descriptions

    def to_dict(self, view='collection', value_mapper=None, app=None):
        as_dict = super().to_dict(view=view, value_mapper=value_mapper, app=app)
        as_dict['structure'] = self.structure.to_dict()
        return as_dict

    @staticmethod
    def from_dict(name, output_dict, tool=None):
        structure = ToolOutputCollectionStructure.from_dict(output_dict["structure"])
        rval = ToolOutputCollection(
            name,
            structure=structure,
            label=output_dict.get("label", None),
            filters=None,
            hidden=output_dict.get("hidden", False),
            default_format=output_dict.get("default_format", "data"),
            default_format_source=output_dict.get("default_format_source", None),
            default_metadata_source=output_dict.get("default_metadata_source", None),
            inherit_format=output_dict.get("inherit_format", False),
            inherit_metadata=output_dict.get("inherit_metadata", False),
        )
        return rval

    @property
    def output_discover_patterns(self) -> List[str]:
        return self.structure.output_discover_patterns


class ToolOutputCollectionStructure:

    def __init__(
        self,
        collection_type,
        collection_type_source=None,
        collection_type_from_rules=None,
        structured_like=None,
        dataset_collector_descriptions=None,
    ):
        self.collection_type = collection_type
        self.collection_type_source = collection_type_source
        self.collection_type_from_rules = collection_type_from_rules
        self.structured_like = structured_like
        self.dataset_collector_descriptions = dataset_collector_descriptions or []
        if collection_type and collection_type_source:
            raise ValueError("Cannot set both type and type_source on collection output.")
        if collection_type is None and structured_like is None and dataset_collector_descriptions is None and collection_type_source is None and collection_type_from_rules is None:
            raise ValueError("Output collection types must specify source of collection type information (e.g. structured_like or type_source).")
        if dataset_collector_descriptions and (structured_like or collection_type_from_rules):
            raise ValueError("Cannot specify dynamic structure (discovered_datasets) and collection type attributes structured_like or collection_type_from_rules.")
        self.dynamic = bool(dataset_collector_descriptions)

    def collection_prototype(self, inputs, type_registry):
        # either must have specified structured_like or something worse
        if self.structured_like:
            collection_prototype = inputs[self.structured_like].collection
        else:
            collection_type = self.collection_type
            assert collection_type
            collection_prototype = type_registry.prototype(collection_type)
            collection_prototype.collection_type = collection_type
        return collection_prototype

    def to_dict(self):
        return {
            'collection_type': self.collection_type,
            'collection_type_source': self.collection_type_source,
            'collection_type_from_rules': self.collection_type_from_rules,
            'structured_like': self.structured_like,
            'discover_datasets': [d.to_dict() for d in self.dataset_collector_descriptions],
        }

    @staticmethod
    def from_dict(as_dict):
        structure = ToolOutputCollectionStructure(
            collection_type=as_dict['collection_type'],
            collection_type_source=as_dict['collection_type_source'],
            collection_type_from_rules=as_dict['collection_type_from_rules'],
            structured_like=as_dict['structured_like'],
            dataset_collector_descriptions=dataset_collector_descriptions_from_output_dict(as_dict),
        )
        return structure

    @property
    def output_discover_patterns(self) -> List[str]:
        if not self.dataset_collector_descriptions:
            return []
        else:
            return _merge_dataset_collector_descriptions_patterns(self.dataset_collector_descriptions)


def _merge_dataset_collector_descriptions_patterns(dataset_collector_descriptions: List[DatasetCollectionDescription]) -> List[str]:
    patterns = []
    for description in dataset_collector_descriptions:
        patterns.extend(description.discover_patterns)
    return patterns


class ToolOutputCollectionPart:

    def __init__(self, output_collection_def, element_identifier, output_def, parent_ids=None):
        parent_ids = parent_ids or []
        self.output_collection_def = output_collection_def
        self.element_identifier = element_identifier
        self.output_def = output_def
        self.parent_ids = parent_ids

    @property
    def effective_output_name(self):
        name = self.output_collection_def.name
        part_name = self.element_identifier
        effective_output_name = f"{name}|__part__|{part_name}"
        return effective_output_name

    @staticmethod
    def is_named_collection_part_name(name):
        return "|__part__|" in name

    @staticmethod
    def split_output_name(name):
        assert ToolOutputCollectionPart.is_named_collection_part_name(name)
        return name.split("|__part__|")
