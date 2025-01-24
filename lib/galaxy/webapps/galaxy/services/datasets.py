"""
API operations on the contents of a history dataset.
"""

import logging
import os
from enum import Enum
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

from pydantic import (
    ConfigDict,
    Field,
    RootModel,
)
from starlette.datastructures import URL

from galaxy import (
    exceptions as galaxy_exceptions,
    model,
    util,
    web,
)
from galaxy.celery.tasks import compute_dataset_hash
from galaxy.datatypes.binary import Binary
from galaxy.datatypes.dataproviders.exceptions import NoProviderAvailable
from galaxy.managers.base import ModelSerializer
from galaxy.managers.context import ProvidesHistoryContext
from galaxy.managers.datasets import (
    DatasetAssociationManager,
    DatasetManager,
)
from galaxy.managers.hdas import (
    HDAManager,
    HDASerializer,
)
from galaxy.managers.hdcas import HDCASerializer
from galaxy.managers.histories import HistoryManager
from galaxy.managers.history_contents import (
    HistoryContentsFilters,
    HistoryContentsManager,
)
from galaxy.managers.lddas import LDDAManager
from galaxy.objectstore.badges import BadgeDict
from galaxy.schema import (
    FilterQueryParams,
    SerializationParams,
)
from galaxy.schema.drs import (
    AccessMethod,
    AccessMethodType,
    AccessURL,
    Checksum,
    DrsObject,
)
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
    AnyHDA,
    AnyHistoryContentItem,
    AsyncTaskResultSummary,
    DatasetAssociationRoles,
    DatasetSourceId,
    DatasetSourceType,
    EncodedDatasetSourceId,
    Model,
    UpdateDatasetPermissionsPayload,
)
from galaxy.schema.tasks import ComputeDatasetHashTaskRequest
from galaxy.schema.types import RelativeUrl
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.util.hash_util import HashFunctionNameEnum
from galaxy.util.path import safe_walk
from galaxy.visualization.data_providers.genome import (
    BamDataProvider,
    FeatureLocationIndexDataProvider,
    SamDataProvider,
)
from galaxy.visualization.data_providers.registry import DataProviderRegistry
from galaxy.webapps.base.controller import UsesVisualizationMixin
from galaxy.webapps.galaxy.services.base import (
    async_task_summary,
    ServiceBase,
)

log = logging.getLogger(__name__)

DEFAULT_LIMIT = 500


class RequestDataType(str, Enum):
    """Particular pieces of information that can be requested for a dataset."""

    state = "state"
    converted_datasets_state = "converted_datasets_state"
    data = "data"
    features = "features"
    raw_data = "raw_data"
    track_config = "track_config"
    genome_data = "genome_data"
    in_use_state = "in_use_state"


class DatasetContentType(str, Enum):
    """For retrieving content from a structured dataset (e.g. HDF5)"""

    meta = "meta"
    attr = "attr"
    stats = "stats"
    data = "data"


class ConcreteObjectStoreQuotaSourceDetails(Model):
    source: Optional[str] = Field(
        description="The quota source label corresponding to the object store the dataset is stored in (or would be stored in)"
    )
    enabled: bool = Field(
        description="Whether the object store tracks quota on the data (independent of Galaxy's configuration)"
    )


class DatasetStorageDetails(Model):
    object_store_id: Optional[str] = Field(
        description="The identifier of the destination ObjectStore for this dataset.",
    )
    name: Optional[str] = Field(
        description="The display name of the destination ObjectStore for this dataset.",
    )
    description: Optional[str] = Field(
        description="A description of how this dataset is stored.",
    )
    percent_used: Optional[float] = Field(
        description="The percentage indicating how full the store is.",
    )
    dataset_state: str = Field(
        description="The model state of the supplied dataset instance.",
    )
    hashes: List[dict] = Field(description="The file contents hashes associated with the supplied dataset instance.")
    sources: List[dict] = Field(description="The file sources associated with the supplied dataset instance.")
    shareable: bool = Field(
        description="Is this dataset shareable.",
    )
    quota: ConcreteObjectStoreQuotaSourceDetails = Field(
        description="Information about quota sources around dataset storage."
    )
    badges: List[BadgeDict] = Field(
        description="A list of badges describing object store properties for concrete object store dataset is stored in."
    )
    relocatable: bool = Field(
        description="Indicator of whether the objectstore for this dataset can be switched by this user."
    )


