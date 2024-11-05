import abc
import logging
import os
import shutil
from typing import (
    cast,
    List,
    NamedTuple,
    Optional,
    Union,
)

from sqlalchemy.orm import (
    object_session,
    Session,
)
from sqlalchemy.orm.exc import DetachedInstanceError

from galaxy.datatypes.sniff import (
    convert_function,
    stream_url_to_file,
)
from galaxy.exceptions import ObjectAttributeInvalidException
from galaxy.files import ConfiguredFileSources
from galaxy.model import (
    Dataset,
    DatasetCollection,
    DatasetCollectionElement,
    DatasetHash,
    DatasetSource,
    DescribesHash,
    History,
    HistoryDatasetAssociation,
    HistoryDatasetCollectionAssociation,
    LibraryDatasetDatasetAssociation,
)
from galaxy.model.base import transaction
from galaxy.objectstore import (
    ObjectStore,
    ObjectStorePopulator,
)
from galaxy.util.hash_util import verify_hash

log = logging.getLogger(__name__)


class TransientDatasetPaths(NamedTuple):
    external_filename: str
    external_extra_files_path: str
    metadata_files_dir: str


class TransientPathMapper:
    @abc.abstractmethod
    def transient_paths_for(self, old_dataset: Dataset) -> TransientDatasetPaths:
        """Map dataset to transient paths for detached HDAs.

        Decide external_filename and external_extra_files_path that the supplied dataset's
        materialized dataset should have its files written to.
        """


class SimpleTransientPathMapper(TransientPathMapper):
    def __init__(self, staging_directory: str):
        self._staging_directory = staging_directory

    def transient_paths_for(self, old_dataset: Dataset) -> TransientDatasetPaths:
        external_filename_basename = f"dataset_{old_dataset.uuid}.dat"
        external_filename = os.path.join(self._staging_directory, external_filename_basename)
        external_extras_basename = f"dataset_{old_dataset.uuid}_files"
        external_extras = os.path.join(self._staging_directory, external_extras_basename)
        return TransientDatasetPaths(external_filename, external_extras, self._staging_directory)


