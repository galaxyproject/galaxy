import logging
import os
from datetime import (
    datetime,
    timedelta
)

import tool_shed.repository_types.util as rt_util
from galaxy import util
from galaxy.model.orm.now import now
from galaxy.util import unique_id
from galaxy.util.bunch import Bunch
from galaxy.util.dictifiable import Dictifiable
from galaxy.util.hash_util import new_secure_hash
from tool_shed.dependencies.repository import relation_builder
from tool_shed.util import (
    hg_util,
    metadata_util
)

log = logging.getLogger(__name__)


class APIKeys(object):
    pass


class User(Dictifiable):
    dict_collection_visible_keys = ['id', 'username']
    dict_element_visible_keys = ['id', 'username']

    def __init__(self, email=None, password=None):
        self.email = email
        self.password = password
        self.external = False
        self.deleted = False
        self.purged = False
        self.username = None
        self.new_repo_alert = False

    def all_roles(self):
        roles = [ura.role for ura in self.roles]
        for group in [uga.group for uga in self.groups]:
            for role in [gra.role for gra in group.roles]:
                if role not in roles:
                    roles.append(role)
        return roles

    def check_password(self, cleartext):
        """Check if 'cleartext' matches 'self.password' when hashed."""
        return self.password == new_secure_hash(text_type=cleartext)

    def get_disk_usage(self, nice_size=False):
        return 0

    @property
    def nice_total_disk_usage(self):
        return 0

    def set_disk_usage(self, bytes):
        pass

    total_disk_usage = property(get_disk_usage, set_disk_usage)

    def set_password_cleartext(self, cleartext):
        """Set 'self.password' to the digest of 'cleartext'."""
        self.password = new_secure_hash(text_type=cleartext)


class PasswordResetToken(object):
    def __init__(self, user, token=None):
        if token:
            self.token = token
        else:
            self.token = unique_id()
        self.user = user
        self.expiration_time = now() + timedelta(hours=24)


class Group(Dictifiable):
    dict_collection_visible_keys = ['id', 'name']
    dict_element_visible_keys = ['id', 'name']

    def __init__(self, name=None):
        self.name = name
        self.deleted = False


class Role(Dictifiable):
    dict_collection_visible_keys = ['id', 'name']
    dict_element_visible_keys = ['id', 'name', 'description', 'type']
    private_id = None
    types = Bunch(PRIVATE='private',
                  SYSTEM='system',
                  USER='user',
                  ADMIN='admin',
                  SHARING='sharing')

    def __init__(self, name="", description="", type="system", deleted=False):
        self.name = name
        self.description = description
        self.type = type
        self.deleted = deleted

    @property
    def is_repository_admin_role(self):
        # A repository admin role must always be associated with a repository. The mapper returns an
        # empty list for those roles that have no repositories.  This method will require changes if
        # new features are introduced that results in more than one role per repository.
        if self.repositories:
            return True
        return False


class UserGroupAssociation(object):
    def __init__(self, user, group):
        self.user = user
        self.group = group


class UserRoleAssociation(object):
    def __init__(self, user, role):
        self.user = user
        self.role = role


class GroupRoleAssociation(object):
    def __init__(self, group, role):
        self.group = group
        self.role = role


class RepositoryRoleAssociation(object):
    def __init__(self, repository, role):
        self.repository = repository
        self.role = role


class GalaxySession(object):

    def __init__(self,
                 id=None,
                 user=None,
                 remote_host=None,
                 remote_addr=None,
                 referer=None,
                 current_history=None,
                 session_key=None,
                 is_valid=False,
                 prev_session_id=None,
                 last_action=None):
        self.id = id
        self.user = user
        self.remote_host = remote_host
        self.remote_addr = remote_addr
        self.referer = referer
        self.current_history = current_history
        self.session_key = session_key
        self.is_valid = is_valid
        self.prev_session_id = prev_session_id
        self.last_action = last_action or datetime.now()


