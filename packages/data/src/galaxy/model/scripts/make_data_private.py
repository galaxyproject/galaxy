import argparse
import logging
import os
import re
import sys
from collections.abc import (
    Callable,
    Iterator,
)

from sqlalchemy import (
    bindparam,
    Connection,
    create_engine,
    Engine,
    text,
    TextClause,
)

from galaxy.model.orm.scripts import get_config
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.util import now
from galaxy.util.properties import load_app_properties
from galaxy.util.script import populate_config_args

DESCRIPTION = """Make existing users' data private by default.

Restricts access to each user's private role for:

- users' default permissions, used for new histories;
- default permissions of histories that are not shared, used for new datasets in those histories;
- datasets that only that user can reach through histories that are not shared.

Datasets are left unchanged if they already have access restrictions, are in a data library, are
reachable through histories of other users or of anonymous users, or are reachable through a
history that is published, accessible via link, shared with other users, or referenced by a page
that is. Datasets converted from another dataset (e.g. for visualizations) are only restricted
if every dataset they were converted from is private to the same user.

Without --commit, only reports what would be changed.
"""

ACCESS = "access"
MANAGE = "manage permissions"
DEFAULT_BATCH_SIZE = 10000
DEFAULT_ID_SECRET = "USING THE DEFAULT IS NOT SECURE!"
PAGE_HISTORY_TABLE = "tmp_make_data_private_page_history"
PRIVATE_ROLE_TABLE = "tmp_make_data_private_role"
IN_CHUNK_SIZE = 1000

log = logging.getLogger(__name__)

# Users with more than one private role use the oldest, like `get_private_user_role`.
PRIVATE_ROLES = """
    SELECT ura.user_id, MIN(role.id)
    FROM user_role_association ura
    JOIN role ON role.id = ura.role_id
    WHERE role.type = 'private'
    GROUP BY ura.user_id
"""

USERS_MISSING_DEFAULT = text(f"""
    SELECT private_role.user_id, private_role.role_id
    FROM {PRIVATE_ROLE_TABLE} AS private_role
    WHERE NOT EXISTS (
        SELECT 1 FROM default_user_permissions dup
        WHERE dup.user_id = private_role.user_id AND dup.action = :action
    )
""")

# History sharing is checked in each batch, rather than once up front, so that histories shared
# while the script runs are left unchanged.
HISTORIES_MISSING_DEFAULT = text(f"""
    SELECT history.id, private_role.role_id
    FROM history
    JOIN {PRIVATE_ROLE_TABLE} AS private_role ON private_role.user_id = history.user_id
    WHERE history.id >= :low AND history.id < :high
    AND NOT COALESCE(history.purged, FALSE)
    AND NOT COALESCE(history.published, FALSE)
    AND NOT COALESCE(history.importable, FALSE)
    AND NOT EXISTS (SELECT 1 FROM history_user_share_association husa WHERE husa.history_id = history.id)
    AND NOT EXISTS (SELECT 1 FROM {PAGE_HISTORY_TABLE} page_history WHERE page_history.id = history.id)
    AND NOT EXISTS (
        SELECT 1 FROM default_history_permissions dhp
        WHERE dhp.history_id = history.id AND dhp.action = :action
    )
""")

