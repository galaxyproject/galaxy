"""Repository-level linters over a :class:`RepositoryDataTables` model.

These are the deterministic bundle-contract checks a repository linter (e.g.
Planemo's ``shed_lint``) runs across a data-manager / reference-data repository.
Assembly and path/``.sample`` resolution live in :mod:`repository`; the linters
here only classify the already-resolved model and report through a
:class:`~galaxy.tool_util.lint.LintContext`.

Every linter here is limited to conditions Planemo can *prove* from statically
resolved evidence -- a referenced loc fixture that is absent, a declared table
nothing configures, a row that cannot fill its columns. Advisory, unresolved, or
externally-supplied conditions are reported as warnings or not at all; they are
never reported here as demonstrably broken. The linters registered with
:func:`lint_repository_data_tables` are listed in
:data:`REPOSITORY_DATA_TABLE_LINTERS`.
"""

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
    """A configured table references a loc file that resolves to no file on disk.

    A reference the repository ships a file for (``LocAsset.repo_backed``) is not
    reported -- either the loc is checked in at its declared path, or a ``.sample``
    ships that Galaxy materializes the real loc from on install. Only a reference the
    loader could not resolve *and* that nothing in the repository backs is a
    demonstrably missing loc. (The loader's own ``found`` answers a different question
    -- resolution against a deployment's ``tool_data_path`` -- so ``repo_backed`` is
    resolved separately; see ``LocAsset.found``.)
    """

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
    """A non-comment loc row cannot supply every declared column index.

    Reports row-shape errors captured by ``TabularToolDataTable`` while parsing
    whichever file backs each reference -- the loader-resolved loc, or the one the
    repository ships (see :func:`~galaxy.tool_util.data.bundles.repository._repo_backing_path`).
    """

    @classmethod
    def lint(cls, model: RepositoryDataTables, lint_ctx: "LintContext"):
        found_error = False
        for asset in model.loc_assets:
            for message in asset.errors:
                lint_ctx.error(message, linter=cls.name())
                found_error = True
        # A backed reference has rows to check; a reference nothing backs does not.
        checked = [asset for asset in model.loc_assets if asset.found or asset.repo_backed]
        if checked and not found_error:
            lint_ctx.valid("All loc rows supply every declared column", linter=cls.name())


# Markers that mean a table name did not fully resolve to a literal after macro /
# token expansion (Cheetah ``$``/``${}``, an undefined ``@TOKEN@``). Such names are
# reported as not-checked rather than demonstrably missing -- see galaxyproject/
# tools-iuc#5003, where raw ``@IDX_DATA_TABLE@`` looks unconfigured but resolves.
_DYNAMIC_MARKERS = ("$", "@", "{", "}")


def _is_literal(name: str) -> bool:
    return bool(name) and not any(marker in name for marker in _DYNAMIC_MARKERS)


class ManagerTableConfigured(Linter[RepositoryDataTables]):
    """A data manager populates a table that nothing in the bundle configures.

    The manager's ``<data_table name="...">`` entries must correspond to a
    configured ``tool_data_table_conf`` table (or a known externally-supplied
    one); an unconfigured target is a broken producer contract (Planemo #706).
    """

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
    """A tool references a data table that no local (or known-external) table defines.

    Only literal, fully-expanded ``from_data_table`` names are checked. Because a
    table may validly be supplied by Galaxy core or another installed repository,
    an unknown reference is a warning, not an error.
    """

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
    """A data-manager ``output_ref`` names an output the expanded wrapper does not declare.

    Only checked when the manager wrapper was actually resolved; an unresolved
    wrapper leaves its outputs unknown, so the reference is not-checked rather
    than reported as demonstrably missing.

    Coverage note: ``output_ref_by_data_table`` keys columns by name, so two
    columns in one ``<data_table>`` sharing a name collapse (last wins) -- the
    same duplicate-column limitation deferred alongside conflicting-schema
    detection also caps output_ref coverage.
    """

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
    """A ``<table>`` declares the same column name more than once.

    The parsed ``columns`` dict silently collapses duplicates, so this is checked
    against the raw declared column list.
    """

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
    """The same table name is declared with different columns/separator/comment across the bundle.

    A column conflict would make the loader raise, so this reads the pre-merge raw
    declarations; a separator/comment-only conflict loads fine but is still
    structurally ambiguous.
    """

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
    """A ``.loc`` / ``.loc.sample`` file is empty and carries no format comment.

    An empty loc file with a leading ``#`` comment documenting the column format is
    the accepted convention (a data manager fills the real rows on install), so a
    documented-but-dataless file is fine; only an empty *and* undocumented file is
    flagged. A warning, not an error: the file is present, just undocumented
    (Planemo #869).
    """

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