class Repository(Dictifiable):
    dict_collection_visible_keys = ['id', 'name', 'type', 'remote_repository_url', 'homepage_url', 'description', 'user_id', 'private', 'deleted',
                                    'times_downloaded', 'deprecated']
    dict_element_visible_keys = ['id', 'name', 'type', 'remote_repository_url', 'homepage_url', 'description', 'long_description', 'user_id', 'private',
                                 'deleted', 'times_downloaded', 'deprecated']
    file_states = Bunch(NORMAL='n',
                        NEEDS_MERGING='m',
                        MARKED_FOR_REMOVAL='r',
                        MARKED_FOR_ADDITION='a',
                        NOT_TRACKED='?')

    def __init__(self, id=None, name=None, type=None, remote_repository_url=None, homepage_url=None,
                 description=None, long_description=None, user_id=None, private=False,
                 deleted=None, email_alerts=None, times_downloaded=0, deprecated=False):
        self.id = id
        self.name = name or "Unnamed repository"
        self.type = type
        self.remote_repository_url = remote_repository_url
        self.homepage_url = homepage_url
        self.description = description
        self.long_description = long_description
        self.user_id = user_id
        self.private = private
        self.deleted = deleted
        self.email_alerts = email_alerts
        self.times_downloaded = times_downloaded
        self.deprecated = deprecated

    @property
    def admin_role(self):
        admin_role_name = '%s_%s_admin' % (str(self.name), str(self.user.username))
        for rra in self.roles:
            role = rra.role
            if str(role.name) == admin_role_name:
                return role
        raise Exception('Repository %s owned by %s is not associated with a required administrative role.' %
                        (str(self.name), str(self.user.username)))

    def allow_push(self, app):
        repo = hg_util.get_repo_for_repository(app, repository=self)
        return repo.ui.config('web', 'allow_push')

    def can_change_type(self, app):
        # Allow changing the type only if the repository has no contents, has never been installed, or has
        # never been changed from the default type.
        if self.is_new(app):
            return True
        if self.times_downloaded == 0:
            return True
        if self.type == rt_util.UNRESTRICTED:
            return True
        return False

    def can_change_type_to(self, app, new_type_label):
        if self.type == new_type_label:
            return False
        if self.can_change_type(app):
            new_type = app.repository_types_registry.get_class_by_label(new_type_label)
            if new_type.is_valid_for_type(app, self):
                return True
        return False

    def get_changesets_for_setting_metadata(self, app):
        type_class = self.get_type_class(app)
        return type_class.get_changesets_for_setting_metadata(app, self)

    def get_repository_dependencies(self, app, changeset, toolshed_url):
        # We aren't concerned with repositories of type tool_dependency_definition here if a
        # repository_metadata record is not returned because repositories of this type will never
        # have repository dependencies. However, if a readme file is uploaded, or some other change
        # is made that does not create a new downloadable changeset revision but updates the existing
        # one, we still want to be able to get repository dependencies.
        repository_metadata = metadata_util.get_current_repository_metadata_for_changeset_revision(app,
                                                                                                   self,
                                                                                                   changeset)
        if repository_metadata:
            metadata = repository_metadata.metadata
            if metadata:
                rb = relation_builder.RelationBuilder(app, self, repository_metadata, toolshed_url)
                repository_dependencies = rb.get_repository_dependencies_for_changeset_revision()
                if repository_dependencies:
                    return repository_dependencies
        return None

    def get_type_class(self, app):
        return app.repository_types_registry.get_class_by_label(self.type)

    def get_tool_dependencies(self, app, changeset_revision):
        changeset_revision = metadata_util.get_next_downloadable_changeset_revision(app, self, changeset_revision)
        for downloadable_revision in self.downloadable_revisions:
            if downloadable_revision.changeset_revision == changeset_revision:
                return downloadable_revision.metadata.get('tool_dependencies', {})
        return {}

    def installable_revisions(self, app, sort_revisions=True):
        return metadata_util.get_metadata_revisions(app, self, sort_revisions=sort_revisions)

    def is_new(self, app):
        repo = hg_util.get_repo_for_repository(app, repository=self)
        tip_ctx = repo.changectx(repo.changelog.tip())
        return tip_ctx.rev() < 0

    def repo_path(self, app):
        return app.hgweb_config_manager.get_entry(os.path.join("repos", self.user.username, self.name))

    def revision(self, app):
        repo = hg_util.get_repo_for_repository(app, repository=self)
        tip_ctx = repo.changectx(repo.changelog.tip())
        return "%s:%s" % (str(tip_ctx.rev()), str(repo.changectx(repo.changelog.tip())))

    def set_allow_push(self, app, usernames, remove_auth=''):
        allow_push = util.listify(self.allow_push(app))
        if remove_auth:
            allow_push.remove(remove_auth)
        else:
            for username in util.listify(usernames):
                if username not in allow_push:
                    allow_push.append(username)
        allow_push = '%s\n' % ','.join(allow_push)
        repo = hg_util.get_repo_for_repository(app, repository=self)
        # Why doesn't the following work?
        # repo.ui.setconfig( 'web', 'allow_push', allow_push )
        lines = repo.opener('hgrc', 'rb').readlines()
        fp = repo.opener('hgrc', 'wb')
        for line in lines:
            if line.startswith('allow_push'):
                fp.write('allow_push = %s' % allow_push)
            else:
                fp.write(line)
        fp.close()

    def tip(self, app):
        repo = hg_util.get_repo_for_repository(app, repository=self)
        return str(repo.changectx(repo.changelog.tip()))

    def to_dict(self, view='collection', value_mapper=None):
        rval = super(Repository, self).to_dict(view=view, value_mapper=value_mapper)
        if 'user_id' in rval:
            rval['owner'] = self.user.username
        return rval


