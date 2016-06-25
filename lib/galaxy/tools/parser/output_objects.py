from galaxy.util.dictifiable import Dictifiable
from galaxy.util.odict import odict


class ToolOutputBase( Dictifiable, object ):

    def __init__( self, name, label=None, filters=None, hidden=False ):
        super( ToolOutputBase, self ).__init__()
        self.name = name
        self.label = label
        self.filters = filters or []
        self.hidden = hidden
        self.collection = False


class ToolOutput( ToolOutputBase ):
    """
    Represents an output datasets produced by a tool. For backward
    compatibility this behaves as if it were the tuple::

      (format, metadata_source, parent)
    """

    dict_collection_visible_keys = ( 'name', 'format', 'label', 'hidden' )

    def __init__( self, name, format=None, format_source=None, metadata_source=None,
                  parent=None, label=None, filters=None, actions=None, hidden=False,
                  implicit=False ):
        super( ToolOutput, self ).__init__( name, label=label, filters=filters, hidden=hidden )
        self.format = format
        self.format_source = format_source
        self.metadata_source = metadata_source
        self.parent = parent
        self.actions = actions

        # Initialize default values
        self.change_format = []
        self.implicit = implicit
        self.from_work_dir = None

    # Tuple emulation

    def __len__( self ):
        return 3

    def __getitem__( self, index ):
        if index == 0:
            return self.format
        elif index == 1:
            return self.metadata_source
        elif index == 2:
            return self.parent
        else:
            raise IndexError( index )

    def __iter__( self ):
        return iter( ( self.format, self.metadata_source, self.parent ) )

    def to_dict( self, view='collection', value_mapper=None, app=None ):
        as_dict = super( ToolOutput, self ).to_dict( view=view, value_mapper=value_mapper )
        format = self.format
        if format and format != "input" and app:
            edam_format = app.datatypes_registry.edam_formats.get(self.format)
            as_dict["edam_format"] = edam_format
            edam_data = app.datatypes_registry.edam_data.get(self.format)
            as_dict["edam_data"] = edam_data
        return as_dict


class ToolOutputCollection( ToolOutputBase ):
    """
    Represents a HistoryDatasetCollectionAssociation of output datasets produced
    by a tool.

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
        super( ToolOutputCollection, self ).__init__( name, label=label, filters=filters, hidden=hidden )
        self.collection = True
        self.default_format = default_format
        self.structure = structure
        self.outputs = odict()

        self.inherit_format = inherit_format
        self.inherit_metadata = inherit_metadata

        self.metadata_source = default_metadata_source
        self.format_source = default_format_source
        self.change_format = []  # TODO

    def known_outputs( self, inputs, type_registry ):
        if self.dynamic_structure:
            return []

        # This line is probably not right - should verify structured_like
        # or have outputs and all outputs have name.
        if len( self.outputs ) > 1:
            output_parts = [ToolOutputCollectionPart(self, k, v) for k, v in self.outputs.items()]
        else:
            # either must have specified structured_like or something worse
            if self.structure.structured_like:
                collection_prototype = inputs[ self.structure.structured_like ].collection
            else:
                collection_prototype = type_registry.prototype( self.structure.collection_type )

            def prototype_dataset_element_to_output( element, parent_ids=[] ):
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

            def prototype_collection_to_output( collection_prototype, parent_ids=[] ):
                output_parts = []
                for element in collection_prototype.elements:
                    element_parts = []
                    if not element.is_collection:
                        element_parts.append(prototype_dataset_element_to_output( element, parent_ids ))
                    else:
                        new_parent_ids = parent_ids[:] + [element.element_identifier]
                        element_parts.extend(prototype_collection_to_output(element.element_object, new_parent_ids))
                    output_parts.extend(element_parts)

                return output_parts

            output_parts = prototype_collection_to_output( collection_prototype )

        return output_parts

    @property
    def dynamic_structure(self):
        return self.structure.dynamic

    @property
    def dataset_collector_descriptions(self):
        if not self.dynamic_structure:
            raise Exception("dataset_collector_descriptions called for output collection with static structure")
        return self.structure.dataset_collector_descriptions


class ToolOutputCollectionStructure( object ):

    def __init__(
        self,
        collection_type,
        collection_type_source,
        structured_like,
        dataset_collector_descriptions,
    ):
        self.collection_type = collection_type
        self.collection_type_source = collection_type_source
        self.structured_like = structured_like
        self.dataset_collector_descriptions = dataset_collector_descriptions
        if collection_type and collection_type_source:
            raise ValueError("Cannot set both type and type_source on collection output.")
        if collection_type is None and structured_like is None and dataset_collector_descriptions is None and collection_type_source is None:
            raise ValueError( "Output collection types must be specify type of structured_like" )
        if dataset_collector_descriptions and structured_like:
            raise ValueError( "Cannot specify dynamic structure (discovered_datasets) and structured_like attribute." )
        self.dynamic = dataset_collector_descriptions is not None


class ToolOutputCollectionPart( object ):

    def __init__( self, output_collection_def, element_identifier, output_def, parent_ids=[] ):
        self.output_collection_def = output_collection_def
        self.element_identifier = element_identifier
        self.output_def = output_def
        self.parent_ids = parent_ids

    @property
    def effective_output_name( self ):
        name = self.output_collection_def.name
        part_name = self.element_identifier
        effective_output_name = "%s|__part__|%s" % ( name, part_name )
        return effective_output_name

    @staticmethod
    def is_named_collection_part_name( name ):
        return "|__part__|" in name

    @staticmethod
    def split_output_name( name ):
        assert ToolOutputCollectionPart.is_named_collection_part_name( name )
        return name.split("|__part__|")
