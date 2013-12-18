from re import search

EXTERNAL_ID_TYPE_ANY = None

EXTERNAL_ID_PATTERNS = [
    ('condor', r'submitted to cluster (\d+)\.'),
    ('slurm', r'Submitted batch job (\w+)'),
    ('torque', r'(.+)'),  # Default 'pattern' assumed by Galaxy code circa August 2013.
]


def parse_external_id(output, type=EXTERNAL_ID_TYPE_ANY):
    """
    Attempt to parse the output of job submission commands for an external id.__doc__

    >>> parse_external_id("12345.pbsmanager")
    '12345.pbsmanager'
    >>> parse_external_id('Submitted batch job 185')
    '185'
    >>> parse_external_id('Submitted batch job 185', type='torque')
    'Submitted batch job 185'
    >>> parse_external_id('submitted to cluster 125.')
    '125'
    >>> parse_external_id('submitted to cluster 125.', type='slurm')
    >>>
    """
    external_id = None
    for pattern_type, pattern in EXTERNAL_ID_PATTERNS:
        if type != EXTERNAL_ID_TYPE_ANY and type != pattern_type:
            continue

        match = search(pattern, output)
        if match:
            external_id = match.group(1)
            break

    return external_id
