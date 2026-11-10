import argparse
import datetime
import math
import os
import signal
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from types import FrameType

from sqlalchemy import (
    bindparam,
    create_engine,
    event,
    text,
)
from sqlalchemy.engine import (
    Connection,
    Engine,
)
from sqlalchemy.exc import SQLAlchemyError

sys.path.insert(
    1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir, os.pardir, "lib"))
)

from galaxy.model.orm.scripts import get_config
from galaxy.util.script import populate_config_args

DESCRIPTION = """Remove old galaxy_session records in bounded, separately committed pages.

Age does not prove disuse. By default, anonymous sessions linked to histories are
eligible too; use --preserve-anonymous-histories to protect those references.
Use --preserve-sessions-with-jobs to keep sessions referenced by jobs without a user.
Registered users' newest sessions are always protected. NULL update times are kept.
"""


def main() -> int:
    args = _get_parser().parse_args()
    if args.through_id is not None and args.through_id < args.after_id:
        _get_parser().error("--through-id must be >= --after-id")
    config_argv = [sys.argv[0]]
    if args.config_file:
        config_argv.extend(["--config-file", args.config_file])
    if args.config_section:
        config_argv.extend(["--config-section", args.config_section])
    config = get_config(config_argv, use_argparse=False, cwd=os.getcwd())
    options = vars(args)
    for name in ("config_file", "config_section"):
        options.pop(name, None)
    options["max_update_time"] = options.pop("updated")
    engine = create_engine(config["db_url"], hide_parameters=True)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(dbapi_connection, connection_record):
            # SQLite otherwise skips the session foreign keys' CASCADE/SET NULL.
            dbapi_connection.execute("PRAGMA foreign_keys = ON")

    previous_handler = signal.signal(signal.SIGTERM, _interrupt)
    try:
        run(engine, **options)
    except KeyboardInterrupt:
        return 130
    except SQLAlchemyError as exc:
        # SQLAlchemy exceptions can contain SQL parameters or connection details.
        code = getattr(getattr(exc, "orig", None), "sqlstate", None) or getattr(
            getattr(exc, "orig", None), "pgcode", None
        )
        print(f"Cleanup failed ({type(exc).__name__}, SQLSTATE={code}); see committed progress above.", file=sys.stderr)
        return 1
    finally:
        signal.signal(signal.SIGTERM, previous_handler)
        engine.dispose()
    return 0


def _interrupt(signum: int, frame: FrameType | None) -> None:
    raise KeyboardInterrupt


