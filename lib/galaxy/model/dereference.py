import logging
import os.path
from typing import (
    List,
    Optional,
    Sequence,
    Union,
)

from sqlalchemy import (
    false,
    null,
    select,
)
from sqlalchemy.orm import (
    aliased,
    Session,
)

from galaxy.model import (
    Dataset,
    DatasetCollection,
    DatasetCollectionElement,
    DatasetHash,
    DatasetSource,
    DatasetSourceHash,
    History,
    HistoryDatasetAssociation,
    HistoryDatasetCollectionAssociation,
    REQUESTED_TRANSFORM_ACTIONS,
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

log = logging.getLogger(__name__)


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
    transform: REQUESTED_TRANSFORM_ACTIONS = [{"action": "datatype_groom"}]
    if data_request_uri.space_to_tab:
        transform.append({"action": "spaces_to_tabs"})
    elif data_request_uri.to_posix_lines:
        transform.append({"action": "to_posix_lines"})
    dataset_source.requested_transform = transform

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


def get_replacement_dataset(
    session: Session,
    user: Optional[User],
    dataset_sources: List[DatasetSource],
    dataset_hashes: Sequence[Union[DatasetHash, DatasetSourceHash]],
    extension: str,
    object_store_id: str,
    created_from_basename: Optional[str] = None,
) -> Optional[HistoryDatasetAssociation]:
    """
    Get a replacement dataset for the given source URI and dataset hash.
    If we already have such a dataset we don't need to create a new one.
    """
    if not user or not dataset_sources:
        return None
    # TODO: this all picks just the first source and hash.
    if not dataset_hashes:
        dataset_hashes = dataset_sources[0].hashes
    if not dataset_hashes:
        # If no hashes are provided, we can't find an existing dataset.
        return None

    dataset_hash = dataset_hashes[0]
    dataset_source = dataset_sources[0]

    existing_source = aliased(DatasetSource, name="existing_source")
    existing_dataset_select = (
        select(HistoryDatasetAssociation)
        .join(Dataset, Dataset.id == HistoryDatasetAssociation.dataset_id)
        .join(existing_source, existing_source.dataset_id == Dataset.id)
        .join(History, HistoryDatasetAssociation.history_id == History.id)
        .where(
            Dataset.deleted == false(),
            Dataset.purged == false(),
            Dataset.created_from_basename == created_from_basename,
            Dataset.object_store_id == object_store_id,
            Dataset.state == Dataset.states.OK,
            HistoryDatasetAssociation.extension == extension,
            HistoryDatasetAssociation._state == null(),
            History.user_id == user.id,
        )
    )
    existing_hash = aliased(DatasetHash, name="existing_hash")
    existing_source_hash = aliased(DatasetSourceHash, name="existing_source_hash")
    if isinstance(dataset_hash, DatasetSourceHash):
        # This is the hash of the source, prior to any transformations.
        # We need to ensure that the source uri matches and that the hash was validated (what happens on hash mismatch? needs test).
        existing_dataset_select = existing_dataset_select.join(
            existing_source_hash, existing_source_hash.dataset_source_id == existing_source.id
        )
        existing_dataset_select = existing_dataset_select.where(
            # we have the prospectice hash and transform, if the dataset is then also coming from the same source, we can use it.
            # if the hash is provided we verify it matches (see test_run_workflow_with_invalid_url_hashes)
            # Note that the requester has included the source hash, so we don't care that the source might have changed since the original request.
            existing_source.requested_transform == dataset_source.requested_transform,
            existing_source.source_uri == dataset_source.source_uri,
            existing_source_hash.hash_function == dataset_hash.hash_function,
            existing_source_hash.hash_value == dataset_hash.hash_value,
        )
    else:
        # We have the actual calculated hash on disk, we don't need to care about the source
        existing_dataset_select = existing_dataset_select.join(existing_hash, existing_hash.dataset_id == Dataset.id)
        existing_dataset_select = existing_dataset_select.where(
            existing_hash.hash_function == dataset_hash.hash_function,
            existing_hash.hash_value == dataset_hash.hash_value,
        )
    log.debug(
        "Searching for existing dataset query: %s",
        str(existing_dataset_select.compile(compile_kwargs={"literal_binds": True})),
    )
    existing_dataset = session.scalars(existing_dataset_select.limit(1)).first()
    if existing_dataset and existing_dataset.extra_files_path_exists():
        # Can't deal with this (yet)
        return None

    datatype = existing_dataset.datatype if existing_dataset else None
    if not datatype:
        return None
    if datatype.composite_files:
        return None
    return existing_dataset
