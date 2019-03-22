import logging
import sqlite3


from six import string_types
from sqlalchemy import or_


from galaxy.tools.deps.docker_util import parse_port_text as docker_parse_port_text
from galaxy.util.filelock import FileLock


log = logging.getLogger(__name__)

DATABASE_TABLE_NAME = 'gxrtproxy'


class RealtimeSqlite(object):

    def __init__(self, sqlite_filename, encode_id):
        self.sqlite_filename = sqlite_filename
        self.encode_id = encode_id

    def get(self, key, key_type):
        with FileLock(self.sqlite_filename):
            conn = sqlite3.connect(self.sqlite_filename)
            try:
                c = conn.cursor()
                select = '''SELECT token, host, port, info
                            FROM %s
                            WHERE key=? and key_type=?''' % (DATABASE_TABLE_NAME)
                c.execute(select, (key, key_type,))
                try:
                    token, host, port, info = c.fetchone()
                except TypeError:
                    log.warning('get(): invalid key: %s key_type %s', key, key_type)
                    return None
                return dict(
                    key=key,
                    key_type=key_type,
                    token=token,
                    host=host,
                    port=port,
                    info=info)
            finally:
                conn.close()

    def save(self, key, key_type, token, host, port, info=None):
        """
        Writeout a key, key_type, token, value store that is can be used for coordinating
        with external resources.
        """
        assert key, ValueError("A non-zero length key is required.")
        assert key_type, ValueError("A non-zero length key_type is required.")
        assert token, ValueError("A non-zero length token is required.")
        with FileLock(self.sqlite_filename):
            conn = sqlite3.connect(self.sqlite_filename)
            try:
                c = conn.cursor()
                try:
                    # Create table
                    c.execute('''CREATE TABLE %s
                                 (key text,
                                  key_type text,
                                  token text,
                                  host text,
                                  port integer,
                                  info text,
                                  PRIMARY KEY (key, key_type)
                                  )''' % (DATABASE_TABLE_NAME))
                except Exception:
                    pass
                delete = '''DELETE FROM %s WHERE key=? and key_type=?''' % (DATABASE_TABLE_NAME)
                c.execute(delete, (key, key_type,))
                insert = '''INSERT INTO %s
                            (key, key_type, token, host, port, info)
                            VALUES (?, ?, ?, ?, ?, ?)''' % (DATABASE_TABLE_NAME)
                c.execute(insert,
                          (key,
                           key_type,
                           token,
                           host,
                           port,
                           info,
                           ))
                conn.commit()
            finally:
                conn.close()

    def remove(self, **kwd):
        """
        Remove entry from a key, key_type, token, value store that is can be used for coordinating
        with external resources. Remove entries that match all provided key=values
        """
        assert kwd, ValueError("You must provide some values to key upon")
        delete = 'DELETE FROM %s WHERE' % (DATABASE_TABLE_NAME)
        value_list = []
        for i, (key, value) in enumerate(kwd.items()):
            if i != 0:
                delete += ' and'
            delete += ' %s=?' % (key)
            value_list.append(value)
        with FileLock(self.sqlite_filename):
            conn = sqlite3.connect(self.sqlite_filename)
            try:
                c = conn.cursor()
                try:
                    # Delete entry
                    # NB: This does not invalidate in-memory caches used by uwsgi (if any)
                    c.execute(delete, tuple(value_list))
                except Exception as e:
                    log.debug('Error removing entry (%s): %s', delete, e)
                conn.commit()
            finally:
                conn.close()

    def save_entry_point(self, entry_point):
        """Convenience method to easily save an entry_point.
        """
        return self.save(self.encode_id(entry_point.id), entry_point.__class__.__name__.lower(), entry_point.token, entry_point.host, entry_point.port, None)

    def remove_entry_point(self, entry_point):
        """Convenience method to easily remove an entry_point.
        """
        return self.remove(key=self.encode_id(entry_point.id), key_type=entry_point.__class__.__name__.lower())

    def remove_entry_points0(self, entry_points):
        """Convenience method to easily remove entry_points.
        """
        rval = []
        for entry_point in entry_points:
            rval.append(self.remove_entry_point(entry_point))
        return rval

    def remove_realtime0(self, rtt):
        """Convenience method to easily remove a RealTimeTool.
        """
        for ep in rtt.entry_points:
            self.remove_entry_point(ep)


