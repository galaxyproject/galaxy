# Repository data-table lint fixtures

Miniature Tool Shed repositories used as **fixtures** (not runtime config) by the
repository data-table linting tests. Each subdirectory is a self-contained repo
laid out the way a real data-manager / reference-data repo is — `data_manager_conf.xml`,
`tool_data_table_conf.xml.*`, `tool-data/*.loc.sample`, `test-data/*.loc`, consumer
tool wrappers — so the tests build real `RepositoryDataTables` models over them with
no mocks (`build_repository_data_tables(...)`).

Consumed by:

- `../test_repository_data_tables.py` — the parser/model builder
- `../test_repository_data_table_lint.py` — the linters
- `../test_data_lint_cli.py` — the `galaxy-tool-data-lint` CLI entry point

## `.gitignore`

Galaxy's top-level `.gitignore` drops `data_manager_conf.xml` and
`shed_data_manager_conf.xml` as runtime config. Here those filenames are fixture
content, so the local `.gitignore` re-includes (`!`) them — otherwise the fixture
repos would be committed incomplete.

## Fixtures

### `fetch_genome_dbkeys_all_fasta/` — the clean, full repo

The one well-formed repo (modeled on IUC's fetch-genome / `all_fasta` data manager);
the happy-path baseline where every linter is expected to pass. Ships extra
`data_manager_conf_*.xml` variants and two consumer wrappers so a single realistic
repo can drive the error cases without a repo-per-case:

- `data_manager_conf.xml` — clean manager (`all_fasta`, `__dbkeys__`)
- `data_manager_conf_bad_output_ref.xml` — `output_ref` to a nonexistent output → `OutputRefValid`
- `data_manager_conf_mixed_output_ref.xml` — one good + one bad ref (per-table iteration)
- `data_manager_conf_missing_wrapper.xml` — `tool_file` points at a missing wrapper (outputs unresolved → not flagged)
- `data_manager_conf_nested_tool.xml` — nested `<tool>` element form (output resolution)
- `tools/consume_all_fasta.xml` — consumer with a **literal** `from_data_table`
- `tools/consume_dynamic_table.xml` — consumer whose `from_data_table` stays **non-literal** after macro expansion (false-positive guard, tools-iuc#5003)

### Missing loc fixtures — `MissingLocFixture`

- `missing_loc/` — conf references a `.loc` that does not exist → one error
- `missing_two/` — two missing locs → two errors
- `sample_fallback/` — production loc resolved via the loader's own `.sample` fallback (`foo.loc.sample`); must **not** be reported missing
- `tool_data_sample/` — Tool Shed layout: conf → `tool-data/bar.loc`, sample ships as `tool-data/bar.loc.sample`. The loader's `.sample` fallback misses this; `sample_backed` must recognize it so reference-data repos aren't falsely flagged.

### Row-shape fixtures — `LocRowShape`

- `broken_rows/` — `broken.loc` with a too-short row and a wrong-separator row → two errors
- `missing_and_broken/` — one missing loc **and** one broken loc; both linters fire and no false "rows are fine" green is emitted off the unparsed missing file

### Empty-loc fixture — `EmptyLocFile`

- `empty_loc/` — ships an empty, comment-less `tool-data/undocumented.loc.sample`
  (the Planemo #869 case → one warning) alongside a header-only
  `tool-data/documented.loc.sample` that must **not** be flagged (a dataless file
  with a format comment is the accepted convention).

### Schema-conflict / duplicate fixtures — `DuplicateColumnNames`, `ConflictingTableSchema`

Each declares the same table twice (or with a repeated column) in a way that would
make the loader's merge raise; assembly must skip the loader and still report cleanly.

- `dup_columns/` — duplicate column name within one table → `DuplicateColumnNames`
- `conflicting_columns/` — same table, different column sets → `ConflictingTableSchema`
- `conflicting_indexes/` — same column names, different index attributes → `ConflictingTableSchema`
- `conflicting_separator/` — same table, different separators → `ConflictingTableSchema`

### Core-table exclusion fixture — `find_and_lint_repository_data_tables`

- `core_table_consumer/` — an index-builder data manager (modeled on IUC
  `data_manager_bwa_mem2_index_builder`) that defines its own `bwa_mem2_indexes`
  table but consumes the core `all_fasta` table via `from_data_table`. The one-call
  `find_and_lint` entry seeds `DEFAULT_EXTERNAL_TABLE_NAMES` (`all_fasta`,
  `fasta_indexes`, `__dbkeys__`), so the core reference must **not** warn; linted
  without that seeding it does, proving the exclusion is what suppresses it.
