from galaxy import model
from galaxy.util.odict import odict


def build_collection(type, dataset_instances):
    """
    Build DatasetCollection with populated DatasetcollectionElement objects
    corresponding to the supplied dataset instances or throw exception if
    this is not a valid collection of the specified type.
    """
    dataset_collection = model.DatasetCollection()
    set_collection_elements(dataset_collection, type, dataset_instances)
    return dataset_collection


def set_collection_elements(dataset_collection, type, dataset_instances):
    element_index = 0
    elements = []
    for element in type.generate_elements(dataset_instances):
        element.element_index = element_index
        element.collection = dataset_collection
        elements.append(element)

        element_index += 1

    dataset_collection.elements = elements
    dataset_collection.element_count = element_index
    return dataset_collection


class CollectionBuilder(object):
    """ Purely functional builder pattern for building a dataset collection. """

    def __init__(self, collection_type_description):
        self._collection_type_description = collection_type_description
        self._current_elements = odict()

    def get_level(self, identifier):
        if not self._nested_collection:
            message_template = "Cannot add nested collection to collection of type [%s]"
            message = message_template % (self._collection_type_description)
            raise AssertionError(message)
        if identifier not in self._current_elements:
            subcollection_builder = CollectionBuilder(
                self._subcollection_type_description
            )
            self._current_elements[identifier] = subcollection_builder

        return self._current_elements[identifier]

    def add_dataset(self, identifier, dataset_instance):
        self._current_elements[identifier] = dataset_instance

    def build_elements(self):
        elements = self._current_elements
        if self._nested_collection:
            new_elements = odict()
            for identifier, element in elements.items():
                new_elements[identifier] = element.build()
            elements = new_elements
        return elements

    def build(self):
        type_plugin = self._collection_type_description.rank_type_plugin()
        collection = build_collection(type_plugin, self.build_elements())
        collection.collection_type = self._collection_type_description.collection_type
        return collection

    @property
    def _subcollection_type_description(self):
        return self._collection_type_description.subcollection_type_description()

    @property
    def _nested_collection(self):
        return self._collection_type_description.has_subcollections()


class BoundCollectionBuilder(CollectionBuilder):
    """ More stateful builder that is bound to a particular model object. """

    def __init__(self, dataset_collection, collection_type_description):
        self.dataset_collection = dataset_collection
        if dataset_collection.populated:
            raise Exception("Cannot reset elements of an already populated dataset collection.")
        super(BoundCollectionBuilder, self).__init__(collection_type_description)

    def populate(self):
        elements = self.build_elements()
        type_plugin = self._collection_type_description.rank_type_plugin()
        set_collection_elements(self.dataset_collection, type_plugin, elements)
        self.dataset_collection.mark_as_populated()
