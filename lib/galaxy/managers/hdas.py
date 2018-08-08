"""
Manager and Serializer for HDAs.

HistoryDatasetAssociations (HDAs) are datasets contained or created in a
history.
"""
import gettext
import logging
import os

from galaxy import (
    datatypes,
    exceptions,
    model
)
from galaxy.managers import (
    annotatable,
    datasets,
    secured,
    taggable,
    users
)

log = logging.getLogger(__name__)


class HDAManager(datasets.DatasetAssociationManager,
                 secured.OwnableManagerMixin,
                 taggable.TaggableManagerMixin,
                 annotatable.AnnotatableManagerMixin):
    """
    Interface/service object for interacting with HDAs.
    """
    model_class = model.HistoryDatasetAssociation
    foreign_key_name = 'history_dataset_association'

    tag_assoc = model.HistoryDatasetAssociationTagAssociation
    annotation_assoc = model.HistoryDatasetAssociationAnnotationAssociation

    # TODO: move what makes sense into DatasetManager
    # TODO: which of these are common with LDDAs and can be pushed down into DatasetAssociationManager?

    def __init__(self, app):
        """
        Set up and initialize other managers needed by hdas.
        """
        super(HDAManager, self).__init__(app)
        self.user_manager = users.UserManager(app)

    # .... security and permissions
    def is_accessible(self, hda, user, **kwargs):
        """
        Override to allow owners (those that own the associated history).
        """
        # this, apparently, is not True:
        #   if I have a copy of a dataset and anyone who manages permissions on it revokes my access
        #   I can not access that dataset even if it's in my history
        # if self.is_owner( hda, user, **kwargs ):
        #     return True
        return super(HDAManager, self).is_accessible(hda, user, **kwargs)

    def is_owner(self, hda, user, current_history=None, **kwargs):
        """
        Use history to see if current user owns HDA.
        """
        history = hda.history
        if self.user_manager.is_admin(user, trans=kwargs.get("trans", None)):
            return True
        # allow anonymous user to access current history
        # TODO: some dup here with historyManager.is_owner but prevents circ import
        # TODO: awkward kwarg (which is my new band name); this may not belong here - move to controller?
        if self.user_manager.is_anonymous(user):
            if current_history and history == current_history:
                return True
            return False
        return history.user == user

    # .... create and copy
    def create(self, history=None, dataset=None, flush=True, **kwargs):
        """
        Create a new hda optionally passing in it's history and dataset.

        ..note: to explicitly set hid to `None` you must pass in `hid=None`, otherwise
        it will be automatically set.
        """
        if not dataset:
            kwargs['create_dataset'] = True
        hda = model.HistoryDatasetAssociation(history=history, dataset=dataset,
                                              sa_session=self.app.model.context, **kwargs)

        if history:
            history.add_dataset(hda, set_hid=('hid' not in kwargs))
        # TODO:?? some internal sanity check here (or maybe in add_dataset) to make sure hids are not duped?

        self.session().add(hda)
        if flush:
            self.session().flush()
        return hda

    def copy(self, hda, history=None, hide_copy=False, **kwargs):
        """
        Copy hda, including annotation and tags, add to history and return the given HDA.
        """
        copy = hda.copy(parent_id=kwargs.get('parent_id'), copy_hid=False)
        if hide_copy:
            copy.visible = False
        # add_dataset will update the hid to the next avail. in history
        if history:
            history.add_dataset(copy)

        copy.copied_from_history_dataset_association = hda
        copy.set_size()

        original_annotation = self.annotation(hda)
        self.annotate(copy, original_annotation, user=hda.history.user)

        # these use a session flush
        original_tags = self.get_tags(hda)
        self.set_tags(copy, original_tags, user=hda.history.user)

        return copy

    def copy_ldda(self, history, ldda, **kwargs):
        """
        Copy this HDA as a LDDA and return.
        """
        return ldda.to_history_dataset_association(history, add_to_history=True)

    # .... deletion and purging
    def purge(self, hda, flush=True):
        """
        Purge this HDA and the dataset underlying it.
        """
        user = hda.history.user or None
        quota_amount_reduction = 0
        if user:
            quota_amount_reduction = hda.quota_amount(user)
        super(HDAManager, self).purge(hda, flush=flush)
        # decrease the user's space used
        if quota_amount_reduction:
            user.adjust_total_disk_usage(-quota_amount_reduction)
        return hda

    # .... states
    def error_if_uploading(self, hda):
        """
        Raise error if HDA is still uploading.
        """
        # TODO: may be better added to an overridden get_accessible
        if hda.state == model.Dataset.states.UPLOAD:
            raise exceptions.Conflict("Please wait until this dataset finishes uploading")
        return hda

    def has_been_resubmitted(self, hda):
        """
        Return True if the hda's job was resubmitted at any point.
        """
        job_states = model.Job.states
        query = (self._job_state_history_query(hda)
                 .filter(model.JobStateHistory.state == job_states.RESUBMITTED))
        return self.app.model.context.query(query.exists()).scalar()

    def _job_state_history_query(self, hda):
        """
        Return a query of the job's state history for the job that created this hda.
        """
        session = self.app.model.context
        JobToOutputDatasetAssociation = model.JobToOutputDatasetAssociation
        JobStateHistory = model.JobStateHistory

        # TODO: this does not play well with copied hdas
        # NOTE: don't eagerload (JODA will load the hda were using!)
        hda_id = hda.id
        query = (session.query(JobToOutputDatasetAssociation, JobStateHistory)
                 .filter(JobToOutputDatasetAssociation.dataset_id == hda_id)
                 .filter(JobStateHistory.job_id == JobToOutputDatasetAssociation.job_id)
                 .enable_eagerloads(False))
        return query

    def data_conversion_status(self, hda):
        """
        Returns a message if an hda is not ready to be used in visualization.
        """
        # this is a weird syntax and return val
        if not hda:
            return self.model_class.conversion_messages.NO_DATA
        if hda.state == model.Job.states.ERROR:
            return self.model_class.conversion_messages.ERROR
        if hda.state != model.Job.states.OK:
            return self.model_class.conversion_messages.PENDING
        return None

    # .... data
    # TODO: to data provider or Text datatype directly
    def text_data(self, hda, preview=True):
        """
        Get data from text file, truncating if necessary.
        """
        # 1 MB
        MAX_PEEK_SIZE = 1000000

        truncated = False
        hda_data = None
        # For now, cannot get data from non-text datasets.
        if not isinstance(hda.datatype, datatypes.data.Text):
            return truncated, hda_data
        if not os.path.exists(hda.file_name):
            return truncated, hda_data

        truncated = preview and os.stat(hda.file_name).st_size > MAX_PEEK_SIZE
        hda_data = open(hda.file_name).read(MAX_PEEK_SIZE)
        return truncated, hda_data

    # .... annotatable
    def annotation(self, hda):
        # override to scope to history owner
        return self._user_annotation(hda, hda.history.user)

    def _set_permissions(self, trans, hda, role_ids_dict):
        # The user associated the DATASET_ACCESS permission on the dataset with 1 or more roles.  We
        # need to ensure that they did not associate roles that would cause accessibility problems.
        permissions, in_roles, error, message = \
            trans.app.security_agent.derive_roles_from_access(trans, hda.dataset.id, 'root', **role_ids_dict)
        if error:
            # Keep the original role associations for the DATASET_ACCESS permission on the dataset.
            access_action = trans.app.security_agent.get_action(trans.app.security_agent.permitted_actions.DATASET_ACCESS.action)
            permissions[access_action] = hda.dataset.get_access_roles(trans)
            trans.sa_session.refresh(hda.dataset)
            raise exceptions.RequestParameterInvalidException(message)
        else:
            error = trans.app.security_agent.set_all_dataset_permissions(hda.dataset, permissions)
            trans.sa_session.refresh(hda.dataset)
            if error:
                raise exceptions.RequestParameterInvalidException(error)


