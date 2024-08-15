"""Variant of JuypterContextImpl that can also use populators.

This provides an environment separate from test cases that can leaverage
both Selenium for testing Galaxy with a browser and API populators for filling
in fixture data rapidly in the target Galaxy.
"""

from typing import Optional

from galaxy.selenium.context import init as base_init
from galaxy.selenium.jupyter_context import JupyterContextImpl
from galaxy_test.base.api_util import get_admin_api_key
from .framework import GalaxyTestSeleniumContext


class JupyterTestContextImpl(JupyterContextImpl, GalaxyTestSeleniumContext):
    # Reload components interactively to limit number of Python kernel
    # restarts needed during test building.
    _interactive_components = True

    def __init__(self, from_dict: Optional[dict] = None) -> None:
        from_dict = from_dict or {}
        super().__init__(from_dict)
        self.admin_api_key = from_dict.get("admin_api_key", get_admin_api_key())
        self.login_email = from_dict.get("login_email")
        self.login_password = from_dict.get("login_password")

    def test_login(self):
        self.home()
        self.submit_login(self.login_email, self.login_password)


def init(config=None):
    return base_init(config, clazz=JupyterTestContextImpl)
