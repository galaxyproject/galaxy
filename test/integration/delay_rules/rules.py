from galaxy.jobs.mapper import JobNotReadyException


def delay():
    raise JobNotReadyException()
