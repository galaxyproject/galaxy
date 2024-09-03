"""Generic I/O and shell processing code used by Galaxy tool dependencies."""

import logging
import os
import shlex
import subprocess
import sys as _sys
import tempfile
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)

from galaxy.util import (
    unicodify,
    which,
)

log = logging.getLogger(__name__)

STDOUT_INDICATOR = "-"


def redirecting_io(sys=_sys):
    """Predicate to determine if we are redicting stdout in process."""
    assert sys is not None
    try:
        # Need to explicitly call fileno() because sys.stdout could be a
        # io.StringIO object, which has a fileno() method but only raises an
        # io.UnsupportedOperation exception
        sys.stdout.fileno()
    except Exception:
        return True
    else:
        return False


def redirect_aware_commmunicate(p, sys=_sys):
    """Variant of process.communicate that works with in process I/O redirection."""
    assert sys is not None
    out, err = p.communicate()
    if redirecting_io(sys=sys):
        if out:
            # We don't unicodify in Python2 because sys.stdout may be a
            # cStringIO.StringIO object, which does not accept Unicode strings
            out = unicodify(out)
            sys.stdout.write(out)
            out = None
        if err:
            err = unicodify(err)
            sys.stderr.write(err)
            err = None
    return out, err


def shell(cmds: Union[List[str], str], env: Optional[Dict[str, str]] = None, **kwds: Any) -> int:
    """Run shell commands with `shell_process` and wait."""
    sys = kwds.get("sys", _sys)
    assert sys is not None
    p = shell_process(cmds, env, **kwds)
    if redirecting_io(sys=sys):
        redirect_aware_commmunicate(p, sys=sys)
        exit = p.returncode
        return exit
    else:
        return p.wait()


def shell_process(cmds: Union[List[str], str], env: Optional[Dict[str, str]] = None, **kwds: Any) -> subprocess.Popen:
    """A high-level method wrapping subprocess.Popen.

    Handles details such as environment extension and in process I/O
    redirection.
    """
    sys = kwds.get("sys", _sys)
    popen_kwds: Dict[str, Any] = {}
    if isinstance(cmds, str):
        log.warning("Passing program arguments as a string may be a security hazard if combined with untrusted input")
        popen_kwds["shell"] = True
    if kwds.get("stdout", None) is None and redirecting_io(sys=sys):
        popen_kwds["stdout"] = subprocess.PIPE
    if kwds.get("stderr", None) is None and redirecting_io(sys=sys):
        popen_kwds["stderr"] = subprocess.PIPE

    popen_kwds.update(**kwds)
    if env:
        new_env = os.environ.copy()
        new_env.update(env)
        popen_kwds["env"] = new_env
    p = subprocess.Popen(cmds, **popen_kwds)
    return p


def execute(cmds, input=None):
    """Execute commands and throw an exception on a non-zero exit.
    if input is not None then the string is sent to the process' stdin.

    Return the standard output if the commands are successful
    """
    return _wait(cmds, input=input, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def argv_to_str(command_argv, quote=True):
    """Convert an argv command list to a string for shell subprocess.

    If None appears in the command list it is simply excluded.

    Arguments are quoted with shlex.quote(). That said, this method is not meant to be
    used in security critical paths of code and should not be used to sanitize
    code.
    """
    map_func = shlex.quote if quote else lambda x: x
    return " ".join(map_func(c) for c in command_argv if c is not None)


def _wait(cmds, input=None, **popen_kwds):
    p = subprocess.Popen(cmds, **popen_kwds)
    stdout, stderr = p.communicate(input)
    stdout, stderr = unicodify(stdout), unicodify(stderr)
    if p.returncode != 0:
        raise CommandLineException(argv_to_str(cmds), stdout, stderr, p.returncode)
    return stdout


def download_command(url, to=STDOUT_INDICATOR):
    """Build a command line to download a URL.

    By default the URL will be downloaded to standard output but a specific
    file can be specified with the `to` argument.
    """
    if which("wget"):
        download_cmd = ["wget", "-q"]
        if to == STDOUT_INDICATOR:
            download_cmd.extend(["-O", STDOUT_INDICATOR, url])
        else:
            download_cmd.extend(["--recursive", "-O", to, url])
    else:
        download_cmd = ["curl", "-L", url]
        if to != STDOUT_INDICATOR:
            download_cmd.extend(["-o", to])
    return download_cmd


class CommandLineException(Exception):
    """An exception indicating a non-zero command-line exit."""

    def __init__(self, command, stdout, stderr, returncode):
        """Construct a CommandLineException from command and standard I/O."""
        self.command = command
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.message = (
            f"Failed to execute command-line {command}, stderr was:\n"
            "-------->>begin stderr<<--------\n"
            f"{stderr}\n"
            "-------->>end stderr<<--------\n"
            "-------->>begin stdout<<--------\n"
            f"{stdout}\n"
            "-------->>end stdout<<--------\n"
        )

    def __str__(self):
        """Return a verbose error message indicating the command problem."""
        return self.message


def new_clean_env():
    """
    Returns a minimal environment to use when invoking a subprocess
    """
    env = {}
    for k in ("HOME", "LC_CTYPE", "PATH", "TMPDIR"):
        if k in os.environ:
            env[k] = os.environ[k]
    if "TMPDIR" not in env:
        env["TMPDIR"] = os.path.abspath(tempfile.gettempdir())
    # Set LC_CTYPE environment variable to enforce UTF-8 file encoding.
    # This is needed e.g. for Python < 3.7 where
    # `locale.getpreferredencoding()` (also used by open() to determine the
    # default file encoding) would return `ANSI_X3.4-1968` without this.
    if not env.get("LC_CTYPE", "").endswith("UTF-8"):
        env["LC_CTYPE"] = "C.UTF-8"
    return env


__all__ = (
    "argv_to_str",
    "CommandLineException",
    "download_command",
    "execute",
    "new_clean_env",
    "redirect_aware_commmunicate",
    "redirecting_io",
    "shell",
    "shell_process",
    "which",
)
