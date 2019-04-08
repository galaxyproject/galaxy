"""
Galaxy data model classes

Naming: try to use class names that have a distinct plural form so that
the relationship cardinalities are obvious (e.g. prefer Dataset to Data)
"""
import base64
import errno
import json
import logging
import numbers
import operator
import os
import pwd
import random
import string
import time
from datetime import datetime, timedelta
from string import Template
from uuid import UUID, uuid4

from boltons.iterutils import remap
from six import string_types
from social_core.storage import AssociationMixin, CodeMixin, NonceMixin, PartialMixin, UserMixin
from sqlalchemy import (
    alias,
    and_,
    func,
    inspect,
    join,
    not_,
    or_,
    select,
    true,
    type_coerce,
    types)
from sqlalchemy.ext import hybrid
from sqlalchemy.orm import (
    aliased,
    joinedload,
    object_session,
)
from sqlalchemy.schema import UniqueConstraint

import galaxy.model.metadata
import galaxy.model.orm.now
import galaxy.model.tags
import galaxy.security.passwords
import galaxy.util
from galaxy.model.item_attrs import get_item_annotation_str, UsesAnnotations
from galaxy.model.util import pgcalc
from galaxy.security import get_permitted_actions
from galaxy.util import (directory_hash_id, ready_name_for_url,
                         unicodify, unique_id)
from galaxy.util.bunch import Bunch
from galaxy.util.dictifiable import dict_for, Dictifiable
from galaxy.util.form_builder import (AddressField, CheckboxField, HistoryField,
                                      PasswordField, SelectField, TextArea, TextField, WorkflowField,
                                      WorkflowMappingField)
from galaxy.util.hash_util import new_secure_hash
from galaxy.util.json import safe_loads
from galaxy.util.sanitize_html import sanitize_html

log = logging.getLogger(__name__)

_datatypes_registry = None

# When constructing filters with in for a fixed set of ids, maximum
# number of items to place in the IN statement. Different databases
# are going to have different limits so it is likely best to not let
# this be unlimited - filter in Python if over this limit.
MAX_IN_FILTER_LENGTH = 100

# The column sizes for job metrics. Note: changing these values does not change the column sizes, a migration must be
# performed to do that.
JOB_METRIC_MAX_LENGTH = 1023
JOB_METRIC_PRECISION = 26
JOB_METRIC_SCALE = 7
# Tags that get automatically propagated from inputs to outputs when running jobs.
AUTO_PROPAGATED_TAGS = ["name"]


class RepresentById(object):
    def __repr__(self):
        try:
            r = '<galaxy.model.%s(%s) at %s>' % (self.__class__.__name__, cached_id(self), hex(id(self)))
        except Exception:
            r = object.__repr__(self)
            log.exception("Caught exception attempting to generate repr for: %s", r)
        return r


class NoConverterException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class ConverterDependencyException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def _get_datatypes_registry():
    if _datatypes_registry is None:
        raise Exception("galaxy.model.set_datatypes_registry must be called before performing certain DatasetInstance operations.")
    return _datatypes_registry


def set_datatypes_registry(d_registry):
    """
    Set up datatypes_registry
    """
    global _datatypes_registry
    _datatypes_registry = d_registry


class HasTags(object):
    dict_collection_visible_keys = ['tags']
    dict_element_visible_keys = ['tags']

    def to_dict(self, *args, **kwargs):
        rval = super(HasTags, self).to_dict(*args, **kwargs)
        rval['tags'] = self.make_tag_string_list()
        return rval

    def make_tag_string_list(self):
        # add tags string list
        tags_str_list = []
        for tag in self.tags:
            tag_str = tag.user_tname
            if tag.value is not None:
                tag_str += ":" + tag.user_value
            tags_str_list.append(tag_str)
        return tags_str_list

    def copy_tags_from(self, target_user, source):
        for source_tag_assoc in source.tags:
            new_tag_assoc = source_tag_assoc.copy()
            new_tag_assoc.user = target_user
            self.tags.append(new_tag_assoc)

    @property
    def auto_propagated_tags(self):
        return [t for t in self.tags if t.user_tname in AUTO_PROPAGATED_TAGS]


class SerializationOptions(object):

    def __init__(self, for_edit, serialize_dataset_objects=None, serialize_files_handler=None):
        self.for_edit = for_edit
        if serialize_dataset_objects is None:
            serialize_dataset_objects = for_edit
        self.serialize_dataset_objects = serialize_dataset_objects
        self.serialize_files_handler = serialize_files_handler

    def attach_identifier(self, id_encoder, obj, ret_val):
        if self.for_edit and obj.id:
            ret_val["id"] = obj.id
        elif obj.id:
            ret_val["encoded_id"] = id_encoder.encode_id(obj.id, kind='model_export')
        else:
            if not hasattr(obj, "temp_id"):
                obj.temp_id = uuid4().hex
            ret_val["encoded_id"] = obj.temp_id

    def get_identifier(self, id_encoder, obj):
        if self.for_edit and obj.id:
            return obj.id
        elif obj.id:
            return id_encoder.encode_id(obj.id, kind='model_export')
        else:
            if not hasattr(obj, "temp_id"):
                obj.temp_id = uuid4().hex
            return obj.temp_id

    def get_identifier_for_id(self, id_encoder, obj_id):
        if self.for_edit and obj_id:
            return obj_id
        elif obj_id:
            return id_encoder.encode_id(obj_id, kind='model_export')
        else:
            raise NotImplementedError()

    def serialize_files(self, dataset, as_dict):
        if self.serialize_files_handler is not None:
            self.serialize_files_handler.serialize_files(dataset, as_dict)


class HasName(object):

    def get_display_name(self):
        """
        These objects have a name attribute can be either a string or a unicode
        object. If string, convert to unicode object assuming 'utf-8' format.
        """
        name = self.name
        name = unicodify(name, 'utf-8')
        return name


class UsesCreateAndUpdateTime(object):

    @property
    def seconds_since_updated(self):
        update_time = self.update_time or galaxy.model.orm.now.now()  # In case not yet flushed
        return (galaxy.model.orm.now.now() - update_time).total_seconds()

    @property
    def seconds_since_created(self):
        create_time = self.create_time or galaxy.model.orm.now.now()  # In case not yet flushed
        return (galaxy.model.orm.now.now() - create_time).total_seconds()


class WorkerProcess(UsesCreateAndUpdateTime):

    def __init__(self, server_name):
        self.server_name = server_name


def cached_id(galaxy_model_object):
    """Get model object id attribute without a firing a database query.

    Useful to fetching the id of a typical Galaxy model object after a flush,
    where SA is going to mark the id attribute as unloaded but we know the id
    is immutable and so we can use the database identity to fetch.

    With Galaxy's default SA initialization - any flush marks all attributes as
    unloaded - even objects completely unrelated to the flushed changes and
    even attributes we know to be immutable like id. See test_galaxy_mapping.py
    for verification of this behavior. This method is a workaround that uses
    the fact that we know all Galaxy objects use the id attribute as identity
    and SA internals (_sa_instance_state) to infer the previously loaded ID
    value. I tried digging into the SA internals extensively and couldn't find
    a way to get the previously loaded values after a flush to allow a
    generalization of this for other attributes.
    """
    if hasattr(galaxy_model_object, "_sa_instance_state"):
        identity = galaxy_model_object._sa_instance_state.identity
        if identity:
            assert len(identity) == 1
            return identity[0]

    return galaxy_model_object.id


class JobLike(object):
    MAX_NUMERIC = 10**(JOB_METRIC_PRECISION - JOB_METRIC_SCALE) - 1

    def _init_metrics(self):
        self.text_metrics = []
        self.numeric_metrics = []

    def add_metric(self, plugin, metric_name, metric_value):
        plugin = unicodify(plugin, 'utf-8')
        metric_name = unicodify(metric_name, 'utf-8')
        number = isinstance(metric_value, numbers.Number)
        if number and int(metric_value) <= JobLike.MAX_NUMERIC:
            metric = self._numeric_metric(plugin, metric_name, metric_value)
            self.numeric_metrics.append(metric)
        elif number:
            log.warning("Cannot store metric due to database column overflow (max: %s): %s: %s",
                        JobLike.MAX_NUMERIC, metric_name, metric_value)
        else:
            metric_value = unicodify(metric_value, 'utf-8')
            if len(metric_value) > (JOB_METRIC_MAX_LENGTH - 1):
                # Truncate these values - not needed with sqlite
                # but other backends must need it.
                metric_value = metric_value[:(JOB_METRIC_MAX_LENGTH - 1)]
            metric = self._text_metric(plugin, metric_name, metric_value)
            self.text_metrics.append(metric)

    @property
    def metrics(self):
        # TODO: Make iterable, concatenate with chain
        return self.text_metrics + self.numeric_metrics

    def set_streams(self, tool_stdout, tool_stderr, job_stdout=None, job_stderr=None, job_messages=None):
        def shrink_and_unicodify(what, stream):
            stream = galaxy.util.unicodify(stream) or u''
            if (len(stream) > galaxy.util.DATABASE_MAX_STRING_SIZE):
                stream = galaxy.util.shrink_string_by_size(tool_stdout, galaxy.util.DATABASE_MAX_STRING_SIZE, join_by="\n..\n", left_larger=True, beginning_on_size_error=True)
                log.info("%s for %s %d is greater than %s, only a portion will be logged to database", what, type(self), self.id, galaxy.util.DATABASE_MAX_STRING_SIZE_PRETTY)
            return stream

        self.tool_stdout = shrink_and_unicodify('tool_stdout', tool_stdout)
        self.tool_stderr = shrink_and_unicodify('tool_stderr', tool_stderr)
        if job_stdout is not None:
            self.job_stdout = shrink_and_unicodify('job_stdout', job_stdout)
        else:
            self.job_stdout = None

        if job_stderr is not None:
            self.job_stderr = shrink_and_unicodify('job_stderr', job_stderr)
        else:
            self.job_stderr = None

        if job_messages is not None:
            self.job_messages = job_messages

    def log_str(self):
        extra = ""
        safe_id = getattr(self, "id", None)
        if safe_id is not None:
            extra += "id=%s" % safe_id
        else:
            extra += "unflushed"

        return "%s[%s,tool_id=%s]" % (self.__class__.__name__, extra, self.tool_id)

    def get_stdout(self):
        stdout = self.tool_stdout
        if self.job_stdout:
            stdout += "\n" + self.job_stdout
        return stdout

    def set_stdout(self, stdout):
        raise NotImplementedError("Attempt to set stdout, must set tool_stdout or job_stdout")

    def get_stderr(self):
        stderr = self.tool_stderr
        if self.job_stderr:
            stderr += "\n" + self.job_stderr
        return stderr

    def set_stderr(self, stderr):
        raise NotImplementedError("Attempt to set stdout, must set tool_stderr or job_stderr")

    stdout = property(get_stdout, set_stdout)
    stderr = property(get_stderr, set_stderr)


class User(Dictifiable, RepresentById):
    use_pbkdf2 = True
    """
    Data for a Galaxy user or admin and relations to their
    histories, credentials, and roles.
    """
    # attributes that will be accessed and returned when calling to_dict( view='collection' )
    dict_collection_visible_keys = ['id', 'email', 'username', 'deleted', 'active', 'last_password_change']
    # attributes that will be accessed and returned when calling to_dict( view='element' )
    dict_element_visible_keys = ['id', 'email', 'username', 'total_disk_usage', 'nice_total_disk_usage', 'deleted', 'active', 'last_password_change']

    def __init__(self, email=None, password=None, username=None):
        self.email = email
        self.password = password
        self.external = False
        self.deleted = False
        self.purged = False
        self.active = False
        self.activation_token = None
        self.username = username
        self.last_password_change = None
        # Relationships
        self.histories = []
        self.credentials = []
        # ? self.roles = []

    @property
    def extra_preferences(self):
        data = {}
        extra_user_preferences = self.preferences.get('extra_user_preferences')
        if extra_user_preferences:
            try:
                data = json.loads(extra_user_preferences)
            except Exception:
                pass
        return data

    def set_password_cleartext(self, cleartext):
        """
        Set user password to the digest of `cleartext`.
        """
        if User.use_pbkdf2:
            self.password = galaxy.security.passwords.hash_password(cleartext)
        else:
            self.password = new_secure_hash(text_type=cleartext)
        self.last_password_change = datetime.now()

    def set_random_password(self, length=16):
        """
        Sets user password to a random string of the given length.
        :return: void
        """
        self.set_password_cleartext(
            ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(length)))

    def check_password(self, cleartext):
        """
        Check if `cleartext` matches user password when hashed.
        """
        return galaxy.security.passwords.check_password(cleartext, self.password)

    def system_user_pwent(self, real_system_username):
        """
        Gives the system user pwent entry based on e-mail or username depending
        on the value in real_system_username
        """
        system_user_pwent = None
        if real_system_username == 'user_email':
            try:
                system_user_pwent = pwd.getpwnam(self.email.split('@')[0])
            except KeyError:
                pass
        elif real_system_username == 'username':
            try:
                system_user_pwent = pwd.getpwnam(self.username)
            except KeyError:
                pass
        else:
            try:
                system_user_pwent = pwd.getpwnam(real_system_username)
            except KeyError:
                log.warning("invalid configuration of real_system_username")
                system_user_pwent = None
                pass
        return system_user_pwent

    def all_roles(self):
        """
        Return a unique list of Roles associated with this user or any of their groups.
        """
        try:
            db_session = object_session(self)
            user = db_session.query(
                User
            ).filter_by(  # don't use get, it will use session variant.
                id=self.id
            ).options(
                joinedload("roles"),
                joinedload("roles.role"),
                joinedload("groups"),
                joinedload("groups.group"),
                joinedload("groups.group.roles"),
                joinedload("groups.group.roles.role")
            ).one()
        except Exception:
            # If not persistent user, just use models normaly and
            # skip optimizations...
            user = self

        roles = [ura.role for ura in user.roles]
        for group in [uga.group for uga in user.groups]:
            for role in [gra.role for gra in group.roles]:
                if role not in roles:
                    roles.append(role)
        return roles

    def all_roles_exploiting_cache(self):
        """
        """
        roles = [ura.role for ura in self.roles]
        for group in [uga.group for uga in self.groups]:
            for role in [gra.role for gra in group.roles]:
                if role not in roles:
                    roles.append(role)
        return roles

    def get_disk_usage(self, nice_size=False):
        """
        Return byte count of disk space used by user or a human-readable
        string if `nice_size` is `True`.
        """
        rval = 0
        if self.disk_usage is not None:
            rval = self.disk_usage
        if nice_size:
            rval = galaxy.util.nice_size(rval)
        return rval

    def set_disk_usage(self, bytes):
        """
        Manually set the disk space used by a user to `bytes`.
        """
        self.disk_usage = bytes

    total_disk_usage = property(get_disk_usage, set_disk_usage)

    def adjust_total_disk_usage(self, amount):
        if amount != 0:
            self.disk_usage = func.coalesce(self.table.c.disk_usage, 0) + amount

    @property
    def nice_total_disk_usage(self):
        """
        Return byte count of disk space used in a human-readable string.
        """
        return self.get_disk_usage(nice_size=True)

    def calculate_disk_usage(self):
        """
        Return byte count total of disk space used by all non-purged, non-library
        HDAs in non-purged histories.
        """
        # maintain a list so that we don't double count
        dataset_ids = []
        total = 0
        # this can be a huge number and can run out of memory, so we avoid the mappers
        db_session = object_session(self)
        for history in db_session.query(History).enable_eagerloads(False).filter_by(user_id=self.id, purged=False).yield_per(1000):
            for hda in db_session.query(HistoryDatasetAssociation).enable_eagerloads(False).filter_by(history_id=history.id, purged=False).yield_per(1000):
                # TODO: def hda.counts_toward_disk_usage():
                #   return ( not self.dataset.purged and not self.dataset.library_associations )
                if hda.dataset.id not in dataset_ids and not hda.dataset.purged and not hda.dataset.library_associations:
                    dataset_ids.append(hda.dataset.id)
                    total += hda.dataset.get_total_size()
        return total

    def calculate_and_set_disk_usage(self):
        """
        Calculates and sets user disk usage.
        """
        new = None
        db_session = object_session(self)
        current = self.get_disk_usage()
        if db_session.get_bind().dialect.name not in ('postgres', 'postgresql'):
            done = False
            while not done:
                new = self.calculate_disk_usage()
                db_session.refresh(self)
                # make sure usage didn't change while calculating
                # set done if it has not, otherwise reset current and iterate again.
                if self.get_disk_usage() == current:
                    done = True
                else:
                    current = self.get_disk_usage()
        else:
            new = pgcalc(db_session, self.id)
        if new not in (current, None):
            self.set_disk_usage(new)
            db_session.add(self)
            db_session.flush()

    @staticmethod
    def user_template_environment(user):
        """

        >>> env = User.user_template_environment(None)
        >>> env['__user_email__']
        'Anonymous'
        >>> env['__user_id__']
        'Anonymous'
        >>> user = User('foo@example.com')
        >>> user.id = 6
        >>> user.username = 'foo2'
        >>> env = User.user_template_environment(user)
        >>> env['__user_id__']
        '6'
        >>> env['__user_name__']
        'foo2'
        """
        if user:
            user_id = '%d' % user.id
            user_email = str(user.email)
            user_name = str(user.username)
        else:
            user = None
            user_id = 'Anonymous'
            user_email = 'Anonymous'
            user_name = 'Anonymous'
        environment = {}
        environment['__user__'] = user
        environment['__user_id__'] = environment['userId'] = user_id
        environment['__user_email__'] = environment['userEmail'] = user_email
        environment['__user_name__'] = user_name
        return environment

    @staticmethod
    def expand_user_properties(user, in_string):
        """
        """
        environment = User.user_template_environment(user)
        return Template(in_string).safe_substitute(environment)

    def is_active(self):
        return self.active

    def is_authenticated(self):
        # TODO: is required for python social auth (PSA); however, a user authentication is relative to the backend.
        # For instance, a user who is authenticated with Google, is not necessarily authenticated
        # with Amazon. Therefore, this function should also receive the backend and check if this
        # user is already authenticated on that backend or not. For now, returning always True
        # seems reasonable. Besides, this is also how a PSA example is implemented:
        # https://github.com/python-social-auth/social-examples/blob/master/example-cherrypy/example/db/user.py
        return True


class PasswordResetToken(object):
    def __init__(self, user, token=None):
        if token:
            self.token = token
        else:
            self.token = unique_id()
        self.user = user
        self.expiration_time = galaxy.model.orm.now.now() + timedelta(hours=24)


class DynamicTool(Dictifiable):
    dict_collection_visible_keys = ('id', 'tool_id', 'tool_format', 'tool_version', 'uuid', 'active', 'hidden')
    dict_element_visible_keys = ('id', 'tool_id', 'tool_format', 'tool_version', 'uuid', 'active', 'hidden')

    def __init__(self, tool_format=None, tool_id=None, tool_version=None,
                 uuid=None, active=True, hidden=True, value=None):
        self.tool_format = tool_format
        self.tool_id = tool_id
        self.tool_version = tool_version
        self.active = active
        self.hidden = hidden
        self.value = value
        if uuid is None:
            self.uuid = uuid4()
        else:
            self.uuid = UUID(str(uuid))


class BaseJobMetric(object):

    def __init__(self, plugin, metric_name, metric_value):
        self.plugin = plugin
        self.metric_name = metric_name
        self.metric_value = metric_value


class JobMetricText(BaseJobMetric, RepresentById):
    pass


class JobMetricNumeric(BaseJobMetric, RepresentById):
    pass


class TaskMetricText(BaseJobMetric, RepresentById):
    pass


class TaskMetricNumeric(BaseJobMetric, RepresentById):
    pass


