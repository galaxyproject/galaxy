"""A sandboxed JavaScript engine for evaluating CWL/ECMAScript expressions.

Galaxy evaluates workflow ``when`` expressions and expression-tool scripts in a
fresh QuickJS context in a Python subprocess. No host bindings are exposed to JS.
The parent deadline also covers exception formatting, serialization and teardown.
This engine registers with ``cwl_utils`` so full JavaScript evaluations use the
worker while simple parameter references continue to resolve in Python.
"""

import functools
import json
import logging
import os
import platform
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
from collections.abc import Sequence
from typing import (
    Any,
    cast,
)

from cwl_utils.errors import JavascriptException
from cwl_utils.sandboxjs import (
    default_timeout,
    NodeJSEngine,
    set_js_engine,
)
from cwl_utils.types import CWLOutputType

from galaxy_ext.expressions import sandbox_worker
from galaxy_ext.expressions.sandbox_worker import MAX_MESSAGE_BYTES

# QuickJS allocator limit per evaluation, not a cap on Python RSS or aggregate
# memory: protocol decoding in the parent and concurrent workers add overhead.
MEMORY_LIMIT_BYTES = 200 * 1024 * 1024

# Absolute path to the out-of-process worker, launched under an isolation command
# (e.g. bubblewrap) when one is configured. It is run by path rather than with
# ``-m`` so it works even when ``galaxy_ext`` is not importable in a bare subprocess
# (e.g. run-from-source deployments that add lib/ to sys.path without exporting
# PYTHONPATH). The worker itself imports no Galaxy code.
WORKER_SCRIPT = os.path.abspath(sandbox_worker.__file__)

# Extra time granted to the jailed subprocess over the in-VM timeout before it is
# hard-killed, so the QuickJS timeout normally fires first with a clean error.
SUBPROCESS_GRACE_SECONDS = 10.0

# Config values that select the built-in bubblewrap recipe instead of a literal command.
BUBBLEWRAP_KEYWORDS = frozenset({"bubblewrap", "bwrap"})

# System paths the worker's interpreter and the QuickJS extension may need
# (dynamic linker, shared libraries, binaries). Bound read-only and best-effort, so a
# path missing on a given distro (e.g. merged-/usr where /lib is a symlink) is skipped.
BUBBLEWRAP_SYSTEM_PATHS = (
    "/usr",
    "/lib",
    "/lib64",
    "/bin",
    "/sbin",
    "/etc/ld.so.cache",
    "/etc/ld.so.preload",
)

log = logging.getLogger(__name__)


def _bubblewrap_command(bwrap: str) -> tuple[str, ...]:
    """Build the built-in bubblewrap jail command.

    Read-only-binds only what the worker needs to run -- the Python runtime, the
    worker script, and the system libraries/binaries -- and gives it ``/proc``, a
    minimal ``/dev`` and a private writable ``/tmp``. Galaxy's config, database, home
    directory and the rest of the filesystem are deliberately NOT mounted, so even a
    compromised worker cannot read secrets from disk. The environment is cleared and
    the PID/IPC/UTS namespaces are unshared. The Python interpreter and worker script
    are appended by the caller.

    The network namespace is intentionally NOT unshared: ``--unshare-net`` makes bwrap
    bring up a loopback interface, which requires privileges not available in many
    container/CI hosts (``bwrap: loopback: Failed RTM_NEWADDR: Operation not
    permitted``) -- and Galaxy is frequently deployed in such environments. Operators
    who can unshare the network, or who want stricter egress control, can add
    ``--unshare-net`` (or enforce egress at the network layer) via a custom command.
    """
    # Bind the Python installation (base + any virtualenv) and the worker script; these
    # cover the interpreter, its standard library, and the QuickJS extension
    # regardless of whether Galaxy runs from a venv, a system install, or a conda env.
    # sys.executable is often a symlink (a venv, or uv's standalone Python) whose real
    # binary and shared libraries live in a separate tree outside sys.prefix/base_prefix;
    # resolve it and bind that tree too, so the interpreter can be exec'd and loaded
    # inside the jail rather than failing with "execvp ...: No such file or directory".
    real_executable = os.path.realpath(sys.executable)
    real_executable_root = os.path.dirname(os.path.dirname(real_executable))
    ro_binds = [
        sys.base_prefix,
        sys.prefix,
        real_executable,
        real_executable_root,
        WORKER_SCRIPT,
        *BUBBLEWRAP_SYSTEM_PATHS,
    ]
    args = [
        "--unshare-pid",
        "--unshare-ipc",
        "--unshare-uts",
        "--die-with-parent",
        "--new-session",
        "--clearenv",
    ]
    seen: set[str] = set()
    for path in ro_binds:
        if path and path not in seen:
            seen.add(path)
            args += ["--ro-bind-try", path, path]
    # A fresh private tmpfs (not the host /tmp) for anything that needs scratch space;
    # TMPDIR is set explicitly since --clearenv wiped it, so tempfile resolves here.
    args += [
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--setenv",
        "TMPDIR",
        "/tmp",
        "--chdir",
        "/tmp",
    ]
    return (bwrap, *args)


