import json
import os
import platform
import shutil
import subprocess
import sys
import time

import psutil
import pytest
from cwl_utils.errors import (
    JavascriptException,
    WorkflowException,
)

from galaxy.tools.expressions import (
    do_eval,
    evaluate,
    js_engine,
)
from galaxy.tools.expressions.js_engine import (
    _bubblewrap_command,
    evaluate_program,
    resolve_isolation_command,
    SandboxedJSEngine,
)
from galaxy_ext.expressions.sandbox_worker import MAX_MESSAGE_BYTES

# A benign stand-in for a real jail command (e.g. bwrap): `/usr/bin/env` just execs
# the worker argv appended after it, exercising the out-of-process plumbing without
# needing bubblewrap installed.
_PASSTHROUGH_SANDBOX = ["/usr/bin/env"]
_needs_env = pytest.mark.skipif(
    not os.path.exists("/usr/bin/env"), reason="requires /usr/bin/env for the out-of-process worker test"
)


def _bwrap_can_sandbox() -> bool:
    # bubblewrap must be installed AND actually able to set up its sandbox here.
    # Namespace creation, uid-map setup, and exec inside the jail can all be blocked
    # on locked-down hosts and CI runners; a plain "is bwrap on PATH" check is not
    # enough. Probe the real recipe by running the interpreter on an empty program.
    command = resolve_isolation_command("bubblewrap")
    if not command:
        return False
    try:
        proc = subprocess.run([*command, sys.executable, "-c", ""], capture_output=True, timeout=1)
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0


_needs_bwrap = pytest.mark.skipif(
    not _bwrap_can_sandbox(),
    reason="bubblewrap not installed or cannot set up a sandbox in this environment",
)


@pytest.fixture(autouse=True)
def check_worker_cleanup():
    parent = psutil.Process()
    before = set(parent.children())
    yield
    remaining = set(parent.children()) - before
    for child in remaining:
        child.kill()
        child.wait(timeout=1)
    assert not remaining, f"Workers were not reaped: {remaining}"


@pytest.fixture
def short_timeout_grace(monkeypatch):
    monkeypatch.setattr(js_engine, "SUBPROCESS_GRACE_SECONDS", 0.9)


def test_evaluate():
    # Expression-tool script path: a `{...}` body is treated as a function body.
    assert evaluate(None, {"script": "{return 5;}"}) == 5
    assert evaluate(None, {"script": "{return {out1: 1 + 2, out2: 'x'};}"}) == {"out1": 3, "out2": "x"}
    assert evaluate(None, {"script": "{return $job.a + 1;}", "job": {"a": 41}}) == 42
    # A bare (non-`{...}`) script is a raw JavaScript expression.
    assert evaluate(None, {"script": "$job.a + 1", "job": {"a": 41}}) == 42


def test_evaluate_legacy_bindings():
    assert evaluate(
        None,
        {
            "script": "[twice($job.n), $self, $runtime.cores, $tmpdir, $outdir]",
            "engineConfig": ["function twice(n) { return n * 2; }"],
            "job": {"n": 3},
            "context": {"name": "é"},
            "runtime": {"cores": 4},
            "tmpdir": "/tmp/job",
            "outdir": "/out/job",
        },
    ) == [6, {"name": "é"}, 4, "/tmp/job", "/out/job"]


@pytest.mark.parametrize("value", [None, True, 42, [1, "é"], {"x": [False, None]}])
def test_evaluate_json_values(value):
    assert evaluate(None, {"script": value}) == value


def test_evaluate_undefined_and_fresh_context():
    assert evaluate(None, {"script": "undefined"}) is None
    assert evaluate(None, {"script": "{ Object.prototype.polluted = true; return ({}).polluted; }"}) is True
    assert evaluate(None, {"script": "({}).polluted"}) is None


def test_default_evaluation_uses_worker(monkeypatch):
    workers = []
    popen = subprocess.Popen

    def record_worker(*args, **kwargs):
        worker = popen(*args, **kwargs)
        workers.append(worker)
        return worker

    monkeypatch.setattr(subprocess, "Popen", record_worker)
    assert SandboxedJSEngine().eval("1 + 1") == 2
    assert len(workers) == 1
    assert workers[0].args == [sys.executable, js_engine.WORKER_SCRIPT]
    assert workers[0].pid != os.getpid()
    assert workers[0].returncode == 0


