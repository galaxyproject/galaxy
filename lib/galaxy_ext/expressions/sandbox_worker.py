"""Standalone worker that evaluates one JavaScript program in QuickJS.

This module is deliberately dependency-light: it imports only the standard library
at module load and ``quickjs`` lazily, so it starts quickly and can run inside
a restrictive jail (for example ``bubblewrap``) that has little more than the Python
interpreter and its site-packages available read-only.

Protocol: read one JSON object ``{"program", "timeout", "memory_limit"}`` from stdin
and write one JSON object ``{"result": <value>}`` or ``{"error": <message>}`` to
stdout. ``program`` must yield a JSON string (i.e. end in ``JSON.stringify(...)``) so
its result round-trips as JSON.
"""

import json
import sys

# Bound protocol bytes separately from the QuickJS allocator limit.
MAX_MESSAGE_BYTES = 16 * 1024 * 1024
STACK_LIMIT_BYTES = 1024 * 1024


def run_program(program: str, timeout: float, memory_limit: int) -> str:
    """Evaluate in a fresh context, returning JSON text for the parent to decode."""
    try:
        import quickjs
    except ImportError as e:
        raise RuntimeError("Full JavaScript evaluation requires Python 3.10+ and the quickjs-ng package.") from e

    ctx = quickjs.Context()
    ctx.set_memory_limit(memory_limit)
    ctx.set_time_limit(timeout)
    ctx.set_max_stack_size(STACK_LIMIT_BYTES)
    raw = ctx.eval(program)
    if not isinstance(raw, str):
        # JSON.stringify(undefined) yields JS ``undefined``; treat as null.
        return "null"
    if len(raw) > MAX_MESSAGE_BYTES:
        raise ValueError("Expression result exceeds protocol limit")
    return raw


def main() -> None:
    try:
        payload = sys.stdin.buffer.read(MAX_MESSAGE_BYTES + 1)
        if len(payload) > MAX_MESSAGE_BYTES:
            raise ValueError("Expression request exceeds protocol limit")
        request = json.loads(payload)
        result = run_program(request["program"], request["timeout"], request["memory_limit"])
        # Forward JSON without expanding it into Python objects in the worker.
        response = ('{"result":' + result + "}").encode("utf-8")
        if len(response) > MAX_MESSAGE_BYTES:
            raise ValueError("Expression result exceeds protocol limit")
    except Exception as e:
        response = json.dumps({"error": str(e)[:500]}).encode("utf-8")
    sys.stdout.buffer.write(response)


if __name__ == "__main__":
    main()
