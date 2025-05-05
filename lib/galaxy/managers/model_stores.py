from typing import (
    Optional,
    Union,
)

from galaxy import model
from galaxy.exceptions import RequestParameterInvalidException
from galaxy.jobs.manager import JobManager
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.export_tracker import StoreExportTracker
from galaxy.managers.histories import HistoryManager
from galaxy.managers.users import UserManager
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.model.store import (
    DirectoryModelExportStore,
    ImportDiscardedDataType,
    ImportOptions,
    ObjectImportTracker,
    source_to_import_store,
)
from galaxy.schema.schema import (
    ExportObjectMetadata,
    ExportObjectRequestMetadata,
    ExportObjectResultMetadata,
    ExportObjectType,
    HistoryContentType,
    ShortTermStoreExportPayload,
    WriteStoreToPayload,
)
from galaxy.schema.tasks import (
    BcoGenerationTaskParametersMixin,
    GenerateHistoryContentDownload,
    GenerateHistoryDownload,
    GenerateInvocationDownload,
    ImportModelStoreTaskRequest,
    SetupHistoryExportJob,
    WriteHistoryContentTo,
    WriteHistoryTo,
    WriteInvocationTo,
)
from galaxy.short_term_storage import (
    ShortTermStorageMonitor,
    storage_context,
)
from galaxy.structured_app import MinimalManagerApp
from galaxy.version import VERSION


class ModelStoreUserContext(ProvidesUserContext):
    def __init__(self, app: MinimalManagerApp, user: model.User) -> None:
        self._app = app
        self._user = user

    @property
    def app(self):
        return self._app

    @property
    def url_builder(self):
        raise NotImplementedError("URL builder not available in ModelStore context.")

    def get_user(self):
        return self._user

    def set_user(self, user):
        raise NotImplementedError("Cannot change user from ModelStore context.")

    user = property(get_user, set_user)


