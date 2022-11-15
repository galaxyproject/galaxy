import glob
import logging
import os
import shutil
from pathlib import Path
from tempfile import (
    NamedTemporaryFile,
    SpooledTemporaryFile,
)
from typing import (
    List,
    Optional,
    Tuple,
    Union,
)

from sqlalchemy import (
    false,
    true,
)

from galaxy import exceptions as glx_exceptions
from galaxy import model
from galaxy.celery.tasks import (
    import_model_store,
    prepare_history_download,
    write_history_to,
)
from galaxy.files.uris import validate_uri_access
from galaxy.managers.citations import CitationsManager
from galaxy.managers.context import ProvidesHistoryContext
from galaxy.managers.histories import (
    HistoryDeserializer,
    HistoryExportView,
    HistoryFilters,
    HistoryManager,
    HistorySerializer,
)
from galaxy.managers.users import UserManager
from galaxy.model.store import payload_to_source_uri
from galaxy.schema import (
    FilterQueryParams,
    SerializationParams,
)
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.schema.schema import (
    AnyHistoryView,
    AsyncFile,
    AsyncTaskResultSummary,
    CreateHistoryFromStore,
    CreateHistoryPayload,
    CustomBuildsMetadataResponse,
    ExportHistoryArchivePayload,
    HistoryArchiveExportResult,
    HistoryImportArchiveSourceType,
    JobExportHistoryArchiveModel,
    JobIdResponse,
    JobImportHistoryResponse,
    LabelValuePair,
    StoreExportPayload,
    WriteStoreToPayload,
)
from galaxy.schema.tasks import (
    GenerateHistoryDownload,
    ImportModelStoreTaskRequest,
    WriteHistoryTo,
)
from galaxy.schema.types import LatestLiteral
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.util import restore_text
from galaxy.web.short_term_storage import ShortTermStorageAllocator
from galaxy.webapps.galaxy.services.base import (
    async_task_summary,
    ConsumesModelStores,
    model_store_storage_target,
    ServesExportStores,
    ServiceBase,
)
from galaxy.webapps.galaxy.services.sharable import ShareableService

log = logging.getLogger(__name__)

DEFAULT_ORDER_BY = "create_time-dsc"


