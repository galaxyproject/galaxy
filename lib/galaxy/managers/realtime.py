import logging
import sqlite3


from six import string_types
from sqlalchemy import or_


from galaxy.util.filelock import FileLock


log = logging.getLogger(__name__)

REALTIMETOOL_DATASET_EXT = 'realtimetool'
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

    def save_entry_point(self, entry_point):
        """Convenience method to easily save an entry_point.
        """
        return self.save(self.encode_id(entry_point.id), entry_point.__class__.__name__.lower(), entry_point.token, entry_point.host, entry_point.port, None)


class RealTimeManager(object):
    """
    Manager for dealing with RealTimeTools
    """

    def __init__(self, app):
        self.model = app.model
        self.security = app.security
        self.propagator = RealtimeSqlite(app.config.proxy_session_map, app.security.encode_id)

    # FIXME: Do we really want to directly associate a single dataset?
    # Probably Not
    def guess_associated_dataset(self, datasets):
        for dataset in datasets:
            dataset = dataset.dataset
            if dataset.ext == REALTIMETOOL_DATASET_EXT:
                return dataset
        return None

    def create_entry_points(self, trans, rtt, tool, flush=True):
        for entry in tool.tool_ports:
            rtt_entry = self.model.RealTimeToolEntryPoint(realtime=rtt, tool_port=entry['port'], entry_url=entry['url'], name=entry['name'])
            trans.sa_session.add(rtt_entry)
        if flush:
            trans.sa_session.flush()

    def configure_entry_point(self, rtt, tool_port=None, host=None, port=None, protocol=None):
        if tool_port is not None:
            tool_port = int(tool_port)
        not_configured = []
        for entry in rtt.entry_points:
            if entry.tool_port == tool_port:
                entry.host = host
                entry.port = port
                entry.protocol = protocol
                entry.configured = True
                self.save_entry_point(entry)
                return entry
            elif not entry.configured:
                not_configured.append(entry)
        # TODO: port not found in entry, add to random one?
        log.warning('tool port not found! %s', str(not_configured))
        return None

    def save_entry_point(self, entry_point):
        """
        Writeout a key, key_type, token, value store that is used validating access
        """
        self.propagator.save_entry_point(entry_point)

    def create_realtime(self, trans, job, tool):
        # create from initial job
        if job:
            realtime_tool = self.model.RealTimeTool(job=job, user=trans.user, session=trans.galaxy_session, dataset=self.guess_associated_dataset(job.get_output_datasets()))
            trans.sa_session.add(realtime_tool)
            if tool:
                self.create_entry_points(trans, realtime_tool, tool, flush=False)
            trans.sa_session.flush()
        else:
            log.warning('Called RealTimeManager.create_realtime, but job is None')

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
        rtts = trans.sa_session.query(trans.app.model.RealTimeTool).filter(trans.app.model.RealTimeTool.job_id.in_([job.id for job in jobs]))
        return trans.sa_session.query(trans.app.model.RealTimeToolEntryPoint).filter(trans.app.model.RealTimeToolEntryPoint.realtime_id.in_([rtt.id for rtt in rtts]))

    def can_access_realtime(self, trans, realtime):
        if realtime:
            if trans.user is None:
                galaxy_session = trans.get_galaxy_session()
                if galaxy_session is None or realtime.session_id != galaxy_session.id:
                    return False
            elif realtime.user != trans.user:
                return False
        else:
            return False
        return True

    def can_access_entry_point(self, trans, entry_point):
        if entry_point:
            return self.can_access_realtime(trans, entry_point.realtime)
        return False

    def stop(self, realtime):
        raise Exception('not implemented')
