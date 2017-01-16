from __future__ import print_function

import argparse
import os.path
import sys
import threading

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'lib')))

from galaxy.util.properties import find_config_file, load_app_properties
from galaxy.config import (
    Configuration,
    configure_logging,
    ConfiguresGalaxyMixin,
    find_path,
    find_root,
    parse_dependency_options,
)
from galaxy.tools.deps import (
    build_dependency_manager,
    CachedDependencyManager,
    DependencyManager,
    NullDependencyManager,
)
from galaxy.util import listify

DESCRIPTION = "Script to manage tool dependencies (with focus on a Conda environments)."


def main(argv=None):
    """Entry point for conversion process."""
    if argv is None:
        argv = sys.argv[1:]
    args = _arg_parser().parse_args(argv)
    action = args.action
    action_func = ACTIONS[action]
    action_func(args)


def _init_if_needed(args):
    kwargs = _app_properties(args)

    # If conda_auto_init is set, simply building the Conda resolver will call handle installation.
    _build_dependency_manager_no_config(kwargs)


def _install_if_needed(args):
    kwargs = _app_properties(args)

    config = _app_config(kwargs)
    ensure_tools_installed = getattr(config, "ensure_tools_installed", None)

    if args.tool_ids is not None:
        tool_ids = args.tool_ids
    else:
        tool_ids = listify(ensure_tools_installed)

    if not tool_ids and not args.all_tools:
        print("install_if_needed called without any tools specified")
        return

    ensure_tools_installed = listify(ensure_tools_installed)
    app = _ManageApp(config)

    toolbox = app.toolbox
    try:
        tools = []
        if args.all_tools:
            print("Installing dependencies for all tools.")
            tools_by_id = toolbox.tools()
            for tool_id, tool in tools_by_id:
                tools.append(tool)
        else:
            for tool_id in tool_ids:
                try:
                    tool = toolbox.get_tool(tool_id)
                except Exception:
                    tool = None

                if tool is None:
                    print("Failed to find tool '%s'" % tool_id)
                    continue

                tools.append(tool)

        for tool in tools:
            tool_id = tool.id
            try:
                tool.install_dependencies()
            except Exception:
                print("Failed to install dependencies for tool '%s'" % tool_id)
                continue
    finally:
        toolbox.shutdown()


class _ManageApp(object, ConfiguresGalaxyMixin):

    def __init__(self, config):
        self.name = "manage_tool_dependencies"
        self.config = config
        self._toolbox_lock = threading.RLock()
        self._configure_object_store()
        self._configure_models()
        self._configure_datatypes_registry()
        self._configure_tool_data_tables(from_shed_config=True)
        self._configure_genome_builds()
        self._configure_toolbox()
        self.dependency_manager = build_dependency_manager(config)


def _app_properties(args):
    config_file = find_config_file("config/galaxy.ini", "universe_wsgi.ini", args.config_file)
    app_properties = load_app_properties(ini_file=config_file)
    return app_properties


def _arg_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('action', metavar='ACTION', type=str,
                        choices=ACTIONS.keys(),
                        help='action to perform')
    parser.add_argument("-c", "--config-file", default=None)
    tool_target_group = parser.add_mutually_exclusive_group()
    tool_target_group.add_argument("--all-tools", action="store_true", default=False, help="Attempt to install dependencies for all tools in the toolbox.")
    tool_target_group.add_argument("--tool-id", dest="tool_ids", action="append", help="Attempt to install dependencies for specified tool id.")
    return parser


def _app_config(kwargs):
    config = Configuration(**kwargs)
    config.check()
    configure_logging(config)

    config.watch_tools = False
    config.update_integrated_tool_panel = True
    return config


def _build_dependency_manager_no_config(kwargs):
    """Simplified variant of build_dependency_manager from galaxy.tools.deps.

    The canonical factory method requires a full Galaxy configuration object
    which we do not have available in this script (an optimization).
    """
    configure_logging(kwargs)
    root = find_root(kwargs)
    dependency_resolvers_config_file = find_path(kwargs, "dependency_resolvers_config_file", root)
    use_dependencies, tool_dependency_dir, use_cached_dependency_manager, tool_dependency_cache_dir, precache_dependencies = \
        parse_dependency_options(kwargs, root, dependency_resolvers_config_file)

    if not use_dependencies:
        dependency_manager = NullDependencyManager()
    else:
        dependency_manager_kwds = {
            'default_base_path': tool_dependency_dir,
            'conf_file': dependency_resolvers_config_file,
            'app_config': kwargs,
        }

        if use_cached_dependency_manager:
            dependency_manager_kwds['tool_dependency_cache_dir'] = tool_dependency_cache_dir
            dependency_manager = CachedDependencyManager(**dependency_manager_kwds)
        else:
            dependency_manager = DependencyManager( **dependency_manager_kwds )

    return dependency_manager


ACTIONS = {
    "init_if_needed": _init_if_needed,
    "install_if_needed": _install_if_needed,
}


if __name__ == '__main__':
    main()
