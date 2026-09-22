"""Assemble a repository's data-table bundle for cross-file linting."""

import os
from collections.abc import Iterable
from dataclasses import (
    dataclass,
    field,
)
from typing import (
    cast,
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
    """Location of a modeled element."""

    path: str
    line: int | None = None


@dataclass
class LocAsset:
    """A configured table's ``.loc`` reference."""

    table_name: str
    path: str
    # ``found`` is loader resolution against ``tool_data_path``; a valid repository
    # checkout may instead satisfy the reference through ``repo_backed``.
    found: bool
    is_sample: bool
    # The repository contains the declared loc or an installable sample for it.
    repo_backed: bool = False
    # Row-shape errors from the loader-resolved or repository-backed file.
    errors: tuple[str, ...] = ()
    source: SourceLoc | None = None


@dataclass
class LocFile:
    """A ``.loc`` file present in the repository, referenced or not."""

    path: str
    # A non-blank, non-comment line.
    has_data: bool
    # A ``#`` comment line documenting the expected column format.
    has_comment: bool


@dataclass
class RawTableDecl:
    """A ``<table>`` declaration captured before loader merging."""

    name: str
    # Ordered names preserve duplicates that the parsed map loses.
    column_names: tuple[str, ...]
    # The loader's name-to-index map, used to detect merge conflicts.
    columns: dict[str, int]
    separator: str
    comment_char: str
    source: SourceLoc


@dataclass
class TableDecl:
    """A parsed ``tool_data_table_conf.xml*`` table definition."""

    name: str
    columns: dict[str, int]
    largest_index: int
    separator: str
    comment_char: str
    allow_duplicate_entries: bool
    loc_paths: tuple[str, ...]
    source: SourceLoc | None = None


@dataclass
class ConsumerRef:
    """A tool reference to a data table (``from_data_table``)."""

    table_name: str
    kind: str
    tool_id: str | None
    source: SourceLoc


@dataclass
class ManagerDecl:
    """A ``<data_manager>`` and the wrapper it points at."""

    id: str
    tool_file: str
    tool_output_names: frozenset[str]
    processor: DataTableBundleProcessorDescription
    source: SourceLoc
    # False means the output names are unknown, not empty.
    wrapper_resolved: bool = False


@dataclass
class RepositoryDataTables:
    """Cross-file lint view of one repository's data-table bundle."""

    repo_root: str
    managers: list[ManagerDecl] = field(default_factory=list)
    configured_tables: list[TableDecl] = field(default_factory=list)
    # Pre-merge declarations remain available when loader merging fails.
    raw_table_decls: list[RawTableDecl] = field(default_factory=list)
    loc_assets: list[LocAsset] = field(default_factory=list)
    # Includes unreferenced files for the empty-file check.
    loc_files: list[LocFile] = field(default_factory=list)
    consumers: list[ConsumerRef] = field(default_factory=list)
    # Tables supplied by Galaxy core or another repository.
    external_table_names: frozenset[str] = frozenset()

    @property
    def configured_table_names(self) -> frozenset[str]:
        # Keep names available when a schema conflict prevents loader enrichment.
        names = {t.name for t in self.configured_tables}
        names |= {d.name for d in self.raw_table_decls}
        return frozenset(names)

    def table(self, name: str) -> TableDecl | None:
        for table in self.configured_tables:
            if table.name == name:
                return table
        return None


def _xml_output_names(root: Element | None) -> frozenset[str]:
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


def _tool_source_root(tool_source: ToolSource) -> Element | None:
    """Return the expanded XML root, or ``None`` for a non-XML source."""
    xml_tree = getattr(tool_source, "xml_tree", None)
    return xml_tree.getroot() if xml_tree is not None else None


def _consumer_refs(tool_source: ToolSource, path: str) -> list[ConsumerRef]:
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


def _build_managers(data_manager_conf: str) -> list[ManagerDecl]:
    conf_dir = os.path.dirname(os.path.abspath(data_manager_conf))
    root = parse_xml(data_manager_conf).getroot()
    managers = []
    for dm_elem in root.findall("data_manager"):
        manager_id = dm_elem.get("guid") or dm_elem.get("id") or ""
        # Mirror the attribute and nested forms accepted by DataManager.
        tool_file = dm_elem.get("tool_file")
        if tool_file is None:
            tool_elem = dm_elem.find("tool")
            tool_file = tool_elem.get("file") if tool_elem is not None else None
        tool_file = tool_file or ""
        output_names: frozenset[str] = frozenset()
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


def _raw_column_spec(table_elem: Element) -> tuple[tuple[str, ...], dict[str, int]]:
    """Return ordered names and the loader's parsed name-to-index map."""
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


def _raw_table_decls(tool_data_table_confs: list[str]) -> list[RawTableDecl]:
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


def _has_column_conflict(raw_decls: list[RawTableDecl]) -> bool:
    """Return whether loader merging would reject inconsistent column maps."""
    by_name: dict[str, list[dict[str, int]]] = {}
    for decl in raw_decls:
        specs = by_name.setdefault(decl.name, [])
        if decl.columns not in specs:
            specs.append(decl.columns)
    return any(len(specs) > 1 for specs in by_name.values())


def _repo_backing_path(repo_root: str, filename: str) -> str | None:
    """Find a checked-in loc or installable sample for ``filename``.

    The conventional ``tool-data`` sample fallback applies only to paths rooted at
    ``tool_data_path``; it must not mask a missing ``test-data`` fixture.
    """
    reference = filename if os.path.isabs(filename) else os.path.join(repo_root, filename)
    for candidate in (reference, f"{reference}.sample"):
        if os.path.isfile(candidate):
            return candidate
    if os.path.dirname(os.path.relpath(reference, repo_root)) in ("", os.curdir, "tool-data"):
        shed_sample = os.path.join(repo_root, "tool-data", f"{os.path.basename(filename)}.sample")
        if os.path.isfile(shed_sample):
            return shed_sample
    return None


def _classify_loc_file(path: str) -> LocFile:
    """Record whether a loc file carries any data row and any format comment."""
    has_data = False
    has_comment = False
    # Strip a BOM so it cannot make an empty file look like data.
    with open(path, encoding="utf-8-sig", errors="replace") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                has_comment = True
            else:
                has_data = True
    return LocFile(path=path, has_data=has_data, has_comment=has_comment)


def _discover_loc_files(repo_root: str) -> list[LocFile]:
    """Every ``.loc`` / ``.loc.sample`` file under ``repo_root`` (data rows / comments recorded)."""
    loc_files = []
    for dirpath, _, filenames in os.walk(repo_root):
        for filename in filenames:
            if filename.endswith(".loc") or filename.endswith(".loc.sample"):
                loc_files.append(_classify_loc_file(os.path.join(dirpath, filename)))
    return loc_files


def _build_tables(
    repo_root: str, tool_data_table_confs: list[str], raw_decls: list[RawTableDecl]
) -> tuple[list[TableDecl], list[LocAsset]]:
    # Preserve raw declarations for linting when loader merging would raise.
    if _has_column_conflict(raw_decls):
        return [], []
    # The cast works around invariant list types in ToolDataTableManager's signature.
    tdt_manager = ToolDataTableManager(
        repo_root, config_filename=cast("list[str | os.PathLike[str]]", tool_data_table_confs)
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
            found = bool(info.get("found"))
            backing_path = _repo_backing_path(repo_root, str(filename)) if not found else None
            errors = list(info.get("errors") or ())
            if backing_path:
                # Match the loader's ``${__HERE__}`` expansion while parsing this file.
                table.parse_file_fields(
                    backing_path, errors=errors, here=os.path.dirname(os.path.abspath(backing_path))
                )
            loc_assets.append(
                LocAsset(
                    table_name=table.name,
                    path=str(filename),
                    found=found,
                    is_sample=str(filename).endswith(".sample"),
                    repo_backed=backing_path is not None,
                    errors=tuple(errors),
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
    data_manager_conf: str | None = None,
    tool_data_table_confs: list[str] | None = None,
    consumer_tool_sources: Iterable[tuple[str, ToolSource]] | None = None,
    external_table_names: frozenset[str] = frozenset(),
) -> RepositoryDataTables:
    """Assemble a data-table model from already-discovered repository assets."""
    model = RepositoryDataTables(repo_root=repo_root, external_table_names=external_table_names)
    model.loc_files = _discover_loc_files(repo_root)
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