# Every history a dataset can be reached through: directly via an HDA, or via an HDCA whose
# (possibly nested) collection contains one of the dataset's HDAs. `{converted}` selects either
# datasets that are not implicit conversions ("NOT") or those that are ("").
PUBLIC_SINGLE_OWNER_DATASETS = f"""
    WITH RECURSIVE dataset_collection_ancestor(dataset_id, collection_id) AS (
        SELECT hda.dataset_id, dce.dataset_collection_id
        FROM history_dataset_association hda
        JOIN dataset_collection_element dce ON dce.hda_id = hda.id
        WHERE hda.dataset_id >= :low AND hda.dataset_id < :high
        UNION
        SELECT ancestor.dataset_id, dce.dataset_collection_id
        FROM dataset_collection_ancestor ancestor
        JOIN dataset_collection_element dce ON dce.child_collection_id = ancestor.collection_id
    ),
    dataset_history(dataset_id, history_id) AS (
        SELECT hda.dataset_id, hda.history_id
        FROM history_dataset_association hda
        WHERE hda.dataset_id >= :low AND hda.dataset_id < :high
        UNION
        SELECT ancestor.dataset_id, hdca.history_id
        FROM dataset_collection_ancestor ancestor
        JOIN history_dataset_collection_association hdca ON hdca.collection_id = ancestor.collection_id
    )
    SELECT dataset_history.dataset_id, MIN(private_role.role_id)
    FROM dataset_history
    JOIN dataset ON dataset.id = dataset_history.dataset_id
    LEFT JOIN history ON history.id = dataset_history.history_id
    LEFT JOIN {PRIVATE_ROLE_TABLE} AS private_role ON private_role.user_id = history.user_id
    LEFT JOIN {PAGE_HISTORY_TABLE} AS page_history ON page_history.id = history.id
    LEFT JOIN (SELECT DISTINCT history_id FROM history_user_share_association) AS shared
        ON shared.history_id = history.id
    WHERE NOT COALESCE(dataset.purged, FALSE)
    AND NOT EXISTS (
        SELECT 1 FROM dataset_permissions dp WHERE dp.dataset_id = dataset.id AND dp.action = '{ACCESS}'
    )
    AND NOT EXISTS (
        SELECT 1 FROM library_dataset_dataset_association ldda WHERE ldda.dataset_id = dataset.id
    )
    AND {{converted}} EXISTS (
        SELECT 1 FROM history_dataset_association converted_hda
        JOIN implicitly_converted_dataset_association icda ON icda.hda_id = converted_hda.id
        WHERE converted_hda.dataset_id = dataset.id
    )
    GROUP BY dataset_history.dataset_id
    HAVING COUNT(private_role.role_id) = COUNT(*)
    AND MIN(private_role.role_id) = MAX(private_role.role_id)
    AND COUNT(page_history.id) = 0
    AND COUNT(shared.history_id) = 0
    AND SUM(CASE WHEN COALESCE(history.published, FALSE) OR COALESCE(history.importable, FALSE) THEN 1 ELSE 0 END) = 0
"""
PUBLIC_SINGLE_OWNER_ORIGINAL_DATASETS = text(PUBLIC_SINGLE_OWNER_DATASETS.format(converted="NOT"))
PUBLIC_SINGLE_OWNER_CONVERTED_DATASETS = text(PUBLIC_SINGLE_OWNER_DATASETS.format(converted=""))

# Galaxy gives a converted dataset to everyone who can access the dataset it was converted from,
# so converted datasets are only restricted if all their parents are restricted to the same role.
CONVERSION_PARENT_ACCESS = text(f"""
    SELECT converted_hda.dataset_id, icda.ldda_parent_id, dp.role_id
    FROM history_dataset_association converted_hda
    JOIN implicitly_converted_dataset_association icda ON icda.hda_id = converted_hda.id
    LEFT JOIN history_dataset_association parent ON parent.id = icda.hda_parent_id
    LEFT JOIN dataset_permissions dp ON dp.dataset_id = parent.dataset_id AND dp.action = '{ACCESS}'
    WHERE converted_hda.dataset_id >= :low AND converted_hda.dataset_id < :high
""")

DATASETS_WITH_MANAGE = text(f"""
    SELECT dataset_id FROM dataset_permissions
    WHERE action = '{MANAGE}' AND dataset_id >= :low AND dataset_id < :high
""")

SHARED_PAGES = text("""
    SELECT page.history_id, page.source_invocation_id, page_revision.content
    FROM page
    LEFT JOIN page_revision ON page_revision.id = page.latest_revision_id
    WHERE NOT COALESCE(page.deleted, FALSE)
    AND (
        COALESCE(page.published, FALSE)
        OR COALESCE(page.importable, FALSE)
        OR EXISTS (SELECT 1 FROM page_user_share_association pusa WHERE pusa.page_id = page.id)
    )
""")

# Galaxy markdown directives store unencoded ids as `<type>_id=<id>`, and visualization blocks as
# `"invocation_id": "<id>"`.
PAGE_REFERENCE_PATTERNS = {
    "history": [re.compile(r"\bhistory_id=(\d+)")],
    "history_dataset_association": [re.compile(r"\bhistory_dataset_id=(\d+)")],
    "history_dataset_collection_association": [re.compile(r"\bhistory_dataset_collection_id=(\d+)")],
    "workflow_invocation": [re.compile(r"\binvocation_id=(\d+)"), re.compile(r'"invocation_id"\s*:\s*"(\d+)"')],
    "job": [re.compile(r"\bjob_id=(\d+)")],
    "implicit_collection_jobs": [re.compile(r"\bimplicit_collection_jobs_id=(\d+)")],
}
# HTML pages embed items as `id="<class>-<id>"`, with ids unencoded since Galaxy 18.09 and encoded before.
HTML_EMBED_PATTERN = re.compile(r"""\bid=["'](History|HistoryDatasetAssociation)-([0-9a-fA-F]+)["']""")
HTML_EMBED_TABLES = {"History": "history", "HistoryDatasetAssociation": "history_dataset_association"}
# Like `get_page_identifiers`: numeric ids below this are unencoded.
PAGE_MAXRAW = 10**15

