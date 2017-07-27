#!/usr/bin/env python
""" Entry point for starting a Galaxy job handler as a uWSGI mule

Example Usage:

uwsgi ... --mule=lib/galaxy/web/stack/uwsgi_mule/handler.py --mule=lib/galaxy/web/stack/uwsgi_mule/handler.py --farm=handlers:1,2
"""
import logging
import os
import sys
import time
from logging.config import fileConfig

import uwsgi

try:
    import ConfigParser as configparser
except ImportError:
    import configparser


SERVER_NAME_TEMPLATE = 'mule-handler-{mule_id}'

log = logging.getLogger(__name__)

real_file = os.path.realpath(__file__)
GALAXY_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(real_file), os.pardir, os.pardir, os.pardir, os.pardir, os.pardir))
GALAXY_LIB_DIR = os.path.join(GALAXY_ROOT_DIR, "lib")
DEFAULT_INI_APP = "main"
DEFAULT_INIS = ["config/galaxy.ini", "universe_wsgi.ini", "config/galaxy.ini.sample"]


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


def app_loop(ini_path, log):
    try:
        config_builder = GalaxyConfigBuilder(ini_path=ini_path)
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

    def __init__(self, **kwds):
        ini_path = kwds.get("ini_path", None)
        # If given app_conf_path - use that - else we need to ensure we have an
        # ini path.
        if not ini_path:
            galaxy_root = kwds.get("galaxy_root", GALAXY_ROOT_DIR)
            ini_path = find_ini(ini_path, galaxy_root)
            ini_path = absolute_config_path(ini_path, galaxy_root=galaxy_root)
        self.ini_path = ini_path
        self.app_name = kwds.get("app") or DEFAULT_INI_APP

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


def galaxy_config_from_uwsgi():
    if 'ini-paste' in uwsgi.opt:
        return uwsgi.opt['ini-paste']
    elif 'set' in uwsgi.opt:
        for k, v in [x.split('=', 1) for x in uwsgi.opt['set']]:
            if k == 'galaxy_config_file':
                return v
    return None


def main():
    # FIXME: need file logging... set=galaxy_mule_handler_log_dir=/path ??
    #if args.log_file:
    #    os.environ["GALAXY_CONFIG_LOG_DESTINATION"] = os.path.abspath(args.log_file)
    os.environ["GALAXY_CONFIG_SERVER_NAME"] = SERVER_NAME_TEMPLATE.format(mule_id=uwsgi.mule_id())
    ini_path = galaxy_config_from_uwsgi()

    log.setLevel(logging.DEBUG)
    log.propagate = False
    app_loop(ini_path, log)


if __name__ == "__main__":
    main()
