"""
LSF helper utilities.
"""
from subprocess import (
    CalledProcessError,
    check_call,
    PIPE,
    Popen,
    STDOUT
)

from ..external import parse_external_id

DEFAULT_QUERY_CLASSAD = dict(
    universe='vanilla',
    getenv='true',
    notification='NEVER',
)

LSF_OPTIONS = dict(
   queue="-q",
   cores="-n",
   memory="-M",  # memory in kb, change unit.
   working_dir="-cwd"
)

PROBLEM_RUNNING_LSF_SUBMIT = \
    "Problem encountered while running bsub."
PROBLEM_PARSING_EXTERNAL_ID = \
    "Failed to find job id from bsub"

SUBMIT_PARAM_PREFIX = "submit_"


def submission_params(prefix=SUBMIT_PARAM_PREFIX, **kwds):
    submission_params = {}
    for key in kwds:
        value = kwds[key]
        key = key.lower()
        if key.startswith(prefix):
            lsf_key = key[len(prefix):]
            submission_params[lsf_key] = value
    return submission_params


def build_submit_description(executable, output, error, user_log, query_params):
    """
    Build up the contents of a lsf submit description file.

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
    submit_description.append('#!/bin/bash')
    for key, value in all_query_params.items():
        if key in LSF_OPTIONS.keys():
            submit_description.append('#BSUB %s %s' % (LSF_OPTIONS[key], value))
    submit_description.append('#BSUB -o ' + output)
    submit_description.append('#BSUB -e ' + error)
    #submit_description.append('log = ' + user_log)
    #submit_description.append('queue')
    submit_description.append(executable)
    return '\n'.join(submit_description)


def lsf_submit(submit_file):
    """
    Submit an lsf job described by the given file. Parse an external id for
    the submission or return None and a reason for the failure.
    """
    external_id = None
    try:
        submit = Popen(('bsub', submit_file), stdout=PIPE, stderr=STDOUT)
        message, _ = submit.communicate()
        if submit.returncode == 0:
            external_id = parse_external_id(message, type='lsf')
        else:
            message = PROBLEM_PARSING_EXTERNAL_ID
    except Exception as e:
        message = str(e)
    return external_id, message


def lsf_stop(external_id):
    """
    Stop running LSF job and return a failure_message if this
    fails.
    """
    failure_message = None
    try:
        check_call(('bstop', external_id))
    except CalledProcessError:
        failure_message = "bstop failed"
    except Exception as e:
        "error encountered calling bstop: %s" % e
    return failure_message


def lsf_bjob(external_id):
    """
    Checks LSF job state through bjobs for external id (LSF job id)
    """
    check_job = Popen(('bjobs', '-o', 'stat', '-noheader',external_id), stdout=PIPE, stderr=STDOUT)
    status, _ = check_job.communicate()

    running = status is "RUN"
    complete = status is "DONE"
    failed = status is "EXIT"
    if "is not found" in status:
        raise Exception("Job %s not found in LSF" % external_id)
    return running, failed, complete
