
## Verify changes

Run these **before committing or when verifying changes**:

| What | Command |
|---|---|
| Format check | `uvx --with tox-uv tox -e format` |
| Lint (ruff + flake8) | `uvx --with tox-uv tox -e lint` |
| Type check | `uvx --with tox-uv tox -e ty` (mypy is still available as `uvx --with tox-uv tox -e mypy`) |
| Unit tests | `uvx --with tox-uv tox -e unit` or `uvx --with tox-uv tox -e unit-coverage` |

All at once: `uvx --with tox-uv tox -e format -e lint -e ty -e unit`

`--with tox-uv` matters: it makes tox build environments with `uv` instead of
`virtualenv` + `pip`, which is roughly 5x faster on environment setup. This is
also what CI does (see `.github/workflows/`). Plain `uvx tox` omits the plugin
and falls back to the slow path. If you prefer a persistent binary, use
`uv tool install tox --with tox-uv` and then invoke `tox` directly.

## Running specific tests

```bash
# Single unit test file (fast, no tox boilerplate)
PYTHONPATH=lib pytest test/unit/test_toolbox.py -v

# API tests (requires Galaxy server setup)
./run_tests.sh -api

# Tool framework tests
./run_tests.sh -framework

# Client tests
make client-test
```

## Code conventions

- Python >= 3.10 style (match existing patterns)
- No unused imports (CI runs `autoflake`/`isort`)
