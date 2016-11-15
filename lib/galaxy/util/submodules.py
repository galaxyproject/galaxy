import logging

from os import listdir

log = logging.getLogger(__name__)


def submodules(module):
    unsorted_submodule_names = __submodule_names(module)
    submodule_names = sorted(unsorted_submodule_names, reverse=True)
    submodules = []
    for submodule_name in submodule_names:
        full_submodule = "%s.%s" % (module.__name__, submodule_name)
        try:
            __import__(full_submodule)
            submodule = getattr(module, submodule_name)
            submodules.append(submodule)
        except BaseException as exception:
            exception_str = str(exception)
            message = "%s dynamic module could not be loaded: %s" % (full_submodule, exception_str)
            log.debug(message)
    return submodules


def __submodule_names(module):
    module_dir = module.__path__[0]
    names = []
    for fname in listdir(module_dir):
        if not(fname.startswith("_")) and fname.endswith(".py"):
            submodule_name = fname[:-len(".py")]
            names.append(submodule_name)
    return names
