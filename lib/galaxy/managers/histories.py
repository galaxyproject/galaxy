"""
Manager and Serializer for histories.

Histories are containers for datasets or dataset collections
created (or copied) by users over the course of an analysis.
"""
import glob
import logging
import os
from typing import (
    cast,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

from pydantic import (
    BaseModel,
    Field,
)
from sqlalchemy import (
    and_,
    asc,
    desc,
    false,
    true,
)

from galaxy import (
    exceptions as glx_exceptions,
    model
)
from galaxy.managers import (
    deletable,
    hdas,
    history_contents,
    sharable
)
from galaxy.managers.base import (
    ServiceBase,
    SortableManager,
)
from galaxy.managers.citations import CitationsManager
from galaxy.managers.users import UserManager
from galaxy.schema import FilterQueryParams
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.schema.schema import (
    CreateHistoryPayload,
    CustomBuildsMetadataResponse,
    ExportHistoryArchivePayload,
    HistoryBeta,
    HistoryDetailed,
    HistoryImportArchiveSourceType,
    HistorySummary,
    JobExportHistoryArchive,
    JobIdResponse,
    JobImportHistoryResponse,
    LabelValuePair,
)
from galaxy.schema.types import SerializationParams
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.structured_app import MinimalManagerApp
from galaxy.util import restore_text

log = logging.getLogger(__name__)


class HDABasicInfo(BaseModel):
    id: EncodedDatabaseIdField
    name: str


class ShareHistoryExtra(sharable.ShareWithExtra):
    can_change: List[HDABasicInfo] = Field(
        [],
        title="Can Change",
        description=(
            "A collection of datasets that are not accessible by one or more of the target users "
            "and that can be made accessible for others by the user sharing the history."
        ),
    )
    cannot_change: List[HDABasicInfo] = Field(
        [],
        title="Cannot Change",
        description=(
            "A collection of datasets that are not accessible by one or more of the target users "
            "and that cannot be made accessible for others by the user sharing the history."
        ),
    )
    accessible_count: int = Field(
        0,
        title="Accessible Count",
        description=(
            "The number of datasets in the history that are public or accessible by all the target users."
        ),
    )


class HistoryManager(sharable.SharableModelManager, deletable.PurgableManagerMixin, SortableManager):

    model_class = model.History
    foreign_key_name = 'history'
    user_share_model = model.HistoryUserShareAssociation

    tag_assoc = model.HistoryTagAssociation
    annotation_assoc = model.HistoryAnnotationAssociation
    rating_assoc = model.HistoryRatingAssociation

    # TODO: incorporate imp/exp (or alias to)

    def __init__(self, app: MinimalManagerApp, hda_manager: hdas.HDAManager, contents_manager: history_contents.HistoryContentsManager, contents_filters: history_contents.HistoryContentsFilters):
        super().__init__(app)
        self.hda_manager = hda_manager
        self.contents_manager = contents_manager
        self.contents_filters = contents_filters

    def copy(self, history, user, **kwargs):
        """
        Copy and return the given `history`.
        """
        return history.copy(target_user=user, **kwargs)

    # .... sharable
    # overriding to handle anonymous users' current histories in both cases
    def by_user(self, user, current_history=None, **kwargs):
        """
        Get all the histories for a given user (allowing anon users' theirs)
        ordered by update time.
        """
        # handle default and/or anonymous user (which still may not have a history yet)
        if self.user_manager.is_anonymous(user):
            return [current_history] if current_history else []
        return super().by_user(user, **kwargs)

    def is_owner(self, history, user, current_history=None, **kwargs):
        """
        True if the current user is the owner of the given history.
        """
        # anon users are only allowed to view their current history
        if self.user_manager.is_anonymous(user):
            if current_history and history == current_history:
                return True
            return False
        return super().is_owner(history, user)

    # TODO: possibly to sharable or base
    def most_recent(self, user, filters=None, current_history=None, **kwargs):
        """
        Return the most recently update history for the user.

        If user is anonymous, return the current history. If the user is anonymous
        and the current history is deleted, return None.
        """
        if self.user_manager.is_anonymous(user):
            return None if (not current_history or current_history.deleted) else current_history
        desc_update_time = desc(self.model_class.update_time)
        filters = self._munge_filters(filters, self.model_class.user_id == user.id)
        # TODO: normalize this return value
        return self.query(filters=filters, order_by=desc_update_time, limit=1, **kwargs).first()

    # .... purgable
    def purge(self, history, flush=True, **kwargs):
        """
        Purge this history and all HDAs, Collections, and Datasets inside this history.
        """
        self.hda_manager.dataset_manager.error_unless_dataset_purge_allowed()
        # First purge all the datasets
        for hda in history.datasets:
            if not hda.purged:
                self.hda_manager.purge(hda, flush=True)

        # Now mark the history as purged
        super().purge(history, flush=flush, **kwargs)

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
        if order_by_string in ('create_time', 'create_time-dsc'):
            return desc(self.model_class.create_time)
        if order_by_string == 'create_time-asc':
            return asc(self.model_class.create_time)
        if order_by_string in ('update_time', 'update_time-dsc'):
            return desc(self.model_class.update_time)
        if order_by_string == 'update_time-asc':
            return asc(self.model_class.update_time)
        if order_by_string in ('name', 'name-asc'):
            return asc(self.model_class.name)
        if order_by_string == 'name-dsc':
            return desc(self.model_class.name)
        # TODO: history columns
        if order_by_string in ('size', 'size-dsc'):
            return desc(self.model_class.disk_size)
        if order_by_string == 'size-asc':
            return asc(self.model_class.disk_size)
        # TODO: add functional/non-orm orders (such as rating)
        if default:
            return self.parse_order_by(default)
        raise glx_exceptions.RequestParameterInvalidException('Unkown order_by', order_by=order_by_string,
            available=['create_time', 'update_time', 'name', 'size'])

    def non_ready_jobs(self, history):
        """Return the currently running job objects associated with this history.

        Where running is defined as new, waiting, queued, running, resubmitted,
        and upload.
        """
        # TODO: defer to jobModelManager (if there was one)
        # TODO: genericize the params to allow other filters
        jobs = (self.session().query(model.Job)
            .filter(model.Job.history == history)
            .filter(model.Job.state.in_(model.Job.non_ready_states)))
        return jobs

    def queue_history_import(self, trans, archive_type, archive_source):
        # Run job to do import.
        history_imp_tool = trans.app.toolbox.get_tool('__IMPORT_HISTORY__')
        incoming = {'__ARCHIVE_SOURCE__': archive_source, '__ARCHIVE_TYPE__': archive_type}
        job, *_ = history_imp_tool.execute(trans, incoming=incoming)
        trans.app.job_manager.enqueue(job, tool=history_imp_tool)
        return job

    def serve_ready_history_export(self, trans, jeha):
        assert jeha.ready
        if jeha.compressed:
            trans.response.set_content_type('application/x-gzip')
        else:
            trans.response.set_content_type('application/x-tar')
        disposition = f'attachment; filename="{jeha.export_name}"'
        trans.response.headers["Content-Disposition"] = disposition
        archive = trans.app.object_store.get_filename(jeha.dataset)
        return open(archive, mode='rb')

    def queue_history_export(self, trans, history, gzip=True, include_hidden=False, include_deleted=False, directory_uri=None, file_name=None):
        # Convert options to booleans.
        if isinstance(gzip, str):
            gzip = (gzip in ['True', 'true', 'T', 't'])
        if isinstance(include_hidden, str):
            include_hidden = (include_hidden in ['True', 'true', 'T', 't'])
        if isinstance(include_deleted, str):
            include_deleted = (include_deleted in ['True', 'true', 'T', 't'])

        params = {
            'history_to_export': history,
            'compress': gzip,
            'include_hidden': include_hidden,
            'include_deleted': include_deleted
        }

        if directory_uri is None:
            export_tool_id = '__EXPORT_HISTORY__'
        else:
            params['directory_uri'] = directory_uri
            params['file_name'] = file_name or None
            export_tool_id = '__EXPORT_HISTORY_TO_URI__'

        # Run job to do export.
        history_exp_tool = trans.app.toolbox.get_tool(export_tool_id)
        job, *_ = history_exp_tool.execute(trans, incoming=params, history=history, set_output_hid=True)
        trans.app.job_manager.enqueue(job, tool=history_exp_tool)
        return job

    def get_sharing_extra_information(
        self, trans, item, users: Set[model.User], errors: Set[str], option: Optional[sharable.SharingOptions] = None
    ) -> Optional[sharable.ShareWithExtra]:
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
                    hda_id = trans.security.encode_id(hda.id)
                    hda_info = HDABasicInfo(id=hda_id, name=hda.name)
                    if owner_can_manage_dataset:
                        can_change_dict[hda_id] = hda_info
                    else:
                        cannot_change_dict[hda_id] = hda_info

        extra.can_change = list(can_change_dict.values())
        extra.cannot_change = list(cannot_change_dict.values())
        extra.accessible_count = total_dataset_count - len(extra.can_change) - len(extra.cannot_change)
        if not extra.accessible_count and not extra.can_change and not share_anyway:
            errors.add("The history you are sharing do not contain any datasets that can be accessed by the users with which you are sharing.")

        extra.can_share = not errors and (extra.accessible_count == total_dataset_count or option is not None)
        return extra

    def is_history_shared_with(self, history, user) -> bool:
        return bool(self.session().query(self.user_share_model).filter(
            and_(
                self.user_share_model.table.c.user_id == user.id,
                self.user_share_model.table.c.history_id == history.id,
            )
        ).first())

    def make_members_public(self, trans, item):
        """ Make the non-purged datasets in history public.
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


class HistoryExportView:

    def __init__(self, app: MinimalManagerApp):
        self.app = app

    def get_exports(self, trans, history_id):
        history = self._history(trans, history_id)
        matching_exports = history.exports
        return [self.serialize(trans, history_id, e) for e in matching_exports]

    def serialize(self, trans, history_id, jeha):
        rval = jeha.to_dict()
        encoded_jeha_id = trans.security.encode_id(jeha.id)
        api_url = self.app.url_for("history_archive_download", id=history_id, jeha_id=encoded_jeha_id)
        # this URL is less likely to be blocked by a proxy and require an API key, so export
        # older-style controller version for use with within the GUI and such.
        external_url = self.app.url_for(controller='history', action="export_archive", id=history_id, qualified=True)
        external_permanent_url = self.app.url_for(controller='history', action="export_archive", id=history_id, jeha_id=encoded_jeha_id, qualified=True)
        rval["download_url"] = api_url
        rval["external_download_latest_url"] = external_url
        rval["external_download_permanent_url"] = external_permanent_url
        rval = trans.security.encode_all_ids(rval)
        return rval

    def get_ready_jeha(self, trans, history_id, jeha_id="latest"):
        history = self._history(trans, history_id)
        matching_exports = history.exports
        if jeha_id != "latest":
            decoded_jeha_id = trans.security.decode_id(jeha_id)
            matching_exports = [e for e in matching_exports if e.id == decoded_jeha_id]
        if len(matching_exports) == 0:
            raise glx_exceptions.ObjectNotFound("Failed to find target history export")

        jeha = matching_exports[0]
        if not jeha.ready:
            raise glx_exceptions.MessageException("Export not available or not yet ready.")

        return jeha

    def _history(self, trans, history_id):
        if history_id is not None:
            history = self.app.history_manager.get_accessible(trans.security.decode_id(history_id), trans.user, current_history=trans.history)
        else:
            history = trans.history
        return history


class HistorySerializer(sharable.SharableModelSerializer, deletable.PurgableSerializerMixin):
    """
    Interface/service object for serializing histories into dictionaries.
    """
    model_manager_class = HistoryManager
    SINGLE_CHAR_ABBR = 'h'

    def __init__(self, app: MinimalManagerApp, hda_manager: hdas.HDAManager, hda_serializer: hdas.HDASerializer, history_contents_serializer: history_contents.HistoryContentsSerializer):
        super().__init__(app)

        self.history_manager = self.manager
        self.hda_manager = hda_manager
        self.hda_serializer = hda_serializer
        self.history_contents_serializer = history_contents_serializer

        self.default_view = 'summary'
        self.add_view('summary', [
            'id',
            'model_class',
            'name',
            'deleted',
            'purged',
            # 'count'
            'url',
            # TODO: why these?
            'published',
            'annotation',
            'tags',
            'update_time',
        ])
        self.add_view('detailed', [
            'contents_url',
            'empty',
            'size',
            'user_id',
            'create_time',
            'update_time',
            'importable',
            'slug',
            'username_and_slug',
            'genome_build',
            # TODO: remove the next three - instead getting the same info from the 'hdas' list
            'state',
            'state_details',
            'state_ids',
            # 'community_rating',
            # 'user_rating',
        ], include_keys_from='summary')
        # in the Historys' case, each of these views includes the keys from the previous

        #: ..note: this is a custom view for newer (2016/3) UI and should be considered volatile
        self.add_view('dev-detailed', [
            'contents_url',
            'size',
            'user_id',
            'create_time',
            'update_time',
            'importable',
            'slug',
            'username_and_slug',
            'genome_build',
            # 'contents_states',
            'contents_active',
            'hid_counter',
        ], include_keys_from='summary')

        # beta web client fields, no summary/detailed/dev-detailed blah
        self.add_view('betawebclient', [
            'annotation',
            'contents_active',
            'contents_url',
            'create_time',
            'deleted',
            'empty',
            'genome_build',
            'hid_counter',
            'id',
            'importable',
            'name',
            'nice_size',
            'published',
            'purged',
            # 'shared',
            'size',
            'slug',
            'state',
            'tags',
            'update_time',
            'url',
            'username_and_slug',
            'user_id',
        ])

    # assumes: outgoing to json.dumps and sanitized
    def add_serializers(self):
        super().add_serializers()
        deletable.PurgableSerializerMixin.add_serializers(self)

        self.serializers.update({
            'model_class': lambda *a, **c: 'History',
            'size': lambda i, k, **c: int(i.disk_size),
            'nice_size': lambda i, k, **c: i.disk_nice_size,
            'state': self.serialize_history_state,

            'url': lambda i, k, **c: self.url_for('history', id=self.app.security.encode_id(i.id)),
            'contents_url': lambda i, k, **c: self.url_for('history_contents',
                                                           history_id=self.app.security.encode_id(i.id)),

            'empty': lambda i, k, **c: (len(i.datasets) + len(i.dataset_collections)) <= 0,
            'count': lambda i, k, **c: len(i.datasets),
            'hdas': lambda i, k, **c: [self.app.security.encode_id(hda.id) for hda in i.datasets],
            'state_details': self.serialize_state_counts,
            'state_ids': self.serialize_state_ids,
            'contents': self.serialize_contents,
            'non_ready_jobs': lambda i, k, **c: [self.app.security.encode_id(job.id) for job
                                                 in self.manager.non_ready_jobs(i)],

            'contents_states': self.serialize_contents_states,
            'contents_active': self.serialize_contents_active,
            #  TODO: Use base manager's serialize_id for user_id (and others)
            #  after refactoring hierarchy here?
            'user_id': lambda i, k, **c: self.app.security.encode_id(i.user_id) if i.user_id is not None else None
        })

    # remove this
    def serialize_state_ids(self, history, key, **context):
        """
        Return a dictionary keyed to possible dataset states and valued with lists
        containing the ids of each HDA in that state.
        """
        state_ids = {}
        for state in model.Dataset.states.values():
            state_ids[state] = []

        # TODO:?? collections and coll. states?
        for hda in history.datasets:
            # TODO: do not encode ids at this layer
            encoded_id = self.app.security.encode_id(hda.id)
            state_ids[hda.state].append(encoded_id)
        return state_ids

    # remove this
    def serialize_state_counts(self, history, key, exclude_deleted=True, exclude_hidden=False, **context):
        """
        Return a dictionary keyed to possible dataset states and valued with the number
        of datasets in this history that have those states.
        """
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
    def serialize_history_state(self, history, key, **context):
        """
        Returns the history state based on the states of the HDAs it contains.
        """
        states = model.Dataset.states
        # (default to ERROR)
        state = states.ERROR
        # TODO: history_state and state_counts are classically calc'd at the same time
        #   so this is rel. ineff. - if we keep this...
        hda_state_counts = self.serialize_state_counts(history, 'counts', exclude_deleted=True, **context)
        num_hdas = sum(hda_state_counts.values())
        if num_hdas == 0:
            state = states.NEW

        else:
            if (hda_state_counts[states.RUNNING] > 0
                    or hda_state_counts[states.SETTING_METADATA] > 0
                    or hda_state_counts[states.UPLOAD] > 0):
                state = states.RUNNING
            # TODO: this method may be more useful if we *also* polled the histories jobs here too
            elif (hda_state_counts[states.QUEUED] > 0
                    or hda_state_counts[states.NEW] > 0):
                state = states.QUEUED
            elif (hda_state_counts[states.ERROR] > 0
                    or hda_state_counts[states.FAILED_METADATA] > 0):
                state = states.ERROR
            elif hda_state_counts[states.OK] == num_hdas:
                state = states.OK

        return state

    def serialize_contents(self, history, key, trans=None, user=None, **context):
        returned = []
        for content in self.manager.contents_manager._union_of_contents_query(history).all():
            serialized = self.history_contents_serializer.serialize_to_view(content,
                view='summary', trans=trans, user=user)
            returned.append(serialized)
        return returned

    def serialize_contents_states(self, history, key, trans=None, **context):
        """
        Return a dictionary containing the counts of all contents in each state
        keyed by the distinct states.

        Note: does not include deleted/hidden contents.
        """
        return self.manager.contents_manager.state_counts(history)

    def serialize_contents_active(self, history, key, **context):
        """
        Return a dictionary keyed with 'deleted', 'hidden', and 'active' with values
        for each representing the count of contents in each state.

        Note: counts for deleted and hidden overlap; In other words, a dataset that's
        both deleted and hidden will be added to both totals.
        """
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

        self.deserializers.update({
            'name': self.deserialize_basestring,
            'genome_build': self.deserialize_genome_build,
        })


class HistoryFilters(sharable.SharableModelFilters, deletable.PurgableFiltersMixin):
    model_class = model.History
    model_manager_class = HistoryManager

    def _add_parsers(self):
        super()._add_parsers()
        deletable.PurgableFiltersMixin._add_parsers(self)
        self.orm_filter_parsers.update({
            # history specific
            'name': {'op': ('eq', 'contains', 'like')},
            'genome_build': {'op': ('eq', 'contains', 'like')},
            'create_time': {'op': ('le', 'ge', 'gt', 'lt'), 'val': self.parse_date},
            'update_time': {'op': ('le', 'ge', 'gt', 'lt'), 'val': self.parse_date},
        })


class HistoriesService(ServiceBase):
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
    ):
        super().__init__(security)
        self.manager = manager
        self.user_manager = user_manager
        self.serializer = serializer
        self.deserializer = deserializer
        self.citations_manager = citations_manager
        self.history_export_view = history_export_view
        self.filters = filters
        self.shareable_service = sharable.ShareableService(self.manager, self.serializer)

    def index(
        self,
        trans,
        serialization_params: SerializationParams,
        filter_query_params: FilterQueryParams,
        deleted_only: Optional[bool] = False,
        all_histories: bool = False,
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
        order_by = self.build_order_by(self.manager, filter_query_params.order)

        histories = self.manager.list(
            filters=filters, order_by=order_by,
            limit=filter_query_params.limit, offset=filter_query_params.offset)

        rval = [self._serialize_history(trans, history, serialization_params, default_view="summary") for history in histories]
        return rval

    def _get_deleted_filter(self, deleted: Optional[bool], filter_params: List[Tuple[str, str, str]]):
        # TODO: this should all be removed (along with the default) in v2
        # support the old default of not-returning/filtering-out deleted histories
        try:
            # the consumer must explicitly ask for both deleted and non-deleted
            #   but pull it from the parsed params (as the filter system will error on None)
            deleted_filter_index = filter_params.index(('deleted', 'eq', 'None'))
            filter_params.pop(deleted_filter_index)
            return []
        except ValueError:
            pass

        # the deleted string bool was also used as an 'include deleted' flag
        if deleted is True:
            return [model.History.deleted == true()]

        # the third option not handled here is 'return only deleted'
        #   if this is passed in (in the form below), simply return and let the filter system handle it
        if ('deleted', 'eq', 'True') in filter_params:
            return []

        # otherwise, do the default filter of removing the deleted histories
        return [model.History.deleted == false()]

    def create(
        self,
        trans,
        payload: CreateHistoryPayload,
        serialization_params: SerializationParams,
    ):
        """Create a new history from scratch, by copying an existing one or by importing
        from URL or File depending on the provided parameters in the payload.
        """
        if trans.user and trans.user.bootstrap_admin_user:
            raise glx_exceptions.RealUserRequiredException("Only real users can create histories.")
        hist_name = None
        if payload.name is not None:
            hist_name = restore_text(payload.name)
        copy_this_history_id = payload.history_id
        all_datasets = payload.all_datasets

        if payload.archive_source is not None:
            archive_source = payload.archive_source
            archive_file = payload.archive_file
            if archive_source:
                archive_type = payload.archive_type
            elif archive_file is not None and hasattr(archive_file, "file"):
                archive_source = archive_file.file.name
                archive_type = HistoryImportArchiveSourceType.file
            else:
                raise glx_exceptions.MessageException("Please provide a url or file.")
            job = self.manager.queue_history_import(trans, archive_type=archive_type, archive_source=archive_source)
            job_dict = job.to_dict()
            job_dict["message"] = f"Importing history from source '{archive_source}'. This history will be visible when the import is complete."
            job_dict = trans.security.encode_all_ids(job_dict)
            return JobImportHistoryResponse.parse_obj(job_dict)

        new_history = None
        # if a history id was passed, copy that history
        if copy_this_history_id:
            decoded_id = self.decode_id(copy_this_history_id)
            original_history = self.manager.get_accessible(decoded_id, trans.user, current_history=trans.history)
            hist_name = hist_name or (f"Copy of '{original_history.name}'")
            new_history = original_history.copy(name=hist_name, target_user=trans.user, all_datasets=all_datasets)

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

    def show(
        self,
        trans,
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
                trans.user,
                filters=(model.History.deleted == false()),
                current_history=trans.history
            )
        else:
            history = self.manager.get_accessible(
                self.decode_id(history_id),
                trans.user,
                current_history=trans.history
            )
        return self._serialize_history(trans, history, serialization_params)

    def update(
        self,
        trans,
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
        trans,
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
        trans,
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
        trans,
        serialization_params: SerializationParams,
        filter_query_params: FilterQueryParams,
    ):
        """
        Return all histories that are shared with the current user. The results can be filtered.
        """
        current_user = trans.user
        filters = self.filters.parse_query_filters(filter_query_params)
        order_by = self.build_order_by(self.manager, filter_query_params.order)
        histories = self.manager.list_shared_with(current_user,
            filters=filters, order_by=order_by,
            limit=filter_query_params.limit, offset=filter_query_params.offset)
        rval = [self._serialize_history(trans, history, serialization_params, default_view="summary") for history in histories]
        return rval

    def published(
        self,
        trans,
        serialization_params: SerializationParams,
        filter_query_params: FilterQueryParams,
    ):
        """
        Return all histories that are published. The results can be filtered.
        """
        filters = self.filters.parse_query_filters(filter_query_params)
        order_by = self.build_order_by(self.manager, filter_query_params.order)
        histories = self.manager.list_published(
            filters=filters, order_by=order_by,
            limit=filter_query_params.limit, offset=filter_query_params.offset,
        )
        rval = [self._serialize_history(trans, history, serialization_params, default_view="summary") for history in histories]
        return rval

    def citations(self, trans, history_id):
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

    def index_exports(self, trans, id):
        """
        Get previous history exports (to links). Effectively returns serialized
        JEHA objects.
        """
        return self.history_export_view.get_exports(trans, id)

    def archive_export(self, trans, id: EncodedDatabaseIdField, payload: ExportHistoryArchivePayload) -> Union[JobExportHistoryArchive, JobIdResponse]:
        """
        start job (if needed) to create history export for corresponding
        history.

        :type   id:     str
        :param  id:     the encoded id of the history to export

        :rtype:     dict
        :returns:   object containing url to fetch export from.
        """
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

        if exporting_to_uri:
            # we don't have a jeha, there will never be a download_url. Just let
            # the client poll on the created job_id to determine when the file has been
            # written.
            job_id = trans.security.encode_id(job.id)
            return JobIdResponse(job_id=job_id)

        if up_to_date and jeha.ready:
            serialized_jeha = self.history_export_view.serialize(trans, id, jeha)
            return JobExportHistoryArchive.parse_obj(serialized_jeha)
        else:
            # Valid request, just resource is not ready yet.
            trans.response.status = "202 Accepted"
            if jeha:
                serialized_jeha = self.history_export_view.serialize(trans, id, jeha)
                return JobExportHistoryArchive.parse_obj(serialized_jeha)
            else:
                assert job is not None, "logic error, don't have a jeha or a job"
                job_id = trans.security.encode_id(job.id)
                return JobIdResponse(job_id=job_id)

    def archive_download(self, trans, id, jeha_id):
        """
        If ready and available, return raw contents of exported history.
        """
        jeha = self.history_export_view.get_ready_jeha(trans, id, jeha_id)
        return self.manager.serve_ready_history_export(trans, jeha)

    def get_custom_builds_metadata(self, trans, id: EncodedDatabaseIdField) -> CustomBuildsMetadataResponse:
        """
        Returns meta data for custom builds.
        """
        history = self.manager.get_accessible(self.decode_id(id), trans.user, current_history=trans.history)
        installed_builds = []
        for build in glob.glob(os.path.join(trans.app.config.len_file_path, "*.len")):
            installed_builds.append(os.path.basename(build).split(".len")[0])
        fasta_hdas = trans.sa_session.query(model.HistoryDatasetAssociation) \
            .filter_by(history=history, extension="fasta", deleted=False) \
            .order_by(model.HistoryDatasetAssociation.hid.desc())
        return CustomBuildsMetadataResponse(
            installed_builds=[LabelValuePair(label=ins, value=ins) for ins in installed_builds],
            fasta_hdas=[LabelValuePair(label=f'{hda.hid}: {hda.name}', value=trans.security.encode_id(hda.id)) for hda in fasta_hdas],
        )

    def _serialize_history(
            self,
            trans,
            history: model.History,
            serialization_params: SerializationParams,
            default_view: str = "detailed",
    ) -> Union[HistoryBeta, HistoryDetailed, HistorySummary]:
        """
        Returns a dictionary with the corresponding values depending on the
        serialization parameters provided.
        """
        serialization_params["default_view"] = default_view
        serialized_history = self.serializer.serialize_to_view(
            history,
            user=trans.user,
            trans=trans,
            **serialization_params
        )
        return serialized_history
