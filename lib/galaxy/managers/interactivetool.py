import json
import logging
import sqlite3
from urllib.parse import (
    urlsplit,
    urlunsplit,
)

from sqlalchemy import (
    or_,
    select,
)

from galaxy import exceptions
from galaxy.model import (
    InteractiveToolEntryPoint,
    Job,
)
from galaxy.model.base import transaction
from galaxy.security.idencoding import IdAsLowercaseAlphanumEncodingHelper
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
                        f"""CREATE TABLE {DATABASE_TABLE_NAME}
                                 (key text,
                                  key_type text,
                                  token text,
                                  host text,
                                  port integer,
                                  info text,
                                  PRIMARY KEY (key, key_type)
                                  )"""
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
                insert = f"""INSERT INTO {DATABASE_TABLE_NAME}
                            (key, key_type, token, host, port, info)
                            VALUES (?, ?, ?, ?, ?, ?)"""
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
            json.dumps(
                {
                    "requires_path_in_url": entry_point.requires_path_in_url,
                    "requires_path_in_header_named": entry_point.requires_path_in_header_named,
                }
            ),
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
        self.encoder = IdAsLowercaseAlphanumEncodingHelper(app.security)
        self.propagator = InteractiveToolSqlite(app.config.interactivetools_map, self.encoder.encode_id)

    def create_entry_points(self, job, tool, entry_points=None, flush=True):
        entry_points = entry_points or tool.ports
        for entry in entry_points:
            ep = self.model.InteractiveToolEntryPoint(
                job=job,
                tool_port=entry["port"],
                entry_url=entry["url"],
                name=entry["name"],
                label=entry["label"],
                requires_domain=entry["requires_domain"],
                requires_path_in_url=entry["requires_path_in_url"],
                requires_path_in_header_named=entry["requires_path_in_header_named"],
            )
            self.sa_session.add(ep)
        if flush:
            with transaction(self.sa_session):
                self.sa_session.commit()

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
            with transaction(self.sa_session):
                self.sa_session.commit()
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
        if trans.user is None and trans.get_galaxy_session() is None:
            return []

        def build_subquery():
            if trans.user:
                stmt = select(Job.id).where(Job.user == trans.user)
            else:
                stmt = select(Job.id).where(Job.session_id == trans.get_galaxy_session().id)
            filters = []
            for state in Job.non_ready_states:
                filters.append(Job.state == state)
            stmt = stmt.where(or_(*filters))
            return stmt.subquery()

        stmt = select(InteractiveToolEntryPoint).where(InteractiveToolEntryPoint.job_id.in_(build_subquery()))
        return trans.sa_session.scalars(stmt)

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
            with transaction(trans.sa_session):
                trans.sa_session.commit()

    def remove_entry_points(self, entry_points):
        if entry_points:
            for entry_point in entry_points:
                self.remove_entry_point(entry_point, flush=False)
            with transaction(self.sa_session):
                self.sa_session.commit()

    def remove_entry_point(self, entry_point, flush=True):
        entry_point.deleted = True
        self.sa_session.add(entry_point)
        if flush:
            with transaction(self.sa_session):
                self.sa_session.commit()
        self.propagator.remove_entry_point(entry_point)

    def target_if_active(self, trans, entry_point):
        if entry_point.active and not entry_point.deleted:
            use_it_proxy_host_cfg = (
                not self.app.config.interactivetools_upstream_proxy and self.app.config.interactivetools_proxy_host
            )

            url_parts = urlsplit(trans.request.host_url)
            url_host = self.app.config.interactivetools_proxy_host if use_it_proxy_host_cfg else trans.request.host
            url_path = url_parts.path

            if entry_point.requires_domain:
                url_host = f"{self.get_entry_point_subdomain(trans, entry_point)}.{url_host}"
                if entry_point.entry_url:
                    url_path = f"{url_path.rstrip('/')}/{entry_point.entry_url.lstrip('/')}"
            else:
                url_path = self.get_entry_point_path(trans, entry_point)
                if not use_it_proxy_host_cfg:
                    return url_path

            return urlunsplit((url_parts.scheme, url_host, url_path, "", ""))

    def _get_entry_point_url_elements(self, trans, entry_point):
        encoder = IdAsLowercaseAlphanumEncodingHelper(trans.security)
        ep_encoded_id = encoder.encode_id(entry_point.id)
        ep_class_id = entry_point.class_id
        ep_prefix = self.app.config.interactivetools_prefix
        ep_token = entry_point.token
        return ep_encoded_id, ep_class_id, ep_prefix, ep_token

    def get_entry_point_subdomain(self, trans, entry_point):
        ep_encoded_id, ep_class_id, ep_prefix, ep_token = self._get_entry_point_url_elements(trans, entry_point)
        return f"{ep_encoded_id}-{ep_token}.{ep_class_id}.{ep_prefix}"

    def get_entry_point_path(self, trans, entry_point):
        url_path = "/"
        if not entry_point.requires_domain:
            ep_encoded_id, ep_class_id, ep_prefix, ep_token = self._get_entry_point_url_elements(trans, entry_point)
            path_parts = [
                part.strip("/")
                for part in (
                    str(self.app.config.interactivetools_base_path),
                    ep_prefix,
                    ep_class_id,
                    ep_encoded_id,
                    ep_token,
                )
            ]
            url_path += "/".join(part for part in path_parts if part) + "/"
        if entry_point.entry_url:
            url_path += entry_point.entry_url.lstrip("/")
        return url_path

    def access_entry_point_target(self, trans, entry_point_id):
        entry_point = trans.sa_session.get(InteractiveToolEntryPoint, entry_point_id)
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
