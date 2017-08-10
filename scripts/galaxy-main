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
import sys
import time
from logging.config import fileConfig

try:
    import ConfigParser as configparser
except ImportError:
    import configparser

try:
    from daemonize import Daemonize
except ImportError:
    Daemonize = None

# Vaguely Python 2.6 compatibile ArgumentParser import
try:
    from argparse import ArgumentParser
except ImportError:
    from optparse import OptionParser

    class ArgumentParser(OptionParser):

        def __init__(self, **kwargs):
            self.delegate = OptionParser(**kwargs)

        def add_argument(self, *args, **kwargs):
            if "required" in kwargs:
                del kwargs["required"]
            return self.delegate.add_option(*args, **kwargs)

        def parse_args(self, args=None):
            (options, args) = self.delegate.parse_args(args)
            return options

REQUIRES_DAEMONIZE_MESSAGE = "Attempted to use Galaxy in daemon mode, but daemonize is unavailable."

log = logging.getLogger(__name__)

real_file = os.path.realpath(__file__)
GALAXY_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(real_file), os.pardir))
GALAXY_LIB_DIR = os.path.join(GALAXY_ROOT_DIR, "lib")
DEFAULT_INI_APP = "main"
DEFAULT_INIS = ["config/galaxy.ini", "universe_wsgi.ini", "config/galaxy.ini.sample"]

DEFAULT_PID = "galaxy.pid"
DEFAULT_VERBOSE = True
DESCRIPTION = "Daemonized entry point for Galaxy."


def load_galaxy_app(
    config_builder,
    config_env=False,
    log=None,
    **kwds
):
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
        try:
            sys.path.insert(1, GALAXY_LIB_DIR)
        except Exception:
            log.exception("Failed to add Galaxy to sys.path")
            raise

    config_builder.setup_logging()
    from galaxy.util.properties import load_app_properties
    kwds = config_builder.app_kwds()
    kwds = load_app_properties(**kwds)
    from galaxy.app import UniverseApplication
    app = UniverseApplication(
        global_conf={"__file__": config_builder.ini_path},
        **kwds
    )
    app.control_worker.bind_and_start()
    return app


def app_loop(args, log):
    try:
        config_builder = GalaxyConfigBuilder(args)
        galaxy_app = load_galaxy_app(
            config_builder,
            config_env=True,
            log=log,
        )
    except BaseException:
        log.exception("Failed to initialize Galaxy application")
        raise
    sleep = True
    while sleep:
        try:
            time.sleep(5)
        except KeyboardInterrupt:
            sleep = False
        except SystemExit:
            sleep = False
        except Exception:
            pass
    try:
        galaxy_app.shutdown()
    except Exception:
        log.exception("Failed to shutdown Galaxy application")
        raise


def absolute_config_path(path, galaxy_root):
    if path and not os.path.isabs(path):
        path = os.path.join(galaxy_root, path)
    return path


def find_ini(supplied_ini, galaxy_root):
    if supplied_ini:
        return supplied_ini

    # If not explicitly supplied an ini, check server.ini and then
    # just restort to sample if that has not been configured.
    for guess in DEFAULT_INIS:
        ini_path = os.path.join(galaxy_root, guess)
        if os.path.exists(ini_path):
            return ini_path

    return guess


class GalaxyConfigBuilder(object):
    """ Generate paste-like configuration from supplied command-line arguments.
    """

    def __init__(self, args=None, **kwds):
        ini_path = kwds.get("ini_path", None) or (args and args.ini_path)
        # If given app_conf_path - use that - else we need to ensure we have an
        # ini path.
        if not ini_path:
            galaxy_root = kwds.get("galaxy_root", GALAXY_ROOT_DIR)
            ini_path = find_ini(ini_path, galaxy_root)
            ini_path = absolute_config_path(ini_path, galaxy_root=galaxy_root)
        self.ini_path = ini_path
        self.app_name = kwds.get("app") or (args and args.app) or DEFAULT_INI_APP
        self.log_file = (args and args.log_file)

    @classmethod
    def populate_options(cls, arg_parser):
        arg_parser.add_argument("-c", "--ini-path", default=None, help="Galaxy ini config file (defaults to config/galaxy.ini)")
        arg_parser.add_argument("--app", default=DEFAULT_INI_APP, help="app section in ini file (defaults to main)")
        arg_parser.add_argument("-d", "--daemonize", default=False, help="Daemonzie process", action="store_true")
        arg_parser.add_argument("--daemon-log-file", default=None, help="log file for daemon script ")
        arg_parser.add_argument("--log-file", default=None, help="Galaxy log file (overrides log configuration in ini_path if set)")
        arg_parser.add_argument("--pid-file", default=DEFAULT_PID, help="pid file (default is %s)" % DEFAULT_PID)
        arg_parser.add_argument("--server-name", default=None, help="set a galaxy server name")

    def app_kwds(self):
        config = dict(
            ini_file=self.ini_path,
            ini_section="app:%s" % self.app_name,
        )
        return config

    def setup_logging(self):
        # Galaxy will attempt to setup logging if loggers is not present in
        # ini config file - this handles that loggers block however if present
        # (the way paste normally would)
        if not self.ini_path:
            return
        raw_config = configparser.ConfigParser()
        raw_config.read([self.ini_path])
        if raw_config.has_section('loggers'):
            config_file = os.path.abspath(self.ini_path)
            fileConfig(
                config_file,
                dict(__file__=config_file, here=os.path.dirname(config_file))
            )


def main():
    arg_parser = ArgumentParser(description=DESCRIPTION)
    GalaxyConfigBuilder.populate_options(arg_parser)
    args = arg_parser.parse_args()
    if args.log_file:
        os.environ["GALAXY_CONFIG_LOG_DESTINATION"] = os.path.abspath(args.log_file)
    if args.server_name:
        os.environ["GALAXY_CONFIG_SERVER_NAME"] = args.server_name
    pid_file = args.pid_file

    log.setLevel(logging.DEBUG)
    log.propagate = False
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
            action=functools.partial(app_loop, args, log),
            verbose=DEFAULT_VERBOSE,
            logger=log,
            keep_fds=keep_fds,
        )
        daemon.start()
    else:
        app_loop(args, log)


if __name__ == "__main__":
    main()
