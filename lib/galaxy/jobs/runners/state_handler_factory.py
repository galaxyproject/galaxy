# Shamelessly stolen from the LWR.

import os
import logging

import galaxy.jobs.runners.state_handlers


log = logging.getLogger(__name__)

def build_state_handlers():
    return _get_state_handlers_dict()

def _get_modules():
    """
    >>> 'galaxy.jobs.runners.state_handlers.resubmit' in _get_modules()
    True
    """
    state_handlers_dir = galaxy.jobs.runners.state_handlers.__path__[0]
    module_names = []
    for fname in os.listdir(state_handlers_dir):
        if not(fname.startswith("_")) and fname.endswith(".py"):
            module_name = "galaxy.jobs.runners.state_handlers.%s" % fname[:-len(".py")]
            module_names.append(module_name)
    log.debug('module_names: %s', module_names)
    return module_names

def _load_modules():
    modules = []
    for module_name in _get_modules():
        try:
            log.debug('Importing %s', module_name)
            module = __import__(module_name)
            for comp in module_name.split(".")[1:]:
                module = getattr(module, comp)
            modules.append(module)
        except BaseException as exception:
            exception_str = str(exception)
            message = "%s module could not be loaded: %s" % (module_name, exception_str)
            log.warn(message)
            continue

    return modules

def _get_state_handlers_dict():
    state_handlers = {}
    for module in _load_modules():
        for func in module.__all__:
            if func not in state_handlers:
                state_handlers[func] = []
            state_handlers[func].append(getattr(module, func))
            log.debug("Loaded '%s' state handler from module %s", func, module.__name__)
    return state_handlers

