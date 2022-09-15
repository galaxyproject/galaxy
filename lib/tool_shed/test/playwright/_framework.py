from urllib.parse import (
    urlencode,
    urlparse,
)

import pytest
from playwright.sync_api import (
    expect,
    Locator,
    Page,
)

from tool_shed.test.base.api import ShedBaseTestCase
from tool_shed.test.base.twilltestcase import test_db_util


@pytest.mark.usefixtures("page")
class ShedPlaywrightTestCase(ShedBaseTestCase):
    def setUp(self):
        super().setUp()
        self.test_db_util = test_db_util

    @pytest.fixture(autouse=True)
    def inject_page(self, page: Page):
        self._page = page

    def _visit_url(self, url, params=None, doseq=False, allowed_codes=None):
        page = self._page
        # mirror twilltestcase visit_url...
        if allowed_codes is None:
            allowed_codes = [200]
        if params is None:
            params = dict()
        parsed_url = urlparse(url)
        if len(parsed_url.netloc) == 0:
            url = f"http://{self.host}:{self.port}{parsed_url.path}"
        else:
            url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
        if parsed_url.query:
            for query_parameter in parsed_url.query.split("&"):
                key, value = query_parameter.split("=")
                params[key] = value
        if params:
            url += f"?{urlencode(params, doseq=doseq)}"
        response = page.goto(url)
        return_code = response.status
        assert return_code in allowed_codes, "Invalid HTTP return code {}, allowed codes: {}".format(
            return_code,
            ", ".join(str(code) for code in allowed_codes),
        )
        return response

    def _check_for_strings(self, strings_displayed=None, strings_not_displayed=None):
        strings_displayed = strings_displayed or []
        strings_not_displayed = strings_not_displayed or []
        if strings_displayed:
            for check_str in strings_displayed:
                self._check_page_for_string(check_str)
        if strings_not_displayed:
            for check_str in strings_not_displayed:
                self._check_string_not_in_page(check_str)

    def _check_page_for_string(self, patt):
        """Looks for 'patt' in the current browser page"""
        expect(self._page.locator("body")).to_contain_text(patt)

    def _check_string_not_in_page(self, patt):
        expect(self._page.locator("body")).not_to_contain_text(patt)

    def _logout(self) -> None:
        self._visit_url("/user/logout")
        self._check_page_for_string("You have been logged out")

    def _login(
        self,
        email: str = "test@bx.psu.edu",
        password: str = "testuser",
        username: str = "admin-user",
        redirect: str = "",
        logout_first: bool = True,
    ):
        # Clear cookies.
        if logout_first:
            self._logout()
        # test@bx.psu.edu is configured as an admin user
        previously_created, username_taken, invalid_username = self._create(
            email=email, password=password, username=username, redirect=redirect
        )
        if previously_created:
            # The acount has previously been created, so just login.
            # HACK: don't use panels because late_javascripts() messes up the twill browser and it
            # can't find form fields (and hence user can't be logged in).
            params = {"use_panels": False}
            self._visit_url("/user/login", params=params)
            self.submit_form(button="login_button", login=email, redirect=redirect, password=password)

    def _create(
        self, cntrller="user", email="test@bx.psu.edu", password="testuser", username="admin-user", redirect=""
    ):
        # HACK: don't use panels because late_javascripts() messes up the twill browser and it
        # can't find form fields (and hence user can't be logged in).
        params = dict(cntrller=cntrller, use_panels=False)
        self._visit_url("/user/create", params)
        self._page.locator("#email_input").fill(email)
        self._page.locator("#password_input").fill(password)
        self._page.locator("#password_check_input").fill(password)
        self._page.locator("#name_input").fill(username)
        self._page.locator("#send").click()
        previously_created = False
        username_taken = False
        invalid_username = False
        try:
            self._check_page_for_string("Created new user account")
        except AssertionError:
            try:
                # May have created the account in a previous test run...
                self._check_page_for_string(f"User with email '{email}' already exists.")
                previously_created = True
            except AssertionError:
                try:
                    self._check_page_for_string("Public name is taken; please choose another")
                    username_taken = True
                except AssertionError:
                    # Note that we're only checking if the usr name is >< 4 chars here...
                    try:
                        self._check_page_for_string("Public name must be at least 4 characters in length")
                        invalid_username = True
                    except AssertionError:
                        pass
        return previously_created, username_taken, invalid_username

    def showforms(self) -> Locator:
        """Shows form, helpful for debugging new tests"""
        return self._page.locator("form")

    def _submit_form(self, form_no=-1, button="runtool_btn", form=None, **kwd):
        """Populates and submits a form from the keyword arguments."""
        # An HTMLForm contains a sequence of Controls.  Supported control classes are:
        # TextControl, FileControl, ListControl, RadioControl, CheckboxControl, SelectControl,
        # SubmitControl, ImageControl
        if form is None:
            try:
                form = self.showforms().nth(form_no)
            except IndexError:
                raise ValueError("No form to submit found")
        controls = {c.name: c for c in form.inputs}
        form_name = form.get("name")
        for control_name, control_value in kwd.items():
            if control_name not in controls:
                continue  # these cannot be handled safely - cause the test to barf out
            if not isinstance(control_value, list):
                control_value = [str(control_value)]
            control = controls[control_name]
            control_type = getattr(control, "type", None)
            if control_type in (
                "text",
                "textfield",
                "submit",
                "password",
                "TextareaElement",
                "checkbox",
                "radio",
                None,
            ):
                for cv in control_value:
                    tc.fv(form_name, control.name, cv)
            else:
                # Add conditions for other control types here when necessary.
                pass
        tc.submit(button)

    def _create_category(self, name: str, description: str):
        if not self.populator.has_category_with_name(name):
            self.populator.new_category(name, description)