class DatasetInstanceMaterializer:
    """This class is responsible for ensuring dataset instances are not deferred."""

    def __init__(
        self,
        attached: bool,
        object_store_populator: Optional[ObjectStorePopulator] = None,
        transient_path_mapper: Optional[TransientPathMapper] = None,
        file_sources: Optional[ConfiguredFileSources] = None,
        sa_session: Optional[Session] = None,
    ):
        """Constructor for DatasetInstanceMaterializer.

        If attached is true, these objects should be created in a supplied object store.
        If not, this class produces transient HDAs with external_filename and
        external_extra_files_path set.
        """
        self._attached = attached
        self._transient_path_mapper = transient_path_mapper
        self._object_store_populator = object_store_populator
        self._file_sources = file_sources
        self._sa_session = sa_session

    def ensure_materialized(
        self,
        dataset_instance: Union[HistoryDatasetAssociation, LibraryDatasetDatasetAssociation],
        target_history: Optional[History] = None,
        in_place: bool = False,
    ) -> HistoryDatasetAssociation:
        """Create a new detached dataset instance from the supplied instance.

        There will be times we want it usable as is without an objectstore and times
        we want to place it in an objectstore.
        """
        attached = self._attached
        dataset = dataset_instance.dataset
        if dataset.state != Dataset.states.DEFERRED and isinstance(dataset_instance, HistoryDatasetAssociation):
            return dataset_instance

        materialized_dataset_hashes = [h.copy() for h in dataset.hashes]
        if in_place:
            materialized_dataset = dataset_instance.dataset
            materialized_dataset.state = Dataset.states.OK
        else:
            materialized_dataset = Dataset()
            materialized_dataset.state = Dataset.states.OK
            materialized_dataset.deleted = False
            materialized_dataset.purged = False
            materialized_dataset.sources = [s.copy() for s in dataset.sources]
            materialized_dataset.hashes = materialized_dataset_hashes
        target_source = self._find_closest_dataset_source(dataset)
        transient_paths = None

        exception_materializing: Optional[Exception] = None
        if attached:
            object_store_populator = self._object_store_populator
            assert object_store_populator
            object_store = object_store_populator.object_store
            store_by = object_store.get_store_by(dataset)
            if store_by == "id":
                # we need a flush...
                sa_session = self._sa_session
                if sa_session is None:
                    sa_session = object_session(dataset_instance)
                assert sa_session
                sa_session.add(materialized_dataset)
                with transaction(sa_session):
                    sa_session.commit()
            object_store_populator.set_dataset_object_store_id(materialized_dataset)
            try:
                path = self._stream_source(target_source, dataset_instance.datatype, materialized_dataset_hashes)
                object_store.update_from_file(materialized_dataset, file_name=path)
                materialized_dataset.set_size()
            except Exception as e:
                exception_materializing = e
        else:
            transient_path_mapper = self._transient_path_mapper
            assert transient_path_mapper
            transient_paths = transient_path_mapper.transient_paths_for(dataset)
            # TODO: optimize this by streaming right to this path...
            # TODO: take into acount transform and ensure we are and are not modifying the file as appropriate.
            try:
                path = self._stream_source(target_source, dataset_instance.datatype, materialized_dataset_hashes)
                shutil.move(path, transient_paths.external_filename)
                materialized_dataset.external_filename = transient_paths.external_filename
            except Exception as e:
                exception_materializing = e

        history = target_history
        if history is None and isinstance(dataset_instance, HistoryDatasetAssociation):
            try:
                history = dataset_instance.history
            except DetachedInstanceError:
                history = None

        materialized_dataset_instance: HistoryDatasetAssociation
        if not in_place:
            materialized_dataset_instance = HistoryDatasetAssociation(
                create_dataset=False,  # is the default but lets make this really clear...
                history=history,
            )
        else:
            assert isinstance(dataset_instance, HistoryDatasetAssociation)
            materialized_dataset_instance = cast(HistoryDatasetAssociation, dataset_instance)
        if exception_materializing is not None:
            materialized_dataset.state = Dataset.states.ERROR
            materialized_dataset_instance.info = (
                f"Failed to materialize deferred dataset with exception: {exception_materializing}"
            )
        if attached:
            sa_session = self._sa_session
            if sa_session is None:
                sa_session = object_session(dataset_instance)
            assert sa_session
            sa_session.add(materialized_dataset_instance)
        if not in_place:
            materialized_dataset_instance.copy_from(
                dataset_instance, new_dataset=materialized_dataset, include_tags=attached, include_metadata=True
            )
        require_metadata_regeneration = (
            materialized_dataset_instance.has_metadata_files or materialized_dataset_instance.metadata_deferred
        )
        if require_metadata_regeneration:
            materialized_dataset_instance.init_meta()
            if transient_paths:
                metadata_tmp_files_dir = transient_paths.metadata_files_dir
            else:
                # If metadata_tmp_files_dir is set we generate a MetadataTempFile,
                # which we don't want when we're generating an attached materialized dataset instance
                metadata_tmp_files_dir = None
            materialized_dataset_instance.set_meta(metadata_tmp_files_dir=metadata_tmp_files_dir)
            materialized_dataset_instance.metadata_deferred = False
        return materialized_dataset_instance

    def _stream_source(self, target_source: DatasetSource, datatype, dataset_hashes: List[DatasetHash]) -> str:
        source_uri = target_source.source_uri
        if source_uri is None:
            raise Exception("Cannot stream from dataset source without specified source_uri")
        path = stream_url_to_file(source_uri, file_sources=self._file_sources)
        if target_source.hashes:
            for source_hash in target_source.hashes:
                _validate_hash(path, source_hash, "downloaded file")

        transform = target_source.transform or []
        to_posix_lines = False
        spaces_to_tabs = False
        datatype_groom = False
        for transform_action in transform:
            action = transform_action["action"]
            if action == "to_posix_lines":
                to_posix_lines = True
            elif action == "spaces_to_tabs":
                spaces_to_tabs = True
            elif action == "datatype_groom":
                datatype_groom = True
            else:
                raise Exception(f"Failed to materialize dataset, unknown transformation action {action} applied.")
        if to_posix_lines or spaces_to_tabs:
            convert_fxn = convert_function(to_posix_lines, spaces_to_tabs)
            convert_result = convert_fxn(path, False)
            assert convert_result.converted_path
            path = convert_result.converted_path
        if datatype_groom:
            datatype.groom_dataset_content(path)

        if dataset_hashes:
            for dataset_hash in dataset_hashes:
                _validate_hash(path, dataset_hash, "dataset contents")

        return path

    def _find_closest_dataset_source(self, dataset: Dataset) -> DatasetSource:
        best_source = None
        for source in dataset.sources:
            if source.extra_files_path:
                continue
            best_source = source
            break
        if best_source is None:
            # TODO: implement test case...
            raise ObjectAttributeInvalidException("dataset does not contain any valid dataset sources")
        return best_source


