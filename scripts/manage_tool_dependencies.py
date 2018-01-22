import os.path
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'lib')))

from galaxy.config import (
    configure_logging,
    find_path,
    find_root,
    parse_dependency_options,
)
from galaxy.tools.deps import CachedDependencyManager, DependencyManager, NullDependencyManager
from galaxy.util.script import main_factory

DESCRIPTION = "Script to manage tool dependencies (with focus on a Conda environments)."


def _init_if_needed(args, kwargs):
    # If conda_auto_init is set, simply building the Conda resolver will call handle installation.
    _build_dependency_manager_no_config(kwargs)


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
            dependency_manager = DependencyManager(**dependency_manager_kwds)

    return dependency_manager


ACTIONS = {
    "init_if_needed": _init_if_needed,
}


if __name__ == '__main__':
    main = main_factory(description=DESCRIPTION, actions=ACTIONS)
    main()