class Job(JobLike, UsesCreateAndUpdateTime, Dictifiable, RepresentById):
    dict_collection_visible_keys = ['id', 'state', 'exit_code', 'update_time', 'create_time']
    dict_element_visible_keys = ['id', 'state', 'exit_code', 'update_time', 'create_time']

    """
    A job represents a request to run a tool given input datasets, tool
    parameters, and output datasets.
    """
    _numeric_metric = JobMetricNumeric
    _text_metric = JobMetricText

    states = Bunch(NEW='new',
                   RESUBMITTED='resubmitted',
                   UPLOAD='upload',
                   WAITING='waiting',
                   QUEUED='queued',
                   RUNNING='running',
                   OK='ok',
                   ERROR='error',
                   FAILED='failed',
                   PAUSED='paused',
                   DELETED='deleted',
                   DELETED_NEW='deleted_new')
    terminal_states = [states.OK,
                       states.ERROR,
                       states.DELETED]
    #: job states where the job hasn't finished and the model may still change
    non_ready_states = [
        states.NEW,
        states.RESUBMITTED,
        states.UPLOAD,
        states.WAITING,
        states.QUEUED,
        states.RUNNING,
    ]

    # Please include an accessor (get/set pair) for any new columns/members.
    def __init__(self):
        self.session_id = None
        self.user_id = None
        self.tool_id = None
        self.tool_version = None
        self.copied_from_job_id = None
        self.command_line = None
        self.dependencies = []
        self.param_filename = None
        self.parameters = []
        self.input_datasets = []
        self.output_datasets = []
        self.input_dataset_collections = []
        self.output_dataset_collection_instances = []
        self.output_dataset_collections = []
        self.input_library_datasets = []
        self.output_library_datasets = []
        self.state = Job.states.NEW
        self.info = None
        self.job_runner_name = None
        self.job_runner_external_id = None
        self.destination_id = None
        self.destination_params = None
        self.post_job_actions = []
        self.state_history = []
        self.imported = False
        self.handler = None
        self.exit_code = None
        self.job_messages = None
        self._init_metrics()
        self.state_history.append(JobStateHistory(self))

    @property
    def finished(self):
        states = self.states
        return self.state in [
            states.OK,
            states.ERROR,
            states.DELETED,
            states.DELETED_NEW,
        ]

    def io_dicts(self):
        inp_data = dict([(da.name, da.dataset) for da in self.input_datasets])
        out_data = dict([(da.name, da.dataset) for da in self.output_datasets])
        inp_data.update([(da.name, da.dataset) for da in self.input_library_datasets])
        out_data.update([(da.name, da.dataset) for da in self.output_library_datasets])

        out_collections = dict([(obj.name, obj.dataset_collection_instance) for obj in self.output_dataset_collection_instances])
        out_collections.update([(obj.name, obj.dataset_collection) for obj in self.output_dataset_collections])
        return inp_data, out_data, out_collections

    # TODO: Add accessors for members defined in SQL Alchemy for the Job table and
    # for the mapper defined to the Job table.
    def get_external_output_metadata(self):
        """
        The external_output_metadata is currently a reference from Job to
        JobExternalOutputMetadata. It exists for a job but not a task.
        """
        return self.external_output_metadata

    def get_session_id(self):
        return self.session_id

    def get_user_id(self):
        return self.user_id

    def get_tool_id(self):
        return self.tool_id

    def get_tool_version(self):
        return self.tool_version

    def get_command_line(self):
        return self.command_line

    def get_dependencies(self):
        return self.dependencies

    def get_param_filename(self):
        return self.param_filename

    def get_parameters(self):
        return self.parameters

    def get_copied_from_job_id(self):
        return self.copied_from_job_id

    def get_input_datasets(self):
        return self.input_datasets

    def get_output_datasets(self):
        return self.output_datasets

    def get_input_library_datasets(self):
        return self.input_library_datasets

    def get_output_library_datasets(self):
        return self.output_library_datasets

    def get_state(self):
        return self.state

    def get_info(self):
        return self.info

    def get_job_runner_name(self):
        # This differs from the Task class in that job_runner_name is
        # accessed instead of task_runner_name. Note that the field
        # runner_name is not the same thing.
        return self.job_runner_name

    def get_job_runner_external_id(self):
        # This is different from the Task just in the member accessed:
        return self.job_runner_external_id

    def get_post_job_actions(self):
        return self.post_job_actions

    def get_imported(self):
        return self.imported

    def get_handler(self):
        return self.handler

    def get_params(self):
        return self.params

    def get_user(self):
        # This is defined in the SQL Alchemy mapper as a relation to the User.
        return self.user

    def get_tasks(self):
        # The tasks member is pert of a reference in the SQL Alchemy schema:
        return self.tasks

    def get_id_tag(self):
        """
        Return a tag that can be useful in identifying a Job.
        This returns the Job's get_id
        """
        return "%s" % self.id

    def set_session_id(self, session_id):
        self.session_id = session_id

    def set_user_id(self, user_id):
        self.user_id = user_id

    def set_tool_id(self, tool_id):
        self.tool_id = tool_id

    def set_tool_version(self, tool_version):
        self.tool_version = tool_version

    def set_command_line(self, command_line):
        self.command_line = command_line

    def set_dependencies(self, dependencies):
        self.dependencies = dependencies

    def set_param_filename(self, param_filename):
        self.param_filename = param_filename

    def set_parameters(self, parameters):
        self.parameters = parameters

    def set_copied_from_job_id(self, job_id):
        self.copied_from_job_id = job_id

    def set_input_datasets(self, input_datasets):
        self.input_datasets = input_datasets

    def set_output_datasets(self, output_datasets):
        self.output_datasets = output_datasets

    def set_input_library_datasets(self, input_library_datasets):
        self.input_library_datasets = input_library_datasets

    def set_output_library_datasets(self, output_library_datasets):
        self.output_library_datasets = output_library_datasets

    def set_info(self, info):
        self.info = info

    def set_runner_name(self, job_runner_name):
        self.job_runner_name = job_runner_name

    def get_job(self):
        # Added so job and task have same interface (.get_job() ) to get at
        # underlying job object.
        return self

    def set_runner_external_id(self, job_runner_external_id):
        self.job_runner_external_id = job_runner_external_id

    def set_post_job_actions(self, post_job_actions):
        self.post_job_actions = post_job_actions

    def set_imported(self, imported):
        self.imported = imported

    def set_handler(self, handler):
        self.handler = handler

    def set_params(self, params):
        self.params = params

    def add_parameter(self, name, value):
        self.parameters.append(JobParameter(name, value))

    def add_input_dataset(self, name, dataset=None, dataset_id=None):
        assoc = JobToInputDatasetAssociation(name, dataset)
        if dataset is None and dataset_id is not None:
            assoc.dataset_id = dataset_id
        self.input_datasets.append(assoc)

    def add_output_dataset(self, name, dataset):
        self.output_datasets.append(JobToOutputDatasetAssociation(name, dataset))

    def add_input_dataset_collection(self, name, dataset_collection):
        self.input_dataset_collections.append(JobToInputDatasetCollectionAssociation(name, dataset_collection))

    def add_output_dataset_collection(self, name, dataset_collection_instance):
        self.output_dataset_collection_instances.append(JobToOutputDatasetCollectionAssociation(name, dataset_collection_instance))

    def add_implicit_output_dataset_collection(self, name, dataset_collection):
        self.output_dataset_collections.append(JobToImplicitOutputDatasetCollectionAssociation(name, dataset_collection))

    def add_input_library_dataset(self, name, dataset):
        self.input_library_datasets.append(JobToInputLibraryDatasetAssociation(name, dataset))

    def add_output_library_dataset(self, name, dataset):
        self.output_library_datasets.append(JobToOutputLibraryDatasetAssociation(name, dataset))

    def add_post_job_action(self, pja):
        self.post_job_actions.append(PostJobActionAssociation(pja, self))

    def set_state(self, state):
        """
        Save state history
        """
        self.state = state
        self.state_history.append(JobStateHistory(self))

    def get_param_values(self, app, ignore_errors=False):
        """
        Read encoded parameter values from the database and turn back into a
        dict of tool parameter values.
        """
        param_dict = self.raw_param_dict()
        tool = app.toolbox.get_tool(self.tool_id, tool_version=self.tool_version)
        param_dict = tool.params_from_strings(param_dict, app, ignore_errors=ignore_errors)
        return param_dict

    def raw_param_dict(self):
        param_dict = dict([(p.name, p.value) for p in self.parameters])
        return param_dict

    def check_if_output_datasets_deleted(self):
        """
        Return true if all of the output datasets associated with this job are
        in the deleted state
        """
        for dataset_assoc in self.output_datasets:
            dataset = dataset_assoc.dataset
            # only the originator of the job can delete a dataset to cause
            # cancellation of the job, no need to loop through history_associations
            if not dataset.deleted:
                return False
        return True

    def mark_deleted(self, track_jobs_in_database=False):
        """
        Mark this job as deleted, and mark any output datasets as discarded.
        """
        if self.finished:
            # Do not modify the state/outputs of jobs that are already terminal
            return
        if track_jobs_in_database:
            self.state = Job.states.DELETED_NEW
        else:
            self.state = Job.states.DELETED
        self.info = "Job output deleted by user before job completed."
        for dataset_assoc in self.output_datasets:
            dataset = dataset_assoc.dataset
            dataset.deleted = True
            dataset.state = dataset.states.DISCARDED
            for dataset in dataset.dataset.history_associations:
                # propagate info across shared datasets
                dataset.deleted = True
                dataset.blurb = 'deleted'
                dataset.peek = 'Job deleted'
                dataset.info = 'Job output deleted by user before job completed'

    def mark_failed(self, info="Job execution failed", blurb=None, peek=None):
        """
        Mark this job as failed, and mark any output datasets as errored.
        """
        self.state = self.states.FAILED
        self.info = info
        for jtod in self.output_datasets:
            jtod.dataset.state = jtod.dataset.states.ERROR
            for hda in jtod.dataset.dataset.history_associations:
                hda.state = hda.states.ERROR
                if blurb:
                    hda.blurb = blurb
                if peek:
                    hda.peek = peek
                hda.info = info

    def resume(self, flush=True):
        if self.state == self.states.PAUSED:
            self.set_state(self.states.NEW)
            object_session(self).add(self)
            for dataset in self.output_datasets:
                dataset.info = None
            if flush:
                object_session(self).flush()

    def serialize(self, id_encoder, serialization_options):
        job_attrs = dict_for(self)
        serialization_options.attach_identifier(id_encoder, self, job_attrs)
        job_attrs['tool_id'] = self.tool_id
        job_attrs['tool_version'] = self.tool_version
        job_attrs['state'] = self.state
        job_attrs['info'] = self.info
        job_attrs['traceback'] = self.traceback
        job_attrs['command_line'] = self.command_line
        job_attrs['tool_stderr'] = self.tool_stderr
        job_attrs['job_stderr'] = self.job_stderr
        job_attrs['tool_stdout'] = self.tool_stdout
        job_attrs['job_stdout'] = self.job_stdout
        job_attrs['exit_code'] = self.exit_code
        job_attrs['create_time'] = self.create_time.isoformat()
        job_attrs['update_time'] = self.update_time.isoformat()

        # Get the job's parameters
        param_dict = self.raw_param_dict()
        params_objects = {}
        for key in param_dict:
            params_objects[key] = safe_loads(param_dict[key])

        def remap_objects(p, k, obj):
            if isinstance(obj, dict) and "src" in obj and obj["src"] in ["hda", "hdca"]:
                new_id = serialization_options.get_identifier_for_id(id_encoder, obj["id"])
                new_obj = obj.copy()
                new_obj["id"] = new_id
                return (k, new_obj)
            return (k, obj)

        params_objects = remap(params_objects, remap_objects)

        params_dict = {}
        for name, value in params_objects.items():
            params_dict[name] = value
        job_attrs['params'] = params_dict
        return job_attrs

    def to_dict(self, view='collection', system_details=False):
        rval = super(Job, self).to_dict(view=view)
        rval['tool_id'] = self.tool_id
        rval['history_id'] = self.history_id
        if system_details:
            # System level details that only admins should have.
            rval['external_id'] = self.job_runner_external_id
            rval['command_line'] = self.command_line

        if view == 'element':
            param_dict = dict([(p.name, p.value) for p in self.parameters])
            rval['params'] = param_dict

            input_dict = {}
            for i in self.input_datasets:
                if i.dataset is not None:
                    input_dict[i.name] = {
                        "id" : i.dataset.id, "src" : "hda",
                        "uuid" : str(i.dataset.dataset.uuid) if i.dataset.dataset.uuid is not None else None
                    }
            for i in self.input_library_datasets:
                if i.dataset is not None:
                    input_dict[i.name] = {
                        "id" : i.dataset.id, "src" : "ldda",
                        "uuid": str(i.dataset.dataset.uuid) if i.dataset.dataset.uuid is not None else None
                    }
            for k in input_dict:
                if k in param_dict:
                    del param_dict[k]
            rval['inputs'] = input_dict

            output_dict = {}
            for i in self.output_datasets:
                if i.dataset is not None:
                    output_dict[i.name] = {
                        "id" : i.dataset.id, "src" : "hda",
                        "uuid" : str(i.dataset.dataset.uuid) if i.dataset.dataset.uuid is not None else None
                    }
            for i in self.output_library_datasets:
                if i.dataset is not None:
                    output_dict[i.name] = {
                        "id" : i.dataset.id, "src" : "ldda",
                        "uuid" : str(i.dataset.dataset.uuid) if i.dataset.dataset.uuid is not None else None
                    }
            rval['outputs'] = output_dict

        return rval

    def set_final_state(self, final_state):
        self.set_state(final_state)
        if self.workflow_invocation_step:
            self.workflow_invocation_step.update()

    def get_destination_configuration(self, dest_params, config, key, default=None):
        """ Get a destination parameter that can be defaulted back
        in specified config if it needs to be applied globally.
        """
        param_unspecified = object()
        config_value = (self.destination_params or {}).get(key, param_unspecified)
        if config_value is param_unspecified:
            config_value = dest_params.get(key, param_unspecified)
        if config_value is param_unspecified:
            config_value = getattr(config, key, param_unspecified)
        if config_value is param_unspecified:
            config_value = default
        return config_value


class Task(JobLike, RepresentById):
    """
    A task represents a single component of a job.
    """
    _numeric_metric = TaskMetricNumeric
    _text_metric = TaskMetricText

    states = Bunch(NEW='new',
                   WAITING='waiting',
                   QUEUED='queued',
                   RUNNING='running',
                   OK='ok',
                   ERROR='error',
                   DELETED='deleted')

    # Please include an accessor (get/set pair) for any new columns/members.
    def __init__(self, job, working_directory, prepare_files_cmd):
        self.command_line = None
        self.parameters = []
        self.state = Task.states.NEW
        self.info = None
        self.working_directory = working_directory
        self.task_runner_name = None
        self.task_runner_external_id = None
        self.job = job
        self.exit_code = None
        self.prepare_input_files_cmd = prepare_files_cmd
        self._init_metrics()

    def get_param_values(self, app):
        """
        Read encoded parameter values from the database and turn back into a
        dict of tool parameter values.
        """
        param_dict = dict([(p.name, p.value) for p in self.job.parameters])
        tool = app.toolbox.get_tool(self.job.tool_id, tool_version=self.job.tool_version)
        param_dict = tool.params_from_strings(param_dict, app)
        return param_dict

    def get_id_tag(self):
        """
        Return an id tag suitable for identifying the task.
        This combines the task's job id and the task's own id.
        """
        return "%s_%s" % (self.job.id, self.id)

    def get_command_line(self):
        return self.command_line

    def get_parameters(self):
        return self.parameters

    def get_state(self):
        return self.state

    def get_info(self):
        return self.info

    def get_working_directory(self):
        return self.working_directory

    def get_task_runner_name(self):
        return self.task_runner_name

    def get_task_runner_external_id(self):
        return self.task_runner_external_id

    def get_job(self):
        return self.job

    def get_prepare_input_files_cmd(self):
        return self.prepare_input_files_cmd

    # The following accessors are for members that are in the Job class but
    # not in the Task class. So they can either refer to the parent Job
    # or return None, depending on whether Tasks need to point to the parent
    # (e.g., for a session) or never use the member (e.g., external output
    # metdata). These can be filled in as needed.
    def get_external_output_metadata(self):
        """
        The external_output_metadata is currently a backref to
        JobExternalOutputMetadata. It exists for a job but not a task,
        and when a task is cancelled its corresponding parent Job will
        be cancelled. So None is returned now, but that could be changed
        to self.get_job().get_external_output_metadata().
        """
        return None

    def get_job_runner_name(self):
        """
        Since runners currently access Tasks the same way they access Jobs,
        this method just refers to *this* instance's runner.
        """
        return self.task_runner_name

    def get_job_runner_external_id(self):
        """
        Runners will use the same methods to get information about the Task
        class as they will about the Job class, so this method just returns
        the task's external id.
        """
        # TODO: Merge into get_runner_external_id.
        return self.task_runner_external_id

    def get_session_id(self):
        # The Job's galaxy session is equal to the Job's session, so the
        # Job's session is the same as the Task's session.
        return self.get_job().get_session_id()

    def set_id(self, id):
        # This is defined in the SQL Alchemy's mapper and not here.
        # This should never be called.
        self.id = id

    def set_command_line(self, command_line):
        self.command_line = command_line

    def set_parameters(self, parameters):
        self.parameters = parameters

    def set_state(self, state):
        self.state = state

    def set_info(self, info):
        self.info = info

    def set_working_directory(self, working_directory):
        self.working_directory = working_directory

    def set_task_runner_name(self, task_runner_name):
        self.task_runner_name = task_runner_name

    def set_job_runner_external_id(self, task_runner_external_id):
        # This method is available for runners that do not want/need to
        # differentiate between the kinds of Runnable things (Jobs and Tasks)
        # that they're using.
        log.debug("Task %d: Set external id to %s"
                  % (self.id, task_runner_external_id))
        self.task_runner_external_id = task_runner_external_id

    def set_task_runner_external_id(self, task_runner_external_id):
        self.task_runner_external_id = task_runner_external_id

    def set_job(self, job):
        self.job = job

    def set_prepare_input_files_cmd(self, prepare_input_files_cmd):
        self.prepare_input_files_cmd = prepare_input_files_cmd


class JobParameter(RepresentById):
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def copy(self):
        return JobParameter(name=self.name, value=self.value)


class JobToInputDatasetAssociation(RepresentById):
    def __init__(self, name, dataset):
        self.name = name
        self.dataset = dataset
        self.dataset_version = 0  # We start with version 0 and update once the job is ready


class JobToOutputDatasetAssociation(RepresentById):
    def __init__(self, name, dataset):
        self.name = name
        self.dataset = dataset


class JobToInputDatasetCollectionAssociation(RepresentById):
    def __init__(self, name, dataset_collection):
        self.name = name
        self.dataset_collection = dataset_collection


# Many jobs may map to one HistoryDatasetCollection using these for a given
# tool output (if mapping over an input collection).
class JobToOutputDatasetCollectionAssociation(RepresentById):
    def __init__(self, name, dataset_collection_instance):
        self.name = name
        self.dataset_collection_instance = dataset_collection_instance


# A DatasetCollection will be mapped to at most one job per tool output
# using these. (You can think of many of these models as going into the
# creation of a JobToOutputDatasetCollectionAssociation.)
class JobToImplicitOutputDatasetCollectionAssociation(RepresentById):
    def __init__(self, name, dataset_collection):
        self.name = name
        self.dataset_collection = dataset_collection


class JobToInputLibraryDatasetAssociation(RepresentById):
    def __init__(self, name, dataset):
        self.name = name
        self.dataset = dataset


class JobToOutputLibraryDatasetAssociation(RepresentById):
    def __init__(self, name, dataset):
        self.name = name
        self.dataset = dataset


class JobStateHistory(RepresentById):
    def __init__(self, job):
        self.job = job
        self.state = job.state
        self.info = job.info


class ImplicitlyCreatedDatasetCollectionInput(RepresentById):
    def __init__(self, name, input_dataset_collection):
        self.name = name
        self.input_dataset_collection = input_dataset_collection


class ImplicitCollectionJobs(RepresentById):

    populated_states = Bunch(
        NEW='new',  # New implicit jobs object, unpopulated job associations
        OK='ok',  # Job associations are set and fixed.
        FAILED='failed',  # There were issues populating job associations, object is in error.
    )

    def __init__(
        self,
        id=None,
        populated_state=None,
    ):
        self.id = id
        self.populated_state = populated_state or ImplicitCollectionJobs.populated_states.NEW

    @property
    def job_list(self):
        return [icjja.job for icjja in self.jobs]

    def serialize(self, id_encoder, serialization_options):
        rval = dict_for(
            self,
            populated_state=self.populated_state,
            jobs=[serialization_options.get_identifier(id_encoder, j_a.job) for j_a in self.jobs]
        )
        serialization_options.attach_identifier(id_encoder, self, rval)
        return rval


class ImplicitCollectionJobsJobAssociation(RepresentById):

    def __init__(self):
        pass


class PostJobAction(RepresentById):
    def __init__(self, action_type, workflow_step, output_name=None, action_arguments=None):
        self.action_type = action_type
        self.output_name = output_name
        self.action_arguments = action_arguments
        self.workflow_step = workflow_step


class PostJobActionAssociation(RepresentById):
    def __init__(self, pja, job=None, job_id=None):
        if job is not None:
            self.job = job
        elif job_id is not None:
            self.job_id = job_id
        else:
            raise Exception("PostJobActionAssociation must be created with a job or a job_id.")
        self.post_job_action = pja


class JobExternalOutputMetadata(RepresentById):
    def __init__(self, job=None, dataset=None):
        self.job = job
        if isinstance(dataset, galaxy.model.HistoryDatasetAssociation):
            self.history_dataset_association = dataset
        elif isinstance(dataset, galaxy.model.LibraryDatasetDatasetAssociation):
            self.library_dataset_dataset_association = dataset

    @property
    def dataset(self):
        if self.history_dataset_association:
            return self.history_dataset_association
        elif self.library_dataset_dataset_association:
            return self.library_dataset_dataset_association
        return None


class JobExportHistoryArchive(RepresentById):
    def __init__(self, job=None, history=None, dataset=None, compressed=False,
                 history_attrs_filename=None):
        self.job = job
        self.history = history
        self.dataset = dataset
        self.compressed = compressed
        self.history_attrs_filename = history_attrs_filename

    @property
    def temp_directory(self):
        return os.path.split(self.history_attrs_filename)[0]

    @property
    def up_to_date(self):
        """ Return False, if a new export should be generated for corresponding
        history.
        """
        job = self.job
        return job.state not in [Job.states.ERROR, Job.states.DELETED] \
            and job.update_time > self.history.update_time

    @property
    def ready(self):
        return self.job.state == Job.states.OK

    @property
    def preparing(self):
        return self.job.state in [Job.states.RUNNING, Job.states.QUEUED, Job.states.WAITING]

    @property
    def export_name(self):
        # Stream archive.
        hname = ready_name_for_url(self.history.name)
        hname = "Galaxy-History-%s.tar" % (hname)
        if self.compressed:
            hname += ".gz"
        return hname


class JobImportHistoryArchive(RepresentById):
    def __init__(self, job=None, history=None, archive_dir=None):
        self.job = job
        self.history = history
        self.archive_dir = archive_dir


class GenomeIndexToolData(RepresentById):
    def __init__(self, job=None, params=None, dataset=None, deferred_job=None,
                 transfer_job=None, fasta_path=None, created_time=None, modified_time=None,
                 dbkey=None, user=None, indexer=None):
        self.job = job
        self.dataset = dataset
        self.fasta_path = fasta_path
        self.user = user
        self.indexer = indexer
        self.created_time = created_time
        self.modified_time = modified_time
        self.deferred = deferred_job
        self.transfer = transfer_job


class DeferredJob(RepresentById):
    states = Bunch(NEW='new',
                   WAITING='waiting',
                   QUEUED='queued',
                   RUNNING='running',
                   OK='ok',
                   ERROR='error')

    def __init__(self, state=None, plugin=None, params=None):
        self.state = state
        self.plugin = plugin
        self.params = params

    def get_check_interval(self):
        if not hasattr(self, '_check_interval'):
            self._check_interval = None
        return self._check_interval

    def set_check_interval(self, seconds):
        self._check_interval = seconds
    check_interval = property(get_check_interval, set_check_interval)

    def get_last_check(self):
        if not hasattr(self, '_last_check'):
            self._last_check = 0
        return self._last_check

    def set_last_check(self, seconds):
        try:
            self._last_check = int(seconds)
        except ValueError:
            self._last_check = time.time()
    last_check = property(get_last_check, set_last_check)

    @property
    def is_check_time(self):
        if self.check_interval is None:
            return True
        elif (int(time.time()) - self.last_check) > self.check_interval:
            return True
        else:
            return False


class Group(Dictifiable, RepresentById):
    dict_collection_visible_keys = ['id', 'name']
    dict_element_visible_keys = ['id', 'name']

    def __init__(self, name=None):
        self.name = name
        self.deleted = False


class UserGroupAssociation(RepresentById):
    def __init__(self, user, group):
        self.user = user
        self.group = group


def is_hda(d):
    return isinstance(d, HistoryDatasetAssociation)


