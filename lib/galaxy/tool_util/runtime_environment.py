"""Shell checks for runtime requirements, without recording variable values."""

from shlex import quote

from galaxy.tool_util_models.runtime_environment import RuntimeEnvironmentVariable

RUNTIME_ENVIRONMENT_WARNING_FILE = "runtime_environment_warnings"


def required_environment_checks(variables: list[RuntimeEnvironmentVariable], path: str) -> str:
    required = [variable.name for variable in variables if variable.required]
    if not required:
        return ""
    statements = [f": > {quote(path)}"]
    for name in required:
        statements.append(f"if [ \"${{{name}+x}}\" != x ]; then printf '%s\\n' {quote(name)} >> {quote(path)}; fi")
    return "\n".join(statements)
