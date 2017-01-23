"""
Galaxy data model classes

Naming: try to use class names that have a distinct plural form so that
the relationship cardinalities are obvious (e.g. prefer Dataset to Data)
"""
import codecs
import errno
import json
import logging
import numbers
import operator
import os
import socket
import time
from datetime import datetime, timedelta
from string import Template
from uuid import UUID, uuid4

from six import string_types
from sqlalchemy import (and_, func, join, not_, or_, select, true, type_coerce,
                        types)
from sqlalchemy.ext import hybrid
from sqlalchemy.orm import aliased, joinedload, object_session

import galaxy.model.metadata
import galaxy.model.orm.now
import galaxy.security.passwords
import galaxy.util
from galaxy.model.item_attrs import UsesAnnotations
from galaxy.security import get_permitted_actions
from galaxy.util import (directory_hash_id, Params, ready_name_for_url,
                         restore_text, send_mail, unicodify, unique_id)
from galaxy.util.bunch import Bunch
from galaxy.util.dictifiable import Dictifiable
from galaxy.util.hash_util import new_secure_hash
from galaxy.util.multi_byte import is_multi_byte
from galaxy.util.sanitize_html import sanitize_html
from galaxy.web.form_builder import (AddressField, CheckboxField, HistoryField,
                                     PasswordField, SelectField, TextArea, TextField, WorkflowField,
                                     WorkflowMappingField)
from galaxy.web.framework.helpers import to_unicode

log = logging.getLogger( __name__ )

_datatypes_registry = None

# When constructing filters with in for a fixed set of ids, maximum
# number of items to place in the IN statement. Different databases
# are going to have different limits so it is likely best to not let
# this be unlimited - filter in Python if over this limit.
MAX_IN_FILTER_LENGTH = 100


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


def set_datatypes_registry( d_registry ):
    """
    Set up datatypes_registry
    """
    global _datatypes_registry
    _datatypes_registry = d_registry


class HasName:

    def get_display_name( self ):
        """
        These objects have a name attribute can be either a string or a unicode
        object. If string, convert to unicode object assuming 'utf-8' format.
        """
        name = self.name
        name = unicodify( name, 'utf-8' )
        return name


class JobLike:

    def _init_metrics( self ):
        self.text_metrics = []
        self.numeric_metrics = []

    def add_metric( self, plugin, metric_name, metric_value ):
        plugin = unicodify( plugin, 'utf-8' )
        metric_name = unicodify( metric_name, 'utf-8' )
        if isinstance( metric_value, numbers.Number ):
            metric = self._numeric_metric( plugin, metric_name, metric_value )
            self.numeric_metrics.append( metric )
        else:
            metric_value = unicodify( metric_value, 'utf-8' )
            if len( metric_value ) > 1022:
                # Truncate these values - not needed with sqlite
                # but other backends must need it.
                metric_value = metric_value[ :1022 ]
            metric = self._text_metric( plugin, metric_name, metric_value )
            self.text_metrics.append( metric )

    @property
    def metrics( self ):
        # TODO: Make iterable, concatenate with chain
        return self.text_metrics + self.numeric_metrics

    def set_streams( self, stdout, stderr ):
        stdout = galaxy.util.unicodify( stdout )
        stderr = galaxy.util.unicodify( stderr )
        if ( len( stdout ) > galaxy.util.DATABASE_MAX_STRING_SIZE ):
            stdout = galaxy.util.shrink_string_by_size( stdout, galaxy.util.DATABASE_MAX_STRING_SIZE, join_by="\n..\n", left_larger=True, beginning_on_size_error=True )
            log.info( "stdout for %s %d is greater than %s, only a portion will be logged to database", type(self), self.id, galaxy.util.DATABASE_MAX_STRING_SIZE_PRETTY )
        self.stdout = stdout
        if ( len( stderr ) > galaxy.util.DATABASE_MAX_STRING_SIZE ):
            stderr = galaxy.util.shrink_string_by_size( stderr, galaxy.util.DATABASE_MAX_STRING_SIZE, join_by="\n..\n", left_larger=True, beginning_on_size_error=True )
            log.info( "stderr for %s %d is greater than %s, only a portion will be logged to database", type(self), self.id, galaxy.util.DATABASE_MAX_STRING_SIZE_PRETTY )
        self.stderr = stderr

    def log_str(self):
        extra = ""
        safe_id = getattr(self, "id", None)
        if safe_id is not None:
            extra += "id=%s" % safe_id
        else:
            extra += "unflushed"

        return "%s[%s,tool_id=%s]" % (self.__class__.__name__, extra, self.tool_id)


class User( object, Dictifiable ):
    use_pbkdf2 = True
    """
    Data for a Galaxy user or admin and relations to their
    histories, credentials, and roles.
    """
    # attributes that will be accessed and returned when calling to_dict( view='collection' )
    dict_collection_visible_keys = ( 'id', 'email', 'username' )
    # attributes that will be accessed and returned when calling to_dict( view='element' )
    dict_element_visible_keys = ( 'id', 'email', 'username', 'total_disk_usage', 'nice_total_disk_usage' )

    def __init__( self, email=None, password=None ):
        self.email = email
        self.password = password
        self.external = False
        self.deleted = False
        self.purged = False
        self.active = False
        self.activation_token = None
        self.username = None
        self.last_password_change = None
        # Relationships
        self.histories = []
        self.credentials = []
        # ? self.roles = []

    def set_password_cleartext( self, cleartext ):
        """
        Set user password to the digest of `cleartext`.
        """
        if User.use_pbkdf2:
            self.password = galaxy.security.passwords.hash_password( cleartext )
        else:
            self.password = new_secure_hash( text_type=cleartext )
        self.last_password_change = datetime.now()

    def check_password( self, cleartext ):
        """
        Check if `cleartext` matches user password when hashed.
        """
        return galaxy.security.passwords.check_password( cleartext, self.password )

    def all_roles( self ):
        """
        Return a unique list of Roles associated with this user or any of their groups.
        """
        try:
            db_session = object_session( self )
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

        roles = [ ura.role for ura in user.roles ]
        for group in [ uga.group for uga in user.groups ]:
            for role in [ gra.role for gra in group.roles ]:
                if role not in roles:
                    roles.append( role )
        return roles

    def all_roles_exploiting_cache( self ):
        """
        """
        roles = [ ura.role for ura in self.roles ]
        for group in [ uga.group for uga in self.groups ]:
            for role in [ gra.role for gra in group.roles ]:
                if role not in roles:
                    roles.append( role )
        return roles

    def get_disk_usage( self, nice_size=False ):
        """
        Return byte count of disk space used by user or a human-readable
        string if `nice_size` is `True`.
        """
        rval = 0
        if self.disk_usage is not None:
            rval = self.disk_usage
        if nice_size:
            rval = galaxy.util.nice_size( rval )
        return rval

    def set_disk_usage( self, bytes ):
        """
        Manually set the disk space used by a user to `bytes`.
        """
        self.disk_usage = bytes

    total_disk_usage = property( get_disk_usage, set_disk_usage )

    def adjust_total_disk_usage( self, amount ):
        if amount != 0:
            self.disk_usage = func.coalesce(self.table.c.disk_usage, 0) + amount

    @property
    def nice_total_disk_usage( self ):
        """
        Return byte count of disk space used in a human-readable string.
        """
        return self.get_disk_usage( nice_size=True )

    def calculate_disk_usage( self ):
        """
        Return byte count total of disk space used by all non-purged, non-library
        HDAs in non-purged histories.
        """
        # maintain a list so that we don't double count
        dataset_ids = []
        total = 0
        # this can be a huge number and can run out of memory, so we avoid the mappers
        db_session = object_session( self )
        for history in db_session.query( History ).enable_eagerloads( False ).filter_by( user_id=self.id, purged=False ).yield_per( 1000 ):
            for hda in db_session.query( HistoryDatasetAssociation ).enable_eagerloads( False ).filter_by( history_id=history.id, purged=False ).yield_per( 1000 ):
                # TODO: def hda.counts_toward_disk_usage():
                #   return ( not self.dataset.purged and not self.dataset.library_associations )
                if hda.dataset.id not in dataset_ids and not hda.dataset.purged and not hda.dataset.library_associations:
                    dataset_ids.append( hda.dataset.id )
                    total += hda.dataset.get_total_size()
        return total

    @staticmethod
    def user_template_environment( user ):
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
            user_email = str( user.email )
            user_name = str( user.username )
        else:
            user = None
            user_id = 'Anonymous'
            user_email = 'Anonymous'
            user_name = 'Anonymous'
        environment = {}
        environment[ '__user__' ] = user
        environment[ '__user_id__' ] = environment[ 'userId' ] = user_id
        environment[ '__user_email__' ] = environment[ 'userEmail' ] = user_email
        environment[ '__user_name__' ] = user_name
        return environment

    @staticmethod
    def expand_user_properties( user, in_string ):
        """
        """
        environment = User.user_template_environment( user )
        return Template( in_string ).safe_substitute( environment )


class PasswordResetToken( object ):
    def __init__( self, user, token=None):
        if token:
            self.token = token
        else:
            self.token = unique_id()
        self.user = user
        self.expiration_time = galaxy.model.orm.now.now() + timedelta(hours=24)


class BaseJobMetric( object ):

    def __init__( self, plugin, metric_name, metric_value ):
        self.plugin = plugin
        self.metric_name = metric_name
        self.metric_value = metric_value


class JobMetricText( BaseJobMetric ):
    pass


class JobMetricNumeric( BaseJobMetric ):
    pass


class TaskMetricText( BaseJobMetric ):
    pass


class TaskMetricNumeric( BaseJobMetric ):
    pass


class Job( object, JobLike, Dictifiable ):
    dict_collection_visible_keys = [ 'id', 'state', 'exit_code', 'update_time', 'create_time' ]
    dict_element_visible_keys = [ 'id', 'state', 'exit_code', 'update_time', 'create_time'  ]

    """
    A job represents a request to run a tool given input datasets, tool
    parameters, and output datasets.
    """
    _numeric_metric = JobMetricNumeric
    _text_metric = JobMetricText

    states = Bunch( NEW='new',
                    RESUBMITTED='resubmitted',
                    UPLOAD='upload',
                    WAITING='waiting',
                    QUEUED='queued',
                    RUNNING='running',
                    OK='ok',
                    ERROR='error',
                    PAUSED='paused',
                    DELETED='deleted',
                    DELETED_NEW='deleted_new' )
    terminal_states = [ states.OK,
                        states.ERROR,
                        states.DELETED ]
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
    def __init__( self ):
        self.session_id = None
        self.user_id = None
        self.tool_id = None
        self.tool_version = None
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
        self._init_metrics()
        self.state_history.append( JobStateHistory( self ) )

    @property
    def finished( self ):
        states = self.states
        return self.state in [
            states.OK,
            states.ERROR,
            states.DELETED,
            states.DELETED_NEW,
        ]

    # TODO: Add accessors for members defined in SQL Alchemy for the Job table and
    # for the mapper defined to the Job table.
    def get_external_output_metadata( self ):
        """
        The external_output_metadata is currently a reference from Job to
        JobExternalOutputMetadata. It exists for a job but not a task.
        """
        return self.external_output_metadata

    def get_session_id( self ):
        return self.session_id

    def get_user_id( self ):
        return self.user_id

    def get_tool_id( self ):
        return self.tool_id

    def get_tool_version( self ):
        return self.tool_version

    def get_command_line( self ):
        return self.command_line

    def get_dependencies(self):
        return self.dependencies

    def get_param_filename( self ):
        return self.param_filename

    def get_parameters( self ):
        return self.parameters

    def get_input_datasets( self ):
        return self.input_datasets

    def get_output_datasets( self ):
        return self.output_datasets

    def get_input_library_datasets( self ):
        return self.input_library_datasets

    def get_output_library_datasets( self ):
        return self.output_library_datasets

    def get_state( self ):
        return self.state

    def get_info( self ):
        return self.info

    def get_job_runner_name( self ):
        # This differs from the Task class in that job_runner_name is
        # accessed instead of task_runner_name. Note that the field
        # runner_name is not the same thing.
        return self.job_runner_name

    def get_job_runner_external_id( self ):
        # This is different from the Task just in the member accessed:
        return self.job_runner_external_id

    def get_post_job_actions( self ):
        return self.post_job_actions

    def get_imported( self ):
        return self.imported

    def get_handler( self ):
        return self.handler

    def get_params( self ):
        return self.params

    def get_user( self ):
        # This is defined in the SQL Alchemy mapper as a relation to the User.
        return self.user

    def get_id( self ):
        # This is defined in the SQL Alchemy's Job table (and not in the model).
        return self.id

    def get_tasks( self ):
        # The tasks member is pert of a reference in the SQL Alchemy schema:
        return self.tasks

    def get_id_tag( self ):
        """
        Return a tag that can be useful in identifying a Job.
        This returns the Job's get_id
        """
        return "%s" % self.id

    def set_session_id( self, session_id ):
        self.session_id = session_id

    def set_user_id( self, user_id ):
        self.user_id = user_id

    def set_tool_id( self, tool_id ):
        self.tool_id = tool_id

    def set_tool_version( self, tool_version ):
        self.tool_version = tool_version

    def set_command_line( self, command_line ):
        self.command_line = command_line

    def set_dependencies( self, dependencies ):
        self.dependencies = dependencies

    def set_param_filename( self, param_filename ):
        self.param_filename = param_filename

    def set_parameters( self, parameters ):
        self.parameters = parameters

    def set_input_datasets( self, input_datasets ):
        self.input_datasets = input_datasets

    def set_output_datasets( self, output_datasets ):
        self.output_datasets = output_datasets

    def set_input_library_datasets( self, input_library_datasets ):
        self.input_library_datasets = input_library_datasets

    def set_output_library_datasets( self, output_library_datasets ):
        self.output_library_datasets = output_library_datasets

    def set_info( self, info ):
        self.info = info

    def set_runner_name( self, job_runner_name ):
        self.job_runner_name = job_runner_name

    def get_job( self ):
        # Added so job and task have same interface (.get_job() ) to get at
        # underlying job object.
        return self

    def set_runner_external_id( self, job_runner_external_id ):
        self.job_runner_external_id = job_runner_external_id

    def set_post_job_actions( self, post_job_actions ):
        self.post_job_actions = post_job_actions

    def set_imported( self, imported ):
        self.imported = imported

    def set_handler( self, handler ):
        self.handler = handler

    def set_params( self, params ):
        self.params = params

    def add_parameter( self, name, value ):
        self.parameters.append( JobParameter( name, value ) )

    def add_input_dataset( self, name, dataset=None, dataset_id=None ):
        assoc = JobToInputDatasetAssociation( name, dataset )
        if dataset is None and dataset_id is not None:
            assoc.dataset_id = dataset_id
        self.input_datasets.append( assoc )

    def add_output_dataset( self, name, dataset ):
        self.output_datasets.append( JobToOutputDatasetAssociation( name, dataset ) )

    def add_input_dataset_collection( self, name, dataset_collection ):
        self.input_dataset_collections.append( JobToInputDatasetCollectionAssociation( name, dataset_collection ) )

    def add_output_dataset_collection( self, name, dataset_collection_instance ):
        self.output_dataset_collection_instances.append( JobToOutputDatasetCollectionAssociation( name, dataset_collection_instance ) )

    def add_implicit_output_dataset_collection( self, name, dataset_collection ):
        self.output_dataset_collections.append( JobToImplicitOutputDatasetCollectionAssociation( name, dataset_collection ) )

    def add_input_library_dataset( self, name, dataset ):
        self.input_library_datasets.append( JobToInputLibraryDatasetAssociation( name, dataset ) )

    def add_output_library_dataset( self, name, dataset ):
        self.output_library_datasets.append( JobToOutputLibraryDatasetAssociation( name, dataset ) )

    def add_post_job_action(self, pja):
        self.post_job_actions.append( PostJobActionAssociation( pja, self ) )

    def set_state( self, state ):
        """
        Save state history
        """
        self.state = state
        self.state_history.append( JobStateHistory( self ) )

    def get_param_values( self, app, ignore_errors=False ):
        """
        Read encoded parameter values from the database and turn back into a
        dict of tool parameter values.
        """
        param_dict = self.raw_param_dict()
        tool = app.toolbox.get_tool( self.tool_id )
        param_dict = tool.params_from_strings( param_dict, app, ignore_errors=ignore_errors )
        return param_dict

    def raw_param_dict( self ):
        param_dict = dict( [ ( p.name, p.value ) for p in self.parameters ] )
        return param_dict

    def check_if_output_datasets_deleted( self ):
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

    def mark_deleted( self, track_jobs_in_database=False ):
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

    def to_dict( self, view='collection', system_details=False ):
        rval = super( Job, self ).to_dict( view=view )
        rval['tool_id'] = self.tool_id
        if system_details:
            # System level details that only admins should have.
            rval['external_id'] = self.job_runner_external_id
            rval['command_line'] = self.command_line

        if view == 'element':
            param_dict = dict( [ ( p.name, p.value ) for p in self.parameters ] )
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

    def set_final_state( self, final_state ):
        self.set_state( final_state )
        if self.workflow_invocation_step:
            self.workflow_invocation_step.update()

    def get_destination_configuration(self, config, key, default=None):
        """ Get a destination parameter that can be defaulted back
        in specified config if it needs to be applied globally.
        """
        param_unspecified = object()
        config_value = (self.destination_params or {}).get(key, param_unspecified)
        if config_value is param_unspecified:
            config_value = getattr(config, key, param_unspecified)
        if config_value is param_unspecified:
            config_value = default
        return config_value

    @property
    def seconds_since_update( self ):
        return (galaxy.model.orm.now.now() - self.update_time).total_seconds()


