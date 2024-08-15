#!/usr/bin/env python
""" Entry point for starting Galaxy without starting as part of a web server.

Example Usage: Start a job/workflow handler without a web server and with
a given name using.

galaxy-main --server-name handler0

Start as a daemon with (requires daemonized - install with 'pip install daemonize'):

galaxy-main -d --daemon-log-file=handler0-daemon.log --pid-file handler0.pid --server-name handler0

In daemon mode logging of Galaxy (as opposed to this script) is configured via
a loggers section in Galaxy's ini file - this can be overridden with sensible
defaults logging to a single file with the following:

galaxy-main -d --server-name handler0 --daemon-log-file=handler0-daemon.log --pid-file handler0.pid --log-file handler0.log

"""
import functools
import logging
import os
import signal
import sys
import threading
from argparse import ArgumentParser
from configparser import ConfigParser
from logging.config import fileConfig

try:
    from daemonize import Daemonize
except ImportError:
    Daemonize = None

log = logging.getLogger(__name__)

real_file = os.path.realpath(__file__)
GALAXY_ROOT_DIR_ = os.path.abspath(os.path.join(os.path.dirname(real_file), os.pardir))
if not os.path.exists(os.path.join(GALAXY_ROOT_DIR_, "run.sh")):
    # Galaxy is installed
    GALAXY_ROOT_DIR = None
else:
    GALAXY_ROOT_DIR = GALAXY_ROOT_DIR_
    GALAXY_LIB_DIR = os.path.join(GALAXY_ROOT_DIR_, "lib")
    try:
        sys.path.insert(1, GALAXY_LIB_DIR)
    except Exception:
        log.exception("Failed to add Galaxy to sys.path")
        raise
from galaxy.main_config import (
    absolute_config_path,
    config_is_ini,
    DEFAULT_CONFIG_SECTION,
    DEFAULT_INI_APP,
    find_config,
)
from galaxy.util import unicodify
from galaxy.web_stack import get_app_kwds

REQUIRES_DAEMONIZE_MESSAGE = "Attempted to use Galaxy in daemon mode, but daemonize is unavailable."

DEFAULT_PID = "galaxy.pid"
DEFAULT_VERBOSE = True
DESCRIPTION = "Daemonized entry point for Galaxy."


exit = threading.Event()


def load_galaxy_app(config_builder, config_env=False, log=None, attach_to_pools=None, **kwds):
    # Allow specification of log so daemon can reuse properly configured one.
    if log is None:
        log = logging.getLogger(__name__)

    # If called in daemon mode, set the ROOT directory and ensure Galaxy is on
    # sys.path.
    if config_env:
        try:
            os.chdir(GALAXY_ROOT_DIR)
        except Exception:
            log.exception("Failed to chdir")
            raise

    config_builder.setup_logging()
    from galaxy.util.properties import load_app_properties

    kwds = config_builder.app_kwds()
    kwds = load_app_properties(**kwds)
    from galaxy.app import UniverseApplication

    app = UniverseApplication(global_conf=config_builder.global_conf(), attach_to_pools=attach_to_pools, **kwds)
    app.database_heartbeat.start()
    app.application_stack.log_startup()
    return app


def handle_signal(signum, frame):
    log.info("Received signal %d, exiting", signum)
    exit.set()


def register_signals():
    for name in ("TERM", "INT", "HUP"):
        sig = getattr(signal, f"SIG{name}")
        signal.signal(sig, handle_signal)


def app_loop(args, log):
    try:
        config_builder = GalaxyConfigBuilder(args)
        config_env = GALAXY_ROOT_DIR is not None
        galaxy_app = load_galaxy_app(
            config_builder,
            config_env=config_env,
            log=log,
            attach_to_pools=args.attach_to_pool,
        )
    except BaseException:
        log.exception("Failed to initialize Galaxy application")
        raise
    try:
        # A timeout is required or the signals won't be handled
        while not exit.wait(20):
            pass
    except (KeyboardInterrupt, SystemExit):
        pass
    try:
        galaxy_app.shutdown()
    except Exception:
        log.exception("Failed to shutdown Galaxy application")
        raise


