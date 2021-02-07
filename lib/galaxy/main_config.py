"""Utilities for finding Galaxy's configuration file.

This is for use by web framework code and scripts (e.g. scripts/galaxy_main.py).
"""
import os

DEFAULT_INIS = ["config/galaxy.yml", "config/galaxy.ini", "universe_wsgi.ini", "config/galaxy.yml.sample"]
DEFAULT_INI_APP = "main"
DEFAULT_CONFIG_SECTION = "galaxy"


def absolute_config_path(path, galaxy_root):
    if path and not os.path.isabs(path):
        path = os.path.join(galaxy_root, path)
    return path


def config_is_ini(config_file):
    return config_file and (config_file.endswith('.ini') or config_file.endswith('.ini.sample'))


def find_config(supplied_config, galaxy_root):
    if supplied_config:
        return supplied_config

    if galaxy_root is None:
        return os.path.abspath('galaxy.yml')

    # If not explicitly supplied an config, check galaxy.ini and then
    # just resort to sample if that has not been configured.
    for guess in DEFAULT_INIS:
        config_path = os.path.join(galaxy_root, guess)
        if os.path.exists(config_path):
            return config_path

    return guess
