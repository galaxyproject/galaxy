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
    cast,
    List,
    Optional,
    Tuple,
    Union,
)

from sqlalchemy import (
    false,
    select,
    true,
)

from galaxy import (
    exceptions as glx_exceptions,
    model,
)
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
    HistoryExportManager,
    HistoryFilters,
    HistoryManager,
    HistorySerializer,
)
from galaxy.managers.users import UserManager
from galaxy.model import HistoryDatasetAssociation
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.model.store import payload_to_source_uri
from galaxy.schema import (
    FilterQueryParams,
    SerializationParams,
)
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.history import HistoryIndexQueryPayload
from galaxy.schema.schema import (
    AnyArchivedHistoryView,
    AnyHistoryView,
    ArchiveHistoryRequestPayload,
    AsyncFile,
    AsyncTaskResultSummary,
    CreateHistoryFromStore,
    CreateHistoryPayload,
    CustomBuildsMetadataResponse,
    ExportHistoryArchivePayload,
    ExportRecordData,
    HistoryArchiveExportResult,
    HistoryImportArchiveSourceType,
    JobExportHistoryArchiveModel,
    JobIdResponse,
    JobImportHistoryResponse,
    LabelValuePair,
    ShareHistoryWithStatus,
    ShareWithPayload,
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
from galaxy.short_term_storage import ShortTermStorageAllocator
from galaxy.util import restore_text
from galaxy.webapps.galaxy.services.base import (
    async_task_summary,
    ConsumesModelStores,
    model_store_storage_target,
    ServesExportStores,
    ServiceBase,
)
from galaxy.webapps.galaxy.services.notifications import NotificationService
from galaxy.webapps.galaxy.services.sharable import ShareableService

log = logging.getLogger(__name__)

DEFAULT_ORDER_BY = "create_time-dsc"


class ShareableHistoryService(ShareableService):
    share_with_status_cls = ShareHistoryWithStatus

    def share_with_users(self, trans, id: DecodedDatabaseIdField, payload: ShareWithPayload) -> ShareHistoryWithStatus:
        return cast(ShareHistoryWithStatus, super().share_with_users(trans, id, payload))


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
        history_export_manager: HistoryExportManager,
        filters: HistoryFilters,
        short_term_storage_allocator: ShortTermStorageAllocator,
        notification_service: NotificationService,
    ):
        super().__init__(security)
        self.manager = manager
        self.user_manager = user_manager
        self.serializer = serializer
        self.deserializer = deserializer
        self.citations_manager = citations_manager
        self.history_export_manager = history_export_manager
        self.filters = filters
        self.shareable_service = ShareableHistoryService(self.manager, self.serializer, notification_service)
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
        # exclude archived histories
        filters += [model.History.archived == false()]
        # and apply any other filters
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

    def index_query(
        self,
        trans,
        payload: HistoryIndexQueryPayload,
        serialization_params: SerializationParams,
        include_total_count: bool = False,
    ) -> Tuple[List[AnyHistoryView], Union[int, None]]:
        """Return a list of History accessible by the user

        :rtype:     list
        :returns:   dictionaries containing History details
        """
        entries, total_matches = self.manager.index_query(trans, payload, include_total_count)
        return (
            [self._serialize_history(trans, entry, serialization_params, default_view="summary") for entry in entries],
            total_matches,
        )

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
            job_dict["message"] = (
                f"Importing history from source '{archive_source}'. This history will be visible when the import is complete."
            )
            return JobImportHistoryResponse(**job_dict)

        new_history = None
        # if a history id was passed, copy that history
        if copy_this_history_id:
            original_history = self.manager.get_accessible(
                copy_this_history_id, trans.user, current_history=trans.history
            )
            hist_name = hist_name or (f"Copy of '{original_history.name}'")
            new_history = original_history.copy(
                name=hist_name, target_user=trans.user, all_datasets=payload.all_datasets
            )

        # otherwise, create a new empty history
        else:
            new_history = self.manager.create(user=trans.user, name=hist_name)

        trans.app.security_agent.history_set_default_permissions(new_history)
        trans.sa_session.add(new_history)
        trans.sa_session.commit()

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
        result = import_model_store.delay(request=request, task_user_id=getattr(trans.user, "id", None))
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
        history_id: Optional[DecodedDatabaseIdField] = None,
    ):
        """
        Returns detailed information about the history with the given encoded `id`. If no `id` is
        provided, then the most recently used history will be returned.

        :param  history_id:      the encoded id of the history to query or None to use the most recently used

        :param  serialization_params:   contains the optional `view`, `keys` and `default_view` for serialization

        :returns:   detailed history information
        """
        if history_id is None:  # By default display the most recent history
            history = self.manager.most_recent(
                trans.user, filters=(model.History.deleted == false()), current_history=trans.history
            )
        else:
            history = self.manager.get_accessible(history_id, trans.user, current_history=trans.history)
        return self._serialize_history(trans, history, serialization_params)

    def prepare_download(
        self, trans: ProvidesHistoryContext, history_id: DecodedDatabaseIdField, payload: StoreExportPayload
    ) -> AsyncFile:
        history = self.manager.get_accessible(history_id, trans.user, current_history=trans.history)
        short_term_storage_target = model_store_storage_target(
            self.short_term_storage_allocator,
            history.name,
            payload.model_store_format,
        )
        export_association = self.history_export_manager.create_export_association(history.id)
        request = GenerateHistoryDownload(
            history_id=history.id,
            short_term_storage_request_id=short_term_storage_target.request_id,
            duration=short_term_storage_target.duration,
            user=trans.async_request_user,
            export_association_id=export_association.id,
            **payload.dict(),
        )
        result = prepare_history_download.delay(request=request, task_user_id=getattr(trans.user, "id", None))
        task_summary = async_task_summary(result)
        export_association.task_uuid = task_summary.id
        trans.sa_session.commit()
        return AsyncFile(storage_request_id=short_term_storage_target.request_id, task=task_summary)

    def write_store(
        self, trans: ProvidesHistoryContext, history_id: DecodedDatabaseIdField, payload: WriteStoreToPayload
    ) -> AsyncTaskResultSummary:
        history = self.manager.get_accessible(history_id, trans.user, current_history=trans.history)
        export_association = self.history_export_manager.create_export_association(history.id)
        request = WriteHistoryTo(
            user=trans.async_request_user,
            history_id=history.id,
            export_association_id=export_association.id,
            **payload.dict(),
        )
        result = write_history_to.delay(request=request, task_user_id=getattr(trans.user, "id", None))
        task_summary = async_task_summary(result)
        export_association.task_uuid = task_summary.id
        trans.sa_session.commit()
        return task_summary

    def update(
        self,
        trans: ProvidesHistoryContext,
        history_id: DecodedDatabaseIdField,
        payload,
        serialization_params: SerializationParams,
    ):
        """Updates the values for the history with the given ``id``

        :param  history_id:      the encoded id of the history to update
        :param  payload: a dictionary containing any or all the
            fields in :func:`galaxy.model.History.to_dict` and/or the following:

            * annotation: an annotation for the history

        :param  serialization_params:   contains the optional `view`, `keys` and `default_view` for serialization

        :returns:   an error object if an error occurred or a dictionary containing
            any values that were different from the original and, therefore, updated
        """
        # TODO: PUT /api/histories/{encoded_history_id} payload = { rating: rating } (w/ no security checks)
        history = self.manager.get_mutable(history_id, trans.user, current_history=trans.history)
        self.deserializer.deserialize(history, payload, user=trans.user, trans=trans)
        return self._serialize_history(trans, history, serialization_params)

    def delete(
        self,
        trans: ProvidesHistoryContext,
        history_id: DecodedDatabaseIdField,
        serialization_params: SerializationParams,
        purge: bool = False,
    ):
        """Delete the history with the given ``id``

        .. note:: Stops all active jobs in the history if purge is set.

        You can purge a history, removing all it's datasets from disk (if unshared),
        by passing in ``purge=True`` in the url.
        """
        history = self.manager.get_mutable(history_id, trans.user, current_history=trans.history)
        if purge:
            self.manager.purge(history)
        else:
            self.manager.delete(history)
        return self._serialize_history(trans, history, serialization_params)

    def undelete(
        self,
        trans: ProvidesHistoryContext,
        history_id: DecodedDatabaseIdField,
        serialization_params: SerializationParams,
    ):
        """Undelete history (that hasn't been purged) with the given ``id``

        :param  history_id:     the encoded id of the history to undelete

        :param  serialization_params:   contains the optional `view`, `keys` and `default_view` for serialization

        :returns:   the undeleted history
        """
        history = self.manager.get_mutable(history_id, trans.user, current_history=trans.history)
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

    def count(
        self,
        trans: ProvidesHistoryContext,
    ):
        """
        Returns number of histories for the current user.
        """
        current_user = self.user_manager.current_user(trans)
        if self.user_manager.is_anonymous(current_user):
            current_history = self.manager.get_current(trans)
            return 1 if current_history else 0
        return self.manager.get_active_count(current_user)

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

    def citations(self, trans: ProvidesHistoryContext, history_id: DecodedDatabaseIdField):
        """
        Return all the citations for the tools used to produce the datasets in
        the history.
        """
        history = self.manager.get_accessible(history_id, trans.user, current_history=trans.history)
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

    def index_exports(
        self,
        trans: ProvidesHistoryContext,
        history_id: DecodedDatabaseIdField,
        use_tasks: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ):
        if use_tasks:
            return self.history_export_manager.get_task_exports(trans, history_id, limit, offset)
        return self.history_export_manager.get_exports(trans, history_id)

    def archive_export(
        self,
        trans,
        history_id: DecodedDatabaseIdField,
        payload: Optional[ExportHistoryArchivePayload] = None,
    ) -> Tuple[HistoryArchiveExportResult, bool]:
        """
        start job (if needed) to create history export for corresponding
        history.

        :param  history_id:     the encoded id of the history to export

        :returns:   object containing url to fetch export from.
        """
        if payload is None:
            payload = ExportHistoryArchivePayload()
        history = self.manager.get_accessible(history_id, trans.user, current_history=trans.history)
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
            return (JobIdResponse(job_id=job.id), ready)

        if up_to_date and jeha.ready:
            serialized_jeha = self.history_export_manager.serialize(trans, history_id, jeha)
            return (JobExportHistoryArchiveModel(**serialized_jeha), ready)
        else:
            # Valid request, just resource is not ready yet.
            if jeha:
                serialized_jeha = self.history_export_manager.serialize(trans, history_id, jeha)
                return (JobExportHistoryArchiveModel(**serialized_jeha), ready)
            else:
                assert job is not None, "logic error, don't have a jeha or a job"
                return (JobIdResponse(job_id=job.id), ready)

    def get_ready_history_export(
        self,
        trans: ProvidesHistoryContext,
        history_id: DecodedDatabaseIdField,
        jeha_id: Union[DecodedDatabaseIdField, LatestLiteral],
    ) -> model.JobExportHistoryArchive:
        """Returns the exported history archive information if it's ready
        or raises an exception if not."""
        return self.history_export_manager.get_ready_jeha(trans, history_id, jeha_id)

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
        history_id: DecodedDatabaseIdField,
        jeha_id: DecodedDatabaseIdField,
    ):
        """
        If ready and available, return raw contents of exported history.
        """
        jeha = self.history_export_manager.get_ready_jeha(trans, history_id, jeha_id)
        return self.manager.legacy_serve_ready_history_export(trans, jeha)

    def get_custom_builds_metadata(
        self,
        trans: ProvidesHistoryContext,
        history_id: DecodedDatabaseIdField,
    ) -> CustomBuildsMetadataResponse:
        """
        Returns metadata for custom builds.
        """
        history = self.manager.get_accessible(history_id, trans.user, current_history=trans.history)
        installed_builds = []
        for build in glob.glob(os.path.join(trans.app.config.len_file_path, "*.len")):
            installed_builds.append(os.path.basename(build).split(".len")[0])
        fasta_hdas = get_fasta_hdas_by_history(trans.sa_session, history.id)
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
    ):
        """
        Returns a dictionary with the corresponding values depending on the
        serialization parameters provided.
        """
        serialization_params.default_view = default_view
        serialized_history = self.serializer.serialize_to_view(
            history, user=trans.user, trans=trans, encode_id=False, **serialization_params.model_dump()
        )
        return serialized_history

    def _build_order_by(self, order: Optional[str]):
        return self.build_order_by(self.manager, order or DEFAULT_ORDER_BY)

    def archive_history(
        self,
        trans: ProvidesHistoryContext,
        history_id: DecodedDatabaseIdField,
        payload: Optional[ArchiveHistoryRequestPayload] = None,
    ) -> AnyArchivedHistoryView:
        """Marks the history with the given id as archived and optionally associates it with the given archive export record in the payload.

        Archived histories are not part of the active histories of the user, so they won't be shown to the user by default.
        """
        if trans.anonymous:
            raise glx_exceptions.AuthenticationRequired("Only registered users can archive histories.")

        history = self.manager.get_owned(history_id, trans.user)
        if history.archived:
            raise glx_exceptions.Conflict("History is already archived.")

        archive_export_id = payload.archive_export_id if payload else None
        if archive_export_id:
            export_record = self.history_export_manager.get_task_export_by_id(archive_export_id)
            self._ensure_export_record_can_be_associated_with_history_archival(history_id, export_record)
            # After this point, the export record is valid and can be associated with the history archival
        purge_history = payload.purge_history if payload else False
        if purge_history:
            if archive_export_id is None:
                raise glx_exceptions.RequestParameterMissingException(
                    "Cannot purge history without an export record. A valid archive_export_id is required."
                )
            self.manager.purge(history)
        history = self.manager.archive_history(history, archive_export_id=archive_export_id)
        return self._serialize_archived_history(trans, history)

    def _ensure_export_record_can_be_associated_with_history_archival(
        self, history_id: int, export_record: model.StoreExportAssociation
    ):
        if export_record.object_id != history_id or export_record.object_type != "history":
            raise glx_exceptions.RequestParameterInvalidException(
                "The given archive export record does not belong to this history."
            )
        export_metadata = self.history_export_manager.get_record_metadata(export_record)
        if export_metadata is None:
            log.error(
                f"Trying to archive history [{history_id}] with an export record. "
                f"But the given archive export record [{export_record.id}] does not have the required metadata."
            )
            raise glx_exceptions.RequestParameterInvalidException(
                "The given archive export record does not have the required metadata."
            )
        if not export_metadata.is_ready():
            raise glx_exceptions.RequestParameterInvalidException(
                "The given archive export record must be ready before it can be used to archive a history. "
                "Please wait for the export to finish and try again."
            )
        if export_metadata.is_short_term():
            raise glx_exceptions.RequestParameterInvalidException(
                "The given archive export record is temporal, only persistent sources can be used to archive a history."
            )
        # TODO: should we also ensure the export was requested to include files with `include_files`, `include_hidden`, etc.?

    def restore_archived_history(
        self,
        trans: ProvidesHistoryContext,
        history_id: DecodedDatabaseIdField,
        force: Optional[bool] = False,
    ) -> AnyHistoryView:
        if trans.anonymous:
            raise glx_exceptions.AuthenticationRequired("Only registered users can access archived histories.")

        history = self.manager.get_owned(history_id, trans.user)
        history = self.manager.restore_archived_history(history, force=force or False)
        return self._serialize_archived_history(trans, history)

    def get_archived_histories(
        self,
        trans: ProvidesHistoryContext,
        serialization_params: SerializationParams,
        filter_query_params: FilterQueryParams,
        include_total_matches: bool = False,
    ) -> Tuple[List[AnyArchivedHistoryView], Optional[int]]:
        if trans.anonymous:
            raise glx_exceptions.AuthenticationRequired("Only registered users can have or access archived histories.")

        filters = self.filters.parse_query_filters(filter_query_params)
        filters += [
            model.History.user == trans.user,
            model.History.archived == true(),
        ]
        total_matches = self.manager.count(filters=filters) if include_total_matches else None
        order_by = self._build_order_by(filter_query_params.order)
        histories = self.manager.list(
            filters=filters, order_by=order_by, limit=filter_query_params.limit, offset=filter_query_params.offset
        )

        histories = [
            self._serialize_archived_history(trans, history, serialization_params, default_view="summary")
            for history in histories
        ]
        return histories, total_matches

    def _serialize_archived_history(
        self,
        trans: ProvidesHistoryContext,
        history: model.History,
        serialization_params: Optional[SerializationParams] = None,
        default_view: str = "detailed",
    ):
        if serialization_params is None:
            serialization_params = SerializationParams()
        archived_history = self._serialize_history(trans, history, serialization_params, default_view)
        export_record_data = self._get_export_record_data(history)
        archived_history["export_record_data"] = export_record_data
        return archived_history

    def _get_export_record_data(self, history: model.History) -> Optional[ExportRecordData]:
        if history.archive_export_id:
            export_record = self.history_export_manager.get_task_export_by_id(history.archive_export_id)
            export_metadata = self.history_export_manager.get_record_metadata(export_record)
            if export_metadata and isinstance(
                request_data_payload := export_metadata.request_data.payload, WriteStoreToPayload
            ):
                request_uri = request_data_payload.target_uri
                result_uri = export_metadata.result_data.uri if export_metadata.result_data else None

                export_record_data_dict = request_data_payload.model_dump()
                export_record_data_dict.update({"target_uri": result_uri or request_uri})
                export_record_data = ExportRecordData(**export_record_data_dict)

                return export_record_data
        return None


def get_fasta_hdas_by_history(session: galaxy_scoped_session, history_id: int):
    stmt = (
        select(HistoryDatasetAssociation)
        .filter_by(history_id=history_id, extension="fasta", deleted=False)
        .order_by(HistoryDatasetAssociation.hid.desc())
    )
    return session.scalars(stmt).all()