class RealTimeManager(object):
    """
    Manager for dealing with RealTimeTools
    """

    def __init__(self, app):
        self.model = app.model
        self.security = app.security
        self.sa_session = app.model.context
        self.job_manager = app.job_manager
        self.propagator = RealtimeSqlite(app.config.proxy_session_map, app.security.encode_id)

    def create_entry_points(self, job, tool, flush=True):
        for entry in tool.ports:
            ep = self.model.RealTimeToolEntryPoint(job=job, tool_port=entry['port'], entry_url=entry['url'], name=entry['name'])
            self.sa_session.add(ep)
        if flush:
            self.sa_session.flush()

    def configure_entry_point(self, job, tool_port=None, host=None, port=None, protocol=None):
        return self.configure_entry_points(job, {tool_port: dict(tool_port=tool_port, host=host, port=port, protocol=protocol)})

    def configure_entry_points(self, job, ports_dict):
        # There can be multiple entry points that reference the same tool port (could have different entry URLs)
        configured = []
        not_configured = []
        for ep in job.realtimetool_entry_points:
            port_dict = ports_dict.get(ep.tool_port, None)
            if port_dict is None:
                log.error("Did not find port to assign to RealTimeToolEntryPoint by tool port: %s.", ep.tool_port)
                not_configured.append(ep)
            else:
                ep.host = port_dict['host']
                ep.port = port_dict['port']
                ep.protocol = port_dict['protocol']
                ep.configured = True
                self.sa_session.add(ep)
                self.save_entry_point(ep)
                configured.append(ep)
        if configured:
            self.sa_session.flush()
        return dict(not_configured=not_configured, configured=configured)

    def configure_entry_points_raw_docker_ports(self, job, port_text):
        ports_dict = docker_parse_port_text(port_text)
        return self.configure_entry_points(job, ports_dict)

    def save_entry_point(self, entry_point):
        """
        Writeout a key, key_type, token, value store that is used validating access
        """
        self.propagator.save_entry_point(entry_point)

    def create_realtime(self, job, tool):
        # create from initial job
        if job and tool:
            self.create_entry_points(job, tool)
        else:
            log.warning('Called RealTimeManager.create_realtime, but job (%s) or tool (%s) is None', job, tool)

    def get_nonterminal_for_user_by_trans(self, trans):
        if trans.user:
            jobs = trans.sa_session.query(trans.app.model.Job).filter(trans.app.model.Job.user == trans.user)
        else:
            jobs = trans.sa_session.query(trans.app.model.Job).filter(trans.app.model.Job.session_id == trans.get_galaxy_session().id)

        def build_and_apply_filters(query, objects, filter_func):
            if objects is not None:
                if isinstance(objects, string_types):
                    query = query.filter(filter_func(objects))
                elif isinstance(objects, list):
                    t = []
                    for obj in objects:
                        t.append(filter_func(obj))
                    query = query.filter(or_(*t))
            return query
        jobs = build_and_apply_filters(jobs, trans.app.model.Job.non_ready_states, lambda s: trans.app.model.Job.state == s)
        return trans.sa_session.query(trans.app.model.RealTimeToolEntryPoint).filter(trans.app.model.RealTimeToolEntryPoint.job_id.in_([job.id for job in jobs]))

    def can_access_job(self, trans, job):
        if job:
            if trans.user is None:
                galaxy_session = trans.get_galaxy_session()
                if galaxy_session is None or job.session_id != galaxy_session.id:
                    return False
            elif job.user != trans.user:
                return False
        else:
            return False
        return True

    def can_access_entry_point(self, trans, entry_point):
        if entry_point:
            return self.can_access_job(trans, entry_point.job)
        return False

    def can_access_entry_points(self, trans, entry_points):
        for ep in entry_points:
            if not self.can_access_entry_point(trans, ep):
                return False
        return True

    def stop(self, trans, entry_point):
        try:
            self.remove_entry_point(entry_point)
            job = entry_point.job
            if not job.finished:
                log.debug('Stopping Job: %s for RealTimeToolEntryPoint: %s', job, entry_point)
                job.mark_deleted(trans.app.config.track_jobs_in_database)
                # This self.job_manager.stop(job) does nothing without changing job.state, manually or e.g. with .mark_deleted()
                self.job_manager.stop(job)
                trans.sa_session.add(job)
                trans.sa_session.flush()
        except Exception as e:
            log.debug('Unable to stop job for RealTimeToolEntryPoint (%s): %s', entry_point, e)
            return False
        return True

    def remove_realtime0(self, realtime):
        return self.propagator.remove_realtime(realtime)

    def remove_entry_points(self, entry_points):
        if entry_points:
            for entry_point in entry_points:
                self.remove_entry_point(entry_point, flush=False)
            self.sa_session.flush()

    def remove_entry_point(self, entry_point, flush=True):
        entry_point.deleted = True
        self.sa_session.add(entry_point)
        if flush:
            self.sa_session.flush()
        self.propagator.remove_entry_point(entry_point)
