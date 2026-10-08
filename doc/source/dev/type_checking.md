# Type checking

Galaxy's Python code is type checked with [mypy](https://mypy.readthedocs.io/) and [ty](https://docs.astral.sh/ty/), configured in `mypy.ini` and `ty.toml` at the root of the repository.

CI runs both checkers during the transition. Ruff enforces annotation presence; mypy (`mypy.ini`) retains the strict-call green list and its Pydantic plugin, while ty adds complementary diagnostics.

## Running ty

Run `make ty` (or `uvx --with tox-uv tox -e ty`) from the root of Galaxy. `make ty` delegates to tox so the checker uses the pinned dependencies in an isolated environment, rather than whichever dependencies happen to be installed in `.venv` or the active shell. This checks `lib/` and `test/` exactly as the "Python linting" CI job does; CI runs it on the oldest and newest supported Python versions. The "Test Galaxy packages" job runs both checkers with each package's dependencies installed. Its mypy runs retain isolated source roots; ty resolves Galaxy imports against the repository's `lib/` tree and therefore does not provide the same package isolation.

The per-package ty runs go through `.ci/ty_check.sh`, because the `packages/*/src` directories are symlinks into `lib/` and ty does not follow symlinks when it walks a directory. The shell entry point delegates file discovery to `.ci/ty_check.py` for portability and propagates discovery failures. The tox environment uses the same helper: it passes the files of `lib/galaxy/tools/bundled` (a symlink to `tools/`) explicitly for the same reason, so that they keep their `galaxy.tools.*` module names.

## The strict defaults

The following rules are enabled globally; they are the ty equivalents of mypy's strict defaults (which are also noted as comments in `ty.toml`):

| ty rule | mypy flag |
|---|---|
| `missing-type-argument` | `disallow_any_generics` |
| `dynamic-function-decorator-return` | `disallow_untyped_decorators` |
| `unsound-return-statement` | `warn_return_any` |
| `unsupported-dynamic-base` | `disallow_subclassing_any` |
| `analysis.strict-equality-semantics` | `strict_equality` |
| `unresolved-import = "ignore"` | `ignore_missing_imports` |

ty has no equivalent of mypy's `disallow_untyped_defs` and `check_untyped_defs`: it always checks the bodies of unannotated functions, and it does not require annotations at all. Ruff's `ANN` rules enforce parameter and return annotations independently of the type checker. Explicit `Any` is allowed (`ANN401` is disabled), and an `__init__` with an annotated parameter may omit its return annotation, matching mypy. Tests remain exempt. Existing violations are baselined by exact file path and rule in `ruff.toml`; remove each exception when the file satisfies that rule, and do not add exceptions for new modules. These exceptions apply to the whole file, so the exempted rules also permit missing annotations in new functions added to that file. Mypy continues to enforce its annotation requirements too. Likewise there are no equivalents of `warn_unreachable`, `no_implicit_reexport` and the `disallow_untyped_calls` "green list".

Ruff's configuration and annotation baseline live in `ruff.toml`. Run `uvx --with tox-uv tox -e ruff_exemptions` to report stale annotation exemptions, or append `-- --fix` to remove them. A weekly GitHub workflow opens a pull request with those removals. Pruning preserves the test policy exemptions and never adds exemptions; it removes individual rules and drops a file entry when none remain. Ruff parses source without importing dependencies, so this job only needs the pinned lint dependencies and a single Python environment.

Test code is exempt from the strict rules above, as it was under mypy. The regular diagnostics ty reports in test code are handled through the exemption list like everywhere else.

## The exemption list

Modules that still fail a rule are listed in the generated section of `ty.toml`, one block per rule, each block listing the files that fail it:

```toml
[[overrides]]
include = [
    "lib/galaxy/managers/example.py",
]

[overrides.rules]
unresolved-attribute = "ignore"
```

This list should only get shorter:

- Don't add entries for new modules; annotate the new code instead.
- When you finish typing a module, remove its entries from the list, and check with `make ty` that it still passes.

`tox -e ty_exemptions` keeps the list fresh: it runs ty everywhere `make ty` and `packages/test.sh` do, then reports the entries whose files no longer fail their rule (and the diagnostics that fail without an entry). `tox -e ty_exemptions -- --fix` also removes the stale entries from `ty.toml`. This takes a few minutes, since it runs ty once per package. A weekly GitHub workflow runs it on `dev` and opens a pull request removing stale entries, so you don't need to run it for your pull requests.

## Running mypy alongside ty

Both checkers run in CI and can be run locally:

```sh
make ty
make mypy  # or: tox -e mypy
```

`mypy.ini` and `.ci/check_mypy_legacy_list.py` (`tox -e mypy_legacy`) are untouched, so mypy's red list can still be pruned while it is around. The weekly mypy red-list pruning workflow is retained too. Their rule sets are not identical, so a module can pass one checker and fail the other; the exemption lists are independent.
