from typing import (
    List,
    TYPE_CHECKING,
)

from pydantic import ValidationError
from typing_extensions import Self

from galaxy.tool_util_models.parameters import (
    AdaptedDataCollectionPromoteCollectionElementToCollectionRequestInternal,
    AdaptedDataCollectionPromoteDatasetsToCollectionRequestInternal,
    AdaptedDataCollectionPromoteDatasetToCollectionRequestInternal,
    AdaptedDataCollectionRequestInternalTypeAdapter,
    AdaptedDataCollectionRequestTypeAdapter,
    AdapterElementRequestInternal,
    DataRequestInternalHda,
    DatasetCollectionElementReference,
)

if TYPE_CHECKING:
    from galaxy.model import (
        DatasetCollectionElement,
        HistoryDatasetAssociation,
    )


class CollectionAdapter:
    # wrap model objects with extra context to create psuedo or ephemeral
    # collections for tool processing code. Used across tool actions and
    # tool evaluation.

    @property
    def dataset_action_tuples(self):
        raise NotImplementedError()

    @property
    def dataset_states_and_extensions_summary(self):
        raise NotImplementedError()

    @property
    def dataset_instances(self):
        raise NotImplementedError()

    @property
    def elements(self):
        raise NotImplementedError()

    def to_adapter_model(self):
        # json kwds to recover state from database after the job has been
        # recorded
        raise NotImplementedError()

    @property
    def adapting(self):
        # return the the thing we're adapting for recording an actual link
        # in the database
        raise NotImplementedError()

    @property
    def collection(self) -> Self:
        # this object serves an adapter to the collection instance and to the collection,
        # may want to break this out someday. For now though just return self when asking for
        # the collection object.
        return self

    @property
    def collection_type(self) -> str:
        raise NotImplementedError()


class DCECollectionAdapter(CollectionAdapter):
    # adapt a DatasetCollectionElement to act as collection.
    _dce: "DatasetCollectionElement"

    def __init__(self, dataset_collection_element: "DatasetCollectionElement"):
        self._dce = dataset_collection_element

    @property
    def dataset_action_tuples(self):
        if self._dce.child_collection:
            return self._dce.child_collection.dataset_action_tuples
        else:
            hda = self._dce.dataset_instance
            return [(permission.action, permission.role_id) for permission in hda.dataset.actions]

    @property
    def dataset_states_and_extensions_summary(self):
        if self._dce.child_collection:
            return self._dce.child_collection.dataset_states_and_extensions_summary
        else:
            hda = self._dce.dataset_instance
            extensions = set()
            states = set()
            states.add(hda.dataset.state)
            extensions.add(hda.extension)
            return (states, extensions)

    @property
    def dataset_instances(self):
        return self._dce.dataset_instances

    @property
    def elements(self):
        if self._dce.child_collection:
            return self._dce.child_collection.elements
        else:
            return [self._dce]

    @property
    def adapting(self):
        return self._dce

    @property
    def _adapting_src_dict(self):
        return {
            "src": "dce",
            "id": self._dce.id,
        }


class PromoteCollectionElementToCollectionAdapter(DCECollectionAdapter):
    # allow a singleton list element to act as paired_or_unpaired collection

    def to_adapter_model(self) -> AdaptedDataCollectionPromoteCollectionElementToCollectionRequestInternal:
        adapting_model = DatasetCollectionElementReference.model_validate(self._adapting_src_dict)
        return AdaptedDataCollectionPromoteCollectionElementToCollectionRequestInternal(
            src="CollectionAdapter",
            adapter_type="PromoteCollectionElementToCollection",
            adapting=adapting_model,
        )

    @property
    def collection_type(self) -> str:
        return "paired_or_unpaired"