class RepositoryMetadata(Dictifiable):
    dict_collection_visible_keys = ['id', 'repository_id', 'changeset_revision', 'malicious', 'downloadable', 'missing_test_components',
                                    'has_repository_dependencies', 'includes_datatypes', 'includes_tools', 'includes_tool_dependencies',
                                    'includes_tools_for_display_in_tool_panel', 'includes_workflows']
    dict_element_visible_keys = ['id', 'repository_id', 'changeset_revision', 'malicious', 'downloadable', 'missing_test_components',
                                 'has_repository_dependencies', 'includes_datatypes', 'includes_tools', 'includes_tool_dependencies',
                                 'includes_tools_for_display_in_tool_panel', 'includes_workflows', 'repository_dependencies']

    def __init__(self, id=None, repository_id=None, changeset_revision=None, metadata=None, tool_versions=None, malicious=False,
                 downloadable=False, missing_test_components=None, tools_functionally_correct=False, test_install_error=False,
                 has_repository_dependencies=False, includes_datatypes=False, includes_tools=False, includes_tool_dependencies=False,
                 includes_workflows=False):
        self.id = id
        self.repository_id = repository_id
        self.changeset_revision = changeset_revision
        self.metadata = metadata
        self.tool_versions = tool_versions
        self.malicious = malicious
        self.downloadable = downloadable
        self.missing_test_components = missing_test_components
        self.has_repository_dependencies = has_repository_dependencies
        # We don't consider the special case has_repository_dependencies_only_if_compiling_contained_td here.
        self.includes_datatypes = includes_datatypes
        self.includes_tools = includes_tools
        self.includes_tool_dependencies = includes_tool_dependencies
        self.includes_workflows = includes_workflows

    @property
    def includes_tools_for_display_in_tool_panel(self):
        if self.metadata:
            tool_dicts = self.metadata.get('tools', [])
            for tool_dict in tool_dicts:
                if tool_dict.get('add_to_tool_panel', True):
                    return True
        return False

    @property
    def repository_dependencies(self):
        if self.has_repository_dependencies:
            return [repository_dependency for repository_dependency in self.metadata['repository_dependencies']['repository_dependencies']]
        return []


class RepositoryReview(Dictifiable):
    dict_collection_visible_keys = ['id', 'repository_id', 'changeset_revision', 'user_id', 'rating', 'deleted']
    dict_element_visible_keys = ['id', 'repository_id', 'changeset_revision', 'user_id', 'rating', 'deleted']
    approved_states = Bunch(NO='no', YES='yes')

    def __init__(self, repository_id=None, changeset_revision=None, user_id=None, rating=None, deleted=False):
        self.repository_id = repository_id
        self.changeset_revision = changeset_revision
        self.user_id = user_id
        self.rating = rating
        self.deleted = deleted