class History(HasTags, Dictifiable, UsesAnnotations, HasName, RepresentById):

    dict_collection_visible_keys = ['id', 'name', 'published', 'deleted']
    dict_element_visible_keys = ['id', 'name', 'genome_build', 'deleted', 'purged', 'update_time',
                                 'published', 'importable', 'slug', 'empty']
    default_name = 'Unnamed history'

    def __init__(self, id=None, name=None, user=None):
        self.id = id
        self.name = name or History.default_name
        self.deleted = False
        self.purged = False
        self.importing = False
        self.genome_build = None
        self.published = False
        # Relationships
        self.user = user
        self.datasets = []
        self.galaxy_sessions = []
        self.tags = []

    @property
    def empty(self):
        return self.hid_counter == 1

    def _next_hid(self, n=1):
        # this is overriden in mapping.py db_next_hid() method
        if len(self.datasets) == 0:
            return n
        else:
            last_hid = 0
            for dataset in self.datasets:
                if dataset.hid > last_hid:
                    last_hid = dataset.hid
            return last_hid + n

    def add_galaxy_session(self, galaxy_session, association=None):
        if association is None:
            self.galaxy_sessions.append(GalaxySessionToHistoryAssociation(galaxy_session, self))
        else:
            self.galaxy_sessions.append(association)

    def add_dataset(self, dataset, parent_id=None, genome_build=None, set_hid=True, quota=True):
        if isinstance(dataset, Dataset):
            dataset = HistoryDatasetAssociation(dataset=dataset)
            object_session(self).add(dataset)
            object_session(self).flush()
        elif not isinstance(dataset, HistoryDatasetAssociation):
            raise TypeError("You can only add Dataset and HistoryDatasetAssociation instances to a history" +
                            " ( you tried to add %s )." % str(dataset))
        if parent_id:
            for data in self.datasets:
                if data.id == parent_id:
                    dataset.hid = data.hid
                    break
            else:
                if set_hid:
                    dataset.hid = self._next_hid()
        else:
            if set_hid:
                dataset.hid = self._next_hid()
        if quota and self.user:
            self.user.adjust_total_disk_usage(dataset.quota_amount(self.user))
        dataset.history = self
        if genome_build not in [None, '?']:
            self.genome_build = genome_build
        dataset.history_id = self.id
        return dataset

    def add_datasets(self, sa_session, datasets, parent_id=None, genome_build=None, set_hid=True, quota=True, flush=False):
        """ Optimized version of add_dataset above that minimizes database
        interactions when adding many datasets to history at once.
        """
        all_hdas = all(is_hda(_) for _ in datasets)
        optimize = len(datasets) > 1 and parent_id is None and all_hdas and set_hid
        if optimize:
            self.__add_datasets_optimized(datasets, genome_build=genome_build)
            if quota and self.user:
                disk_usage = sum([d.get_total_size() for d in datasets])
                self.user.adjust_total_disk_usage(disk_usage)
            sa_session.add_all(datasets)
            if flush:
                sa_session.flush()
        else:
            for dataset in datasets:
                self.add_dataset(dataset, parent_id=parent_id, genome_build=genome_build, set_hid=set_hid, quota=quota)
                sa_session.add(dataset)
                if flush:
                    sa_session.flush()

    def __add_datasets_optimized(self, datasets, genome_build=None):
        """ Optimized version of add_dataset above that minimizes database
        interactions when adding many datasets to history at once under
        certain circumstances.
        """
        n = len(datasets)

        base_hid = self._next_hid(n=n)
        set_genome = genome_build not in [None, '?']
        for i, dataset in enumerate(datasets):
            dataset.hid = base_hid + i
            # Don't let SA manage this.
            delattr(dataset, "history")
            dataset.history_id = cached_id(self)
            if set_genome:
                self.genome_build = genome_build
        for dataset in datasets:
            dataset.history_id = cached_id(self)
        return datasets

    def add_dataset_collection(self, history_dataset_collection, set_hid=True):
        if set_hid:
            history_dataset_collection.hid = self._next_hid()
        history_dataset_collection.history = self
        # TODO: quota?
        self.dataset_collections.append(history_dataset_collection)
        return history_dataset_collection

    def copy(self, name=None, target_user=None, activatable=False, all_datasets=False):
        """
        Return a copy of this history using the given `name` and `target_user`.
        If `activatable`, copy only non-deleted datasets. If `all_datasets`, copy
        non-deleted, deleted, and purged datasets.
        """
        name = name or self.name
        applies_to_quota = target_user != self.user

        # Create new history.
        new_history = History(name=name, user=target_user)
        db_session = object_session(self)
        db_session.add(new_history)
        db_session.flush([new_history])

        # copy history tags and annotations (if copying user is not anonymous)
        if target_user:
            self.copy_item_annotation(db_session, self.user, self, target_user, new_history)
            new_history.copy_tags_from(target_user=target_user, source=self)

        # Copy HDAs.
        if activatable:
            hdas = self.activatable_datasets
        elif all_datasets:
            hdas = self.datasets
        else:
            hdas = self.active_datasets
        for hda in hdas:
            # Copy HDA.
            new_hda = hda.copy(force_flush=False)
            new_history.add_dataset(new_hda, set_hid=False, quota=applies_to_quota)

            if target_user:
                new_hda.copy_item_annotation(db_session, self.user, hda, target_user, new_hda)
                new_hda.copy_tags_from(target_user, hda)

        # Copy history dataset collections
        if all_datasets:
            hdcas = self.dataset_collections
        else:
            hdcas = self.active_dataset_collections
        for hdca in hdcas:
            new_hdca = hdca.copy()
            new_history.add_dataset_collection(new_hdca, set_hid=False)
            db_session.add(new_hdca)
            db_session.flush()

            if target_user:
                new_hdca.copy_item_annotation(db_session, self.user, hdca, target_user, new_hdca)
                new_hdca.copy_tags_from(target_user, hdca)

        new_history.hid_counter = self.hid_counter
        db_session.flush()

        return new_history

    @property
    def has_possible_members(self):
        return True

    @property
    def activatable_datasets(self):
        # This needs to be a list
        return [hda for hda in self.datasets if not hda.dataset.deleted]

    def serialize(self, id_encoder, serialization_options):

        history_attrs = dict_for(
            self,
            create_time=self.create_time.__str__(),
            update_time=self.update_time.__str__(),
            name=unicodify(self.name),
            hid_counter=self.hid_counter,
            genome_build=self.genome_build,
            annotation=unicodify(get_item_annotation_str(object_session(self), self.user, self)),
            tags=self.make_tag_string_list(),
        )
        serialization_options.attach_identifier(id_encoder, self, history_attrs)
        return history_attrs

    def to_dict(self, view='collection', value_mapper=None):

        # Get basic value.
        rval = super(History, self).to_dict(view=view, value_mapper=value_mapper)

        if view == 'element':
            rval['size'] = int(self.disk_size)

        return rval

    @property
    def latest_export(self):
        exports = self.exports
        return exports and exports[0]

    def unhide_datasets(self):
        for dataset in self.datasets:
            dataset.mark_unhidden()

    def resume_paused_jobs(self):
        job = None
        for job in self.paused_jobs:
            job.resume(flush=False)
        if job is not None:
            # We'll flush once if there was a paused job
            object_session(job).flush()

    @property
    def paused_jobs(self):
        db_session = object_session(self)
        return db_session.query(Job).filter(Job.history_id == self.id,
                                            Job.state == Job.states.PAUSED).all()

    @hybrid.hybrid_property
    def disk_size(self):
        """
        Return the size in bytes of this history by summing the 'total_size's of
        all non-purged, unique datasets within it.
        """
        # non-.expression part of hybrid.hybrid_property: called when an instance is the namespace (not the class)
        db_session = object_session(self)
        rval = db_session.query(
            func.sum(db_session.query(HistoryDatasetAssociation.dataset_id, Dataset.total_size).join(Dataset)
                    .filter(HistoryDatasetAssociation.table.c.history_id == self.id)
                    .filter(HistoryDatasetAssociation.purged != true())
                    .filter(Dataset.purged != true())
                    # unique datasets only
                    .distinct().subquery().c.total_size)).first()[0]
        if rval is None:
            rval = 0
        return rval

    @disk_size.expression
    def disk_size(cls):
        """
        Return a query scalar that will get any history's size in bytes by summing
        the 'total_size's of all non-purged, unique datasets within it.
        """
        # .expression acts as a column_property and should return a scalar
        # first, get the distinct datasets within a history that are not purged
        hda_to_dataset_join = join(HistoryDatasetAssociation, Dataset,
            HistoryDatasetAssociation.table.c.dataset_id == Dataset.table.c.id)
        distinct_datasets = (
            select([
                # use labels here to better access from the query above
                HistoryDatasetAssociation.table.c.history_id.label('history_id'),
                Dataset.total_size.label('dataset_size'),
                Dataset.id.label('dataset_id')
            ])
            .where(HistoryDatasetAssociation.table.c.purged != true())
            .where(Dataset.table.c.purged != true())
            .select_from(hda_to_dataset_join)
            # TODO: slow (in general) but most probably here - index total_size for easier sorting/distinct?
            .distinct()
        )
        # postgres needs an alias on FROM
        distinct_datasets_alias = aliased(distinct_datasets, name="datasets")
        # then, bind as property of history using the cls.id
        size_query = (
            select([
                func.coalesce(func.sum(distinct_datasets_alias.c.dataset_size), 0)
            ])
            .select_from(distinct_datasets_alias)
            .where(distinct_datasets_alias.c.history_id == cls.id)
        )
        # label creates a scalar
        return size_query.label('disk_size')

    @property
    def disk_nice_size(self):
        """Returns human readable size of history on disk."""
        return galaxy.util.nice_size(self.disk_size)

    @property
    def active_datasets_and_roles(self):
        if not hasattr(self, '_active_datasets_and_roles'):
            db_session = object_session(self)
            query = (db_session.query(HistoryDatasetAssociation)
                .filter(HistoryDatasetAssociation.table.c.history_id == self.id)
                .filter(not_(HistoryDatasetAssociation.deleted))
                .order_by(HistoryDatasetAssociation.table.c.hid.asc())
                .options(joinedload("dataset"),
                         joinedload("dataset.actions"),
                         joinedload("dataset.actions.role"),
                         joinedload("tags")))
            self._active_datasets_and_roles = query.all()
        return self._active_datasets_and_roles

    @property
    def active_visible_datasets_and_roles(self):
        if not hasattr(self, '_active_visible_datasets_and_roles'):
            db_session = object_session(self)
            query = (db_session.query(HistoryDatasetAssociation)
                .filter(HistoryDatasetAssociation.table.c.history_id == self.id)
                .filter(not_(HistoryDatasetAssociation.deleted))
                .filter(HistoryDatasetAssociation.visible)
                .order_by(HistoryDatasetAssociation.table.c.hid.asc())
                .options(joinedload("dataset"),
                         joinedload("dataset.actions"),
                         joinedload("dataset.actions.role"),
                         joinedload("tags")))
            self._active_visible_datasets_and_roles = query.all()
        return self._active_visible_datasets_and_roles

    @property
    def active_visible_dataset_collections(self):
        if not hasattr(self, '_active_visible_dataset_collections'):
            db_session = object_session(self)
            query = (db_session.query(HistoryDatasetCollectionAssociation)
                .filter(HistoryDatasetCollectionAssociation.table.c.history_id == self.id)
                .filter(not_(HistoryDatasetCollectionAssociation.deleted))
                .filter(HistoryDatasetCollectionAssociation.visible)
                .order_by(HistoryDatasetCollectionAssociation.table.c.hid.asc())
                .options(joinedload("collection"),
                         joinedload("tags")))
            self._active_visible_dataset_collections = query.all()
        return self._active_visible_dataset_collections

    @property
    def active_contents(self):
        """ Return all active contents ordered by hid.
        """
        return self.contents_iter(types=["dataset", "dataset_collection"], deleted=False, visible=True)

    def contents_iter(self, **kwds):
        """
        Fetch filtered list of contents of history.
        """
        default_contents_types = [
            'dataset',
        ]
        types = kwds.get('types', default_contents_types)
        iters = []
        if 'dataset' in types:
            iters.append(self.__dataset_contents_iter(**kwds))
        if 'dataset_collection' in types:
            iters.append(self.__collection_contents_iter(**kwds))
        return galaxy.util.merge_sorted_iterables(operator.attrgetter("hid"), *iters)

    def __dataset_contents_iter(self, **kwds):
        return self.__filter_contents(HistoryDatasetAssociation, **kwds)

    def __filter_contents(self, content_class, **kwds):
        db_session = object_session(self)
        assert db_session is not None
        query = db_session.query(content_class).filter(content_class.table.c.history_id == self.id)
        query = query.order_by(content_class.table.c.hid.asc())
        deleted = galaxy.util.string_as_bool_or_none(kwds.get('deleted', None))
        if deleted is not None:
            query = query.filter(content_class.deleted == deleted)
        visible = galaxy.util.string_as_bool_or_none(kwds.get('visible', None))
        if visible is not None:
            query = query.filter(content_class.visible == visible)
        if 'ids' in kwds:
            ids = kwds['ids']
            max_in_filter_length = kwds.get('max_in_filter_length', MAX_IN_FILTER_LENGTH)
            if len(ids) < max_in_filter_length:
                query = query.filter(content_class.id.in_(ids))
            else:
                query = (content for content in query if content.id in ids)
        return query

    def __collection_contents_iter(self, **kwds):
        return self.__filter_contents(HistoryDatasetCollectionAssociation, **kwds)


class HistoryUserShareAssociation(RepresentById):
    def __init__(self):
        self.history = None
        self.user = None


class UserRoleAssociation(RepresentById):
    def __init__(self, user, role):
        self.user = user
        self.role = role


class GroupRoleAssociation(RepresentById):
    def __init__(self, group, role):
        self.group = group
        self.role = role


class Role(Dictifiable, RepresentById):
    dict_collection_visible_keys = ['id', 'name']
    dict_element_visible_keys = ['id', 'name', 'description', 'type']
    private_id = None
    types = Bunch(
        PRIVATE='private',
        SYSTEM='system',
        USER='user',
        ADMIN='admin',
        SHARING='sharing'
    )

    def __init__(self, name="", description="", type="system", deleted=False):
        self.name = name
        self.description = description
        self.type = type
        self.deleted = deleted


class UserQuotaAssociation(Dictifiable, RepresentById):
    dict_element_visible_keys = ['user']

    def __init__(self, user, quota):
        self.user = user
        self.quota = quota


class GroupQuotaAssociation(Dictifiable, RepresentById):
    dict_element_visible_keys = ['group']

    def __init__(self, group, quota):
        self.group = group
        self.quota = quota


class Quota(Dictifiable, RepresentById):
    dict_collection_visible_keys = ['id', 'name']
    dict_element_visible_keys = ['id', 'name', 'description', 'bytes', 'operation', 'display_amount', 'default', 'users', 'groups']
    valid_operations = ('+', '-', '=')

    def __init__(self, name="", description="", amount=0, operation="="):
        self.name = name
        self.description = description
        if amount is None:
            self.bytes = -1
        else:
            self.bytes = amount
        self.operation = operation

    def get_amount(self):
        if self.bytes == -1:
            return None
        return self.bytes

    def set_amount(self, amount):
        if amount is None:
            self.bytes = -1
        else:
            self.bytes = amount
    amount = property(get_amount, set_amount)

    @property
    def display_amount(self):
        if self.bytes == -1:
            return "unlimited"
        else:
            return galaxy.util.nice_size(self.bytes)


class DefaultQuotaAssociation(Quota, Dictifiable, RepresentById):
    dict_element_visible_keys = ['type']
    types = Bunch(
        UNREGISTERED='unregistered',
        REGISTERED='registered'
    )

    def __init__(self, type, quota):
        assert type in self.types.__dict__.values(), 'Invalid type'
        self.type = type
        self.quota = quota


class DatasetPermissions(RepresentById):
    def __init__(self, action, dataset, role=None, role_id=None):
        self.action = action
        self.dataset = dataset
        if role is not None:
            self.role = role
        else:
            self.role_id = role_id


class LibraryPermissions(RepresentById):
    def __init__(self, action, library_item, role):
        self.action = action
        if isinstance(library_item, Library):
            self.library = library_item
        else:
            raise Exception("Invalid Library specified: %s" % library_item.__class__.__name__)
        self.role = role


class LibraryFolderPermissions(RepresentById):
    def __init__(self, action, library_item, role):
        self.action = action
        if isinstance(library_item, LibraryFolder):
            self.folder = library_item
        else:
            raise Exception("Invalid LibraryFolder specified: %s" % library_item.__class__.__name__)
        self.role = role


class LibraryDatasetPermissions(RepresentById):
    def __init__(self, action, library_item, role):
        self.action = action
        if isinstance(library_item, LibraryDataset):
            self.library_dataset = library_item
        else:
            raise Exception("Invalid LibraryDataset specified: %s" % library_item.__class__.__name__)
        self.role = role


class LibraryDatasetDatasetAssociationPermissions(RepresentById):
    def __init__(self, action, library_item, role):
        self.action = action
        if isinstance(library_item, LibraryDatasetDatasetAssociation):
            self.library_dataset_dataset_association = library_item
        else:
            raise Exception("Invalid LibraryDatasetDatasetAssociation specified: %s" % library_item.__class__.__name__)
        self.role = role


class DefaultUserPermissions(RepresentById):
    def __init__(self, user, action, role):
        self.user = user
        self.action = action
        self.role = role


class DefaultHistoryPermissions(RepresentById):
    def __init__(self, history, action, role):
        self.history = history
        self.action = action
        self.role = role


class StorableObject(object):

    def __init__(self, id, uuid):
        self.id = id
        if uuid is None:
            self.uuid = uuid4()
        else:
            self.uuid = UUID(str(uuid))


class Dataset(StorableObject, RepresentById):
    states = Bunch(NEW='new',
                   UPLOAD='upload',
                   QUEUED='queued',
                   RUNNING='running',
                   OK='ok',
                   EMPTY='empty',
                   ERROR='error',
                   DISCARDED='discarded',
                   PAUSED='paused',
                   SETTING_METADATA='setting_metadata',
                   FAILED_METADATA='failed_metadata')
    # failed_metadata is only valid as DatasetInstance state currently

    non_ready_states = (
        states.NEW,
        states.UPLOAD,
        states.QUEUED,
        states.RUNNING,
        states.SETTING_METADATA
    )
    ready_states = tuple(set(states.__dict__.values()) - set(non_ready_states))
    valid_input_states = tuple(
        set(states.__dict__.values()) - set([states.ERROR, states.DISCARDED])
    )
    terminal_states = (
        states.OK,
        states.EMPTY,
        states.ERROR,
        states.DISCARDED,
        states.FAILED_METADATA,
    )

    conversion_messages = Bunch(PENDING="pending",
                                NO_DATA="no data",
                                NO_CHROMOSOME="no chromosome",
                                NO_CONVERTER="no converter",
                                NO_TOOL="no tool",
                                DATA="data",
                                ERROR="error",
                                OK="ok")

    permitted_actions = get_permitted_actions(filter='DATASET')
    file_path = "/tmp/"
    object_store = None  # This get initialized in mapping.py (method init) by app.py
    engine = None

    def __init__(self, id=None, state=None, external_filename=None, extra_files_path=None, file_size=None, purgable=True, uuid=None):
        super(Dataset, self).__init__(id=id, uuid=uuid)
        self.state = state
        self.deleted = False
        self.purged = False
        self.purgable = purgable
        self.external_filename = external_filename
        self.external_extra_files_path = None
        self._extra_files_path = extra_files_path
        self.file_size = file_size
        self.sources = []
        self.hashes = []

    def in_ready_state(self):
        return self.state in self.ready_states

    def get_file_name(self):
        if not self.external_filename:
            assert self.object_store is not None, "Object Store has not been initialized for dataset %s" % self.id
            filename = self.object_store.get_filename(self)
            return filename
        else:
            filename = self.external_filename
        # Make filename absolute
        return os.path.abspath(filename)

    def set_file_name(self, filename):
        if not filename:
            self.external_filename = None
        else:
            self.external_filename = filename
    file_name = property(get_file_name, set_file_name)

    def get_extra_files_path(self):
        # Unlike get_file_name - external_extra_files_path is not backed by an
        # actual database column so if SA instantiates this object - the
        # attribute won't exist yet.
        if not getattr(self, "external_extra_files_path", None):
            return self.object_store.get_filename(self, dir_only=True, extra_dir=self._extra_files_rel_path)
        else:
            return os.path.abspath(self.external_extra_files_path)

    def set_extra_files_path(self, extra_files_path):
        if not extra_files_path:
            self.external_extra_files_path = None
        else:
            self.external_extra_files_path = extra_files_path
    extra_files_path = property(get_extra_files_path, set_extra_files_path)

    def extra_files_path_exists(self):
        return self.object_store.exists(self, extra_dir=self._extra_files_rel_path, dir_only=True)

    @property
    def _extra_files_rel_path(self):
        store_by = getattr(self.object_store, "store_by", "id")
        return self._extra_files_path or "dataset_%s_files" % getattr(self, store_by)

    def _calculate_size(self):
        if self.external_filename:
            try:
                return os.path.getsize(self.external_filename)
            except OSError:
                return 0
        else:
            return self.object_store.size(self)

    def get_size(self, nice_size=False):
        """Returns the size of the data on disk"""
        if self.file_size:
            if nice_size:
                return galaxy.util.nice_size(self.file_size)
            else:
                return self.file_size
        else:
            if nice_size:
                return galaxy.util.nice_size(self._calculate_size())
            else:
                return self._calculate_size()

    def set_size(self, no_extra_files=False):
        """Sets the size of the data on disk.

        If the caller is sure there are no extra files, pass no_extra_files as True to optimize subsequent
        calls to get_total_size or set_total_size - potentially avoiding both a database flush and check against
        the file system.
        """
        if not self.file_size:
            self.file_size = self._calculate_size()
            if no_extra_files:
                self.total_size = self.file_size

    def get_total_size(self):
        if self.total_size is not None:
            return self.total_size
        # for backwards compatibility, set if unset
        self.set_total_size()
        db_session = object_session(self)
        db_session.flush()
        return self.total_size

    def set_total_size(self):
        if self.file_size is None:
            self.set_size()
        self.total_size = self.file_size or 0
        if self.object_store.exists(self, extra_dir=self._extra_files_rel_path, dir_only=True):
            for root, dirs, files in os.walk(self.extra_files_path):
                self.total_size += sum([os.path.getsize(os.path.join(root, file)) for file in files if os.path.exists(os.path.join(root, file))])

    def has_data(self):
        """Detects whether there is any data"""
        return self.get_size() > 0

    def mark_deleted(self):
        self.deleted = True

    # FIXME: sqlalchemy will replace this
    def _delete(self):
        """Remove the file that corresponds to this data"""
        self.object_store.delete(self)

    @property
    def user_can_purge(self):
        return self.purged is False \
            and not bool(self.library_associations) \
            and len(self.history_associations) == len(self.purged_history_associations)

    def full_delete(self):
        """Remove the file and extra files, marks deleted and purged"""
        # os.unlink( self.file_name )
        self.object_store.delete(self)
        if self.object_store.exists(self, extra_dir=self._extra_files_rel_path, dir_only=True):
            self.object_store.delete(self, entire_dir=True, extra_dir=self._extra_files_rel_path, dir_only=True)
        # if os.path.exists( self.extra_files_path ):
        #     shutil.rmtree( self.extra_files_path )
        # TODO: purge metadata files
        self.deleted = True
        self.purged = True

    def get_access_roles(self, trans):
        roles = []
        for dp in self.actions:
            if dp.action == trans.app.security_agent.permitted_actions.DATASET_ACCESS.action:
                roles.append(dp.role)
        return roles

    def get_manage_permissions_roles(self, trans):
        roles = []
        for dp in self.actions:
            if dp.action == trans.app.security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS.action:
                roles.append(dp.role)
        return roles

    def has_manage_permissions_roles(self, trans):
        for dp in self.actions:
            if dp.action == trans.app.security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS.action:
                return True
        return False

    def serialize(self, id_encoder, serialization_options):
        # serialize Dataset objects only for jobs that can actually modify these models.
        assert serialization_options.serialize_dataset_objects
        rval = dict_for(
            self,
            state=self.state,
            deleted=self.deleted,
            purged=self.purged,
            external_filename=self.external_filename,
            _extra_files_path=self._extra_files_path,
            file_size=self.file_size,
            object_store_id=self.object_store_id,
            total_size=self.total_size,
            uuid=str(self.uuid or '') or None,
            hashes=list(map(lambda h: h.serialize(id_encoder, serialization_options), self.hashes))
        )
        serialization_options.attach_identifier(id_encoder, self, rval)
        return rval


