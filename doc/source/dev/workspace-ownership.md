# Workspace Ownership

This repository is a uv workspace: runtime and test code lives in distributions
under `packages/`, and the workspace root keeps only cross-cutting test
infrastructure (`lib/galaxy_test`, `test/`). The rule established by the
symlink-elimination work is:

- Every import root is owned by exactly one distribution, and the owning
  distribution ships that code as **real files** under `packages/<name>/src`.
- Retained fixture and asset symlinks are documented below.

## Import root → distribution

Generated from `ls packages/*/src`:

| Import root(s) | Distribution | Package directory |
| --- | --- | --- |
| `galaxy.util`, `galaxy.exceptions`, `galaxy.version` | `galaxy-util` | `packages/util` |
| `galaxy.config` | `galaxy-config` | `packages/config` |
| `galaxy.datatypes`, `galaxy.model`, `galaxy.quota`, `galaxy.security` | `galaxy-data` | `packages/data` |
| `galaxy.files` | `galaxy-files` | `packages/files` |
| `galaxy.job_execution`, `galaxy.metadata` | `galaxy-job-execution` | `packages/job_execution` |
| `galaxy.job_metrics` | `galaxy-job-metrics` | `packages/job_metrics` |
| `galaxy.navigation` | `galaxy-navigation` | `packages/navigation` |
| `galaxy.objectstore` | `galaxy-objectstore` | `packages/objectstore` |
| `galaxy.schema` | `galaxy-schema` | `packages/schema` |
| `galaxy.auth` | `galaxy-auth` | `packages/auth` |
| `galaxy.tours` | `galaxy-tours` | `packages/tours` |
| `galaxy.selenium` | `galaxy-selenium` | `packages/selenium` |
| `galaxy.tool_util` | `galaxy-tool-util` | `packages/tool_util` |
| `galaxy.tool_util_models` | `galaxy-tool-util-models` | `packages/tool_util_models` |
| `galaxy.web` | `galaxy-web-framework` | `packages/web_framework` |
| `galaxy.web_stack` | `galaxy-web-stack` | `packages/web_stack` |
| `galaxy.webapps` | `galaxy-web-apps` | `packages/web_apps` |
| `galaxy.web_client` | `galaxy-web-client` | `packages/web_client` |
| `galaxy` remainder (`actions`, `agents`, `app`, `authnz`, `carbon_emissions`, `celery`, `config_watchers`, `dependencies`, `di`, `forms`, `jobs`, `main`, `main_config`, `managers`, `queue_worker`, `queues`, `short_term_storage`, `sse_monitor`, `structured_app`, `tool_shed`, `tools`, `visualization`, `webhooks`, `work`, `workflow`) plus `galaxy_ext` (regular package: `container_monitor`, `expressions`, `metadata`) | `galaxy-app` | `packages/app` |
| `tool_shed` | `galaxy-tool-shed` | `packages/tool_shed` |
| `tool_shed_client` | `galaxy-tool-shed-schema` | `packages/tool_shed_schema` |
| `galaxy_test.api` | `galaxy-test-api` | `packages/test_api` |
| `galaxy_test.base` | `galaxy-test-base` | `packages/test_base` |
| `galaxy_test.driver` | `galaxy-test-driver` | `packages/test_driver` |
| `galaxy_test.selenium` | `galaxy-test-selenium` | `packages/test_selenium` |
| (no `src`; metapackage manifest has no runtime dependencies) | `galaxy` (metapackage) | `packages/meta` |

Notes:

- `galaxy.tool_shed` (the Galaxy-side integration under `packages/app`) is
  distinct from the top-level `tool_shed` package owned by
  `galaxy-tool-shed`.
- `tool_shed_client` is owned **only** by `galaxy-tool-shed-schema`; the
  former alias under `packages/app/src/tool_shed_client` was removed.
- `galaxy_ext` is a regular (non-stub) package shipped inside `galaxy-app`,
  not a link into `lib/`.

## Test ownership

Package-owned unit tests live in `packages/*/tests`, mirroring the `src`
layout of the owning distribution (generated from `ls packages/*/tests`):

| Package directory | `tests/` contents |
| --- | --- |
| `packages/app` | `agents`, `app`, `scripts`, `tools`, `workflow`, `workflows` |
| `packages/auth` | `auth` |
| `packages/config` | `config` |
| `packages/data` | `data`, `model` |
| `packages/files` | `files` |
| `packages/job_execution` | `job_execution` |
| `packages/job_metrics` | `job_metrics` |
| `packages/objectstore` | `objectstore` |
| `packages/schema` | `schema` |
| `packages/selenium` | `seleniumtests` |
| `packages/test_base` | `test_base` |
| `packages/test_driver` | `test_driver` |
| `packages/tool_shed` | `tool_shed` |
| `packages/tool_shed_schema` | `tool_shed_schema` |
| `packages/tool_util` | `tool_util` |
| `packages/tool_util_models` | `tool_util_models` |
| `packages/util` | `util` |
| `packages/web_apps` | `authnz`, `webapps` |
| `packages/web_client` | `test_packaging.py` |
| `packages/web_framework` | `web_framework` |
| `packages/web_stack` | `web_stack` |

Workspace-root test trees are **not** owned by any distribution; they stay at
the root because they test root-owned infrastructure or the composed
workspace:

