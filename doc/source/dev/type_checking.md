# Type checking

Galaxy's Python code is type checked with [mypy](https://mypy.readthedocs.io/), configured in `mypy.ini` at the root of the repository.

## Running mypy

Run `make mypy` (or `tox -e mypy`) from the root of Galaxy. This checks `lib/` and `test/` exactly as the "Python linting" CI job does; CI runs it on the oldest and newest supported Python versions. The "Test Galaxy packages" job also runs mypy separately inside each package under `packages/`.

## New code must be fully typed

The following flags are enabled for the whole codebase:

- `disallow_untyped_defs`: every function needs annotations for all its arguments and its return type. Use `-> None` for functions that don't return a value.
- `disallow_any_generics`: generic types need type arguments, e.g. `dict[str, Any]` instead of `dict`, `list[str]` instead of `list`.
- `disallow_untyped_decorators`: a typed function must not be wrapped by an untyped decorator.
- `warn_return_any`: a function declared to return a specific type must not return a value of type `Any` (for example the result of `json.loads()`). Narrow or validate the value, or use `typing.cast()` if you know its type.

A new module is checked with all of these flags, and so is new code in an existing module unless that module has an entry in the legacy list described below.

## The legacy list

Modules that predated these defaults are listed at the end of `mypy.ini`, under the comment "legacy modules that predate the strict defaults". Each entry turns off only the flags that module doesn't pass yet, for example:

```ini
[mypy-galaxy.managers.example]
disallow_untyped_defs = False
```

This list should only get shorter:

- Don't add entries for new modules; annotate the new code instead.
- When you finish typing a module, remove its flags (or its whole section) from the list, and check with `make mypy` that it still passes.

## Test code

Test code is exempt from the strict defaults: `galaxy_test`, `tool_shed.test` and the packages under `test/` (which are seen as `tests.*` in the per-package runs). Annotating tests is still welcome.

## The green list

Modules listed under "green list" in `mypy.ini` are also checked with `disallow_untyped_calls`, which forbids calling functions that are not annotated. This flag isn't enabled globally because it would fail new, fully annotated code that calls into existing untyped code. Adding a fully typed module to the green list is welcome.