class DatasetSource(RepresentById):
    """ """


class DatasetSourceHash(RepresentById):
    """ """


class DatasetHash(RepresentById):
    """ """
    def serialize(self, id_encoder, serialization_options):
        # serialize Dataset objects only for jobs that can actually modify these models.
        rval = dict_for(
            self,
            hash_function=self.hash_function,
            hash_value=self.hash_value,
            extra_files_path=self.extra_files_path,
        )
        serialization_options.attach_identifier(id_encoder, self, rval)
        return rval


def datatype_for_extension(extension, datatypes_registry=None):
    if datatypes_registry is None:
        datatypes_registry = _get_datatypes_registry()
    if not extension or extension == 'auto' or extension == '_sniff_':
        extension = 'data'
    ret = datatypes_registry.get_datatype_by_extension(extension)
    if ret is None:
        log.warning("Datatype class not found for extension '%s'" % extension)
        return datatypes_registry.get_datatype_by_extension('data')
    return ret


class DatasetInstance(object):
    """A base class for all 'dataset instances', HDAs, LDAs, etc"""
    states = Dataset.states
    conversion_messages = Dataset.conversion_messages
    permitted_actions = Dataset.permitted_actions

    def __init__(self, id=None, hid=None, name=None, info=None, blurb=None, peek=None, tool_version=None, extension=None,
                 dbkey=None, metadata=None, history=None, dataset=None, deleted=False, designation=None,
                 parent_id=None, validation_errors=None, visible=True, create_dataset=False, sa_session=None,
                 extended_metadata=None, flush=True):
        self.name = name or "Unnamed dataset"
        self.id = id
        self.info = info
        self.blurb = blurb
        self.peek = peek
        self.tool_version = tool_version
        self.extension = extension
        self.designation = designation
        # set private variable to None here, since the attribute may be needed in by MetadataCollection.__init__
        self._metadata = None
        self.metadata = metadata or dict()
        self.extended_metadata = extended_metadata
        if dbkey:  # dbkey is stored in metadata, only set if non-zero, or else we could clobber one supplied by input 'metadata'
            self._metadata['dbkey'] = dbkey
        self.deleted = deleted
        self.visible = visible
        # Relationships
        if not dataset and create_dataset:
            # Had to pass the sqlalchemy session in order to create a new dataset
            dataset = Dataset(state=Dataset.states.NEW)
            if flush:
                sa_session.add(dataset)
                sa_session.flush()
        self.dataset = dataset
        self.parent_id = parent_id
        self.validation_errors = validation_errors

    def update(self):
        self.update_time = galaxy.model.orm.now.now()

    @property
    def ext(self):
        return self.extension

    def get_dataset_state(self):
        # self._state is currently only used when setting metadata externally
        # leave setting the state as-is, we'll currently handle this specially in the external metadata code
        if self._state:
            return self._state
        return self.dataset.state

    def raw_set_dataset_state(self, state):
        if state != self.dataset.state:
            self.dataset.state = state
            return True
        else:
            return False

    def set_dataset_state(self, state):
        if self.raw_set_dataset_state(state):
            object_session(self).add(self.dataset)
            object_session(self).flush()  # flush here, because hda.flush() won't flush the Dataset object
    state = property(get_dataset_state, set_dataset_state)

    def get_file_name(self):
        if self.dataset.purged:
            return ""
        return self.dataset.get_file_name()

    def set_file_name(self, filename):
        return self.dataset.set_file_name(filename)
    file_name = property(get_file_name, set_file_name)

    def link_to(self, path):
        self.file_name = os.path.abspath(path)
        # Since we are not copying the file into Galaxy's managed
        # default file location, the dataset should never be purgable.
        self.dataset.purgable = False

    @property
    def extra_files_path(self):
        return self.dataset.extra_files_path

    def extra_files_path_exists(self):
        return self.dataset.extra_files_path_exists()

    @property
    def datatype(self):
        return datatype_for_extension(self.extension)

    def get_metadata(self):
        # using weakref to store parent (to prevent circ ref),
        #   does a Session.clear() cause parent to be invalidated, while still copying over this non-database attribute?
        if not hasattr(self, '_metadata_collection') or self._metadata_collection.parent != self:
            self._metadata_collection = galaxy.model.metadata.MetadataCollection(self)
        return self._metadata_collection

    @property
    def set_metadata_requires_flush(self):
        return self.metadata.requires_dataset_id

    def set_metadata(self, bunch):
        # Needs to accept a MetadataCollection, a bunch, or a dict
        self._metadata = self.metadata.make_dict_copy(bunch)
    metadata = property(get_metadata, set_metadata)

    @property
    def metadata_file_types(self):
        meta_types = []
        for meta_type in self.metadata.spec.keys():
            if isinstance(self.metadata.spec[meta_type].param, galaxy.model.metadata.FileParameter):
                meta_types.append(meta_type)
        return meta_types

    # This provide backwards compatibility with using the old dbkey
    # field in the database.  That field now maps to "old_dbkey" (see mapping.py).

    def get_dbkey(self):
        dbkey = self.metadata.dbkey
        if not isinstance(dbkey, list):
            dbkey = [dbkey]
        if dbkey in [[None], []]:
            return "?"
        return dbkey[0]

    def set_dbkey(self, value):
        if "dbkey" in self.datatype.metadata_spec:
            if not isinstance(value, list):
                self.metadata.dbkey = [value]
    dbkey = property(get_dbkey, set_dbkey)

    def change_datatype(self, new_ext):
        self.clear_associated_files()
        _get_datatypes_registry().change_datatype(self, new_ext)

    def get_size(self, nice_size=False):
        """Returns the size of the data on disk"""
        if nice_size:
            return galaxy.util.nice_size(self.dataset.get_size())
        return self.dataset.get_size()

    def set_size(self, **kwds):
        """Sets and gets the size of the data on disk"""
        return self.dataset.set_size(**kwds)

    def get_total_size(self):
        return self.dataset.get_total_size()

    def set_total_size(self):
        return self.dataset.set_total_size()

    def has_data(self):
        """Detects whether there is any data"""
        return self.dataset.has_data()

    def get_raw_data(self):
        """Returns the full data. To stream it open the file_name and read/write as needed"""
        return self.datatype.get_raw_data(self)

    def get_mime(self):
        """Returns the mime type of the data"""
        try:
            return _get_datatypes_registry().get_mimetype_by_extension(self.extension.lower())
        except AttributeError:
            # extension is None
            return 'data'

    def set_peek(self):
        return self.datatype.set_peek(self)

    def init_meta(self, copy_from=None):
        return self.datatype.init_meta(self, copy_from=copy_from)

    def set_meta(self, **kwd):
        self.clear_associated_files(metadata_safe=True)
        return self.datatype.set_meta(self, **kwd)

    def missing_meta(self, **kwd):
        return self.datatype.missing_meta(self, **kwd)

    def as_display_type(self, type, **kwd):
        return self.datatype.as_display_type(self, type, **kwd)

    def display_peek(self):
        return self.datatype.display_peek(self)

    def display_name(self):
        return self.datatype.display_name(self)

    def display_info(self):
        return self.datatype.display_info(self)

    def get_converted_files_by_type(self, file_type):
        for assoc in self.implicitly_converted_datasets:
            if not assoc.deleted and assoc.type == file_type:
                if assoc.dataset:
                    return assoc.dataset
                return assoc.dataset_ldda
        return None

    def get_converted_dataset_deps(self, trans, target_ext):
        """
        Returns dict of { "dependency" => HDA }
        """
        # List of string of dependencies
        try:
            depends_list = trans.app.datatypes_registry.converter_deps[self.extension][target_ext]
        except KeyError:
            depends_list = []
        return dict([(dep, self.get_converted_dataset(trans, dep)) for dep in depends_list])

    def get_converted_dataset(self, trans, target_ext, target_context=None, history=None):
        """
        Return converted dataset(s) if they exist, along with a dict of dependencies.
        If not converted yet, do so and return None (the first time). If unconvertible, raise exception.
        """
        # See if we can convert the dataset
        if target_ext not in self.get_converter_types():
            raise NoConverterException("Conversion from '%s' to '%s' not possible" % (self.extension, target_ext))
        # See if converted dataset already exists, either in metadata in conversions.
        converted_dataset = self.get_metadata_dataset(target_ext)
        if converted_dataset:
            return converted_dataset
        converted_dataset = self.get_converted_files_by_type(target_ext)
        if converted_dataset:
            return converted_dataset
        deps = {}
        # List of string of dependencies
        try:
            depends_list = trans.app.datatypes_registry.converter_deps[self.extension][target_ext]
        except KeyError:
            depends_list = []
        # Conversion is possible but hasn't been done yet, run converter.
        # Check if we have dependencies
        try:
            for dependency in depends_list:
                dep_dataset = self.get_converted_dataset(trans, dependency)
                if dep_dataset is None:
                    # None means converter is running first time
                    return None
                elif dep_dataset.state == Job.states.ERROR:
                    raise ConverterDependencyException("A dependency (%s) was in an error state." % dependency)
                elif dep_dataset.state != Job.states.OK:
                    # Pending
                    return None
                deps[dependency] = dep_dataset
        except NoConverterException:
            raise NoConverterException("A dependency (%s) is missing a converter." % dependency)
        except KeyError:
            pass  # No deps
        new_dataset = next(iter(self.datatype.convert_dataset(trans, self, target_ext, return_output=True, visible=False, deps=deps, target_context=target_context, history=history).values()))
        new_dataset.name = self.name
        self.copy_attributes(new_dataset)
        assoc = ImplicitlyConvertedDatasetAssociation(parent=self, file_type=target_ext, dataset=new_dataset, metadata_safe=False)
        session = trans.sa_session
        session.add(new_dataset)
        session.add(assoc)
        session.flush()
        return new_dataset

    def copy_attributes(self, new_dataset):
        """
        Copies attributes to a new datasets, used for implicit conversions
        """
        pass

    def get_metadata_dataset(self, dataset_ext):
        """
        Returns an HDA that points to a metadata file which contains a
        converted data with the requested extension.
        """
        for name, value in self.metadata.items():
            # HACK: MetadataFile objects do not have a type/ext, so need to use metadata name
            # to determine type.
            if dataset_ext == 'bai' and name == 'bam_index' and isinstance(value, MetadataFile):
                # HACK: MetadataFile objects cannot be used by tools, so return
                # a fake HDA that points to metadata file.
                fake_dataset = Dataset(state=Dataset.states.OK, external_filename=value.file_name)
                fake_hda = HistoryDatasetAssociation(dataset=fake_dataset)
                return fake_hda

    def clear_associated_files(self, metadata_safe=False, purge=False):
        raise Exception("Unimplemented")

    def get_converter_types(self):
        return self.datatype.get_converter_types(self, _get_datatypes_registry())

    def can_convert_to(self, format):
        return format in self.get_converter_types()

    def find_conversion_destination(self, accepted_formats, **kwd):
        """Returns ( target_ext, existing converted dataset )"""
        return self.datatype.find_conversion_destination(self, accepted_formats, _get_datatypes_registry(), **kwd)

    def add_validation_error(self, validation_error):
        self.validation_errors.append(validation_error)

    def extend_validation_errors(self, validation_errors):
        self.validation_errors.extend(validation_errors)

    def mark_deleted(self):
        self.deleted = True

    def mark_undeleted(self):
        self.deleted = False

    def mark_unhidden(self):
        self.visible = True

    def undeletable(self):
        if self.purged:
            return False
        return True

    @property
    def is_ok(self):
        return self.state == self.states.OK

    @property
    def is_pending(self):
        """
        Return true if the dataset is neither ready nor in error
        """
        return self.state in (self.states.NEW, self.states.UPLOAD,
                              self.states.QUEUED, self.states.RUNNING,
                              self.states.SETTING_METADATA)

    @property
    def source_library_dataset(self):
        def get_source(dataset):
            if isinstance(dataset, LibraryDatasetDatasetAssociation):
                if dataset.library_dataset:
                    return (dataset, dataset.library_dataset)
            if dataset.copied_from_library_dataset_dataset_association:
                source = get_source(dataset.copied_from_library_dataset_dataset_association)
                if source:
                    return source
            if dataset.copied_from_history_dataset_association:
                source = get_source(dataset.copied_from_history_dataset_association)
                if source:
                    return source
            return (None, None)
        return get_source(self)

    @property
    def source_dataset_chain(self):
        def _source_dataset_chain(dataset, lst):
            try:
                cp_from_ldda = dataset.copied_from_library_dataset_dataset_association
                if cp_from_ldda:
                    lst.append((cp_from_ldda, "(Data Library)"))
                    return _source_dataset_chain(cp_from_ldda, lst)
            except Exception as e:
                log.warning(e)
            try:
                cp_from_hda = dataset.copied_from_history_dataset_association
                if cp_from_hda:
                    lst.append((cp_from_hda, cp_from_hda.history.name))
                    return _source_dataset_chain(cp_from_hda, lst)
            except Exception as e:
                log.warning(e)
            return lst
        return _source_dataset_chain(self, [])

    @property
    def creating_job(self):
        creating_job_associations = None
        if self.creating_job_associations:
            creating_job_associations = self.creating_job_associations
        else:
            inherit_chain = self.source_dataset_chain
            if inherit_chain:
                creating_job_associations = inherit_chain[-1][0].creating_job_associations
        if creating_job_associations:
            return creating_job_associations[0].job
        return None

    def get_display_applications(self, trans):
        return self.datatype.get_display_applications_by_dataset(self, trans)

    def get_visualizations(self):
        return self.datatype.get_visualizations(self)

    def get_datasources(self, trans):
        """
        Returns datasources for dataset; if datasources are not available
        due to indexing, indexing is started. Return value is a dictionary
        with entries of type
        (<datasource_type> : {<datasource_name>, <indexing_message>}).
        """
        data_sources_dict = {}
        msg = None
        for source_type, source_list in self.datatype.data_sources.items():
            data_source = None
            if source_type == "data_standalone":
                # Nothing to do.
                msg = None
                data_source = source_list
            else:
                # Convert.
                if isinstance(source_list, string_types):
                    source_list = [source_list]

                # Loop through sources until viable one is found.
                for source in source_list:
                    msg = self.convert_dataset(trans, source)
                    # No message or PENDING means that source is viable. No
                    # message indicates conversion was done and is successful.
                    if not msg or msg == self.conversion_messages.PENDING:
                        data_source = source
                        break

            # Store msg.
            data_sources_dict[source_type] = {"name": data_source, "message": msg}

        return data_sources_dict

    def convert_dataset(self, trans, target_type):
        """
        Converts a dataset to the target_type and returns a message indicating
        status of the conversion. None is returned to indicate that dataset
        was converted successfully.
        """

        # Get converted dataset; this will start the conversion if necessary.
        try:
            converted_dataset = self.get_converted_dataset(trans, target_type)
        except NoConverterException:
            return self.conversion_messages.NO_CONVERTER
        except ConverterDependencyException as dep_error:
            return {'kind': self.conversion_messages.ERROR, 'message': dep_error.value}

        # Check dataset state and return any messages.
        msg = None
        if converted_dataset and converted_dataset.state == Dataset.states.ERROR:
            job_id = trans.sa_session.query(JobToOutputDatasetAssociation) \
                .filter_by(dataset_id=converted_dataset.id).first().job_id
            job = trans.sa_session.query(Job).get(job_id)
            msg = {'kind': self.conversion_messages.ERROR, 'message': job.stderr}
        elif not converted_dataset or converted_dataset.state != Dataset.states.OK:
            msg = self.conversion_messages.PENDING

        return msg

    def serialize(self, id_encoder, serialization_options, for_link=False):
        if for_link:
            rval = dict_for(
                self
            )
            serialization_options.attach_identifier(id_encoder, self, rval)
            return rval

        rval = dict_for(
            self,
            create_time=self.create_time.__str__(),
            update_time=self.update_time.__str__(),
            name=unicodify(self.name),
            info=unicodify(self.info),
            blurb=self.blurb,
            peek=self.peek,
            extension=self.extension,
            metadata=_prepare_metadata_for_serialization(dict(self.metadata.items())),
            designation=self.designation,
            deleted=self.deleted,
            visible=self.visible,
            dataset_uuid=(lambda uuid: str(uuid) if uuid else None)(self.dataset.uuid),
        )

        serialization_options.attach_identifier(id_encoder, self, rval)
        return rval

    def _handle_serialize_files(self, id_encoder, serialization_options, rval):
        if serialization_options.serialize_dataset_objects:
            rval["dataset"] = self.dataset.serialize(id_encoder, serialization_options)
        else:
            serialization_options.serialize_files(self, rval)


