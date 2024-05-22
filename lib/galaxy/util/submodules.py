import importlib
import logging
import pkgutil

log = logging.getLogger(__name__)


def import_submodules(module, ordered=True, recursive=False):
    """Import all submodules of a module

    :param module: module (package name or actual module)
    :type module: str | module

    :param ordered: Whether to order the returned modules. The default is True, and
           modules are returned in reverse order to allow hierarchical overrides
           i.e. 000_galaxy_rules.py, 100_site_rules.py, 200_instance_rules.py
    :type ordered: bool

    :param recursive: Recursively returns all subpackages
    :type recursive: bool

    :rtype: [module]
    """
    sub_modules = __import_submodules_impl(module, recursive)
    if ordered:
        return sorted(sub_modules, reverse=True, key=lambda m: m.__name__)
    else:
        return sub_modules


def __import_submodules_impl(module, recursive=False):
    """Implementation of import only, without sorting.

    :param module: module (package name or actual module)
    :type module: str | module
    :rtype: [module]
    """
    if isinstance(module, str):
        module = importlib.import_module(module)
    submodules = []
    for _, name, is_pkg in pkgutil.walk_packages(module.__path__):
        full_name = f"{module.__name__}.{name}"
        try:
            submodule = importlib.import_module(full_name)
            submodules.append(submodule)
            if recursive and is_pkg:
                submodules.update(__import_submodules_impl(submodule, recursive=True))
        except Exception:
            message = f"{full_name} dynamic module could not be loaded (traceback follows):"
            log.exception(message)
            continue
    return submodules
