from collections.abc import Mapping

RAW_VALUE_BY_DEFAULT = False


def env_to_statement(env: Mapping[str, object]) -> str:
    """Return the abstraction description of an environment variable definition
    into a statement for shell script.

    >>> env_to_statement(dict(name='X', value='Y'))
    'X="Y"; export X'
    >>> env_to_statement(dict(name='X', value='Y', raw=True))
    'X=Y; export X'
    >>> env_to_statement(dict(name='X', value='"A","B","C"'))
    'X="\\\\"A\\\\",\\\\"B\\\\",\\\\"C\\\\""; export X'
    >>> env_to_statement(dict(file="Y"))
    '. "Y"'
    >>> env_to_statement(dict(file="'RAW $FILE'", raw=True))
    ". 'RAW $FILE'"
    >>> # Source file takes precedence
    >>> env_to_statement(dict(name='X', value='"A","B","C"', file="S"))
    '. "S"'
    >>> env_to_statement(dict(execute="module load java/1.5.1"))
    'module load java/1.5.1'
    """
    if source_file := env.get("file", None):
        assert isinstance(source_file, str)
        return f". {__escape(source_file, env)}"
    if execute := env.get("execute", None):
        assert isinstance(execute, str)
        return execute
    name = env["name"]
    value = env["value"]
    assert isinstance(name, str)
    assert isinstance(value, str)
    value = __escape(value, env)
    return f"{name}={value}; export {name}"


def __escape(value: str, env: Mapping[str, object]) -> str:
    raw = env.get("raw", RAW_VALUE_BY_DEFAULT)
    if not raw:
        value = '"' + value.replace('"', '\\"') + '"'
    return value