@functools.cache
def resolve_isolation_command(setting: str) -> tuple[str, ...] | None:
    """Resolve the ``expression_evaluation_isolation_command`` setting to a wrapper.

    - empty -> ``None`` (ordinary worker subprocess)
    - ``"bubblewrap"``/``"bwrap"`` -> the built-in bubblewrap command, but only on
      Linux with ``bwrap`` on PATH; otherwise ``None`` (ordinary worker subprocess) with a one-time
      warning, so a macOS dev box or a host without bubblewrap degrades cleanly
    - anything else -> the value parsed as a literal command prefix, used as-is

    Cached so the PATH lookup and any warning happen once per distinct setting.
    """
    setting = (setting or "").strip()
    if not setting:
        return None
    if setting.lower() in BUBBLEWRAP_KEYWORDS:
        if platform.system() != "Linux":
            log.warning(
                "Expression isolation %r is only supported on Linux; using an ordinary expression worker subprocess.",
                setting,
            )
            return None
        bwrap = shutil.which("bwrap")
        if bwrap is None:
            log.warning(
                "Expression isolation requested but 'bwrap' (bubblewrap) was not found on PATH; "
                "using an ordinary expression worker subprocess."
            )
            return None
        return _bubblewrap_command(bwrap)
    return tuple(shlex.split(setting))


def evaluate_program(
    program: str,
    timeout: float = default_timeout,
    sandbox_command: Sequence[str] | None = None,
) -> CWLOutputType:
    """Run JS in a fresh worker, optionally prefixed with an isolation command.

    ``program`` must yield JSON text as its final value. The parent enforces a
    wall-clock deadline even if QuickJS hangs outside its CPU interrupt handler.
    """
    return _evaluate_in_subprocess(program, timeout, sandbox_command or ())


def _evaluate_in_subprocess(program: str, timeout: float, sandbox_command: Sequence[str]) -> CWLOutputType:
    argv = [*sandbox_command, sys.executable, WORKER_SCRIPT]
    if len(program) > MAX_MESSAGE_BYTES:
        raise JavascriptException("Expression request exceeds protocol limit")
    request = json.dumps({"program": program, "timeout": timeout, "memory_limit": MEMORY_LIMIT_BYTES}).encode("utf-8")
    if len(request) > MAX_MESSAGE_BYTES:
        raise JavascriptException("Expression request exceeds protocol limit")
    # Files avoid unbounded pipe capture, including diagnostics from custom wrappers.
    # The worker also bounds its response before writing it.
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        try:
            with subprocess.Popen(
                argv, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, start_new_session=True
            ) as proc:
                try:
                    proc.communicate(input=request, timeout=timeout + SUBPROCESS_GRACE_SECONDS)
                except subprocess.TimeoutExpired as e:
                    # Include wrappers that wait for a child instead of exec'ing it.
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    proc.wait()
                    raise JavascriptException("Expression evaluation timed out in worker subprocess") from e
        except OSError as e:
            raise JavascriptException(f"Could not run expression worker: {e}") from e
        if proc.returncode != 0:
            stderr.seek(0)
            detail = stderr.read(500).decode("utf-8", "replace").strip()
            raise JavascriptException(f"Expression worker exited with code {proc.returncode}: {detail}")
        stdout.seek(0)
        output = stdout.read(MAX_MESSAGE_BYTES + 1)
    if len(output) > MAX_MESSAGE_BYTES:
        raise JavascriptException("Expression response exceeds protocol limit")
    try:
        response = json.loads(output)
        if not isinstance(response, dict):
            raise ValueError("Expected a response object")
        if "error" in response:
            raise JavascriptException(str(response["error"])[:500])
        return cast(CWLOutputType, response["result"])
    except (ValueError, KeyError, RecursionError) as e:
        raise JavascriptException("Malformed response from expression worker") from e


