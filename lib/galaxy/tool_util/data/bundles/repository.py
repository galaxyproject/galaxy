"""Cross-file *lint view* of a repository's data-table bundle.

This module assembles the producer/configuration/consumer artifacts of a
data-manager / reference-data repository into a single :class:`RepositoryDataTables`
model so repository-level linters can reason across files. It is deliberately
*pure data assembly* -- it parses and resolves, it does not emit diagnostics.

It composes existing galaxy-tool-util abstractions rather than duplicating them:

- the data-manager ``<data_tables>`` block is parsed with
  :func:`galaxy.tool_util.data.bundles.models.convert_data_tables_xml` into a
  :class:`~galaxy.tool_util.data.bundles.models.DataTableBundleProcessorDescription`
  (giving ``output_ref`` values, table names, and column mappings);
- ``tool_data_table_conf.xml*`` files are loaded with
  :class:`~galaxy.tool_util.data.ToolDataTableManager`, which already resolves
  ``${__HERE__}`` / ``.sample`` fallback and records per-row parse errors; and
- tool wrappers are read through :func:`galaxy.tool_util.parser.factory.get_tool_source`,
  which expands macros before names are resolved.
"""

import os
from dataclasses import (
    dataclass,
    field,
)
from typing import (
    cast,
    Dict,
    FrozenSet,
    Iterable,
    List,
    Optional,
    Tuple,
    Union,
)

from galaxy.tool_util.data import (
    TabularToolDataTable,
    ToolDataTableManager,
)
from galaxy.tool_util.data.bundles.models import (
    convert_data_tables_xml,
    DataTableBundleProcessorDescription,
)
from galaxy.tool_util.parser.factory import get_tool_source
from galaxy.tool_util.parser.interface import ToolSource
from galaxy.util import (
    Element,
    parse_xml,
    xml_text,
)


@dataclass
class SourceLoc:
    """Where a modeled element came from, for narrow skips and PR annotations."""

    path: str
    line: Optional[int] = None


@dataclass
class LocAsset:
    """A resolved ``.loc`` / ``.loc.sample`` file referenced by a configured table."""

    table_name: str
    path: str
    # ``found`` means the *loader* resolved and parsed a real file for this reference.
    # The loader's ``.sample`` fallback (data/__init__.py) strips the ``tool-data/``
    # subdir and only looks in ``tool_data_path`` root, so it does *not* match a shed
    # repo's ``tool-data/x.loc.sample`` -- those come back ``found=False``. Use
    # ``sample_backed`` for "the repo ships a sample for this reference"; a reference is
    # unresolved only when ``not found and not sample_backed``.
    found: bool
    is_sample: bool
    # Whether the repo ships a ``.sample`` backing this reference (a sibling
    # ``<ref>.sample`` or the conventional ``tool-data/<basename>.sample``). On install
    # Galaxy materializes the real ``.loc`` from it, so a sample-backed reference is not
    # a missing loc even though the loader reports ``found=False``.
    sample_backed: bool = False
    # Row-shape errors captured by ``parse_file_fields`` at load time (too-few-fields /
    # wrong-separator lines). Only populated when ``found`` (parsing only runs on a
    # loader-resolved file), so "no errors" is not "clean" for an unfound reference.
    errors: Tuple[str, ...] = ()
    source: Optional[SourceLoc] = None


@dataclass
class RawTableDecl:
    """A single ``<table>`` element as declared, before the loader merges same-named tables.

    Kept separate from :class:`TableDecl` because the loader collapses duplicate
    column names into a dict and *raises* when two same-named tables declare
    different columns -- so conflicting/duplicate schemas are only observable in
    this pre-merge view.
    """

    name: str
    # Declared column names in order, keeping duplicates (the parsed ``columns``
    # map collapses them) -- used to detect a table declaring one name twice.
    column_names: Tuple[str, ...]
    # The name->index map the loader would parse; this is what it compares when
    # merging same-named tables, so schema-conflict detection keys on this.
    columns: Dict[str, int]
    separator: str
    comment_char: str
    source: SourceLoc


