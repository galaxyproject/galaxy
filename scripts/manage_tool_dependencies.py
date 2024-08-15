import os.path
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))

from galaxy.config import configure_logging
from galaxy.tool_util.deps import build_dependency_manager
from galaxy.util.properties import find_config_file
from galaxy.util.script import main_factory

DESCRIPTION = "Script to manage tool dependencies (with focus on a Conda environments)."


def _init_if_needed(args, kwargs):
    # If conda_auto_init is set, simply building the Conda resolver will call handle installation.
    _build_dependency_manager_no_config(kwargs)


def _build_dependency_manager_no_config(kwargs):
    """Simplified variant of build_dependency_manager from galaxy.tool_util.deps.

    The canonical factory method requires a full Galaxy configuration object
    which we do not have available in this script (an optimization).
    """
    configure_logging(kwargs)
    base, ext = os.path.splitext(kwargs.get("dependency_resolvers_config_file", "dependency_resolvers_conf.xml"))
    dependency_resolvers_config_file = find_config_file(base, exts=[ext.lstrip(".")])
    # FIXME: default is wrong for installed Galaxy
    dependency_manager = build_dependency_manager(
        app_config_dict=kwargs,
        conf_file=dependency_resolvers_config_file,
        default_tool_dependency_dir="database/dependencies",
    )
    return dependency_manager


ACTIONS = {
    "init_if_needed": _init_if_needed,
}


if __name__ == "__main__":
    main = main_factory(description=DESCRIPTION, actions=ACTIONS)
    main()