class SandboxedJSEngine(NodeJSEngine):
    """A ``cwl_utils`` JS engine backed by a QuickJS worker subprocess.

    Only :meth:`eval` (full JavaScript expressions) is overridden. ``regex_eval``
    (pure-Python CWL parameter-reference resolution, e.g. ``$(inputs.foo)``) is
    inherited unchanged from :class:`NodeJSEngine` and never touches JavaScript.
    """

    def eval(
        self,
        scan: str,
        jslib: str = "",
        timeout: float = default_timeout,
        force_docker_pull: bool = False,
        debug: bool = False,
        js_console: bool = False,
        container_engine: str = "docker",
        sandbox_command: Sequence[str] | None = None,
        **kwargs: Any,
    ) -> CWLOutputType:
        if isinstance(scan, str) and len(scan) > 1 and scan[0] == "{":
            inner = scan
        else:
            inner = f"{{return ({scan});}}"
        program = f'"use strict";\n{jslib}\nJSON.stringify((function(){inner})())'
        return evaluate_program(program, timeout, sandbox_command=sandbox_command)


_registered: bool = False
_lock = threading.Lock()


def register() -> None:
    """Install the sandboxed engine as the process-wide ``cwl_utils`` JS engine.

    Idempotent and thread-safe. Call before any expression is evaluated so no code
    path falls back to the unsafe Node ``vm`` engine.
    """
    global _registered
    with _lock:
        if not _registered:
            set_js_engine(SandboxedJSEngine())
            _registered = True


def build_evaluate_program(new_input: dict[str, Any]) -> str:
    """Assemble the program for the expression-tool (``evaluate``) input contract.

    Mirrors the variable bindings the retired ``cwlNodeEngine.js`` produced
    (``$job``/``$self``/``$runtime``/``$tmpdir``/``$outdir`` plus ``engineConfig``
    lines) so expression tools behave identically, minus the Node ``vm`` sink.
    """
    script = new_input["script"]
    if isinstance(script, str) and len(script) > 0 and script[0] == "{":
        # A ``{...}`` body is a function body: wrap and invoke it.
        exp = "{return function()" + script + "();}"
    elif isinstance(script, str):
        # A bare string is a raw JavaScript expression, inserted verbatim.
        exp = "{return " + script + ";}"
    else:
        # Non-string literals (numbers, bools, null): their JSON form is a valid
        # JS literal, matching the historical engine's ``"{return " + value`` coercion.
        exp = "{return " + json.dumps(script) + ";}"

    lines = ['"use strict";']
    for line in new_input.get("engineConfig") or []:
        lines.append(line)

    def _js_var(name: str, key: str) -> str:
        # JSON.stringify(undefined) rendered as the JS literal `undefined`, as the
        # old engine did for keys absent from the input payload.
        if key not in new_input:
            return f"var {name} = undefined;"
        return f"var {name} = {json.dumps(new_input[key])};"

    lines.append(_js_var("$job", "job"))
    lines.append(_js_var("$self", "context"))
    lines.append(_js_var("$runtime", "runtime"))
    lines.append(_js_var("$tmpdir", "tmpdir"))
    lines.append(_js_var("$outdir", "outdir"))
    lines.append(f"JSON.stringify((function(){exp})())")
    return "\n".join(lines)