class HistoryDatasetAssociation(DatasetInstance, HasTags, Dictifiable, UsesAnnotations,
                                HasName, RepresentById):
    """
    Resource class that creates a relation between a dataset and a user history.
    """

    def __init__(self,
                 hid=None,
                 history=None,
                 copied_from_history_dataset_association=None,
                 copied_from_library_dataset_dataset_association=None,
                 sa_session=None,
                 **kwd):
        """
        Create a a new HDA and associate it with the given history.
        """
        # FIXME: sa_session is must be passed to DataSetInstance if the create_dataset
        # parameter is True so that the new object can be flushed.  Is there a better way?
        DatasetInstance.__init__(self, sa_session=sa_session, **kwd)
        self.hid = hid
        # Relationships
        self.history = history
        self.copied_from_history_dataset_association = copied_from_history_dataset_association
        self.copied_from_library_dataset_dataset_association = copied_from_library_dataset_dataset_association

    def __create_version__(self, session):
        state = inspect(self)
        changes = {}

        for attr in state.mapper.columns:
            # We only create a new version if columns of the HDA table have changed, and ignore relationships.
            hist = state.get_history(attr.key, True)

            if not hist.has_changes():
                continue

            # hist.deleted holds old value(s)
            changes[attr.key] = hist.deleted
        if self.update_time and self.state == self.states.OK:
            # We only record changes to HDAs that exist in the database and have a update_time
            new_values = {}
            new_values['name'] = changes.get('name', self.name)
            new_values['dbkey'] = changes.get('dbkey', self.dbkey)
            new_values['extension'] = changes.get('extension', self.extension)
            new_values['extended_metadata_id'] = changes.get('extended_metadata_id', self.extended_metadata_id)
            for k, v in new_values.items():
                if isinstance(v, list):
                    new_values[k] = v[0]
            new_values['update_time'] = self.update_time
            new_values['version'] = self.version or 1
            new_values['metadata'] = self._metadata
            past_hda = HistoryDatasetAssociationHistory(history_dataset_association_id=self.id,
                                                        **new_values)
            self.version = self.version + 1 if self.version else 1
            session.add(past_hda)

    def copy(self, parent_id=None, copy_tags=None, force_flush=True, copy_hid=True, new_name=None):
        """
        Create a copy of this HDA.
        """
        hid = None
        if copy_hid:
            hid = self.hid
        hda = HistoryDatasetAssociation(hid=hid,
                                        name=new_name or self.name,
                                        info=self.info,
                                        blurb=self.blurb,
                                        peek=self.peek,
                                        tool_version=self.tool_version,
                                        extension=self.extension,
                                        dbkey=self.dbkey,
                                        dataset=self.dataset,
                                        visible=self.visible,
                                        deleted=self.deleted,
                                        parent_id=parent_id,
                                        copied_from_history_dataset_association=self,
                                        flush=False)
        # update init non-keywords as well
        hda.purged = self.purged
        hda.copy_tags_to(copy_tags)
        object_session(self).add(hda)
        flushed = False
        # May need to set after flushed, as MetadataFiles require dataset.id
        if hda.set_metadata_requires_flush:
            object_session(self).flush([self])
            flushed = True
        hda.metadata = self.metadata
        # In some instances peek relies on dataset_id, i.e. gmaj.zip for viewing MAFs
        if not self.datatype.copy_safe_peek:
            if not flushed:
                object_session(self).flush([self])

            hda.set_peek()
        if force_flush:
            object_session(self).flush()
        return hda

    def copy_tags_to(self, copy_tags=None):
        if copy_tags is not None:
            for tag in copy_tags.values():
                copied_tag = tag.copy(cls=HistoryDatasetAssociationTagAssociation)
                self.tags.append(copied_tag)

    def copy_attributes(self, new_dataset):
        new_dataset.hid = self.hid

    def to_library_dataset_dataset_association(self, trans, target_folder, replace_dataset=None,
                                               parent_id=None, user=None, roles=None, ldda_message='', element_identifier=None):
        """
        Copy this HDA to a library optionally replacing an existing LDDA.
        """
        if replace_dataset:
            # The replace_dataset param ( when not None ) refers to a LibraryDataset that
            #   is being replaced with a new version.
            library_dataset = replace_dataset
        else:
            # If replace_dataset is None, the Library level permissions will be taken from the folder and
            #   applied to the new LibraryDataset, and the current user's DefaultUserPermissions will be applied
            #   to the associated Dataset.
            library_dataset = LibraryDataset(folder=target_folder, name=self.name, info=self.info)
            object_session(self).add(library_dataset)
            object_session(self).flush()
        if not user:
            # This should never happen since users must be authenticated to upload to a data library
            user = self.history.user
        ldda = LibraryDatasetDatasetAssociation(name=element_identifier or self.name,
                                                info=self.info,
                                                blurb=self.blurb,
                                                peek=self.peek,
                                                tool_version=self.tool_version,
                                                extension=self.extension,
                                                dbkey=self.dbkey,
                                                dataset=self.dataset,
                                                library_dataset=library_dataset,
                                                visible=self.visible,
                                                deleted=self.deleted,
                                                parent_id=parent_id,
                                                copied_from_history_dataset_association=self,
                                                user=user)
        object_session(self).add(ldda)
        object_session(self).flush()
        # If roles were selected on the upload form, restrict access to the Dataset to those roles
        roles = roles or []
        for role in roles:
            dp = trans.model.DatasetPermissions(trans.app.security_agent.permitted_actions.DATASET_ACCESS.action,
                                                ldda.dataset, role)
            trans.sa_session.add(dp)
            trans.sa_session.flush()
        # Must set metadata after ldda flushed, as MetadataFiles require ldda.id
        ldda.metadata = self.metadata
        # TODO: copy #tags from history
        if ldda_message:
            ldda.message = ldda_message
        if not replace_dataset:
            target_folder.add_library_dataset(library_dataset, genome_build=ldda.dbkey)
            object_session(self).add(target_folder)
            object_session(self).flush()
        library_dataset.library_dataset_dataset_association_id = ldda.id
        object_session(self).add(library_dataset)
        object_session(self).flush()
        if not self.datatype.copy_safe_peek:
            # In some instances peek relies on dataset_id, i.e. gmaj.zip for viewing MAFs
            ldda.set_peek()
        object_session(self).flush()
        return ldda

    def clear_associated_files(self, metadata_safe=False, purge=False):
        """
        """
        # metadata_safe = True means to only clear when assoc.metadata_safe == False
        for assoc in self.implicitly_converted_datasets:
            if not assoc.deleted and (not metadata_safe or not assoc.metadata_safe):
                assoc.clear(purge=purge)
        for assoc in self.implicitly_converted_parent_datasets:
            assoc.clear(purge=purge, delete_dataset=False)

    def get_access_roles(self, trans):
        """
        Return The access roles associated with this HDA's dataset.
        """
        return self.dataset.get_access_roles(trans)

    def quota_amount(self, user):
        """
        Return the disk space used for this HDA relevant to user quotas.

        If the user has multiple instances of this dataset, it will not affect their
        disk usage statistic.
        """
        rval = 0
        # Anon users are handled just by their single history size.
        if not user:
            return rval
        # Gets an HDA disk usage, if the user does not already
        #   have an association of the same dataset
        if not self.dataset.library_associations and not self.purged and not self.dataset.purged:
            for hda in self.dataset.history_associations:
                if hda.id == self.id:
                    continue
                if not hda.purged and hda.history and hda.history.user and hda.history.user == user:
                    break
            else:
                rval += self.get_total_size()
        return rval

    def serialize(self, id_encoder, serialization_options, for_link=False):
        if for_link:
            rval = dict_for(
                self
            )
            serialization_options.attach_identifier(id_encoder, self, rval)
            return rval

        rval = super(HistoryDatasetAssociation, self).serialize(id_encoder, serialization_options)
        rval["hid"] = self.hid
        rval["annotation"] = unicodify(getattr(self, 'annotation', ''))
        rval["tags"] = self.make_tag_string_list()
        if self.history:
            rval["history_encoded_id"] = serialization_options.get_identifier(id_encoder, self.history)

        # Handle copied_from_history_dataset_association information...
        copied_from_history_dataset_association_chain = []
        src_hda = self
        while src_hda.copied_from_history_dataset_association:
            src_hda = src_hda.copied_from_history_dataset_association
            copied_from_history_dataset_association_chain.append(serialization_options.get_identifier(id_encoder, src_hda))
        rval["copied_from_history_dataset_association_id_chain"] = copied_from_history_dataset_association_chain
        self._handle_serialize_files(id_encoder, serialization_options, rval)
        return rval

    def to_dict(self, view='collection', expose_dataset_path=False):
        """
        Return attributes of this HDA that are exposed using the API.
        """
        # Since this class is a proxy to rather complex attributes we want to
        # display in other objects, we can't use the simpler method used by
        # other model classes.
        original_rval = super(HistoryDatasetAssociation, self).to_dict(view=view)
        hda = self
        rval = dict(id=hda.id,
                    hda_ldda='hda',
                    uuid=(lambda uuid: str(uuid) if uuid else None)(hda.dataset.uuid),
                    hid=hda.hid,
                    file_ext=hda.ext,
                    peek=unicodify(hda.display_peek()) if hda.peek and hda.peek != 'no peek' else None,
                    model_class=self.__class__.__name__,
                    name=hda.name,
                    deleted=hda.deleted,
                    purged=hda.purged,
                    visible=hda.visible,
                    state=hda.state,
                    history_content_type=hda.history_content_type,
                    file_size=int(hda.get_size()),
                    create_time=hda.create_time.isoformat(),
                    update_time=hda.update_time.isoformat(),
                    data_type=hda.datatype.__class__.__module__ + '.' + hda.datatype.__class__.__name__,
                    genome_build=hda.dbkey,
                    misc_info=hda.info.strip() if isinstance(hda.info, string_types) else hda.info,
                    misc_blurb=hda.blurb)

        rval.update(original_rval)

        if hda.copied_from_library_dataset_dataset_association is not None:
            rval['copied_from_ldda_id'] = hda.copied_from_library_dataset_dataset_association.id

        if hda.history is not None:
            rval['history_id'] = hda.history.id

        if hda.extended_metadata is not None:
            rval['extended_metadata'] = hda.extended_metadata.data

        for name, spec in hda.metadata.spec.items():
            val = hda.metadata.get(name)
            if isinstance(val, MetadataFile):
                # only when explicitly set: fetching filepaths can be expensive
                if not expose_dataset_path:
                    continue
                val = val.file_name
            # If no value for metadata, look in datatype for metadata.
            elif val is None and hasattr(hda.datatype, name):
                val = getattr(hda.datatype, name)
            rval['metadata_' + name] = val
        return rval

    @property
    def history_content_type(self):
        return "dataset"

    # TODO: down into DatasetInstance
    content_type = u'dataset'

    @hybrid.hybrid_property
    def type_id(self):
        return u'-'.join([self.content_type, str(self.id)])

    @type_id.expression
    def type_id(cls):
        return ((type_coerce(cls.content_type, types.Unicode) + u'-' +
                 type_coerce(cls.id, types.Unicode)).label('type_id'))


class HistoryDatasetAssociationHistory(RepresentById):
    def __init__(self,
                 history_dataset_association_id,
                 name,
                 dbkey,
                 update_time,
                 version,
                 extension,
                 extended_metadata_id,
                 metadata,
                 ):
        self.history_dataset_association_id = history_dataset_association_id
        self.name = name
        self.dbkey = dbkey
        self.update_time = update_time
        self.version = version
        self.extension = extension
        self.extended_metadata_id = extended_metadata_id
        self._metadata = metadata


class HistoryDatasetAssociationDisplayAtAuthorization(RepresentById):
    def __init__(self, hda=None, user=None, site=None):
        self.history_dataset_association = hda
        self.user = user
        self.site = site


class HistoryDatasetAssociationSubset(RepresentById):
    def __init__(self, hda, subset, location):
        self.hda = hda
        self.subset = subset
        self.location = location


class Library(Dictifiable, HasName, RepresentById):
    permitted_actions = get_permitted_actions(filter='LIBRARY')
    dict_collection_visible_keys = ['id', 'name']
    dict_element_visible_keys = ['id', 'deleted', 'name', 'description', 'synopsis', 'root_folder_id', 'create_time']

    def __init__(self, name=None, description=None, synopsis=None, root_folder=None):
        self.name = name or "Unnamed library"
        self.description = description
        self.synopsis = synopsis
        self.root_folder = root_folder

    def serialize(self, id_encoder, serialization_options):
        rval = dict_for(
            self,
            name=self.name,
            description=self.description,
            synopsis=self.synopsis,
        )
        if self.root_folder:
            rval["root_folder"] = self.root_folder.serialize(id_encoder, serialization_options)

        serialization_options.attach_identifier(id_encoder, self, rval)
        return rval

    def to_dict(self, view='collection', value_mapper=None):
        """
        We prepend an F to folders.
        """
        rval = super(Library, self).to_dict(view=view, value_mapper=value_mapper)
        if 'root_folder_id' in rval:
            rval['root_folder_id'] = 'F' + str(rval['root_folder_id'])
        return rval

    def get_active_folders(self, folder, folders=None):
        # TODO: should we make sure the library is not deleted?
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
        if folders is None:
            active_folders = [folder]
        for active_folder in folder.active_folders:
            active_folders.extend(self.get_active_folders(active_folder, folders))
        return sort_by_attr(active_folders, 'id')

    def get_access_roles(self, trans):
        roles = []
        for lp in self.actions:
            if lp.action == trans.app.security_agent.permitted_actions.LIBRARY_ACCESS.action:
                roles.append(lp.role)
        return roles


class LibraryFolder(Dictifiable, HasName, RepresentById):
    dict_element_visible_keys = ['id', 'parent_id', 'name', 'description', 'item_count', 'genome_build', 'update_time', 'deleted']

    def __init__(self, name=None, description=None, item_count=0, order_id=None, genome_build=None):
        self.name = name or "Unnamed folder"
        self.description = description
        self.item_count = item_count
        self.order_id = order_id
        self.genome_build = genome_build
        self.folders = []
        self.datasets = []

    def add_library_dataset(self, library_dataset, genome_build=None):
        library_dataset.folder_id = self.id
        library_dataset.order_id = self.item_count
        self.item_count += 1
        if genome_build not in [None, '?']:
            self.genome_build = genome_build

    def add_folder(self, folder):
        folder.parent_id = self.id
        folder.order_id = self.item_count
        self.item_count += 1

    @property
    def activatable_library_datasets(self):
        # This needs to be a list
        return [ld for ld in self.datasets if ld.library_dataset_dataset_association and not ld.library_dataset_dataset_association.dataset.deleted]

    def serialize(self, id_encoder, serialization_options):
        rval = dict_for(
            self,
            name=self.name,
            description=self.description,
            genome_build=self.genome_build,
            item_count=self.item_count,
            order_id=self.order_id,
            # update_time=self.update_time,
            deleted=self.deleted,
        )
        folders = []
        for folder in self.folders:
            folders.append(folder.serialize(id_encoder, serialization_options))
        rval["folders"] = folders
        datasets = []
        for dataset in self.datasets:
            datasets.append(dataset.serialize(id_encoder, serialization_options))
        rval['datasets'] = datasets
        serialization_options.attach_identifier(id_encoder, self, rval)
        return rval

    def to_dict(self, view='collection', value_mapper=None):
        rval = super(LibraryFolder, self).to_dict(view=view, value_mapper=value_mapper)
        rval['library_path'] = self.library_path
        rval['parent_library_id'] = self.parent_library.id
        return rval

    @property
    def library_path(self):
        l_path = []
        f = self
        while f.parent:
            l_path.insert(0, f.name)
            f = f.parent
        return l_path

    @property
    def parent_library(self):
        f = self
        while f.parent:
            f = f.parent
        return f.library_root[0]


class LibraryDataset(RepresentById):
    # This class acts as a proxy to the currently selected LDDA
    upload_options = [('upload_file', 'Upload files'),
                      ('upload_directory', 'Upload directory of files'),
                      ('upload_paths', 'Upload files from filesystem paths'),
                      ('import_from_history', 'Import datasets from your current history')]

    def __init__(self, folder=None, order_id=None, name=None, info=None, library_dataset_dataset_association=None, **kwd):
        self.folder = folder
        self.order_id = order_id
        self.name = name
        self.info = info
        self.library_dataset_dataset_association = library_dataset_dataset_association

    def set_library_dataset_dataset_association(self, ldda):
        self.library_dataset_dataset_association = ldda
        ldda.library_dataset = self
        object_session(self).add_all((ldda, self))
        object_session(self).flush()

    def get_info(self):
        if self.library_dataset_dataset_association:
            return self.library_dataset_dataset_association.info
        elif self._info:
            return self._info
        else:
            return 'no info'

    def set_info(self, info):
        self._info = info
    info = property(get_info, set_info)

    def get_name(self):
        if self.library_dataset_dataset_association:
            return self.library_dataset_dataset_association.name
        elif self._name:
            return self._name
        else:
            return 'Unnamed dataset'

    def set_name(self, name):
        self._name = name
    name = property(get_name, set_name)

    def display_name(self):
        self.library_dataset_dataset_association.display_name()

    def serialize(self, id_encoder, serialization_options):
        rval = dict_for(
            self,
            name=self.name,
            info=self.info,
            order_id=self.order_id,
            ldda=self.library_dataset_dataset_association.serialize(id_encoder, serialization_options, for_link=True),
        )
        serialization_options.attach_identifier(id_encoder, self, rval)
        return rval

    def to_dict(self, view='collection'):
        # Since this class is a proxy to rather complex attributes we want to
        # display in other objects, we can't use the simpler method used by
        # other model classes.
        ldda = self.library_dataset_dataset_association
        rval = dict(id=self.id,
                    ldda_id=ldda.id,
                    parent_library_id=self.folder.parent_library.id,
                    folder_id=self.folder_id,
                    model_class=self.__class__.__name__,
                    state=ldda.state,
                    name=ldda.name,
                    file_name=ldda.file_name,
                    uploaded_by=ldda.user.email,
                    message=ldda.message,
                    date_uploaded=ldda.create_time.isoformat(),
                    file_size=int(ldda.get_size()),
                    file_ext=ldda.ext,
                    data_type=ldda.datatype.__class__.__module__ + '.' + ldda.datatype.__class__.__name__,
                    genome_build=ldda.dbkey,
                    misc_info=ldda.info,
                    misc_blurb=ldda.blurb,
                    peek=(lambda ldda: ldda.display_peek() if ldda.peek and ldda.peek != 'no peek' else None)(ldda))
        if ldda.dataset.uuid is None:
            rval['uuid'] = None
        else:
            rval['uuid'] = str(ldda.dataset.uuid)
        for name, spec in ldda.metadata.spec.items():
            val = ldda.metadata.get(name)
            if isinstance(val, MetadataFile):
                val = val.file_name
            elif isinstance(val, list):
                val = ', '.join([str(v) for v in val])
            rval['metadata_' + name] = val
        return rval


class LibraryDatasetDatasetAssociation(DatasetInstance, HasName, RepresentById):
    def __init__(self,
                 copied_from_history_dataset_association=None,
                 copied_from_library_dataset_dataset_association=None,
                 library_dataset=None,
                 user=None,
                 sa_session=None,
                 **kwd):
        # FIXME: sa_session is must be passed to DataSetInstance if the create_dataset
        # parameter in kwd is True so that the new object can be flushed.  Is there a better way?
        DatasetInstance.__init__(self, sa_session=sa_session, **kwd)
        if copied_from_history_dataset_association:
            self.copied_from_history_dataset_association_id = copied_from_history_dataset_association.id
        if copied_from_library_dataset_dataset_association:
            self.copied_from_library_dataset_dataset_association_id = copied_from_library_dataset_dataset_association.id
        self.library_dataset = library_dataset
        self.user = user

    def to_history_dataset_association(self, target_history, parent_id=None, add_to_history=False):
        sa_session = object_session(self)
        hda = HistoryDatasetAssociation(name=self.name,
                                        info=self.info,
                                        blurb=self.blurb,
                                        peek=self.peek,
                                        tool_version=self.tool_version,
                                        extension=self.extension,
                                        dbkey=self.dbkey,
                                        dataset=self.dataset,
                                        visible=self.visible,
                                        deleted=self.deleted,
                                        parent_id=parent_id,
                                        copied_from_library_dataset_dataset_association=self,
                                        history=target_history)

        tag_manager = galaxy.model.tags.GalaxyTagHandler(sa_session)
        src_ldda_tags = tag_manager.get_tags_str(self.tags)
        tag_manager.apply_item_tags(user=self.user, item=hda, tags_str=src_ldda_tags)

        sa_session.add(hda)
        sa_session.flush()
        hda.metadata = self.metadata  # need to set after flushed, as MetadataFiles require dataset.id
        if add_to_history and target_history:
            target_history.add_dataset(hda)
        if not self.datatype.copy_safe_peek:
            hda.set_peek()  # in some instances peek relies on dataset_id, i.e. gmaj.zip for viewing MAFs
        sa_session.flush()
        return hda

    def copy(self, parent_id=None, target_folder=None):
        sa_session = object_session(self)
        ldda = LibraryDatasetDatasetAssociation(name=self.name,
                                                info=self.info,
                                                blurb=self.blurb,
                                                peek=self.peek,
                                                tool_version=self.tool_version,
                                                extension=self.extension,
                                                dbkey=self.dbkey,
                                                dataset=self.dataset,
                                                visible=self.visible,
                                                deleted=self.deleted,
                                                parent_id=parent_id,
                                                copied_from_library_dataset_dataset_association=self,
                                                folder=target_folder)

        tag_manager = galaxy.model.tags.GalaxyTagHandler(sa_session)
        src_ldda_tags = tag_manager.get_tags_str(self.tags)
        tag_manager.apply_item_tags(user=self.user, item=ldda, tags_str=src_ldda_tags)

        sa_session.add(ldda)
        sa_session.flush()
        # Need to set after flushed, as MetadataFiles require dataset.id
        ldda.metadata = self.metadata
        if not self.datatype.copy_safe_peek:
            # In some instances peek relies on dataset_id, i.e. gmaj.zip for viewing MAFs
            ldda.set_peek()
        sa_session.flush()
        return ldda

    def clear_associated_files(self, metadata_safe=False, purge=False):
        return

    def get_access_roles(self, trans):
        return self.dataset.get_access_roles(trans)

    def get_manage_permissions_roles(self, trans):
        return self.dataset.get_manage_permissions_roles(trans)

    def has_manage_permissions_roles(self, trans):
        return self.dataset.has_manage_permissions_roles(trans)

    def serialize(self, id_encoder, serialization_options, for_link=False):
        if for_link:
            rval = dict_for(
                self
            )
            serialization_options.attach_identifier(id_encoder, self, rval)
            return rval

        rval = super(LibraryDatasetDatasetAssociation, self).serialize(id_encoder, serialization_options)
        self._handle_serialize_files(id_encoder, serialization_options, rval)
        return rval

    def to_dict(self, view='collection'):
        # Since this class is a proxy to rather complex attributes we want to
        # display in other objects, we can't use the simpler method used by
        # other model classes.
        ldda = self
        try:
            file_size = int(ldda.get_size())
        except OSError:
            file_size = 0

        # TODO: render tags here
        rval = dict(id=ldda.id,
                    hda_ldda='ldda',
                    model_class=self.__class__.__name__,
                    name=ldda.name,
                    deleted=ldda.deleted,
                    visible=ldda.visible,
                    state=ldda.state,
                    library_dataset_id=ldda.library_dataset_id,
                    file_size=file_size,
                    file_name=ldda.file_name,
                    update_time=ldda.update_time.isoformat(),
                    file_ext=ldda.ext,
                    data_type=ldda.datatype.__class__.__module__ + '.' + ldda.datatype.__class__.__name__,
                    genome_build=ldda.dbkey,
                    misc_info=ldda.info,
                    misc_blurb=ldda.blurb)
        if ldda.dataset.uuid is None:
            rval['uuid'] = None
        else:
            rval['uuid'] = str(ldda.dataset.uuid)
        rval['parent_library_id'] = ldda.library_dataset.folder.parent_library.id
        if ldda.extended_metadata is not None:
            rval['extended_metadata'] = ldda.extended_metadata.data
        for name, spec in ldda.metadata.spec.items():
            val = ldda.metadata.get(name)
            if isinstance(val, MetadataFile):
                val = val.file_name
            # If no value for metadata, look in datatype for metadata.
            elif val is None and hasattr(ldda.datatype, name):
                val = getattr(ldda.datatype, name)
            rval['metadata_' + name] = val
        return rval


class ExtendedMetadata(RepresentById):
    def __init__(self, data):
        self.data = data


class ExtendedMetadataIndex(RepresentById):
    def __init__(self, extended_metadata, path, value):
        self.extended_metadata = extended_metadata
        self.path = path
        self.value = value


class LibraryInfoAssociation(RepresentById):
    def __init__(self, library, form_definition, info, inheritable=False):
        self.library = library
        self.template = form_definition
        self.info = info
        self.inheritable = inheritable


class LibraryFolderInfoAssociation(RepresentById):
    def __init__(self, folder, form_definition, info, inheritable=False):
        self.folder = folder
        self.template = form_definition
        self.info = info
        self.inheritable = inheritable


class LibraryDatasetDatasetInfoAssociation(RepresentById):
    def __init__(self, library_dataset_dataset_association, form_definition, info):
        # TODO: need to figure out if this should be inheritable to the associated LibraryDataset
        self.library_dataset_dataset_association = library_dataset_dataset_association
        self.template = form_definition
        self.info = info

    @property
    def inheritable(self):
        return True  # always allow inheriting, used for replacement


class ValidationError(RepresentById):
    def __init__(self, message=None, err_type=None, attributes=None):
        self.message = message
        self.err_type = err_type
        self.attributes = attributes


class DatasetToValidationErrorAssociation(object):
    def __init__(self, dataset, validation_error):
        self.dataset = dataset
        self.validation_error = validation_error


