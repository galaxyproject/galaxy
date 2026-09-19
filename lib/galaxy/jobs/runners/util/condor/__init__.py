"""
Condor helper utilities.
"""

from subprocess import (
    CalledProcessError,
    check_call,
)

from galaxy.util import (
    commands,
    unicodify,
)
from ..external import parse_external_id

DEFAULT_QUERY_CLASSAD = dict(
    universe="vanilla",
    getenv="true",
    notification="NEVER",
)

PROBLEM_PARSING_EXTERNAL_ID = "Failed to find job id from condor_submit"

SUBMIT_PARAM_PREFIX = "submit_"


def submission_params(prefix=SUBMIT_PARAM_PREFIX, **kwds):
    submission_params = {}
    prefix_len = len(prefix)
    for key in kwds:
        value = kwds[key]
        key = key.lower()
        if key.startswith(prefix):
            condor_key = key[prefix_len:]
            submission_params[condor_key] = value
    return submission_params


def build_submit_description(executable, output, error, user_log, query_params):
    """
    Build up the contents of a condor submit description file.

    >>> submit_args = dict(executable='/path/to/script', output='o', error='e', user_log='ul')
    >>> submit_args['query_params'] = dict()
    >>> default_description = build_submit_description(**submit_args)
    >>> assert 'executable = /path/to/script' in default_description
    >>> assert 'output = o' in default_description
    >>> assert 'error = e' in default_description
    >>> assert 'queue' in default_description
    >>> assert 'universe = vanilla' in default_description
    >>> assert 'universe = standard' not in default_description
    >>> submit_args['query_params'] = dict(universe='standard')
    >>> std_description = build_submit_description(**submit_args)
    >>> assert 'universe = vanilla' not in std_description
    >>> assert 'universe = standard' in std_description
    """
    all_query_params = DEFAULT_QUERY_CLASSAD.copy()
    all_query_params.update(query_params)

    submit_description = []
    for key, value in all_query_params.items():
        submit_description.append(f"{key} = {value}")
    submit_description.append(f"executable = {executable}")
    submit_description.append(f"output = {output}")
    submit_description.append(f"error = {error}")
    submit_description.append(f"log = {user_log}")
    submit_description.append("queue")
    return "\n".join(submit_description)


def condor_submit(submit_file):
    """
    Submit a condor job described by the given file. Parse an external id for
    the submission or return None and a reason for the failure.
    """
    external_id = None
    failure_message = None
    try:
        condor_message = commands.execute(("condor_submit", submit_file))
    except commands.CommandLineException as e:
        failure_message = unicodify(e)
    else:
        try:
            external_id = parse_external_id(condor_message, type="condor")
        except Exception:
            failure_message = f"{PROBLEM_PARSING_EXTERNAL_ID}: {condor_message}"
    return external_id, failure_message


def condor_stop(external_id):
    """
    Stop running condor job and return a failure_message if this
    fails.
    """
    failure_message = None
    try:
        check_call(("condor_rm", external_id))
    except CalledProcessError:
        failure_message = "condor_rm failed"
    except Exception as e:
        failure_message = f"error encountered calling condor_rm: {unicodify(e)}"
    return failure_message


def summarize_condor_log(log_file, external_id):
    """ """
    log_job_id = external_id.zfill(3)
    s1 = s4 = s7 = s5 = s9 = False
    with open(log_file) as log_handle:
        for line in log_handle:
            if f"001 ({log_job_id}." in line:
                s1 = True
            if f"004 ({log_job_id}." in line:
                s4 = True
            if f"007 ({log_job_id}." in line:
                s7 = True
            if f"005 ({log_job_id}." in line:
                s5 = True
            if f"009 ({log_job_id}." in line:
                s9 = True
        file_size = log_handle.tell()
    return s1, s4, s7, s5, s9, file_size