@dataclass
class TableDecl:
    """A ``tool_data_table_conf.xml*`` ``<table>`` definition (name + parsed schema).

    Only ``name`` is read today (via ``configured_table_names``); the parsed schema
    fields are retained for the planned bundle-completeness check.
    """

    name: str
    columns: Dict[str, int]
    largest_index: int
    separator: str
    comment_char: str
    allow_duplicate_entries: bool
    loc_paths: Tuple[str, ...]
    source: Optional[SourceLoc] = None


@dataclass
class ConsumerRef:
    """A tool reference to a data table (``from_data_table``)."""

    table_name: str
    kind: str
    tool_id: Optional[str]
    source: SourceLoc


@dataclass
class ManagerDecl:
    """A ``<data_manager>`` and the wrapper it points at."""

    id: str
    tool_file: str
    tool_output_names: FrozenSet[str]
    # Reused manager-side model: output_ref values, table names, column mappings.
    processor: DataTableBundleProcessorDescription
    source: SourceLoc
    # Whether the wrapper was located and parsed. When False ``tool_output_names``
    # is unknown (not "empty"), so output_ref checks must treat it as not-checked
    # rather than reporting a demonstrably-missing output.
    wrapper_resolved: bool = False


@dataclass
class RepositoryDataTables:
    """Cross-file lint view of one repository's data-table bundle."""

    repo_root: str
    managers: List[ManagerDecl] = field(default_factory=list)
    configured_tables: List[TableDecl] = field(default_factory=list)
    # Every ``<table>`` element as declared (pre-merge); may hold several entries
    # for one name. Populated even when the loader is skipped over a conflict.
    raw_table_decls: List[RawTableDecl] = field(default_factory=list)
    loc_assets: List[LocAsset] = field(default_factory=list)
    consumers: List[ConsumerRef] = field(default_factory=list)
    # Tables validly supplied by Galaxy core or another installed repository; a
    # consumer of one of these is not a demonstrably-missing definition (req #2).
    external_table_names: FrozenSet[str] = frozenset()

    @property
    def configured_table_names(self) -> FrozenSet[str]:
        # Union of loader-enriched and raw declarations: names stay available for
        # cross-component checks even when a schema conflict made the loader skip.
        names = {t.name for t in self.configured_tables}
        names |= {d.name for d in self.raw_table_decls}
        return frozenset(names)

    def table(self, name: str) -> Optional[TableDecl]:
        for table in self.configured_tables:
            if table.name == name:
                return table
        return None


def _xml_output_names(root: Optional[Element]) -> FrozenSet[str]:
    """Names of ``<data>`` / ``<collection>`` outputs declared by a (macro-expanded) wrapper."""
    if root is None:
        return frozenset()
    outputs_elem = root.find("outputs")
    if outputs_elem is None:
        return frozenset()
    names = set()
    for output_elem in outputs_elem:
        if output_elem.tag in ("data", "collection"):
            name = output_elem.get("name")
            if name:
                names.add(name)
    return frozenset(names)


def _tool_source_root(tool_source: ToolSource) -> Optional[Element]:
    """Root element of a (macro-expanded) XML wrapper, or None for a non-XML source.

    Reads the ``xml_tree`` attribute the tool linters standardize on rather than the
    equivalent ``root`` attribute.
    """
    xml_tree = getattr(tool_source, "xml_tree", None)
    return xml_tree.getroot() if xml_tree is not None else None


def _consumer_refs(tool_source: ToolSource, path: str) -> List[ConsumerRef]:
    """Scan a (macro-expanded) wrapper for ``from_data_table`` table references."""
    root = _tool_source_root(tool_source)
    if root is None:
        return []
    tool_id = tool_source.parse_id()
    refs = []
    for elem in root.iter():
        table_name = elem.get("from_data_table")
        if table_name:
            refs.append(
                ConsumerRef(
                    table_name=table_name,
                    kind="from_data_table",
                    tool_id=tool_id,
                    source=SourceLoc(path=path, line=getattr(elem, "sourceline", None)),
                )
            )
    return refs


