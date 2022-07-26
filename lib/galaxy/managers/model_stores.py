from typing import Optional

from galaxy import model
from galaxy.exceptions import RequestParameterInvalidException
from galaxy.jobs.manager import JobManager
from galaxy.managers.histories import HistoryManager
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.model.store import (
    ImportDiscardedDataType,
    ImportOptions,
    ObjectImportTracker,
    source_to_import_store,
)
from galaxy.schema.schema import HistoryContentType
from galaxy.schema.tasks import (
    GenerateHistoryContentDownload,
    GenerateHistoryDownload,
    GenerateInvocationDownload,
    ImportModelStoreTaskRequest,
    SetupHistoryExportJob,
    WriteHistoryContentTo,
    WriteHistoryTo,
    WriteInvocationTo,
)
from galaxy.structured_app import MinimalManagerApp
from galaxy.web.short_term_storage import (
    ShortTermStorageMonitor,
    storage_context,
)


class ModelStoreManager:
    def __init__(
        self,
        app: MinimalManagerApp,
        history_manager: HistoryManager,
        sa_session: galaxy_scoped_session,
        job_manager: JobManager,
        short_term_storage_monitor: ShortTermStorageMonitor,
    ):
        self._app = app
        self._sa_session = sa_session
        self._job_manager = job_manager
        self._history_manager = history_manager
        self._short_term_storage_monitor = short_term_storage_monitor

    def setup_history_export_job(self, request: SetupHistoryExportJob):
        history_id = request.history_id
        job_id = request.job_id
        include_hidden = request.include_hidden
        include_deleted = request.include_deleted
        store_directory = request.store_directory

        history = self._sa_session.query(model.History).get(history_id)
        # symlink files on export, on worker files will tarred up in a dereferenced manner.
        with model.store.DirectoryModelExportStore(
            store_directory, app=self._app, export_files="symlink"
        ) as export_store:
            export_store.export_history(history, include_hidden=include_hidden, include_deleted=include_deleted)
        job = self._sa_session.query(model.Job).get(job_id)
        job.state = model.Job.states.NEW
        self._sa_session.flush()
        self._job_manager.enqueue(job)

    def prepare_history_download(self, request: GenerateHistoryDownload):
        model_store_format = request.model_store_format
        history = self._history_manager.by_id(request.history_id)
        export_files = "symlink" if request.include_files else None
        include_hidden = request.include_hidden
        include_deleted = request.include_deleted
        with storage_context(
            request.short_term_storage_request_id, self._short_term_storage_monitor
        ) as short_term_storage_target:
            with model.store.get_export_store_factory(self._app, model_store_format, export_files=export_files)(
                short_term_storage_target.path
            ) as export_store:
                export_store.export_history(history, include_hidden=include_hidden, include_deleted=include_deleted)

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
                    hda = self._sa_session.query(model.HistoryDatasetAssociation).get(request.content_id)
                    export_store.add_dataset(hda)
                else:
                    hdca = self._sa_session.query(model.HistoryDatasetCollectionAssociation).get(request.content_id)
                    export_store.export_collection(
                        hdca, include_hidden=request.include_hidden, include_deleted=request.include_deleted
                    )

    def prepare_invocation_download(self, request: GenerateInvocationDownload):
        model_store_format = request.model_store_format
        export_files = "symlink" if request.include_files else None
        with storage_context(
            request.short_term_storage_request_id, self._short_term_storage_monitor
        ) as short_term_storage_target:
            with model.store.get_export_store_factory(self._app, model_store_format, export_files=export_files)(
                short_term_storage_target.path
            ) as export_store:
                invocation = self._sa_session.query(model.WorkflowInvocation).get(request.invocation_id)
                export_store.export_workflow_invocation(
                    invocation, include_hidden=request.include_hidden, include_deleted=request.include_deleted
                )

    def write_invocation_to(self, request: WriteInvocationTo):
        model_store_format = request.model_store_format
        export_files = "symlink" if request.include_files else None
        target_uri = request.target_uri
        with model.store.get_export_store_factory(self._app, model_store_format, export_files=export_files)(
            target_uri
        ) as export_store:
            invocation = self._sa_session.query(model.WorkflowInvocation).get(request.invocation_id)
            export_store.export_workflow_invocation(
                invocation, include_hidden=request.include_hidden, include_deleted=request.include_deleted
            )

    def write_history_content_to(self, request: WriteHistoryContentTo):
        model_store_format = request.model_store_format
        export_files = "symlink" if request.include_files else None
        target_uri = request.target_uri
        with model.store.get_export_store_factory(self._app, model_store_format, export_files=export_files)(
            target_uri
        ) as export_store:
            if request.content_type == HistoryContentType.dataset:
                hda = self._sa_session.query(model.HistoryDatasetAssociation).get(request.content_id)
                export_store.add_dataset(hda)
            else:
                hdca = self._sa_session.query(model.HistoryDatasetCollectionAssociation).get(request.content_id)
                export_store.export_collection(
                    hdca, include_hidden=request.include_hidden, include_deleted=request.include_deleted
                )

    def write_history_to(self, request: WriteHistoryTo):
        model_store_format = request.model_store_format
        export_files = "symlink" if request.include_files else None
        target_uri = request.target_uri
        with model.store.get_export_store_factory(self._app, model_store_format, export_files=export_files)(
            target_uri
        ) as export_store:
            history = self._history_manager.by_id(request.history_id)
            export_store.export_history(
                history, include_hidden=request.include_hidden, include_deleted=request.include_deleted
            )

    def import_model_store(self, request: ImportModelStoreTaskRequest):
        import_options = ImportOptions(
            discarded_data=ImportDiscardedDataType.FORCE,
            allow_library_creation=request.for_library,
        )
        history_id = request.history_id
        if history_id:
            history = self._sa_session.query(model.History).get(history_id)
        else:
            history = None
        user_id = request.user.user_id
        if user_id:
            galaxy_user = self._sa_session.query(model.User).get(user_id)
        else:
            galaxy_user = None
        model_import_store = source_to_import_store(
            request.source_uri,
            self._app,
            galaxy_user,
            import_options,
        )
        new_history = history is None and not request.for_library
        if new_history:
            if not model_import_store.defines_new_history():
                raise RequestParameterInvalidException("Supplied model store doesn't define new history to import.")
            with model_import_store.target_history(legacy_history_naming=False) as new_history:
                object_tracker = model_import_store.perform_import(new_history, new_history=True)
                object_tracker.new_history = new_history
        else:
            object_tracker = model_import_store.perform_import(
                history=history,
                new_history=new_history,
            )
        return object_tracker


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
    model_import_store = source_to_import_store(
        payload.store_content_uri or payload.store_dict,
        app=app,
        galaxy_user=galaxy_user,
        import_options=import_options,
        model_store_format=payload.model_store_format,
    )
    new_history = history is None and not for_library
    if new_history:
        if not model_import_store.defines_new_history():
            raise RequestParameterInvalidException("Supplied model store doesn't define new history to import.")
        with model_import_store.target_history(legacy_history_naming=False) as new_history:
            object_tracker = model_import_store.perform_import(new_history, new_history=True)
            object_tracker.new_history = new_history
    else:
        object_tracker = model_import_store.perform_import(
            history=history,
            new_history=new_history,
        )
    return object_tracker
