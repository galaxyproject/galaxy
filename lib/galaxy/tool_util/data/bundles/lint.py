"""Repository-level linters for data-table bundles."""

import os
from collections.abc import Iterable
from typing import (
    TYPE_CHECKING,
)

from galaxy.tool_util.data.bundles.repository import (
    build_repository_data_tables,
    RepositoryDataTables,
)
from galaxy.tool_util.lint import Linter
from galaxy.tool_util.loader_directory import (
    is_tool_load_error,
    load_tool_sources_from_path,
)
from galaxy.tool_util.parser.interface import ToolSource
from galaxy.util import unicodify

if TYPE_CHECKING:
    from galaxy.tool_util.lint import LintContext


class MissingLocFixture(Linter[RepositoryDataTables]):
    """Report loc references absent from both the loader and repository."""

    @classmethod
    def lint(cls, model: RepositoryDataTables, lint_ctx: "LintContext"):
        missing = [asset for asset in model.loc_assets if not asset.found and not asset.repo_backed]
        for asset in missing:
            lint_ctx.error(
                f"Data table '{asset.table_name}' references loc file [{asset.path}] which does not exist",
                linter=cls.name(),
            )
        if model.loc_assets and not missing:
            lint_ctx.valid("All referenced loc files resolve", linter=cls.name())


class LocRowShape(Linter[RepositoryDataTables]):
    """Report loc rows that cannot supply every declared column."""

    @classmethod
    def lint(cls, model: RepositoryDataTables, lint_ctx: "LintContext"):
        found_error = False
        for asset in model.loc_assets:
            for message in asset.errors:
                lint_ctx.error(message, linter=cls.name())
                found_error = True
        checked = [asset for asset in model.loc_assets if asset.found or asset.repo_backed]
        if checked and not found_error:
            lint_ctx.valid("All loc rows supply every declared column", linter=cls.name())


# Unexpanded Cheetah or XML-macro names cannot prove a table is missing.
_DYNAMIC_MARKERS = ("$", "@", "{", "}")


def _is_literal(name: str) -> bool:
    return bool(name) and not any(marker in name for marker in _DYNAMIC_MARKERS)


class ManagerTableConfigured(Linter[RepositoryDataTables]):
    """Report manager-produced tables with no known configuration."""

    @classmethod
    def lint(cls, model: RepositoryDataTables, lint_ctx: "LintContext"):
        known = model.configured_table_names | model.external_table_names
        clean = True
        for manager in model.managers:
            for table_name in manager.processor.data_table_names:
                if not _is_literal(table_name):
                    continue
                if table_name not in known:
                    lint_ctx.error(
                        f"Data manager '{manager.id}' populates table '{table_name}' but no local "
                        "tool_data_table configuration defines it",
                        linter=cls.name(),
                    )
                    clean = False
        if model.managers and clean:
            lint_ctx.valid("All data-manager tables are locally configured", linter=cls.name())


class ConsumerTableDefined(Linter[RepositoryDataTables]):
    """Warn about literal consumer references with no known definition."""

    @classmethod
    def lint(cls, model: RepositoryDataTables, lint_ctx: "LintContext"):
        known = model.configured_table_names | model.external_table_names
        checked = False
        clean = True
        for consumer in model.consumers:
            name = consumer.table_name
            if not _is_literal(name):
                continue
            checked = True
            if name not in known:
                lint_ctx.warn(
                    f"Tool '{consumer.tool_id}' references data table '{name}' via {consumer.kind}, but no "
                    "local configuration defines it (it may be supplied by Galaxy core or another repository)",
                    linter=cls.name(),
                )
                clean = False
        if checked and clean:
            lint_ctx.valid("All literal from_data_table references resolve locally", linter=cls.name())


class OutputRefValid(Linter[RepositoryDataTables]):
    """Report ``output_ref`` values absent from a resolved manager wrapper."""

    @classmethod
    def lint(cls, model: RepositoryDataTables, lint_ctx: "LintContext"):
        checked = False
        clean = True
        for manager in model.managers:
            if not manager.wrapper_resolved:
                continue
            outputs = manager.tool_output_names
            for table_name, refs in manager.processor.output_ref_by_data_table.items():
                for column_name, output_ref in refs.items():
                    checked = True
                    if output_ref not in outputs:
                        declared = ", ".join(sorted(outputs)) or "none"
                        lint_ctx.error(
                            f"Data manager '{manager.id}' table '{table_name}' column '{column_name}' has "
                            f"output_ref '{output_ref}', which is not an output of the manager tool "
                            f"(declared outputs: {declared})",
                            linter=cls.name(),
                        )
                        clean = False
        if checked and clean:
            lint_ctx.valid("All data-manager output_ref values name real wrapper outputs", linter=cls.name())


class DuplicateColumnNames(Linter[RepositoryDataTables]):
    """Report duplicate column names in raw table declarations."""

    @classmethod
    def lint(cls, model: RepositoryDataTables, lint_ctx: "LintContext"):
        clean = True
        for decl in model.raw_table_decls:
            seen = set()
            duplicates = []
            for name in decl.column_names:
                if name in seen and name not in duplicates:
                    duplicates.append(name)
                seen.add(name)
            if duplicates:
                dupes = ", ".join(duplicates)
                lint_ctx.error(
                    f"Data table '{decl.name}' declares duplicate column name(s): {dupes}",
                    linter=cls.name(),
                )
                clean = False
        if model.raw_table_decls and clean:
            lint_ctx.valid("No data table declares duplicate column names", linter=cls.name())


