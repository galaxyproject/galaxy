import time
from typing import List

from playwright.sync_api import (
    expect,
    Locator,
    Page,
)

from .browser import (
    FormValueType,
    ShedBrowser,
)


class Locators:
    toolbar_login = ".toolbar-login"
    toolbar_logout = ".toolbar-logout"
    login_submit_button = '[name="login_button"]'
    register_link = ".register-link"


class PlaywrightShedBrowser(ShedBrowser):
    _page: Page

    def __init__(self, page: Page):
        self._page = page

    def visit_url(self, url: str, allowed_codes: List[int]) -> str:
        try:
            response = self._page.goto(url)
        except Exception as e:
            if "Navigation interrupted by another one" in str(e):
                # I believe redirect on the target page interfering with
                # this thread's test.
                time.sleep(0.25)
                response = self._page.goto(url)
            else:
                raise
        assert response is not None
        return_code = response.status
        assert return_code in allowed_codes, "Invalid HTTP return code {}, allowed codes: {}".format(
            return_code,
            ", ".join(str(code) for code in allowed_codes),
        )
        return response.url

    def page_content(self) -> str:
        self._page.wait_for_load_state("networkidle")
        return self._page.content()

    def check_page_for_string(self, patt: str) -> None:
        """Looks for 'patt' in the current browser page"""
        patt = patt.replace("<b>", "").replace("</b>", "")
        expect(self._page.locator("body")).to_contain_text(patt)

    def check_string_not_in_page(self, patt: str) -> None:
        patt = patt.replace("<b>", "").replace("</b>", "")
        expect(self._page.locator("body")).not_to_contain_text(patt)

    def xcheck_page_for_string(self, patt: str) -> None:
        page = self.page_content()
        if page.find(patt) == -1:
            fname = self.write_temp_file(page)
            errmsg = f"no match to '{patt}'\npage content written to '{fname}'\npage: [[{page}]]"
            raise AssertionError(errmsg)

    def xcheck_string_not_in_page(self, patt: str) -> None:
        page = self.page_content()
        if page.find(patt) != -1:
            fname = self.write_temp_file(page)
            errmsg = f"string ({patt}) incorrectly displayed in page.\npage content written to '{fname}'"
            raise AssertionError(errmsg)

    def write_temp_file(self, content, suffix=".html"):
        import tempfile

        from galaxy.util import smart_str

        with tempfile.NamedTemporaryFile(suffix=suffix, prefix="twilltestcase-", delete=False) as fh:
            fh.write(smart_str(content))
        return fh.name

    def show_forms(self) -> Locator:
        """Shows form, helpful for debugging new tests"""
        return self._page.locator("form")

    def submit_form_with_name(self, form_name: str, button="runtool_btn", **kwd):
        form = self._form_with_name(form_name)
        self._submit_form(form, button, **kwd)

    def submit_form(self, form_no=-1, button="runtool_btn", form=None, **kwd):
        """Populates and submits a form from the keyword arguments."""
        # An HTMLForm contains a sequence of Controls.  Supported control classes are:
        # TextControl, FileControl, ListControl, RadioControl, CheckboxControl, SelectControl,
        # SubmitControl, ImageControl
        if form is None:
            try:
                form = self.show_forms().nth(form_no)
            except IndexError:
                raise ValueError("No form to submit found")
        self._submit_form(form, button, **kwd)

    def _submit_form(self, form: Locator, button="runtool_btn", **kwd):
        for control_name, control_value in kwd.items():
            self._fill_form_value(form, control_name, control_value)
        input = self._page.locator(f"[name='{button}']")
        if input.count():
            input.click()
        else:
            submit_input = form.locator("input[type=submit]")
            submit_input.click()
        time.sleep(0.25)
        # tc.submit(button)

    def _form_with_name(self, name: str) -> Locator:
        forms = self.show_forms()
        count = forms.count()
        for i in range(count):
            nth_form = self.show_forms().nth(i)
            if nth_form.get_attribute("name") == name:
                return nth_form
        raise KeyError(f"No form with name [{name}]")

    def fill_form_value(self, form_name: str, control_name: str, value: FormValueType):
        form: Locator = self._form_with_name(form_name)
        self._fill_form_value(form, control_name, value)

    def _fill_form_value(self, form: Locator, control_name: str, value: FormValueType):
        input_i = form.locator(f"input[name='{control_name}']")
        input_t = form.locator(f"textarea[name='{control_name}']")
        input_s = form.locator(f"select[name='{control_name}']")
        if input_i.count():
            if control_name in ["redirect"]:
                input_i.input_value = value  # type:ignore[assignment, unused-ignore]
            else:
                if isinstance(value, bool):
                    if value and not input_i.is_checked():
                        input_i.check()
                    elif not value and input_i.is_checked():
                        input_i.uncheck()
                else:
                    input_i.fill(value)
        if input_t.count():
            input_t.fill(value)  # type:ignore[arg-type, unused-ignore]
        if input_s.count():
            input_s.select_option(value)  # type:ignore[arg-type, unused-ignore]

    def edit_repository_categories(self, categories_to_add: List[str], categories_to_remove: List[str]) -> None:
        multi_select = "form[name='categories'] select[name='category_id']"
        select_locator = self._page.locator(multi_select)
        select_locator.evaluate("node => node.selectedOptions = []")
        select_locator.select_option(label=categories_to_add)
        self.submit_form_with_name("categories", "manage_categories_button")

        select_locator.evaluate("node => node.selectedOptions = []")
        select_locator.select_option(label=categories_to_remove)
        self.submit_form_with_name("categories", "manage_categories_button")

    def grant_users_access(self, usernames: List[str]):
        multi_select = "form[name='user_access'] select[name='allow_push']"
        select_locator = self._page.locator(multi_select)
        select_locator.evaluate("node => node.selectedOptions = []")
        select_locator.select_option(label=usernames)
        self.submit_form_with_name("user_access", "user_access_button")

    @property
    def is_twill(self) -> bool:
        return False

    def logout_if_logged_in(self, assert_logged_out=True):
        self._page.wait_for_selector(f"{Locators.toolbar_login}, {Locators.toolbar_logout}")
        logout_locator = self._page.locator(Locators.toolbar_logout)
        if logout_locator.is_visible():
            logout_locator.click()
            self._page.wait_for_load_state("networkidle")
        if assert_logged_out:
            self.expect_not_logged_in()

    def explicit_logout(self):
        self._page.wait_for_selector(Locators.toolbar_logout)
        logout_locator = self._page.locator(Locators.toolbar_logout)
        logout_locator.click()
        self._page.wait_for_load_state("networkidle")
        expect(self._page.locator(Locators.toolbar_logout)).not_to_be_visible()

    def expect_not_logged_in(self):
        expect(self._page.locator(Locators.toolbar_logout)).not_to_be_visible()

    def expect_logged_in(self):
        expect(self._page.locator(Locators.toolbar_logout)).to_be_visible()
