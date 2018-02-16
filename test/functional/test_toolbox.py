from __future__ import print_function

import logging
import new

try:
    from nose.tools import nottest
except ImportError:
    def nottest(x):
        return x

from base.driver_util import setup_keep_outdir, target_url_parts
from galaxy.tools import DataManagerTool  # noqa: I201
from galaxy.tools.verify.interactor import GalaxyInteractorApi, ToolTestDescription, verify_tool  # noqa: I201
from .twilltestcase import TwillTestCase

log = logging.getLogger(__name__)

toolbox = None

# Do not test Data Managers as part of the standard Tool Test Framework.
TOOL_TYPES_NO_TEST = (DataManagerTool, )


class ToolTestCase(TwillTestCase):
    """Abstract test case that runs tests based on a `galaxy.tools.test.ToolTest`.

    Ideally this would be FunctionalTestCase instead of a TwillTestCase but the
    subclass DataManagerToolTestCase requires the use of Twill still.
    """

    def do_it(self, testdef, resource_parameters={}):
        """
        Run through a tool test case.
        """
        tool_id = self.tool_id

        self._handle_test_def_errors(testdef)

        galaxy_interactor = self.galaxy_interactor

        verify_tool(testdef, tool_id, galaxy_interactor, resource_parameters=resource_parameters)

    def _handle_test_def_errors(self, testdef):
        # If the test generation had an error, raise
        if testdef.error:
            if testdef.exception:
                if isinstance(testdef.exception, Exception):
                    raise testdef.exception
                else:
                    raise Exception(testdef.exception)
            else:
                raise Exception("Test parse failure")


@nottest
def build_tests(app=None, testing_shed_tools=False, master_api_key=None, user_api_key=None):
    """
    If the module level variable `toolbox` is set, generate `ToolTestCase`
    classes for all of its tests and put them into this modules globals() so
    they can be discovered by nose.
    """
    # galaxy_interactor = None
    # if app is None:
    host, port, url = target_url_parts()
    keep_outputs_dir = setup_keep_outdir()
    galaxy_interactor_kwds = {
        "galaxy_url": url,
        "master_api_key": master_api_key,
        "api_key": user_api_key,
        "keep_outputs_dir": keep_outputs_dir,
    }
    galaxy_interactor = GalaxyInteractorApi(**galaxy_interactor_kwds)

    # Push all the toolbox tests to module level
    G = globals()

    # Eliminate all previous tests from G.
    for key, val in G.items():
        if key.startswith('TestForTool_'):
            del G[key]

    # if app:
    #    tool_ids = app.toolbox.tools_by_id.keys()
    # else:

    tools = galaxy_interactor.get_tools()
    for tool in tools:
        if tool.get("form_style", None) != "regular":
            # We do not test certain types of tools (e.g. Data Manager tools) as part of ToolTestCase
            continue
        tool_id = tool["id"]
        if not tool_id:
            continue
        tool_name = tool["name"]
        tool_test_dicts = galaxy_interactor.get_tool_tests(tool_id)
        if tool_test_dicts:
            # Create a new subclass of ToolTestCase, dynamically adding methods
            # named test_tool_XXX that run each test defined in the tool config.
            name = "TestForTool_" + tool_id.replace(' ', '_')
            baseclasses = (ToolTestCase, )
            namespace = dict()
            for j, tool_test_dict in enumerate(tool_test_dicts):
                testdef = ToolTestDescription(tool_test_dict)
                test_function_name = 'test_tool_%06d' % j

                def make_test_method(td):
                    def test_tool(self):
                        self.do_it(td)
                    test_tool.__name__ = test_function_name

                    return test_tool

                test_method = make_test_method(testdef)
                test_method.__doc__ = "%s ( %s ) > %s" % (tool_name, tool_id, testdef.name)
                namespace[test_function_name] = test_method
                namespace['tool_id'] = tool_id
                namespace["galaxy_interactor"] = galaxy_interactor
                namespace['master_api_key'] = master_api_key
                namespace['user_api_key'] = user_api_key
            # The new.classobj function returns a new class object, with name name, derived
            # from baseclasses (which should be a tuple of classes) and with namespace dict.
            new_class_obj = new.classobj(str(name), baseclasses, namespace)
            G[name] = new_class_obj
