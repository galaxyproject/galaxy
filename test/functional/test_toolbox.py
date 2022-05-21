import logging

try:
    from nose.tools import nottest
except ImportError:

    def nottest(x):
        return x


from galaxy.tool_util.verify.interactor import (
    GalaxyInteractorApi,
    verify_tool,
)
from galaxy.tools import DataManagerTool
from galaxy_test.base.env import (
    setup_keep_outdir,
    target_url_parts,
)
from galaxy_test.base.instrument import register_job_data
from galaxy_test.driver.testcase import DrivenFunctionalTestCase

log = logging.getLogger(__name__)

toolbox = None

# Do not test Data Managers as part of the standard Tool Test Framework.
TOOL_TYPES_NO_TEST = (DataManagerTool,)


class ToolTestCase(DrivenFunctionalTestCase):
    """Abstract test case that runs tests based on a `galaxy.tools.test.ToolTest`."""

    def do_it(self, tool_id=None, tool_version=None, test_index=0, resource_parameters=None):
        """
        Run through a tool test case.
        """
        resource_parameters = resource_parameters or {}
        if tool_id is None:
            tool_id = self.tool_id
        assert tool_id

        verify_tool(
            tool_id,
            self.galaxy_interactor,
            resource_parameters=resource_parameters,
            test_index=test_index,
            tool_version=tool_version,
            register_job_data=register_job_data,
        )


@nottest
def build_tests(
    app=None,
    testing_shed_tools=False,
    master_api_key=None,
    user_api_key=None,
    name_prefix="TestForTool_",
    baseclass=ToolTestCase,
    create_admin=False,
    user_email=None,
    G=None,
    contains=None,
):
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
        "user_api_key_is_admin_key": True,
    }
    if create_admin and not user_api_key:
        galaxy_interactor_kwds["test_user"] = user_email
    galaxy_interactor = GalaxyInteractorApi(**galaxy_interactor_kwds)

    if not G:
        # Push all the toolbox tests to module level
        G = globals()

    # Eliminate all previous tests from G.
    for key in G.copy().keys():
        if key.startswith("TestForTool_"):
            del G[key]

    tests_summary = galaxy_interactor.get_tests_summary()
    for tool_id, tool_summary in tests_summary.items():
        # Create a new subclass of ToolTestCase, dynamically adding methods
        # named test_tool_XXX that run each test defined in the tool config.
        if contains and contains not in tool_id:
            continue
        name = name_prefix + tool_id.replace(" ", "_")
        baseclasses = (baseclass,)
        namespace = dict()

        all_versions_test_count = 0

        for tool_version, version_summary in tool_summary.items():
            count = version_summary["count"]
            for i in range(count):
                test_function_name = "test_tool_%06d" % all_versions_test_count

                def make_test_method(tool_version, test_index):
                    def test_tool(self):
                        self.do_it(tool_version=tool_version, test_index=test_index)

                    test_tool.__name__ = test_function_name

                    return test_tool

                test_method = make_test_method(tool_version, i)
                test_method.__doc__ = "( %s ) > Test-%d" % (tool_id, all_versions_test_count + 1)
                namespace[test_function_name] = test_method
                namespace["tool_id"] = tool_id
                namespace["galaxy_interactor"] = galaxy_interactor
                namespace["master_api_key"] = master_api_key
                namespace["user_api_key"] = user_api_key or galaxy_interactor.api_key
                namespace["test_count"] = count

                all_versions_test_count += 1

            # Create new class object, with name name, derived
            # from baseclasses (which should be a tuple of classes) and with namespace dict.
            new_class_obj = type(str(name), baseclasses, namespace)
            G[name] = new_class_obj
    return G
