import os
import shlex
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))

from galaxy.util.path import get_ext
from galaxy.util.properties import (
    load_app_properties,
    nice_config_parser,
)
from galaxy.util.script import main_factory

DESCRIPTION = "Script to determine uWSGI command line arguments"
# socket is not an alias for http, but it is assumed that if you configure a socket in your uwsgi config you do not
# want to run the default http server (or you can configure it yourself)
ALIASES = {
    "virtualenv": ("home", "venv", "pyhome"),
    "pythonpath": ("python-path", "pp"),
    "http": ("httprouter", "socket", "uwsgi-socket", "suwsgi-socket", "ssl-socket"),
    "module": ("mount",),  # mount is not actually an alias for module, but we don't want to set module if mount is set
}
DEFAULT_ARGS = {
    "_all_": (
        "pythonpath",
        "threads",
        "buffer-size",
        "http",
        "static-map",
        "die-on-term",
        "hook-master-start",
        "enable-threads",
        "umask",
    ),
    "galaxy": ("py-call-osafterfork",),
    "reports": (),
    "tool_shed": ("cron",),
}
DEFAULT_PORTS = {
    "galaxy": 8080,
    "reports": 9001,
    "tool_shed": 9009,
}


def __arg_set(arg, kwargs):
    if arg in kwargs:
        return True
    for alias in ALIASES.get(arg, ()):
        if alias in kwargs:
            return True
    return False


def __add_arg(args, arg, value):
    optarg = "--%s" % arg
    if isinstance(value, bool):
        if value is True:
            args.append(optarg)
    elif isinstance(value, str):
        # the = in --optarg=value is usually, but not always, optional
        if value.startswith("="):
            args.append(shlex.quote(optarg + value))
        else:
            args.append(optarg)
            args.append(shlex.quote(value))
    else:
        [__add_arg(args, arg, v) for v in value]


def __add_config_file_arg(args, config_file, app):
    ext = None
    if config_file:
        ext = get_ext(config_file)
    if ext in ("yaml", "json"):
        __add_arg(args, ext, config_file)
    elif ext == "ini":
        config = nice_config_parser(config_file)
        has_logging = config.has_section("loggers")
        if config.has_section("app:main"):
            # uWSGI does not have any way to set the app name when loading with paste.deploy:loadapp(), so hardcoding
            # the name to `main` is fine
            __add_arg(args, "ini-paste" if not has_logging else "ini-paste-logged", config_file)
            return  # do not add --module
        else:
            __add_arg(args, ext, config_file)
            if has_logging:
                __add_arg(args, "paste-logger", True)


def _get_uwsgi_args(cliargs, kwargs):
    # it'd be nice if we didn't have to reparse here but we need things out of more than one section
    config_file = cliargs.config_file or kwargs.get("__file__")
    uwsgi_kwargs = load_app_properties(config_file=config_file, config_section="uwsgi")
    args = []
    ts_cron_config_option = "" if config_file is None else "-c %s" % config_file
    defaults = {
        "pythonpath": "lib",
        "threads": "4",
        "buffer-size": "16384",  # https://github.com/galaxyproject/galaxy/issues/1530
        "http": f"localhost:{DEFAULT_PORTS[cliargs.app]}",
        "static-map": (f"/static={os.getcwd()}/static", f"/favicon.ico={os.getcwd()}/static/favicon.ico"),
        "die-on-term": True,
        "enable-threads": True,
        "hook-master-start": ("unix_signal:2 gracefully_kill_them_all", "unix_signal:15 gracefully_kill_them_all"),
        "py-call-osafterfork": True,
        "cron": "0 -1 -1 -1 -1 python scripts/tool_shed/build_ts_whoosh_index.py %s --config-section tool_shed -d"
        % ts_cron_config_option,
        "umask": "027",
    }
    __add_config_file_arg(args, config_file, cliargs.app)
    if not __arg_set("module", uwsgi_kwargs):
        if cliargs.app in ["tool_shed"]:
            __add_arg(args, "module", "tool_shed.webapp.buildapp:uwsgi_app()")
        else:
            __add_arg(args, "module", f"galaxy.webapps.{cliargs.app}.buildapp:uwsgi_app()")
    # only include virtualenv if it's set/exists, otherwise this breaks conda-env'd Galaxy
    if not __arg_set("virtualenv", uwsgi_kwargs) and ("VIRTUAL_ENV" in os.environ or os.path.exists(".venv")):
        __add_arg(args, "virtualenv", os.environ.get("VIRTUAL_ENV", ".venv"))

    # We always want to append client/src/assets as static-safe.
    __add_arg(args, "static-safe", f"{os.getcwd()}/client/src/assets")

    # Do not let uwsgi remap stdin to /dev/null if galaxy is in debug mode
    galaxy_kwargs = load_app_properties(config_file=config_file, config_section="galaxy")
    if __arg_set("debug", galaxy_kwargs) and not __arg_set("honour-stdin", uwsgi_kwargs):
        __add_arg(args, "honour-stdin", True)

    for arg in DEFAULT_ARGS["_all_"] + DEFAULT_ARGS[cliargs.app]:
        if not __arg_set(arg, uwsgi_kwargs):
            __add_arg(args, arg, defaults[arg])
    print(" ".join(args))


ACTIONS = {
    "get_uwsgi_args": _get_uwsgi_args,
}


if __name__ == "__main__":
    main = main_factory(description=DESCRIPTION, actions=ACTIONS, default_action="get_uwsgi_args")
    main()