class ImplicitlyConvertedDatasetAssociation(RepresentById):

    def __init__(self, id=None, parent=None, dataset=None, file_type=None, deleted=False, purged=False, metadata_safe=True):
        self.id = id
        if isinstance(dataset, HistoryDatasetAssociation):
            self.dataset = dataset
        elif isinstance(dataset, LibraryDatasetDatasetAssociation):
            self.dataset_ldda = dataset
        else:
            raise AttributeError('Unknown dataset type provided for dataset: %s' % type(dataset))
        if isinstance(parent, HistoryDatasetAssociation):
            self.parent_hda = parent
        elif isinstance(parent, LibraryDatasetDatasetAssociation):
            self.parent_ldda = parent
        else:
            raise AttributeError('Unknown dataset type provided for parent: %s' % type(parent))
        self.type = file_type
        self.deleted = deleted
        self.purged = purged
        self.metadata_safe = metadata_safe

    def clear(self, purge=False, delete_dataset=True):
        self.deleted = True
        if self.dataset:
            if delete_dataset:
                self.dataset.deleted = True
            if purge:
                self.dataset.purged = True
        if purge and self.dataset.deleted:  # do something with purging
            self.purged = True
            try:
                os.unlink(self.file_name)
            except Exception as e:
                log.error("Failed to purge associated file (%s) from disk: %s" % (self.file_name, e))


DEFAULT_COLLECTION_NAME = "Unnamed Collection"


class DatasetCollection(Dictifiable, UsesAnnotations, RepresentById):
    """
    """
    dict_collection_visible_keys = ['id', 'collection_type']
    dict_element_visible_keys = ['id', 'collection_type']
    populated_states = Bunch(
        NEW='new',  # New dataset collection, unpopulated elements
        OK='ok',  # Collection elements populated (HDAs may or may not have errors)
        FAILED='failed',  # some problem populating state, won't be populated
    )

    def __init__(
        self,
        id=None,
        collection_type=None,
        populated=True,
        element_count=None
    ):
        self.id = id
        self.collection_type = collection_type
        if not populated:
            self.populated_state = DatasetCollection.populated_states.NEW
        self.element_count = element_count

    @property
    def dataset_states_and_extensions_summary(self):
        if not hasattr(self, '_dataset_states_and_extensions_summary'):
            db_session = object_session(self)

            dc = alias(DatasetCollection.table)
            de = alias(DatasetCollectionElement.table)
            hda = alias(HistoryDatasetAssociation.table)
            dataset = alias(Dataset.table)

            select_from = dc.outerjoin(de, de.c.dataset_collection_id == dc.c.id)

            depth_collection_type = self.collection_type
            while ":" in depth_collection_type:
                child_collection = alias(DatasetCollection.table)
                child_collection_element = alias(DatasetCollectionElement.table)
                select_from = select_from.outerjoin(child_collection, child_collection.c.id == de.c.child_collection_id)
                select_from = select_from.outerjoin(child_collection_element, child_collection_element.c.dataset_collection_id == child_collection.c.id)

                de = child_collection_element
                depth_collection_type = depth_collection_type.split(":", 1)[1]

            select_from = select_from.outerjoin(hda, hda.c.id == de.c.hda_id).outerjoin(dataset, hda.c.dataset_id == dataset.c.id)
            select_stmt = select([hda.c.extension, dataset.c.state]).select_from(select_from).where(dc.c.id == self.id).distinct()
            extensions = set()
            states = set()
            for extension, state in db_session.execute(select_stmt).fetchall():
                states.add(state)
                extensions.add(extension)

            self._dataset_states_and_extensions_summary = (states, extensions)

        return self._dataset_states_and_extensions_summary

    @property
    def populated_optimized(self):
        if not hasattr(self, '_populated_optimized'):
            _populated_optimized = True
            if ":" not in self.collection_type:
                _populated_optimized = self.populated_state == DatasetCollection.populated_states.OK
            else:
                db_session = object_session(self)

                dc = alias(DatasetCollection.table)
                de = alias(DatasetCollectionElement.table)

                select_from = dc.outerjoin(de, de.c.dataset_collection_id == dc.c.id)

                collection_depth_aliases = [dc]

                depth_collection_type = self.collection_type
                while ":" in depth_collection_type:
                    child_collection = alias(DatasetCollection.table)
                    child_collection_element = alias(DatasetCollectionElement.table)
                    select_from = select_from.outerjoin(child_collection, child_collection.c.id == de.c.child_collection_id)
                    select_from = select_from.outerjoin(child_collection_element, child_collection_element.c.dataset_collection_id == child_collection.c.id)

                    collection_depth_aliases.append(child_collection)

                    de = child_collection_element
                    depth_collection_type = depth_collection_type.split(":", 1)[1]

                select_stmt = select(list(map(lambda dc: dc.c.populated_state, collection_depth_aliases))).select_from(select_from).where(dc.c.id == self.id).distinct()
                for populated_states in db_session.execute(select_stmt).fetchall():
                    for populated_state in populated_states:
                        if populated_state != DatasetCollection.populated_states.OK:
                            _populated_optimized = False

            self._populated_optimized = _populated_optimized

        return self._populated_optimized

    @property
    def populated(self):
        top_level_populated = self.populated_state == DatasetCollection.populated_states.OK
        if top_level_populated and self.has_subcollections:
            return all(e.child_collection.populated for e in self.elements)
        return top_level_populated

    @property
    def dataset_action_tuples(self):
        if not hasattr(self, '_dataset_action_tuples'):
            db_session = object_session(self)

            dc = alias(DatasetCollection.table)
            de = alias(DatasetCollectionElement.table)
            hda = alias(HistoryDatasetAssociation.table)
            dataset = alias(Dataset.table)
            dataset_permission = alias(DatasetPermissions.table)

            select_from = dc.outerjoin(de, de.c.dataset_collection_id == dc.c.id)

            depth_collection_type = self.collection_type
            while ":" in depth_collection_type:
                child_collection = alias(DatasetCollection.table)
                child_collection_element = alias(DatasetCollectionElement.table)
                select_from = select_from.outerjoin(child_collection, child_collection.c.id == de.c.child_collection_id)
                select_from = select_from.outerjoin(child_collection_element, child_collection_element.c.dataset_collection_id == child_collection.c.id)

                de = child_collection_element
                depth_collection_type = depth_collection_type.split(":", 1)[1]

            select_from = select_from.outerjoin(hda, hda.c.id == de.c.hda_id).outerjoin(dataset, hda.c.dataset_id == dataset.c.id)
            select_from = select_from.outerjoin(dataset_permission, dataset.c.id == dataset_permission.c.dataset_id)

            select_stmt = select([dataset_permission.c.action, dataset_permission.c.role_id]).select_from(select_from).where(dc.c.id == self.id).distinct()

            _dataset_action_tuples = []
            for _dataset_action_tuple in db_session.execute(select_stmt).fetchall():
                if _dataset_action_tuple[0] is None:
                    continue
                _dataset_action_tuples.append(_dataset_action_tuple)

            self._dataset_action_tuples = _dataset_action_tuples

        return self._dataset_action_tuples

    @property
    def waiting_for_elements(self):
        top_level_waiting = self.populated_state == DatasetCollection.populated_states.NEW
        if not top_level_waiting and self.has_subcollections:
            return any(e.child_collection.waiting_for_elements for e in self.elements)
        return top_level_waiting

    def mark_as_populated(self):
        self.populated_state = DatasetCollection.populated_states.OK

    def handle_population_failed(self, message):
        self.populated_state = DatasetCollection.populated_states.FAILED
        self.populated_state_message = message

    def finalize(self, collection_type_description):
        # All jobs have written out their elements - everything should be populated
        # but might not be - check that second case! (TODO)
        self.mark_as_populated()
        if self.has_subcollections and collection_type_description.has_subcollections():
            for element in self.elements:
                element.child_collection.finalize(collection_type_description.child_collection_type_description())

    @property
    def dataset_instances(self):
        instances = []
        for element in self.elements:
            if element.is_collection:
                instances.extend(element.child_collection.dataset_instances)
            else:
                instance = element.dataset_instance
                instances.append(instance)
        return instances

    @property
    def dataset_elements(self):
        elements = []
        for element in self.elements:
            if element.is_collection:
                elements.extend(element.child_collection.dataset_elements)
            else:
                elements.append(element)
        return elements

    @property
    def first_dataset_element(self):
        for element in self.elements:
            if element.is_collection:
                first_element = element.child_collection.first_dataset_element
                if first_element:
                    return first_element
            else:
                return element
        return None

    @property
    def state(self):
        # TODO: DatasetCollection state handling...
        return 'ok'

    def validate(self):
        if self.collection_type is None:
            raise Exception("Each dataset collection must define a collection type.")

    def __getitem__(self, key):
        get_by_attribute = "element_index" if isinstance(key, int) else "element_identifier"
        for element in self.elements:
            if getattr(element, get_by_attribute) == key:
                return element
        error_message = "Dataset collection has no %s with key %s." % (get_by_attribute, key)
        raise KeyError(error_message)

    def copy(self, destination=None, element_destination=None):
        new_collection = DatasetCollection(
            collection_type=self.collection_type,
            element_count=self.element_count
        )
        for element in self.elements:
            element.copy_to_collection(
                new_collection,
                destination=destination,
                element_destination=element_destination,
            )
        object_session(self).add(new_collection)
        object_session(self).flush()
        return new_collection

    def replace_failed_elements(self, replacements):
        for element in self.elements:
            if element.element_object in replacements:
                if element.element_type == 'hda':
                    element.hda = replacements[element.element_object]
                    element.hda.visible = False
                # TODO: handle the case where elements are collections

    def set_from_dict(self, new_data):
        # Nothing currently editable in this class.
        return {}

    @property
    def has_subcollections(self):
        return ":" in self.collection_type

    def serialize(self, id_encoder, serialization_options):
        rval = dict_for(
            self,
            type=self.collection_type,
            populated_state=self.populated_state,
            elements=list(map(lambda e: e.serialize(id_encoder, serialization_options), self.elements))
        )
        serialization_options.attach_identifier(id_encoder, self, rval)
        return rval


class DatasetCollectionInstance(HasName):
    """
    """

    def __init__(
        self,
        collection=None,
        deleted=False,
    ):
        # Relationships
        self.collection = collection
        # Since deleted property is shared between history and dataset collections,
        # it could be on either table - some places in the code however it is convient
        # it is on instance instead of collection.
        self.deleted = deleted

    @property
    def state(self):
        return self.collection.state

    @property
    def populated(self):
        return self.collection.populated

    @property
    def dataset_instances(self):
        return self.collection.dataset_instances

    def display_name(self):
        return self.get_display_name()

    def _base_to_dict(self, view):
        return dict(
            id=self.id,
            name=self.name,
            collection_type=self.collection.collection_type,
            populated=self.populated,
            populated_state=self.collection.populated_state,
            populated_state_message=self.collection.populated_state_message,
            element_count=self.collection.element_count,
            type="collection",  # contents type (distinguished from file or folder (in case of library))
        )

    def set_from_dict(self, new_data):
        """
        Set object attributes to the values in dictionary new_data limiting
        to only those keys in dict_element_visible_keys.

        Returns a dictionary of the keys, values that have been changed.
        """
        # precondition: keys are proper, values are parsed and validated
        changed = self.collection.set_from_dict(new_data)

        # unknown keys are ignored here
        for key in (k for k in new_data.keys() if k in self.editable_keys):
            new_val = new_data[key]
            old_val = self.__getattribute__(key)
            if new_val == old_val:
                continue

            self.__setattr__(key, new_val)
            changed[key] = new_val

        return changed


class HistoryDatasetCollectionAssociation(DatasetCollectionInstance,
                                          HasTags,
                                          Dictifiable,
                                          UsesAnnotations,
                                          RepresentById):
    """ Associates a DatasetCollection with a History. """
    editable_keys = ('name', 'deleted', 'visible')

    def __init__(
        self,
        id=None,
        hid=None,
        collection=None,
        history=None,
        name=None,
        deleted=False,
        visible=True,
        copied_from_history_dataset_collection_association=None,
        implicit_output_name=None,
        implicit_input_collections=[],
    ):
        super(HistoryDatasetCollectionAssociation, self).__init__(
            collection=collection,
            deleted=deleted,
        )
        self.id = id
        self.hid = hid
        self.history = history
        self.name = name
        self.visible = visible
        self.copied_from_history_dataset_collection_association = copied_from_history_dataset_collection_association
        self.implicit_output_name = implicit_output_name
        self.implicit_input_collections = implicit_input_collections

    @property
    def history_content_type(self):
        return "dataset_collection"

    # TODO: down into DatasetCollectionInstance
    content_type = u'dataset_collection'

    @hybrid.hybrid_property
    def type_id(self):
        return u'-'.join([self.content_type, str(self.id)])

    @type_id.expression
    def type_id(cls):
        return ((type_coerce(cls.content_type, types.Unicode) + u'-' +
                 type_coerce(cls.id, types.Unicode)).label('type_id'))

    @property
    def job_source_type(self):
        if self.implicit_collection_jobs_id:
            return "ImplicitCollectionJobs"
        elif self.job_id:
            return "Job"
        else:
            return None

    @property
    def job_source_id(self):
        return self.implicit_collection_jobs_id or self.job_id

    def to_hda_representative(self, multiple=False):
        rval = []
        for dataset in self.collection.dataset_elements:
            rval.append(dataset.dataset_instance)
            if multiple is False:
                break
        if len(rval) > 0:
            return rval if multiple else rval[0]

    def serialize(self, id_encoder, serialization_options, for_link=False):
        if for_link:
            rval = dict_for(
                self
            )
            serialization_options.attach_identifier(id_encoder, self, rval)
            return rval

        rval = dict_for(
            self,
            display_name=self.display_name(),
            state=self.state,
            hid=self.hid,
            collection=self.collection.serialize(id_encoder, serialization_options),
            implicit_output_name=self.implicit_output_name,
        )
        if self.history:
            rval["history_encoded_id"] = serialization_options.get_identifier(id_encoder, self.history)

        implicit_input_collections = []
        for implicit_input_collection in self.implicit_input_collections:
            input_hdca = implicit_input_collection.input_dataset_collection
            implicit_input_collections.append({
                "name": implicit_input_collection.name,
                "input_dataset_collection": serialization_options.get_identifier(id_encoder, input_hdca)
            })
        if implicit_input_collections:
            rval["implicit_input_collections"] = implicit_input_collections

        # Handle copied_from_history_dataset_association information...
        copied_from_history_dataset_collection_association_chain = []
        src_hdca = self
        while src_hdca.copied_from_history_dataset_collection_association:
            src_hdca = src_hdca.copied_from_history_dataset_collection_association
            copied_from_history_dataset_collection_association_chain.append(serialization_options.get_identifier(id_encoder, src_hdca))
        rval["copied_from_history_dataset_collection_association_id_chain"] = copied_from_history_dataset_collection_association_chain
        serialization_options.attach_identifier(id_encoder, self, rval)
        return rval

    def to_dict(self, view='collection'):
        original_dict_value = super(HistoryDatasetCollectionAssociation, self).to_dict(view=view)
        dict_value = dict(
            hid=self.hid,
            history_id=self.history.id,
            history_content_type=self.history_content_type,
            visible=self.visible,
            deleted=self.deleted,
            job_source_id=self.job_source_id,
            job_source_type=self.job_source_type,
            **self._base_to_dict(view=view)
        )

        dict_value.update(original_dict_value)

        return dict_value

    def add_implicit_input_collection(self, name, history_dataset_collection):
        self.implicit_input_collections.append(ImplicitlyCreatedDatasetCollectionInput(name, history_dataset_collection))

    def find_implicit_input_collection(self, name):
        matching_collection = None
        for implicit_input_collection in self.implicit_input_collections:
            if implicit_input_collection.name == name:
                matching_collection = implicit_input_collection.input_dataset_collection
                break
        return matching_collection

    def copy(self, element_destination=None):
        """
        Create a copy of this history dataset collection association. Copy
        underlying collection.
        """
        hdca = HistoryDatasetCollectionAssociation(
            hid=self.hid,
            collection=None,
            visible=self.visible,
            deleted=self.deleted,
            name=self.name,
            copied_from_history_dataset_collection_association=self,
        )
        if self.implicit_collection_jobs_id:
            hdca.implicit_collection_jobs_id = self.implicit_collection_jobs_id
        elif self.job_id:
            hdca.job_id = self.job_id

        collection_copy = self.collection.copy(
            destination=hdca,
            element_destination=element_destination,
        )
        hdca.collection = collection_copy
        object_session(self).add(hdca)
        object_session(self).flush()
        return hdca


class LibraryDatasetCollectionAssociation(DatasetCollectionInstance, RepresentById):
    """ Associates a DatasetCollection with a library folder. """
    editable_keys = ('name', 'deleted')

    def __init__(
        self,
        id=None,
        collection=None,
        name=None,
        deleted=False,
        folder=None,
    ):
        super(LibraryDatasetCollectionAssociation, self).__init__(
            collection=collection,
            deleted=deleted,
        )
        self.id = id
        self.folder = folder
        self.name = name

    def to_dict(self, view='collection'):
        dict_value = dict(
            folder_id=self.folder.id,
            **self._base_to_dict(view=view)
        )
        return dict_value


class DatasetCollectionElement(Dictifiable, RepresentById):
    """ Associates a DatasetInstance (hda or ldda) with a DatasetCollection. """
    # actionable dataset id needs to be available via API...
    dict_collection_visible_keys = ['id', 'element_type', 'element_index', 'element_identifier']
    dict_element_visible_keys = ['id', 'element_type', 'element_index', 'element_identifier']

    UNINITIALIZED_ELEMENT = object()

    def __init__(
        self,
        id=None,
        collection=None,
        element=None,
        element_index=None,
        element_identifier=None,
    ):
        if isinstance(element, HistoryDatasetAssociation):
            self.hda = element
        elif isinstance(element, LibraryDatasetDatasetAssociation):
            self.ldda = element
        elif isinstance(element, DatasetCollection):
            self.child_collection = element
        elif element != self.UNINITIALIZED_ELEMENT:
            raise AttributeError('Unknown element type provided: %s' % type(element))

        self.id = id
        self.collection = collection
        self.element_index = element_index
        self.element_identifier = element_identifier or str(element_index)

    @property
    def element_type(self):
        if self.hda:
            return "hda"
        elif self.ldda:
            return "ldda"
        elif self.child_collection:
            # TOOD: Rename element_type to element_type.
            return "dataset_collection"
        else:
            return None

    @property
    def is_collection(self):
        return self.element_type == "dataset_collection"

    @property
    def element_object(self):
        if self.hda:
            return self.hda
        elif self.ldda:
            return self.ldda
        elif self.child_collection:
            return self.child_collection
        else:
            return None

    @property
    def dataset_instance(self):
        element_object = self.element_object
        if isinstance(element_object, DatasetCollection):
            raise AttributeError("Nested collection has no associated dataset_instance.")
        return element_object

    @property
    def dataset(self):
        return self.dataset_instance.dataset

    def first_dataset_instance(self):
        element_object = self.element_object
        if isinstance(element_object, DatasetCollection):
            return element_object.dataset_instances[0]
        else:
            return element_object

    @property
    def dataset_instances(self):
        element_object = self.element_object
        if isinstance(element_object, DatasetCollection):
            return element_object.dataset_instances
        else:
            return [element_object]

    def copy_to_collection(self, collection, destination=None, element_destination=None):
        element_object = self.element_object
        if element_destination:
            if self.is_collection:
                element_object = element_object.copy(
                    destination=destination,
                    element_destination=element_destination
                )
            else:
                new_element_object = element_object.copy()
                if destination is not None and element_object.hidden_beneath_collection_instance:
                    new_element_object.hidden_beneath_collection_instance = destination
                # Ideally we would not need to give the following
                # element an HID and it would exist in the history only
                # as an element of the containing collection.
                element_destination.add_dataset(new_element_object)
                element_object = new_element_object

        new_element = DatasetCollectionElement(
            element=element_object,
            collection=collection,
            element_index=self.element_index,
            element_identifier=self.element_identifier,
        )
        return new_element

    def serialize(self, id_encoder, serialization_options):
        rval = dict_for(
            self,
            element_type=self.element_type,
            element_index=self.element_index,
            element_identifier=self.element_identifier
        )
        serialization_options.attach_identifier(id_encoder, self, rval)
        element_obj = self.element_object
        if isinstance(element_obj, HistoryDatasetAssociation):
            rval["hda"] = element_obj.serialize(id_encoder, serialization_options, for_link=True)
        else:
            rval["child_collection"] = element_obj.serialize(id_encoder, serialization_options)
        return rval


class Event(RepresentById):
    def __init__(self, message=None, history=None, user=None, galaxy_session=None):
        self.history = history
        self.galaxy_session = galaxy_session
        self.user = user
        self.tool_id = None
        self.message = message


class GalaxySession(RepresentById):
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
        self.histories = []
        self.last_action = last_action or datetime.now()

    def add_history(self, history, association=None):
        if association is None:
            self.histories.append(GalaxySessionToHistoryAssociation(self, history))
        else:
            self.histories.append(association)

    def get_disk_usage(self):
        if self.disk_usage is None:
            return 0
        return self.disk_usage

    def set_disk_usage(self, bytes):
        self.disk_usage = bytes
    total_disk_usage = property(get_disk_usage, set_disk_usage)


class GalaxySessionToHistoryAssociation(RepresentById):
    def __init__(self, galaxy_session, history):
        self.galaxy_session = galaxy_session
        self.history = history


class UCI(object):
    def __init__(self):
        self.id = None
        self.user = None


class StoredWorkflow(HasTags, Dictifiable, RepresentById):

    dict_collection_visible_keys = ['id', 'name', 'published', 'deleted']
    dict_element_visible_keys = ['id', 'name', 'published', 'deleted']

    def __init__(self):
        self.id = None
        self.user = None
        self.name = None
        self.slug = None
        self.published = False
        self.latest_workflow_id = None
        self.workflows = []

    def get_internal_version(self, version):
        if version is None:
            return self.latest_workflow
        if len(self.workflows) <= version:
            raise Exception("Version does not exist")
        return list(reversed(self.workflows))[version]

    def show_in_tool_panel(self, user_id):
        sa_session = object_session(self)
        return bool(sa_session.query(StoredWorkflowMenuEntry).filter(
            StoredWorkflowMenuEntry.stored_workflow_id == self.id,
            StoredWorkflowMenuEntry.user_id == user_id,
        ).count())

    def copy_tags_from(self, target_user, source_workflow):
        # Override to only copy owner tags.
        for src_swta in source_workflow.owner_tags:
            new_swta = src_swta.copy()
            new_swta.user = target_user
            self.tags.append(new_swta)

    def to_dict(self, view='collection', value_mapper=None):
        rval = super(StoredWorkflow, self).to_dict(view=view, value_mapper=value_mapper)
        rval['latest_workflow_uuid'] = (lambda uuid: str(uuid) if self.latest_workflow.uuid else None)(self.latest_workflow.uuid)
        return rval


