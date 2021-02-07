import logging
import multiprocessing as mp
import sys

from galaxy.util import listify

log = logging.getLogger(__name__)


class CreateUserFactory:
    """
    An instance of this class is responsible for filtering the list
    of tools presented to a given user in a given context.
    """

    def __init__(self, app):
        self.__base_modules = listify(getattr(app.config, "user_create_base_modules", "galaxy.users.create"))
        self.__functions = listify(getattr(app.config, "user_create_functions", ""))
        self.__loaded_functions = []
        self.__init_functions()

    def run(self, user):
        run_user_functions(self.__loaded_functions, user)

    def __init_functions(self):
        for usercreatefunction in self.__functions:
            create_user_function = self.build_create_user_function(usercreatefunction)
            if create_user_function is not None:
                self.__loaded_functions.append(create_user_function)

    def build_create_user_function(self, filter_name):
        """Obtain python function (importing a submodule if needed)
        corresponding to create user name.
        """
        if ":" in filter_name:
            # Should be a submodule of filters (e.g. examples:restrict_development_tools)
            (module_name, function_name) = filter_name.rsplit(":", 1)
            function = self._import_create_user(module_name, function_name)
        else:
            # No module found, just load a function from this file or
            # one that has be explicitly imported.
            function = globals()[filter_name.strip()]
        return function

    def _import_create_user(self, module_name, function_name):
        function_name = function_name.strip()
        for base_module in self.__base_modules:
            full_module_name = f"{base_module}.{module_name.strip()}"
            try:
                __import__(full_module_name)
            except ImportError:
                continue
            module = sys.modules[full_module_name]
            if hasattr(module, function_name):
                return getattr(module, function_name)
        log.warning("Failed to load module for '%s.%s'.", module_name, function_name, exc_info=True)


def run_user_functions(functions, user):
    # Spawn processes so the regular user creation process doesn't hang
    mp.set_start_method('spawn')
    user = user.to_dict()
    for function in functions:
        log.debug("Running after user creation function: %s" % function.__name__)
        p = mp.Process(target=function, args=(user,), daemon=True)
        p.start()
