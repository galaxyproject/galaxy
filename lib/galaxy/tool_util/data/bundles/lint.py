"""Repository-level linters over a :class:`RepositoryDataTables` model.

These are the deterministic bundle-contract checks a repository linter (e.g.
Planemo's ``shed_lint``) runs across a data-manager / reference-data repository.
Assembly and path/``.sample`` resolution live in :mod:`repository`; the linters
here only classify the already-resolved model and report through a
:class:`~galaxy.tool_util.lint.LintContext`.

The set is intentionally limited to conditions Planemo can *prove* from
statically resolved evidence:

- a referenced loc fixture is absent (:class:`MissingLocFixture`); and
- a non-comment loc row cannot supply every declared column index
  (:class:`LocRowShape`).

Advisory / unresolved / externally-supplied conditions are handled elsewhere so
they are never reported here as demonstrably missing.
"""

from typing import TYPE_CHECKING

from galaxy.tool_util.data.bundles.repository import RepositoryDataTables
from galaxy.tool_util.lint import Linter

if TYPE_CHECKING:
    from galaxy.tool_util.lint import LintContext


class MissingLocFixture(Linter):
    """A configured table references a loc file that resolves to no file on disk.

    ``LocAsset.found`` already accounts for the ``.sample`` fallback, so a
    sample-backed production loc does not trip this error (only that the
    reference resolves to *something*).
    """

    @classmethod
    def lint(cls, model: RepositoryDataTables, lint_ctx: "LintContext"):
        missing = [asset for asset in model.loc_assets if not asset.found]
        for asset in missing:
            lint_ctx.error(
                f"Data table '{asset.table_name}' references loc file [{asset.path}] which does not exist",
                linter=cls.name(),
            )
        if model.loc_assets and not missing:
            lint_ctx.valid("All referenced loc files resolve", linter=cls.name())


class LocRowShape(Linter):
    """A non-comment loc row cannot supply every declared column index.

    Reuses the row-shape errors captured by ``TabularToolDataTable`` at load
    time (too-few-fields / wrong-separator rows), which already name the offending
    file line and table.
    """

    @classmethod
    def lint(cls, model: RepositoryDataTables, lint_ctx: "LintContext"):
        found_error = False
        for asset in model.loc_assets:
            for message in asset.errors:
                lint_ctx.error(message, linter=cls.name())
                found_error = True
        # Only assets whose file resolved were actually parsed -- an unfound loc has
        # no rows to check, so it must not license a "rows are fine" confirmation.
        checked = [asset for asset in model.loc_assets if asset.found]
        if checked and not found_error:
            lint_ctx.valid("All loc rows supply every declared column", linter=cls.name())


REPOSITORY_DATA_TABLE_LINTERS = (
    MissingLocFixture,
    LocRowShape,
)


def lint_repository_data_tables(model: RepositoryDataTables, lint_ctx: "LintContext") -> None:
    """Run the repository data-table linters over ``model``.

    Each linter is dispatched through ``lint_ctx.lint`` so it is individually
    skippable by name (matching how Planemo drives the tool linters).
    """
    for linter in REPOSITORY_DATA_TABLE_LINTERS:
        lint_ctx.lint(linter.name(), linter.lint, model)