- `test/unit/test_shard.py`, `test/unit/test_galaxy_transactions.py` (and
  `test/unit/__init__.py`) — unit tests for the retained root infrastructure
  described below.
- `test/functional`, `test/integration`, `test/integration_selenium`,
  `test/deployment`, `test/manual`, `test/evals` — workspace-level test trees
  (functional tools, webhooks, composed-app tests).

## Symlink disposition

Top-level package source and test aliases have been replaced with real files.
Links retained for shared fixtures, executable assets, frontend resources, and
package metadata are either relocated with their owners or retargeted to the
new package paths. The Tool Shed Mercurial fixture retains its tracked
`.hg/wcache/checklink` probe and all repository metadata.

Use `git ls-files -s` to inspect the current inventory; the enforcement check
below covers every tracked link under package source and test directories.

Three tracked symlinks are **intentionally dangling** (verified with
`test -e`): `doc/source/_static/22.01-colour.mp4` and
`doc/source/_static/22.01-export.mp4` point at release media that is not
committed to the repository, and `test/functional/webhooks/tour_generator`
points at the `demo/tour_generator` webhook plugin that is not present in the
tree. They are kept because they resolve in release/deployment contexts.

## Allowed source links

The only symlinks permitted under `packages/*/src/**` or
`packages/*/tests/**` are listed here:

| Category | Count | Links | Target |
| --- | --- | --- | --- |
| Nested fixture links | 34 | `packages/data/src/galaxy/datatypes/test/*` (31), `packages/app/src/galaxy/tools/parameters/test/*` (3) | shared `test-data/` fixtures |
| Mercurial fixture probe | 1 | `packages/tool_shed/tests/tool_shed/data/toolshed_community_files/database/community_files/000/repo_1/.hg/wcache/checklink` | `checklink-target` in the same fixture directory |
| `functional_tools` chain | 1 | `packages/tool_util/src/galaxy/tool_util/unittest_utils/functional_tools` | `test/functional/tools` |
| `bundled` chain | 1 | `packages/app/src/galaxy/tools/bundled` | `tools` |
| `static` chain | 1 | `packages/web_apps/src/galaxy/webapps/base/static` | `static` |
| `templates` chain | 1 | `packages/web_apps/src/galaxy/webapps/base/templates` | `templates` |
| `maf` chain | 1 | `packages/app/src/galaxy/tools/util/maf_utilities.py` | `packages/data/src/galaxy/datatypes/util/maf_utilities.py` |
| `navigation` chain | 1 | `packages/navigation/src/galaxy/navigation/navigation.yml` | `client/src/utils/navigation/navigation.yml` |
| `linters` chain | 1 | `packages/tool_util/src/galaxy/tool_util/linters/datatypes_conf.xml.sample` | `packages/config/src/galaxy/config/sample/datatypes_conf.xml.sample` |
| `main` chain | 1 | `packages/app/src/galaxy/main/__init__.py` | `scripts/galaxy-main` |

Package-owned Python sources are real files; the links above retain shared
fixtures and assets.

## `lib/galaxy_test` remainder

The following files provide repository-level test infrastructure:

- `lib/galaxy_test/conftest.py`
- `lib/galaxy_test/shard.py`
- `lib/galaxy_test/shard_durations.json`
- `lib/galaxy_test/performance/`
- `lib/galaxy_test/workflow/`
- `test/unit/test_shard.py`, `test/unit/test_galaxy_transactions.py`,
  `test/unit/test_package_versions.py`, `test/unit/__init__.py`

Rationale:

1. **Dependency direction.** `shard.py` implements workspace-wide CI
   sharding: it groups tests by the Galaxy instance they boot, keeps whole
   test classes together, and packs shards longest-first using the recorded
   per-group durations in `shard_durations.json`. To do that it must observe
   tests from *every* distribution plus the root trees. Hosting it inside any
   one distribution would make that distribution depend on all others,
   inverting the dependency DAG the packages encode.
2. **Root pytest conftest.** `conftest.py` provides the session-scoped
   fixtures for tests invoked from the workspace root (the Galaxy test
   driver, celery pytest plugin registration, and the statsd/JSON-report
   hooks). `pytest.ini` puts `lib` on `pythonpath`, so these apply to the
   retained root trees. The package-owned API and Selenium conftests import
   their shared fixtures and hooks explicitly. Their imports also require the
   installed Galaxy test and application packages.
3. **Cross-cutting test trees.** `performance/` and `workflow/` exercise the
   composed workspace (the workflow framework alone spans `galaxy-tool-util`,
   `galaxy-data`, `galaxy-job-execution`, and `galaxy-app`), so no single
   distribution owns them.
4. **Mirrored unit tests.** `test/unit/test_shard.py` unit-tests root-owned
   `shard.py`, and `test_galaxy_transactions.py` covers transaction handling
   of the composed app; both subjects live at the root, so their tests do
   too.
5. **No payoff.** These files already resolve via `pytest.ini`
   (`pythonpath = lib .`). They test the composed application and remain
   outside the independently distributed package test suites.

## Inspecting the layout

To regenerate the tables in this document:

```sh
git ls-files -s | grep ^120000        # tracked symlinks (paths and modes)
ls packages/*/src                     # import roots per distribution
ls packages/*/tests                   # package-owned tests
ls lib/galaxy_test test/unit          # retained root test infrastructure
```
