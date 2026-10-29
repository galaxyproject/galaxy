"""Runtime declarations and shell checks, without recording variable values."""

import logging
from collections.abc import Iterable
from shlex import quote

from galaxy.tool_util_models.runtime_environment import RuntimeEnvironmentVariable

log = logging.getLogger(__name__)


def parse_runtime_environment_variables(
    entries: Iterable[object], *, strict: bool = True
) -> list[RuntimeEnvironmentVariable]:
    variables = []
    for entry in entries:
        try:
            variables.append(RuntimeEnvironmentVariable.model_validate(entry))
        except ValueError as exc:
            if strict:
                raise
            log.warning("Ignoring invalid runtime environment declaration: %s", exc)
    return variables


RUNTIME_ENVIRONMENT_WARNING_FILE = "runtime_environment_warnings"


def required_variable_names(variables: Iterable[RuntimeEnvironmentVariable]) -> list[str]:
    return [variable.name for variable in variables if variable.required]


def required_environment_checks(variables: list[RuntimeEnvironmentVariable], path: str) -> str:
    required = required_variable_names(variables)
    if not required:
        return ""
    statements = [f": > {quote(path)}"]
    for name in required:
        statements.append(f"if [ \"${{{name}+x}}\" != x ]; then printf '%s\\n' {quote(name)} >> {quote(path)}; fi")
    # The check runs inside the tool container, where the warning path may not be
    # writable. A failed redirection on ``:`` exits a POSIX shell, so isolate it.
    body = "\n".join(statements)
    return f"(\n{body}\n) 2>/dev/null || :"
