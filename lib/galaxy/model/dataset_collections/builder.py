from typing import (
    cast,
    Dict,
    List,
    Optional,
    Set,
    TYPE_CHECKING,
    Union,
)

from galaxy.model import (
    DatasetCollection,
    DatasetInstance,
)
from galaxy.model.orm.util import add_object_to_object_session
from galaxy.util.oset import OrderedSet
from .type_description import COLLECTION_TYPE_DESCRIPTION_FACTORY

if TYPE_CHECKING:
    from galaxy.model.dataset_collections.adapters import CollectionAdapter
    from galaxy.model.dataset_collections.type_description import CollectionTypeDescription
    from galaxy.model.dataset_collections.types import (
        BaseDatasetCollectionType,
        DatasetInstanceMapping,
    )
    from galaxy.tool_util_models.tool_source import FieldDict


def build_collection(
    type: "BaseDatasetCollectionType",
    dataset_instances: "DatasetInstanceMapping",
    collection: Optional[DatasetCollection] = None,
    associated_identifiers: Optional[Set[str]] = None,
    fields: Optional[Union[str, List["FieldDict"]]] = None,
) -> DatasetCollection:
    """
    Build DatasetCollection with populated DatasetcollectionElement objects
    corresponding to the supplied dataset instances or throw exception if
    this is not a valid collection of the specified type.
    """
    dataset_collection = collection or DatasetCollection(fields=fields)
    associated_identifiers = associated_identifiers or set()
    set_collection_elements(dataset_collection, type, dataset_instances, associated_identifiers, fields=fields)
    return dataset_collection


def set_collection_elements(
    dataset_collection: DatasetCollection,
    type: "BaseDatasetCollectionType",
    dataset_instances: "DatasetInstanceMapping",
    associated_identifiers: Set[str],
    fields: Optional[Union[str, List["FieldDict"]]] = None,
) -> DatasetCollection:
    new_element_keys = OrderedSet(dataset_instances.keys()) - associated_identifiers
    new_dataset_instances = {k: dataset_instances[k] for k in new_element_keys}
    dataset_collection.element_count = dataset_collection.element_count or 0
    element_index = dataset_collection.element_count
    elements = []
    if type.collection_type == "record" and fields == "auto":
        fields = guess_fields(dataset_instances)
    for element in type.generate_elements(new_dataset_instances, fields=fields):
        element.element_index = element_index
        add_object_to_object_session(element, dataset_collection)
        element.collection = dataset_collection
        elements.append(element)

        element_index += 1
        assert element.element_identifier
        associated_identifiers.add(element.element_identifier)

    dataset_collection.element_count = element_index
    return dataset_collection


def guess_fields(dataset_instances: "DatasetInstanceMapping") -> List["FieldDict"]:
    fields: List[FieldDict] = []
    for identifier, element in dataset_instances.items():
        if isinstance(element, DatasetCollection):
            return []
        else:
            fields.append({"type": "File", "name": identifier})

    return fields


ElementsDict = Dict[str, Union["CollectionBuilder", DatasetInstance]]


class CollectionBuilder:
    """Purely functional builder pattern for building a dataset collection."""

    def __init__(self, collection_type_description: "CollectionTypeDescription"):
        self._collection_type_description = collection_type_description
        self._current_elements: ElementsDict = {}
        # Store collection here so we don't recreate the collection all the time
        self.collection: Optional[DatasetCollection] = None
        self.associated_identifiers: Set[str] = set()

    def replace_elements_in_collection(
        self,
        template_collection: Union["CollectionAdapter", DatasetCollection],
        replacement_dict: Dict[DatasetInstance, DatasetInstance],
    ) -> None:
        self._current_elements = self._replace_elements_in_collection(
            template_collection=template_collection,
            replacement_dict=replacement_dict,
        )

    def _replace_elements_in_collection(
        self,
        template_collection: Union["CollectionAdapter", DatasetCollection],
        replacement_dict: Dict[DatasetInstance, DatasetInstance],
    ) -> ElementsDict:
        elements: ElementsDict = {}
        for element in template_collection.elements:
            assert element.element_identifier
            if element.child_collection:
                collection_builder = CollectionBuilder(
                    collection_type_description=self._collection_type_description.child_collection_type_description()
                )
                collection_builder.replace_elements_in_collection(
                    template_collection=element.child_collection, replacement_dict=replacement_dict
                )
                elements[element.element_identifier] = collection_builder
            else:
                assert isinstance(element.element_object, DatasetInstance)
                elements[element.element_identifier] = replacement_dict.get(
                    element.element_object, element.element_object
                )
        return elements

    def get_level(self, identifier: str) -> "CollectionBuilder":
        if not self._nested_collection:
            message_template = "Cannot add nested collection to collection of type [%s]"
            message = message_template % (self._collection_type_description)
            raise AssertionError(message)
        if identifier in self._current_elements:
            subcollection_builder = self._current_elements[identifier]
            assert isinstance(subcollection_builder, CollectionBuilder)
        else:
            subcollection_builder = CollectionBuilder(self._subcollection_type_description)
            self._current_elements[identifier] = subcollection_builder
        return subcollection_builder

    def add_dataset(self, identifier: str, dataset_instance: DatasetInstance) -> None:
        self._current_elements[identifier] = dataset_instance

    def build_elements(self) -> "DatasetInstanceMapping":
        elements = self._current_elements
        if self._nested_collection:
            new_elements = {}
            for identifier, element in elements.items():
                assert isinstance(element, CollectionBuilder)
                new_elements[identifier] = element.build()
            return new_elements
        else:
            self._current_elements = {}
            return cast(Dict[str, DatasetInstance], elements)

    def build(self) -> DatasetCollection:
        type_plugin = self._collection_type_description.rank_type_plugin()
        self.collection = build_collection(
            type_plugin, self.build_elements(), self.collection, self.associated_identifiers
        )
        self.collection.collection_type = self._collection_type_description.collection_type
        return self.collection

    @property
    def _subcollection_type_description(self) -> "CollectionTypeDescription":
        return self._collection_type_description.subcollection_type_description()

    @property
    def _nested_collection(self) -> bool:
        return self._collection_type_description.has_subcollections()


class BoundCollectionBuilder(CollectionBuilder):
    """More stateful builder that is bound to a particular model object."""

    def __init__(self, dataset_collection):
        self.dataset_collection = dataset_collection
        if dataset_collection.populated:
            raise Exception("Cannot reset elements of an already populated dataset collection.")
        collection_type = dataset_collection.collection_type
        collection_type_description = COLLECTION_TYPE_DESCRIPTION_FACTORY.for_collection_type(collection_type)
        super().__init__(collection_type_description)

    def populate_partial(self):
        elements = self.build_elements()
        type_plugin = self._collection_type_description.rank_type_plugin()
        set_collection_elements(self.dataset_collection, type_plugin, elements, self.associated_identifiers)

    def populate(self):
        self.populate_partial()
        self.dataset_collection.mark_as_populated()
