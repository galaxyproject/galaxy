import logging
import sqlite3

from sqlalchemy import or_

from galaxy import (
    exceptions,
    model,
)
from galaxy.util.filelock import FileLock

log = logging.getLogger(__name__)

DATABASE_TABLE_NAME = "gxitproxy"


class InteractiveToolSqlite:
    def __init__(self, sqlite_filename, encode_id):
        self.sqlite_filename = sqlite_filename
        self.encode_id = encode_id

    def get(self, key, key_type):
        with FileLock(self.sqlite_filename):
            conn = sqlite3.connect(self.sqlite_filename)
            try:
                c = conn.cursor()
                select = f"""SELECT token, host, port, info
                            FROM {DATABASE_TABLE_NAME}
                            WHERE key=? and key_type=?"""
                c.execute(
                    select,
                    (
                        key,
                        key_type,
                    ),
                )
                try:
                    token, host, port, info = c.fetchone()
                except TypeError:
                    log.warning("get(): invalid key: %s key_type %s", key, key_type)
                    return None
                return dict(key=key, key_type=key_type, token=token, host=host, port=port, info=info)
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
                    c.execute(
                        """CREATE TABLE %s
                                 (key text,
                                  key_type text,
                                  token text,
                                  host text,
                                  port integer,
                                  info text,
                                  PRIMARY KEY (key, key_type)
                                  )"""
                        % (DATABASE_TABLE_NAME)
                    )
                except Exception:
                    pass
                delete = f"""DELETE FROM {DATABASE_TABLE_NAME} WHERE key=? and key_type=?"""
                c.execute(
                    delete,
                    (
                        key,
                        key_type,
                    ),
                )
                insert = """INSERT INTO %s
                            (key, key_type, token, host, port, info)
                            VALUES (?, ?, ?, ?, ?, ?)""" % (
                    DATABASE_TABLE_NAME
                )
                c.execute(
                    insert,
                    (
                        key,
                        key_type,
                        token,
                        host,
                        port,
                        info,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def remove(self, **kwd):
        """
        Remove entry from a key, key_type, token, value store that is can be used for coordinating
        with external resources. Remove entries that match all provided key=values
        """
        assert kwd, ValueError("You must provide some values to key upon")
        delete = f"DELETE FROM {DATABASE_TABLE_NAME} WHERE"
        value_list = []
        for i, (key, value) in enumerate(kwd.items()):
            if i != 0:
                delete += " and"
            delete += f" {key}=?"
            value_list.append(value)
        with FileLock(self.sqlite_filename):
            conn = sqlite3.connect(self.sqlite_filename)
            try:
                c = conn.cursor()
                try:
                    # Delete entry
                    c.execute(delete, tuple(value_list))
                except Exception as e:
                    log.debug("Error removing entry (%s): %s", delete, e)
                conn.commit()
            finally:
                conn.close()

    def save_entry_point(self, entry_point):
        """Convenience method to easily save an entry_point."""
        return self.save(
            self.encode_id(entry_point.id),
            entry_point.__class__.__name__.lower(),
            entry_point.token,
            entry_point.host,
            entry_point.port,
            None,
        )

    def remove_entry_point(self, entry_point):
        """Convenience method to easily remove an entry_point."""
        return self.remove(key=self.encode_id(entry_point.id), key_type=entry_point.__class__.__name__.lower())


class InteractiveToolManager:
    """
    Manager for dealing with InteractiveTools
    """

    def __init__(self, app):
        self.app = app
        self.model = app.model
        self.security = app.security
        self.sa_session = app.model.context
        self.job_manager = app.job_manager
        self.propagator = InteractiveToolSqlite(app.config.interactivetools_map, app.security.encode_id)

    def create_entry_points(self, job, tool, entry_points=None, flush=True):
        entry_points = entry_points or tool.ports
        for entry in entry_points:
            ep = self.model.InteractiveToolEntryPoint(
                job=job,
                tool_port=entry["port"],
                entry_url=entry["url"],
                name=entry["name"],
                requires_domain=entry["requires_domain"],
                short_token=self.app.config.interactivetools_shorten_url,
            )
            self.sa_session.add(ep)
        if flush:
            self.sa_session.flush()

    def configure_entry_point(self, job, tool_port=None, host=None, port=None, protocol=None):
        return self.configure_entry_points(
            job, {tool_port: dict(tool_port=tool_port, host=host, port=port, protocol=protocol)}
        )

    def configure_entry_points(self, job, ports_dict):
        # There can be multiple entry points that reference the same tool port (could have different entry URLs)
        configured = []
        not_configured = []
        for ep in job.interactivetool_entry_points:
            port_dict = ports_dict.get(str(ep.tool_port), None)
            if port_dict is None:
                log.error("Did not find port to assign to InteractiveToolEntryPoint by tool port: %s.", ep.tool_port)
                not_configured.append(ep)
            else:
                ep.host = port_dict["host"]
                ep.port = port_dict["port"]
                ep.protocol = port_dict["protocol"]
                ep.configured = True
                self.sa_session.add(ep)
                self.save_entry_point(ep)
                configured.append(ep)
        if configured:
            self.sa_session.flush()
        return dict(not_configured=not_configured, configured=configured)

    def save_entry_point(self, entry_point):
        """
        Writeout a key, key_type, token, value store that is used validating access
        """
        self.propagator.save_entry_point(entry_point)

    def create_interactivetool(self, job, tool, entry_points):
        # create from initial job
        if job and tool:
            self.create_entry_points(job, tool, entry_points)
        else:
            log.warning(
                "Called InteractiveToolManager.create_interactivetool, but job (%s) or tool (%s) is None", job, tool
            )

    def get_nonterminal_for_user_by_trans(self, trans):
        if trans.user:
            jobs = trans.sa_session.query(trans.app.model.Job).filter(trans.app.model.Job.user == trans.user)
        else:
            jobs = trans.sa_session.query(trans.app.model.Job).filter(
                trans.app.model.Job.session_id == trans.get_galaxy_session().id
            )

        def build_and_apply_filters(query, objects, filter_func):
            if objects is not None:
                if isinstance(objects, str):
                    query = query.filter(filter_func(objects))
                elif isinstance(objects, list):
                    t = []
                    for obj in objects:
                        t.append(filter_func(obj))
                    query = query.filter(or_(*t))
            return query

        jobs = build_and_apply_filters(
            jobs, trans.app.model.Job.non_ready_states, lambda s: trans.app.model.Job.state == s
        )
        return trans.sa_session.query(trans.app.model.InteractiveToolEntryPoint).filter(
            trans.app.model.InteractiveToolEntryPoint.job_id.in_([job.id for job in jobs])
        )

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
        self.remove_entry_point(entry_point)
        job = entry_point.job
        if not job.finished:
            log.debug("Stopping Job: %s for InteractiveToolEntryPoint: %s", job, entry_point)
            job.mark_stopped(trans.app.config.track_jobs_in_database)
            # This self.job_manager.stop(job) does nothing without changing job.state, manually or e.g. with .mark_deleted()
            self.job_manager.stop(job)
            trans.sa_session.add(job)
            trans.sa_session.flush()

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

    def target_if_active(self, trans, entry_point):
        if entry_point.active and not entry_point.deleted:
            request_host = trans.request.host
            if not self.app.config.interactivetools_upstream_proxy and self.app.config.interactivetools_proxy_host:
                request_host = self.app.config.interactivetools_proxy_host
            protocol = trans.request.host_url.split("//", 1)[0]
            if entry_point.requires_domain:
                rval = f"{protocol}//{self.get_entry_point_subdomain(trans, entry_point)}.{request_host}/"
                if entry_point.entry_url:
                    rval = "{}/{}".format(rval.rstrip("/"), entry_point.entry_url.lstrip("/"))
            else:
                rval = self.get_entry_point_path(trans, entry_point)

            return rval

    def get_entry_point_subdomain(self, trans, entry_point):
        entry_point_encoded_id = trans.security.encode_id(entry_point.id)
        entry_point_class = entry_point.__class__.__name__.lower()
        entry_point_prefix = self.app.config.interactivetools_prefix
        entry_point_token = entry_point.token
        if self.app.config.interactivetools_shorten_url:
            return f"{entry_point_encoded_id}-{entry_point_token[:10]}.{entry_point_prefix}"
        return f"{entry_point_encoded_id}-{entry_point_token}.{entry_point_class}.{entry_point_prefix}"

    def get_entry_point_path(self, trans, entry_point):
        entry_point_encoded_id = trans.security.encode_id(entry_point.id)
        entry_point_class = entry_point.__class__.__name__.lower()
        entry_point_prefix = self.app.config.interactivetools_prefix
        rval = "/"
        if not entry_point.requires_domain:
            rval = str(self.app.config.interactivetools_base_path).rstrip("/").lstrip("/")
            if self.app.config.interactivetools_shorten_url:
                rval = f"/{rval}/{entry_point_prefix}/{entry_point_encoded_id}/{entry_point.token[:10]}/"
            else:
                rval = f"/{rval}/{entry_point_prefix}/access/{entry_point_class}/{entry_point_encoded_id}/{entry_point.token}/"
        if entry_point.entry_url:
            rval = f"{rval.rstrip('/')}/{entry_point.entry_url.lstrip('/')}"
        if rval[0] != "/":
            rval = f"/{rval}"
        return rval

    def access_entry_point_target(self, trans, entry_point_id):
        entry_point = trans.sa_session.query(model.InteractiveToolEntryPoint).get(entry_point_id)
        if self.app.interactivetool_manager.can_access_entry_point(trans, entry_point):
            if entry_point.active:
                return self.target_if_active(trans, entry_point)
            elif entry_point.deleted:
                raise exceptions.MessageException("InteractiveTool has ended. You will have to start a new one.")
            else:
                raise exceptions.MessageException(
                    "InteractiveTool is not active. If you recently launched this tool it may not be ready yet, please wait a moment and refresh this page."
                )
        raise exceptions.ItemAccessibilityException("You do not have access to this InteractiveTool entry point.")