class GalaxyConfigBuilder:
    """Generate paste-like configuration from supplied command-line arguments."""

    def __init__(self, args=None, **kwds):
        self.config_file = None
        self.config_section = None
        self.app_name = kwds.get("app") or (args and args.app) or DEFAULT_CONFIG_SECTION
        config_file = kwds.get("config_file", None) or (args and args.config_file)
        # If given app_conf_path - use that - else we need to ensure we have a
        # config file path.
        if not config_file and "config_file" in self.app_kwds():
            config_file = self.app_kwds()["config_file"]
        if not config_file:
            galaxy_root = kwds.get("galaxy_root", GALAXY_ROOT_DIR)
            config_file = find_config(config_file, galaxy_root)
            config_file = absolute_config_path(config_file, galaxy_root=galaxy_root)
        self.config_file = unicodify(config_file)
        # FIXME: this won't work for non-Paste ini configs
        if self.config_is_ini:
            self.config_section = f"app:{unicodify(kwds.get('app') or args and args.app or DEFAULT_INI_APP)}"
        else:
            self.config_section = self.app_name
        self.log_file = args and args.log_file

    @classmethod
    def populate_options(cls, arg_parser):
        arg_parser.add_argument(
            "-c", "--config-file", default=None, help="Galaxy config file (defaults to config/galaxy.ini)"
        )
        arg_parser.add_argument("--ini-path", default=None, help="DEPRECATED: use -c/--config-file")
        arg_parser.add_argument(
            "--app",
            default=None,
            help="app section in config file (defaults to 'galaxy' for YAML/JSON, 'main' (w/ 'app:' prepended) for INI",
        )
        arg_parser.add_argument("-d", "--daemonize", default=False, help="Daemonize process", action="store_true")
        arg_parser.add_argument("--daemon-log-file", default=None, help="log file for daemon script ")
        arg_parser.add_argument(
            "--log-file", default=None, help="Galaxy log file (overrides log configuration in config_file if set)"
        )
        arg_parser.add_argument("--pid-file", default=DEFAULT_PID, help=f"pid file (default is {DEFAULT_PID})")
        arg_parser.add_argument("--server-name", default=None, help="set a galaxy server name")
        arg_parser.add_argument(
            "--attach-to-pool",
            action="append",
            default=None,
            help="attach to asynchronous worker pool (specify multiple times for multiple pools)",
        )

    @property
    def config_is_ini(self):
        return config_is_ini(self.config_file)

    def app_kwds(self):
        kwds = get_app_kwds(self.app_name, app_name=self.app_name)
        if "config_file" not in kwds:
            kwds["config_file"] = self.config_file
        if "config_section" not in kwds:
            kwds["config_section"] = self.config_section
        return kwds

    def global_conf(self):
        conf = {}
        if self.config_is_ini:
            conf["__file__"] = self.config_file
        return conf

    def setup_logging(self):
        # Galaxy will attempt to setup logging if loggers is not present in
        # ini config file - this handles that loggers block however if present
        # (the way paste normally would)
        if not self.config_file:
            return
        if self.config_is_ini:
            raw_config = ConfigParser()
            raw_config.read([self.config_file])
            if raw_config.has_section("loggers"):
                config_file = os.path.abspath(self.config_file)
                fileConfig(config_file, dict(__file__=config_file, here=os.path.dirname(config_file)))


def main(func=app_loop):
    arg_parser = ArgumentParser(description=DESCRIPTION)
    GalaxyConfigBuilder.populate_options(arg_parser)
    args = arg_parser.parse_args()
    if args.ini_path and not args.config_file:
        args.config_file = args.ini_path
    if args.log_file:
        os.environ["GALAXY_CONFIG_LOG_DESTINATION"] = os.path.abspath(args.log_file)
    if args.server_name:
        os.environ["GALAXY_CONFIG_SERVER_NAME"] = args.server_name
    pid_file = args.pid_file

    log.setLevel(logging.DEBUG)
    log.propagate = False
    register_signals()
    if args.daemonize:
        if Daemonize is None:
            raise ImportError(REQUIRES_DAEMONIZE_MESSAGE)

        keep_fds = []
        if args.daemon_log_file:
            fh = logging.FileHandler(args.daemon_log_file, "w")
            fh.setLevel(logging.DEBUG)
            log.addHandler(fh)
            keep_fds.append(fh.stream.fileno())
        else:
            fh = logging.StreamHandler(sys.stderr)
            fh.setLevel(logging.DEBUG)
            log.addHandler(fh)

        daemon = Daemonize(
            app="galaxy",
            pid=pid_file,
            action=functools.partial(func, args, log),
            verbose=DEFAULT_VERBOSE,
            logger=log,
            keep_fds=keep_fds,
        )
        daemon.start()
    else:
        func(args, log)


if __name__ == "__main__":
    main()