def _positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def _nonnegative_int(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be a nonnegative integer")
    return number


def _pause(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("must be finite and nonnegative")
    return number


def _cutoff(value: str) -> datetime.datetime:
    cutoff = datetime.datetime.fromisoformat(value)
    if cutoff.tzinfo is not None:
        raise argparse.ArgumentTypeError("use a timezone-naive cutoff, matching galaxy_session.update_time")
    return cutoff


def _get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=DESCRIPTION, formatter_class=argparse.RawDescriptionHelpFormatter)
    populate_config_args(parser)
    parser.add_argument(
        "--updated", type=_cutoff, help="exclusive ISO cutoff; default: local date.today() minus 30 days"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="SELECT-only preview (PostgreSQL read-only transactions)"
    )
    parser.add_argument(
        "--batch-size", type=_positive_int, default=1000, help="maximum sessions scanned per page (default: 1000)"
    )
    parser.add_argument(
        "--max-batches", type=_positive_int, help="stop after this many scanned pages, including empty eligible pages"
    )
    parser.add_argument("--pause", type=_pause, default=0.1, help="seconds between transactions (default: 0.1)")
    parser.add_argument("--anonymous-only", action="store_true", help="only delete anonymous sessions")
    parser.add_argument(
        "--preserve-anonymous-histories",
        action="store_true",
        help="keep anonymous sessions with current_history_id or any session/history association (default: off)",
    )
    parser.add_argument(
        "--preserve-sessions-with-jobs",
        action="store_true",
        help="keep sessions referenced by jobs with no user_id, regardless of state (default: off)",
    )
    parser.add_argument(
        "--after-id", type=_nonnegative_int, default=0, help="resume scanning strictly after this ID (default: 0)"
    )
    parser.add_argument("--through-id", type=_nonnegative_int, help="upper ID boundary; default: maximum ID at start")
    parser.add_argument(
        "--statement-timeout",
        type=_positive_int,
        default=30000,
        help="PostgreSQL per-statement timeout in ms (default: 30000)",
    )
    parser.add_argument(
        "--lock-timeout", type=_positive_int, default=1000, help="PostgreSQL lock timeout in ms (default: 1000)"
    )
    return parser


# Materialize one newest-session result per distinct candidate-page user. Without
# this boundary, a planner can repeat the user-index scan for every candidate.
# Both preview and DELETE compute this afresh within their statement snapshot.
NEWEST_SESSIONS = """
    WITH newest_sessions AS MATERIALIZED (
        SELECT users.user_id, (
            SELECT newer.id FROM galaxy_session newer
            WHERE newer.user_id = users.user_id
            ORDER BY newer.update_time DESC NULLS LAST, newer.id DESC LIMIT 1
        ) AS id
        FROM (
            SELECT DISTINCT user_id FROM galaxy_session
            WHERE id IN :ids AND user_id IS NOT NULL AND update_time < :update_time
        ) users
    )
"""

# Keep this ordering aligned with User.current_galaxy_session. Checking the owner
# as well as the ID fails closed if a locked target is reassigned to a user absent
# from the statement's page snapshot. Other-row snapshot races still apply.
ELIGIBILITY = """
    s.update_time < :update_time
    AND (s.user_id IS NULL OR EXISTS (
        SELECT 1 FROM newest_sessions newest
        WHERE newest.user_id = s.user_id AND newest.id <> s.id
    ))
"""


def _eligibility(
    anonymous_only: bool, preserve_anonymous_histories: bool, preserve_sessions_with_jobs: bool = False
) -> str:
    predicate = ELIGIBILITY
    if anonymous_only:
        # Avoid registered-user lookups entirely in this operational scope.
        predicate = "s.update_time < :update_time AND s.user_id IS NULL"
    if preserve_anonymous_histories:
        predicate += """
            AND (s.user_id IS NOT NULL OR (
                s.current_history_id IS NULL AND NOT EXISTS (
                    SELECT 1 FROM galaxy_session_to_history h WHERE h.session_id = s.id
                )
            ))
        """
    if preserve_sessions_with_jobs:
        predicate += " AND NOT EXISTS (SELECT 1 FROM job j WHERE j.session_id = s.id AND j.user_id IS NULL)"
    return predicate


def _eligible_ids(conn: Connection, ids: list[int], predicate: str, cutoff: datetime.date) -> list[int]:
    stmt = text(f"{NEWEST_SESSIONS} SELECT s.id FROM galaxy_session s WHERE s.id IN :ids AND {predicate} ORDER BY s.id")
    return list(conn.scalars(stmt.bindparams(bindparam("ids", expanding=True)), {"ids": ids, "update_time": cutoff}))


def _delete_batch(conn: Connection, ids: list[int], predicate: str, cutoff: datetime.date) -> int:
    # Re-evaluate age, ownership, newest-session, history and job protection at DELETE
    # time, rather than deleting the previously selected IDs unconditionally.
    stmt = text(f"{NEWEST_SESSIONS} DELETE FROM galaxy_session AS s WHERE s.id IN :ids AND {predicate} RETURNING id")
    # SQLite reports rowcount=-1 for WITH-prefixed DML. RETURNING counts actual
    # deletions reliably on both backends, with at most one page in memory.
    return len(
        list(conn.scalars(stmt.bindparams(bindparam("ids", expanding=True)), {"ids": ids, "update_time": cutoff}))
    )


@contextmanager
def _transaction(engine: Engine, dry_run: bool, statement_timeout: int, lock_timeout: int) -> Iterator[Connection]:
    with engine.connect() as conn:
        if engine.dialect.name == "postgresql":
            conn = conn.execution_options(isolation_level="READ COMMITTED")
        with conn.begin():
            if engine.dialect.name == "sqlite":
                dbapi = conn.connection.driver_connection
                assert dbapi is not None
                if not dbapi.in_transaction:
                    # sqlite3's legacy mode does not BEGIN for WITH DML. Ensure
                    # a failing CTE DELETE rolls back with the rest of its page.
                    conn.exec_driver_sql("BEGIN")
            if engine.dialect.name == "postgresql":
                if dry_run:
                    conn.execute(text("SET TRANSACTION READ ONLY"))
                conn.execute(
                    text("SELECT set_config('statement_timeout', :value, true)"), {"value": f"{statement_timeout}ms"}
                )
                conn.execute(text("SELECT set_config('lock_timeout', :value, true)"), {"value": f"{lock_timeout}ms"})
            yield conn


@dataclass
class Progress:
    batches: int = 0
    scanned: int = 0
    selected: int = 0
    deleted: int = 0
    would_delete: int = 0
    after_id: int = 0
    through_id: int = 0
    status: str = "starting"

    def report(self) -> str:
        return " ".join(f"{name}={value}" for name, value in vars(self).items())


def run(
    engine: Engine,
    max_update_time: datetime.date | None = None,
    *,
    batch_size: int = 1000,
    max_batches: int | None = None,
    pause: float = 0.1,
    dry_run: bool = False,
    anonymous_only: bool = False,
    preserve_anonymous_histories: bool = False,
    preserve_sessions_with_jobs: bool = False,
    after_id: int = 0,
    through_id: int | None = None,
    statement_timeout: int = 30000,
    lock_timeout: int = 1000,
) -> Progress:
    """Scan a finite ID window; return progress for committed pages only.

    Restart with the reported after_id/through_id and the same cutoff/policy, or
    scan from the beginning to reconsider rows skipped due to concurrent changes.
    A preview is a sequence of observations, not a reservation of future deletes.
    """
    for name, value in (
        ("batch_size", batch_size),
        ("statement_timeout", statement_timeout),
        ("lock_timeout", lock_timeout),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    if max_batches is not None and (
        not isinstance(max_batches, int) or isinstance(max_batches, bool) or max_batches <= 0
    ):
        raise ValueError("max_batches must be a positive integer")
    if not math.isfinite(pause) or pause < 0:
        raise ValueError("pause must be finite and nonnegative")
    if not isinstance(after_id, int) or isinstance(after_id, bool) or after_id < 0:
        raise ValueError("after_id must be a nonnegative integer")
    if through_id is not None and (
        not isinstance(through_id, int) or isinstance(through_id, bool) or through_id < after_id
    ):
        raise ValueError("through_id must be an integer >= after_id")
    cutoff = max_update_time or _get_default_max_update_time()
    if isinstance(cutoff, datetime.datetime) and cutoff.tzinfo is not None:
        raise ValueError("use a timezone-naive cutoff")
    if engine.dialect.name not in ("postgresql", "sqlite"):
        raise ValueError("session cleanup supports PostgreSQL and SQLite")
    predicate = _eligibility(anonymous_only, preserve_anonymous_histories, preserve_sessions_with_jobs)
    progress = Progress(after_id=after_id)
    print(
        f"cutoff={cutoff.isoformat()} dry_run={dry_run} anonymous_only={anonymous_only} "
        f"preserve_anonymous_histories={preserve_anonymous_histories} "
        f"preserve_sessions_with_jobs={preserve_sessions_with_jobs} "
        f"batch_size={batch_size} max_batches={max_batches} pause={pause} "
        f"statement_timeout_ms={statement_timeout} lock_timeout_ms={lock_timeout}",
        flush=True,
    )
    if engine.dialect.name == "sqlite":
        print("SQLite: PostgreSQL timeout controls and enforced read-only transactions are unavailable.", flush=True)
    try:
        with _transaction(engine, dry_run, statement_timeout, lock_timeout) as conn:
            maximum = conn.scalar(text("SELECT id FROM galaxy_session ORDER BY id DESC LIMIT 1")) or 0
        progress.through_id = min(maximum, through_id) if through_id is not None else maximum
        progress.status = "running"
        print(progress.report(), flush=True)
        while progress.after_id < progress.through_id:
            with _transaction(engine, dry_run, statement_timeout, lock_timeout) as conn:
                # LIMIT bounds scanned rows, not eligible rows: even an entirely
                # protected page advances the cursor. The PK supports this seek.
                ids = list(
                    conn.scalars(
                        text("""
                    SELECT id FROM galaxy_session
                    WHERE id > :after_id AND id <= :through_id ORDER BY id LIMIT :batch_size
                """),
                        {"after_id": progress.after_id, "through_id": progress.through_id, "batch_size": batch_size},
                    )
                )
                selected = _eligible_ids(conn, ids, predicate, cutoff) if ids else []
                deleted = _delete_batch(conn, selected, predicate, cutoff) if selected and not dry_run else 0
            # Publish only after commit. A failed page must be scanned again.
            if not ids:
                progress.after_id = progress.through_id
                break
            progress.batches += 1
            progress.scanned += len(ids)
            progress.selected += len(selected)
            progress.deleted += deleted
            progress.would_delete += len(selected) if dry_run else 0
            progress.after_id = ids[-1]
            print(progress.report(), flush=True)
            if progress.after_id >= progress.through_id:
                break
            if max_batches is not None and progress.batches >= max_batches:
                progress.status = "limited"
                break
            # No transaction or connection is held while pacing.
            if pause:
                time.sleep(pause)
        if progress.status == "running":
            progress.status = "complete"
    except KeyboardInterrupt:
        progress.status = "interrupted"
        raise
    except Exception:
        progress.status = "failed"
        raise
    finally:
        print(progress.report(), flush=True)
    return progress


def _get_default_max_update_time(today: datetime.date | None = None) -> datetime.date:
    """Preserve the original local-date, exclusive cutoff semantics."""
    today = today or datetime.date.today()
    return today - datetime.timedelta(days=30)


if __name__ == "__main__":
    sys.exit(main())