class ComponentReview(Dictifiable):
    dict_collection_visible_keys = ['id', 'repository_review_id', 'component_id', 'private', 'approved', 'rating', 'deleted']
    dict_element_visible_keys = ['id', 'repository_review_id', 'component_id', 'private', 'approved', 'rating', 'deleted']
    approved_states = Bunch(NO='no', YES='yes', NA='not_applicable')

    def __init__(self, repository_review_id=None, component_id=None, comment=None, private=False, approved=False, rating=None, deleted=False):
        self.repository_review_id = repository_review_id
        self.component_id = component_id
        self.comment = comment
        self.private = private
        self.approved = approved
        self.rating = rating
        self.deleted = deleted


class Component(object):

    def __init__(self, name=None, description=None):
        self.name = name
        self.description = description


class ItemRatingAssociation(object):

    def __init__(self, id=None, user=None, item=None, rating=0, comment=''):
        self.id = id
        self.user = user
        self.item = item
        self.rating = rating
        self.comment = comment

    def set_item(self, item):
        """ Set association's item. """
        pass


class RepositoryRatingAssociation(ItemRatingAssociation):

    def set_item(self, repository):
        self.repository = repository


class Category(Dictifiable):
    dict_collection_visible_keys = ['id', 'name', 'description', 'deleted']
    dict_element_visible_keys = ['id', 'name', 'description', 'deleted']

    def __init__(self, name=None, description=None, deleted=False):
        self.name = name
        self.description = description
        self.deleted = deleted


class RepositoryCategoryAssociation(object):

    def __init__(self, repository=None, category=None):
        self.repository = repository
        self.category = category


class Tag(object):

    def __init__(self, id=None, type=None, parent_id=None, name=None):
        self.id = id
        self.type = type
        self.parent_id = parent_id
        self.name = name

    def __str__(self):
        return "Tag(id=%s, type=%i, parent_id=%s, name=%s)" % (self.id, self.type, self.parent_id, self.name)


class ItemTagAssociation(object):

    def __init__(self, id=None, user=None, item_id=None, tag_id=None, user_tname=None, value=None):
        self.id = id
        self.user = user
        self.item_id = item_id
        self.tag_id = tag_id
        self.user_tname = user_tname
        self.value = None
        self.user_value = None


class PostJobAction(object):

    def __init__(self, action_type, workflow_step, output_name=None, action_arguments=None):
        self.action_type = action_type
        self.output_name = output_name
        self.action_arguments = action_arguments
        self.workflow_step = workflow_step


class StoredWorkflowAnnotationAssociation(object):
    pass


class WorkflowStepAnnotationAssociation(object):
    pass


class Workflow(object):

    def __init__(self):
        self.user = None
        self.name = None
        self.has_cycles = None
        self.has_errors = None
        self.steps = []


class WorkflowStep(object):

    def __init__(self):
        self.id = None
        self.type = None
        self.name = None
        self.tool_id = None
        self.tool_inputs = None
        self.tool_errors = None
        self.position = None
        self.inputs = []
        self.config = None
        self.label = None

    def get_or_add_input(self, input_name):
        for step_input in self.inputs:
            if step_input.name == input_name:
                return step_input

        step_input = WorkflowStepInput()
        step_input.workflow_step = self
        step_input.name = input_name
        self.inputs.append(step_input)
        return step_input

    @property
    def input_connections(self):
        connections = [_ for step_input in self.inputs for _ in step_input.connections]
        return connections


class WorkflowStepInput(object):

    def __init__(self):
        self.id = None
        self.name = None
        self.connections = []


class WorkflowStepConnection(object):

    def __init__(self):
        self.output_step = None
        self.output_name = None
        self.input_step = None
        self.input_name = None


# Utility methods
def sort_by_attr(seq, attr):
    """
    Sort the sequence of objects by object's attribute
    Arguments:
    seq  - the list or any sequence (including immutable one) of objects to sort.
    attr - the name of attribute to sort by
    """
    # Use the "Schwartzian transform"
    # Create the auxiliary list of tuples where every i-th tuple has form
    # (seq[i].attr, i, seq[i]) and sort it. The second item of tuple is needed not
    # only to provide stable sorting, but mainly to eliminate comparison of objects
    # (which can be expensive or prohibited) in case of equal attribute values.
    intermed = [(getattr(v, attr), i, v) for i, v in enumerate(seq)]
    intermed.sort()
    return [_[-1] for _ in intermed]
