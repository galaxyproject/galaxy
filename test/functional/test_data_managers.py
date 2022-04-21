import logging

from .test_toolbox import build_tests as _build_tests
from .test_toolbox import ToolTestCase

try:
    from nose.tools import nottest
except ImportError:

    def nottest(x):
        return x


log = logging.getLogger(__name__)
data_managers = None


class DataManagerToolTestCase(ToolTestCase):
    """Test case that runs Data Manager tests based on a `galaxy.tools.test.ToolTest`"""


@nottest
def build_tests(
    tmp_dir=None, testing_shed_tools=False, master_api_key=None, user_api_key=None, create_admin=False, user_email=None
):
    """
    If the module level variable `data_managers` is set, generate `DataManagerToolTestCase`
    classes for all of its tests and put them into this modules globals() so
    they can be discovered by nose.
    """

    if data_managers is None:
        log.warning("data_managers was not set for Data Manager functional testing. Will not test.")
        return

    G = globals()

    _build_tests(
        testing_shed_tools=testing_shed_tools,
        master_api_key=master_api_key,
        user_api_key=user_api_key,
        name_prefix="TestForDataManagerTool_",
        baseclass=DataManagerToolTestCase,
        user_email=user_email,
        create_admin=create_admin,
        G=G,
        contains="data_manager",
    )
