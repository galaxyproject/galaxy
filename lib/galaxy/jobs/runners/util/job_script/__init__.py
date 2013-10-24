from string import Template
from pkg_resources import resource_string

DEFAULT_JOB_FILE_TEMPLATE = Template(
    resource_string(__name__, 'DEFAULT_JOB_FILE_TEMPLATE.sh')
)

SLOTS_STATEMENT_CLUSTER_DEFAULT = \
    resource_string(__name__, 'CLUSTER_SLOTS_STATEMENT.sh')

SLOTS_STATEMENT_SINGLE = """
GALAXY_SLOTS="1"
"""

REQUIRED_TEMPLATE_PARAMS = ['working_directory', 'command', 'exit_code_path']
OPTIONAL_TEMPLATE_PARAMS = {
    'galaxy_lib': None,
    'headers': '',
    'env_setup_commands': '',
    'slots_statement': SLOTS_STATEMENT_CLUSTER_DEFAULT,
}


def job_script(template=DEFAULT_JOB_FILE_TEMPLATE, **kwds):
    """

    >>> has_exception = False
    >>> try: job_script()
    ... except Exception as e: has_exception = True
    >>> has_exception
    True
    >>> script = job_script(working_directory='wd', command='uptime', exit_code_path='ec')
    >>> '\\nuptime\\n' in script
    True
    >>> 'echo $? > ec' in script
    True
    >>> 'GALAXY_LIB="None"' in script
    True
    >>> script.startswith('#!/bin/sh\\n#PBS -test\\n')
    False
    >>> script = job_script(working_directory='wd', command='uptime', exit_code_path='ec', headers='#PBS -test')
    >>> script.startswith('#!/bin/sh\\n#PBS -test\\n')
    True
    >>> script = job_script(working_directory='wd', command='uptime', exit_code_path='ec', slots_statement='GALAXY_SLOTS="$SLURM_JOB_NUM_NODES"')
    >>> script.find('GALAXY_SLOTS="$SLURM_JOB_NUM_NODES"\\nexport GALAXY_SLOTS\\n') > 0
    True
    """
    if any([param not in kwds for param in REQUIRED_TEMPLATE_PARAMS]):
        raise Exception("Failed to create job_script, a required parameter is missing.")
    template_params = OPTIONAL_TEMPLATE_PARAMS.copy()
    template_params.update(**kwds)
    if not isinstance(template, Template):
        template = Template(template)
    return template.safe_substitute(template_params)