def _build_managers(data_manager_conf: str) -> List[ManagerDecl]:
    conf_dir = os.path.dirname(os.path.abspath(data_manager_conf))
    root = parse_xml(data_manager_conf).getroot()
    managers = []
    for dm_elem in root.findall("data_manager"):
        manager_id = dm_elem.get("guid") or dm_elem.get("id") or ""
        # tool_file is either the attribute form or the nested <tool file="..."/> (shed/guid)
        # form -- mirror DataManager._load_from_element in tools/data_manager/manager.py.
        tool_file = dm_elem.get("tool_file")
        if tool_file is None:
            tool_elem = dm_elem.find("tool")
            tool_file = tool_elem.get("file") if tool_elem is not None else None
        tool_file = tool_file or ""
        output_names: FrozenSet[str] = frozenset()
        wrapper_resolved = False
        if tool_file:
            tool_path = os.path.join(conf_dir, tool_file)
            if os.path.exists(tool_path):
                tool_source = get_tool_source(config_file=tool_path)
                output_names = _xml_output_names(_tool_source_root(tool_source))
                wrapper_resolved = True
        managers.append(
            ManagerDecl(
                id=manager_id,
                tool_file=tool_file,
                tool_output_names=output_names,
                processor=convert_data_tables_xml(dm_elem),
                source=SourceLoc(path=data_manager_conf, line=getattr(dm_elem, "sourceline", None)),
                wrapper_resolved=wrapper_resolved,
            )
        )
    return managers


def _raw_column_spec(table_elem: Element) -> Tuple[Tuple[str, ...], Dict[str, int]]:
    """Declared column names (with duplicates) and the parsed name->index map.

    The name->index map is produced by the canonical
    ``TabularToolDataTable.parse_column_spec_element`` so it matches exactly what the
    loader compares when merging same-named tables. Only the ordered name list (which
    keeps the duplicates ``DuplicateColumnNames`` needs, but the canonical map
    collapses) is derived here.
    """
    columns, _, _ = TabularToolDataTable.parse_column_spec_element(table_elem)
    columns_elem = table_elem.find("columns")
    if columns_elem is not None:
        column_names = tuple(name.strip() for name in xml_text(columns_elem).split(","))
    else:
        column_names = tuple(
            column_elem.get("name")
            for column_elem in table_elem.findall("column")
            if column_elem.get("name") is not None and column_elem.get("index") is not None
        )
    return column_names, columns


def _raw_table_decls(tool_data_table_confs: List[str]) -> List[RawTableDecl]:
    """Parse every ``<table>`` element as declared, before the loader merges same names."""
    decls = []
    for conf in tool_data_table_confs:
        root = parse_xml(conf).getroot()
        for table_elem in root.findall("table"):
            column_names, columns = _raw_column_spec(table_elem)
            decls.append(
                RawTableDecl(
                    name=table_elem.get("name") or "",
                    column_names=column_names,
                    columns=columns,
                    separator=table_elem.get("separator", "\t"),
                    comment_char=table_elem.get("comment_char", "#"),
                    source=SourceLoc(path=conf, line=getattr(table_elem, "sourceline", None)),
                )
            )
    return decls


def _has_column_conflict(raw_decls: List[RawTableDecl]) -> bool:
    """Whether any table name is declared with differing columns (what the loader's merge rejects).

    Keys on the parsed name->index map, not the raw name list, because that map is
    exactly what the loader compares -- ``merge_tool_data_table`` /
    ``ToolDataTableManager.assert_data_table_consistency`` reject same-named tables
    whose ``columns`` maps differ (two ``<column>`` forms can share names yet differ
    by index). This is the pre-load counterpart of that check: same columns-equality
    rule, applied to the raw declarations before the loader is invoked.
    """
    by_name: Dict[str, List[Dict[str, int]]] = {}
    for decl in raw_decls:
        specs = by_name.setdefault(decl.name, [])
        if decl.columns not in specs:
            specs.append(decl.columns)
    return any(len(specs) > 1 for specs in by_name.values())