REFERENCED_HISTORIES = {
    "history_dataset_association": "SELECT history_id FROM history_dataset_association WHERE id IN :ids",
    "history_dataset_collection_association": (
        "SELECT history_id FROM history_dataset_collection_association WHERE id IN :ids"
    ),
    "workflow_invocation": "SELECT history_id FROM workflow_invocation WHERE id IN :ids",
    "job": "SELECT history_id FROM job WHERE id IN :ids",
    "implicit_collection_jobs": """
        SELECT job.history_id FROM implicit_collection_jobs_job_association icjja
        JOIN job ON job.id = icjja.job_id
        WHERE icjja.implicit_collection_jobs_id IN :ids
    """,
}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _get_parser().parse_args()
    config = get_config(sys.argv, use_argparse=False, cwd=os.getcwd())
    properties = load_app_properties(config_file=config["config_file"])
    security = IdEncodingHelper(id_secret=properties.get("id_secret", DEFAULT_ID_SECRET))
    engine = create_engine(config["db_url"])
    run(engine, commit=args.commit, batch_size=args.batch, decode_id=security.decode_id)


def _get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=DESCRIPTION, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--commit", action="store_true", help="apply the changes (default: only report them)")
    parser.add_argument("--batch", type=int, default=DEFAULT_BATCH_SIZE, help="number of ids processed per batch")
    populate_config_args(parser)
    return parser


def run(
    engine: Engine,
    commit: bool = False,
    batch_size: int = DEFAULT_BATCH_SIZE,
    decode_id: Callable[[str], int] | None = None,
) -> dict[str, int]:
    """Restrict access to the owner's private role, returning the number of rows added per table.

    `decode_id` decodes the encoded ids in pages saved before Galaxy 18.09.
    """
    with engine.connect() as conn:
        _create_tmp_tables(conn, decode_id)
        try:
            counts = {
                "default_user_permissions": _update_user_defaults(conn, commit),
                "default_history_permissions": _update_history_defaults(conn, commit, batch_size),
                "dataset_permissions": _update_datasets(conn, commit, batch_size),
            }
        finally:
            conn.rollback()
            conn.execute(text(f"DROP TABLE IF EXISTS {PAGE_HISTORY_TABLE}"))
            conn.execute(text(f"DROP TABLE IF EXISTS {PRIVATE_ROLE_TABLE}"))
            conn.commit()
    verb = "Added" if commit else "Would add"
    for table, count in counts.items():
        log.info("%s %d %s rows", verb, count, table)
    if not commit:
        log.info("Converted datasets are only counted if the datasets they were converted from are already private.")
    return counts


def _create_tmp_tables(conn: Connection, decode_id: Callable[[str], int] | None) -> None:
    conn.execute(text(f"CREATE TEMPORARY TABLE {PRIVATE_ROLE_TABLE} (user_id INTEGER PRIMARY KEY, role_id INTEGER)"))
    conn.execute(text(f"INSERT INTO {PRIVATE_ROLE_TABLE} (user_id, role_id) {PRIVATE_ROLES}"))
    conn.execute(text(f"CREATE TEMPORARY TABLE {PAGE_HISTORY_TABLE} (id INTEGER PRIMARY KEY)"))
    page_history_ids = _page_history_ids(conn, decode_id)
    if page_history_ids:
        conn.execute(text(f"INSERT INTO {PAGE_HISTORY_TABLE} (id) VALUES (:id)"), [{"id": i} for i in page_history_ids])
    if conn.dialect.name == "postgresql":
        # Autovacuum does not analyze temporary tables.
        conn.execute(text(f"ANALYZE {PRIVATE_ROLE_TABLE}"))
        conn.execute(text(f"ANALYZE {PAGE_HISTORY_TABLE}"))
    conn.commit()
    log.info("Leaving %d histories referenced by shared pages unchanged", len(page_history_ids))


def _page_history_ids(conn: Connection, decode_id: Callable[[str], int] | None) -> set[int]:
    """Return ids of histories that shared, published or importable pages refer to."""
    references: dict[str, set[int]] = {table: set() for table in PAGE_REFERENCE_PATTERNS}
    for history_id, invocation_id, content in conn.execute(SHARED_PAGES):
        if history_id:
            references["history"].add(history_id)
        if invocation_id:
            references["workflow_invocation"].add(invocation_id)
        content = content or ""
        for table, patterns in PAGE_REFERENCE_PATTERNS.items():
            for pattern in patterns:
                references[table].update(int(i) for i in pattern.findall(content))
        for item_class, item_id in HTML_EMBED_PATTERN.findall(content):
            decoded_id = _decode_page_id(item_id, decode_id)
            if decoded_id is not None:
                references[HTML_EMBED_TABLES[item_class]].add(decoded_id)
    history_ids = references.pop("history")
    for table, ids in references.items():
        stmt = text(REFERENCED_HISTORIES[table]).bindparams(bindparam("ids", expanding=True))
        id_list = list(ids)
        for start in range(0, len(id_list), IN_CHUNK_SIZE):
            history_ids.update(i for i in conn.scalars(stmt, {"ids": id_list[start : start + IN_CHUNK_SIZE]}) if i)
    return history_ids


