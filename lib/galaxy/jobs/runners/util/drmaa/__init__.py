try:
    from drmaa import JobControlAction, Session
except ImportError as e:
    # Will not be able to use DRMAA
    Session = None

NO_DRMAA_MESSAGE = "Attempt to use DRMAA, but DRMAA Python library cannot be loaded."


class DrmaaSessionFactory(object):
    """
    Abstraction used to production DrmaaSession wrappers.
    """
    def __init__(self):
        self.session_constructor = Session

    def get(self, **kwds):
        session_constructor = self.session_constructor
        if not session_constructor:
            raise Exception(NO_DRMAA_MESSAGE)
        return DrmaaSession(session_constructor(), **kwds)


class DrmaaSession(object):
    """
    Abstraction around `drmaa` module `Session` objects.
    """

    def __init__(self, session, **kwds):
        self.session = session
        session.initialize()

    def run_job(self, **kwds):
        """
        Create a DRMAA job template, populate with specified properties,
        run the job, and return the external_job_id.
        """
        template = self.session.createJobTemplate()
        try:
            for key in kwds:
                setattr(template, key, kwds[key])
            return self.session.runJob(template)
        finally:
            self.session.deleteJobTemplate(template)

    def kill(self, external_job_id):
        return self.session.control(str(external_job_id), JobControlAction.TERMINATE)

    def job_status(self, external_job_id):
        return self.session.jobStatus(str(external_job_id))

    def close(self):
        return self.session.exit()


__all__ = ('DrmaaSessionFactory', )