def _sample_backed(repo_root: str, filename: str) -> bool:
    """Whether the repo ships a ``.sample`` that backs a loc ``filename``.

    The loader's own ``.sample`` fallback does not match the shed layout (see
    ``LocAsset.found``), so resolve it the way the shed does: a reference is
    sample-backed if a sibling ``<filename>.sample`` exists, or the conventional
    ``tool-data/<basename>.sample`` does (samples ship there and the real ``.loc`` is
    materialized on install). Basename matching mirrors that a table is keyed by name,
    so ``test-data/x.loc`` in a ``.test`` conf is still backed by ``tool-data/x.loc.sample``.
    """
    sibling = filename if os.path.isabs(filename) else os.path.join(repo_root, filename)
    if os.path.exists(f"{sibling}.sample"):
        return True
    tool_data_sample = os.path.join(repo_root, "tool-data", f"{os.path.basename(filename)}.sample")
    return os.path.exists(tool_data_sample)


def _build_tables(
    repo_root: str, tool_data_table_confs: List[str], raw_decls: List[RawTableDecl]
) -> Tuple[List[TableDecl], List[LocAsset]]:
    # A same-named table declared with conflicting columns makes the loader's merge
    # raise; skip enrichment in that case and let the linter report the conflict from
    # the raw declarations (table names still come from those). Loc diagnostics for
    # sibling tables are suppressed until the conflict is fixed and the loader re-runs.
    if _has_column_conflict(raw_decls):
        return [], []
    # ToolDataTableManager loads the confs, resolving ${__HERE__} / .sample fallback and
    # recording per-file parse errors -- we read that resolved state back out.
    # cast around list invariance: ToolDataTableManager takes list[str | PathLike]; our
    # str paths are compatible element-wise, but List[str] is not List[str | PathLike].
    tdt_manager = ToolDataTableManager(
        repo_root, config_filename=cast("List[Union[str, os.PathLike[str]]]", tool_data_table_confs)
    )
    conf_source = SourceLoc(path=tool_data_table_confs[0]) if len(tool_data_table_confs) == 1 else None
    tables = []
    loc_assets = []
    for table in tdt_manager.data_tables.values():
        if not isinstance(table, TabularToolDataTable):
            continue
        loc_paths = []
        for filename, info in table.filenames.items():
            loc_paths.append(filename)
            loc_assets.append(
                LocAsset(
                    table_name=table.name,
                    path=str(filename),
                    found=bool(info.get("found")),
                    is_sample=str(filename).endswith(".sample"),
                    sample_backed=_sample_backed(repo_root, str(filename)),
                    errors=tuple(info.get("errors") or ()),
                    source=SourceLoc(path=str(filename)),
                )
            )
        tables.append(
            TableDecl(
                name=table.name,
                columns=dict(table.columns),
                largest_index=table.largest_index,
                separator=table.separator,
                comment_char=table.comment_char,
                allow_duplicate_entries=table.allow_duplicate_entries,
                loc_paths=tuple(loc_paths),
                source=conf_source,
            )
        )
    return tables, loc_assets


def build_repository_data_tables(
    repo_root: str,
    data_manager_conf: Optional[str] = None,
    tool_data_table_confs: Optional[List[str]] = None,
    consumer_tool_sources: Optional[Iterable[Tuple[str, ToolSource]]] = None,
    external_table_names: FrozenSet[str] = frozenset(),
) -> RepositoryDataTables:
    """Assemble a :class:`RepositoryDataTables` from already-discovered repository assets.

    ``repo_root`` anchors ``${__HERE__}`` resolution and shed path handling.
    Discovery (which files to pass) is the caller's responsibility -- e.g. Planemo's
    ``shed_lint`` preferring ``tool_data_table_conf.xml.test`` over ``.sample``.
    ``consumer_tool_sources`` are ``(path, tool_source)`` pairs for ordinary
    (non data-manager) tools that may reference the repository's tables.
    """
    model = RepositoryDataTables(repo_root=repo_root, external_table_names=external_table_names)
    if data_manager_conf:
        model.managers = _build_managers(data_manager_conf)
    if tool_data_table_confs:
        model.raw_table_decls = _raw_table_decls(tool_data_table_confs)
        model.configured_tables, model.loc_assets = _build_tables(
            repo_root, tool_data_table_confs, model.raw_table_decls
        )
    for path, tool_source in consumer_tool_sources or []:
        model.consumers.extend(_consumer_refs(tool_source, path))
    return model