class Workflow(Dictifiable, RepresentById):

    dict_collection_visible_keys = ['name', 'has_cycles', 'has_errors']
    dict_element_visible_keys = ['name', 'has_cycles', 'has_errors']
    input_step_types = ['data_input', 'data_collection_input', 'parameter_input']

    def __init__(self, uuid=None):
        self.user = None
        self.name = None
        self.has_cycles = None
        self.has_errors = None
        self.steps = []
        if uuid is None:
            self.uuid = uuid4()
        else:
            self.uuid = UUID(str(uuid))

    def has_outputs_defined(self):
        """
        Returns true or false indicating whether or not a workflow has outputs defined.
        """
        for step in self.steps:
            if step.workflow_outputs:
                return True
        return False

    def to_dict(self, view='collection', value_mapper=None):
        rval = super(Workflow, self).to_dict(view=view, value_mapper=value_mapper)
        rval['uuid'] = (lambda uuid: str(uuid) if uuid else None)(self.uuid)
        return rval

    @property
    def steps_by_id(self):
        steps = {}
        for step in self.steps:
            step_id = step.id
            steps[step_id] = step
        return steps

    def step_by_index(self, order_index):
        for step in self.steps:
            if order_index == step.order_index:
                return step
        raise KeyError("Workflow has no step with order_index '%s'" % order_index)

    @property
    def input_steps(self):
        for step in self.steps:
            if step.type in Workflow.input_step_types:
                yield step

    @property
    def workflow_outputs(self):
        for step in self.steps:
            for workflow_output in step.workflow_outputs:
                yield workflow_output

    @property
    def top_level_workflow(self):
        """ If this workflow is not attached to stored workflow directly,
        recursively grab its parents until it is the top level workflow
        which must have a stored workflow associated with it.
        """
        top_level_workflow = self
        if self.stored_workflow is None:
            # TODO: enforce this at creation...
            assert len(set(w.uuid for w in self.parent_workflow_steps)) == 1
            return self.parent_workflow_steps[0].workflow.top_level_workflow
        return top_level_workflow

    @property
    def top_level_stored_workflow(self):
        """ If this workflow is not attached to stored workflow directly,
        recursively grab its parents until it is the top level workflow
        which must have a stored workflow associated with it and then
        grab that stored workflow.
        """
        return self.top_level_workflow.stored_workflow

    def copy(self):
        """ Copy a workflow (without user information) for a new
        StoredWorkflow object.
        """
        copied_workflow = Workflow()
        copied_workflow.name = self.name
        copied_workflow.has_cycles = self.has_cycles
        copied_workflow.has_errors = self.has_errors

        # Map old step ids to new steps
        step_mapping = {}
        copied_steps = []
        for step in self.steps:
            copied_step = WorkflowStep()
            copied_steps.append(copied_step)
            step_mapping[step.id] = copied_step

        for old_step, new_step in zip(self.steps, copied_steps):
            old_step.copy_to(new_step, step_mapping)
        copied_workflow.steps = copied_steps
        return copied_workflow

    def log_str(self):
        extra = ""
        if self.stored_workflow:
            extra = ",name=%s" % self.stored_workflow.name
        return "Workflow[id=%d%s]" % (self.id, extra)


class WorkflowStep(RepresentById):

    def __init__(self):
        self.id = None
        self.type = None
        self.tool_id = None
        self.tool_inputs = None
        self.tool_errors = None
        self.dynamic_tool = None
        self.position = None
        self.inputs = []
        self.config = None
        self.label = None
        self.uuid = uuid4()
        self.workflow_outputs = []
        self._input_connections_by_name = None

    @property
    def tool_uuid(self):
        return self.dynamic_tool and self.dynamic_tool.uuid

    def get_input(self, input_name):
        for step_input in self.inputs:
            if step_input.name == input_name:
                return step_input

        return None

    def get_or_add_input(self, input_name):
        step_input = self.get_input(input_name)

        if step_input is None:
            step_input = WorkflowStepInput(self)
            step_input.name = input_name
        return step_input

    def add_connection(self, input_name, output_name, output_step, input_subworkflow_step_index=None):
        step_input = self.get_or_add_input(input_name)

        conn = WorkflowStepConnection()
        conn.input_step_input = step_input
        conn.output_name = output_name
        conn.output_step = output_step
        if input_subworkflow_step_index is not None:
            input_subworkflow_step = self.subworkflow.step_by_index(input_subworkflow_step_index)
            conn.input_subworkflow_step = input_subworkflow_step
        return conn

    @property
    def input_connections(self):
        connections = [_ for step_input in self.inputs for _ in step_input.connections]
        return connections

    @property
    def unique_workflow_outputs(self):
        # Older Galaxy workflows may have multiple WorkflowOutputs
        # per "output_name", when serving these back to the editor
        # feed only a "best" output per "output_name.""
        outputs = {}
        for workflow_output in self.workflow_outputs:
            output_name = workflow_output.output_name

            if output_name in outputs:
                found_output = outputs[output_name]
                if found_output.label is None and workflow_output.label is not None:
                    outputs[output_name] = workflow_output
            else:
                outputs[output_name] = workflow_output
        return list(outputs.values())

    @property
    def content_id(self):
        content_id = None
        if self.type == "tool":
            content_id = self.tool_id
        elif self.type == "subworkflow":
            content_id = self.subworkflow.id
        else:
            content_id = None
        return content_id

    @property
    def input_connections_by_name(self):
        if self._input_connections_by_name is None:
            self.setup_input_connections_by_name()
        return self._input_connections_by_name

    def setup_input_connections_by_name(self):
        # Ensure input_connections has already been set.

        # Make connection information available on each step by input name.
        input_connections_by_name = {}
        for conn in self.input_connections:
            input_name = conn.input_name
            if input_name not in input_connections_by_name:
                input_connections_by_name[input_name] = []
            input_connections_by_name[input_name].append(conn)
        self._input_connections_by_name = input_connections_by_name

    def create_or_update_workflow_output(self, output_name, label, uuid):
        output = self.workflow_output_for(output_name)
        if output is None:
            output = WorkflowOutput(workflow_step=self, output_name=output_name)
        if uuid is not None:
            output.uuid = uuid
        if label is not None:
            output.label = label
        return output

    def workflow_output_for(self, output_name):
        target_output = None
        for workflow_output in self.workflow_outputs:
            if workflow_output.output_name == output_name:
                target_output = workflow_output
                break
        return target_output

    def copy_to(self, copied_step, step_mapping):
        copied_step.order_index = self.order_index
        copied_step.type = self.type
        copied_step.tool_id = self.tool_id
        copied_step.tool_inputs = self.tool_inputs
        copied_step.tool_errors = self.tool_errors
        copied_step.position = self.position
        copied_step.config = self.config
        copied_step.label = self.label
        copied_step.inputs = copy_list(self.inputs, copied_step)

        subworkflow_step_mapping = {}
        subworkflow = self.subworkflow
        if subworkflow:
            copied_subworkflow = subworkflow.copy()
            copied_step.subworkflow = copied_subworkflow
            for subworkflow_step, copied_subworkflow_step in zip(subworkflow.steps, copied_subworkflow.steps):
                subworkflow_step_mapping[subworkflow_step.id] = copied_subworkflow_step

        for old_conn, new_conn in zip(self.input_connections, copied_step.input_connections):
            new_conn.input_step_input = copied_step.get_or_add_input(old_conn.input_name)
            new_conn.output_step = step_mapping[old_conn.output_step_id]
            if old_conn.input_subworkflow_step_id:
                new_conn.input_subworkflow_step = subworkflow_step_mapping[old_conn.input_subworkflow_step_id]
        for orig_pja in self.post_job_actions:
            PostJobAction(orig_pja.action_type,
                          copied_step,
                          output_name=orig_pja.output_name,
                          action_arguments=orig_pja.action_arguments)
        copied_step.workflow_outputs = copy_list(self.workflow_outputs, copied_step)

    def log_str(self):
        return "WorkflowStep[index=%d,type=%s]" % (self.order_index, self.type)


class WorkflowStepInput(RepresentById):
    default_merge_type = None
    default_scatter_type = None

    def __init__(self, workflow_step):
        self.workflow_step = workflow_step
        self.name = None
        self.default_value = None
        self.default_value_set = False
        self.merge_type = self.default_merge_type
        self.scatter_type = self.default_scatter_type

    def copy(self, copied_step):
        copied_step_input = WorkflowStepInput(copied_step)
        copied_step_input.name = self.name
        copied_step_input.default_value = self.default_value
        copied_step_input.default_value_set = self.default_value_set
        copied_step_input.merge_type = self.merge_type
        copied_step_input.scatter_type = self.scatter_type

        copied_step_input.connections = copy_list(self.connections)
        return copied_step_input


class WorkflowStepConnection(RepresentById):
    # Constant used in lieu of output_name and input_name to indicate an
    # implicit connection between two steps that is not dependent on a dataset
    # or a dataset collection. Allowing for instance data manager steps to setup
    # index data before a normal tool runs or for workflows that manage data
    # outside of Galaxy.
    NON_DATA_CONNECTION = "__NO_INPUT_OUTPUT_NAME__"

    def __init__(self):
        self.output_step_id = None
        self.output_name = None
        self.input_step_input_id = None

    @property
    def non_data_connection(self):
        return (self.output_name == self.input_name == WorkflowStepConnection.NON_DATA_CONNECTION)

    @property
    def input_name(self):
        return self.input_step_input.name

    @property
    def input_step(self):
        return self.input_step_input and self.input_step_input.workflow_step

    @property
    def input_step_id(self):
        input_step = self.input_step
        return input_step and input_step.id

    def copy(self):
        # TODO: handle subworkflow ids...
        copied_connection = WorkflowStepConnection()
        copied_connection.output_name = self.output_name
        return copied_connection


class WorkflowOutput(RepresentById):

    def __init__(self, workflow_step, output_name=None, label=None, uuid=None):
        self.workflow_step = workflow_step
        self.output_name = output_name
        self.label = label
        if uuid is None:
            self.uuid = uuid4()
        else:
            self.uuid = UUID(str(uuid))

    def copy(self, copied_step):
        copied_output = WorkflowOutput(copied_step)
        copied_output.output_name = self.output_name
        copied_output.label = self.label
        return copied_output


class StoredWorkflowUserShareAssociation(RepresentById):

    def __init__(self):
        self.stored_workflow = None
        self.user = None


class StoredWorkflowMenuEntry(RepresentById):

    def __init__(self):
        self.stored_workflow = None
        self.user = None
        self.order_index = None


class WorkflowInvocation(UsesCreateAndUpdateTime, Dictifiable, RepresentById):
    dict_collection_visible_keys = ['id', 'update_time', 'workflow_id', 'history_id', 'uuid', 'state']
    dict_element_visible_keys = ['id', 'update_time', 'workflow_id', 'history_id', 'uuid', 'state']
    states = Bunch(
        NEW='new',  # Brand new workflow invocation... maybe this should be same as READY
        READY='ready',  # Workflow ready for another iteration of scheduling.
        SCHEDULED='scheduled',  # Workflow has been scheduled.
        CANCELLED='cancelled',
        FAILED='failed',
    )

    def __init__(self):
        self.subworkflow_invocations = []
        self.step_states = []
        self.steps = []

    def create_subworkflow_invocation_for_step(self, step):
        assert step.type == "subworkflow"
        subworkflow_invocation = WorkflowInvocation()
        self.attach_subworkflow_invocation_for_step(step, subworkflow_invocation)
        return subworkflow_invocation

    def attach_subworkflow_invocation_for_step(self, step, subworkflow_invocation):
        assert step.type == "subworkflow"
        assoc = WorkflowInvocationToSubworkflowInvocationAssociation()
        assoc.workflow_invocation = self
        assoc.workflow_step = step
        subworkflow_invocation.history = self.history
        subworkflow_invocation.workflow = step.subworkflow
        assoc.subworkflow_invocation = subworkflow_invocation
        self.subworkflow_invocations.append(assoc)
        return assoc

    def get_subworkflow_invocation_for_step(self, step):
        assoc = self.get_subworkflow_invocation_association_for_step(step)
        return assoc.subworkflow_invocation

    def get_subworkflow_invocation_association_for_step(self, step):
        assert step.type == "subworkflow"
        assoc = None
        for subworkflow_invocation in self.subworkflow_invocations:
            if subworkflow_invocation.workflow_step == step:
                assoc = subworkflow_invocation
                break
        return assoc

    @property
    def active(self):
        """ Indicates the workflow invocation is somehow active - and in
        particular valid actions may be performed on its
        WorkflowInvocationSteps.
        """
        states = WorkflowInvocation.states
        return self.state in [states.NEW, states.READY]

    def cancel(self):
        if not self.active:
            return False
        else:
            self.state = WorkflowInvocation.states.CANCELLED
            return True

    def fail(self):
        self.state = WorkflowInvocation.states.FAILED

    def step_states_by_step_id(self):
        step_states = {}
        for step_state in self.step_states:
            step_id = step_state.workflow_step_id
            step_states[step_id] = step_state
        return step_states

    def step_invocations_by_step_id(self):
        step_invocations = {}
        for invocation_step in self.steps:
            step_id = invocation_step.workflow_step_id
            assert step_id not in step_invocations
            step_invocations[step_id] = invocation_step
        return step_invocations

    def step_invocation_for_step_id(self, step_id):
        target_invocation_step = None
        for invocation_step in self.steps:
            if step_id == invocation_step.workflow_step_id:
                target_invocation_step = invocation_step
        return target_invocation_step

    @staticmethod
    def poll_unhandled_workflow_ids(sa_session):
        and_conditions = [
            WorkflowInvocation.state == WorkflowInvocation.states.NEW,
            WorkflowInvocation.handler.is_(None)
        ]
        query = sa_session.query(
            WorkflowInvocation.id
        ).filter(and_(*and_conditions)).order_by(WorkflowInvocation.table.c.id.asc())
        return [wid for wid in query.all()]

    @staticmethod
    def poll_active_workflow_ids(
        sa_session,
        scheduler=None,
        handler=None
    ):
        and_conditions = [
            or_(
                WorkflowInvocation.state == WorkflowInvocation.states.NEW,
                WorkflowInvocation.state == WorkflowInvocation.states.READY
            ),
        ]
        if scheduler is not None:
            and_conditions.append(WorkflowInvocation.scheduler == scheduler)
        if handler is not None:
            and_conditions.append(WorkflowInvocation.handler == handler)

        query = sa_session.query(
            WorkflowInvocation.id
        ).filter(and_(*and_conditions)).order_by(WorkflowInvocation.table.c.id.asc())
        # Immediately just load all ids into memory so time slicing logic
        # is relatively intutitive.
        return [wid for wid in query.all()]

    def add_output(self, workflow_output, step, output_object):
        if output_object.history_content_type == "dataset":
            output_assoc = WorkflowInvocationOutputDatasetAssociation()
            output_assoc.workflow_invocation = self
            output_assoc.workflow_output = workflow_output
            output_assoc.workflow_step = step
            output_assoc.dataset = output_object
            self.output_datasets.append(output_assoc)
        elif output_object.history_content_type == "dataset_collection":
            output_assoc = WorkflowInvocationOutputDatasetCollectionAssociation()
            output_assoc.workflow_invocation = self
            output_assoc.workflow_output = workflow_output
            output_assoc.workflow_step = step
            output_assoc.dataset_collection = output_object
            self.output_dataset_collections.append(output_assoc)
        else:
            raise Exception("Unknown output type encountered")

    def to_dict(self, view='collection', value_mapper=None, step_details=False, legacy_job_state=False):
        rval = super(WorkflowInvocation, self).to_dict(view=view, value_mapper=value_mapper)
        if view == 'element':
            steps = []
            for step in self.steps:
                if step_details:
                    v = step.to_dict(view='element')
                else:
                    v = step.to_dict(view='collection')
                if legacy_job_state:
                    step_jobs = step.jobs
                    if step_jobs:
                        for step_job in step_jobs:
                            v_clone = v.copy()
                            v_clone["state"] = step_job.state
                            v_clone["job_id"] = step_job.id
                            steps.append(v_clone)
                    else:
                        v["state"] = None
                        steps.append(v)
                else:
                    steps.append(v)
            rval['steps'] = steps

            inputs = {}
            for step in self.steps:
                if step.workflow_step.type == 'tool':
                    for job in step.jobs:
                        for step_input in step.workflow_step.input_connections:
                            output_step_type = step_input.output_step.type
                            if output_step_type in ['data_input', 'data_collection_input']:
                                src = "hda" if output_step_type == 'data_input' else 'hdca'
                                for job_input in job.input_datasets:
                                    if job_input.name == step_input.input_name:
                                        inputs[str(step_input.output_step.order_index)] = {
                                            "id": job_input.dataset_id, "src": src,
                                            "uuid" : str(job_input.dataset.dataset.uuid) if job_input.dataset.dataset.uuid is not None else None
                                        }
            rval['inputs'] = inputs

            outputs = {}
            for output_assoc in self.output_datasets:
                label = output_assoc.workflow_output.label
                if not label:
                    continue

                outputs[label] = {
                    'src': 'hda',
                    'id': output_assoc.dataset_id,
                }

            output_collections = {}
            for output_assoc in self.output_dataset_collections:
                label = output_assoc.workflow_output.label
                if not label:
                    continue

                output_collections[label] = {
                    'src': 'hdca',
                    'id': output_assoc.dataset_collection_id,
                }

            rval['outputs'] = outputs
            rval['output_collections'] = output_collections
        return rval

    def update(self):
        self.update_time = galaxy.model.orm.now.now()

    def add_input(self, content, step_id):
        history_content_type = getattr(content, "history_content_type", None)
        if history_content_type == "dataset":
            request_to_content = WorkflowRequestToInputDatasetAssociation()
            request_to_content.dataset = content
            request_to_content.workflow_step_id = step_id
            self.input_datasets.append(request_to_content)
        elif history_content_type == "dataset_collection":
            request_to_content = WorkflowRequestToInputDatasetCollectionAssociation()
            request_to_content.dataset_collection = content
            request_to_content.workflow_step_id = step_id
            self.input_dataset_collections.append(request_to_content)
        else:
            request_to_content = WorkflowRequestInputStepParameter()
            request_to_content.parameter_value = content
            request_to_content.workflow_step_id = step_id
            self.input_step_parameters.append(request_to_content)

    @property
    def resource_parameters(self):
        resource_type = WorkflowRequestInputParameter.types.RESOURCE_PARAMETERS
        _resource_parameters = {}
        for input_parameter in self.input_parameters:
            if input_parameter.type == resource_type:
                _resource_parameters[input_parameter.name] = input_parameter.value

        return _resource_parameters

    def has_input_for_step(self, step_id):
        for content in self.input_datasets:
            if content.workflow_step_id == step_id:
                return True
        for content in self.input_dataset_collections:
            if content.workflow_step_id == step_id:
                return True
        return False

    def set_handler(self, handler):
        self.handler = handler

    def log_str(self):
        extra = ""
        safe_id = getattr(self, "id", None)
        if safe_id is not None:
            extra += "id=%s" % safe_id
        else:
            extra += "unflushed"
        return "%s[%s]" % (self.__class__.__name__, extra)


class WorkflowInvocationToSubworkflowInvocationAssociation(Dictifiable, RepresentById):
    dict_collection_visible_keys = ['id', 'workflow_step_id', 'workflow_invocation_id', 'subworkflow_invocation_id']
    dict_element_visible_keys = ['id', 'workflow_step_id', 'workflow_invocation_id', 'subworkflow_invocation_id']


class WorkflowInvocationStep(Dictifiable, RepresentById):
    dict_collection_visible_keys = ['id', 'update_time', 'job_id', 'workflow_step_id', 'state', 'action']
    dict_element_visible_keys = ['id', 'update_time', 'job_id', 'workflow_step_id', 'state', 'action']
    states = Bunch(
        NEW='new',  # Brand new workflow invocation step
        READY='ready',  # Workflow invocation step ready for another iteration of scheduling.
        SCHEDULED='scheduled',  # Workflow invocation step has been scheduled.
        # CANCELLED='cancelled',  TODO: implement and expose
        # FAILED='failed',  TODO: implement and expose
    )

    def update(self):
        self.workflow_invocation.update()

    @property
    def is_new(self):
        return self.state == self.states.NEW

    def add_output(self, output_name, output_object):
        if output_object.history_content_type == "dataset":
            output_assoc = WorkflowInvocationStepOutputDatasetAssociation()
            output_assoc.workflow_invocation_step = self
            output_assoc.dataset = output_object
            output_assoc.output_name = output_name
            self.output_datasets.append(output_assoc)
        elif output_object.history_content_type == "dataset_collection":
            output_assoc = WorkflowInvocationStepOutputDatasetCollectionAssociation()
            output_assoc.workflow_invocation_step = self
            output_assoc.dataset_collection = output_object
            output_assoc.output_name = output_name
            self.output_dataset_collections.append(output_assoc)
        else:
            raise Exception("Unknown output type encountered")

    @property
    def jobs(self):
        if self.job:
            return [self.job]
        elif self.implicit_collection_jobs:
            return self.implicit_collection_jobs.job_list
        else:
            return []

    def to_dict(self, view='collection', value_mapper=None):
        rval = super(WorkflowInvocationStep, self).to_dict(view=view, value_mapper=value_mapper)
        rval['order_index'] = self.workflow_step.order_index
        rval['workflow_step_label'] = self.workflow_step.label
        rval['workflow_step_uuid'] = str(self.workflow_step.uuid)
        # Following no longer makes sense...
        # rval['state'] = self.job.state if self.job is not None else None
        if view == 'element':
            jobs = []
            for job in self.jobs:
                jobs.append(job.to_dict())

            outputs = {}
            for output_assoc in self.output_datasets:
                name = output_assoc.output_name
                outputs[name] = {
                    'src': 'hda',
                    'id': output_assoc.dataset.id,
                    'uuid': str(output_assoc.dataset.dataset.uuid) if output_assoc.dataset.dataset.uuid is not None else None
                }

            output_collections = {}
            for output_assoc in self.output_dataset_collections:
                name = output_assoc.output_name
                output_collections[name] = {
                    'src': 'hdca',
                    'id': output_assoc.dataset_collection.id,
                }

            rval['outputs'] = outputs
            rval['output_collections'] = output_collections
            rval['jobs'] = jobs
        return rval


class WorkflowRequestInputParameter(Dictifiable, RepresentById):
    """ Workflow-related parameters not tied to steps or inputs.
    """
    dict_collection_visible_keys = ['id', 'name', 'value', 'type']
    types = Bunch(
        REPLACEMENT_PARAMETERS='replacements',
        STEP_PARAMETERS='step',
        META_PARAMETERS='meta',
        RESOURCE_PARAMETERS='resource',
    )

    def __init__(self, name=None, value=None, type=None):
        self.name = name
        self.value = value
        self.type = type