class HDASerializer(  # datasets._UnflattenedMetadataDatasetAssociationSerializer,
        datasets.DatasetAssociationSerializer,
        taggable.TaggableSerializerMixin,
        annotatable.AnnotatableSerializerMixin):
    model_manager_class = HDAManager

    def __init__(self, app):
        super(HDASerializer, self).__init__(app)
        self.hda_manager = self.manager

        self.default_view = 'summary'
        self.add_view('summary', [
            'id',
            'type_id',
            'name',
            'history_id',
            'hid',
            'history_content_type',
            'dataset_id',
            'state',
            'extension',
            'deleted', 'purged', 'visible',
            'tags',
            'type',
            'url',
            'create_time',
            'update_time',
        ])
        self.add_view('detailed', [
            'model_class',
            'history_id', 'hid',
            # why include if model_class is there?
            'hda_ldda',
            # TODO: accessible needs to go away
            'accessible',

            # remapped
            'genome_build', 'misc_info', 'misc_blurb',
            'file_ext', 'file_size',

            'resubmitted',
            'metadata', 'meta_files', 'data_type',
            'peek',

            'creating_job',
            'rerunnable',

            'uuid',
            'permissions',
            'file_name',

            'display_apps',
            'display_types',
            'visualizations',

            # 'url',
            'download_url',

            'annotation',

            'api_type'
        ], include_keys_from='summary')

        self.add_view('extended', [
            'tool_version', 'parent_id', 'designation',
        ], include_keys_from='detailed')

        # keyset returned to create show a dataset where the owner has no access
        self.add_view('inaccessible', [
            'accessible',
            'id', 'name', 'history_id', 'hid', 'history_content_type',
            'state', 'deleted', 'visible'
        ])

    def add_serializers(self):
        super(HDASerializer, self).add_serializers()
        taggable.TaggableSerializerMixin.add_serializers(self)
        annotatable.AnnotatableSerializerMixin.add_serializers(self)

        self.serializers.update({
            'model_class'   : lambda *a, **c: 'HistoryDatasetAssociation',
            'history_content_type': lambda *a, **c: 'dataset',
            'hda_ldda'      : lambda *a, **c: 'hda',
            'type_id'       : self.serialize_type_id,

            'history_id'    : self.serialize_id,

            # remapped
            'misc_info'     : self._remap_from('info'),
            'misc_blurb'    : self._remap_from('blurb'),
            'file_ext'      : self._remap_from('extension'),
            'file_path'     : self._remap_from('file_name'),
            'resubmitted'   : lambda i, k, **c: self.hda_manager.has_been_resubmitted(i),
            'display_apps'  : self.serialize_display_apps,
            'display_types' : self.serialize_old_display_applications,
            'visualizations': self.serialize_visualization_links,

            # 'url'   : url_for( 'history_content_typed', history_id=encoded_history_id, id=encoded_id, type="dataset" ),
            # TODO: this intermittently causes a routes.GenerationException - temp use the legacy route to prevent this
            #   see also: https://trello.com/c/5d6j4X5y
            #   see also: https://sentry.galaxyproject.org/galaxy/galaxy-main/group/20769/events/9352883/
            'url'           : lambda i, k, **c: self.url_for('history_content',
                                                             history_id=self.app.security.encode_id(i.history_id),
                                                             id=self.app.security.encode_id(i.id)),
            'urls'          : self.serialize_urls,

            # TODO: backwards compat: need to go away
            'download_url'  : lambda i, k, **c: self.url_for('history_contents_display',
                                                             history_id=self.app.security.encode_id(i.history.id),
                                                             history_content_id=self.app.security.encode_id(i.id)),
            'parent_id'     : self.serialize_id,
            # TODO: to DatasetAssociationSerializer
            'accessible'    : lambda i, k, user=None, **c: self.manager.is_accessible(i, user, **c),
            'api_type'      : lambda *a, **c: 'file',
            'type'          : lambda *a, **c: 'file'
        })

    def serialize(self, hda, keys, user=None, **context):
        """
        Override to hide information to users not able to access.
        """
        # TODO: to DatasetAssociationSerializer
        if not self.manager.is_accessible(hda, user, **context):
            keys = self._view_to_keys('inaccessible')
        return super(HDASerializer, self).serialize(hda, keys, user=user, **context)

    def serialize_display_apps(self, hda, key, trans=None, **context):
        """
        Return dictionary containing new-style display app urls.
        """
        display_apps = []
        for display_app in hda.get_display_applications(trans).values():

            app_links = []
            for link_app in display_app.links.values():
                app_links.append({
                    'target': link_app.url.get('target_frame', '_blank'),
                    'href': link_app.get_display_url(hda, trans),
                    'text': gettext.gettext(link_app.name)
                })
            if app_links:
                display_apps.append(dict(label=display_app.name, links=app_links))

        return display_apps

    def serialize_old_display_applications(self, hda, key, trans=None, **context):
        """
        Return dictionary containing old-style display app urls.
        """
        display_apps = []
        if not self.app.config.enable_old_display_applications:
            return display_apps

        display_link_fn = hda.datatype.get_display_links
        for display_app in hda.datatype.get_display_types():
            target_frame, display_links = display_link_fn(hda, display_app, self.app, trans.request.base)

            if len(display_links) > 0:
                display_label = hda.datatype.get_display_label(display_app)

                app_links = []
                for display_name, display_link in display_links:
                    app_links.append({
                        'target': target_frame,
                        'href': display_link,
                        'text': gettext.gettext(display_name)
                    })
                if app_links:
                    display_apps.append(dict(label=display_label, links=app_links))

        return display_apps

    def serialize_visualization_links(self, hda, key, trans=None, **context):
        """
        Return a list of dictionaries with links to visualization pages
        for those visualizations that apply to this hda.
        """
        # use older system if registry is off in the config
        if not self.app.visualizations_registry:
            return hda.get_visualizations()
        return self.app.visualizations_registry.get_visualizations(trans, hda)

    def serialize_urls(self, hda, key, **context):
        """
        Return web controller urls useful for this HDA.
        """
        url_for = self.url_for
        encoded_id = self.app.security.encode_id(hda.id)
        urls = {
            'purge'         : url_for(controller='dataset', action='purge_async', dataset_id=encoded_id),
            'display'       : url_for(controller='dataset', action='display', dataset_id=encoded_id, preview=True),
            'edit'          : url_for(controller='dataset', action='edit', dataset_id=encoded_id),
            'download'      : url_for(controller='dataset', action='display',
                                      dataset_id=encoded_id, to_ext=hda.extension),
            'report_error'  : url_for(controller='dataset', action='errors', id=encoded_id),
            'rerun'         : url_for(controller='tool_runner', action='rerun', id=encoded_id),
            'show_params'   : url_for(controller='dataset', action='show_params', dataset_id=encoded_id),
            'visualization' : url_for(controller='visualization', action='index',
                                      id=encoded_id, model='HistoryDatasetAssociation'),
            'meta_download' : url_for(controller='dataset', action='get_metadata_file',
                                      hda_id=encoded_id, metadata_name=''),
        }
        return urls