class DatasetInheritanceChainEntry(Model):
    name: str = Field(
        description="Name of the referenced dataset",
    )
    dep: str = Field(
        description="Name of the source of the referenced dataset at this point of the inheritance chain.",
    )


class DatasetInheritanceChain(RootModel):
    root: List[DatasetInheritanceChainEntry] = Field(
        default=[],
        title="Dataset inheritance chain",
    )


class ExtraFilesEntryClass(str, Enum):
    Directory = "Directory"
    File = "File"


class ExtraFileEntry(Model):
    class_: ExtraFilesEntryClass = Field(
        alias="class",  # Is a reserved word so cannot be directly used as field
        description="The class of this entry, either File or Directory.",
    )
    path: str = Field(
        description="Relative path to the file or directory.",
    )


class DatasetExtraFiles(RootModel):
    """A list of extra files associated with a dataset."""

    root: List[ExtraFileEntry]


class DatasetTextContentDetails(Model):
    item_data: Optional[str] = Field(
        description="First chunk of text content (maximum 1MB) of the dataset.",
    )
    truncated: bool = Field(
        description="Whether the text in `item_data` has been truncated or contains the whole contents.",
    )
    item_url: RelativeUrl = Field(
        description="URL to access this dataset.",
    )


class ConvertedDatasetsMap(RootModel):
    """Map of `file extension` -> `converted dataset encoded id`"""

    root: Dict[str, DecodedDatabaseIdField]  # extension -> dataset ID
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "csv": "dataset_id",
            }
        }
    )


class DataMode(str, Enum):
    Coverage = "Coverage"
    Auto = "Auto"


class DataResult(Model):
    data: List[Any]
    dataset_type: Optional[str] = None
    message: Optional[str] = None
    extra_info: Optional[Any] = None  # Seems to be always None, deprecate?


class BamDataResult(DataResult):
    max_low: int
    max_high: int


class DeleteDatasetBatchPayload(Model):
    datasets: List[DatasetSourceId] = Field(
        description="The list of datasets IDs with their sources to be deleted/purged.",
    )
    purge: Optional[bool] = Field(
        default=False,
        description=(
            "Whether to permanently delete from disk the specified datasets. "
            "*Warning*: this is a destructive operation."
        ),
    )


class ComputeDatasetHashPayload(Model):
    hash_function: Optional[HashFunctionNameEnum] = Field(
        default=HashFunctionNameEnum.md5, description="Hash function name to use to compute dataset hashes."
    )
    extra_files_path: Optional[str] = Field(default=None, description="If set, extra files path to compute a hash for.")
    model_config = ConfigDict(use_enum_values=True)


class UpdateObjectStoreIdPayload(Model):
    object_store_id: str = Field(
        ...,
        description="Object store ID to update to, it must be an object store with the same device ID as the target dataset currently.",
    )


class DatasetErrorMessage(Model):
    dataset: EncodedDatasetSourceId = Field(
        description="The encoded ID of the dataset and its source.",
    )
    error_message: str = Field(
        description="The error message returned while processing this dataset.",
    )


class DeleteDatasetBatchResult(Model):
    success_count: int = Field(
        description="The number of datasets successfully processed.",
    )
    errors: Optional[List[DatasetErrorMessage]] = Field(
        default=None,
        description=(
            "A list of dataset IDs and the corresponding error message if something "
            "went wrong while processing the dataset."
        ),
    )