class ConflictingTableSchema(Linter[RepositoryDataTables]):
    """Report incompatible schemas declared for the same table."""

    @classmethod
    def lint(cls, model: RepositoryDataTables, lint_ctx: "LintContext"):
        by_name: dict[str, list] = {}
        for decl in model.raw_table_decls:
            by_name.setdefault(decl.name, []).append(decl)
        conflicted = False
        for name, decls in by_name.items():
            schemas = {(tuple(sorted(decl.columns.items())), decl.separator, decl.comment_char) for decl in decls}
            if len(schemas) > 1:
                lint_ctx.error(
                    f"Data table '{name}' is declared with conflicting schemas across the bundle "
                    f"({len(decls)} definitions do not agree on columns/separator/comment_char)",
                    linter=cls.name(),
                )
                conflicted = True
        if model.raw_table_decls and not conflicted:
            lint_ctx.valid("Each data table is declared with a single consistent schema", linter=cls.name())


class EmptyLocFile(Linter[RepositoryDataTables]):
    """Warn when an empty loc file has no format comment."""

    @classmethod
    def lint(cls, model: RepositoryDataTables, lint_ctx: "LintContext"):
        undocumented = [loc for loc in model.loc_files if not loc.has_data and not loc.has_comment]
        for loc in undocumented:
            rel = os.path.relpath(loc.path, model.repo_root)
            lint_ctx.warn(
                f"Location file [{rel}] is empty and has no comment describing the expected "
                "column format; add a comment documenting the format",
                linter=cls.name(),
            )
        if model.loc_files and not undocumented:
            lint_ctx.valid("All loc files carry data or a documenting comment", linter=cls.name())


REPOSITORY_DATA_TABLE_LINTERS = (
    MissingLocFixture,
    LocRowShape,
    ManagerTableConfigured,
    ConsumerTableDefined,
    OutputRefValid,
    DuplicateColumnNames,
    ConflictingTableSchema,
    EmptyLocFile,
)

# Common tables supplied outside the repository under lint.
DEFAULT_EXTERNAL_TABLE_NAMES: frozenset[str] = frozenset({"all_fasta", "fasta_indexes", "__dbkeys__"})


def lint_repository_data_tables(model: RepositoryDataTables, lint_ctx: "LintContext") -> None:
    """Run each skippable repository data-table linter over ``model``."""
    for linter in REPOSITORY_DATA_TABLE_LINTERS:
        lint_ctx.lint(linter.name(), linter.lint, model)


def lint_repository_data_tables_bundle(
    lint_ctx: "LintContext",
    repo_root: str,
    data_manager_conf: str | None = None,
    tool_data_table_confs: list[str] | None = None,
    consumer_tool_sources: Iterable[tuple[str, "ToolSource"]] | None = None,
    external_table_names: frozenset[str] = frozenset(),
) -> None:
    """Assemble and lint a model from already-discovered repository assets."""
    model: RepositoryDataTables | None = None

    def assemble(_unused_target, lint_ctx: "LintContext") -> None:
        nonlocal model
        if not data_manager_conf and not tool_data_table_confs:
            lint_ctx.info("No data manager or tool data table configuration found, skipping data table linting.")
            return
        try:
            model = build_repository_data_tables(
                repo_root,
                data_manager_conf=data_manager_conf,
                tool_data_table_confs=tool_data_table_confs,
                consumer_tool_sources=consumer_tool_sources,
                external_table_names=external_table_names,
            )
        except Exception as e:
            lint_ctx.error(f"Problem assembling repository data table model [{unicodify(e)}]")

    lint_ctx.lint("lint_data_tables_bundle", assemble, None)
    if model is not None:
        lint_repository_data_tables(model, lint_ctx)


DATA_MANAGER_CONF = "data_manager_conf.xml"
# Each shipped configuration describes a distinct bundle that must be linted.
TOOL_DATA_TABLE_CONF_NAMES = (
    "tool_data_table_conf.xml.test",
    "tool_data_table_conf.xml.sample",
    "tool_data_table_conf.xml",
)


def _find_data_manager_conf(repo_root: str) -> str | None:
    candidate = os.path.join(repo_root, DATA_MANAGER_CONF)
    return candidate if os.path.exists(candidate) else None


def _find_tool_data_table_confs(repo_root: str) -> list[str]:
    """Every ``tool_data_table_conf.xml*`` variant the repository ships."""
    candidates = [os.path.join(repo_root, name) for name in TOOL_DATA_TABLE_CONF_NAMES]
    return [candidate for candidate in candidates if os.path.exists(candidate)]


def _discover_consumer_tool_sources(repo_root: str) -> list[tuple[str, "ToolSource"]]:
    """Find loadable tool wrappers that might consume a data table."""
    sources: list[tuple[str, ToolSource]] = []
    for tool_path, tool_source in load_tool_sources_from_path(repo_root, recursive=True, register_load_errors=True):
        if is_tool_load_error(tool_source):
            continue
        if not isinstance(tool_source, ToolSource):
            continue
        sources.append((tool_path, tool_source))
    return sources


def find_and_lint_repository_data_tables(
    lint_ctx: "LintContext",
    repo_root: str,
    external_table_names: frozenset[str] = frozenset(),
) -> None:
    """Discover and lint every data-table configuration in ``repo_root``."""
    external_table_names = DEFAULT_EXTERNAL_TABLE_NAMES | external_table_names
    data_manager_conf = _find_data_manager_conf(repo_root)
    tool_data_table_confs = _find_tool_data_table_confs(repo_root)
    consumer_tool_sources = None
    if data_manager_conf or tool_data_table_confs:
        consumer_tool_sources = _discover_consumer_tool_sources(repo_root)
    lint_repository_data_tables_bundle(
        lint_ctx,
        repo_root,
        data_manager_conf=data_manager_conf,
        tool_data_table_confs=tool_data_table_confs or None,
        consumer_tool_sources=consumer_tool_sources,
        external_table_names=external_table_names,
    )
