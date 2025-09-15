import json
import logging
from collections.abc import (
    Callable,
    Iterable,
)
from typing import (
    Any,
    TYPE_CHECKING,
    Union,
)
from urllib.parse import (
    urlsplit,
    urlunsplit,
)

from sqlalchemy import (
    Column,
    create_engine,
    delete,
    insert,
    Integer,
    MetaData,
    select,
    String,
    Table,
    Text,
)

from galaxy import exceptions
from galaxy.model import (
    InteractiveToolEntryPoint,
    Job,
)
from galaxy.security.idencoding import IdAsLowercaseAlphanumEncodingHelper

if TYPE_CHECKING:
    from galaxy.managers.context import ProvidesUserContext
    from galaxy.structured_app import MinimalManagerApp
    from galaxy.tools import Tool

log = logging.getLogger(__name__)

gxitproxy = Table(
    "gxitproxy",
    MetaData(),
    Column("key", String(16), primary_key=True),
    Column("key_type", Text(), primary_key=True),
    Column("token", String(32)),
    Column("host", Text()),
    Column("port", Integer()),
    Column("info", Text()),
)


class InteractiveToolPropagatorSQLAlchemy:
    """
    Propagator for InteractiveToolManager implemented using SQLAlchemy.
    """

    def __init__(self, database_url: str, encode_id: Callable[[int], str]) -> None:
        """
        Constructor that sets up the propagator using a SQLAlchemy database URL.

        :param database_url: SQLAlchemy database URL, read more on the SQLAlchemy documentation
                             https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls.
        :param encode_id: A helper class that can encode ids as lowercase alphanumeric strings and vice versa.
        """
        self._engine = create_engine(database_url)
        self._encode_id = encode_id

    def save(
        self,
        key: str,
        key_type: str,
        token: Union[str, None],
        host: Union[str, None],
        port: Union[int, None],
        info: Union[str, None] = None,
    ) -> None:
        """
        Write out a key, key_type, token, value store that is can be used for coordinating with external resources.
        """
        assert key, ValueError("A non-zero length key is required.")
        assert key_type, ValueError("A non-zero length key_type is required.")
        assert token, ValueError("A non-zero length token is required.")
        with self._engine.connect() as conn:
            # create database table if not exists
            gxitproxy.create(conn, checkfirst=True)

            # delete existing data with same key
            stmt_delete = delete(gxitproxy).where(
                gxitproxy.c.key == key,
                gxitproxy.c.key_type == key_type,
            )
            conn.execute(stmt_delete)

            # save data
            stmt_insert = insert(gxitproxy).values(
                key=key,
                key_type=key_type,
                token=token,
                host=host,
                port=port,
                info=info,
            )
            conn.execute(stmt_insert)

            conn.commit()

    def remove(self, **kwd) -> None:
        """
        Remove entry from a key, key_type, token, value store that is can be used for coordinating
        with external resources. Remove entries that match all provided key=values
        """
        assert kwd, ValueError("You must provide some values to key upon")
        with self._engine.connect() as conn:
            stmt = delete(gxitproxy).where(
                *(gxitproxy.c[key] == value for key, value in kwd.items()),
            )
            conn.execute(stmt)
            conn.commit()

    def save_entry_point(self, entry_point: InteractiveToolEntryPoint) -> None:
        """Convenience method to easily save an entry_point."""
        return self.save(
            self._encode_id(entry_point.id),
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

    def remove_entry_point(self, entry_point: InteractiveToolEntryPoint) -> None:
        """Convenience method to easily remove an entry_point."""
        return self.remove(key=self._encode_id(entry_point.id), key_type=entry_point.__class__.__name__.lower())


class InteractiveToolManager:
    """
    Manager for dealing with InteractiveTools
    """

    def __init__(self, app: "MinimalManagerApp") -> None:
        self.app = app
        self.security = app.security
        self.sa_session = app.model.context
        self.job_manager = app.job_manager
        self.encoder = IdAsLowercaseAlphanumEncodingHelper(app.security)
        self.propagator = InteractiveToolPropagatorSQLAlchemy(
            app.config.interactivetoolsproxy_map or app.config.interactivetools_map,
            self.encoder.encode_id,
        )

    def create_entry_points(
        self, job: Job, tool: "Tool", entry_points=Union[Iterable[dict[str, Any]], None], flush: bool = True
    ) -> None:
        entry_points = entry_points or tool.ports
        for entry in entry_points:
            ep = InteractiveToolEntryPoint(
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
            self.sa_session.commit()

    def configure_entry_points(
        self, job: Job, ports_dict: dict[str, dict]
    ) -> dict[str, list[InteractiveToolEntryPoint]]:
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
            self.sa_session.commit()
        return dict(not_configured=not_configured, configured=configured)

    def save_entry_point(self, entry_point: InteractiveToolEntryPoint) -> None:
        """
        Writeout a key, key_type, token, value store that is used validating access
        """
        self.propagator.save_entry_point(entry_point)

    def create_interactivetool(self, job: Job, tool: "Tool", entry_points: Iterable[dict[str, Any]]) -> None:
        # create from initial job
        if job and tool:
            self.create_entry_points(job, tool, entry_points)
        else:
            log.warning(
                "Called InteractiveToolManager.create_interactivetool, but job (%s) or tool (%s) is None", job, tool
            )

    def get_nonterminal_for_user_by_trans(self, trans: "ProvidesUserContext") -> list[InteractiveToolEntryPoint]:
        if trans.user is None and trans.galaxy_session is None:
            return []

        stmt = (
            select(InteractiveToolEntryPoint)
            .join(Job, InteractiveToolEntryPoint.job_id == Job.id)
            .where(Job.state.in_(Job.non_ready_states))
        )
        if trans.user is not None:
            stmt = stmt.where(Job.user == trans.user)
        else:
            assert trans.galaxy_session is not None  # help mypy
            stmt = stmt.where(Job.session_id == trans.galaxy_session.id)
        return trans.sa_session.scalars(stmt)

    def can_access_job(self, trans: "ProvidesUserContext", job: Union[Job, None]) -> bool:
        if job:
            if trans.user is None:
                galaxy_session = trans.galaxy_session
                if galaxy_session is None or job.session_id != galaxy_session.id:
                    return False
            elif job.user != trans.user:
                return False
        else:
            return False
        return True

    def can_access_entry_point(self, trans: "ProvidesUserContext", entry_point: InteractiveToolEntryPoint) -> bool:
        if entry_point:
            return self.can_access_job(trans, entry_point.job)
        return False

    def can_access_entry_points(
        self, trans: "ProvidesUserContext", entry_points: Iterable[InteractiveToolEntryPoint]
    ) -> bool:
        for ep in entry_points:
            if not self.can_access_entry_point(trans, ep):
                return False
        return True

    def stop(self, trans: "ProvidesUserContext", entry_point: InteractiveToolEntryPoint) -> None:
        self.remove_entry_point(entry_point)
        job = entry_point.job
        if job and not job.finished:
            log.debug("Stopping Job: %s for InteractiveToolEntryPoint: %s", job, entry_point)
            job.mark_stopped(trans.app.config.track_jobs_in_database)
            # This self.job_manager.stop(job) does nothing without changing job.state, manually or e.g. with .mark_deleted()
            self.job_manager.stop(job)
            trans.sa_session.add(job)
            trans.sa_session.commit()

    def remove_entry_points(self, entry_points: Iterable[InteractiveToolEntryPoint]) -> None:
        if entry_points:
            for entry_point in entry_points:
                self.remove_entry_point(entry_point, flush=False)
            self.sa_session.commit()

    def remove_entry_point(self, entry_point: InteractiveToolEntryPoint, flush: bool = True) -> None:
        entry_point.deleted = True
        self.sa_session.add(entry_point)
        if flush:
            self.sa_session.commit()
        self.propagator.remove_entry_point(entry_point)

    def target_if_active(self, trans, entry_point: InteractiveToolEntryPoint) -> Union[str, None]:
        if entry_point.active and not entry_point.deleted:
            use_it_proxy_host_cfg = (
                not self.app.config.interactivetools_upstream_proxy and self.app.config.interactivetools_proxy_host
            )

            url_parts = urlsplit(trans.request.host_url)
            url_host = self.app.config.interactivetools_proxy_host if use_it_proxy_host_cfg else trans.request.host
            url_path = url_parts.path

            if entry_point.requires_domain:
                url_host = f"{self.get_entry_point_subdomain(entry_point)}.{url_host}"
                if entry_point.entry_url:
                    url_path = f"{url_path.rstrip('/')}/{entry_point.entry_url.lstrip('/')}"
            else:
                url_path = self.get_entry_point_path(entry_point)
                if not use_it_proxy_host_cfg:
                    return url_path

            return urlunsplit((url_parts.scheme, url_host, url_path, "", ""))
        return None

    def _get_entry_point_url_elements(self, entry_point: InteractiveToolEntryPoint) -> tuple[str, str, str, str]:
        encoder = IdAsLowercaseAlphanumEncodingHelper(self.app.security)
        ep_encoded_id = encoder.encode_id(entry_point.id)
        ep_class_id = entry_point.class_id
        ep_prefix = self.app.config.interactivetools_prefix
        ep_token = entry_point.token
        return ep_encoded_id, ep_class_id, ep_prefix, ep_token

    def get_entry_point_subdomain(self, entry_point: InteractiveToolEntryPoint) -> str:
        ep_encoded_id, ep_class_id, ep_prefix, ep_token = self._get_entry_point_url_elements(entry_point)
        return f"{ep_encoded_id}-{ep_token}.{ep_class_id}.{ep_prefix}"

    def get_entry_point_path(self, entry_point: InteractiveToolEntryPoint) -> str:
        url_path = "/"
        if not entry_point.requires_domain:
            ep_encoded_id, ep_class_id, ep_prefix, ep_token = self._get_entry_point_url_elements(entry_point)
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

    def access_entry_point_target(self, trans: "ProvidesUserContext", entry_point_id: int) -> Union[str, None]:
        entry_point = self.sa_session.get(InteractiveToolEntryPoint, entry_point_id)
        assert entry_point
        if self.can_access_entry_point(trans, entry_point):
            if entry_point.active:
                return self.target_if_active(trans, entry_point)
            elif entry_point.deleted:
                raise exceptions.MessageException("InteractiveTool has ended. You will have to start a new one.")
            else:
                raise exceptions.MessageException(
                    "InteractiveTool is not active. If you recently launched this tool it may not be ready yet, please wait a moment and refresh this page."
                )
        raise exceptions.ItemAccessibilityException("You do not have access to this InteractiveTool entry point.")