def test_do_eval_parameter_reference():
    # An unavailable wrapper would fail if these references tried to launch JS.
    wrapper = ["/nonexistent/jail/binary"]
    assert do_eval("$(inputs.should_run)", {"should_run": True}, sandbox_command=wrapper) is True
    assert do_eval("$(inputs.nested.value)", {"nested": {"value": 7}}, sandbox_command=wrapper) == 7


@pytest.fixture
def without_quickjs(tmp_path, monkeypatch):
    worker = tmp_path / "worker_without_quickjs.py"
    worker.write_text(
        "import runpy, sys\n"
        "sys.modules['quickjs'] = None\n"
        f"runpy.run_path({js_engine.WORKER_SCRIPT!r}, run_name='__main__')\n"
    )
    monkeypatch.setattr(js_engine, "WORKER_SCRIPT", str(worker))


@pytest.mark.parametrize(
    "expression, inputs, expected",
    [
        (True, {}, True),
        ("literal", {}, "literal"),
        ("$(inputs.should_run)", {"should_run": False}, False),
        ("$(inputs.nested.value)", {"nested": {"value": 7}}, 7),
        ("prefix-$(inputs.name)", {"name": "sample"}, "prefix-sample"),
    ],
)
def test_do_eval_without_quickjs_parameter_references(without_quickjs, expression, inputs, expected):
    assert do_eval(expression, inputs) == expected


@pytest.mark.parametrize("expression", ["$(1 + 1)", "${ return false; }"])
def test_do_eval_without_quickjs_fails_closed(without_quickjs, expression):
    with pytest.raises(WorkflowException, match=r"Full JavaScript evaluation requires Python 3\.10\+.*quickjs-ng"):
        do_eval(expression, {})


def test_evaluate_without_quickjs_fails_closed(without_quickjs):
    with pytest.raises(JavascriptException, match=r"Full JavaScript evaluation requires Python 3\.10\+.*quickjs-ng"):
        evaluate(None, {"script": "{return 42;}"})


def test_do_eval_javascript_expression():
    # Expression-bearing `$(...)` and `${...}` bodies are evaluated as JavaScript.
    assert do_eval('$(inputs.format != "bwa_mem2_index")', {"format": "bwa_mem2_index"}) is False
    assert do_eval('$(inputs.format != "bwa_mem2_index")', {"format": "other"}) is True
    assert do_eval("${ return 1 + 1 > 1; }", {}) is True


@pytest.mark.parametrize(
    "payload",
    [
        # The published exploit gadgets: reach the host Function constructor and try
        # to get at Node's `process`/`require('child_process')`. In the QuickJS
        # context there is no `process`, so each either fails closed or yields nothing.
        "${ return globalThis.constructor.constructor(\"return process.mainModule.require('child_process').execSync('id')\")(); }",
        "${ return globalThis.constructor.constructor(\"return process\")().getBuiltinModule('child_process'); }",
    ],
)
def test_do_eval_sandbox_blocks_process_escape(payload):
    with pytest.raises((JavascriptException, WorkflowException)):
        do_eval(payload, {})


def test_do_eval_process_is_undefined():
    # The escape's own fingerprint: `typeof process` is "undefined" in the isolate,
    # so the Function constructor is reachable but has nothing dangerous to return.
    result = do_eval(
        '${ return String(globalThis.constructor.constructor("return typeof process")()); }',
        {},
    )
    assert result == "undefined"


@pytest.mark.parametrize("body", ["{while (true) {}}", "{return {toJSON() {while (true) {}}};}"])
def test_sandbox_engine_timeout(body):
    # A runaway expression is killed rather than hanging the scheduler.
    engine = SandboxedJSEngine()
    with pytest.raises(JavascriptException, match="interrupted"):
        engine.eval(body, timeout=0.1)