CollectionInputT = Union[HistoryDatasetCollectionAssociation, DatasetCollectionElement]


def materialize_collection_input(
    collection_input: CollectionInputT, materializer: DatasetInstanceMaterializer
) -> CollectionInputT:
    if isinstance(collection_input, HistoryDatasetCollectionAssociation):
        return materialize_collection_instance(
            cast(HistoryDatasetCollectionAssociation, collection_input), materializer
        )
    else:
        return _materialize_collection_element(cast(DatasetCollectionElement, collection_input), materializer)


def materialize_collection_instance(
    hdca: HistoryDatasetCollectionAssociation, materializer: DatasetInstanceMaterializer
) -> HistoryDatasetCollectionAssociation:
    if materializer._attached:
        raise NotImplementedError("Materializing collections to attached collections unimplemented")

    if not hdca.has_deferred_data:
        return hdca

    materialized_instance = HistoryDatasetCollectionAssociation()
    materialized_instance.name = hdca.name
    materialized_instance.collection = _materialize_collection(hdca.collection, materializer)
    # TODO: tags
    return materialized_instance


def _materialize_collection(
    dataset_collection: DatasetCollection, materializer: DatasetInstanceMaterializer
) -> DatasetCollection:
    materialized_collection = DatasetCollection()

    materialized_elements = []
    for element in dataset_collection.elements:
        materialized_elements.append(_materialize_collection_element(element, materializer))
    materialized_collection.elements = materialized_elements
    return materialized_collection


def _materialize_collection_element(
    element: DatasetCollectionElement, materializer: DatasetInstanceMaterializer
) -> DatasetCollectionElement:
    materialized_object: Union[DatasetCollection, HistoryDatasetAssociation, LibraryDatasetDatasetAssociation]
    if element.is_collection:
        assert element.child_collection
        materialized_object = _materialize_collection(element.child_collection, materializer)
    else:
        element_object = element.dataset_instance
        assert element_object
        materialized_object = materializer.ensure_materialized(element_object)
    materialized_element = DatasetCollectionElement(
        element=materialized_object,
        element_index=element.element_index,
        element_identifier=element.element_identifier,
    )
    return materialized_element


def materializer_factory(
    attached: bool,
    object_store: Optional[ObjectStore] = None,
    object_store_populator: Optional[ObjectStorePopulator] = None,
    transient_path_mapper: Optional[TransientPathMapper] = None,
    transient_directory: Optional[str] = None,
    file_sources: Optional[ConfiguredFileSources] = None,
    sa_session: Optional[Session] = None,
) -> DatasetInstanceMaterializer:
    if object_store_populator is None and object_store is not None:
        object_store_populator = ObjectStorePopulator(object_store, None)
    if transient_path_mapper is None and transient_directory is not None:
        transient_path_mapper = SimpleTransientPathMapper(transient_directory)
    return DatasetInstanceMaterializer(
        attached,
        object_store_populator=object_store_populator,
        transient_path_mapper=transient_path_mapper,
        file_sources=file_sources,
        sa_session=sa_session,
    )


def _validate_hash(path: str, describes_hash: DescribesHash, what: str) -> None:
    hash_value = describes_hash.hash_value
    if hash_value is not None:
        verify_hash(path, hash_func_name=describes_hash.hash_func_name, hash_value=hash_value)