class Task( object, JobLike ):
    """
    A task represents a single component of a job.
    """
    _numeric_metric = TaskMetricNumeric
    _text_metric = TaskMetricText

    states = Bunch( NEW='new',
                    WAITING='waiting',
                    QUEUED='queued',
                    RUNNING='running',
                    OK='ok',
                    ERROR='error',
                    DELETED='deleted' )

    # Please include an accessor (get/set pair) for any new columns/members.
    def __init__( self, job, working_directory, prepare_files_cmd ):
        self.command_line = None
        self.parameters = []
        self.state = Task.states.NEW
        self.info = None
        self.working_directory = working_directory
        self.task_runner_name = None
        self.task_runner_external_id = None
        self.job = job
        self.stdout = ""
        self.stderr = ""
        self.exit_code = None
        self.prepare_input_files_cmd = prepare_files_cmd
        self._init_metrics()

    def get_param_values( self, app ):
        """
        Read encoded parameter values from the database and turn back into a
        dict of tool parameter values.
        """
        param_dict = dict( [ ( p.name, p.value ) for p in self.parent_job.parameters ] )
        tool = app.toolbox.get_tool( self.tool_id )
        param_dict = tool.params_from_strings( param_dict, app )
        return param_dict

    def get_id( self ):
        # This is defined in the SQL Alchemy schema:
        return self.id

    def get_id_tag( self ):
        """
        Return an id tag suitable for identifying the task.
        This combines the task's job id and the task's own id.
        """
        return "%s_%s" % ( self.job.get_id(), self.get_id() )

    def get_command_line( self ):
        return self.command_line

    def get_parameters( self ):
        return self.parameters

    def get_state( self ):
        return self.state

    def get_info( self ):
        return self.info

    def get_working_directory( self ):
        return self.working_directory

    def get_task_runner_name( self ):
        return self.task_runner_name

    def get_task_runner_external_id( self ):
        return self.task_runner_external_id

    def get_job( self ):
        return self.job

    def get_stdout( self ):
        return self.stdout

    def get_stderr( self ):
        return self.stderr

    def get_prepare_input_files_cmd( self ):
        return self.prepare_input_files_cmd

    # The following accessors are for members that are in the Job class but
    # not in the Task class. So they can either refer to the parent Job
    # or return None, depending on whether Tasks need to point to the parent
    # (e.g., for a session) or never use the member (e.g., external output
    # metdata). These can be filled in as needed.
    def get_external_output_metadata( self ):
        """
        The external_output_metadata is currently a backref to
        JobExternalOutputMetadata. It exists for a job but not a task,
        and when a task is cancelled its corresponding parent Job will
        be cancelled. So None is returned now, but that could be changed
        to self.get_job().get_external_output_metadata().
        """
        return None

    def get_job_runner_name( self ):
        """
        Since runners currently access Tasks the same way they access Jobs,
        this method just refers to *this* instance's runner.
        """
        return self.task_runner_name

    def get_job_runner_external_id( self ):
        """
        Runners will use the same methods to get information about the Task
        class as they will about the Job class, so this method just returns
        the task's external id.
        """
        # TODO: Merge into get_runner_external_id.
        return self.task_runner_external_id

    def get_session_id( self ):
        # The Job's galaxy session is equal to the Job's session, so the
        # Job's session is the same as the Task's session.
        return self.get_job().get_session_id()

    def set_id( self, id ):
        # This is defined in the SQL Alchemy's mapper and not here.
        # This should never be called.
        self.id = id

    def set_command_line( self, command_line ):
        self.command_line = command_line

    def set_parameters( self, parameters ):
        self.parameters = parameters

    def set_state( self, state ):
        self.state = state

    def set_info( self, info ):
        self.info = info

    def set_working_directory( self, working_directory ):
        self.working_directory = working_directory

    def set_task_runner_name( self, task_runner_name ):
        self.task_runner_name = task_runner_name

    def set_job_runner_external_id( self, task_runner_external_id ):
        # This method is available for runners that do not want/need to
        # differentiate between the kinds of Runnable things (Jobs and Tasks)
        # that they're using.
        log.debug( "Task %d: Set external id to %s"
                   % ( self.id, task_runner_external_id ) )
        self.task_runner_external_id = task_runner_external_id

    def set_task_runner_external_id( self, task_runner_external_id ):
        self.task_runner_external_id = task_runner_external_id

    def set_job( self, job ):
        self.job = job

    def set_stdout( self, stdout ):
        self.stdout = stdout

    def set_stderr( self, stderr ):
        self.stderr = stderr

    def set_prepare_input_files_cmd( self, prepare_input_files_cmd ):
        self.prepare_input_files_cmd = prepare_input_files_cmd


class JobParameter( object ):
    def __init__( self, name, value ):
        self.name = name
        self.value = value


class JobToInputDatasetAssociation( object ):
    def __init__( self, name, dataset ):
        self.name = name
        self.dataset = dataset


class JobToOutputDatasetAssociation( object ):
    def __init__( self, name, dataset ):
        self.name = name
        self.dataset = dataset


class JobToInputDatasetCollectionAssociation( object ):
    def __init__( self, name, dataset_collection ):
        self.name = name
        self.dataset_collection = dataset_collection


# Many jobs may map to one HistoryDatasetCollection using these for a given
# tool output (if mapping over an input collection).
class JobToOutputDatasetCollectionAssociation( object ):
    def __init__( self, name, dataset_collection_instance ):
        self.name = name
        self.dataset_collection_instance = dataset_collection_instance


# A DatasetCollection will be mapped to at most one job per tool output
# using these. (You can think of many of these models as going into the
# creation of a JobToOutputDatasetCollectionAssociation.)
class JobToImplicitOutputDatasetCollectionAssociation( object ):
    def __init__( self, name, dataset_collection ):
        self.name = name
        self.dataset_collection = dataset_collection


class JobToInputLibraryDatasetAssociation( object ):
    def __init__( self, name, dataset ):
        self.name = name
        self.dataset = dataset


class JobToOutputLibraryDatasetAssociation( object ):
    def __init__( self, name, dataset ):
        self.name = name
        self.dataset = dataset


class JobStateHistory( object ):
    def __init__( self, job ):
        self.job = job
        self.state = job.state
        self.info = job.info


class ImplicitlyCreatedDatasetCollectionInput( object ):
    def __init__( self, name, input_dataset_collection ):
        self.name = name
        self.input_dataset_collection = input_dataset_collection


class PostJobAction( object ):
    def __init__( self, action_type, workflow_step, output_name=None, action_arguments=None):
        self.action_type = action_type
        self.output_name = output_name
        self.action_arguments = action_arguments
        self.workflow_step = workflow_step


class PostJobActionAssociation( object ):
    def __init__(self, pja, job=None, job_id=None ):
        if job is not None:
            self.job = job
        elif job_id is not None:
            self.job_id = job_id
        else:
            raise Exception("PostJobActionAssociation must be created with a job or a job_id.")
        self.post_job_action = pja


class JobExternalOutputMetadata( object ):
    def __init__( self, job=None, dataset=None ):
        self.job = job
        if isinstance( dataset, galaxy.model.HistoryDatasetAssociation ):
            self.history_dataset_association = dataset
        elif isinstance( dataset, galaxy.model.LibraryDatasetDatasetAssociation ):
            self.library_dataset_dataset_association = dataset

    @property
    def dataset( self ):
        if self.history_dataset_association:
            return self.history_dataset_association
        elif self.library_dataset_dataset_association:
            return self.library_dataset_dataset_association
        return None


class JobExportHistoryArchive( object ):
    def __init__( self, job=None, history=None, dataset=None, compressed=False,
                  history_attrs_filename=None, datasets_attrs_filename=None,
                  jobs_attrs_filename=None ):
        self.job = job
        self.history = history
        self.dataset = dataset
        self.compressed = compressed
        self.history_attrs_filename = history_attrs_filename
        self.datasets_attrs_filename = datasets_attrs_filename
        self.jobs_attrs_filename = jobs_attrs_filename

    @property
    def up_to_date( self ):
        """ Return False, if a new export should be generated for corresponding
        history.
        """
        job = self.job
        return job.state not in [ Job.states.ERROR, Job.states.DELETED ] \
            and job.update_time > self.history.update_time

    @property
    def ready( self ):
        return self.job.state == Job.states.OK

    @property
    def preparing( self ):
        return self.job.state in [ Job.states.RUNNING, Job.states.QUEUED, Job.states.WAITING ]

    @property
    def export_name( self ):
        # Stream archive.
        hname = ready_name_for_url( self.history.name )
        hname = "Galaxy-History-%s.tar" % ( hname )
        if self.compressed:
            hname += ".gz"
        return hname


class JobImportHistoryArchive( object ):
    def __init__( self, job=None, history=None, archive_dir=None ):
        self.job = job
        self.history = history
        self.archive_dir = archive_dir


class GenomeIndexToolData( object ):
    def __init__( self, job=None, params=None, dataset=None, deferred_job=None,
                  transfer_job=None, fasta_path=None, created_time=None, modified_time=None,
                  dbkey=None, user=None, indexer=None ):
        self.job = job
        self.dataset = dataset
        self.fasta_path = fasta_path
        self.user = user
        self.indexer = indexer
        self.created_time = created_time
        self.modified_time = modified_time
        self.deferred = deferred_job
        self.transfer = transfer_job


class DeferredJob( object ):
    states = Bunch( NEW='new',
                    WAITING='waiting',
                    QUEUED='queued',
                    RUNNING='running',
                    OK='ok',
                    ERROR='error' )

    def __init__( self, state=None, plugin=None, params=None ):
        self.state = state
        self.plugin = plugin
        self.params = params

    def get_check_interval( self ):
        if not hasattr( self, '_check_interval' ):
            self._check_interval = None
        return self._check_interval

    def set_check_interval( self, seconds ):
        self._check_interval = seconds
    check_interval = property( get_check_interval, set_check_interval )

    def get_last_check( self ):
        if not hasattr( self, '_last_check' ):
            self._last_check = 0
        return self._last_check

    def set_last_check( self, seconds ):
        try:
            self._last_check = int( seconds )
        except:
            self._last_check = time.time()
    last_check = property( get_last_check, set_last_check )

    @property
    def is_check_time( self ):
        if self.check_interval is None:
            return True
        elif ( int( time.time() ) - self.last_check ) > self.check_interval:
            return True
        else:
            return False


class Group( object, Dictifiable  ):
    dict_collection_visible_keys = ( 'id', 'name' )
    dict_element_visible_keys = ( 'id', 'name' )

    def __init__( self, name=None ):
        self.name = name
        self.deleted = False


class UserGroupAssociation( object ):
    def __init__( self, user, group ):
        self.user = user
        self.group = group


def is_hda(d):
    return isinstance( d, HistoryDatasetAssociation )


class History( object, Dictifiable, UsesAnnotations, HasName ):

    dict_collection_visible_keys = ( 'id', 'name', 'published', 'deleted' )
    dict_element_visible_keys = ( 'id', 'name', 'genome_build', 'deleted', 'purged', 'update_time',
                                  'published', 'importable', 'slug', 'empty' )
    default_name = 'Unnamed history'

    def __init__( self, id=None, name=None, user=None ):
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
    def empty( self ):
        return self.hid_counter == 1

    def _next_hid( self, n=1 ):
        # this is overriden in mapping.py db_next_hid() method
        if len( self.datasets ) == 0:
            return n
        else:
            last_hid = 0
            for dataset in self.datasets:
                if dataset.hid > last_hid:
                    last_hid = dataset.hid
            return last_hid + n

    def add_galaxy_session( self, galaxy_session, association=None ):
        if association is None:
            self.galaxy_sessions.append( GalaxySessionToHistoryAssociation( galaxy_session, self ) )
        else:
            self.galaxy_sessions.append( association )

    def add_dataset( self, dataset, parent_id=None, genome_build=None, set_hid=True, quota=True ):
        if isinstance( dataset, Dataset ):
            dataset = HistoryDatasetAssociation(dataset=dataset)
            object_session( self ).add( dataset )
            object_session( self ).flush()
        elif not isinstance( dataset, HistoryDatasetAssociation ):
            raise TypeError( "You can only add Dataset and HistoryDatasetAssociation instances to a history" +
                             " ( you tried to add %s )." % str( dataset ) )
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

    def add_datasets( self, sa_session, datasets, parent_id=None, genome_build=None, set_hid=True, quota=True, flush=False ):
        """ Optimized version of add_dataset above that minimizes database
        interactions when adding many datasets to history at once.
        """
        all_hdas = all( is_hda(_) for _ in datasets )
        optimize = len( datasets) > 1 and parent_id is None and all_hdas and set_hid
        if optimize:
            self.__add_datasets_optimized( datasets, genome_build=genome_build )
            if quota and self.user:
                disk_usage = sum([d.get_total_size() for d in datasets])
                self.user.adjust_total_disk_usage(disk_usage)

            sa_session.add_all( datasets )
            if flush:
                sa_session.flush()
        else:
            for dataset in datasets:
                self.add_dataset( dataset, parent_id=parent_id, genome_build=genome_build, set_hid=set_hid, quota=quota )
                sa_session.add( dataset )
                if flush:
                    sa_session.flush()

    def __add_datasets_optimized( self, datasets, genome_build=None ):
        """ Optimized version of add_dataset above that minimizes database
        interactions when adding many datasets to history at once under
        certain circumstances.
        """
        n = len( datasets )

        base_hid = self._next_hid( n=n )
        set_genome = genome_build not in [None, '?']
        for i, dataset in enumerate( datasets ):
            dataset.hid = base_hid + i
            dataset.history = self
            if set_genome:
                self.genome_build = genome_build
        for dataset in datasets:
            dataset.history_id = self.id
        return datasets

    def add_dataset_collection( self, history_dataset_collection, set_hid=True ):
        if set_hid:
            history_dataset_collection.hid = self._next_hid()
        history_dataset_collection.history = self
        # TODO: quota?
        self.dataset_collections.append( history_dataset_collection )
        return history_dataset_collection

    def copy( self, name=None, target_user=None, activatable=False, all_datasets=False ):
        """
        Return a copy of this history using the given `name` and `target_user`.
        If `activatable`, copy only non-deleted datasets. If `all_datasets`, copy
        non-deleted, deleted, and purged datasets.
        """
        name = name or self.name
        applies_to_quota = target_user != self.user

        # Create new history.
        new_history = History( name=name, user=target_user )
        db_session = object_session( self )
        db_session.add( new_history )
        db_session.flush()

        # copy history tags and annotations (if copying user is not anonymous)
        if target_user:
            self.copy_item_annotation( db_session, self.user, self, target_user, new_history )
            new_history.copy_tags_from(target_user=target_user, source_history=self)

        # Copy HDAs.
        if activatable:
            hdas = self.activatable_datasets
        elif all_datasets:
            hdas = self.datasets
        else:
            hdas = self.active_datasets
        for hda in hdas:
            # Copy HDA.
            new_hda = hda.copy( copy_children=True )
            new_history.add_dataset( new_hda, set_hid=False, quota=applies_to_quota )
            db_session.add( new_hda )
            db_session.flush()

            if target_user:
                new_hda.copy_item_annotation( db_session, self.user, hda, target_user, new_hda )
                new_hda.copy_tags_from( target_user, hda )

        # Copy history dataset collections
        if all_datasets:
            hdcas = self.dataset_collections
        else:
            hdcas = self.active_dataset_collections
        for hdca in hdcas:
            new_hdca = hdca.copy()
            new_history.add_dataset_collection( new_hdca, set_hid=False )
            db_session.add( new_hdca )
            db_session.flush()

            if target_user:
                new_hdca.copy_item_annotation( db_session, self.user, hdca, target_user, new_hdca )

        new_history.hid_counter = self.hid_counter
        db_session.add( new_history )
        db_session.flush()

        return new_history

    @property
    def activatable_datasets( self ):
        # This needs to be a list
        return [ hda for hda in self.datasets if not hda.dataset.deleted ]

    def to_dict( self, view='collection', value_mapper=None ):

        # Get basic value.
        rval = super( History, self ).to_dict( view=view, value_mapper=value_mapper )

        # Add tags.
        tags_str_list = []
        for tag in self.tags:
            tag_str = tag.user_tname
            if tag.value is not None:
                tag_str += ":" + tag.user_value
            tags_str_list.append( tag_str )
        rval[ 'tags' ] = tags_str_list

        if view == 'element':
            rval[ 'size' ] = int( self.disk_size )

        return rval

    @property
    def latest_export( self ):
        exports = self.exports
        return exports and exports[ 0 ]

    def unhide_datasets( self ):
        for dataset in self.datasets:
            dataset.mark_unhidden()

    def resume_paused_jobs( self ):
        for dataset in self.datasets:
            job = dataset.creating_job
            if job is not None and job.state == Job.states.PAUSED:
                job.set_state(Job.states.NEW)

    @hybrid.hybrid_property
    def disk_size( self ):
        """
        Return the size in bytes of this history by summing the 'total_size's of
        all non-purged, unique datasets within it.
        """
        # non-.expression part of hybrid.hybrid_property: called when an instance is the namespace (not the class)
        db_session = object_session( self )
        rval = db_session.query(
            func.sum( db_session.query( HistoryDatasetAssociation.dataset_id, Dataset.total_size ).join( Dataset )
                    .filter( HistoryDatasetAssociation.table.c.history_id == self.id )
                    .filter( HistoryDatasetAssociation.purged != true() )
                    .filter( Dataset.purged != true() )
                    # unique datasets only
                    .distinct().subquery().c.total_size ) ).first()[0]
        if rval is None:
            rval = 0
        return rval

    @disk_size.expression
    def disk_size( cls ):
        """
        Return a query scalar that will get any history's size in bytes by summing
        the 'total_size's of all non-purged, unique datasets within it.
        """
        # .expression acts as a column_property and should return a scalar
        # first, get the distinct datasets within a history that are not purged
        hda_to_dataset_join = join( HistoryDatasetAssociation, Dataset,
            HistoryDatasetAssociation.table.c.dataset_id == Dataset.table.c.id )
        distinct_datasets = (
            select([
                # use labels here to better accrss from the query above
                HistoryDatasetAssociation.table.c.history_id.label( 'history_id' ),
                Dataset.total_size.label( 'dataset_size' ),
                Dataset.id.label( 'dataset_id' )
            ])
            .where( HistoryDatasetAssociation.table.c.purged != true() )
            .where( Dataset.table.c.purged != true() )
            .select_from( hda_to_dataset_join )
            # TODO: slow (in general) but most probably here - index total_size for easier sorting/distinct?
            .distinct()
        )
        # postgres needs an alias on FROM
        distinct_datasets_alias = aliased( distinct_datasets, name="datasets" )
        # then, bind as property of history using the cls.id
        size_query = (
            select([
                func.coalesce( func.sum( distinct_datasets_alias.c.dataset_size ), 0 )
            ])
            .select_from( distinct_datasets_alias )
            .where( distinct_datasets_alias.c.history_id == cls.id )
        )
        # label creates a scalar
        return size_query.label( 'disk_size' )

    @property
    def disk_nice_size( self ):
        """Returns human readable size of history on disk."""
        return galaxy.util.nice_size( self.disk_size )

    @property
    def active_datasets_children_and_roles( self ):
        if not hasattr(self, '_active_datasets_children_and_roles'):
            db_session = object_session( self )
            query = ( db_session.query( HistoryDatasetAssociation )
                      .filter( HistoryDatasetAssociation.table.c.history_id == self.id )
                      .filter( not_( HistoryDatasetAssociation.deleted ) )
                      .order_by( HistoryDatasetAssociation.table.c.hid.asc() )
                      .options( joinedload("children"),
                                joinedload("dataset"),
                                joinedload("dataset.actions"),
                                joinedload("dataset.actions.role"),
                                ))
            self._active_datasets_children_and_roles = query.all()
        return self._active_datasets_children_and_roles

    @property
    def active_contents( self ):
        """ Return all active contents ordered by hid.
        """
        return self.contents_iter( types=[ "dataset", "dataset_collection" ], deleted=False, visible=True )

    def contents_iter( self, **kwds ):
        """
        Fetch filtered list of contents of history.
        """
        default_contents_types = [
            'dataset',
        ]
        types = kwds.get('types', default_contents_types)
        iters = []
        if 'dataset' in types:
            iters.append( self.__dataset_contents_iter( **kwds ) )
        if 'dataset_collection' in types:
            iters.append( self.__collection_contents_iter( **kwds ) )
        return galaxy.util.merge_sorted_iterables( operator.attrgetter( "hid" ), *iters )

    def __dataset_contents_iter(self, **kwds):
        return self.__filter_contents( HistoryDatasetAssociation, **kwds )

    def __filter_contents( self, content_class, **kwds ):
        db_session = object_session( self )
        assert db_session is not None
        query = db_session.query( content_class ).filter( content_class.table.c.history_id == self.id )
        query = query.order_by( content_class.table.c.hid.asc() )
        deleted = galaxy.util.string_as_bool_or_none( kwds.get( 'deleted', None ) )
        if deleted is not None:
            query = query.filter( content_class.deleted == deleted )
        visible = galaxy.util.string_as_bool_or_none( kwds.get( 'visible', None ) )
        if visible is not None:
            query = query.filter( content_class.visible == visible )
        if 'ids' in kwds:
            ids = kwds['ids']
            max_in_filter_length = kwds.get('max_in_filter_length', MAX_IN_FILTER_LENGTH)
            if len(ids) < max_in_filter_length:
                query = query.filter( content_class.id.in_(ids) )
            else:
                query = (content for content in query if content.id in ids)
        return query

    def __collection_contents_iter( self, **kwds ):
        return self.__filter_contents( HistoryDatasetCollectionAssociation, **kwds )

    def copy_tags_from(self, target_user, source_history):
        for src_shta in source_history.tags:
            new_shta = src_shta.copy()
            new_shta.user = target_user
            self.tags.append(new_shta)