def _decode_page_id(item_id: str, decode_id: Callable[[str], int] | None) -> int | None:
    if item_id.isdigit() and int(item_id) < PAGE_MAXRAW:
        return int(item_id)
    if decode_id is not None:
        try:
            return decode_id(item_id)
        except Exception:
            pass
    log.warning("Cannot decode page item id %s, the history it refers to may be made private", item_id)
    return None


def _update_user_defaults(conn: Connection, commit: bool) -> int:
    count = 0
    for action in (MANAGE, ACCESS):
        rows = conn.execute(USERS_MISSING_DEFAULT, {"action": action}).all()
        if rows and commit:
            conn.execute(
                text("INSERT INTO default_user_permissions (user_id, action, role_id) VALUES (:id, :action, :role_id)"),
                [{"id": user_id, "action": action, "role_id": role_id} for user_id, role_id in rows],
            )
        conn.commit()
        count += len(rows)
    return count


def _update_history_defaults(conn: Connection, commit: bool, batch_size: int) -> int:
    count = 0
    for low, high in _batches(conn, "history", batch_size):
        for action in (MANAGE, ACCESS):
            rows = conn.execute(HISTORIES_MISSING_DEFAULT, {"action": action, "low": low, "high": high}).all()
            if rows and commit:
                conn.execute(
                    text(
                        "INSERT INTO default_history_permissions (history_id, action, role_id) VALUES (:id, :action, :role_id)"
                    ),
                    [{"id": history_id, "action": action, "role_id": role_id} for history_id, role_id in rows],
                )
            conn.commit()
            count += len(rows)
    return count


def _update_datasets(conn: Connection, commit: bool, batch_size: int) -> int:
    count = 0
    for low, high in _batches(conn, "dataset", batch_size):
        rows = _dataset_roles(conn, PUBLIC_SINGLE_OWNER_ORIGINAL_DATASETS, low, high)
        count += _restrict_datasets(conn, commit, low, high, rows)
    # Converted datasets go last, once the datasets they were converted from have been restricted.
    for low, high in _batches(conn, "dataset", batch_size):
        rows = _dataset_roles(conn, PUBLIC_SINGLE_OWNER_CONVERTED_DATASETS, low, high)
        if rows:
            parent_access: dict[int, set[int | None]] = {}
            for dataset_id, ldda_parent_id, role_id in conn.execute(
                CONVERSION_PARENT_ACCESS, {"low": low, "high": high}
            ):
                parent_access.setdefault(dataset_id, set()).add(None if ldda_parent_id else role_id)
            rows = [(dataset_id, role_id) for dataset_id, role_id in rows if parent_access.get(dataset_id) == {role_id}]
        count += _restrict_datasets(conn, commit, low, high, rows)
    return count


def _dataset_roles(conn: Connection, stmt: TextClause, low: int, high: int) -> list[tuple[int, int]]:
    return [(dataset_id, role_id) for dataset_id, role_id in conn.execute(stmt, {"low": low, "high": high})]


def _restrict_datasets(conn: Connection, commit: bool, low: int, high: int, rows: list[tuple[int, int]]) -> int:
    if not rows:
        conn.commit()
        return 0
    with_manage = set(conn.scalars(DATASETS_WITH_MANAGE, {"low": low, "high": high}))
    permissions = [(ACCESS, dataset_id, role_id) for dataset_id, role_id in rows]
    permissions += [(MANAGE, dataset_id, role_id) for dataset_id, role_id in rows if dataset_id not in with_manage]
    if commit:
        timestamp = now()
        conn.execute(
            text(
                "INSERT INTO dataset_permissions (create_time, update_time, action, dataset_id, role_id) "
                "VALUES (:time, :time, :action, :id, :role_id)"
            ),
            [
                {"time": timestamp, "action": action, "id": dataset_id, "role_id": role_id}
                for action, dataset_id, role_id in permissions
            ],
        )
    conn.commit()
    log.info("Dataset ids %d-%d: %d datasets to restrict", low, high - 1, len(rows))
    return len(permissions)


def _batches(conn: Connection, table: str, batch_size: int) -> Iterator[tuple[int, int]]:
    min_id, max_id = conn.execute(text(f"SELECT MIN(id), MAX(id) FROM {table}")).one()
    if min_id is None:
        return
    for low in range(min_id, max_id + 1, batch_size):
        yield low, low + batch_size


if __name__ == "__main__":
    main()
