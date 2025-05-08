import os.path
from typing import (
    List,
    Union,
)

from galaxy.model import (
    DatasetCollection,
    DatasetCollectionElement,
    DatasetSource,
    DatasetSourceHash,
    History,
    HistoryDatasetAssociation,
    HistoryDatasetCollectionAssociation,
    TransformAction,
    User,
)
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.tool_util_models.parameters import (
    CollectionElementCollectionRequestUri,
    CollectionElementDataRequestUri,
    DataRequestCollectionUri,
    DataRequestUri,
    FileRequestUri,
)


def dereference_to_model(
    sa_session: galaxy_scoped_session,
    user: User,
    history: History,
    data_request_uri: Union[DataRequestUri, FileRequestUri, CollectionElementDataRequestUri],
    add_to_history=True,
    visible=True,
) -> HistoryDatasetAssociation:
    if isinstance(data_request_uri, CollectionElementDataRequestUri):
        name = data_request_uri.identifier
    else:
        name = data_request_uri.name or os.path.basename(data_request_uri.url)
    dbkey = data_request_uri.dbkey or "?"
    hda = HistoryDatasetAssociation(
        name=name,
        extension=data_request_uri.ext,
        dbkey=dbkey,  # TODO
        history=history,
        create_dataset=True,
        sa_session=sa_session,
        visible=visible,
        flush=False,
    )
    hda.state = hda.states.DEFERRED
    dataset_source = DatasetSource()
    dataset_source.source_uri = data_request_uri.url
    hashes = []
    for dataset_hash in data_request_uri.hashes or []:
        hash_object = DatasetSourceHash()
        hash_object.hash_function = dataset_hash.hash_function
        hash_object.hash_value = dataset_hash.hash_value
        hashes.append(hash_object)
    dataset_source.hashes = hashes
    assert hda.dataset
    hda.dataset.sources = [dataset_source]
    transform: List[TransformAction] = []
    if data_request_uri.space_to_tab:
        transform.append({"action": "spaces_to_tabs"})
    elif data_request_uri.to_posix_lines:
        transform.append({"action": "to_posix_lines"})
    if len(transform) > 0:
        dataset_source.transform = transform

    sa_session.add(hda)
    sa_session.add(dataset_source)
    if add_to_history:
        history.add_dataset(hda, genome_build=dbkey, quota=False)
    return hda


def derefence_collection_element(
    sa_session: galaxy_scoped_session,
    user: User,
    history: History,
    element: CollectionElementCollectionRequestUri,
    parent_dataset_collection: DatasetCollection,
    element_index: int,
):
    child_dataset_collection = DatasetCollection(collection_type=element.collection_type)
    DatasetCollectionElement(
        collection=parent_dataset_collection,
        element=child_dataset_collection,
        element_identifier=element.identifier,
        element_index=element_index,
    )
    sa_session.add(child_dataset_collection)
    for index, child_element in enumerate(element.elements):
        if child_element.class_ == "File":
            dereference_collection_dataset_element(
                sa_session, user, history, child_element, child_dataset_collection, element_index=index
            )
        elif child_element.class_ == "Collection":
            derefence_collection_element(
                sa_session, user, history, child_element, child_dataset_collection, element_index=element_index
            )
    child_dataset_collection.populated_state = "ok"
    child_dataset_collection.element_count = len(element.elements)


def dereference_collection_dataset_element(
    sa_session: galaxy_scoped_session,
    user: User,
    history: History,
    element: CollectionElementDataRequestUri,
    parent_dataset_collection: DatasetCollection,
    element_index: int,
):
    hda = dereference_to_model(sa_session, user, history, element, add_to_history=False, visible=False)
    history.stage_addition(hda)
    dce = DatasetCollectionElement(
        collection=parent_dataset_collection,
        element=hda,
        element_identifier=element.identifier,
        element_index=element_index,
    )
    parent_dataset_collection.elements.append(dce)


def derefence_collection_to_model(
    sa_session: galaxy_scoped_session,
    user: User,
    history: History,
    data_request_uri: DataRequestCollectionUri,
    collection_name: str = "Collection",
) -> HistoryDatasetCollectionAssociation:
    name = data_request_uri.name or collection_name
    hdca = HistoryDatasetCollectionAssociation(
        name=name,
        history=history,
    )
    sa_session.add(hdca)
    dc = DatasetCollection(collection_type=data_request_uri.collection_type)
    sa_session.add(dc)
    hdca.collection = dc
    for i, element in enumerate(data_request_uri.elements):
        if element.class_ == "File":
            dereference_collection_dataset_element(sa_session, user, history, element, dc, element_index=i)
        elif element.class_ == "Collection":
            derefence_collection_element(sa_session, user, history, element, dc, i)
    dc.populated_state = "ok"
    dc.element_count = len(data_request_uri.elements)
    history.stage_addition(hdca)
    return hdca