class HistoryUserShareAssociation( object ):
    def __init__( self ):
        self.history = None
        self.user = None


class UserRoleAssociation( object ):
    def __init__( self, user, role ):
        self.user = user
        self.role = role


class GroupRoleAssociation( object ):
    def __init__( self, group, role ):
        self.group = group
        self.role = role


class Role( object, Dictifiable ):
    dict_collection_visible_keys = ( 'id', 'name' )
    dict_element_visible_keys = ( 'id', 'name', 'description', 'type' )
    private_id = None
    types = Bunch(
        PRIVATE='private',
        SYSTEM='system',
        USER='user',
        ADMIN='admin',
        SHARING='sharing'
    )

    def __init__( self, name="", description="", type="system", deleted=False ):
        self.name = name
        self.description = description
        self.type = type
        self.deleted = deleted


class UserQuotaAssociation( object, Dictifiable ):
    dict_element_visible_keys = ( 'user', )

    def __init__( self, user, quota ):
        self.user = user
        self.quota = quota


class GroupQuotaAssociation( object, Dictifiable ):
    dict_element_visible_keys = ( 'group', )

    def __init__( self, group, quota ):
        self.group = group
        self.quota = quota


class Quota( object, Dictifiable ):
    dict_collection_visible_keys = ( 'id', 'name' )
    dict_element_visible_keys = ( 'id', 'name', 'description', 'bytes', 'operation', 'display_amount', 'default', 'users', 'groups' )
    valid_operations = ( '+', '-', '=' )

    def __init__( self, name="", description="", amount=0, operation="=" ):
        self.name = name
        self.description = description
        if amount is None:
            self.bytes = -1
        else:
            self.bytes = amount
        self.operation = operation

    def get_amount( self ):
        if self.bytes == -1:
            return None
        return self.bytes

    def set_amount( self, amount ):
        if amount is None:
            self.bytes = -1
        else:
            self.bytes = amount
    amount = property( get_amount, set_amount )

    @property
    def display_amount( self ):
        if self.bytes == -1:
            return "unlimited"
        else:
            return galaxy.util.nice_size( self.bytes )


class DefaultQuotaAssociation( Quota, Dictifiable ):
    dict_element_visible_keys = ( 'type', )
    types = Bunch(
        UNREGISTERED='unregistered',
        REGISTERED='registered'
    )

    def __init__( self, type, quota ):
        assert type in self.types.__dict__.values(), 'Invalid type'
        self.type = type
        self.quota = quota


class DatasetPermissions( object ):
    def __init__( self, action, dataset, role=None, role_id=None ):
        self.action = action
        self.dataset = dataset
        if role is not None:
            self.role = role
        else:
            self.role_id = role_id


class LibraryPermissions( object ):
    def __init__( self, action, library_item, role ):
        self.action = action
        if isinstance( library_item, Library ):
            self.library = library_item
        else:
            raise Exception( "Invalid Library specified: %s" % library_item.__class__.__name__ )
        self.role = role


class LibraryFolderPermissions( object ):
    def __init__( self, action, library_item, role ):
        self.action = action
        if isinstance( library_item, LibraryFolder ):
            self.folder = library_item
        else:
            raise Exception( "Invalid LibraryFolder specified: %s" % library_item.__class__.__name__ )
        self.role = role


class LibraryDatasetPermissions( object ):
    def __init__( self, action, library_item, role ):
        self.action = action
        if isinstance( library_item, LibraryDataset ):
            self.library_dataset = library_item
        else:
            raise Exception( "Invalid LibraryDataset specified: %s" % library_item.__class__.__name__ )
        self.role = role


class LibraryDatasetDatasetAssociationPermissions( object ):
    def __init__( self, action, library_item, role ):
        self.action = action
        if isinstance( library_item, LibraryDatasetDatasetAssociation ):
            self.library_dataset_dataset_association = library_item
        else:
            raise Exception( "Invalid LibraryDatasetDatasetAssociation specified: %s" % library_item.__class__.__name__ )
        self.role = role


class DefaultUserPermissions( object ):
    def __init__( self, user, action, role ):
        self.user = user
        self.action = action
        self.role = role


class DefaultHistoryPermissions( object ):
    def __init__( self, history, action, role ):
        self.history = history
        self.action = action
        self.role = role


class StorableObject( object ):

    def __init__( self, id, **kwargs):
        self.id = id