class HDADeserializer(datasets.DatasetAssociationDeserializer,
                      taggable.TaggableDeserializerMixin,
                      annotatable.AnnotatableDeserializerMixin):
    """
    Interface/service object for validating and deserializing dictionaries into histories.
    """
    model_manager_class = HDAManager

    def __init__(self, app):
        super(HDADeserializer, self).__init__(app)
        self.hda_manager = self.manager

    def add_deserializers(self):
        super(HDADeserializer, self).add_deserializers()
        taggable.TaggableDeserializerMixin.add_deserializers(self)
        annotatable.AnnotatableDeserializerMixin.add_deserializers(self)

        self.deserializers.update({
            'visible'       : self.deserialize_bool,
            # remapped
            'genome_build'  : lambda i, k, v, **c: self.deserialize_genome_build(i, 'dbkey', v),
            'misc_info'     : lambda i, k, v, **c: self.deserialize_basestring(i, 'info', v,
                                                                               convert_none_to_empty=True),
        })
        self.deserializable_keyset.update(self.deserializers.keys())


class HDAFilterParser(datasets.DatasetAssociationFilterParser,
                      taggable.TaggableFilterMixin,
                      annotatable.AnnotatableFilterMixin):
    model_manager_class = HDAManager
    model_class = model.HistoryDatasetAssociation

    def _add_parsers(self):
        super(HDAFilterParser, self)._add_parsers()
        taggable.TaggableFilterMixin._add_parsers(self)
        annotatable.AnnotatableFilterMixin._add_parsers(self)
