"""Shared ``ToolSource`` lookup-or-create helper.

A ``ToolSource`` row is content+identity-addressable: the same persisted tool
source (XML, or JSON for CWL) under the same parser class and execution
identity corresponds to one row. Distinct dynamic-tool rows can therefore carry
identical source text without one request later queueing with the other's
``DynamicTool``.

``ToolSource`` carries ``UniqueConstraint("hash", "source_class",
"identity_hash")``, so even under concurrent inserts (PostgreSQL) at most one
row survives; :func:`get_or_create_tool_source` scopes its insert in a savepoint
and, on the unique-violation race, rolls back just that savepoint and returns
the winner. Scoping to a savepoint (rather than a full session rollback) keeps
the helper safe to call from within an enclosing transaction or savepoint.
"""

import hashlib
import logging
from typing import (
    Any,
    Optional,
)

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from galaxy.model import ToolSource

log = logging.getLogger(__name__)


def get_or_create_tool_source(session: Session, tool) -> ToolSource:
    """Return a ``ToolSource`` row matching the tool's persisted source content
    and execution identity, creating one only when no equivalent row exists."""
    source_str = tool.tool_source.to_string()
    source_class = type(tool.tool_source).__name__
    content_hash = hashlib.sha256(source_str.encode("utf-8")).hexdigest()
    identity_hash = tool_source_identity_hash(tool)
    existing = _lookup(session, content_hash, source_class, identity_hash)
    if existing is not None:
        return existing
    tool_source = ToolSource(
        source=source_str,
        source_class=source_class,
        hash=content_hash,
        identity_hash=identity_hash,
        tool_id=tool.id,
        tool_version=tool.version,
        dynamic_tool_id=tool.dynamic_tool.id if tool.dynamic_tool else None,
    )
    try:
        with session.begin_nested():
            session.add(tool_source)
            session.flush()
    except IntegrityError:
        # Concurrent writer won the race. The savepoint rolled back only our
        # insert, leaving the surrounding transaction intact (a full
        # session.rollback() here would deactivate an enclosing savepoint in
        # callers that wrap us in begin_nested()). The unique constraint
        # guarantees a row exists now, so return theirs.
        winner = _lookup(session, content_hash, source_class, identity_hash)
        if winner is None:
            raise
        return winner
    return tool_source


def tool_source_identity_hash(tool: Any) -> str:
    dynamic_tool = getattr(tool, "dynamic_tool", None)
    identity: tuple[str, ...]
    if dynamic_tool is not None and dynamic_tool.id is not None:
        identity = ("dynamic", str(dynamic_tool.id))
    else:
        identity = ("static", tool.id or "", tool.version or "")
    return hashlib.sha256("\0".join(identity).encode("utf-8")).hexdigest()


def _lookup(session: Session, content_hash: str, source_class: str, identity_hash: str) -> Optional[ToolSource]:
    return session.scalars(
        select(ToolSource)
        .where(
            ToolSource.hash == content_hash,
            ToolSource.source_class == source_class,
            ToolSource.identity_hash == identity_hash,
        )
        .limit(1)
    ).first()