def test_parent_timeout_during_exception_formatting(short_timeout_grace):
    started = time.monotonic()
    with pytest.raises(JavascriptException, match="timed out in worker subprocess") as exc:
        SandboxedJSEngine().eval("{throw {toString() {while (true) {}}};}", timeout=0.1)
    assert isinstance(exc.value.__cause__, subprocess.TimeoutExpired)
    assert time.monotonic() - started < 5


@pytest.mark.parametrize("constructor", ["Uint8Array", "ArrayBuffer", "SharedArrayBuffer"])
def test_quickjs_allocator_limit(constructor):
    program = f"JSON.stringify(new {constructor}(256 * 1024 * 1024).byteLength)"
    with pytest.raises(JavascriptException, match="out of memory|allocation size overflow"):
        evaluate_program(program, timeout=0.5)
    assert evaluate_program("JSON.stringify(42)") == 42


def test_quickjs_stack_limit():
    with pytest.raises(JavascriptException, match="call stack size exceeded"):
        evaluate_program("function recurse() {return recurse();} recurse();", timeout=0.5)


def test_no_host_apis():
    assert (
        do_eval("${ return [typeof process, typeof require, typeof fetch, typeof std, typeof os]; }", {})
        == ["undefined"] * 5
    )


@pytest.mark.parametrize("program", ["JSON.stringify(()", "throw new Error('bad expression')"])
def test_javascript_errors_are_translated(program):
    with pytest.raises(JavascriptException):
        evaluate_program(program)


@pytest.mark.parametrize("character", ["x", "é"])
def test_request_limit_before_starting_worker(character):
    length = MAX_MESSAGE_BYTES + 1 if character == "x" else MAX_MESSAGE_BYTES // 6 + 1
    with pytest.raises(JavascriptException, match="request exceeds protocol limit"):
        evaluate_program(character * length, sandbox_command=["/nonexistent/jail/binary"])


def test_worker_result_limit():
    with pytest.raises(JavascriptException, match="result exceeds protocol limit"):
        evaluate_program(f"JSON.stringify('x'.repeat({MAX_MESSAGE_BYTES}))", timeout=1)


def test_parent_response_limit():
    # Exercise the parent bound even when a wrapper writes beyond the worker limit.
    wrapper = [
        sys.executable,
        "-c",
        f"import sys; sys.stdin.read(); sys.stdout.write('x' * {MAX_MESSAGE_BYTES + 1})",
    ]
    with pytest.raises(JavascriptException, match="response exceeds protocol limit"):
        evaluate_program("JSON.stringify(42)", sandbox_command=wrapper)


def test_malformed_result_is_translated():
    with pytest.raises(JavascriptException, match="Malformed response"):
        evaluate_program(json.dumps("invalid JSON"))


def test_response_recursion_error_is_translated(monkeypatch):
    # JSON decoder nesting limits differ between Python versions.
    def fail_to_decode(response):
        raise RecursionError("response nesting limit exceeded")

    monkeypatch.setattr(json, "loads", fail_to_decode)
    with pytest.raises(JavascriptException, match="Malformed response") as exc:
        evaluate_program("JSON.stringify(42)")
    assert isinstance(exc.value.__cause__, RecursionError)


def test_parent_timeout_covers_worker_teardown(short_timeout_grace):
    wrapper = [
        sys.executable,
        "-c",
        (
            "import atexit, subprocess, sys, time; "
            "subprocess.run(sys.argv[1:], check=True); atexit.register(time.sleep, 60)"
        ),
    ]
    with pytest.raises(JavascriptException, match="timed out in worker subprocess"):
        evaluate_program("JSON.stringify(42)", timeout=0.1, sandbox_command=wrapper)


def test_error_message_is_bounded():
    with pytest.raises(JavascriptException) as exc:
        evaluate_program("throw new Error('x'.repeat(1000000))", timeout=0.5)
    assert len(str(exc.value)) <= 500