class PromoteDatasetToCollection(CollectionAdapter):

    def __init__(self, hda: "HistoryDatasetAssociation", collection_type: str):
        assert collection_type in ["list", "paired_or_unpaired"]
        self._hda = hda
        self._collection_type = collection_type

    def to_adapter_model(self) -> AdaptedDataCollectionPromoteDatasetToCollectionRequestInternal:
        adapting = {
            "src": "hda",
            "id": self._hda.id,
        }
        adapting_model = DataRequestInternalHda.model_validate(adapting)
        return AdaptedDataCollectionPromoteDatasetToCollectionRequestInternal(
            src="CollectionAdapter",
            adapter_type="PromoteDatasetToCollection",
            collection_type=self._collection_type,
            adapting=adapting_model,
        )

    @property
    def dataset_action_tuples(self):
        hda = self._hda
        return [(permission.action, permission.role_id) for permission in hda.dataset.actions]

    @property
    def dataset_states_and_extensions_summary(self):
        hda = self._hda
        extensions = set()
        states = set()
        states.add(hda.dataset.state)
        extensions.add(hda.extension)
        return (states, extensions)

    @property
    def dataset_instances(self):
        return [self._hda]

    @property
    def elements(self):
        identifier = self._hda.name
        if self._collection_type == "paired_or_unpaired":
            identifier = "unpaired"
        return [TransientCollectionAdapterDatasetInstanceElement(identifier, self._hda)]

    @property
    def adapting(self):
        return self._hda

    @property
    def collection_type(self) -> str:
        return self._collection_type


class PromoteDatasetsToCollection(CollectionAdapter):
    _collection_type: str
    _elements: List["TransientCollectionAdapterDatasetInstanceElement"]

    def __init__(self, elements: List["TransientCollectionAdapterDatasetInstanceElement"], collection_type: str):
        assert collection_type in ["paired", "paired_or_unpaired"]
        self._collection_type = collection_type
        self._elements = elements

    def to_adapter_model(self) -> AdaptedDataCollectionPromoteDatasetsToCollectionRequestInternal:
        element_models = []
        for element in self._elements:
            element_model = AdapterElementRequestInternal(
                src="hda",
                id=element.hda.id,
                name=element.element_identifier,
            )
            element_models.append(element_model)
        return AdaptedDataCollectionPromoteDatasetsToCollectionRequestInternal(
            src="CollectionAdapter",
            adapter_type="PromoteDatasetsToCollection",
            collection_type=self._collection_type,
            adapting=element_models,
        )

    @property
    def dataset_instances(self):
        return [e.dataset_instance for e in self._elements]

    @property
    def elements(self):
        return self._elements

    @property
    def element_object(self) -> Self:
        # this is a stand-in or adapter for a real collection so this might be the object?
        return self

    @property
    def dataset_action_tuples(self):
        tuples = []
        for hda in self.dataset_instances:
            tuples.append([(permission.action, permission.role_id) for permission in hda.dataset.actions])
        return tuples

    @property
    def dataset_states_and_extensions_summary(self):
        extensions = set()
        states = set()
        for hda in self.dataset_instances:
            states.add(hda.dataset.state)
            extensions.add(hda.extension)
        return (states, extensions)

    @property
    def adapting(self):
        return self._elements

    @property
    def collection_type(self) -> str:
        return self._collection_type


class TransientCollectionAdapterDatasetInstanceElement:
    def __init__(self, element_identifier, hda: "HistoryDatasetAssociation"):
        self.element_identifier = element_identifier
        self.child_collection = None
        self.hda = hda

    @property
    def element_object(self):
        return self.hda

    @property
    def dataset_instance(self):
        return self.hda

    @property
    def is_collection(self):
        return False


def recover_adapter(wrapped_object, adapter_model):
    adapter_type = adapter_model.adapter_type
    if adapter_type == "PromoteCollectionElementToCollection":
        return PromoteCollectionElementToCollectionAdapter(wrapped_object)
    elif adapter_type == "PromoteDatasetToCollection":
        return PromoteDatasetToCollection(wrapped_object, adapter_model.collection_type)
    elif adapter_type == "PromoteDatasetsToCollection":
        return PromoteDatasetsToCollection(wrapped_object, adapter_model.collection_type)
    else:
        raise Exception(f"Unknown collection adapter encountered {adapter_type}")


def validate_collection_adapter_src_dict(value):
    try:
        return AdaptedDataCollectionRequestInternalTypeAdapter.validate_python(value)
    except ValidationError:
        return AdaptedDataCollectionRequestTypeAdapter.validate_python(value)