class Dataset( StorableObject ):
    states = Bunch( NEW='new',
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
    ready_states = tuple( set( states.__dict__.values() ) - set( non_ready_states ) )
    valid_input_states = tuple(
        set( states.__dict__.values() ) - set( [states.ERROR, states.DISCARDED] )
    )
    terminal_states = (
        states.OK,
        states.EMPTY,
        states.ERROR,
        states.DISCARDED,
        states.FAILED_METADATA,
    )

    conversion_messages = Bunch( PENDING="pending",
                                 NO_DATA="no data",
                                 NO_CHROMOSOME="no chromosome",
                                 NO_CONVERTER="no converter",
                                 NO_TOOL="no tool",
                                 DATA="data",
                                 ERROR="error",
                                 OK="ok" )

    permitted_actions = get_permitted_actions( filter='DATASET' )
    file_path = "/tmp/"
    object_store = None  # This get initialized in mapping.py (method init) by app.py
    engine = None

    def __init__( self, id=None, state=None, external_filename=None, extra_files_path=None, file_size=None, purgable=True, uuid=None ):
        super(Dataset, self).__init__(id=id)
        self.state = state
        self.deleted = False
        self.purged = False
        self.purgable = purgable
        self.external_filename = external_filename
        self.external_extra_files_path = None
        self._extra_files_path = extra_files_path
        self.file_size = file_size
        if uuid is None:
            self.uuid = uuid4()
        else:
            self.uuid = UUID(str(uuid))

    def in_ready_state( self ):
        return self.state in self.ready_states

    def get_file_name( self ):
        if not self.external_filename:
            assert self.id is not None, "ID must be set before filename used (commit the object)"
            assert self.object_store is not None, "Object Store has not been initialized for dataset %s" % self.id
            filename = self.object_store.get_filename( self )
            return filename
        else:
            filename = self.external_filename
        # Make filename absolute
        return os.path.abspath( filename )

    def set_file_name( self, filename ):
        if not filename:
            self.external_filename = None
        else:
            self.external_filename = filename
    file_name = property( get_file_name, set_file_name )

    def get_extra_files_path( self ):
        # Unlike get_file_name - external_extra_files_path is not backed by an
        # actual database column so if SA instantiates this object - the
        # attribute won't exist yet.
        if not getattr( self, "external_extra_files_path", None ):
            return self.object_store.get_filename( self, dir_only=True, extra_dir=self._extra_files_path or "dataset_%d_files" % self.id )
        else:
            return os.path.abspath( self.external_extra_files_path )

    def set_extra_files_path( self, extra_files_path ):
        if not extra_files_path:
            self.external_extra_files_path = None
        else:
            self.external_extra_files_path = extra_files_path
    extra_files_path = property( get_extra_files_path, set_extra_files_path)

    def _calculate_size( self ):
        if self.external_filename:
            try:
                return os.path.getsize(self.external_filename)
            except OSError:
                return 0
        else:
            return self.object_store.size(self)

    def get_size( self, nice_size=False ):
        """Returns the size of the data on disk"""
        if self.file_size:
            if nice_size:
                return galaxy.util.nice_size( self.file_size )
            else:
                return self.file_size
        else:
            if nice_size:
                return galaxy.util.nice_size( self._calculate_size() )
            else:
                return self._calculate_size()

    def set_size( self ):
        """Returns the size of the data on disk"""
        if not self.file_size:
            self.file_size = self._calculate_size()

    def get_total_size( self ):
        if self.total_size is not None:
            return self.total_size
        # for backwards compatibility, set if unset
        self.set_total_size()
        db_session = object_session( self )
        db_session.flush()
        return self.total_size

    def set_total_size( self ):
        if self.file_size is None:
            self.set_size()
        self.total_size = self.file_size or 0
        if self.object_store.exists(self, extra_dir=self._extra_files_path or "dataset_%d_files" % self.id, dir_only=True):
            for root, dirs, files in os.walk( self.extra_files_path ):
                self.total_size += sum( [ os.path.getsize( os.path.join( root, file ) ) for file in files if os.path.exists( os.path.join( root, file ) ) ] )

    def has_data( self ):
        """Detects whether there is any data"""
        return self.get_size() > 0

    def mark_deleted( self, include_children=True ):
        self.deleted = True

    def is_multi_byte( self ):
        if not self.has_data():
            return False
        try:
            return is_multi_byte( codecs.open( self.file_name, 'r', 'utf-8' ).read( 100 ) )
        except UnicodeDecodeError:
            return False
    # FIXME: sqlalchemy will replace this

    def _delete(self):
        """Remove the file that corresponds to this data"""
        self.object_store.delete(self)

    @property
    def user_can_purge( self ):
        return self.purged is False \
            and not bool( self.library_associations ) \
            and len( self.history_associations ) == len( self.purged_history_associations )

    def full_delete( self ):
        """Remove the file and extra files, marks deleted and purged"""
        # os.unlink( self.file_name )
        self.object_store.delete(self)
        if self.object_store.exists(self, extra_dir=self._extra_files_path or "dataset_%d_files" % self.id, dir_only=True):
            self.object_store.delete(self, entire_dir=True, extra_dir=self._extra_files_path or "dataset_%d_files" % self.id, dir_only=True)
        # if os.path.exists( self.extra_files_path ):
        #     shutil.rmtree( self.extra_files_path )
        # TODO: purge metadata files
        self.deleted = True
        self.purged = True

    def get_access_roles( self, trans ):
        roles = []
        for dp in self.actions:
            if dp.action == trans.app.security_agent.permitted_actions.DATASET_ACCESS.action:
                roles.append( dp.role )
        return roles

    def get_manage_permissions_roles( self, trans ):
        roles = []
        for dp in self.actions:
            if dp.action == trans.app.security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS.action:
                roles.append( dp.role )
        return roles

    def has_manage_permissions_roles( self, trans ):
        for dp in self.actions:
            if dp.action == trans.app.security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS.action:
                return True
        return False


class DatasetInstance( object ):
    """A base class for all 'dataset instances', HDAs, LDAs, etc"""
    states = Dataset.states
    conversion_messages = Dataset.conversion_messages
    permitted_actions = Dataset.permitted_actions

    def __init__( self, id=None, hid=None, name=None, info=None, blurb=None, peek=None, tool_version=None, extension=None,
                  dbkey=None, metadata=None, history=None, dataset=None, deleted=False, designation=None,
                  parent_id=None, validation_errors=None, visible=True, create_dataset=False, sa_session=None,
                  extended_metadata=None, flush=True ):
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
            self.dbkey = dbkey
        self.deleted = deleted
        self.visible = visible
        # Relationships
        if not dataset and create_dataset:
            # Had to pass the sqlalchemy session in order to create a new dataset
            dataset = Dataset( state=Dataset.states.NEW )
            if flush:
                sa_session.add( dataset )
                sa_session.flush()
        self.dataset = dataset
        self.parent_id = parent_id
        self.validation_errors = validation_errors

    @property
    def ext( self ):
        return self.extension

    def get_dataset_state( self ):
        # self._state is currently only used when setting metadata externally
        # leave setting the state as-is, we'll currently handle this specially in the external metadata code
        if self._state:
            return self._state
        return self.dataset.state

    def raw_set_dataset_state( self, state ):
        if state != self.dataset.state:
            self.dataset.state = state
            return True
        else:
            return False

    def set_dataset_state( self, state ):
        if self.raw_set_dataset_state( state ):
            object_session( self ).add( self.dataset )
            object_session( self ).flush()  # flush here, because hda.flush() won't flush the Dataset object
    state = property( get_dataset_state, set_dataset_state )

    def get_file_name( self ):
        return self.dataset.get_file_name()

    def set_file_name(self, filename):
        return self.dataset.set_file_name( filename )
    file_name = property( get_file_name, set_file_name )

    @property
    def extra_files_path( self ):
        return self.dataset.extra_files_path

    @property
    def datatype( self ):
        return _get_datatypes_registry().get_datatype_by_extension( self.extension )

    def get_metadata( self ):
        # using weakref to store parent (to prevent circ ref),
        #   does a Session.clear() cause parent to be invalidated, while still copying over this non-database attribute?
        if not hasattr( self, '_metadata_collection' ) or self._metadata_collection.parent != self:
            self._metadata_collection = galaxy.model.metadata.MetadataCollection( self )
        return self._metadata_collection

    def set_metadata( self, bunch ):
        # Needs to accept a MetadataCollection, a bunch, or a dict
        self._metadata = self.metadata.make_dict_copy( bunch )
    metadata = property( get_metadata, set_metadata )
    # This provide backwards compatibility with using the old dbkey
    # field in the database.  That field now maps to "old_dbkey" (see mapping.py).

    def get_dbkey( self ):
        dbkey = self.metadata.dbkey
        if not isinstance(dbkey, list):
            dbkey = [dbkey]
        if dbkey in [[None], []]:
            return "?"
        return dbkey[0]

    def set_dbkey( self, value ):
        if "dbkey" in self.datatype.metadata_spec:
            if not isinstance(value, list):
                self.metadata.dbkey = [value]
            else:
                self.metadata.dbkey = value
    dbkey = property( get_dbkey, set_dbkey )

    def change_datatype( self, new_ext ):
        self.clear_associated_files()
        _get_datatypes_registry().change_datatype( self, new_ext )

    def get_size( self, nice_size=False ):
        """Returns the size of the data on disk"""
        if nice_size:
            return galaxy.util.nice_size( self.dataset.get_size() )
        return self.dataset.get_size()

    def set_size( self ):
        """Returns the size of the data on disk"""
        return self.dataset.set_size()

    def get_total_size( self ):
        return self.dataset.get_total_size()

    def set_total_size( self ):
        return self.dataset.set_total_size()

    def has_data( self ):
        """Detects whether there is any data"""
        return self.dataset.has_data()

    def get_raw_data( self ):
        """Returns the full data. To stream it open the file_name and read/write as needed"""
        return self.datatype.get_raw_data( self )

    def write_from_stream( self, stream ):
        """Writes data from a stream"""
        self.datatype.write_from_stream(self, stream)

    def set_raw_data( self, data ):
        """Saves the data on the disc"""
        self.datatype.set_raw_data(self, data)

    def get_mime( self ):
        """Returns the mime type of the data"""
        try:
            return _get_datatypes_registry().get_mimetype_by_extension( self.extension.lower() )
        except AttributeError:
            # extension is None
            return 'data'

    def is_multi_byte( self ):
        """Data consists of multi-byte characters"""
        return self.dataset.is_multi_byte()

    def set_peek( self, is_multi_byte=False ):
        return self.datatype.set_peek( self, is_multi_byte=is_multi_byte )

    def init_meta( self, copy_from=None ):
        return self.datatype.init_meta( self, copy_from=copy_from )

    def set_meta( self, **kwd ):
        self.clear_associated_files( metadata_safe=True )
        return self.datatype.set_meta( self, **kwd )

    def missing_meta( self, **kwd ):
        return self.datatype.missing_meta( self, **kwd )

    def as_display_type( self, type, **kwd ):
        return self.datatype.as_display_type( self, type, **kwd )

    def display_peek( self ):
        return self.datatype.display_peek( self )

    def display_name( self ):
        return self.datatype.display_name( self )

    def display_info( self ):
        return self.datatype.display_info( self )

    def get_converted_files_by_type( self, file_type ):
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
        return dict([ (dep, self.get_converted_dataset(trans, dep)) for dep in depends_list ])

    def get_converted_dataset(self, trans, target_ext, target_context=None, history=None):
        """
        Return converted dataset(s) if they exist, along with a dict of dependencies.
        If not converted yet, do so and return None (the first time). If unconvertible, raise exception.
        """
        # See if we can convert the dataset
        if target_ext not in self.get_converter_types():
            raise NoConverterException("Conversion from '%s' to '%s' not possible" % (self.extension, target_ext) )
        deps = {}
        # List of string of dependencies
        try:
            depends_list = trans.app.datatypes_registry.converter_deps[self.extension][target_ext]
        except KeyError:
            depends_list = []
        # See if converted dataset already exists, either in metadata in conversions.
        converted_dataset = self.get_metadata_dataset( target_ext )
        if converted_dataset:
            return converted_dataset
        converted_dataset = self.get_converted_files_by_type( target_ext )
        if converted_dataset:
            return converted_dataset
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
        new_dataset = next(iter(self.datatype.convert_dataset( trans, self, target_ext, return_output=True, visible=False, deps=deps, target_context=target_context, history=history ).values()))
        new_dataset.name = self.name
        self.copy_attributes( new_dataset )
        assoc = ImplicitlyConvertedDatasetAssociation( parent=self, file_type=target_ext, dataset=new_dataset, metadata_safe=False )
        session = trans.sa_session
        session.add( new_dataset )
        session.add( assoc )
        session.flush()
        return new_dataset

    def copy_attributes( self, new_dataset ):
        """
        Copies attributes to a new datasets, used for implicit conversions
        """
        pass

    def get_metadata_dataset( self, dataset_ext ):
        """
        Returns an HDA that points to a metadata file which contains a
        converted data with the requested extension.
        """
        for name, value in self.metadata.items():
            # HACK: MetadataFile objects do not have a type/ext, so need to use metadata name
            # to determine type.
            if dataset_ext == 'bai' and name == 'bam_index' and isinstance( value, MetadataFile ):
                # HACK: MetadataFile objects cannot be used by tools, so return
                # a fake HDA that points to metadata file.
                fake_dataset = Dataset( state=Dataset.states.OK, external_filename=value.file_name )
                fake_hda = HistoryDatasetAssociation( dataset=fake_dataset )
                return fake_hda

    def clear_associated_files( self, metadata_safe=False, purge=False ):
        raise Exception( "Unimplemented" )

    def get_child_by_designation(self, designation):
        for child in self.children:
            if child.designation == designation:
                return child
        return None

    def get_converter_types(self):
        return self.datatype.get_converter_types( self, _get_datatypes_registry() )

    def can_convert_to(self, format):
        return format in self.get_converter_types()

    def find_conversion_destination( self, accepted_formats, **kwd ):
        """Returns ( target_ext, existing converted dataset )"""
        return self.datatype.find_conversion_destination( self, accepted_formats, _get_datatypes_registry(), **kwd )

    def add_validation_error( self, validation_error ):
        self.validation_errors.append( validation_error )

    def extend_validation_errors( self, validation_errors ):
        self.validation_errors.extend(validation_errors)

    def mark_deleted( self, include_children=True ):
        self.deleted = True
        if include_children:
            for child in self.children:
                child.mark_deleted()

    def mark_undeleted( self, include_children=True ):
        self.deleted = False
        if include_children:
            for child in self.children:
                child.mark_undeleted()

    def mark_unhidden( self, include_children=True ):
        self.visible = True
        if include_children:
            for child in self.children:
                child.mark_unhidden()

    def undeletable( self ):
        if self.purged:
            return False
        return True

    @property
    def is_ok(self):
        return self.state == self.states.OK

    @property
    def is_pending( self ):
        """
        Return true if the dataset is neither ready nor in error
        """
        return self.state in ( self.states.NEW, self.states.UPLOAD,
                               self.states.QUEUED, self.states.RUNNING,
                               self.states.SETTING_METADATA )

    @property
    def source_library_dataset( self ):
        def get_source( dataset ):
            if isinstance( dataset, LibraryDatasetDatasetAssociation ):
                if dataset.library_dataset:
                    return ( dataset, dataset.library_dataset )
            if dataset.copied_from_library_dataset_dataset_association:
                source = get_source( dataset.copied_from_library_dataset_dataset_association )
                if source:
                    return source
            if dataset.copied_from_history_dataset_association:
                source = get_source( dataset.copied_from_history_dataset_association )
                if source:
                    return source
            return ( None, None )
        return get_source( self )

    @property
    def source_dataset_chain( self ):
        def _source_dataset_chain( dataset, lst ):
            try:
                cp_from_ldda = dataset.copied_from_library_dataset_dataset_association
                if cp_from_ldda:
                    lst.append( (cp_from_ldda, "(Data Library)") )
                    return _source_dataset_chain( cp_from_ldda, lst )
            except Exception as e:
                log.warning( e )
            try:
                cp_from_hda = dataset.copied_from_history_dataset_association
                if cp_from_hda:
                    lst.append( (cp_from_hda, cp_from_hda.history.name) )
                    return _source_dataset_chain( cp_from_hda, lst )
            except Exception as e:
                log.warning( e )
            return lst
        return _source_dataset_chain( self, [] )

    @property
    def creating_job( self ):
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

    def get_display_applications( self, trans ):
        return self.datatype.get_display_applications_by_dataset( self, trans )

    def get_visualizations( self ):
        return self.datatype.get_visualizations( self )

    def get_datasources( self, trans ):
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
                if isinstance( source_list, string_types ):
                    source_list = [ source_list ]

                # Loop through sources until viable one is found.
                for source in source_list:
                    msg = self.convert_dataset( trans, source )
                    # No message or PENDING means that source is viable. No
                    # message indicates conversion was done and is successful.
                    if not msg or msg == self.conversion_messages.PENDING:
                        data_source = source
                        break

            # Store msg.
            data_sources_dict[ source_type ] = { "name": data_source, "message": msg }

        return data_sources_dict

    def convert_dataset( self, trans, target_type ):
        """
        Converts a dataset to the target_type and returns a message indicating
        status of the conversion. None is returned to indicate that dataset
        was converted successfully.
        """

        # Get converted dataset; this will start the conversion if necessary.
        try:
            converted_dataset = self.get_converted_dataset( trans, target_type )
        except NoConverterException:
            return self.conversion_messages.NO_CONVERTER
        except ConverterDependencyException as dep_error:
            return { 'kind': self.conversion_messages.ERROR, 'message': dep_error.value }

        # Check dataset state and return any messages.
        msg = None
        if converted_dataset and converted_dataset.state == Dataset.states.ERROR:
            job_id = trans.sa_session.query( JobToOutputDatasetAssociation ) \
                .filter_by( dataset_id=converted_dataset.id ).first().job_id
            job = trans.sa_session.query( Job ).get( job_id )
            msg = { 'kind': self.conversion_messages.ERROR, 'message': job.stderr }
        elif not converted_dataset or converted_dataset.state != Dataset.states.OK:
            msg = self.conversion_messages.PENDING

        return msg


class HistoryDatasetAssociation( DatasetInstance, Dictifiable, UsesAnnotations, HasName ):
    """
    Resource class that creates a relation between a dataset and a user history.
    """

    def __init__( self,
                  hid=None,
                  history=None,
                  copied_from_history_dataset_association=None,
                  copied_from_library_dataset_dataset_association=None,
                  sa_session=None,
                  **kwd ):
        """
        Create a a new HDA and associate it with the given history.
        """
        # FIXME: sa_session is must be passed to DataSetInstance if the create_dataset
        # parameter is True so that the new object can be flushed.  Is there a better way?
        DatasetInstance.__init__( self, sa_session=sa_session, **kwd )
        self.hid = hid
        # Relationships
        self.history = history
        self.copied_from_history_dataset_association = copied_from_history_dataset_association
        self.copied_from_library_dataset_dataset_association = copied_from_library_dataset_dataset_association

    def copy( self, copy_children=False, parent_id=None ):
        """
        Create a copy of this HDA.
        """
        hda = HistoryDatasetAssociation( hid=self.hid,
                                         name=self.name,
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
                                         copied_from_history_dataset_association=self )
        # update init non-keywords as well
        hda.purged = self.purged

        object_session( self ).add( hda )
        object_session( self ).flush()
        hda.set_size()
        # Need to set after flushed, as MetadataFiles require dataset.id
        hda.metadata = self.metadata
        if copy_children:
            for child in self.children:
                child.copy( copy_children=copy_children, parent_id=hda.id )
        if not self.datatype.copy_safe_peek:
            # In some instances peek relies on dataset_id, i.e. gmaj.zip for viewing MAFs
            hda.set_peek()
        object_session( self ).flush()
        return hda

    def copy_attributes( self, new_dataset ):
        new_dataset.hid = self.hid

    def to_library_dataset_dataset_association( self, trans, target_folder,
                                                replace_dataset=None, parent_id=None, user=None, roles=None, ldda_message='' ):
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
            library_dataset = LibraryDataset( folder=target_folder, name=self.name, info=self.info )
            object_session( self ).add( library_dataset )
            object_session( self ).flush()
        if not user:
            # This should never happen since users must be authenticated to upload to a data library
            user = self.history.user
        ldda = LibraryDatasetDatasetAssociation( name=self.name,
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
                                                 user=user )
        object_session( self ).add( ldda )
        object_session( self ).flush()
        # If roles were selected on the upload form, restrict access to the Dataset to those roles
        roles = roles or []
        for role in roles:
            dp = trans.model.DatasetPermissions( trans.app.security_agent.permitted_actions.DATASET_ACCESS.action,
                                                 ldda.dataset, role )
            trans.sa_session.add( dp )
            trans.sa_session.flush()
        # Must set metadata after ldda flushed, as MetadataFiles require ldda.id
        ldda.metadata = self.metadata
        if ldda_message:
            ldda.message = ldda_message
        if not replace_dataset:
            target_folder.add_library_dataset( library_dataset, genome_build=ldda.dbkey )
            object_session( self ).add( target_folder )
            object_session( self ).flush()
        library_dataset.library_dataset_dataset_association_id = ldda.id
        object_session( self ).add( library_dataset )
        object_session( self ).flush()
        for child in self.children:
            child.to_library_dataset_dataset_association( trans,
                                                          target_folder=target_folder,
                                                          replace_dataset=replace_dataset,
                                                          parent_id=ldda.id,
                                                          user=ldda.user )
        if not self.datatype.copy_safe_peek:
            # In some instances peek relies on dataset_id, i.e. gmaj.zip for viewing MAFs
            ldda.set_peek()
        object_session( self ).flush()
        return ldda

    def clear_associated_files( self, metadata_safe=False, purge=False ):
        """
        """
        # metadata_safe = True means to only clear when assoc.metadata_safe == False
        for assoc in self.implicitly_converted_datasets:
            if not assoc.deleted and ( not metadata_safe or not assoc.metadata_safe ):
                assoc.clear( purge=purge )
        for assoc in self.implicitly_converted_parent_datasets:
            assoc.clear( purge=purge, delete_dataset=False )

    def get_access_roles( self, trans ):
        """
        Return The access roles associated with this HDA's dataset.
        """
        return self.dataset.get_access_roles( trans )

    def quota_amount( self, user ):
        """
        Return the disk space used for this HDA relevant to user quotas.

        If the user has multiple instances of this dataset, it will not affect their
        disk usage statistic.
        """
        rval = 0
        # Anon users are handled just by their single history size.
        if not user:
            return rval
        # Gets an HDA and its children's disk usage, if the user does not already
        #   have an association of the same dataset
        if not self.dataset.library_associations and not self.purged and not self.dataset.purged:
            for hda in self.dataset.history_associations:
                if hda.id == self.id:
                    continue
                if not hda.purged and hda.history and hda.history.user and hda.history.user == user:
                    break
            else:
                rval += self.get_total_size()
        for child in self.children:
            rval += child.get_disk_usage( user )
        return rval

    def to_dict( self, view='collection', expose_dataset_path=False ):
        """
        Return attributes of this HDA that are exposed using the API.
        """
        # Since this class is a proxy to rather complex attributes we want to
        # display in other objects, we can't use the simpler method used by
        # other model classes.
        hda = self
        rval = dict( id=hda.id,
                     hda_ldda='hda',
                     uuid=( lambda uuid: str( uuid ) if uuid else None )( hda.dataset.uuid ),
                     hid=hda.hid,
                     file_ext=hda.ext,
                     peek=( lambda hda: hda.display_peek() if hda.peek and hda.peek != 'no peek' else None )( hda ),
                     model_class=self.__class__.__name__,
                     name=hda.name,
                     deleted=hda.deleted,
                     purged=hda.purged,
                     visible=hda.visible,
                     state=hda.state,
                     history_content_type=hda.history_content_type,
                     file_size=int( hda.get_size() ),
                     create_time=hda.create_time.isoformat(),
                     update_time=hda.update_time.isoformat(),
                     data_type=hda.datatype.__class__.__module__ + '.' + hda.datatype.__class__.__name__,
                     genome_build=hda.dbkey,
                     misc_info=hda.info.strip() if isinstance( hda.info, string_types ) else hda.info,
                     misc_blurb=hda.blurb )

        # add tags string list
        tags_str_list = []
        for tag in self.tags:
            tag_str = tag.user_tname
            if tag.value is not None:
                tag_str += ":" + tag.user_value
            tags_str_list.append( tag_str )
        rval[ 'tags' ] = tags_str_list

        if hda.copied_from_library_dataset_dataset_association is not None:
            rval['copied_from_ldda_id'] = hda.copied_from_library_dataset_dataset_association.id

        if hda.history is not None:
            rval['history_id'] = hda.history.id

        if hda.extended_metadata is not None:
            rval['extended_metadata'] = hda.extended_metadata.data

        rval[ 'peek' ] = to_unicode( hda.display_peek() )

        for name, spec in hda.metadata.spec.items():
            val = hda.metadata.get( name )
            if isinstance( val, MetadataFile ):
                # only when explicitly set: fetching filepaths can be expensive
                if not expose_dataset_path:
                    continue
                val = val.file_name
            # If no value for metadata, look in datatype for metadata.
            elif val is None and hasattr( hda.datatype, name ):
                val = getattr( hda.datatype, name )
            rval['metadata_' + name] = val
        return rval

    @property
    def history_content_type( self ):
        return "dataset"

    # TODO: down into DatasetInstance
    content_type = u'dataset'

    @hybrid.hybrid_property
    def type_id( self ):
        return u'-'.join([ self.content_type, str( self.id ) ])

    @type_id.expression
    def type_id( cls ):
        return (( type_coerce( cls.content_type, types.Unicode ) + u'-' +
                  type_coerce( cls.id, types.Unicode ) ).label( 'type_id' ))

    def copy_tags_from( self, target_user, source_hda ):
        """
        Copy tags from `source_hda` to this HDA and assign them the user `target_user`.
        """
        for source_tag_assoc in source_hda.tags:
            new_tag_assoc = source_tag_assoc.copy()
            new_tag_assoc.user = target_user
            self.tags.append( new_tag_assoc )


class HistoryDatasetAssociationDisplayAtAuthorization( object ):
    def __init__( self, hda=None, user=None, site=None ):
        self.history_dataset_association = hda
        self.user = user
        self.site = site


class HistoryDatasetAssociationSubset( object ):
    def __init__(self, hda, subset, location):
        self.hda = hda
        self.subset = subset
        self.location = location


class Library( object, Dictifiable, HasName ):
    permitted_actions = get_permitted_actions( filter='LIBRARY' )
    dict_collection_visible_keys = ( 'id', 'name' )
    dict_element_visible_keys = ( 'id', 'deleted', 'name', 'description', 'synopsis', 'root_folder_id', 'create_time' )

    def __init__( self, name=None, description=None, synopsis=None, root_folder=None ):
        self.name = name or "Unnamed library"
        self.description = description
        self.synopsis = synopsis
        self.root_folder = root_folder

    def to_dict( self, view='collection', value_mapper=None ):
        """
        We prepend an F to folders.
        """
        rval = super( Library, self ).to_dict( view=view, value_mapper=value_mapper )
        if 'root_folder_id' in rval:
            rval[ 'root_folder_id' ] = 'F' + str(rval[ 'root_folder_id' ])
        return rval

    def get_active_folders( self, folder, folders=None ):
        # TODO: should we make sure the library is not deleted?
        def sort_by_attr( seq, attr ):
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
            intermed = map( None, (getattr(_, attr) for _ in seq), range( len( seq ) ), seq )
            intermed.sort()
            return [_[-1] for _ in intermed]
        if folders is None:
            active_folders = [ folder ]
        for active_folder in folder.active_folders:
            active_folders.extend( self.get_active_folders( active_folder, folders ) )
        return sort_by_attr( active_folders, 'id' )

    def get_info_association( self, restrict=False, inherited=False ):
        if self.info_association:
            if not inherited or self.info_association[0].inheritable:
                return self.info_association[0], inherited
            else:
                return None, inherited
        return None, inherited

    def get_template_widgets( self, trans, get_contents=True ):
        # See if we have any associated templates - the returned value for
        # inherited is not applicable at the library level.  The get_contents
        # param is passed by callers that are inheriting a template - these
        # are usually new library datsets for which we want to include template
        # fields on the upload form, but not necessarily the contents of the
        # inherited template saved for the parent.
        info_association, inherited = self.get_info_association()
        if info_association:
            template = info_association.template
            if get_contents:
                # See if we have any field contents
                info = info_association.info
                if info:
                    return template.get_widgets( trans.user, contents=info.content )
            return template.get_widgets( trans.user )
        return []

    def get_access_roles( self, trans ):
        roles = []
        for lp in self.actions:
            if lp.action == trans.app.security_agent.permitted_actions.LIBRARY_ACCESS.action:
                roles.append( lp.role )
        return roles


class LibraryFolder( object, Dictifiable, HasName ):
    dict_element_visible_keys = ( 'id', 'parent_id', 'name', 'description', 'item_count', 'genome_build', 'update_time', 'deleted' )

    def __init__( self, name=None, description=None, item_count=0, order_id=None ):
        self.name = name or "Unnamed folder"
        self.description = description
        self.item_count = item_count
        self.order_id = order_id
        self.genome_build = None

    def add_library_dataset( self, library_dataset, genome_build=None ):
        library_dataset.folder_id = self.id
        library_dataset.order_id = self.item_count
        self.item_count += 1
        if genome_build not in [None, '?']:
            self.genome_build = genome_build

    def add_folder( self, folder ):
        folder.parent_id = self.id
        folder.order_id = self.item_count
        self.item_count += 1

    def get_info_association( self, restrict=False, inherited=False ):
        # If restrict is True, we will return this folder's info_association, not inheriting.
        # If restrict is False, we'll return the next available info_association in the
        # inheritable hierarchy if it is "inheritable".  True is also returned if the
        # info_association was inherited and False if not.  This enables us to eliminate
        # displaying any contents of the inherited template.
        if self.info_association:
            if not inherited or self.info_association[0].inheritable:
                return self.info_association[0], inherited
            else:
                return None, inherited
        if restrict:
            return None, inherited
        if self.parent:
            return self.parent.get_info_association( inherited=True )
        if self.library_root:
            return self.library_root[0].get_info_association( inherited=True )
        return None, inherited

    def get_template_widgets( self, trans, get_contents=True ):
        # See if we have any associated templates.  The get_contents
        # param is passed by callers that are inheriting a template - these
        # are usually new library datsets for which we want to include template
        # fields on the upload form.
        info_association, inherited = self.get_info_association()
        if info_association:
            if inherited:
                template = info_association.template.current.latest_form
            else:
                template = info_association.template
            # See if we have any field contents, but only if the info_association was
            # not inherited ( we do not want to display the inherited contents ).
            # (gvk: 8/30/10) Based on conversations with Dan, we agreed to ALWAYS inherit
            # contents.  We'll use this behavior until we hear from the community that
            # contents should not be inherited.  If we don't hear anything for a while,
            # eliminate the old commented out behavior.
            # if not inherited and get_contents:
            if get_contents:
                info = info_association.info
                if info:
                    return template.get_widgets( trans.user, info.content )
            else:
                return template.get_widgets( trans.user )
        return []

    @property
    def activatable_library_datasets( self ):
        # This needs to be a list
        return [ ld for ld in self.datasets if ld.library_dataset_dataset_association and not ld.library_dataset_dataset_association.dataset.deleted ]

    def to_dict( self, view='collection', value_mapper=None ):
        rval = super( LibraryFolder, self ).to_dict( view=view, value_mapper=value_mapper  )
        info_association, inherited = self.get_info_association()
        if info_association:
            if inherited:
                template = info_association.template.current.latest_form
            else:
                template = info_association.template
            rval['data_template'] = template.name
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
    def parent_library( self ):
        f = self
        while f.parent:
            f = f.parent
        return f.library_root[0]


class LibraryDataset( object ):
    # This class acts as a proxy to the currently selected LDDA
    upload_options = [ ( 'upload_file', 'Upload files' ),
                       ( 'upload_directory', 'Upload directory of files' ),
                       ( 'upload_paths', 'Upload files from filesystem paths' ),
                       ( 'import_from_history', 'Import datasets from your current history' ) ]

    def __init__( self, folder=None, order_id=None, name=None, info=None, library_dataset_dataset_association=None, **kwd ):
        self.folder = folder
        self.order_id = order_id
        self.name = name
        self.info = info
        self.library_dataset_dataset_association = library_dataset_dataset_association

    def set_library_dataset_dataset_association( self, ldda ):
        self.library_dataset_dataset_association = ldda
        ldda.library_dataset = self
        object_session( self ).add_all( ( ldda, self ) )
        object_session( self ).flush()

    def get_info( self ):
        if self.library_dataset_dataset_association:
            return self.library_dataset_dataset_association.info
        elif self._info:
            return self._info
        else:
            return 'no info'

    def set_info( self, info ):
        self._info = info
    info = property( get_info, set_info )

    def get_name( self ):
        if self.library_dataset_dataset_association:
            return self.library_dataset_dataset_association.name
        elif self._name:
            return self._name
        else:
            return 'Unnamed dataset'

    def set_name( self, name ):
        self._name = name
    name = property( get_name, set_name )

    def display_name( self ):
        self.library_dataset_dataset_association.display_name()

    def to_dict( self, view='collection' ):
        # Since this class is a proxy to rather complex attributes we want to
        # display in other objects, we can't use the simpler method used by
        # other model classes.
        ldda = self.library_dataset_dataset_association
        template_data = {}
        for temp_info in ldda.info_association:
            template = temp_info.template
            content = temp_info.info.content
            tmp_dict = {}
            for field in template.fields:
                tmp_dict[field['label']] = content[field['name']]
            template_data[template.name] = tmp_dict

        rval = dict( id=self.id,
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
                     file_size=int( ldda.get_size() ),
                     file_ext=ldda.ext,
                     data_type=ldda.datatype.__class__.__module__ + '.' + ldda.datatype.__class__.__name__,
                     genome_build=ldda.dbkey,
                     misc_info=ldda.info,
                     misc_blurb=ldda.blurb,
                     peek=( lambda ldda: ldda.display_peek() if ldda.peek and ldda.peek != 'no peek' else None )( ldda ),
                     template_data=template_data )
        if ldda.dataset.uuid is None:
            rval['uuid'] = None
        else:
            rval['uuid'] = str(ldda.dataset.uuid)
        for name, spec in ldda.metadata.spec.items():
            val = ldda.metadata.get( name )
            if isinstance( val, MetadataFile ):
                val = val.file_name
            elif isinstance( val, list ):
                val = ', '.join( [str(v) for v in val] )
            rval['metadata_' + name] = val
        return rval


class LibraryDatasetDatasetAssociation( DatasetInstance, HasName ):
    def __init__( self,
                  copied_from_history_dataset_association=None,
                  copied_from_library_dataset_dataset_association=None,
                  library_dataset=None,
                  user=None,
                  sa_session=None,
                  **kwd ):
        # FIXME: sa_session is must be passed to DataSetInstance if the create_dataset
        # parameter in kwd is True so that the new object can be flushed.  Is there a better way?
        DatasetInstance.__init__( self, sa_session=sa_session, **kwd )
        if copied_from_history_dataset_association:
            self.copied_from_history_dataset_association_id = copied_from_history_dataset_association.id
        if copied_from_library_dataset_dataset_association:
            self.copied_from_library_dataset_dataset_association_id = copied_from_library_dataset_dataset_association.id
        self.library_dataset = library_dataset
        self.user = user

    def to_history_dataset_association( self, target_history, parent_id=None, add_to_history=False ):
        hda = HistoryDatasetAssociation( name=self.name,
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
                                         history=target_history )
        object_session( self ).add( hda )
        object_session( self ).flush()
        hda.metadata = self.metadata  # need to set after flushed, as MetadataFiles require dataset.id
        if add_to_history and target_history:
            target_history.add_dataset( hda )
        for child in self.children:
            child.to_history_dataset_association( target_history=target_history, parent_id=hda.id, add_to_history=False )
        if not self.datatype.copy_safe_peek:
            hda.set_peek()  # in some instances peek relies on dataset_id, i.e. gmaj.zip for viewing MAFs
        object_session( self ).flush()
        return hda

    def copy( self, copy_children=False, parent_id=None, target_folder=None ):
        ldda = LibraryDatasetDatasetAssociation( name=self.name,
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
                                                 folder=target_folder )
        object_session( self ).add( ldda )
        object_session( self ).flush()
        # Need to set after flushed, as MetadataFiles require dataset.id
        ldda.metadata = self.metadata
        if copy_children:
            for child in self.children:
                child.copy( copy_children=copy_children, parent_id=ldda.id )
        if not self.datatype.copy_safe_peek:
            # In some instances peek relies on dataset_id, i.e. gmaj.zip for viewing MAFs
            ldda.set_peek()
        object_session( self ).flush()
        return ldda

    def clear_associated_files( self, metadata_safe=False, purge=False ):
        return

    def get_access_roles( self, trans ):
        return self.dataset.get_access_roles( trans )

    def get_manage_permissions_roles( self, trans ):
        return self.dataset.get_manage_permissions_roles( trans )

    def has_manage_permissions_roles( self, trans ):
        return self.dataset.has_manage_permissions_roles( trans )

    def get_info_association( self, restrict=False, inherited=False ):
        # If restrict is True, we will return this ldda's info_association whether it
        # exists or not ( in which case None will be returned ).  If restrict is False,
        # we'll return the next available info_association in the inheritable hierarchy.
        # True is also returned if the info_association was inherited, and False if not.
        # This enables us to eliminate displaying any contents of the inherited template.
        # SM: Accessing self.info_association can cause a query to be emitted
        if self.info_association:
            return self.info_association[0], inherited
        if restrict:
            return None, inherited
        return self.library_dataset.folder.get_info_association( inherited=True )

    def to_dict( self, view='collection' ):
        # Since this class is a proxy to rather complex attributes we want to
        # display in other objects, we can't use the simpler method used by
        # other model classes.
        ldda = self
        try:
            file_size = int( ldda.get_size() )
        except OSError:
            file_size = 0

        rval = dict( id=ldda.id,
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
                     misc_blurb=ldda.blurb )
        if ldda.dataset.uuid is None:
            rval['uuid'] = None
        else:
            rval['uuid'] = str(ldda.dataset.uuid)
        rval['parent_library_id'] = ldda.library_dataset.folder.parent_library.id
        if ldda.extended_metadata is not None:
            rval['extended_metadata'] = ldda.extended_metadata.data
        for name, spec in ldda.metadata.spec.items():
            val = ldda.metadata.get( name )
            if isinstance( val, MetadataFile ):
                val = val.file_name
            # If no value for metadata, look in datatype for metadata.
            elif val is None and hasattr( ldda.datatype, name ):
                val = getattr( ldda.datatype, name )
            rval['metadata_' + name] = val
        return rval

    def get_template_widgets( self, trans, get_contents=True ):
        # See if we have any associated templatesThe get_contents
        # param is passed by callers that are inheriting a template - these
        # are usually new library datsets for which we want to include template
        # fields on the upload form, but not necessarily the contents of the
        # inherited template saved for the parent.
        info_association, inherited = self.get_info_association()
        if info_association:
            if inherited:
                template = info_association.template.current.latest_form
            else:
                template = info_association.template
            # See if we have any field contents, but only if the info_association was
            # not inherited ( we do not want to display the inherited contents ).
            # (gvk: 8/30/10) Based on conversations with Dan, we agreed to ALWAYS inherit
            # contents.  We'll use this behavior until we hear from the community that
            # contents should not be inherited.  If we don't hear anything for a while,
            # eliminate the old commented out behavior.
            # if not inherited and get_contents:
            if get_contents:
                info = info_association.info
                if info:
                    return template.get_widgets( trans.user, info.content )
            else:
                return template.get_widgets( trans.user )
        return []

    def templates_dict( self, use_name=False ):
        """
        Returns a dict of template info
        """
        # TODO: Should have a method that allows names and labels to be returned together in a structured way
        template_data = {}
        for temp_info in self.info_association:
            template = temp_info.template
            content = temp_info.info.content
            tmp_dict = {}
            for field in template.fields:
                if use_name:
                    name = field[ 'name' ]
                else:
                    name = field[ 'label' ]
                tmp_dict[ name ] = content.get( field[ 'name' ] )
            template_data[template.name] = tmp_dict
        return template_data

    def templates_json( self, use_name=False ):
        return json.dumps( self.templates_dict( use_name=use_name ) )


class ExtendedMetadata( object ):
    def __init__(self, data):
        self.data = data


class ExtendedMetadataIndex( object ):
    def __init__( self, extended_metadata, path, value):
        self.extended_metadata = extended_metadata
        self.path = path
        self.value = value


class LibraryInfoAssociation( object ):
    def __init__( self, library, form_definition, info, inheritable=False ):
        self.library = library
        self.template = form_definition
        self.info = info
        self.inheritable = inheritable


class LibraryFolderInfoAssociation( object ):
    def __init__( self, folder, form_definition, info, inheritable=False ):
        self.folder = folder
        self.template = form_definition
        self.info = info
        self.inheritable = inheritable


class LibraryDatasetDatasetInfoAssociation( object ):
    def __init__( self, library_dataset_dataset_association, form_definition, info ):
        # TODO: need to figure out if this should be inheritable to the associated LibraryDataset
        self.library_dataset_dataset_association = library_dataset_dataset_association
        self.template = form_definition
        self.info = info

    @property
    def inheritable( self ):
        return True  # always allow inheriting, used for replacement


class ValidationError( object ):
    def __init__( self, message=None, err_type=None, attributes=None ):
        self.message = message
        self.err_type = err_type
        self.attributes = attributes


class DatasetToValidationErrorAssociation( object ):
    def __init__( self, dataset, validation_error ):
        self.dataset = dataset
        self.validation_error = validation_error


class ImplicitlyConvertedDatasetAssociation( object ):

    def __init__( self, id=None, parent=None, dataset=None, file_type=None, deleted=False, purged=False, metadata_safe=True ):
        self.id = id
        if isinstance(dataset, HistoryDatasetAssociation):
            self.dataset = dataset
        elif isinstance(dataset, LibraryDatasetDatasetAssociation):
            self.dataset_ldda = dataset
        else:
            raise AttributeError( 'Unknown dataset type provided for dataset: %s' % type( dataset ) )
        if isinstance(parent, HistoryDatasetAssociation):
            self.parent_hda = parent
        elif isinstance(parent, LibraryDatasetDatasetAssociation):
            self.parent_ldda = parent
        else:
            raise AttributeError( 'Unknown dataset type provided for parent: %s' % type( parent ) )
        self.type = file_type
        self.deleted = deleted
        self.purged = purged
        self.metadata_safe = metadata_safe

    def clear( self, purge=False, delete_dataset=True ):
        self.deleted = True
        if self.dataset:
            if delete_dataset:
                self.dataset.deleted = True
            if purge:
                self.dataset.purged = True
        if purge and self.dataset.deleted:  # do something with purging
            self.purged = True
            try:
                os.unlink( self.file_name )
            except Exception as e:
                log.error( "Failed to purge associated file (%s) from disk: %s" % ( self.file_name, e ) )


DEFAULT_COLLECTION_NAME = "Unnamed Collection"


class DatasetCollection( object, Dictifiable, UsesAnnotations ):
    """
    """
    dict_collection_visible_keys = ( 'id', 'collection_type' )
    dict_element_visible_keys = ( 'id', 'collection_type' )
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
    ):
        self.id = id
        self.collection_type = collection_type
        if not populated:
            self.populated_state = DatasetCollection.populated_states.NEW

    @property
    def populated( self ):
        top_level_populated = self.populated_state == DatasetCollection.populated_states.OK
        if top_level_populated and self.has_subcollections:
            return all(e.child_collection.populated for e in self.elements)
        return top_level_populated

    @property
    def waiting_for_elements( self ):
        top_level_waiting = self.populated_state == DatasetCollection.populated_states.NEW
        if not top_level_waiting and self.has_subcollections:
            return any(e.child_collection.waiting_for_elements for e in self.elements)
        return top_level_waiting

    def mark_as_populated( self ):
        self.populated_state = DatasetCollection.populated_states.OK

    def handle_population_failed( self, message ):
        self.populated_state = DatasetCollection.populated_states.FAILED
        self.populated_state_message = message

    @property
    def dataset_instances( self ):
        instances = []
        for element in self.elements:
            if element.is_collection:
                instances.extend( element.child_collection.dataset_instances )
            else:
                instance = element.dataset_instance
                instances.append( instance )
        return instances

    @property
    def dataset_elements( self ):
        elements = []
        for element in self.elements:
            if element.is_collection:
                elements.extend( element.child_collection.dataset_elements )
            else:
                elements.append( element )
        return elements

    @property
    def state( self ):
        # TODO: DatasetCollection state handling...
        return 'ok'

    def validate( self ):
        if self.collection_type is None:
            raise Exception("Each dataset collection must define a collection type.")

    def __getitem__( self, key ):
        get_by_attribute = "element_index" if isinstance( key, int ) else "element_identifier"
        for element in self.elements:
            if getattr( element, get_by_attribute ) == key:
                return element
        error_message = "Dataset collection has no %s with key %s." % ( get_by_attribute, key )
        raise KeyError( error_message )

    def copy( self, destination=None, element_destination=None ):
        new_collection = DatasetCollection(
            collection_type=self.collection_type,
        )
        for element in self.elements:
            element.copy_to_collection(
                new_collection,
                destination=destination,
                element_destination=element_destination,
            )
        object_session( self ).add( new_collection )
        object_session( self ).flush()
        return new_collection

    def set_from_dict( self, new_data ):
        # Nothing currently editable in this class.
        return {}

    @property
    def has_subcollections(self):
        return ":" in self.collection_type