# Tables that Galaxy core ships (config/tool_data_table_conf.xml.sample) or that a
# stock data manager provides on essentially every deployment. A repository may consume
# these via from_data_table without defining them locally, so they are treated as
# externally supplied by default; callers extend this set through the
# external_table_names argument (e.g. from a Tool Shed supplier index).
DEFAULT_EXTERNAL_TABLE_NAMES: frozenset[str] = frozenset({"all_fasta", "fasta_indexes", "__dbkeys__"})


def lint_repository_data_tables(model: RepositoryDataTables, lint_ctx: "LintContext") -> None:
    """Run the repository data-table linters over ``model``.

    Each linter is dispatched through ``lint_ctx.lint`` so it is individually
    skippable by name (matching how Planemo drives the tool linters).
    """
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
    """Assemble a repository data-table model from already-discovered paths and lint it.

    The convenience entry point for repository linters (e.g. Planemo's ``shed_lint``):
    the caller does discovery -- which ``data_manager_conf`` / ``tool_data_table_conf``
    files, which consumer tool sources -- and this builds the
    :class:`~galaxy.tool_util.data.bundles.repository.RepositoryDataTables` and runs the
    linters over it.

    Assembly (the discovery-result build) runs inside its own ``lint_ctx.lint`` so its
    skip / assembly-failure diagnostics are actually emitted -- ``LintContext`` only
    flushes messages appended during a dispatched ``lint`` call. The per-table linters
    are then dispatched by :func:`lint_repository_data_tables`, so they must not nest
    inside that same call (which would print them twice).
    """
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
# tool_data_table_conf variants a repository may ship. These describe *different*
# bundles, not alternatives: the test conf points loc files at checked-in test-data,
# the sample conf describes what the shed materializes on install, and a plain conf is
# a checked-in deployment. Each one shipped is a contract the repository makes, so all
# of them are linted -- picking one would leave the others, including the shipped
# bundle that actually reaches a deployment, silently unvalidated.
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
    """Walk ``repo_root`` for loadable tool wrappers that might consume a data table.

    Uses the same directory loader Planemo's ``yield_tool_sources`` is built on;
    tool files that fail to load or are not ordinary tool wrappers are skipped.
    """
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
    """Discover a repository's data-table bundle from ``repo_root`` and lint it.

    The one-call entry point for a repository linter (Planemo's ``shed_lint``, the
    ``galaxy-tool-data-lint`` CLI): it locates the ``data_manager_conf`` and every
    ``tool_data_table_conf.xml*`` variant the repository ships, plus the consumer tool
    sources, then hands them to :func:`lint_repository_data_tables_bundle`. Consumer
    tools are only walked when the repository actually declares a data-table bundle.

    All shipped conf variants are linted together (see
    :data:`TOOL_DATA_TABLE_CONF_NAMES`): each describes a bundle the repository has to
    honour, so a repository with a ``.test`` conf still gets its shipped ``.sample``
    bundle validated. Same-named tables across the variants are merged by the loader
    and must agree on schema -- a disagreement is itself reported, by
    :class:`ConflictingTableSchema`.

    The common Galaxy-core tables (:data:`DEFAULT_EXTERNAL_TABLE_NAMES`) are always
    treated as externally supplied so a bare invocation does not warn on every stock
    ``from_data_table`` reference; ``external_table_names`` adds to that set.
    """
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