class WorkflowRequestStepState(Dictifiable, RepresentById):
    """ Workflow step value parameters.
    """
    dict_collection_visible_keys = ['id', 'name', 'value', 'workflow_step_id']

    def __init__(self, workflow_step=None, name=None, value=None):
        self.workflow_step = workflow_step
        self.name = name
        self.value = value
        self.type = type


class WorkflowRequestToInputDatasetAssociation(Dictifiable, RepresentById):
    """ Workflow step input dataset parameters.
    """
    dict_collection_visible_keys = ['id', 'workflow_invocation_id', 'workflow_step_id', 'dataset_id', 'name']


class WorkflowRequestToInputDatasetCollectionAssociation(Dictifiable, RepresentById):
    """ Workflow step input dataset collection parameters.
    """
    dict_collection_visible_keys = ['id', 'workflow_invocation_id', 'workflow_step_id', 'dataset_collection_id', 'name']


class WorkflowRequestInputStepParameter(Dictifiable, RepresentById):
    """ Workflow step parameter inputs.
    """
    dict_collection_visible_keys = ['id', 'workflow_invocation_id', 'workflow_step_id', 'parameter_value']


class WorkflowInvocationOutputDatasetAssociation(Dictifiable, RepresentById):
    """Represents links to output datasets for the workflow."""
    dict_collection_visible_keys = ['id', 'workflow_invocation_id', 'workflow_step_id', 'dataset_id', 'name']


class WorkflowInvocationOutputDatasetCollectionAssociation(Dictifiable, RepresentById):
    """Represents links to output dataset collections for the workflow."""
    dict_collection_visible_keys = ['id', 'workflow_invocation_id', 'workflow_step_id', 'dataset_collection_id', 'name']


class WorkflowInvocationStepOutputDatasetAssociation(Dictifiable, RepresentById):
    """Represents links to output datasets for the workflow."""
    dict_collection_visible_keys = ['id', 'workflow_invocation_step_id', 'dataset_id', 'output_name']


class WorkflowInvocationStepOutputDatasetCollectionAssociation(Dictifiable, RepresentById):
    """Represents links to output dataset collections for the workflow."""
    dict_collection_visible_keys = ['id', 'workflow_invocation_step_id', 'dataset_collection_id', 'output_name']


class MetadataFile(StorableObject, RepresentById):

    def __init__(self, dataset=None, name=None, uuid=None):
        super(MetadataFile, self).__init__(id=None, uuid=uuid)
        if isinstance(dataset, HistoryDatasetAssociation):
            self.history_dataset = dataset
        elif isinstance(dataset, LibraryDatasetDatasetAssociation):
            self.library_dataset = dataset
        self.name = name

    @property
    def file_name(self):
        # Ensure the directory structure and the metadata file object exist
        try:
            da = self.history_dataset or self.library_dataset
            if self.object_store_id is None and da is not None:
                self.object_store_id = da.dataset.object_store_id
            object_store = da.dataset.object_store
            store_by = object_store.store_by
            identifier = getattr(self, store_by)
            alt_name = "metadata_%s.dat" % identifier
            if not object_store.exists(self, extra_dir='_metadata_files', extra_dir_at_root=True, alt_name=alt_name):
                object_store.create(self, extra_dir='_metadata_files', extra_dir_at_root=True, alt_name=alt_name)
            path = object_store.get_filename(self, extra_dir='_metadata_files', extra_dir_at_root=True, alt_name=alt_name)
            return path
        except AttributeError:
            assert self.id is not None, "ID must be set before MetadataFile used without an HDA/LDDA (commit the object)"
            # In case we're not working with the history_dataset
            path = os.path.join(Dataset.file_path, '_metadata_files', *directory_hash_id(self.id))
            # Create directory if it does not exist
            try:
                os.makedirs(path)
            except OSError as e:
                # File Exists is okay, otherwise reraise
                if e.errno != errno.EEXIST:
                    raise
            # Return filename inside hashed directory
            return os.path.abspath(os.path.join(path, "metadata_%d.dat" % self.id))


class FormDefinition(Dictifiable, RepresentById):
    # The following form_builder classes are supported by the FormDefinition class.
    supported_field_types = [AddressField, CheckboxField, PasswordField, SelectField, TextArea, TextField, WorkflowField, WorkflowMappingField, HistoryField]
    types = Bunch(USER_INFO='User Information')
    dict_collection_visible_keys = ['id', 'name']
    dict_element_visible_keys = ['id', 'name', 'desc', 'form_definition_current_id', 'fields', 'layout']

    def __init__(self, name=None, desc=None, fields=[], form_definition_current=None, form_type=None, layout=None):
        self.name = name
        self.desc = desc
        self.fields = fields
        self.form_definition_current = form_definition_current
        self.type = form_type
        self.layout = layout

    def to_dict(self, user=None, values=None, security=None):
        values = values or {}
        form_def = {'id': security.encode_id(self.id) if security else self.id, 'name': self.name, 'inputs': []}
        for field in self.fields:
            FieldClass = ({'AddressField'         : AddressField,
                           'CheckboxField'        : CheckboxField,
                           'HistoryField'         : HistoryField,
                           'PasswordField'        : PasswordField,
                           'SelectField'          : SelectField,
                           'TextArea'             : TextArea,
                           'TextField'            : TextField,
                           'WorkflowField'        : WorkflowField}).get(field['type'], TextField)
            form_def['inputs'].append(FieldClass(user=user, value=values.get(field['name'], field['default']), security=security, **field).to_dict())
        return form_def

    def grid_fields(self, grid_index):
        # Returns a dictionary whose keys are integers corresponding to field positions
        # on the grid and whose values are the field.
        gridfields = {}
        for i, f in enumerate(self.fields):
            if str(f['layout']) == str(grid_index):
                gridfields[i] = f
        return gridfields


class FormDefinitionCurrent(RepresentById):
    def __init__(self, form_definition=None):
        self.latest_form = form_definition


class FormValues(RepresentById):
    def __init__(self, form_def=None, content=None):
        self.form_definition = form_def
        self.content = content


class UserAddress(RepresentById):
    def __init__(self, user=None, desc=None, name=None, institution=None,
                 address=None, city=None, state=None, postal_code=None,
                 country=None, phone=None):
        self.user = user
        self.desc = desc
        self.name = name
        self.institution = institution
        self.address = address
        self.city = city
        self.state = state
        self.postal_code = postal_code
        self.country = country
        self.phone = phone

    def to_dict(self, trans):
        return {'id'           : trans.security.encode_id(self.id),
                'name'         : sanitize_html(self.name),
                'desc'         : sanitize_html(self.desc),
                'institution'  : sanitize_html(self.institution),
                'address'      : sanitize_html(self.address),
                'city'         : sanitize_html(self.city),
                'state'        : sanitize_html(self.state),
                'postal_code'  : sanitize_html(self.postal_code),
                'country'      : sanitize_html(self.country),
                'phone'        : sanitize_html(self.phone)}


class PSAAssociation(AssociationMixin, RepresentById):

    # This static property is set at: galaxy.authnz.psa_authnz.PSAAuthnz
    sa_session = None

    def __init__(self, server_url=None, handle=None, secret=None, issued=None, lifetime=None, assoc_type=None):
        self.server_url = server_url
        self.handle = handle
        self.secret = secret
        self.issued = issued
        self.lifetime = lifetime
        self.assoc_type = assoc_type

    def save(self):
        self.sa_session.add(self)
        self.sa_session.flush()

    @classmethod
    def store(cls, server_url, association):
        try:
            assoc = cls.sa_session.query(cls).filter_by(server_url=server_url, handle=association.handle)[0]
        except IndexError:
            assoc = cls(server_url=server_url, handle=association.handle)
        assoc.secret = base64.encodestring(association.secret).decode()
        assoc.issued = association.issued
        assoc.lifetime = association.lifetime
        assoc.assoc_type = association.assoc_type
        cls.sa_session.add(assoc)
        cls.sa_session.flush()

    @classmethod
    def get(cls, *args, **kwargs):
        return cls.sa_session.query(cls).filter_by(*args, **kwargs)

    @classmethod
    def remove(cls, ids_to_delete):
        cls.sa_session.query(cls).filter(cls.id.in_(ids_to_delete)).delete(synchronize_session='fetch')


class PSACode(CodeMixin, RepresentById):
    __table_args__ = (UniqueConstraint('code', 'email'),)

    # This static property is set at: galaxy.authnz.psa_authnz.PSAAuthnz
    sa_session = None

    def __init__(self, email, code):
        self.email = email
        self.code = code

    def save(self):
        self.sa_session.add(self)
        self.sa_session.flush()

    @classmethod
    def get_code(cls, code):
        return cls.sa_session.query(cls).filter(cls.code == code).first()


class PSANonce(NonceMixin, RepresentById):

    # This static property is set at: galaxy.authnz.psa_authnz.PSAAuthnz
    sa_session = None

    def __init__(self, server_url, timestamp, salt):
        self.server_url = server_url
        self.timestamp = timestamp
        self.salt = salt

    def save(self):
        self.sa_session.add(self)
        self.sa_session.flush()

    @classmethod
    def use(cls, server_url, timestamp, salt):
        try:
            return cls.sa_session.query(cls).filter_by(server_url=server_url, timestamp=timestamp, salt=salt)[0]
        except IndexError:
            instance = cls(server_url=server_url, timestamp=timestamp, salt=salt)
            cls.sa_session.add(instance)
            cls.sa_session.flush()
            return instance


class PSAPartial(PartialMixin, RepresentById):

    # This static property is set at: galaxy.authnz.psa_authnz.PSAAuthnz
    sa_session = None

    def __init__(self, token, data, next_step, backend):
        self.token = token
        self.data = data
        self.next_step = next_step
        self.backend = backend

    def save(self):
        self.sa_session.add(self)
        self.sa_session.flush()

    @classmethod
    def load(cls, token):
        return cls.sa_session.query(cls).filter(cls.token == token).first()

    @classmethod
    def destroy(cls, token):
        partial = cls.load(token)
        if partial:
            cls.sa_session.delete(partial)


class UserAuthnzToken(UserMixin, RepresentById):
    __table_args__ = (UniqueConstraint('provider', 'uid'),)

    # This static property is set at: galaxy.authnz.psa_authnz.PSAAuthnz
    sa_session = None

    def __init__(self, provider, uid, extra_data=None, lifetime=None, assoc_type=None, user=None):
        self.provider = provider
        self.uid = uid
        self.user_id = user.id
        self.extra_data = extra_data
        self.lifetime = lifetime
        self.assoc_type = assoc_type

    def get_id_token(self, strategy):
        if self.access_token_expired():
            # Access and ID tokens have same expiration time;
            # hence, if one is expired, the other is expired too.
            self.refresh_token(strategy)
        return self.extra_data.get('id_token', None) if self.extra_data is not None else None

    def set_extra_data(self, extra_data=None):
        if super(UserAuthnzToken, self).set_extra_data(extra_data):
            self.sa_session.add(self)
            self.sa_session.flush()

    def save(self):
        self.sa_session.add(self)
        self.sa_session.flush()

    @classmethod
    def username_max_length(cls):
        # Note: This is the maximum field length set for the username column of the galaxy_user table.
        # A better alternative is to retrieve this number from the table, instead of this const value.
        return 255

    @classmethod
    def user_model(cls):
        return User

    @classmethod
    def changed(cls, user):
        cls.sa_session.add(user)
        cls.sa_session.flush()

    @classmethod
    def user_query(cls):
        return cls.sa_session.query(cls.user_model())

    @classmethod
    def user_exists(cls, *args, **kwargs):
        return cls.user_query().filter_by(*args, **kwargs).count() > 0

    @classmethod
    def get_username(cls, user):
        return getattr(user, 'username', None)

    @classmethod
    def create_user(cls, *args, **kwargs):
        model = cls.user_model()
        instance = model(*args, **kwargs)
        instance.set_random_password()
        cls.sa_session.add(instance)
        cls.sa_session.flush()
        return instance

    @classmethod
    def get_user(cls, pk):
        return cls.user_query().get(pk)

    @classmethod
    def get_users_by_email(cls, email):
        return cls.user_query().filter_by(email=email)

    @classmethod
    def get_social_auth(cls, provider, uid):
        uid = str(uid)
        try:
            return cls.sa_session.query(cls).filter_by(provider=provider, uid=uid)[0]
        except IndexError:
            return None

    @classmethod
    def get_social_auth_for_user(cls, user, provider=None, id=None):
        qs = cls.sa_session.query(cls).filter_by(user_id=user.id)
        if provider:
            qs = qs.filter_by(provider=provider)
        if id:
            qs = qs.filter_by(id=id)
        return qs

    @classmethod
    def create_social_auth(cls, user, uid, provider):
        uid = str(uid)
        instance = cls(user=user, uid=uid, provider=provider)
        cls.sa_session.add(instance)
        cls.sa_session.flush()
        return instance


class CloudAuthz(RepresentById):
    def __init__(self, user_id, provider, config, authn_id, description=""):
        self.id = None
        self.user_id = user_id
        self.provider = provider
        self.config = config
        self.authn_id = authn_id
        self.tokens = None
        self.last_update = datetime.now()
        self.last_activity = datetime.now()
        self.description = description

    def __eq__(self, other):
        if not isinstance(other, CloudAuthz):
            return False
        return self.equals(other.user_id, other.provider, other.authn_id, other.config)

    def __ne__(self, other):
        return not self.__eq__(other)

    def equals(self, user_id, provider, authn_id, config):
        return (self.user_id == user_id and
                self.provider == provider and
                self.authn_id == authn_id and
                len({k: self.config[k] for k in self.config if k in config and
                     self.config[k] == config[k]}) == len(self.config))


class Page(Dictifiable, RepresentById):
    dict_element_visible_keys = ['id', 'title', 'latest_revision_id', 'slug', 'published', 'importable', 'deleted']

    def __init__(self):
        self.id = None
        self.user = None
        self.title = None
        self.slug = None
        self.latest_revision_id = None
        self.revisions = []
        self.importable = None
        self.published = None

    def to_dict(self, view='element'):
        rval = super(Page, self).to_dict(view=view)
        rev = []
        for a in self.revisions:
            rev.append(a.id)
        rval['revision_ids'] = rev
        return rval


class PageRevision(Dictifiable, RepresentById):
    dict_element_visible_keys = ['id', 'page_id', 'title', 'content']

    def __init__(self):
        self.user = None
        self.title = None
        self.content = None

    def to_dict(self, view='element'):
        rval = super(PageRevision, self).to_dict(view=view)
        rval['create_time'] = str(self.create_time)
        rval['update_time'] = str(self.update_time)
        return rval


class PageUserShareAssociation(RepresentById):
    def __init__(self):
        self.page = None
        self.user = None


class Visualization(RepresentById):
    def __init__(self, id=None, user=None, type=None, title=None, dbkey=None, slug=None, latest_revision=None):
        self.id = id
        self.user = user
        self.type = type
        self.title = title
        self.dbkey = dbkey
        self.slug = slug
        self.latest_revision = latest_revision
        self.revisions = []
        if self.latest_revision:
            self.revisions.append(latest_revision)

    def copy(self, user=None, title=None):
        """
        Provide copy of visualization with only its latest revision.
        """
        # NOTE: a shallow copy is done: the config is copied as is but datasets
        # are not copied nor are the dataset ids changed. This means that the
        # user does not have a copy of the data in his/her history and the
        # user who owns the datasets may delete them, making them inaccessible
        # for the current user.
        # TODO: a deep copy option is needed.

        if not user:
            user = self.user
        if not title:
            title = self.title

        copy_viz = Visualization(user=user, type=self.type, title=title, dbkey=self.dbkey)
        copy_revision = self.latest_revision.copy(visualization=copy_viz)
        copy_viz.latest_revision = copy_revision
        return copy_viz


class VisualizationRevision(RepresentById):
    def __init__(self, visualization=None, title=None, dbkey=None, config=None):
        self.id = None
        self.visualization = visualization
        self.title = title
        self.dbkey = dbkey
        self.config = config

    def copy(self, visualization=None):
        """
        Returns a copy of this object.
        """
        if not visualization:
            visualization = self.visualization

        return VisualizationRevision(
            visualization=visualization,
            title=self.title,
            dbkey=self.dbkey,
            config=self.config
        )


class VisualizationUserShareAssociation(RepresentById):
    def __init__(self):
        self.visualization = None
        self.user = None


class TransferJob(RepresentById):
    # These states are used both by the transfer manager's IPC and the object
    # state in the database.  Not all states are used by both.
    states = Bunch(NEW='new',
                   UNKNOWN='unknown',
                   PROGRESS='progress',
                   RUNNING='running',
                   ERROR='error',
                   DONE='done')
    terminal_states = [states.ERROR,
                       states.DONE]

    def __init__(self, state=None, path=None, info=None, pid=None, socket=None, params=None):
        self.state = state
        self.path = path
        self.info = info
        self.pid = pid
        self.socket = socket
        self.params = params


class Tag(RepresentById):
    def __init__(self, id=None, type=None, parent_id=None, name=None):
        self.id = id
        self.type = type
        self.parent_id = parent_id
        self.name = name

    def __str__(self):
        return "Tag(id=%s, type=%i, parent_id=%s, name=%s)" % (self.id, self.type or -1, self.parent_id, self.name)


class ItemTagAssociation(Dictifiable):
    dict_collection_visible_keys = ['id', 'user_tname', 'user_value']
    dict_element_visible_keys = dict_collection_visible_keys

    def __init__(self, id=None, user=None, item_id=None, tag_id=None, user_tname=None, value=None):
        self.id = id
        self.user = user
        self.item_id = item_id
        self.tag_id = tag_id
        self.user_tname = user_tname
        self.value = None
        self.user_value = None

    def copy(self, cls=None):
        if cls:
            new_ta = cls()
        else:
            new_ta = type(self)()
        new_ta.tag_id = self.tag_id
        new_ta.user_tname = self.user_tname
        new_ta.value = self.value
        new_ta.user_value = self.user_value
        return new_ta


class HistoryTagAssociation(ItemTagAssociation, RepresentById):
    pass


class DatasetTagAssociation(ItemTagAssociation, RepresentById):
    pass


class HistoryDatasetAssociationTagAssociation(ItemTagAssociation, RepresentById):
    pass


class LibraryDatasetDatasetAssociationTagAssociation(ItemTagAssociation, RepresentById):
    pass


class PageTagAssociation(ItemTagAssociation, RepresentById):
    pass


class WorkflowStepTagAssociation(ItemTagAssociation, RepresentById):
    pass


class StoredWorkflowTagAssociation(ItemTagAssociation, RepresentById):
    pass


class VisualizationTagAssociation(ItemTagAssociation, RepresentById):
    pass


class HistoryDatasetCollectionTagAssociation(ItemTagAssociation, RepresentById):
    pass


class LibraryDatasetCollectionTagAssociation(ItemTagAssociation, RepresentById):
    pass


class ToolTagAssociation(ItemTagAssociation, RepresentById):
    def __init__(self, id=None, user=None, tool_id=None, tag_id=None, user_tname=None, value=None):
        self.id = id
        self.user = user
        self.tool_id = tool_id
        self.tag_id = tag_id
        self.user_tname = user_tname
        self.value = None
        self.user_value = None


# Item annotation classes.
class HistoryAnnotationAssociation(RepresentById):
    pass


class HistoryDatasetAssociationAnnotationAssociation(RepresentById):
    pass


class StoredWorkflowAnnotationAssociation(RepresentById):
    pass


class WorkflowStepAnnotationAssociation(RepresentById):
    pass


class PageAnnotationAssociation(RepresentById):
    pass


class VisualizationAnnotationAssociation(RepresentById):
    pass


class HistoryDatasetCollectionAssociationAnnotationAssociation(RepresentById):
    pass


class LibraryDatasetCollectionAnnotationAssociation(RepresentById):
    pass


# Item rating classes.
class ItemRatingAssociation(object):
    def __init__(self, id=None, user=None, item=None, rating=0):
        self.id = id
        self.user = user
        self.item = item
        self.rating = rating

    def set_item(self, item):
        """ Set association's item. """
        pass


class HistoryRatingAssociation(ItemRatingAssociation, RepresentById):
    def set_item(self, history):
        self.history = history


class HistoryDatasetAssociationRatingAssociation(ItemRatingAssociation, RepresentById):
    def set_item(self, history_dataset_association):
        self.history_dataset_association = history_dataset_association


class StoredWorkflowRatingAssociation(ItemRatingAssociation, RepresentById):
    def set_item(self, stored_workflow):
        self.stored_workflow = stored_workflow


class PageRatingAssociation(ItemRatingAssociation, RepresentById):
    def set_item(self, page):
        self.page = page


class VisualizationRatingAssociation(ItemRatingAssociation, RepresentById):
    def set_item(self, visualization):
        self.visualization = visualization


class HistoryDatasetCollectionRatingAssociation(ItemRatingAssociation, RepresentById):
    def set_item(self, dataset_collection):
        self.dataset_collection = dataset_collection


class LibraryDatasetCollectionRatingAssociation(ItemRatingAssociation, RepresentById):
    def set_item(self, dataset_collection):
        self.dataset_collection = dataset_collection


# Data manager classes.
class DataManagerHistoryAssociation(RepresentById):
    def __init__(self, id=None, history=None, user=None):
        self.id = id
        self.history = history
        self.user = user


class DataManagerJobAssociation(RepresentById):
    def __init__(self, id=None, job=None, data_manager_id=None):
        self.id = id
        self.job = job
        self.data_manager_id = data_manager_id


class UserPreference(RepresentById):
    def __init__(self, name=None, value=None):
        self.name = name
        self.value = value


class UserAction(RepresentById):
    def __init__(self, id=None, create_time=None, user_id=None, session_id=None, action=None, params=None, context=None):
        self.id = id
        self.create_time = create_time
        self.user_id = user_id
        self.session_id = session_id
        self.action = action
        self.params = params
        self.context = context


class APIKeys(RepresentById):
    def __init__(self, id=None, user_id=None, key=None):
        self.id = id
        self.user_id = user_id
        self.key = key


def copy_list(lst, *args, **kwds):
    if lst is None:
        return lst
    else:
        return [el.copy(*args, **kwds) for el in lst]


def _prepare_metadata_for_serialization(metadata):
    """ Prepare metatdata for exporting. """
    for name, value in list(metadata.items()):
        # Metadata files are not needed for export because they can be
        # regenerated.
        if isinstance(value, MetadataFile):
            del metadata[name]
    return metadata