class DatasetsService(ServiceBase, UsesVisualizationMixin):
    def __init__(
        self,
        security: IdEncodingHelper,
        history_manager: HistoryManager,
        hda_manager: HDAManager,
        hda_serializer: HDASerializer,
        hdca_serializer: HDCASerializer,
        ldda_manager: LDDAManager,
        history_contents_manager: HistoryContentsManager,
        history_contents_filters: HistoryContentsFilters,
        data_provider_registry: DataProviderRegistry,
        dataset_manager: DatasetManager,
    ):
        super().__init__(security)
        self.history_manager = history_manager
        self.hda_manager = hda_manager
        self.hda_serializer = hda_serializer
        self.hdca_serializer = hdca_serializer
        self.ldda_manager = ldda_manager
        self.history_contents_manager = history_contents_manager
        self.history_contents_filters = history_contents_filters
        self.data_provider_registry = data_provider_registry
        self.dataset_manager = dataset_manager

    @property
    def serializer_by_type(self) -> Dict[str, ModelSerializer]:
        return {"dataset": self.hda_serializer, "dataset_collection": self.hdca_serializer}

    @property
    def dataset_manager_by_type(self) -> Dict[str, DatasetAssociationManager]:
        return {"hda": self.hda_manager, "ldda": self.ldda_manager}

    def index(
        self,
        trans: ProvidesHistoryContext,
        history_id: Optional[DecodedDatabaseIdField],
        serialization_params: SerializationParams,
        filter_query_params: FilterQueryParams,
    ) -> Tuple[List[AnyHistoryContentItem], int]:
        """
        Search datasets or collections using a query system and returns a list
        containing summary of dataset or dataset_collection information.
        """
        user = self.get_authenticated_user(trans)
        filters = self.history_contents_filters.parse_query_filters(filter_query_params)
        serialization_params.default_view = "summary"
        order_by = self.build_order_by(self.history_contents_manager, filter_query_params.order or "create_time-dsc")
        container = None
        if history_id:
            container = self.history_manager.get_accessible(history_id, user)
        contents = self.history_contents_manager.contents(
            container=container,
            filters=filters,
            limit=filter_query_params.limit or DEFAULT_LIMIT,
            offset=filter_query_params.offset,
            order_by=order_by,
            user_id=user.id,
        )
        total_matches = self.history_contents_manager.contents_count(
            container=container,
            filters=filters,
            user_id=user.id,
        )
        return (
            [
                self.serializer_by_type[content.history_content_type].serialize_to_view(
                    content, user=user, trans=trans, encode_id=False, **serialization_params.model_dump()
                )
                for content in contents
            ],
            total_matches,
        )

    def show(
        self,
        trans: ProvidesHistoryContext,
        dataset_id: DecodedDatabaseIdField,
        hda_ldda: DatasetSourceType,
        serialization_params: SerializationParams,
        data_type: Optional[RequestDataType] = None,
        **extra_params,
    ):
        """
        Displays information about and/or content of a dataset.
        """
        dataset_manager = self.dataset_manager_by_type[hda_ldda]
        dataset = dataset_manager.get_accessible(dataset_id, trans.user)
        requests_that_require_data = (
            RequestDataType.converted_datasets_state,
            RequestDataType.data,
            RequestDataType.features,
            RequestDataType.raw_data,
            RequestDataType.track_config,
        )
        if data_type in requests_that_require_data:
            dataset_manager.ensure_dataset_on_disk(trans, dataset)

        # Use data type to return particular type of data.
        rval: Any
        if data_type == RequestDataType.state:
            rval = self._dataset_state(dataset)
        elif data_type == RequestDataType.converted_datasets_state:
            rval = self._converted_datasets_state(
                trans,
                dataset,
                chrom=extra_params.get("chrom", None),
                retry=extra_params.get("retry", False),
            )
        elif data_type == RequestDataType.data:
            rval = self._data(trans, dataset, **extra_params)
        elif data_type == RequestDataType.features:
            rval = self._search_features(trans, dataset, query=extra_params.get("query", None))
        elif data_type == RequestDataType.raw_data:
            rval = self._raw_data(trans, dataset, **extra_params)
        elif data_type == RequestDataType.track_config:
            rval = self.get_new_track_config(trans, dataset)
        elif data_type == RequestDataType.genome_data:
            rval = self._get_genome_data(trans, dataset, dbkey=extra_params.get("dbkey", None))
        elif data_type == RequestDataType.in_use_state:
            rval = self._dataset_in_use_state(dataset)
        else:
            # Default: return dataset as dict.
            if hda_ldda == DatasetSourceType.hda:
                return self.hda_serializer.serialize_to_view(
                    dataset,
                    view=serialization_params.view or "detailed",
                    keys=serialization_params.keys,
                    user=trans.user,
                    trans=trans,
                )
            else:
                dataset_dict = dataset.to_dict()
                rval = self.encode_all_ids(dataset_dict)
        return rval

    def show_storage(
        self,
        trans: ProvidesHistoryContext,
        dataset_id: DecodedDatabaseIdField,
        hda_ldda: DatasetSourceType = DatasetSourceType.hda,
    ) -> DatasetStorageDetails:
        """
        Display user-facing storage details related to the objectstore a
        dataset resides in.
        """
        dataset_instance = self.dataset_manager_by_type[hda_ldda].get_accessible(dataset_id, trans.user)
        dataset = dataset_instance.dataset
        object_store = trans.app.object_store
        object_store_id = dataset.object_store_id
        name = object_store.get_concrete_store_name(dataset)
        description = object_store.get_concrete_store_description_markdown(dataset)
        badges = object_store.get_concrete_store_badges(dataset)
        # not really working (existing problem)
        try:
            percent_used = object_store.get_store_usage_percent()
        except AttributeError:
            # not implemented on nestedobjectstores yet.
            percent_used = None
        except FileNotFoundError:
            # uninitialized directory (empty) disk object store can cause this...
            percent_used = None

        quota_source = dataset.quota_source_info
        quota = ConcreteObjectStoreQuotaSourceDetails(
            source=quota_source.label,
            enabled=quota_source.use,
        )
        relocatable = trans.app.security_agent.can_change_object_store_id(trans.user, dataset)
        dataset_state = dataset.state
        hashes = [h.to_dict() for h in dataset.hashes]
        sources = [s.to_dict() for s in dataset.sources]
        return DatasetStorageDetails(
            object_store_id=object_store_id,
            shareable=dataset.shareable,
            name=name,
            description=description,
            percent_used=percent_used,
            dataset_state=dataset_state,
            hashes=hashes,
            sources=sources,
            quota=quota,
            badges=badges,
            relocatable=relocatable,
        )

    def show_inheritance_chain(
        self,
        trans: ProvidesHistoryContext,
        dataset_id: DecodedDatabaseIdField,
        hda_ldda: DatasetSourceType = DatasetSourceType.hda,
    ) -> DatasetInheritanceChain:
        """
        Display inheritance chain for the given dataset.
        """
        dataset_instance = self.dataset_manager_by_type[hda_ldda].get_accessible(dataset_id, trans.user)
        inherit_chain = dataset_instance.source_dataset_chain
        result = []
        for dep in inherit_chain:
            result.append(DatasetInheritanceChainEntry(name=f"{dep[0].name}", dep=dep[1]))

        return DatasetInheritanceChain(root=result)

    def compute_hash(
        self,
        trans: ProvidesHistoryContext,
        dataset_id: DecodedDatabaseIdField,
        payload: ComputeDatasetHashPayload,
        hda_ldda: DatasetSourceType = DatasetSourceType.hda,
    ) -> AsyncTaskResultSummary:
        dataset_instance = self.dataset_manager_by_type[hda_ldda].get_accessible(dataset_id, trans.user)
        request = ComputeDatasetHashTaskRequest(
            dataset_id=dataset_instance.dataset.id,
            extra_files_path=payload.extra_files_path,
            hash_function=payload.hash_function,
            user=trans.async_request_user,
        )
        result = compute_dataset_hash.delay(request=request, task_user_id=getattr(trans.user, "id", None))
        return async_task_summary(result)

    def drs_dataset_instance(self, object_id: str) -> Tuple[int, DatasetSourceType]:
        if object_id.startswith("hda-"):
            decoded_object_id = self.decode_id(object_id[len("hda-") :], kind="drs")
            hda_ldda = DatasetSourceType.hda
        elif object_id.startswith("ldda-"):
            decoded_object_id = self.decode_id(object_id[len("ldda-") :], kind="drs")
            hda_ldda = DatasetSourceType.ldda
        else:
            raise galaxy_exceptions.RequestParameterInvalidException(
                "Invalid object_id format specified for this Galaxy server"
            )
        return decoded_object_id, hda_ldda

    def get_drs_object(self, trans: ProvidesHistoryContext, object_id: str, request_url: URL) -> DrsObject:
        decoded_object_id, hda_ldda = self.drs_dataset_instance(object_id)
        dataset_instance = self.dataset_manager_by_type[hda_ldda].get_accessible(decoded_object_id, trans.user)
        if not trans.app.security_agent.dataset_is_public(dataset_instance.dataset):
            # Only public datasets may be access as DRS datasets currently
            raise galaxy_exceptions.ObjectNotFound("Cannot find a public dataset with specified object ID.")

        # TODO: issue warning if not being served on HTTPS @ 443 - required by the spec.
        self_uri = f"drs://drs.{request_url.components.netloc}/{object_id}"
        checksums: List[Checksum] = []
        for dataset_hash in dataset_instance.dataset.hashes:
            if dataset_hash.extra_files_path:
                continue
            type = dataset_hash.hash_function
            checksum = dataset_hash.hash_value
            checksums.append(Checksum(type=type, checksum=checksum))

        if len(checksums) == 0:
            hash_function = HashFunctionNameEnum.md5
            request = ComputeDatasetHashTaskRequest(
                dataset_id=dataset_instance.dataset.id,
                extra_files_path=None,
                hash_function=hash_function,
                user=None,
            )
            compute_dataset_hash.delay(request=request, task_user_id=getattr(trans.user, "id", None))
            raise galaxy_exceptions.AcceptedRetryLater(
                "required checksum task for DRS object response launched.", retry_after=60
            )

        base = str(request_url).split("/ga4gh", 1)[0]
        access_url = base + f"/api/drs_download/{object_id}"

        access_method = AccessMethod(
            type=AccessMethodType.https,
            access_url=AccessURL(url=access_url),
        )

        return DrsObject(
            id=object_id,
            self_uri=self_uri,
            size=dataset_instance.dataset.file_size,
            created_time=dataset_instance.create_time,
            checksums=checksums,
            access_methods=[access_method],
        )

    def update_permissions(
        self,
        trans: ProvidesHistoryContext,
        dataset_id: DecodedDatabaseIdField,
        payload: UpdateDatasetPermissionsPayload,
        hda_ldda: DatasetSourceType = DatasetSourceType.hda,
    ) -> DatasetAssociationRoles:
        """
        Updates permissions of a dataset.
        """
        self.check_user_is_authenticated(trans)
        payload_dict = payload.model_dump(by_alias=True)
        dataset_manager = self.dataset_manager_by_type[hda_ldda]
        dataset = dataset_manager.get_accessible(dataset_id, trans.user)
        dataset_manager.update_permissions(trans, dataset, **payload_dict)
        return dataset_manager.serialize_dataset_association_roles(dataset)

    def extra_files(
        self,
        trans: ProvidesHistoryContext,
        history_content_id: DecodedDatabaseIdField,
    ):
        """
        Generate list of extra files.
        """
        hda = self.hda_manager.get_accessible(history_content_id, trans.user)
        rval = []
        if not hda.is_pending and hda.extra_files_path_exists():
            extra_files_path = hda.extra_files_path
            for root, directories, files in safe_walk(extra_files_path):
                for directory in directories:
                    rval.append(
                        {"class": "Directory", "path": os.path.relpath(os.path.join(root, directory), extra_files_path)}
                    )
                for file in files:
                    rval.append({"class": "File", "path": os.path.relpath(os.path.join(root, file), extra_files_path)})

        return rval

    def display(
        self,
        trans: ProvidesHistoryContext,
        dataset_id: DecodedDatabaseIdField,
        hda_ldda: DatasetSourceType = DatasetSourceType.hda,
        preview: bool = False,
        filename: Optional[str] = None,
        to_ext: Optional[str] = None,
        raw: bool = False,
        offset: Optional[int] = None,
        ck_size: Optional[int] = None,
        **kwd,
    ):
        """
        Displays history content (dataset).

        The query parameter 'raw' should be considered experimental and may be dropped at
        some point in the future without warning. Generally, data should be processed by its
        datatype prior to display (the default if raw is unspecified or explicitly false.
        """
        headers = {}
        rval: Any = ""
        try:
            dataset_manager = self.dataset_manager_by_type[hda_ldda]
            dataset_instance = dataset_manager.get_accessible(dataset_id, trans.user)
            dataset_manager.ensure_dataset_on_disk(trans, dataset_instance)
            if raw:
                if filename and filename != "index":
                    object_store = trans.app.object_store
                    dir_name = dataset_instance.dataset.extra_files_path_name
                    file_path = object_store.get_filename(
                        dataset_instance.dataset, extra_dir=dir_name, alt_name=filename
                    )
                else:
                    file_path = dataset_instance.get_file_name()
                rval = open(file_path, "rb")
            else:
                if offset is not None:
                    kwd["offset"] = offset
                if ck_size is not None:
                    kwd["ck_size"] = ck_size
                rval, headers = dataset_instance.datatype.display_data(
                    trans, dataset_instance, preview, filename, to_ext, **kwd
                )
        except galaxy_exceptions.MessageException:
            raise
        except Exception as e:
            raise galaxy_exceptions.InternalServerError(f"Could not get display data for dataset: {util.unicodify(e)}")
        return rval, headers

    def get_content_as_text(
        self,
        trans: ProvidesHistoryContext,
        dataset_id: DecodedDatabaseIdField,
    ) -> DatasetTextContentDetails:
        """Returns dataset content as Text."""
        user = trans.user
        hda = self.hda_manager.get_accessible(dataset_id, user)
        hda = self.hda_manager.error_if_uploading(hda)
        truncated, dataset_data = self.hda_manager.text_data(hda, preview=True)
        item_url = web.url_for(
            controller="dataset",
            action="display_by_username_and_slug",
            username=hda.user and hda.user.username,
            slug=self.encode_id(hda.id),
            preview=False,
        )
        return DatasetTextContentDetails(
            item_data=dataset_data,
            truncated=truncated,
            item_url=item_url,
        )

    def get_metadata_file(
        self,
        trans: ProvidesHistoryContext,
        history_content_id: DecodedDatabaseIdField,
        metadata_file: str,
        open_file: bool = False,
    ):
        """
        Gets the associated metadata file.

        The `open_file` parameter determines if we return the path of the file or the opened file handle.
        TODO: Remove the `open_file` parameter when removing the associated legacy endpoint.
        """
        hda = self.hda_manager.get_accessible(history_content_id, trans.user)
        self.hda_manager.ensure_dataset_on_disk(trans, hda)
        file_ext = hda.metadata.spec.get(metadata_file).get("file_ext", metadata_file)
        fname = "".join(c in util.FILENAME_VALID_CHARS and c or "_" for c in hda.name)[0:150]
        headers = {}
        headers["Content-Type"] = "application/octet-stream"
        headers["Content-Disposition"] = f'attachment; filename="Galaxy{hda.hid}-[{fname}].{file_ext}"'
        file_path = hda.metadata.get(metadata_file).get_file_name()
        if open_file:
            return open(file_path, "rb"), headers
        return file_path, headers

    def converted_ext(
        self,
        trans: ProvidesHistoryContext,
        dataset_id: DecodedDatabaseIdField,
        ext: str,
        serialization_params: SerializationParams,
    ) -> AnyHDA:
        """
        Return information about datasets made by converting this dataset to a new format
        """
        hda = self.hda_manager.get_accessible(dataset_id, trans.user)
        serialization_params.default_view = "detailed"
        converted = self._get_or_create_converted(trans, hda, ext)
        return self.hda_serializer.serialize_to_view(
            converted, user=trans.user, trans=trans, **serialization_params.model_dump()
        )

    def converted(
        self,
        trans: ProvidesHistoryContext,
        dataset_id: DecodedDatabaseIdField,
    ) -> ConvertedDatasetsMap:
        """
        Return a `file extension` -> `converted dataset encoded id` map
        with all the existing converted datasets associated with this instance.
        """
        hda = self.hda_manager.get_accessible(dataset_id, trans.user)
        return self.hda_serializer.serialize_converted_datasets(hda, "converted")

    def delete_batch(
        self,
        trans: ProvidesHistoryContext,
        payload: DeleteDatasetBatchPayload,
    ) -> DeleteDatasetBatchResult:
        """
        Deletes or purges a batch of datasets.
        Warning: only the ownership of the dataset and upload state for HDAs is checked, no other checks or restrictions are made.
        """
        success_count = 0
        errors: List[DatasetErrorMessage] = []
        for dataset in payload.datasets:
            try:
                manager = self.dataset_manager_by_type[dataset.src]
                dataset_instance = manager.get_owned(dataset.id, trans.user)
                manager.error_unless_mutable(dataset_instance.history)
                if dataset.src == DatasetSourceType.hda:
                    self.hda_manager.error_if_uploading(dataset_instance)
                if payload.purge:
                    manager.purge(dataset_instance, flush=True)
                else:
                    manager.delete(dataset_instance, flush=False)
                success_count += 1
            except galaxy_exceptions.MessageException as e:
                errors.append(
                    DatasetErrorMessage(
                        dataset=EncodedDatasetSourceId(id=dataset.id, src=dataset.src),
                        error_message=str(e),
                    )
                )

        if success_count:
            trans.sa_session.commit()
        return DeleteDatasetBatchResult.model_construct(success_count=success_count, errors=errors)

    def get_structured_content(
        self,
        trans: ProvidesHistoryContext,
        dataset_id: DecodedDatabaseIdField,
        content_type: DatasetContentType,
        **params,
    ):
        """
        Retrieves contents of a dataset. It is left to the datatype to decide how
        to interpret the content types.
        """
        headers = {}
        content: Any = ""
        dataset = self.hda_manager.get_accessible(dataset_id, trans.user)
        if not isinstance(dataset.datatype, Binary):
            raise galaxy_exceptions.InvalidFileFormatError("Only available for structured datatypes")
        try:
            content, headers = dataset.datatype.get_structured_content(dataset, content_type, **params)
        except galaxy_exceptions.MessageException:
            raise
        except Exception as e:
            raise galaxy_exceptions.InternalServerError(f"Could not get content for dataset: {util.unicodify(e)}")
        return content, headers

    def update_object_store_id(self, trans, dataset_id: DecodedDatabaseIdField, payload: UpdateObjectStoreIdPayload):
        hda = self.hda_manager.get_accessible(dataset_id, trans.user)
        dataset = hda.dataset
        self.dataset_manager.update_object_store_id(trans, dataset, payload.object_store_id)

    def _get_or_create_converted(self, trans, original: model.DatasetInstance, target_ext: str):
        try:
            original.get_converted_dataset(trans, target_ext)
            converted = original.get_converted_files_by_type(target_ext)
            return converted

        except model.NoConverterException:
            exc_data = dict(
                source=original.ext, target=target_ext, available=list(original.get_converter_types().keys())
            )
            raise galaxy_exceptions.RequestParameterInvalidException("Conversion not possible", **exc_data)

    def _dataset_in_use_state(self, dataset: model.DatasetInstance) -> bool:
        """
        Return True if dataset is currently used as an input or output. False otherwise.
        """
        return not dataset.ok_to_edit_metadata()

    def _dataset_state(self, dataset: model.DatasetInstance) -> model.Dataset.conversion_messages:
        """
        Returns state of dataset.
        """
        msg = self.hda_manager.data_conversion_status(dataset)
        if not msg:
            msg = dataset.conversion_messages.DATA

        return msg

    def _converted_datasets_state(
        self,
        trans,
        dataset: model.DatasetInstance,
        chrom: Optional[str] = None,
        retry: bool = False,
    ) -> Union[model.Dataset.conversion_messages, dict]:
        """
        Init-like method that returns state of dataset's converted datasets.
        Returns valid chroms for that dataset as well.
        """
        msg = self.hda_manager.data_conversion_status(dataset)
        if msg:
            return msg

        # Get datasources and check for messages (which indicate errors). Retry if flag is set.
        data_sources = dataset.get_datasources(trans)
        messages_list = [data_source_dict["message"] for data_source_dict in data_sources.values()]
        msg = self._get_highest_priority_msg(messages_list)
        if msg:
            if retry:
                # Clear datasources and then try again.
                dataset.clear_associated_files()
                return self._converted_datasets_state(trans, dataset, chrom)
            else:
                return msg

        # If there is a chrom, check for data on the chrom.
        if chrom:
            data_provider = self.data_provider_registry.get_data_provider(
                trans, original_dataset=dataset, source="index"
            )
            if not dataset.has_data() or not data_provider.has_data(chrom):
                return dataset.conversion_messages.NO_DATA

        # Have data if we get here
        return {"status": dataset.conversion_messages.DATA, "valid_chroms": None}

    def _search_features(
        self,
        trans,
        dataset: model.DatasetInstance,
        query: Optional[str],
    ) -> List[List[str]]:
        """
        Returns features, locations in dataset that match query. Format is a
        list of features; each feature is a list itself: [name, location]
        """
        if query is None:
            raise galaxy_exceptions.RequestParameterMissingException(
                "Parameter `query` is required when searching features."
            )
        if dataset.can_convert_to("fli"):
            converted_dataset = dataset.get_converted_dataset(trans, "fli")
            if converted_dataset:
                data_provider = FeatureLocationIndexDataProvider(converted_dataset=converted_dataset)
                if data_provider:
                    return data_provider.get_data(query)

        return []

    def _data(
        self,
        trans: ProvidesHistoryContext,
        dataset: model.DatasetInstance,
        chrom: str,
        low: int,
        high: int,
        start_val: int = 0,
        max_vals: Optional[int] = None,
        **kwargs,
    ) -> Union[model.Dataset.conversion_messages, BamDataResult, DataResult]:
        """
        Provides a block of data from a dataset.
        """
        # Parameter check.
        if not chrom:
            return dataset.conversion_messages.NO_DATA

        # Dataset check.
        if msg := self.hda_manager.data_conversion_status(dataset):
            return msg

        # Get datasources and check for messages.
        data_sources = dataset.get_datasources(trans)
        messages_list = [data_source_dict["message"] for data_source_dict in data_sources.values()]
        if return_message := self._get_highest_priority_msg(messages_list):
            return return_message

        extra_info = None
        mode = kwargs.get("mode", "Auto")

        # Coverage mode uses index data.
        if mode == "Coverage":
            # Get summary using minimal cutoffs.
            indexer = self._get_indexer(trans, dataset)
            return indexer.get_data(chrom, low, high, **kwargs)

        # TODO:
        # (1) add logic back in for no_detail
        # (2) handle scenario where mode is Squish/Pack but data requested is large, so reduced data needed to be returned.

        # If mode is Auto, need to determine what type of data to return.
        if mode == "Auto":
            # Get stats from indexer.
            indexer = self._get_indexer(trans, dataset)
            stats = indexer.get_data(chrom, low, high, stats=True)

            # If stats were requested, return them.
            if "stats" in kwargs:
                if stats["data"]["max"] == 0:
                    return DataResult(dataset_type=indexer.dataset_type, data=[])
                else:
                    return stats

            # Stats provides features/base and resolution is bases/pixel, so
            # multiplying them yields features/pixel.
            features_per_pixel = stats["data"]["max"] * float(kwargs["resolution"])

            # Use heuristic based on features/pixel and region size to determine whether to
            # return coverage data. When zoomed out and region is large, features/pixel
            # is determining factor. However, when sufficiently zoomed in and region is
            # small, coverage data is no longer provided.
            if int(high) - int(low) > 50000 and features_per_pixel > 1000:
                return indexer.get_data(chrom, low, high)

        #
        # Provide individual data points.
        #

        # Get data provider.
        data_provider = self.data_provider_registry.get_data_provider(trans, original_dataset=dataset, source="data")

        # Allow max_vals top be data provider set if not passed
        if max_vals is None:
            max_vals = data_provider.get_default_max_vals()

        # Get reference sequence and mean depth for region; these is used by providers for aligned reads.
        region = None
        mean_depth = None
        if isinstance(data_provider, (SamDataProvider, BamDataProvider)):
            # Get reference sequence.
            if dataset.dbkey:
                # FIXME: increase region 1M each way to provide sequence for
                # spliced/gapped reads. Probably should provide refseq object
                # directly to data provider.
                region = trans.app.genomes.reference(
                    trans,
                    dbkey=dataset.dbkey,
                    chrom=chrom,
                    low=(max(0, int(low) - 1000000)),
                    high=(int(high) + 1000000),
                )

            # Get mean depth.
            indexer = self._get_indexer(trans, dataset)
            stats = indexer.get_data(chrom, low, high, stats=True)
            mean_depth = stats["data"]["mean"]

        # Get and return data from data_provider.
        result = data_provider.get_data(
            chrom, int(low), int(high), int(start_val), int(max_vals), ref_seq=region, mean_depth=mean_depth, **kwargs
        )
        result.update({"dataset_type": data_provider.dataset_type, "extra_info": extra_info})
        return result

    def _raw_data(
        self,
        trans,
        dataset,
        provider=None,
        **kwargs,
    ) -> Union[model.Dataset.conversion_messages, BamDataResult, DataResult]:
        """
        Uses original (raw) dataset to return data. This method is useful
        when the dataset is not yet indexed and hence using data would
        be slow because indexes need to be created.
        """
        # Dataset check.
        if msg := self.hda_manager.data_conversion_status(dataset):
            return msg

        registry = self.data_provider_registry

        # allow the caller to specify which provider is used
        #   pulling from the original providers if possible, then the new providers
        if provider:
            if provider in registry.dataset_type_name_to_data_provider:
                data_provider = registry.get_data_provider(trans, name=provider, original_dataset=dataset)

            elif dataset.datatype.has_dataprovider(provider):
                kwargs = dataset.datatype.dataproviders[provider].parse_query_string_settings(kwargs)
                # use dictionary to allow more than the data itself to be returned (data totals, other meta, etc.)
                return DataResult(data=list(dataset.datatype.dataprovider(dataset, provider, **kwargs)))

            else:
                raise NoProviderAvailable(dataset.datatype, provider)

        # no provider name: look up by datatype
        else:
            data_provider = registry.get_data_provider(trans, raw=True, original_dataset=dataset)

        # Return data.
        data = data_provider.get_data(**kwargs)

        return data

    def _get_indexer(self, trans, dataset):
        indexer = self.data_provider_registry.get_data_provider(trans, original_dataset=dataset, source="index")
        if indexer is None:
            msg = f"No indexer available for dataset {self.encode_id(dataset.id)}"
            log.exception(msg)
            raise galaxy_exceptions.ObjectNotFound(msg)
        return indexer