class HistoriesService(ServiceBase, ConsumesModelStores, ServesExportStores):
    """Common interface/service logic for interactions with histories in the context of the API.

    Provides the logic of the actions invoked by API controllers and uses type definitions
    and pydantic models to declare its parameters and return types.
    """

    def __init__(
        self,
        security: IdEncodingHelper,
        manager: HistoryManager,
        user_manager: UserManager,
        serializer: HistorySerializer,
        deserializer: HistoryDeserializer,
        citations_manager: CitationsManager,
        history_export_view: HistoryExportView,
        filters: HistoryFilters,
        short_term_storage_allocator: ShortTermStorageAllocator,
    ):
        super().__init__(security)
        self.manager = manager
        self.user_manager = user_manager
        self.serializer = serializer
        self.deserializer = deserializer
        self.citations_manager = citations_manager
        self.history_export_view = history_export_view
        self.filters = filters
        self.shareable_service = ShareableService(self.manager, self.serializer)
        self.short_term_storage_allocator = short_term_storage_allocator

    def index(
        self,
        trans: ProvidesHistoryContext,
        serialization_params: SerializationParams,
        filter_query_params: FilterQueryParams,
        deleted_only: Optional[bool] = False,
        all_histories: Optional[bool] = False,
    ):
        """
        Return a collection of histories for the current user. Additional filters can be applied.

        :type   deleted_only: optional boolean
        :param  deleted_only: if True, show only deleted histories, if False, non-deleted

        .. note:: Anonymous users are allowed to get their current history
        """
        # bail early with current history if user is anonymous
        current_user = self.user_manager.current_user(trans)
        if self.user_manager.is_anonymous(current_user):
            current_history = self.manager.get_current(trans)
            if not current_history:
                return []
            # note: ignores filters, limit, offset
            return [self._serialize_history(trans, current_history, serialization_params)]

        filter_params = self.filters.build_filter_params(filter_query_params)
        filters = []
        # support the old default of not-returning/filtering-out deleted_only histories
        filters += self._get_deleted_filter(deleted_only, filter_params)

        # if parameter 'all_histories' is true, throw exception if not admin
        # else add current user filter to query (default behaviour)
        if all_histories:
            if not trans.user_is_admin:
                message = "Only admins can query all histories"
                raise glx_exceptions.AdminRequiredException(message)
        else:
            filters += [model.History.user == current_user]
        # and any sent in from the query string
        filters += self.filters.parse_filters(filter_params)
        order_by = self._build_order_by(filter_query_params.order)

        histories = self.manager.list(
            filters=filters, order_by=order_by, limit=filter_query_params.limit, offset=filter_query_params.offset
        )

        rval = [
            self._serialize_history(trans, history, serialization_params, default_view="summary")
            for history in histories
        ]
        return rval

    def _get_deleted_filter(self, deleted: Optional[bool], filter_params: List[Tuple[str, str, str]]):
        # TODO: this should all be removed (along with the default) in v2
        # support the old default of not-returning/filtering-out deleted histories
        try:
            # the consumer must explicitly ask for both deleted and non-deleted
            #   but pull it from the parsed params (as the filter system will error on None)
            deleted_filter_index = filter_params.index(("deleted", "eq", "None"))
            filter_params.pop(deleted_filter_index)
            return []
        except ValueError:
            pass

        # the deleted string bool was also used as an 'include deleted' flag
        if deleted is True:
            return [model.History.deleted == true()]

        # the third option not handled here is 'return only deleted'
        #   if this is passed in (in the form below), simply return and let the filter system handle it
        if ("deleted", "eq", "True") in filter_params:
            return []

        # otherwise, do the default filter of removing the deleted histories
        return [model.History.deleted == false()]

    def create(
        self,
        trans: ProvidesHistoryContext,
        payload: CreateHistoryPayload,
        serialization_params: SerializationParams,
    ):
        """Create a new history from scratch, by copying an existing one or by importing
        from URL or File depending on the provided parameters in the payload.
        """
        copy_this_history_id = payload.history_id
        if trans.anonymous and not copy_this_history_id:  # Copying/Importing histories is allowed for anonymous users
            raise glx_exceptions.AuthenticationRequired("You need to be logged in to create histories.")
        if trans.user and trans.user.bootstrap_admin_user:
            raise glx_exceptions.RealUserRequiredException("Only real users can create histories.")
        hist_name = None
        if payload.name is not None:
            hist_name = restore_text(payload.name)

        if payload.archive_source is not None or hasattr(payload.archive_file, "file"):
            archive_source = payload.archive_source
            archive_file = payload.archive_file
            if archive_source:
                archive_type = payload.archive_type
            elif archive_file is not None and hasattr(archive_file, "file"):
                archive_source = archive_file.file.name
                archive_type = HistoryImportArchiveSourceType.file
                if isinstance(archive_file.file, SpooledTemporaryFile):
                    archive_source = self._save_upload_file_tmp(archive_file)
            else:
                raise glx_exceptions.MessageException("Please provide a url or file.")
            if archive_type == HistoryImportArchiveSourceType.url:
                assert archive_source
                validate_uri_access(archive_source, trans.user_is_admin, trans.app.config.fetch_url_allowlist_ips)
            job = self.manager.queue_history_import(trans, archive_type=archive_type, archive_source=archive_source)
            job_dict = job.to_dict()
            job_dict[
                "message"
            ] = f"Importing history from source '{archive_source}'. This history will be visible when the import is complete."
            job_dict = trans.security.encode_all_ids(job_dict)
            return JobImportHistoryResponse.parse_obj(job_dict)

        new_history = None
        # if a history id was passed, copy that history
        if copy_this_history_id:
            decoded_id = self.decode_id(copy_this_history_id)
            original_history = self.manager.get_accessible(decoded_id, trans.user, current_history=trans.history)
            hist_name = hist_name or (f"Copy of '{original_history.name}'")
            new_history = original_history.copy(
                name=hist_name, target_user=trans.user, all_datasets=payload.all_datasets
            )

        # otherwise, create a new empty history
        else:
            new_history = self.manager.create(user=trans.user, name=hist_name)

        trans.app.security_agent.history_set_default_permissions(new_history)
        trans.sa_session.add(new_history)
        trans.sa_session.flush()

        # an anonymous user can only have one history
        if self.user_manager.is_anonymous(trans.user):
            self.manager.set_current(trans, new_history)

        return self._serialize_history(trans, new_history, serialization_params)

    def create_from_store(
        self,
        trans,
        payload: CreateHistoryFromStore,
        serialization_params: SerializationParams,
    ) -> AnyHistoryView:
        self._ensure_can_create_history(trans)
        object_tracker = self.create_objects_from_store(
            trans,
            payload,
        )
        return self._serialize_history(trans, object_tracker.new_history, serialization_params)

    def create_from_store_async(
        self,
        trans,
        payload: CreateHistoryFromStore,
    ) -> AsyncTaskResultSummary:
        self._ensure_can_create_history(trans)
        source_uri = payload_to_source_uri(payload)
        request = ImportModelStoreTaskRequest(
            user=trans.async_request_user,
            source_uri=source_uri,
            for_library=False,
            model_store_format=payload.model_store_format,
        )
        result = import_model_store.delay(request=request)
        return async_task_summary(result)

    def _ensure_can_create_history(self, trans):
        if trans.anonymous:
            raise glx_exceptions.AuthenticationRequired("You need to be logged in to create histories.")
        if trans.user and trans.user.bootstrap_admin_user:
            raise glx_exceptions.RealUserRequiredException("Only real users can create histories.")

    def _save_upload_file_tmp(self, upload_file) -> str:
        try:
            suffix = Path(upload_file.filename).suffix
            with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                shutil.copyfileobj(upload_file.file, tmp)
                tmp_path = Path(tmp.name)
        finally:
            upload_file.file.close()
        return str(tmp_path)

    def show(
        self,
        trans: ProvidesHistoryContext,
        serialization_params: SerializationParams,
        history_id: Optional[EncodedDatabaseIdField] = None,
    ):
        """
        Returns detailed information about the history with the given encoded `id`. If no `id` is
        provided, then the most recently used history will be returned.

        :type   id:      an optional encoded id string
        :param  id:      the encoded id of the history to query or None to use the most recently used

        :type   serialization_params:   dictionary
        :param  serialization_params:   contains the optional `view`, `keys` and `default_view` for serialization

        :rtype:     dictionary
        :returns:   detailed history information
        """
        if history_id is None:  # By default display the most recent history
            history = self.manager.most_recent(
                trans.user, filters=(model.History.deleted == false()), current_history=trans.history
            )
        else:
            history = self.manager.get_accessible(self.decode_id(history_id), trans.user, current_history=trans.history)
        return self._serialize_history(trans, history, serialization_params)

    def prepare_download(
        self, trans: ProvidesHistoryContext, history_id: EncodedDatabaseIdField, payload: StoreExportPayload
    ) -> AsyncFile:
        history = self.manager.get_accessible(self.decode_id(history_id), trans.user, current_history=trans.history)
        short_term_storage_target = model_store_storage_target(
            self.short_term_storage_allocator,
            history.name,
            payload.model_store_format,
        )
        request = GenerateHistoryDownload(
            history_id=history.id,
            short_term_storage_request_id=short_term_storage_target.request_id,
            user=trans.async_request_user,
            **payload.dict(),
        )
        result = prepare_history_download.delay(request=request)
        return AsyncFile(storage_request_id=short_term_storage_target.request_id, task=async_task_summary(result))

    def write_store(
        self, trans: ProvidesHistoryContext, history_id: EncodedDatabaseIdField, payload: WriteStoreToPayload
    ) -> AsyncTaskResultSummary:
        history = self.manager.get_accessible(self.decode_id(history_id), trans.user, current_history=trans.history)
        request = WriteHistoryTo(user=trans.async_request_user, history_id=history.id, **payload.dict())
        result = write_history_to.delay(request=request)
        return async_task_summary(result)

    def update(
        self,
        trans: ProvidesHistoryContext,
        id: EncodedDatabaseIdField,
        payload,
        serialization_params: SerializationParams,
    ):
        """Updates the values for the history with the given ``id``

        :type   id:      str
        :param  id:      the encoded id of the history to update
        :type   payload: dict
        :param  payload: a dictionary containing any or all the
            fields in :func:`galaxy.model.History.to_dict` and/or the following:

            * annotation: an annotation for the history

        :type   serialization_params:   dictionary
        :param  serialization_params:   contains the optional `view`, `keys` and `default_view` for serialization

        :rtype:     dict
        :returns:   an error object if an error occurred or a dictionary containing
            any values that were different from the original and, therefore, updated
        """
        # TODO: PUT /api/histories/{encoded_history_id} payload = { rating: rating } (w/ no security checks)
        history = self.manager.get_owned(self.decode_id(id), trans.user, current_history=trans.history)
        self.deserializer.deserialize(history, payload, user=trans.user, trans=trans)
        return self._serialize_history(trans, history, serialization_params)

    def delete(
        self,
        trans: ProvidesHistoryContext,
        history_id: EncodedDatabaseIdField,
        serialization_params: SerializationParams,
        purge: bool = False,
    ):
        """Delete the history with the given ``id``

        .. note:: Stops all active jobs in the history if purge is set.

        You can purge a history, removing all it's datasets from disk (if unshared),
        by passing in ``purge=True`` in the url.

        :type   serialization_params:   dictionary
        :param  serialization_params:   contains the optional `view`, `keys` and `default_view` for serialization

        :rtype:     dict
        :returns:   the deleted or purged history
        """
        history = self.manager.get_owned(self.decode_id(history_id), trans.user, current_history=trans.history)
        if purge:
            self.manager.purge(history)
        else:
            self.manager.delete(history)
        return self._serialize_history(trans, history, serialization_params)

    def undelete(
        self,
        trans: ProvidesHistoryContext,
        history_id: EncodedDatabaseIdField,
        serialization_params: SerializationParams,
    ):
        """Undelete history (that hasn't been purged) with the given ``id``

        :type   id:     str
        :param  id:     the encoded id of the history to undelete

        :type   serialization_params:   dictionary
        :param  serialization_params:   contains the optional `view`, `keys` and `default_view` for serialization

        :rtype:     dict
        :returns:   the undeleted history
        """
        history = self.manager.get_owned(self.decode_id(history_id), trans.user, current_history=trans.history)
        self.manager.undelete(history)
        return self._serialize_history(trans, history, serialization_params)

    def shared_with_me(
        self,
        trans: ProvidesHistoryContext,
        serialization_params: SerializationParams,
        filter_query_params: FilterQueryParams,
    ):
        """
        Return all histories that are shared with the current user. The results can be filtered.
        """
        current_user = trans.user
        filters = self.filters.parse_query_filters(filter_query_params)
        order_by = self._build_order_by(filter_query_params.order)
        histories = self.manager.list_shared_with(
            current_user,
            filters=filters,
            order_by=order_by,
            limit=filter_query_params.limit,
            offset=filter_query_params.offset,
        )
        rval = [
            self._serialize_history(trans, history, serialization_params, default_view="summary")
            for history in histories
        ]
        return rval

    def published(
        self,
        trans: ProvidesHistoryContext,
        serialization_params: SerializationParams,
        filter_query_params: FilterQueryParams,
    ):
        """
        Return all histories that are published. The results can be filtered.
        """
        filters = self.filters.parse_query_filters(filter_query_params)
        order_by = self._build_order_by(filter_query_params.order)
        histories = self.manager.list_published(
            filters=filters,
            order_by=order_by,
            limit=filter_query_params.limit,
            offset=filter_query_params.offset,
        )
        rval = [
            self._serialize_history(trans, history, serialization_params, default_view="summary")
            for history in histories
        ]
        return rval

    def citations(self, trans: ProvidesHistoryContext, history_id: EncodedDatabaseIdField):
        """
        Return all the citations for the tools used to produce the datasets in
        the history.
        """
        history = self.manager.get_accessible(self.decode_id(history_id), trans.user, current_history=trans.history)
        tool_ids = set()
        for dataset in history.datasets:
            job = dataset.creating_job
            if not job:
                continue
            tool_id = job.tool_id
            if not tool_id:
                continue
            tool_ids.add(tool_id)
        return [citation.to_dict("bibtex") for citation in self.citations_manager.citations_for_tool_ids(tool_ids)]

    def index_exports(self, trans: ProvidesHistoryContext, id: EncodedDatabaseIdField):
        """
        Get previous history exports (to links). Effectively returns serialized
        JEHA objects.
        """
        return self.history_export_view.get_exports(trans, id)

    def archive_export(
        self,
        trans,
        id: EncodedDatabaseIdField,
        payload: Optional[ExportHistoryArchivePayload] = None,
    ) -> Tuple[HistoryArchiveExportResult, bool]:
        """
        start job (if needed) to create history export for corresponding
        history.

        :type   id:     str
        :param  id:     the encoded id of the history to export

        :rtype:     dict
        :returns:   object containing url to fetch export from.
        """
        if payload is None:
            payload = ExportHistoryArchivePayload()
        history = self.manager.get_accessible(self.decode_id(id), trans.user, current_history=trans.history)
        jeha = history.latest_export
        exporting_to_uri = payload.directory_uri
        # always just issue a new export when exporting to a URI.
        up_to_date = not payload.force and not exporting_to_uri and (jeha and jeha.up_to_date)
        job = None
        if not up_to_date:
            # Need to create new JEHA + job.
            job = self.manager.queue_history_export(
                trans,
                history,
                gzip=payload.gzip,
                include_hidden=payload.include_hidden,
                include_deleted=payload.include_deleted,
                directory_uri=payload.directory_uri,
                file_name=payload.file_name,
            )
        else:
            job = jeha.job

        ready = bool((up_to_date and jeha.ready) or exporting_to_uri)

        if exporting_to_uri:
            # we don't have a jeha, there will never be a download_url. Just let
            # the client poll on the created job_id to determine when the file has been
            # written.
            job_id = trans.security.encode_id(job.id)
            return (JobIdResponse(job_id=job_id), ready)

        if up_to_date and jeha.ready:
            serialized_jeha = self.history_export_view.serialize(trans, id, jeha)
            return (JobExportHistoryArchiveModel.parse_obj(serialized_jeha), ready)
        else:
            # Valid request, just resource is not ready yet.
            if jeha:
                serialized_jeha = self.history_export_view.serialize(trans, id, jeha)
                return (JobExportHistoryArchiveModel.parse_obj(serialized_jeha), ready)
            else:
                assert job is not None, "logic error, don't have a jeha or a job"
                job_id = trans.security.encode_id(job.id)
                return (JobIdResponse(job_id=job_id), ready)

    def get_ready_history_export(
        self,
        trans: ProvidesHistoryContext,
        id: EncodedDatabaseIdField,
        jeha_id: Union[EncodedDatabaseIdField, LatestLiteral],
    ) -> model.JobExportHistoryArchive:
        """Returns the exported history archive information if it's ready
        or raises an exception if not."""
        return self.history_export_view.get_ready_jeha(trans, id, jeha_id)

    def get_archive_download_path(
        self,
        trans: ProvidesHistoryContext,
        jeha: model.JobExportHistoryArchive,
    ) -> str:
        """
        If ready and available, return raw contents of exported history
        using a generator function.
        """
        return self.manager.get_ready_history_export_file_path(trans, jeha)

    def get_archive_media_type(self, jeha: model.JobExportHistoryArchive):
        media_type = "application/x-tar"
        if jeha.compressed:
            media_type = "application/x-gzip"
        return media_type

    # TODO: remove this function and HistoryManager.legacy_serve_ready_history_export when
    # removing the legacy HistoriesController
    def legacy_archive_download(
        self,
        trans: ProvidesHistoryContext,
        id: EncodedDatabaseIdField,
        jeha_id: EncodedDatabaseIdField,
    ):
        """
        If ready and available, return raw contents of exported history.
        """
        jeha = self.history_export_view.get_ready_jeha(trans, id, jeha_id)
        return self.manager.legacy_serve_ready_history_export(trans, jeha)

    def get_custom_builds_metadata(
        self,
        trans: ProvidesHistoryContext,
        id: EncodedDatabaseIdField,
    ) -> CustomBuildsMetadataResponse:
        """
        Returns metadata for custom builds.
        """
        history = self.manager.get_accessible(self.decode_id(id), trans.user, current_history=trans.history)
        installed_builds = []
        for build in glob.glob(os.path.join(trans.app.config.len_file_path, "*.len")):
            installed_builds.append(os.path.basename(build).split(".len")[0])
        fasta_hdas = (
            trans.sa_session.query(model.HistoryDatasetAssociation)
            .filter_by(history=history, extension="fasta", deleted=False)
            .order_by(model.HistoryDatasetAssociation.hid.desc())
        )
        return CustomBuildsMetadataResponse(
            installed_builds=[LabelValuePair(label=ins, value=ins) for ins in installed_builds],
            fasta_hdas=[
                LabelValuePair(label=f"{hda.hid}: {hda.name}", value=trans.security.encode_id(hda.id))
                for hda in fasta_hdas
            ],
        )

    def _serialize_history(
        self,
        trans: ProvidesHistoryContext,
        history: model.History,
        serialization_params: SerializationParams,
        default_view: str = "detailed",
    ) -> AnyHistoryView:
        """
        Returns a dictionary with the corresponding values depending on the
        serialization parameters provided.
        """
        serialization_params.default_view = default_view
        serialized_history = self.serializer.serialize_to_view(
            history, user=trans.user, trans=trans, **serialization_params.dict()
        )
        return serialized_history

    def _build_order_by(self, order: Optional[str]):
        return self.build_order_by(self.manager, order or DEFAULT_ORDER_BY)
