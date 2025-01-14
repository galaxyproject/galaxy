"""
Manager and Serializer for histories.

Histories are containers for datasets or dataset collections
created (or copied) by users over the course of an analysis.
"""

import logging
from typing import (
    Any,
    cast,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

from sqlalchemy import (
    asc,
    desc,
    exists,
    false,
    func,
    or_,
    select,
    true,
)
from sqlalchemy.orm import aliased
from typing_extensions import Literal

from galaxy import model
from galaxy.exceptions import (
    MessageException,
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.managers import (
    deletable,
    hdas,
    history_contents,
    sharable,
)
from galaxy.managers.base import (
    combine_lists,
    ModelDeserializingError,
    Serializer,
    SortableManager,
    StorageCleanerManager,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.export_tracker import StoreExportTracker
from galaxy.model import (
    History,
    HistoryUserShareAssociation,
    Job,
)
from galaxy.model.index_filter_util import (
    append_user_filter,
    raw_text_column_filter,
    tag_filter,
    text_column_filter,
)
from galaxy.schema.fields import Security
from galaxy.schema.history import HistoryIndexQueryPayload
from galaxy.schema.schema import (
    ExportObjectMetadata,
    ExportObjectType,
    HDABasicInfo,
    ShareHistoryExtra,
)
from galaxy.schema.storage_cleaner import (
    CleanableItemsSummary,
    StorageItemCleanupError,
    StorageItemsCleanupResult,
    StoredItem,
    StoredItemOrderBy,
)
from galaxy.security.validate_user_input import validate_preferred_object_store_id
from galaxy.structured_app import MinimalManagerApp
from galaxy.util.search import (
    FilteredTerm,
    parse_filters_structured,
    RawTextTerm,
)

log = logging.getLogger(__name__)

INDEX_SEARCH_FILTERS = {
    "name": "name",
    "user": "user",
    "tag": "tag",
    "is": "is",
}


class HistoryManager(sharable.SharableModelManager, deletable.PurgableManagerMixin, SortableManager):
    model_class = model.History
    foreign_key_name = "history"
    user_share_model = model.HistoryUserShareAssociation

    tag_assoc = model.HistoryTagAssociation
    annotation_assoc = model.HistoryAnnotationAssociation
    rating_assoc = model.HistoryRatingAssociation

    # TODO: incorporate imp/exp (or alias to)

    def __init__(
        self,
        app: MinimalManagerApp,
        hda_manager: hdas.HDAManager,
        contents_manager: history_contents.HistoryContentsManager,
        contents_filters: history_contents.HistoryContentsFilters,
    ) -> None:
        super().__init__(app)
        self.hda_manager = hda_manager
        self.contents_manager = contents_manager
        self.contents_filters = contents_filters

    def index_query(
        self, trans: ProvidesUserContext, payload: HistoryIndexQueryPayload, include_total_count: bool = False
    ) -> Tuple[List[model.History], int]:
        show_deleted = False
        show_own = payload.show_own
        show_published = payload.show_published
        show_purged = False
        show_shared = payload.show_shared
        show_archived = payload.show_archived
        is_admin = trans.user_is_admin
        user = trans.user

        if not user and not show_published:
            message = "Requires user to log in."
            raise RequestParameterInvalidException(message)

        stmt = select(self.model_class).outerjoin(model.User)

        filters = []
        if show_own or (not show_published and not show_shared and not is_admin):
            filters = [self.model_class.user == user]
        if show_published:
            filters.append(self.model_class.published == true())
        if show_shared:
            filters.append(self.user_share_model.user == user)
            stmt = stmt.outerjoin(self.model_class.users_shared_with)
        stmt = stmt.where(or_(*filters))

        if payload.search:
            search_query = payload.search
            parsed_search = parse_filters_structured(search_query, INDEX_SEARCH_FILTERS)

            def p_tag_filter(term_text: str, quoted: bool):
                nonlocal stmt
                alias = aliased(model.HistoryTagAssociation)
                stmt = stmt.outerjoin(self.model_class.tags.of_type(alias))
                return tag_filter(alias, term_text, quoted)

            for term in parsed_search.terms:
                if isinstance(term, FilteredTerm):
                    key = term.filter
                    q = term.text
                    if key == "tag":
                        pg = p_tag_filter(term.text, term.quoted)
                        stmt = stmt.where(pg)
                    elif key == "name":
                        stmt = stmt.where(text_column_filter(self.model_class.name, term))
                    elif key == "user":
                        stmt = append_user_filter(stmt, self.model_class, term)
                    elif key == "is":
                        if q == "deleted":
                            show_deleted = True
                        elif q == "importable":
                            stmt = stmt.where(self.model_class.importable == true())
                        elif q == "published":
                            stmt = stmt.where(self.model_class.published == true())
                        elif q == "purged":
                            show_purged = True
                        elif q == "shared_with_me":
                            if not show_shared:
                                message = "Can only use tag is:shared_with_me if show_shared parameter also true."
                                raise RequestParameterInvalidException(message)
                            stmt = stmt.where(self.user_share_model.user == user)
                elif isinstance(term, RawTextTerm):
                    tf = p_tag_filter(term.text, False)
                    alias = aliased(model.User)
                    stmt = stmt.outerjoin(self.model_class.user.of_type(alias))
                    stmt = stmt.where(
                        raw_text_column_filter(
                            [
                                self.model_class.name,
                                tf,
                                alias.username,
                            ],
                            term,
                        )
                    )

        if (show_published or show_shared) and not is_admin:
            show_deleted = False
            show_purged = False

        if show_purged:
            stmt = stmt.where(self.model_class.purged == true())
        else:
            stmt = stmt.where(self.model_class.purged == false()).where(
                self.model_class.deleted == (true() if show_deleted else false())
            )

        # By default, return only non-archived histories when we are showing the current user's histories
        # if listing other users' histories, we don't filter out archived histories as they may be
        # public or shared with the current user
        if show_own and not show_archived:
            stmt = stmt.where(self.model_class.archived == false())

        stmt = stmt.distinct()

        if include_total_count:
            total_matches = get_count(trans.sa_session, stmt)
        else:
            total_matches = None

        sort_column: Any
        if payload.sort_by == "username":
            sort_column = model.User.username
            stmt = stmt.add_columns(sort_column)
        else:
            sort_column = getattr(model.History, payload.sort_by)
        if payload.sort_desc:
            sort_column = sort_column.desc()
        stmt = stmt.order_by(sort_column)

        if payload.limit is not None:
            stmt = stmt.limit(payload.limit)
        if payload.offset is not None:
            stmt = stmt.offset(payload.offset)
        return trans.sa_session.scalars(stmt), total_matches  # type:ignore[return-value]

    # .... sharable
    # overriding to handle anonymous users' current histories in both cases
    def by_user(
        self, user: model.User, current_history: Optional[model.History] = None, **kwargs: Any
    ) -> List[model.History]:
        """
        Get all the histories for a given user (allowing anon users' theirs)
        ordered by update time.
        """
        # handle default and/or anonymous user (which still may not have a history yet)
        if self.user_manager.is_anonymous(user):
            return [current_history] if current_history else []
        return super().by_user(user, **kwargs)

    def is_owner(
        self,
        item: model.Base,
        user: Optional[model.User],
        current_history: Optional[model.History] = None,
        **kwargs: Any,
    ) -> bool:
        """
        True if the current user is the owner of the given history.
        """
        # anon users are only allowed to view their current history
        if self.user_manager.is_anonymous(user):
            return current_history is not None and item == current_history
        return super().is_owner(item, user)

    # TODO: possibly to sharable or base
    def most_recent(self, user, filters=None, current_history=None):
        """
        Return the most recently update history for the user.

        If user is anonymous, return the current history. If the user is anonymous
        and the current history is deleted, return None.
        """
        if self.user_manager.is_anonymous(user):
            return None if (not current_history or current_history.deleted) else current_history
        filters = combine_lists(filters, History.user_id == user.id)
        stmt = select(History).where(*filters).order_by(History.update_time.desc()).limit(1)
        return self.session().scalars(stmt).first()

    # .... purgable
    def purge(self, item, flush=True, **kwargs):
        """
        Purge this history and all HDAs, Collections, and Datasets inside this history.
        """
        self.error_unless_mutable(item)
        self.hda_manager.dataset_manager.error_unless_dataset_purge_allowed()
        # First purge all the datasets
        for hda in item.datasets:
            if not hda.purged:
                self.hda_manager.purge(hda, flush=True, **kwargs)

        # Now mark the history as purged
        super().purge(item, flush=flush, **kwargs)

    # .... current
    # TODO: make something to bypass the anon user + current history permissions issue
    # def is_current_users_current_history( self, history, trans ):
    #     pass

    def get_current(self, trans):
        """
        Return the current history.
        """
        # TODO: trans
        return trans.get_history()

    def set_current(self, trans, history):
        """
        Set the current history.
        """
        # TODO: trans
        trans.set_history(history)
        return history

    def set_current_by_id(self, trans, history_id):
        """
        Set the current history by an id.
        """
        return self.set_current(trans, self.by_id(history_id))

    # order_by parsing - similar to FilterParser but not enough yet to warrant a class?
    def parse_order_by(self, order_by_string, default=None):
        """Return an ORM compatible order_by using the given string"""
        # TODO: generalize into class
        # TODO: general (enough) columns
        if order_by_string in ("create_time", "create_time-dsc"):
            return desc(self.model_class.create_time)
        if order_by_string == "create_time-asc":
            return asc(self.model_class.create_time)
        if order_by_string in ("update_time", "update_time-dsc"):
            return desc(self.model_class.update_time)
        if order_by_string == "update_time-asc":
            return asc(self.model_class.update_time)
        if order_by_string in ("name", "name-asc"):
            return asc(self.model_class.name)
        if order_by_string == "name-dsc":
            return desc(self.model_class.name)
        # TODO: history columns
        if order_by_string in ("size", "size-dsc"):
            return desc(self.model_class.disk_size)
        if order_by_string == "size-asc":
            return asc(self.model_class.disk_size)
        # TODO: add functional/non-orm orders (such as rating)
        if default:
            return self.parse_order_by(default)
        raise RequestParameterInvalidException(
            "Unknown order_by", order_by=order_by_string, available=["create_time", "update_time", "name", "size"]
        )

    def non_ready_jobs(self, history):
        """Return the currently running job objects associated with this history.

        Where running is defined as new, waiting, queued, running, resubmitted,
        and upload.
        """
        # TODO: defer to jobModelManager (if there was one)
        # TODO: genericize the params to allow other filters
        stmt = select(Job).where(Job.history == history).where(Job.state.in_(Job.non_ready_states))
        return self.session().scalars(stmt)

    def queue_history_import(self, trans, archive_type, archive_source):
        # Run job to do import.
        history_imp_tool = trans.app.toolbox.get_tool("__IMPORT_HISTORY__")
        incoming = {"__ARCHIVE_SOURCE__": archive_source, "__ARCHIVE_TYPE__": archive_type}
        job, *_ = history_imp_tool.execute(trans, incoming=incoming)
        trans.app.job_manager.enqueue(job, tool=history_imp_tool)
        return job

    # TODO: remove this function when the legacy endpoint using it is removed
    def legacy_serve_ready_history_export(self, trans, jeha):
        assert jeha.ready
        if jeha.compressed:
            trans.response.set_content_type("application/x-gzip")
        else:
            trans.response.set_content_type("application/x-tar")
        disposition = f'attachment; filename="{jeha.export_name}"'
        trans.response.headers["Content-Disposition"] = disposition
        archive = trans.app.object_store.get_filename(jeha.dataset)
        return open(archive, mode="rb")

    def get_ready_history_export_file_path(self, trans, jeha) -> str:
        """
        Serves the history export archive for use as a streaming response so the file
        doesn't need to be loaded into memory.
        """
        assert jeha.ready
        return trans.app.object_store.get_filename(jeha.dataset)

    def queue_history_export(
        self, trans, history, gzip=True, include_hidden=False, include_deleted=False, directory_uri=None, file_name=None
    ):
        # Convert options to booleans.
        if isinstance(gzip, str):
            gzip = gzip in ["True", "true", "T", "t"]
        if isinstance(include_hidden, str):
            include_hidden = include_hidden in ["True", "true", "T", "t"]
        if isinstance(include_deleted, str):
            include_deleted = include_deleted in ["True", "true", "T", "t"]

        params = {
            "history_to_export": history,
            "compress": gzip,
            "include_hidden": include_hidden,
            "include_deleted": include_deleted,
        }

        if directory_uri is None:
            export_tool_id = "__EXPORT_HISTORY__"
        else:
            params["directory_uri"] = directory_uri
            params["file_name"] = file_name or None
            export_tool_id = "__EXPORT_HISTORY_TO_URI__"

        # Run job to do export.
        history_exp_tool = trans.app.toolbox.get_tool(export_tool_id)
        job, *_ = history_exp_tool.execute(trans, incoming=params, history=history)
        trans.app.job_manager.enqueue(job, tool=history_exp_tool)
        return job

    def get_sharing_extra_information(
        self, trans, item, users: Set[model.User], errors: Set[str], option: Optional[sharable.SharingOptions] = None
    ) -> ShareHistoryExtra:
        """Returns optional extra information about the datasets of the history that can be accessed by the users."""
        extra = ShareHistoryExtra()
        history = cast(model.History, item)
        if history.empty:
            errors.add("You cannot share an empty history.")
            return extra

        owner = trans.user
        owner_roles = owner.all_roles()
        can_change_dict = {}
        cannot_change_dict = {}
        share_anyway = option is not None and option == sharable.SharingOptions.no_changes
        datasets = history.activatable_datasets
        total_dataset_count = len(datasets)
        for user in users:
            if self.is_history_shared_with(history, user):
                continue

            user_roles = user.all_roles()
            # TODO: Handle this is a more performant way
            # Only deal with datasets that have not been purged
            for hda in datasets:
                if trans.app.security_agent.can_access_dataset(user_roles, hda.dataset):
                    continue
                # The user with which we are sharing the history does not have access permission on the current dataset
                owner_can_manage_dataset = (
                    trans.app.security_agent.can_manage_dataset(owner_roles, hda.dataset)
                    and not hda.dataset.library_associations
                )
                if option and owner_can_manage_dataset:
                    if option == sharable.SharingOptions.make_accessible_to_shared:
                        trans.app.security_agent.privately_share_dataset(hda.dataset, users=[owner, user])
                    elif option == sharable.SharingOptions.make_public:
                        trans.app.security_agent.make_dataset_public(hda.dataset)
                else:
                    hda_id = hda.id
                    hda_info = HDABasicInfo(id=hda_id, name=hda.name)
                    if owner_can_manage_dataset:
                        can_change_dict[hda_id] = hda_info
                    else:
                        cannot_change_dict[hda_id] = hda_info

        extra.can_change = list(can_change_dict.values())
        extra.cannot_change = list(cannot_change_dict.values())
        extra.accessible_count = total_dataset_count - len(extra.can_change) - len(extra.cannot_change)
        if not extra.accessible_count and not extra.can_change and not share_anyway:
            errors.add(
                "The history you are sharing do not contain any datasets that can be accessed by the users with which you are sharing."
            )

        extra.can_share = not errors and (extra.accessible_count == total_dataset_count or option is not None)
        return extra

    def is_history_shared_with(self, history: model.History, user: model.User) -> bool:
        stmt = select(
            exists()
            .where(HistoryUserShareAssociation.user_id == user.id)
            .where(HistoryUserShareAssociation.history_id == history.id)
        )
        return bool(self.session().scalar(stmt))

    def make_members_public(self, trans, item):
        """Make the non-purged datasets in history public.
        Performs permissions check.
        """
        for hda in item.activatable_datasets:
            dataset = hda.dataset
            if not trans.app.security_agent.dataset_is_public(dataset):
                if trans.app.security_agent.can_manage_dataset(trans.user.all_roles(), dataset):
                    try:
                        trans.app.security_agent.make_dataset_public(hda.dataset)
                    except Exception:
                        log.warning(f"Unable to make dataset with id: {dataset.id} public")
                else:
                    log.warning(f"User without permissions tried to make dataset with id: {dataset.id} public")

    def archive_history(self, history: model.History, archive_export_id: Optional[int]):
        """Marks the history with the given id as archived and optionally associates it with the given archive export record.

        **Important**: The caller is responsible for passing a valid `archive_export_id` that belongs to the given history.
        """
        history.archived = True
        history.archive_export_id = archive_export_id
        self.session().commit()

        return history

    def restore_archived_history(self, history: model.History, force: bool = False):
        """Marks the history with the given id as not archived anymore.

        Only un-archives the history if it is not associated with an archive export record. You can force the un-archiving
        in this case by passing `force=True`.

        Please note that histories that are associated with an archive export are usually purged after export, so un-archiving them
        will not restore the datasets that were in the history before it was archived. You will need to import the archive export
        record to restore the history and its datasets as a new copy.
        """
        if history.archive_export_id is not None and history.purged and not force:
            raise RequestParameterInvalidException(
                "Cannot restore an archived (and purged) history that is associated with an archive export record. "
                "Please try importing it back as a new copy from the associated archive export record instead. "
                "You can still force the un-archiving of the purged history by setting the 'force' parameter."
            )

        history.archived = False
        self.session().commit()

        return history

    def get_active_count(self, user: model.User) -> int:
        """Return the number of active histories for the given user."""
        user_active_histories_filter = [
            model.History.user_id == user.id,
            model.History.deleted == false(),
            model.History.archived == false(),
        ]
        return self.count(filters=user_active_histories_filter)


class HistoryStorageCleanerManager(StorageCleanerManager):
    def __init__(self, history_manager: HistoryManager):
        self.history_manager = history_manager
        self.sort_map = {
            StoredItemOrderBy.NAME_ASC: asc(model.History.name),
            StoredItemOrderBy.NAME_DSC: desc(model.History.name),
            StoredItemOrderBy.SIZE_ASC: asc(model.History.disk_size),
            StoredItemOrderBy.SIZE_DSC: desc(model.History.disk_size),
            StoredItemOrderBy.UPDATE_TIME_ASC: asc(model.History.update_time),
            StoredItemOrderBy.UPDATE_TIME_DSC: desc(model.History.update_time),
        }

    def get_discarded_summary(self, user: model.User) -> CleanableItemsSummary:
        stmt = select(func.sum(model.History.disk_size), func.count(model.History.id)).where(
            model.History.user_id == user.id,
            model.History.deleted == true(),
            model.History.purged == false(),
        )
        result = self.history_manager.session().execute(stmt).fetchone()
        assert result
        total_size = 0 if result[0] is None else result[0]
        return CleanableItemsSummary(total_size=total_size, total_items=result[1])

    def get_discarded(
        self,
        user: model.User,
        offset: Optional[int],
        limit: Optional[int],
        order: Optional[StoredItemOrderBy],
    ) -> List[StoredItem]:
        stmt = select(model.History).where(
            model.History.user_id == user.id,
            model.History.deleted == true(),
            model.History.purged == false(),
        )
        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)
        if order:
            stmt = stmt.order_by(self.sort_map[order])
        result = self.history_manager.session().execute(stmt).scalars()
        discarded = [self._history_to_stored_item(item) for item in result]
        return discarded

    # TODO reduce duplication

    def get_archived_summary(self, user: model.User) -> CleanableItemsSummary:
        stmt = select(func.sum(model.History.disk_size), func.count(model.History.id)).where(
            model.History.user_id == user.id,
            model.History.archived == true(),
            model.History.purged == false(),
        )
        result = self.history_manager.session().execute(stmt).fetchone()
        assert result
        total_size = 0 if result[0] is None else result[0]
        return CleanableItemsSummary(total_size=total_size, total_items=result[1])

    def get_archived(
        self,
        user: model.User,
        offset: Optional[int],
        limit: Optional[int],
        order: Optional[StoredItemOrderBy],
    ) -> List[StoredItem]:
        stmt = select(model.History).where(
            model.History.user_id == user.id,
            model.History.archived == true(),
            model.History.purged == false(),
        )
        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)
        if order:
            stmt = stmt.order_by(self.sort_map[order])
        result = self.history_manager.session().execute(stmt).scalars()
        archived = [self._history_to_stored_item(item) for item in result]
        return archived

    def cleanup_items(self, user: model.User, item_ids: Set[int]) -> StorageItemsCleanupResult:
        success_item_count = 0
        total_free_bytes = 0
        errors: List[StorageItemCleanupError] = []

        for history_id in item_ids:
            try:
                history = self.history_manager.get_owned(history_id, user)
                self._unarchive_if_needed(history)
                self.history_manager.purge(history, flush=False, user=user)
                success_item_count += 1
                total_free_bytes += int(history.disk_size)
            except Exception as e:
                errors.append(StorageItemCleanupError(item_id=history_id, error=str(e)))

        if success_item_count:
            session = self.history_manager.session()
            session.commit()

        return StorageItemsCleanupResult(
            total_item_count=len(item_ids),
            success_item_count=success_item_count,
            total_free_bytes=total_free_bytes,
            errors=errors,
        )

    def _unarchive_if_needed(self, history: model.History):
        if history.archived:
            self.history_manager.restore_archived_history(history, force=True)

    def _history_to_stored_item(self, history: model.History) -> StoredItem:
        return StoredItem(
            id=history.id, name=history.name, type="history", size=history.disk_size, update_time=history.update_time
        )


class HistoryExportManager:
    export_object_type = ExportObjectType.HISTORY

    def __init__(self, app: MinimalManagerApp, export_tracker: StoreExportTracker):
        self.app = app
        self.export_tracker = export_tracker

    def get_task_exports(self, trans, history_id: int, limit: Optional[int] = None, offset: Optional[int] = None):
        """Returns task-based exports associated with this history"""
        history = self._history(trans, history_id)
        export_associations = self.export_tracker.get_object_exports(
            object_id=history_id, object_type=self.export_object_type, limit=limit, offset=offset
        )
        return [self._serialize_task_export(export, history) for export in export_associations]

    def get_task_export_by_id(self, store_export_id: int) -> model.StoreExportAssociation:
        return self.export_tracker.get_export_association(store_export_id)

    def create_export_association(self, history_id: int) -> model.StoreExportAssociation:
        return self.export_tracker.create_export_association(object_id=history_id, object_type=self.export_object_type)

    def get_record_metadata(self, export: model.StoreExportAssociation) -> Optional[ExportObjectMetadata]:
        json_metadata = export.export_metadata
        export_metadata = ExportObjectMetadata.parse_raw(json_metadata) if json_metadata else None
        return export_metadata

    def _serialize_task_export(self, export: model.StoreExportAssociation, history: model.History):
        task_uuid = export.task_uuid
        export_date = export.create_time
        assert history.update_time is not None, "History update time must be set"
        history_has_changed = history.update_time > export_date
        export_metadata = self.get_record_metadata(export)
        is_ready = export_metadata is not None and export_metadata.is_ready()
        is_export_up_to_date = is_ready and not history_has_changed
        return {
            "id": export.id,
            "ready": is_ready,
            "preparing": export_metadata is None or export_metadata.result_data is None,
            "up_to_date": is_export_up_to_date,
            "task_uuid": task_uuid,
            "create_time": export_date,
            "export_metadata": export_metadata,
        }

    def get_exports(self, trans, history_id: int):
        """Returns job-based exports associated with this history"""
        history = self._history(trans, history_id)
        matching_exports = history.exports
        return [self.serialize(trans, history_id, e) for e in matching_exports]

    def serialize(self, trans, history_id: int, jeha: model.JobExportHistoryArchive) -> dict:
        rval = jeha.to_dict()
        rval["type"] = "job"
        encoded_jeha_id = Security.security.encode_id(jeha.id)
        encoded_history_id = Security.security.encode_id(history_id)
        api_url = trans.url_builder("history_archive_download", history_id=encoded_history_id, jeha_id=encoded_jeha_id)
        external_url = trans.url_builder(
            "history_archive_download", history_id=encoded_history_id, jeha_id="latest", qualified=True
        )
        external_permanent_url = trans.url_builder(
            "history_archive_download", history_id=encoded_history_id, jeha_id=encoded_jeha_id, qualified=True
        )
        rval["download_url"] = api_url
        rval["external_download_latest_url"] = external_url
        rval["external_download_permanent_url"] = external_permanent_url
        rval = trans.security.encode_all_ids(rval)
        return rval

    def get_ready_jeha(self, trans, history_id: int, jeha_id: Union[int, Literal["latest"]] = "latest"):
        history = self._history(trans, history_id)
        matching_exports = history.exports
        if jeha_id != "latest":
            matching_exports = [e for e in matching_exports if e.id == jeha_id]
        if len(matching_exports) == 0:
            raise ObjectNotFound("Failed to find target history export")

        jeha = matching_exports[0]
        if not jeha.ready:
            raise MessageException("Export not available or not yet ready.")

        return jeha

    def _history(self, trans, history_id: int) -> model.History:
        history = self.app.history_manager.get_accessible(history_id, trans.user, current_history=trans.history)
        return history


class HistorySerializer(sharable.SharableModelSerializer, deletable.PurgableSerializerMixin):
    """
    Interface/service object for serializing histories into dictionaries.
    """

    model_manager_class = HistoryManager
    SINGLE_CHAR_ABBR = "h"

    def __init__(
        self,
        app: MinimalManagerApp,
        hda_manager: hdas.HDAManager,
        hda_serializer: hdas.HDASerializer,
        history_contents_serializer: history_contents.HistoryContentsSerializer,
    ):
        super().__init__(app)

        self.history_manager = self.manager
        self.hda_manager = hda_manager
        self.hda_serializer = hda_serializer
        self.history_contents_serializer = history_contents_serializer

        self.default_view = "summary"
        self.add_view(
            "summary",
            [
                "id",
                "model_class",
                "name",
                "deleted",
                "purged",
                "archived",
                "count",
                "url",
                # TODO: why these?
                "published",
                "annotation",
                "tags",
                "update_time",
                "preferred_object_store_id",
            ],
        )
        self.add_view(
            "detailed",
            [
                "contents_url",
                "email_hash",
                "empty",
                "size",
                "user_id",
                "create_time",
                "importable",
                "slug",
                "username",
                "username_and_slug",
                "genome_build",
                # TODO: remove the next three - instead getting the same info from the 'hdas' list
                "state",
                "state_details",
                "state_ids",
                "hid_counter",
                # 'community_rating',
                # 'user_rating',
            ],
            include_keys_from="summary",
        )
        # in the Historys' case, each of these views includes the keys from the previous

        #: ..note: this is a custom view for newer (2016/3) UI and should be considered volatile
        self.add_view(
            "dev-detailed",
            [
                "contents_url",
                "size",
                "user_id",
                "create_time",
                "importable",
                "slug",
                "username_and_slug",
                "genome_build",
                # 'contents_states',
                "contents_active",
                "hid_counter",
            ],
            include_keys_from="summary",
        )

    # assumes: outgoing to json.dumps and sanitized
    def add_serializers(self):
        super().add_serializers()
        deletable.PurgableSerializerMixin.add_serializers(self)

        serializers: Dict[str, Serializer] = {
            "model_class": lambda item, key, **context: "History",
            "size": lambda item, key, **context: int(item.disk_size),
            "nice_size": lambda item, key, **context: item.disk_nice_size,
            "state": self.serialize_history_state,
            "url": lambda item, key, **context: self.url_for(
                "history", history_id=self.app.security.encode_id(item.id), context=context
            ),
            "contents_url": lambda item, key, **context: self.url_for(
                "history_contents", history_id=self.app.security.encode_id(item.id), context=context
            ),
            "hdas": lambda item, key, encode_id=True, **context: [
                self.app.security.encode_id(hda.id) if encode_id else hda.id for hda in item.datasets
            ],
            "state_details": self.serialize_state_counts,
            "state_ids": self.serialize_state_ids,
            "contents": self.serialize_contents,
            "non_ready_jobs": lambda item, key, encode_id=True, **context: [
                self.app.security.encode_id(job.id) for job in self.manager.non_ready_jobs(item)
            ],
            "contents_states": self.serialize_contents_states,
            "contents_active": self.serialize_contents_active,
            #  TODO: Use base manager's serialize_id for user_id (and others)
            #  after refactoring hierarchy here?
            "user_id": lambda item, key, encode_id=True, **context: (
                self.app.security.encode_id(item.user_id) if item.user_id is not None and encode_id else item.user_id
            ),
        }
        self.serializers.update(serializers)

    # remove this
    def serialize_state_ids(self, item, key, **context):
        """
        Return a dictionary keyed to possible dataset states and valued with lists
        containing the ids of each HDA in that state.
        """
        history = item
        state_ids: Dict[str, List[str]] = {}
        for state in model.Dataset.states.values():
            state_ids[state] = []

        # TODO:?? collections and coll. states?
        for hda in history.datasets:
            # TODO: do not encode ids at this layer
            encoded_id = self.app.security.encode_id(hda.id)
            state_ids[hda.state].append(encoded_id)
        return state_ids

    # remove this
    def serialize_state_counts(self, item, key, exclude_deleted=True, exclude_hidden=False, **context):
        """
        Return a dictionary keyed to possible dataset states and valued with the number
        of datasets in this history that have those states.
        """
        history = item
        # TODO: the default flags above may not make a lot of sense (T,T?)
        state_counts = {}
        for state in model.Dataset.states.values():
            state_counts[state] = 0

        # TODO:?? collections and coll. states?
        for hda in history.datasets:
            if exclude_deleted and hda.deleted:
                continue
            if exclude_hidden and not hda.visible:
                continue
            state_counts[hda.state] = state_counts[hda.state] + 1
        return state_counts

    # TODO: remove this (is state used/useful?)
    def serialize_history_state(self, item, key, **context):
        """
        Returns the history state based on the states of the HDAs it contains.
        """
        history = item
        states = model.Dataset.states
        # (default to ERROR)
        state = states.ERROR
        # TODO: history_state and state_counts are classically calc'd at the same time
        #   so this is rel. ineff. - if we keep this...
        hda_state_counts = self.serialize_state_counts(history, "counts", exclude_deleted=True, **context)
        if history.empty:
            state = states.NEW
        else:
            num_hdas = sum(hda_state_counts.values())
            if (
                hda_state_counts[states.RUNNING] > 0
                or hda_state_counts[states.SETTING_METADATA] > 0
                or hda_state_counts[states.UPLOAD] > 0
            ):
                state = states.RUNNING
            # TODO: this method may be more useful if we *also* polled the histories jobs here too
            elif hda_state_counts[states.QUEUED] > 0 or hda_state_counts[states.NEW] > 0:
                state = states.QUEUED
            elif hda_state_counts[states.ERROR] > 0 or hda_state_counts[states.FAILED_METADATA] > 0:
                state = states.ERROR
            elif (hda_state_counts[states.OK] + hda_state_counts[states.DEFERRED]) == num_hdas:
                state = states.OK

        return state

    def serialize_contents(self, item, key, trans=None, user=None, **context):
        history = item
        returned = []
        for content in self.manager.contents_manager._union_of_contents_query(history).all():
            serialized = self.history_contents_serializer.serialize_to_view(
                content, view="summary", trans=trans, user=user
            )
            returned.append(serialized)
        return returned

    def serialize_contents_states(self, item, key, trans=None, **context):
        """
        Return a dictionary containing the counts of all contents in each state
        keyed by the distinct states.

        Note: does not include deleted/hidden contents.
        """
        history = item
        return self.manager.contents_manager.state_counts(history)

    def serialize_contents_active(self, item, key, **context):
        """
        Return a dictionary keyed with 'deleted', 'hidden', and 'active' with values
        for each representing the count of contents in each state.

        Note: counts for deleted and hidden overlap; In other words, a dataset that's
        both deleted and hidden will be added to both totals.
        """
        history = item
        return self.manager.contents_manager.active_counts(history)


class HistoryDeserializer(sharable.SharableModelDeserializer, deletable.PurgableDeserializerMixin):
    """
    Interface/service object for validating and deserializing dictionaries into histories.
    """

    model_manager_class = HistoryManager

    def __init__(self, app: MinimalManagerApp):
        super().__init__(app)
        self.history_manager = self.manager

    def add_deserializers(self):
        super().add_deserializers()
        deletable.PurgableDeserializerMixin.add_deserializers(self)

        self.deserializers.update(
            {
                "name": self.deserialize_basestring,
                "genome_build": self.deserialize_genome_build,
                "preferred_object_store_id": self.deserialize_preferred_object_store_id,
            }
        )

    def deserialize_preferred_object_store_id(self, item, key, val, **context):
        preferred_object_store_id = val
        validation_error = validate_preferred_object_store_id(
            context["trans"], self.app.object_store, preferred_object_store_id
        )
        if validation_error:
            raise ModelDeserializingError(validation_error)
        return self.default_deserializer(item, key, preferred_object_store_id, **context)


class HistoryFilters(sharable.SharableModelFilters, deletable.PurgableFiltersMixin):
    model_class = model.History
    model_manager_class = HistoryManager

    def _add_parsers(self):
        super()._add_parsers()
        deletable.PurgableFiltersMixin._add_parsers(self)
        self.orm_filter_parsers.update(
            {
                # history specific
                "name": {"op": ("eq", "contains", "like")},
                "genome_build": {"op": ("eq", "contains", "like")},
                "create_time": {"op": ("le", "ge", "gt", "lt"), "val": self.parse_date},
                "update_time": {"op": ("le", "ge", "gt", "lt"), "val": self.parse_date},
            }
        )
        self.fn_filter_parsers.update(
            {
                "username": {
                    "op": {
                        "eq": self.username_eq,
                        "contains": self.username_contains,
                    },
                },
            }
        )

    def username_eq(self, item, val: str) -> bool:
        return val.lower() == str(item.user.username).lower()

    def username_contains(self, item, val: str) -> bool:
        return val.lower() in str(item.user.username).lower()


def get_count(session, statement):
    stmt = select(func.count()).select_from(statement)
    return session.scalar(stmt)