class DatasetCollectionInstance( object, HasName ):
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
    def state( self ):
        return self.collection.state

    @property
    def populated( self ):
        return self.collection.populated

    @property
    def dataset_instances( self ):
        return self.collection.dataset_instances

    def display_name( self ):
        return self.get_display_name()

    def _base_to_dict( self, view ):
        return dict(
            id=self.id,
            name=self.name,
            collection_type=self.collection.collection_type,
            populated=self.populated,
            populated_state=self.collection.populated_state,
            populated_state_message=self.collection.populated_state_message,
            type="collection",  # contents type (distinguished from file or folder (in case of library))
        )

    def set_from_dict( self, new_data ):
        """
        Set object attributes to the values in dictionary new_data limiting
        to only those keys in dict_element_visible_keys.

        Returns a dictionary of the keys, values that have been changed.
        """
        # precondition: keys are proper, values are parsed and validated
        changed = self.collection.set_from_dict( new_data )

        # unknown keys are ignored here
        for key in ( k for k in new_data.keys() if k in self.editable_keys ):
            new_val = new_data[ key ]
            old_val = self.__getattribute__( key )
            if new_val == old_val:
                continue

            self.__setattr__( key, new_val )
            changed[ key ] = new_val

        return changed


class HistoryDatasetCollectionAssociation( DatasetCollectionInstance, UsesAnnotations, Dictifiable ):
    """ Associates a DatasetCollection with a History. """
    editable_keys = ( 'name', 'deleted', 'visible' )

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
        super( HistoryDatasetCollectionAssociation, self ).__init__(
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
    def history_content_type( self ):
        return "dataset_collection"

    # TODO: down into DatasetCollectionInstance
    content_type = u'dataset_collection'

    @hybrid.hybrid_property
    def type_id( self ):
        return u'-'.join([ self.content_type, str( self.id ) ])

    @type_id.expression
    def type_id( cls ):
        return (( type_coerce( cls.content_type, types.Unicode ) + u'-' +
                  type_coerce( cls.id, types.Unicode ) ).label( 'type_id' ))

    def to_hda_representative( self, multiple=False ):
        rval = []
        for dataset in self.collection.dataset_elements:
            rval.append( dataset.dataset_instance )
            if multiple is False:
                break
        if len( rval ) > 0:
            return rval if multiple else rval[ 0 ]

    def to_dict( self, view='collection' ):
        dict_value = dict(
            hid=self.hid,
            history_id=self.history.id,
            history_content_type=self.history_content_type,
            visible=self.visible,
            deleted=self.deleted,
            **self._base_to_dict(view=view)
        )
        return dict_value

    def add_implicit_input_collection( self, name, history_dataset_collection ):
        self.implicit_input_collections.append( ImplicitlyCreatedDatasetCollectionInput( name, history_dataset_collection)  )

    def find_implicit_input_collection( self, name ):
        matching_collection = None
        for implicit_input_collection in self.implicit_input_collections:
            if implicit_input_collection.name == name:
                matching_collection = implicit_input_collection.input_dataset_collection
                break
        return matching_collection

    def copy( self, element_destination=None ):
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
        collection_copy = self.collection.copy(
            destination=hdca,
            element_destination=element_destination,
        )
        hdca.collection = collection_copy
        object_session( self ).add( hdca )
        object_session( self ).flush()
        return hdca


class LibraryDatasetCollectionAssociation( DatasetCollectionInstance, Dictifiable ):
    """ Associates a DatasetCollection with a library folder. """
    editable_keys = ( 'name', 'deleted' )

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

    def to_dict( self, view='collection' ):
        dict_value = dict(
            folder_id=self.folder.id,
            **self._base_to_dict(view=view)
        )
        return dict_value


class DatasetCollectionElement( object, Dictifiable ):
    """ Associates a DatasetInstance (hda or ldda) with a DatasetCollection. """
    # actionable dataset id needs to be available via API...
    dict_collection_visible_keys = ( 'id', 'element_type', 'element_index', 'element_identifier' )
    dict_element_visible_keys = ( 'id', 'element_type', 'element_index', 'element_identifier' )

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
        elif isinstance( element, DatasetCollection ):
            self.child_collection = element
        else:
            raise AttributeError( 'Unknown element type provided: %s' % type( element ) )

        self.id = id
        self.collection = collection
        self.element_index = element_index
        self.element_identifier = element_identifier or str(element_index)

    @property
    def element_type( self ):
        if self.hda:
            return "hda"
        elif self.ldda:
            return "ldda"
        elif self.child_collection:
            # TOOD: Rename element_type to element_type.
            return "dataset_collection"
        else:
            raise Exception( "Unknown element instance type" )

    @property
    def is_collection( self ):
        return self.element_type == "dataset_collection"

    @property
    def element_object( self ):
        if self.hda:
            return self.hda
        elif self.ldda:
            return self.ldda
        elif self.child_collection:
            return self.child_collection
        else:
            raise Exception( "Unknown element instance type" )

    @property
    def dataset_instance( self ):
        element_object = self.element_object
        if isinstance( element_object, DatasetCollection ):
            raise AttributeError( "Nested collection has no associated dataset_instance." )
        return element_object

    @property
    def dataset( self ):
        return self.dataset_instance.dataset

    def first_dataset_instance( self ):
        element_object = self.element_object
        if isinstance( element_object, DatasetCollection ):
            return element_object.dataset_instances[ 0 ]
        else:
            return element_object

    def copy_to_collection( self, collection, destination=None, element_destination=None ):
        element_object = self.element_object
        if element_destination:
            if self.is_collection:
                element_object = element_object.copy(
                    destination=destination,
                    element_destination=element_destination
                )
            else:
                new_element_object = element_object.copy( copy_children=True )
                if destination is not None and element_object.hidden_beneath_collection_instance:
                    new_element_object.hidden_beneath_collection_instance = destination
                # Ideally we would not need to give the following
                # element an HID and it would exist in the history only
                # as an element of the containing collection.
                element_destination.add_dataset( new_element_object )
                element_object = new_element_object

        new_element = DatasetCollectionElement(
            element=element_object,
            collection=collection,
            element_index=self.element_index,
            element_identifier=self.element_identifier,
        )
        return new_element


class Event( object ):
    def __init__( self, message=None, history=None, user=None, galaxy_session=None ):
        self.history = history
        self.galaxy_session = galaxy_session
        self.user = user
        self.tool_id = None
        self.message = message


class GalaxySession( object ):
    def __init__( self,
                  id=None,
                  user=None,
                  remote_host=None,
                  remote_addr=None,
                  referer=None,
                  current_history=None,
                  session_key=None,
                  is_valid=False,
                  prev_session_id=None,
                  last_action=None ):
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

    def add_history( self, history, association=None ):
        if association is None:
            self.histories.append( GalaxySessionToHistoryAssociation( self, history ) )
        else:
            self.histories.append( association )

    def get_disk_usage( self ):
        if self.disk_usage is None:
            return 0
        return self.disk_usage

    def set_disk_usage( self, bytes ):
        self.disk_usage = bytes
    total_disk_usage = property( get_disk_usage, set_disk_usage )


class GalaxySessionToHistoryAssociation( object ):
    def __init__( self, galaxy_session, history ):
        self.galaxy_session = galaxy_session
        self.history = history


class UCI( object ):
    def __init__( self ):
        self.id = None
        self.user = None


class StoredWorkflow( object, Dictifiable):

    dict_collection_visible_keys = ( 'id', 'name', 'published', 'deleted' )
    dict_element_visible_keys = ( 'id', 'name', 'published', 'deleted' )

    def __init__( self ):
        self.id = None
        self.user = None
        self.name = None
        self.slug = None
        self.published = False
        self.latest_workflow_id = None
        self.workflows = []

    def copy_tags_from(self, target_user, source_workflow):
        for src_swta in source_workflow.owner_tags:
            new_swta = src_swta.copy()
            new_swta.user = target_user
            self.tags.append(new_swta)

    def to_dict( self, view='collection', value_mapper=None ):
        rval = super( StoredWorkflow, self ).to_dict( view=view, value_mapper=value_mapper )
        tags_str_list = []
        for tag in self.tags:
            tag_str = tag.user_tname
            if tag.value is not None:
                tag_str += ":" + tag.user_value
            tags_str_list.append( tag_str )
        rval['tags'] = tags_str_list
        rval['latest_workflow_uuid'] = ( lambda uuid: str( uuid ) if self.latest_workflow.uuid else None )( self.latest_workflow.uuid )
        return rval


class Workflow( object, Dictifiable ):

    dict_collection_visible_keys = ( 'name', 'has_cycles', 'has_errors' )
    dict_element_visible_keys = ( 'name', 'has_cycles', 'has_errors' )
    input_step_types = ['data_input', 'data_collection_input', 'parameter_input']

    def __init__( self, uuid=None ):
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

    def to_dict( self, view='collection', value_mapper=None):
        rval = super( Workflow, self ).to_dict( view=view, value_mapper=value_mapper )
        rval['uuid'] = ( lambda uuid: str( uuid ) if uuid else None )( self.uuid )
        return rval

    @property
    def steps_by_id( self ):
        steps = {}
        for step in self.steps:
            step_id = step.id
            steps[ step_id ] = step
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
    def top_level_workflow( self ):
        """ If this workflow is not attached to stored workflow directly,
        recursively grab its parents until it is the top level workflow
        which must have a stored workflow associated with it.
        """
        top_level_workflow = self
        if self.stored_workflow is None:
            # TODO: enforce this at creation...
            assert len(self.parent_workflow_steps) == 1
            return self.parent_workflow_steps[0].workflow.top_level_workflow
        return top_level_workflow

    @property
    def top_level_stored_workflow( self ):
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


class WorkflowStep( object ):

    def __init__( self ):
        self.id = None
        self.type = None
        self.tool_id = None
        self.tool_inputs = None
        self.tool_errors = None
        self.position = None
        self.input_connections = []
        self.config = None
        self.label = None
        self.uuid = uuid4()
        self.workflow_outputs = []
        self._input_connections_by_name = None

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
    def content_id( self ):
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
        copied_step.input_connections = copy_list(self.input_connections)

        subworkflow_step_mapping = {}
        subworkflow = self.subworkflow
        if subworkflow:
            copied_subworkflow = subworkflow.copy()
            copied_step.subworkflow = copied_subworkflow
            for subworkflow_step, copied_subworkflow_step in zip(subworkflow.steps, copied_subworkflow.steps):
                subworkflow_step_mapping[subworkflow_step.id] = copied_subworkflow_step

        for old_conn, new_conn in zip(self.input_connections, copied_step.input_connections):
            # new_conn.input_step = new_
            new_conn.input_step = step_mapping[old_conn.input_step_id]
            new_conn.output_step = step_mapping[old_conn.output_step_id]
            if old_conn.input_subworkflow_step_id:
                new_conn.input_subworkflow_step = subworkflow_step_mapping[old_conn.input_subworkflow_step_id]
        for orig_pja in self.post_job_actions:
            PostJobAction( orig_pja.action_type,
                           copied_step,
                           output_name=orig_pja.output_name,
                           action_arguments=orig_pja.action_arguments )
        copied_step.workflow_outputs = copy_list(self.workflow_outputs, copied_step)

    def log_str(self):
        return "WorkflowStep[index=%d,type=%s]" % (self.order_index, self.type)


class WorkflowStepConnection( object ):
    # Constant used in lieu of output_name and input_name to indicate an
    # implicit connection between two steps that is not dependent on a dataset
    # or a dataset collection. Allowing for instance data manager steps to setup
    # index data before a normal tool runs or for workflows that manage data
    # outside of Galaxy.
    NON_DATA_CONNECTION = "__NO_INPUT_OUTPUT_NAME__"

    def __init__( self ):
        self.output_step_id = None
        self.output_name = None
        self.input_step_id = None
        self.input_name = None

    def set_non_data_connection(self):
        self.output_name = WorkflowStepConnection.NON_DATA_CONNECTION
        self.input_name = WorkflowStepConnection.NON_DATA_CONNECTION

    @property
    def non_data_connection(self):
        return (self.output_name == WorkflowStepConnection.NON_DATA_CONNECTION and
                self.input_name == WorkflowStepConnection.NON_DATA_CONNECTION)

    def copy(self):
        # TODO: handle subworkflow ids...
        copied_connection = WorkflowStepConnection()
        copied_connection.output_name = self.output_name
        copied_connection.input_name = self.input_name
        return copied_connection


class WorkflowOutput(object):

    def __init__( self, workflow_step, output_name=None, label=None, uuid=None):
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


class StoredWorkflowUserShareAssociation( object ):

    def __init__( self ):
        self.stored_workflow = None
        self.user = None


class StoredWorkflowMenuEntry( object ):

    def __init__( self ):
        self.stored_workflow = None
        self.user = None
        self.order_index = None


class WorkflowInvocation( object, Dictifiable ):
    dict_collection_visible_keys = ( 'id', 'update_time', 'workflow_id', 'history_id', 'uuid', 'state' )
    dict_element_visible_keys = ( 'id', 'update_time', 'workflow_id', 'history_id', 'uuid', 'state' )
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

    def create_subworkflow_invocation_for_step( self, step ):
        assert step.type == "subworkflow"
        subworkflow_invocation = WorkflowInvocation()
        return self.attach_subworkflow_invocation_for_step( step, subworkflow_invocation )

    def attach_subworkflow_invocation_for_step( self, step, subworkflow_invocation ):
        assert step.type == "subworkflow"
        assoc = WorkflowInvocationToSubworkflowInvocationAssociation()
        assoc.workflow_invocation = self
        assoc.workflow_step = step
        subworkflow_invocation.history = self.history
        subworkflow_invocation.workflow = step.subworkflow
        assoc.subworkflow_invocation = subworkflow_invocation
        self.subworkflow_invocations.append(assoc)
        return assoc

    def get_subworkflow_invocation_for_step( self, step ):
        assoc = self.get_subworkflow_invocation_association_for_step(step)
        return assoc.subworkflow_invocation

    def get_subworkflow_invocation_association_for_step( self, step ):
        assert step.type == "subworkflow"
        assoc = None
        for subworkflow_invocation in self.subworkflow_invocations:
            if subworkflow_invocation.workflow_step == step:
                assoc = subworkflow_invocation
                break
        return assoc

    @property
    def active( self ):
        """ Indicates the workflow invocation is somehow active - and in
        particular valid actions may be performed on its
        WorkflowInvocationSteps.
        """
        states = WorkflowInvocation.states
        return self.state in [ states.NEW, states.READY ]

    def cancel( self ):
        if not self.active:
            return False
        else:
            self.state = WorkflowInvocation.states.CANCELLED
            return True

    def fail( self ):
        self.state = WorkflowInvocation.states.FAILED

    def step_states_by_step_id( self ):
        step_states = {}
        for step_state in self.step_states:
            step_id = step_state.workflow_step_id
            step_states[ step_id ] = step_state
        return step_states

    def step_invocations_by_step_id( self ):
        step_invocations = {}
        for invocation_step in self.steps:
            step_id = invocation_step.workflow_step_id
            if step_id not in step_invocations:
                step_invocations[ step_id ] = []
            step_invocations[ step_id ].append( invocation_step )
        return step_invocations

    def step_invocations_for_step_id( self, step_id ):
        step_invocations = []
        for invocation_step in self.steps:
            if step_id == invocation_step.workflow_step_id:
                step_invocations.append( invocation_step )
        return step_invocations

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
            and_conditions.append( WorkflowInvocation.scheduler == scheduler )
        if handler is not None:
            and_conditions.append( WorkflowInvocation.handler == handler )

        query = sa_session.query(
            WorkflowInvocation
        ).filter( and_( *and_conditions ) )
        # Immediately just load all ids into memory so time slicing logic
        # is relatively intutitive.
        return [wi.id for wi in query.all()]

    def to_dict( self, view='collection', value_mapper=None, step_details=False ):
        rval = super( WorkflowInvocation, self ).to_dict( view=view, value_mapper=value_mapper )
        if view == 'element':
            steps = []
            for step in self.steps:
                if step_details:
                    v = step.to_dict(view='element')
                else:
                    v = step.to_dict(view='collection')
                steps.append( v )
            rval['steps'] = steps

            inputs = {}
            for step in self.steps:
                if step.workflow_step.type == 'tool':
                    for step_input in step.workflow_step.input_connections:
                        output_step_type = step_input.output_step.type
                        if output_step_type in [ 'data_input', 'data_collection_input' ]:
                            src = "hda" if output_step_type == 'data_input' else 'hdca'
                            for job_input in step.job.input_datasets:
                                if job_input.name == step_input.input_name:
                                    inputs[str(step_input.output_step.order_index)] = {
                                        "id": job_input.dataset_id, "src": src,
                                        "uuid" : str(job_input.dataset.dataset.uuid) if job_input.dataset.dataset.uuid is not None else None
                                    }
            rval['inputs'] = inputs
        return rval

    def update( self ):
        self.update_time = galaxy.model.orm.now.now()

    def add_input( self, content, step_id ):
        history_content_type = getattr(content, "history_content_type", None)
        if history_content_type == "dataset":
            request_to_content = WorkflowRequestToInputDatasetAssociation()
            request_to_content.dataset = content
            request_to_content.workflow_step_id = step_id
            self.input_datasets.append( request_to_content )
        elif history_content_type == "dataset_collection":
            request_to_content = WorkflowRequestToInputDatasetCollectionAssociation()
            request_to_content.dataset_collection = content
            request_to_content.workflow_step_id = step_id
            self.input_dataset_collections.append( request_to_content )
        else:
            request_to_content = WorkflowRequestInputStepParmeter()
            request_to_content.parameter_value = content
            request_to_content.workflow_step_id = step_id
            self.input_step_parameters.append( request_to_content )

    def has_input_for_step( self, step_id ):
        for content in self.input_datasets:
            if content.workflow_step_id == step_id:
                return True
        for content in self.input_dataset_collections:
            if content.workflow_step_id == step_id:
                return True
        return False


class WorkflowInvocationToSubworkflowInvocationAssociation( object, Dictifiable ):
    dict_collection_visible_keys = ( 'id', 'workflow_step_id', 'workflow_invocation_id', 'subworkflow_invocation_id' )
    dict_element_visible_keys = ( 'id', 'workflow_step_id', 'workflow_invocation_id', 'subworkflow_invocation_id' )


class WorkflowInvocationStep( object, Dictifiable ):
    dict_collection_visible_keys = ( 'id', 'update_time', 'job_id', 'workflow_step_id', 'action' )
    dict_element_visible_keys = ( 'id', 'update_time', 'job_id', 'workflow_step_id', 'action' )

    def update( self ):
        self.workflow_invocation.update()

    def to_dict( self, view='collection', value_mapper=None ):
        rval = super( WorkflowInvocationStep, self ).to_dict( view=view, value_mapper=value_mapper )
        rval['order_index'] = self.workflow_step.order_index
        rval['workflow_step_label'] = self.workflow_step.label
        rval['workflow_step_uuid'] = str(self.workflow_step.uuid)
        rval['state'] = self.job.state if self.job is not None else None
        if self.job is not None and view == 'element':
            output_dict = {}
            for i in self.job.output_datasets:
                if i.dataset is not None:
                    output_dict[i.name] = {
                        "id" : i.dataset.id, "src" : "hda",
                        "uuid" : str(i.dataset.dataset.uuid) if i.dataset.dataset.uuid is not None else None
                    }
            for i in self.job.output_library_datasets:
                if i.dataset is not None:
                    output_dict[i.name] = {
                        "id" : i.dataset.id, "src" : "ldda",
                        "uuid" : str(i.dataset.dataset.uuid) if i.dataset.dataset.uuid is not None else None
                    }
            rval['outputs'] = output_dict
        return rval


class WorkflowRequest( object, Dictifiable ):
    dict_collection_visible_keys = [ 'id', 'name', 'type', 'state', 'history_id', 'workflow_id' ]
    dict_element_visible_keys = [ 'id', 'name', 'type', 'state', 'history_id', 'workflow_id' ]

    def to_dict( self, view='collection', value_mapper=None ):
        rval = super( WorkflowRequest, self ).to_dict( view=view, value_mapper=value_mapper )
        return rval


class WorkflowRequestInputParameter(object, Dictifiable):
    """ Workflow-related parameters not tied to steps or inputs.
    """
    dict_collection_visible_keys = ['id', 'name', 'value', 'type']
    types = Bunch(
        REPLACEMENT_PARAMETERS='replacements',
        META_PARAMETERS='meta',  #
    )

    def __init__( self, name=None, value=None, type=None ):
        self.name = name
        self.value = value
        self.type = type


class WorkflowRequestStepState(object, Dictifiable):
    """ Workflow step value parameters.
    """
    dict_collection_visible_keys = ['id', 'name', 'value', 'workflow_step_id']

    def __init__( self, workflow_step=None, name=None, value=None ):
        self.workflow_step = workflow_step
        self.name = name
        self.value = value
        self.type = type


class WorkflowRequestToInputDatasetAssociation(object, Dictifiable):
    """ Workflow step input dataset parameters.
    """
    dict_collection_visible_keys = ['id', 'workflow_invocation_id', 'workflow_step_id', 'dataset_id', 'name' ]


class WorkflowRequestToInputDatasetCollectionAssociation(object, Dictifiable):
    """ Workflow step input dataset collection parameters.
    """
    dict_collection_visible_keys = ['id', 'workflow_invocation_id', 'workflow_step_id', 'dataset_collection_id', 'name' ]


class WorkflowRequestInputStepParmeter(object, Dictifiable):
    """ Workflow step parameter inputs.
    """
    dict_collection_visible_keys = ['id', 'workflow_invocation_id', 'workflow_step_id', 'parameter_value' ]


class MetadataFile( StorableObject ):

    def __init__( self, dataset=None, name=None ):
        super(MetadataFile, self).__init__(id=None)
        if isinstance( dataset, HistoryDatasetAssociation ):
            self.history_dataset = dataset
        elif isinstance( dataset, LibraryDatasetDatasetAssociation ):
            self.library_dataset = dataset
        self.name = name

    @property
    def file_name( self ):
        assert self.id is not None, "ID must be set before filename used (commit the object)"
        # Ensure the directory structure and the metadata file object exist
        try:
            da = self.history_dataset or self.library_dataset
            if self.object_store_id is None and da is not None:
                self.object_store_id = da.dataset.object_store_id
            if not da.dataset.object_store.exists( self, extra_dir='_metadata_files', extra_dir_at_root=True, alt_name="metadata_%d.dat" % self.id ):
                da.dataset.object_store.create( self, extra_dir='_metadata_files', extra_dir_at_root=True, alt_name="metadata_%d.dat" % self.id )
            path = da.dataset.object_store.get_filename( self, extra_dir='_metadata_files', extra_dir_at_root=True, alt_name="metadata_%d.dat" % self.id )
            return path
        except AttributeError:
            # In case we're not working with the history_dataset
            # print "Caught AttributeError"
            path = os.path.join( Dataset.file_path, '_metadata_files', *directory_hash_id( self.id ) )
            # Create directory if it does not exist
            try:
                os.makedirs( path )
            except OSError as e:
                # File Exists is okay, otherwise reraise
                if e.errno != errno.EEXIST:
                    raise
            # Return filename inside hashed directory
            return os.path.abspath( os.path.join( path, "metadata_%d.dat" % self.id ) )


class FormDefinition( object, Dictifiable ):
    # The following form_builder classes are supported by the FormDefinition class.
    supported_field_types = [ AddressField, CheckboxField, PasswordField, SelectField, TextArea, TextField, WorkflowField, WorkflowMappingField, HistoryField ]
    types = Bunch( REQUEST='Sequencing Request Form',
                   SAMPLE='Sequencing Sample Form',
                   EXTERNAL_SERVICE='External Service Information Form',
                   RUN_DETAILS_TEMPLATE='Sample run details template',
                   LIBRARY_INFO_TEMPLATE='Library information template',
                   USER_INFO='User Information' )
    dict_collection_visible_keys = ( 'id', 'name' )
    dict_element_visible_keys = ( 'id', 'name', 'desc', 'form_definition_current_id', 'fields', 'layout' )

    def __init__( self, name=None, desc=None, fields=[], form_definition_current=None, form_type=None, layout=None ):
        self.name = name
        self.desc = desc
        self.fields = fields
        self.form_definition_current = form_definition_current
        self.type = form_type
        self.layout = layout

    def to_dict( self, user=None, values=None, security=None ):
        values = values or {}
        form_def = { 'id': security.encode_id( self.id ) if security else self.id, 'name': self.name, 'inputs': [] }
        for field in self.fields:
            FieldClass = ( { 'AddressField'         : AddressField,
                             'CheckboxField'        : CheckboxField,
                             'HistoryField'         : HistoryField,
                             'PasswordField'        : PasswordField,
                             'SelectField'          : SelectField,
                             'TextArea'             : TextArea,
                             'TextField'            : TextField,
                             'WorkflowField'        : WorkflowField } ).get( field[ 'type' ], TextField )
            form_def[ 'inputs' ].append( FieldClass( user=user, value=values.get( field[ 'name' ], field[ 'default' ] ), security=security, **field ).to_dict() )
        return form_def

    def grid_fields( self, grid_index ):
        # Returns a dictionary whose keys are integers corresponding to field positions
        # on the grid and whose values are the field.
        gridfields = {}
        for i, f in enumerate( self.fields ):
            if str( f[ 'layout' ] ) == str( grid_index ):
                gridfields[i] = f
        return gridfields

    def get_widgets( self, user, contents={}, **kwd ):
        '''
        Return the list of widgets that comprise a form definition,
        including field contents if any.
        '''
        params = Params( kwd )
        widgets = []
        for index, field in enumerate( self.fields ):
            field_type = field[ 'type' ]
            if 'name' in field:
                field_name = field[ 'name' ]
            else:
                # Default to names like field_0, field_1, etc for backward compatibility
                # (not sure this is necessary)...
                field_name = 'field_%i' % index
            # Determine the value of the field
            if field_name in kwd:
                # The form was submitted via refresh_on_change
                if field_type == 'CheckboxField':
                    value = CheckboxField.is_checked( params.get( field_name, False ) )
                else:
                    value = restore_text( params.get( field_name, '' ) )
            elif contents:
                try:
                    # This field has a saved value.
                    value = str( contents[ field[ 'name' ] ] )
                except:
                    # If there was an error getting the saved value, we'll still
                    # display the widget, but it will be empty.
                    if field_type == 'AddressField':
                        value = 'none'
                    elif field_type == 'CheckboxField':
                        # Since we do not have contents, set checkbox value to False
                        value = False
                    else:
                        # Set other field types to empty string
                        value = ''
            else:
                # If none of the above, then leave the field empty
                if field_type == 'AddressField':
                    value = 'none'
                elif field_type == 'CheckboxField':
                    # Since we do not have contents, set checkbox value to False
                    value = False
                else:
                    # Set other field types to the default value of the field
                    value = field.get( 'default', '' )
            # Create the field widget
            field_widget = eval( field_type )( field_name )
            if field_type in [ 'TextField', 'PasswordField' ]:
                field_widget.set_size( 40 )
                field_widget.value = value
            elif field_type == 'TextArea':
                field_widget.set_size( 3, 40 )
                field_widget.value = value
            elif field_type in ['AddressField', 'WorkflowField', 'WorkflowMappingField', 'HistoryField']:
                field_widget.user = user
                field_widget.value = value
                field_widget.params = params
            elif field_type == 'SelectField':
                for option in field[ 'selectlist' ]:
                    if option == value:
                        field_widget.add_option( option, option, selected=True )
                    else:
                        field_widget.add_option( option, option )
            elif field_type == 'CheckboxField':
                field_widget.set_checked( value )
            if field[ 'required' ] == 'required':
                req = 'Required'
            else:
                req = 'Optional'
            if field[ 'helptext' ]:
                helptext = '%s (%s)' % ( field[ 'helptext' ], req )
            else:
                helptext = '(%s)' % req
            widgets.append( dict( label=field[ 'label' ], widget=field_widget, helptext=helptext ) )
        return widgets

    def field_as_html( self, field ):
        """Generates disabled html for a field"""
        type = field[ 'type' ]
        form_field = None
        for field_type in self.supported_field_types:
            if type == field_type.__name__:
                # Name it AddressField, CheckboxField, etc.
                form_field = field_type( type )
                break
        if form_field:
            return form_field.get_html( disabled=True )
        # Return None if unsupported field type
        return None


class FormDefinitionCurrent( object ):
    def __init__(self, form_definition=None):
        self.latest_form = form_definition


class FormValues( object ):
    def __init__(self, form_def=None, content=None):
        self.form_definition = form_def
        self.content = content


class Request( object, Dictifiable ):
    states = Bunch( NEW='New',
                    SUBMITTED='In Progress',
                    REJECTED='Rejected',
                    COMPLETE='Complete' )
    dict_collection_visible_keys = ( 'id', 'name', 'state' )

    def __init__( self, name=None, desc=None, request_type=None, user=None, form_values=None, notification=None ):
        self.name = name
        self.desc = desc
        self.type = request_type
        self.values = form_values
        self.user = user
        self.notification = notification
        self.samples_list = []

    @property
    def state( self ):
        latest_event = self.latest_event
        if latest_event:
            return latest_event.state
        return None

    @property
    def latest_event( self ):
        if self.events:
            return self.events[0]
        return None

    @property
    def samples_have_common_state( self ):
        """
        Returns the state of this request's samples when they are all
        in one common state. Otherwise returns False.
        """
        state_for_comparison = self.samples[0].state
        if state_for_comparison is None:
            for s in self.samples:
                if s.state is not None:
                    return False
        for s in self.samples:
            if s.state.id != state_for_comparison.id:
                return False
        return state_for_comparison

    @property
    def last_comment( self ):
        latest_event = self.latest_event
        if latest_event:
            if latest_event.comment:
                return latest_event.comment
            return ''
        return 'No comment'

    def get_sample( self, sample_name ):
        for sample in self.samples:
            if sample.name == sample_name:
                return sample
        return None

    @property
    def is_unsubmitted( self ):
        return self.state in [ self.states.REJECTED, self.states.NEW ]

    @property
    def is_rejected( self ):
        return self.state == self.states.REJECTED

    @property
    def is_submitted( self ):
        return self.state == self.states.SUBMITTED

    @property
    def is_new( self ):

        return self.state == self.states.NEW

    @property
    def is_complete( self ):
        return self.state == self.states.COMPLETE

    @property
    def samples_without_library_destinations( self ):
        # Return all samples that are not associated with a library
        samples = []
        for sample in self.samples:
            if not sample.library:
                samples.append( sample )
        return samples

    @property
    def samples_with_bar_code( self ):
        # Return all samples that have associated bar code
        samples = []
        for sample in self.samples:
            if sample.bar_code:
                samples.append( sample )
        return samples

    def send_email_notification( self, trans, common_state, final_state=False ):
        # Check if an email notification is configured to be sent when the samples
        # are in this state
        if self.notification and common_state.id not in self.notification[ 'sample_states' ]:
            return
        comments = ''
        # Send email
        if trans.app.config.smtp_server is not None and self.notification and self.notification[ 'email' ]:
            body = """
Galaxy Sample Tracking Notification
===================================

User:                     %(user)s

Sequencing request:       %(request_name)s
Sequencer configuration:  %(request_type)s
Sequencing request state: %(request_state)s

Number of samples:        %(num_samples)s
All samples in state:     %(sample_state)s

"""
            values = dict( user=self.user.email,
                           request_name=self.name,
                           request_type=self.type.name,
                           request_state=self.state,
                           num_samples=str( len( self.samples ) ),
                           sample_state=common_state.name,
                           create_time=self.create_time,
                           submit_time=self.create_time )
            body = body % values
            # check if this is the final state of the samples
            if final_state:
                txt = "Sample Name -> Data Library/Folder\r\n"
                for s in self.samples:
                    if s.library:
                        library_name = s.library.name
                        folder_name = s.folder.name
                    else:
                        library_name = 'No target data library'
                        folder_name = 'No target data library folder'
                    txt = txt + "%s -> %s/%s\r\n" % ( s.name, library_name, folder_name )
                body = body + txt
            to = self.notification['email']
            frm = trans.app.config.email_from
            if frm is None:
                host = trans.request.host.split( ':' )[0]
                if host in [ 'localhost', '127.0.0.1', '0.0.0.0' ]:
                    host = socket.getfqdn()
                frm = 'galaxy-no-reply@' + host
            subject = "Galaxy Sample Tracking notification: '%s' sequencing request" % self.name
            try:
                send_mail( frm, to, subject, body, trans.app.config )
                comments = "Email notification sent to %s." % ", ".join( to ).strip().strip( ',' )
            except Exception as e:
                comments = "Email notification failed. (%s)" % str(e)
            # update the request history with the email notification event
        elif not trans.app.config.smtp_server:
            comments = "Email notification failed as SMTP server not set in config file"
        if comments:
            event = RequestEvent( self, self.state, comments )
            trans.sa_session.add( event )
            trans.sa_session.flush()
        return comments


class RequestEvent( object ):
    def __init__(self, request=None, request_state=None, comment=''):
        self.request = request
        self.state = request_state
        self.comment = comment


class ExternalService( object ):
    data_transfer_protocol = Bunch( HTTP='http',
                                    HTTPS='https',
                                    SCP='scp' )

    def __init__( self, name=None, description=None, external_service_type_id=None, version=None, form_definition_id=None, form_values_id=None, deleted=None ):
        self.name = name
        self.description = description
        self.external_service_type_id = external_service_type_id
        self.version = version
        self.form_definition_id = form_definition_id
        self.form_values_id = form_values_id
        self.deleted = deleted
        self.label = None  # Used in the request_type controller's __build_external_service_select_field() method

    def get_external_service_type( self, trans ):
        return trans.app.external_service_types.all_external_service_types[ self.external_service_type_id ]

    def load_data_transfer_settings( self, trans ):
        trans.app.external_service_types.reload( self.external_service_type_id )
        self.data_transfer = {}
        external_service_type = self.get_external_service_type( trans )
        for data_transfer_protocol, data_transfer_obj in external_service_type.data_transfer.items():
            if data_transfer_protocol == self.data_transfer_protocol.SCP:
                scp_configs = {}
                automatic_transfer = data_transfer_obj.config.get( 'automatic_transfer', 'false' )
                scp_configs[ 'automatic_transfer' ] = galaxy.util.string_as_bool( automatic_transfer )
                scp_configs[ 'host' ] = self.form_values.content.get( data_transfer_obj.config.get( 'host', '' ), '' )
                scp_configs[ 'user_name' ] = self.form_values.content.get( data_transfer_obj.config.get( 'user_name', '' ), '' )
                scp_configs[ 'password' ] = self.form_values.content.get( data_transfer_obj.config.get( 'password', '' ), '' )
                scp_configs[ 'data_location' ] = self.form_values.content.get( data_transfer_obj.config.get( 'data_location', '' ), '' )
                scp_configs[ 'rename_dataset' ] = self.form_values.content.get( data_transfer_obj.config.get( 'rename_dataset', '' ), '' )
                self.data_transfer[ self.data_transfer_protocol.SCP ] = scp_configs
            if data_transfer_protocol == self.data_transfer_protocol.HTTP:
                http_configs = {}
                automatic_transfer = data_transfer_obj.config.get( 'automatic_transfer', 'false' )
                http_configs[ 'automatic_transfer' ] = galaxy.util.string_as_bool( automatic_transfer )
                self.data_transfer[ self.data_transfer_protocol.HTTP ] = http_configs

    def populate_actions( self, trans, item, param_dict=None ):
        return self.get_external_service_type( trans ).actions.populate( self, item, param_dict=param_dict )


class RequestType( object, Dictifiable ):
    dict_collection_visible_keys = ( 'id', 'name', 'desc' )
    dict_element_visible_keys = ( 'id', 'name', 'desc', 'request_form_id', 'sample_form_id' )
    rename_dataset_options = Bunch( NO='Do not rename',
                                    SAMPLE_NAME='Preprend sample name',
                                    EXPERIMENT_NAME='Prepend experiment name',
                                    EXPERIMENT_AND_SAMPLE_NAME='Prepend experiment and sample name')
    permitted_actions = get_permitted_actions( filter='REQUEST_TYPE' )

    def __init__( self, name=None, desc=None, request_form=None, sample_form=None ):
        self.name = name
        self.desc = desc
        self.request_form = request_form
        self.sample_form = sample_form

    @property
    def external_services( self ):
        external_services = []
        for rtesa in self.external_service_associations:
            external_services.append( rtesa.external_service )
        return external_services

    def get_external_service( self, external_service_type_id ):
        for rtesa in self.external_service_associations:
            if rtesa.external_service.external_service_type_id == external_service_type_id:
                return rtesa.external_service
        return None

    def get_external_services_for_manual_data_transfer( self, trans ):
        '''Returns all external services that use manual data transfer'''
        external_services = []
        for rtesa in self.external_service_associations:
            external_service = rtesa.external_service
            # load data transfer settings
            external_service.load_data_transfer_settings( trans )
            if external_service.data_transfer:
                for transfer_type, transfer_type_settings in external_service.data_transfer.items():
                    if not transfer_type_settings[ 'automatic_transfer' ]:
                        external_services.append( external_service )
        return external_services

    def delete_external_service_associations( self, trans ):
        '''Deletes all external service associations.'''
        flush_needed = False
        for rtesa in self.external_service_associations:
            trans.sa_session.delete( rtesa )
            flush_needed = True
        if flush_needed:
            trans.sa_session.flush()

    def add_external_service_association( self, trans, external_service ):
        rtesa = trans.model.RequestTypeExternalServiceAssociation( self, external_service )
        trans.sa_session.add( rtesa )
        trans.sa_session.flush()

    @property
    def final_sample_state( self ):
        # The states mapper for this object orders ascending
        return self.states[-1]

    @property
    def run_details( self ):
        if self.run:
            # self.run[0] is [RequestTypeRunAssociation]
            return self.run[0]
        return None

    def get_template_widgets( self, trans, get_contents=True ):
        # See if we have any associated templates.  The get_contents param
        # is passed by callers that are inheriting a template - these are
        # usually new samples for which we want to include template fields,
        # but not necessarily the contents of the inherited template.
        rtra = self.run_details
        if rtra:
            run = rtra.run
            template = run.template
            if get_contents:
                # See if we have any field contents
                info = run.info
                if info:
                    return template.get_widgets( trans.user, contents=info.content )
            return template.get_widgets( trans.user )
        return []


class RequestTypeExternalServiceAssociation( object ):
    def __init__( self, request_type, external_service ):
        self.request_type = request_type
        self.external_service = external_service


class RequestTypePermissions( object ):
    def __init__( self, action, request_type, role ):
        self.action = action
        self.request_type = request_type
        self.role = role


class Sample( object, Dictifiable ):
    # The following form_builder classes are supported by the Sample class.
    supported_field_types = [ CheckboxField, SelectField, TextField, WorkflowField, WorkflowMappingField, HistoryField ]
    bulk_operations = Bunch( CHANGE_STATE='Change state',
                             SELECT_LIBRARY='Select data library and folder' )
    dict_collection_visible_keys = ( 'id', 'name' )

    def __init__(self, name=None, desc=None, request=None, form_values=None, bar_code=None, library=None, folder=None, workflow=None, history=None):
        self.name = name
        self.desc = desc
        self.request = request
        self.values = form_values
        self.bar_code = bar_code
        self.library = library
        self.folder = folder
        self.history = history
        self.workflow = workflow

    @property
    def state( self ):
        latest_event = self.latest_event
        if latest_event:
            return latest_event.state
        return None

    @property
    def latest_event( self ):
        if self.events:
            return self.events[0]
        return None

    @property
    def adding_to_library_dataset_files( self ):
        adding_to_library_datasets = []
        for dataset in self.datasets:
            if dataset.status == SampleDataset.transfer_status.ADD_TO_LIBRARY:
                adding_to_library_datasets.append( dataset )
        return adding_to_library_datasets

    @property
    def inprogress_dataset_files( self ):
        inprogress_datasets = []
        for dataset in self.datasets:
            if dataset.status not in [ SampleDataset.transfer_status.NOT_STARTED, SampleDataset.transfer_status.COMPLETE ]:
                inprogress_datasets.append( dataset )
        return inprogress_datasets

    @property
    def queued_dataset_files( self ):
        queued_datasets = []
        for dataset in self.datasets:
            if dataset.status == SampleDataset.transfer_status.IN_QUEUE:
                queued_datasets.append( dataset )
        return queued_datasets

    @property
    def transfer_error_dataset_files( self ):
        transfer_error_datasets = []
        for dataset in self.datasets:
            if dataset.status == SampleDataset.transfer_status.ERROR:
                transfer_error_datasets.append( dataset )
        return transfer_error_datasets

    @property
    def transferred_dataset_files( self ):
        transferred_datasets = []
        for dataset in self.datasets:
            if dataset.status == SampleDataset.transfer_status.COMPLETE:
                transferred_datasets.append( dataset )
        return transferred_datasets

    @property
    def transferring_dataset_files( self ):
        transferring_datasets = []
        for dataset in self.datasets:
            if dataset.status == SampleDataset.transfer_status.TRANSFERRING:
                transferring_datasets.append( dataset )
        return transferring_datasets

    @property
    def untransferred_dataset_files( self ):
        untransferred_datasets = []
        for dataset in self.datasets:
            if dataset.status != SampleDataset.transfer_status.COMPLETE:
                untransferred_datasets.append( dataset )
        return untransferred_datasets

    @property
    def run_details( self ):
        # self.runs is a list of SampleRunAssociations ordered descending on update_time.
        if self.runs:
            # Always use the latest run details template, self.runs[0] is a SampleRunAssociation
            return self.runs[0]
        # Inherit this sample's RequestType run details, if one exists.
        return self.request.type.run_details

    def get_template_widgets( self, trans, get_contents=True ):
        # Samples have a one-to-many relationship with run details, so we return the
        # widgets for last associated template.  The get_contents param will populate
        # the widget fields with values from the template inherited from the sample's
        # RequestType.
        template = None
        if self.runs:
            # The self.runs mapper orders descending on update_time.
            run = self.runs[0].run
            template = run.template
        if template is None:
            # There are no run details associated with this sample, so inherit the
            # run details template from the sample's RequestType.
            rtra = self.request.type.run_details
            if rtra:
                run = rtra.run
                template = run.template
        if template:
            if get_contents:
                # See if we have any field contents
                info = run.info
                if info:
                    return template.get_widgets( trans.user, contents=info.content )
            return template.get_widgets( trans.user )
        return []

    def populate_external_services( self, param_dict=None, trans=None ):
        if self.request and self.request.type:
            return [ service.populate_actions( item=self, param_dict=param_dict, trans=trans ) for service in self.request.type.external_services ]


class SampleState( object ):
    def __init__(self, name=None, desc=None, request_type=None):
        self.name = name
        self.desc = desc
        self.request_type = request_type


class SampleEvent( object ):
    def __init__(self, sample=None, sample_state=None, comment=''):
        self.sample = sample
        self.state = sample_state
        self.comment = comment


class SampleDataset( object ):
    transfer_status = Bunch( NOT_STARTED='Not started',
                             IN_QUEUE='In queue',
                             TRANSFERRING='Transferring dataset',
                             ADD_TO_LIBRARY='Adding to data library',
                             COMPLETE='Complete',
                             ERROR='Error' )

    def __init__( self, sample=None, name=None, file_path=None, status=None, error_msg=None, size=None, external_service=None ):
        self.sample = sample
        self.name = name
        self.file_path = file_path
        self.status = status
        self.error_msg = error_msg
        self.size = size
        self.external_service = external_service


class Run( object ):
    def __init__( self, form_definition, form_values, subindex=None ):
        self.template = form_definition
        self.info = form_values
        self.subindex = subindex


class RequestTypeRunAssociation( object ):
    def __init__( self, request_type, run ):
        self.request_type = request_type
        self.run = run


class SampleRunAssociation( object ):
    def __init__( self, sample, run ):
        self.sample = sample
        self.run = run


class UserAddress( object ):
    def __init__( self, user=None, desc=None, name=None, institution=None,
                  address=None, city=None, state=None, postal_code=None,
                  country=None, phone=None ):
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

    def to_dict( self, trans ):
        return { 'id'           : trans.security.encode_id( self.id ),
                 'name'         : sanitize_html( self.name ),
                 'desc'         : sanitize_html( self.desc ),
                 'institution'  : sanitize_html( self.institution ),
                 'address'      : sanitize_html( self.address ),
                 'city'         : sanitize_html( self.city ),
                 'state'        : sanitize_html( self.state ),
                 'postal_code'  : sanitize_html( self.postal_code ),
                 'country'      : sanitize_html( self.country ),
                 'phone'        : sanitize_html( self.phone ) }

    def get_html(self):
        # This should probably be deprecated eventually.  It should currently
        # sanitize.
        # TODO Find out where else uses this and replace with
        # templates
        html = ''
        if self.name:
            html = html + sanitize_html(self.name)
        if self.institution:
            html = html + '<br/>' + sanitize_html(self.institution)
        if self.address:
            html = html + '<br/>' + sanitize_html(self.address)
        if self.city:
            html = html + '<br/>' + sanitize_html(self.city)
        if self.state:
            html = html + ' ' + sanitize_html(self.state)
        if self.postal_code:
            html = html + ' ' + sanitize_html(self.postal_code)
        if self.country:
            html = html + '<br/>' + sanitize_html(self.country)
        if self.phone:
            html = html + '<br/>' + 'phone: ' + sanitize_html(self.phone)
        return html


class UserOpenID( object ):
    def __init__( self, user=None, session=None, openid=None ):
        self.user = user
        self.session = session
        self.openid = openid


class Page( object, Dictifiable ):
    dict_element_visible_keys = [ 'id', 'title', 'latest_revision_id', 'slug', 'published', 'importable', 'deleted' ]

    def __init__( self ):
        self.id = None
        self.user = None
        self.title = None
        self.slug = None
        self.latest_revision_id = None
        self.revisions = []
        self.importable = None
        self.published = None

    def to_dict( self, view='element' ):
        rval = super( Page, self ).to_dict( view=view )
        rev = []
        for a in self.revisions:
            rev.append(a.id)
        rval['revision_ids'] = rev
        return rval


class PageRevision( object, Dictifiable ):
    dict_element_visible_keys = [ 'id', 'page_id', 'title', 'content' ]

    def __init__( self ):
        self.user = None
        self.title = None
        self.content = None

    def to_dict( self, view='element' ):
        rval = super( PageRevision, self ).to_dict( view=view )
        rval['create_time'] = str(self.create_time)
        rval['update_time'] = str(self.update_time)
        return rval


class PageUserShareAssociation( object ):
    def __init__( self ):
        self.page = None
        self.user = None


class Visualization( object ):
    def __init__( self, id=None, user=None, type=None, title=None, dbkey=None, slug=None, latest_revision=None ):
        self.id = id
        self.user = user
        self.type = type
        self.title = title
        self.dbkey = dbkey
        self.slug = slug
        self.latest_revision = latest_revision
        self.revisions = []
        if self.latest_revision:
            self.revisions.append( latest_revision )

    def copy( self, user=None, title=None ):
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

        copy_viz = Visualization( user=user, type=self.type, title=title, dbkey=self.dbkey )
        copy_revision = self.latest_revision.copy( visualization=copy_viz )
        copy_viz.latest_revision = copy_revision
        return copy_viz


class VisualizationRevision( object ):
    def __init__( self, visualization=None, title=None, dbkey=None, config=None ):
        self.id = None
        self.visualization = visualization
        self.title = title
        self.dbkey = dbkey
        self.config = config

    def copy( self, visualization=None ):
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


class VisualizationUserShareAssociation( object ):
    def __init__( self ):
        self.visualization = None
        self.user = None


class TransferJob( object ):
    # These states are used both by the transfer manager's IPC and the object
    # state in the database.  Not all states are used by both.
    states = Bunch( NEW='new',
                    UNKNOWN='unknown',
                    PROGRESS='progress',
                    RUNNING='running',
                    ERROR='error',
                    DONE='done' )
    terminal_states = [ states.ERROR,
                        states.DONE ]

    def __init__( self, state=None, path=None, info=None, pid=None, socket=None, params=None ):
        self.state = state
        self.path = path
        self.info = info
        self.pid = pid
        self.socket = socket
        self.params = params


class Tag ( object ):
    def __init__( self, id=None, type=None, parent_id=None, name=None ):
        self.id = id
        self.type = type
        self.parent_id = parent_id
        self.name = name

    def __str__( self ):
        return "Tag(id=%s, type=%i, parent_id=%s, name=%s)" % ( self.id, self.type, self.parent_id, self.name )


class ItemTagAssociation ( object, Dictifiable ):
    dict_collection_visible_keys = ( 'id', 'user_tname', 'user_value' )
    dict_element_visible_keys = dict_collection_visible_keys

    def __init__( self, id=None, user=None, item_id=None, tag_id=None, user_tname=None, value=None ):
        self.id = id
        self.user = user
        self.item_id = item_id
        self.tag_id = tag_id
        self.user_tname = user_tname
        self.value = None
        self.user_value = None

    def copy(self):
        new_ta = type(self)()
        new_ta.tag_id = self.tag_id
        new_ta.user_tname = self.user_tname
        new_ta.value = self.value
        new_ta.user_value = self.user_value
        return new_ta


class HistoryTagAssociation ( ItemTagAssociation ):
    pass


class DatasetTagAssociation ( ItemTagAssociation ):
    pass


class HistoryDatasetAssociationTagAssociation ( ItemTagAssociation ):
    pass


class PageTagAssociation ( ItemTagAssociation ):
    pass


class WorkflowStepTagAssociation ( ItemTagAssociation ):
    pass


class StoredWorkflowTagAssociation ( ItemTagAssociation ):
    pass


class VisualizationTagAssociation ( ItemTagAssociation ):
    pass


class HistoryDatasetCollectionTagAssociation( ItemTagAssociation ):
    pass


class LibraryDatasetCollectionTagAssociation( ItemTagAssociation ):
    pass


class ToolTagAssociation( ItemTagAssociation ):
    def __init__( self, id=None, user=None, tool_id=None, tag_id=None, user_tname=None, value=None ):
        self.id = id
        self.user = user
        self.tool_id = tool_id
        self.tag_id = tag_id
        self.user_tname = user_tname
        self.value = None
        self.user_value = None


class WorkRequestTagAssociation( ItemTagAssociation ):
    def __init__( self, id=None, user=None, workflow_request_id=None, tag_id=None, user_tname=None, value=None ):
        self.id = id
        self.user = user
        self.workflow_request_id = workflow_request_id
        self.tag_id = tag_id
        self.user_tname = user_tname
        self.value = None
        self.user_value = None


# Item annotation classes.
class HistoryAnnotationAssociation( object ):
    pass


class HistoryDatasetAssociationAnnotationAssociation( object ):
    pass


class StoredWorkflowAnnotationAssociation( object ):
    pass


class WorkflowStepAnnotationAssociation( object ):
    pass


class PageAnnotationAssociation( object ):
    pass


class VisualizationAnnotationAssociation( object ):
    pass


class HistoryDatasetCollectionAnnotationAssociation( object ):
    pass


class LibraryDatasetCollectionAnnotationAssociation( object ):
    pass


# Item rating classes.

class ItemRatingAssociation( object ):
    def __init__( self, id=None, user=None, item=None, rating=0 ):
        self.id = id
        self.user = user
        self.item = item
        self.rating = rating

    def set_item( self, item ):
        """ Set association's item. """
        pass


class HistoryRatingAssociation( ItemRatingAssociation ):
    def set_item( self, history ):
        self.history = history


class HistoryDatasetAssociationRatingAssociation( ItemRatingAssociation ):
    def set_item( self, history_dataset_association ):
        self.history_dataset_association = history_dataset_association


class StoredWorkflowRatingAssociation( ItemRatingAssociation ):
    def set_item( self, stored_workflow ):
        self.stored_workflow = stored_workflow


class PageRatingAssociation( ItemRatingAssociation ):
    def set_item( self, page ):
        self.page = page


class VisualizationRatingAssociation( ItemRatingAssociation ):
    def set_item( self, visualization ):
        self.visualization = visualization


class HistoryDatasetCollectionRatingAssociation( ItemRatingAssociation ):
    def set_item( self, dataset_collection ):
        self.dataset_collection = dataset_collection


class LibraryDatasetCollectionRatingAssociation( ItemRatingAssociation ):
    def set_item( self, dataset_collection ):
        self.dataset_collection = dataset_collection


# Data Manager Classes
class DataManagerHistoryAssociation( object ):
    def __init__( self, id=None, history=None, user=None ):
        self.id = id
        self.history = history
        self.user = user


class DataManagerJobAssociation( object ):
    def __init__( self, id=None, job=None, data_manager_id=None ):
        self.id = id
        self.job = job
        self.data_manager_id = data_manager_id
# end of Data Manager Classes


class UserPreference ( object ):
    def __init__( self, name=None, value=None):
        self.name = name
        self.value = value


class UserAction( object ):
    def __init__( self, id=None, create_time=None, user_id=None, session_id=None, action=None, params=None, context=None):
        self.id = id
        self.create_time = create_time
        self.user_id = user_id
        self.session_id = session_id
        self.action = action
        self.params = params
        self.context = context


class APIKeys( object ):
    def __init__( self, id=None, user_id=None, key=None):
        self.id = id
        self.user_id = user_id
        self.key = key


def copy_list(lst, *args, **kwds):
    if lst is None:
        return lst
    else:
        return [el.copy(*args, **kwds) for el in lst]