class ModelStoreManager:
    def __init__(
        self,
        app: MinimalManagerApp,
        history_manager: HistoryManager,
        export_tracker: StoreExportTracker,
        sa_session: galaxy_scoped_session,
        job_manager: JobManager,
        short_term_storage_monitor: ShortTermStorageMonitor,
        user_manager: UserManager,
    ):
        self._app = app
        self._sa_session = sa_session
        self._job_manager = job_manager
        self._history_manager = history_manager
        self._export_tracker = export_tracker
        self._short_term_storage_monitor = short_term_storage_monitor
        self._user_manager = user_manager

    def setup_history_export_job(self, request: SetupHistoryExportJob):
        history_id = request.history_id
        job_id = request.job_id
        include_hidden = request.include_hidden
        include_deleted = request.include_deleted
        store_directory = request.store_directory

        history = self._sa_session.get(model.History, history_id)
        assert history
        # symlink files on export, on worker files will tarred up in a dereferenced manner.
        with DirectoryModelExportStore(store_directory, app=self._app, export_files="symlink") as export_store:
            export_store.export_history(history, include_hidden=include_hidden, include_deleted=include_deleted)
        job = self._sa_session.get(model.Job, job_id)
        assert job
        job.state = model.Job.states.NEW
        self._sa_session.commit()
        self._job_manager.enqueue(job)

    def prepare_history_download(self, request: GenerateHistoryDownload):
        model_store_format = request.model_store_format
        history = self._history_manager.by_id(request.history_id)
        export_files = "symlink" if request.include_files else None
        include_hidden = request.include_hidden
        include_deleted = request.include_deleted
        export_metadata = self.set_history_export_request_metadata(request)

        exception_exporting_history: Optional[Exception] = None
        try:
            with storage_context(
                request.short_term_storage_request_id, self._short_term_storage_monitor
            ) as short_term_storage_target:
                with model.store.get_export_store_factory(self._app, model_store_format, export_files=export_files)(
                    short_term_storage_target.path
                ) as export_store:
                    export_store.export_history(history, include_hidden=include_hidden, include_deleted=include_deleted)
        except Exception as exception:
            exception_exporting_history = exception
            raise
        finally:
            self.set_history_export_result_metadata(
                request.export_association_id,
                export_metadata,
                success=not bool(exception_exporting_history),
                error=str(exception_exporting_history) if exception_exporting_history else None,
            )

    def prepare_history_content_download(self, request: GenerateHistoryContentDownload):
        model_store_format = request.model_store_format
        export_files = "symlink" if request.include_files else None
        with storage_context(
            request.short_term_storage_request_id, self._short_term_storage_monitor
        ) as short_term_storage_target:
            with model.store.get_export_store_factory(self._app, model_store_format, export_files=export_files)(
                short_term_storage_target.path
            ) as export_store:
                if request.content_type == HistoryContentType.dataset:
                    hda = self._sa_session.get(model.HistoryDatasetAssociation, request.content_id)
                    export_store.add_dataset(hda)  # type: ignore[arg-type]
                else:
                    hdca = self._sa_session.get(model.HistoryDatasetCollectionAssociation, request.content_id)
                    export_store.export_collection(
                        hdca,  # type: ignore[arg-type]
                        include_hidden=request.include_hidden,
                        include_deleted=request.include_deleted,
                    )

    def prepare_invocation_download(self, request: GenerateInvocationDownload):
        model_store_format = request.model_store_format
        export_files = "symlink" if request.include_files else None
        with storage_context(
            request.short_term_storage_request_id, self._short_term_storage_monitor
        ) as short_term_storage_target:
            with model.store.get_export_store_factory(
                self._app,
                model_store_format,
                export_files=export_files,
                bco_export_options=self._bco_export_options(request),
            )(short_term_storage_target.path) as export_store:
                invocation = self._sa_session.get(model.WorkflowInvocation, request.invocation_id)
                export_store.export_workflow_invocation(
                    invocation,  # type: ignore[arg-type]
                    include_hidden=request.include_hidden,
                    include_deleted=request.include_deleted,
                )

    def write_invocation_to(self, request: WriteInvocationTo):
        model_store_format = request.model_store_format
        export_files = "symlink" if request.include_files else None
        target_uri = request.target_uri
        user_context = self._build_user_context(request.user.user_id)
        with model.store.get_export_store_factory(
            self._app,
            model_store_format,
            export_files=export_files,
            bco_export_options=self._bco_export_options(request),
            user_context=user_context,
        )(target_uri) as export_store:
            invocation = self._sa_session.get(model.WorkflowInvocation, request.invocation_id)
            export_store.export_workflow_invocation(
                invocation,  # type: ignore[arg-type]
                include_hidden=request.include_hidden,
                include_deleted=request.include_deleted,
            )

    def _bco_export_options(self, request: BcoGenerationTaskParametersMixin):
        return model.store.BcoExportOptions(
            galaxy_url=request.galaxy_url,
            galaxy_version=VERSION,
            merge_history_metadata=request.bco_merge_history_metadata,
            override_environment_variables=request.bco_override_environment_variables,
            override_empirical_error=request.bco_override_empirical_error,
            override_algorithmic_error=request.bco_override_algorithmic_error,
            override_xref=request.bco_override_xref,
        )

    def write_history_content_to(self, request: WriteHistoryContentTo):
        model_store_format = request.model_store_format
        export_files = "symlink" if request.include_files else None
        target_uri = request.target_uri
        user_context = self._build_user_context(request.user.user_id)
        with model.store.get_export_store_factory(
            self._app, model_store_format, export_files=export_files, user_context=user_context
        )(target_uri) as export_store:
            if request.content_type == HistoryContentType.dataset:
                hda = self._sa_session.get(model.HistoryDatasetAssociation, request.content_id)
                export_store.add_dataset(hda)  # type: ignore[arg-type]
            else:
                hdca = self._sa_session.get(model.HistoryDatasetCollectionAssociation, request.content_id)
                export_store.export_collection(
                    hdca,  # type: ignore[arg-type]
                    include_hidden=request.include_hidden,
                    include_deleted=request.include_deleted,
                )

    def write_history_to(self, request: WriteHistoryTo):
        model_store_format = request.model_store_format
        export_files = "symlink" if request.include_files else None
        user_context = self._build_user_context(request.user.user_id)
        export_metadata = self.set_history_export_request_metadata(request)

        exception_exporting_history: Optional[Exception] = None
        uri: Optional[str] = None
        try:
            export_store = model.store.get_export_store_factory(
                self._app, model_store_format, export_files=export_files, user_context=user_context
            )(request.target_uri)
            with export_store:
                history = self._history_manager.by_id(request.history_id)
                export_store.export_history(
                    history, include_hidden=request.include_hidden, include_deleted=request.include_deleted
                )
            uri = str(export_store.file_source_uri) if export_store.file_source_uri else request.target_uri
        except Exception as exception:
            exception_exporting_history = exception
            raise
        finally:
            self.set_history_export_result_metadata(
                request.export_association_id,
                export_metadata,
                success=not bool(exception_exporting_history),
                uri=uri,
                error=str(exception_exporting_history) if exception_exporting_history else None,
            )

    def set_history_export_request_metadata(
        self, request: Union[WriteHistoryTo, GenerateHistoryDownload]
    ) -> Optional[ExportObjectMetadata]:
        if request.export_association_id is None:
            return None
        request_dict = request.model_dump()
        request_payload = (
            WriteStoreToPayload(**request_dict)
            if isinstance(request, WriteHistoryTo)
            else ShortTermStoreExportPayload(**request_dict)
        )
        export_metadata = ExportObjectMetadata(
            request_data=ExportObjectRequestMetadata(
                object_id=request.history_id,
                object_type=ExportObjectType.HISTORY,
                user_id=request.user.user_id,
                payload=request_payload,
            ),
        )
        self._export_tracker.set_export_association_metadata(request.export_association_id, export_metadata)
        return export_metadata

    def set_history_export_result_metadata(
        self,
        export_association_id: Optional[int],
        export_metadata: Optional[ExportObjectMetadata],
        success: bool,
        uri: Optional[str] = None,
        error: Optional[str] = None,
    ):
        if export_association_id is not None and export_metadata is not None:
            export_metadata.result_data = ExportObjectResultMetadata(success=success, uri=uri, error=error)
            self._export_tracker.set_export_association_metadata(export_association_id, export_metadata)

    def import_model_store(self, request: ImportModelStoreTaskRequest):
        import_options = ImportOptions(
            allow_library_creation=request.for_library,
        )
        if history_id := request.history_id:
            history = self._sa_session.get(model.History, history_id)
        else:
            history = None
        user_context = self._build_user_context(request.user.user_id)
        model_import_store = source_to_import_store(
            request.source_uri,
            self._app,
            import_options,
            model_store_format=request.model_store_format,
            user_context=user_context,
        )
        create_new_history = history is None and not request.for_library
        if create_new_history:
            if not model_import_store.defines_new_history():
                raise RequestParameterInvalidException("Supplied model store doesn't define new history to import.")
            with model_import_store.target_history(legacy_history_naming=False) as new_history:
                object_tracker = model_import_store.perform_import(new_history, new_history=True)
                object_tracker.new_history = new_history
        else:
            object_tracker = model_import_store.perform_import(
                history=history,
                new_history=create_new_history,
            )
        return object_tracker

    def _build_user_context(self, user_id: int):
        user = self._user_manager.by_id(user_id)
        assert user is not None
        user_context = ModelStoreUserContext(self._app, user)
        return user_context


def create_objects_from_store(
    app: MinimalManagerApp,
    galaxy_user: Optional[model.User],
    payload,
    history: Optional[model.History] = None,
    for_library: bool = False,
) -> ObjectImportTracker:
    import_options = ImportOptions(
        discarded_data=ImportDiscardedDataType.FORCE,
        allow_library_creation=for_library,
    )
    user_context = ModelStoreUserContext(app, galaxy_user) if galaxy_user is not None else None
    model_import_store = source_to_import_store(
        payload.store_content_uri or payload.store_dict,
        app=app,
        import_options=import_options,
        model_store_format=payload.model_store_format,
        user_context=user_context,
    )
    create_new_history = history is None and not for_library
    if create_new_history:
        if not model_import_store.defines_new_history():
            raise RequestParameterInvalidException("Supplied model store doesn't define new history to import.")
        with model_import_store.target_history(legacy_history_naming=False) as new_history:
            object_tracker = model_import_store.perform_import(new_history, new_history=True)
            object_tracker.new_history = new_history
    else:
        object_tracker = model_import_store.perform_import(
            history=history,
            new_history=create_new_history,
        )
    return object_tracker