def test_timeout_kills_worker_under_waiting_wrapper(tmp_path, short_timeout_grace):
    pid_file = tmp_path / "worker.pid"
    wrapper = tmp_path / "wrapper.py"
    wrapper.write_text(
        "import pathlib, subprocess, sys\n"
        "child = subprocess.Popen(sys.argv[2:])\n"
        "pathlib.Path(sys.argv[1]).write_text(str(child.pid))\n"
        "child.wait()\n"
    )
    with pytest.raises(JavascriptException, match="timed out in worker subprocess"):
        evaluate_program(
            "throw {toString() {while (true) {}}}",
            timeout=0.1,
            sandbox_command=[sys.executable, str(wrapper), str(pid_file)],
        )
    pid = int(pid_file.read_text())
    try:
        child = psutil.Process(pid)
        assert child.status() == psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        pass


@_needs_env
def test_out_of_process_evaluation():
    # With a sandbox command set, evaluation runs in a separate worker process.
    program = '"use strict";\nJSON.stringify((function(){return 1 + 2;})())'
    assert evaluate_program(program, sandbox_command=_PASSTHROUGH_SANDBOX) == 3


@_needs_env
def test_out_of_process_do_eval_and_escape():
    # The sandbox_command flows through cwl_utils to the worker, and the escape
    # remains blocked out-of-process too.
    assert do_eval("${ return 6 * 7; }", {}, sandbox_command=_PASSTHROUGH_SANDBOX) == 42
    with pytest.raises((JavascriptException, WorkflowException)):
        do_eval(
            '${ return globalThis.constructor.constructor("return process")(); }',
            {},
            sandbox_command=_PASSTHROUGH_SANDBOX,
        )


def test_missing_sandbox_command_raises():
    program = '"use strict";\nJSON.stringify((function(){return 1;})())'
    with pytest.raises(JavascriptException):
        evaluate_program(program, sandbox_command=["/nonexistent/jail/binary"])


def test_resolve_isolation_none():
    assert resolve_isolation_command("") is None
    assert resolve_isolation_command("   ") is None


def test_resolve_isolation_custom_command():
    assert resolve_isolation_command("/usr/bin/env --unset=FOO") == ("/usr/bin/env", "--unset=FOO")


def test_resolve_isolation_bubblewrap_matches_environment():
    # No mocking: resolve against the real host. On Linux with bwrap installed the
    # keyword yields a real bwrap command; anywhere else it uses an ordinary subprocess.
    resolved = resolve_isolation_command("bubblewrap")
    if resolved is None:
        assert platform.system() != "Linux" or shutil.which("bwrap") is None
    else:
        assert resolved[0].endswith("bwrap")
        assert "--unshare-pid" in resolved
        assert "--ro-bind-try" in resolved


def test_bubblewrap_command_minimal_binds():
    # The built-in jail mounts only what the worker needs -- the Python runtime, the
    # worker script and system libs -- and never the whole root filesystem.
    argv = _bubblewrap_command("/usr/bin/bwrap")
    assert argv[0] == "/usr/bin/bwrap"
    for flag in ("--unshare-pid", "--clearenv", "--proc", "--tmpfs"):
        assert flag in argv
    # The Python prefix is bound so the interpreter and quickjs are available.
    assert sys.prefix in argv
    # Crucially, the root filesystem is NOT bound.
    pairs = list(zip(argv, argv[1:], argv[2:]))
    assert ("--ro-bind", "/", "/") not in pairs
    assert ("--ro-bind-try", "/", "/") not in pairs


@_needs_bwrap
def test_bubblewrap_real_execution():
    # Real bubblewrap: the built-in jail actually runs, its minimal bind set is
    # sufficient for the worker, expressions evaluate correctly, and the escape stays
    # blocked inside the jail. Skipped unless Linux with bwrap installed.
    sandbox = resolve_isolation_command("bubblewrap")
    assert sandbox is not None
    ok = '"use strict";\nJSON.stringify((function(){return 6 * 7;})())'
    assert evaluate_program(ok, sandbox_command=sandbox) == 42
    escape = (
        '"use strict";\n'
        'JSON.stringify((function(){return String(globalThis.constructor.constructor("return typeof process")());})())'
    )
    assert evaluate_program(escape, sandbox_command=sandbox) == "undefined"
