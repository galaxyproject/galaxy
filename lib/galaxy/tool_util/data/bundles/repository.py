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
    Dict,
    FrozenSet,
    Iterable,
    List,
    Optional,
    Tuple,
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
    # ``found`` means the loader resolved *some* file for this reference. Note a table's
    # ``<file path="tool-data/x.loc">`` whose real ``.loc`` is absent resolves to the
    # ``x.loc.sample`` fallback with ``found=True`` -- so a check that a production loc
    # exists must consider ``found and not is_sample``, not ``found`` alone.
    found: bool
    is_sample: bool
    # Row-shape errors captured by ``parse_file_fields`` at load time (too-few-fields /
    # wrong-separator lines). Only populated when ``found`` (parsing only runs on a
    # resolved file), so "no errors" is not "clean" for an unfound reference.
    errors: Tuple[str, ...] = ()
    source: Optional[SourceLoc] = None


@dataclass
class TableDecl:
    """A ``tool_data_table_conf.xml*`` ``<table>`` definition, plus its live instance."""

    name: str
    columns: Dict[str, int]
    largest_index: int
    separator: str
    comment_char: str
    allow_duplicate_entries: bool
    loc_paths: Tuple[str, ...]
    # The configured runtime table -- reused by downstream row-shape / schema checks.
    instance: TabularToolDataTable
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
    loc_assets: List[LocAsset] = field(default_factory=list)
    consumers: List[ConsumerRef] = field(default_factory=list)
    # Tables validly supplied by Galaxy core or another installed repository; a
    # consumer of one of these is not a demonstrably-missing definition (req #2).
    external_table_names: FrozenSet[str] = frozenset()

    @property
    def configured_table_names(self) -> FrozenSet[str]:
        return frozenset(t.name for t in self.configured_tables)

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


def _consumer_refs(tool_source: ToolSource, path: str) -> List[ConsumerRef]:
    """Scan a (macro-expanded) wrapper for ``from_data_table`` table references."""
    root = getattr(tool_source, "root", None)
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
                output_names = _xml_output_names(getattr(tool_source, "root", None))
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


def _build_tables(repo_root: str, tool_data_table_confs: List[str]) -> Tuple[List[TableDecl], List[LocAsset]]:
    # ToolDataTableManager loads the confs, resolving ${__HERE__} / .sample fallback and
    # recording per-file parse errors -- we read that resolved state back out.
    tdt_manager = ToolDataTableManager(repo_root, config_filename=tool_data_table_confs)
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
                instance=table,
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
        model.configured_tables, model.loc_assets = _build_tables(repo_root, tool_data_table_confs)
    for path, tool_source in consumer_tool_sources or []:
        model.consumers.extend(_consumer_refs(tool_source, path))
    return model
