"""
Condor helper utilities.
"""

DEFAULT_QUERY_CLASSAD = dict(
    universe='vanilla',
    getenv='true',
    notification='NEVER',
)

PROBLEM_PARSING_EXTERNAL_ID = \
    "Failed to find job id from condor_submit"

SUBMIT_PARAM_PREFIX = "submit_"


def submission_params(prefix=SUBMIT_PARAM_PREFIX, **kwds):
    submission_params = {}
    for key in kwds:
        value = kwds[key]
        key = key.lower()
        if key.startswith(prefix):
            condor_key = key[len(prefix):]
            submission_params[condor_key] = value
    return submission_params


def build_submit_description(submit_params, query_params):
    """
    Build up the contents of a condor submit description file.

    >>> submit_args = dict(executable='/path/to/script', output='o', error='e', log='ul')
    >>> query_args = dict()
    >>> default_description = build_submit_description(submit_args, query_args)
    >>> assert ('executable', '/path/to/script') in default_description.items()
    >>> assert ('output', 'o') in default_description.items()
    >>> assert ('error', 'e') in default_description.items()
    >>> assert ('universe', 'vanilla') in default_description.items()
    >>> assert ('universe', 'standard') not in default_description.items()
    >>> query_args = dict(universe='standard')
    >>> std_description = build_submit_description(submit_args, query_args)
    >>> assert ('universe', 'vanilla') not in std_description.items()
    >>> assert ('universe', 'standard') in std_description.items()
    """
    all_query_params = DEFAULT_QUERY_CLASSAD.copy()
    all_query_params.update(query_params)
    all_query_params.update(submit_params)
    return all_query_params
