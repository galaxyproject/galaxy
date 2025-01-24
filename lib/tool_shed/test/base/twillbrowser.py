import tempfile
from typing import (
    Dict,
    List,
)

import twill.commands as tc
from twill.browser import FormElement  # type:ignore[attr-defined, unused-ignore]

from galaxy.util import smart_str
from .browser import (
    FormValueType,
    ShedBrowser,
)

tc.options["equiv_refresh_interval"] = 0
# Resetting all repository metadata can take a really long time
tc.timeout(240)


def visit_url(url: str, allowed_codes: List[int]) -> str:
    tc.go(url)
    return_code = tc.browser.code
    assert return_code in allowed_codes, "Invalid HTTP return code {}, allowed codes: {}".format(
        return_code,
        ", ".join(str(code) for code in allowed_codes),
    )
    return url


def page_content() -> str:
    return tc.browser.html


class TwillShedBrowser(ShedBrowser):
    def visit_url(self, url: str, allowed_codes: List[int]) -> str:
        return visit_url(url, allowed_codes=allowed_codes)

    def page_content(self) -> str:
        """
        Return the last visited page (usually HTML, but can binary data as
        well).
        """
        return page_content()

    def check_page_for_string(self, patt: str) -> None:
        page = self.page_content()
        if page.find(patt) == -1:
            fname = self.write_temp_file(page)
            errmsg = f"no match to '{patt}'\npage content written to '{fname}'\npage: [[{page}]]"
            raise AssertionError(errmsg)

    def check_string_not_in_page(self, patt: str) -> None:
        page = self.page_content()
        if page.find(patt) != -1:
            fname = self.write_temp_file(page)
            errmsg = f"string ({patt}) incorrectly displayed in page.\npage content written to '{fname}'"
            raise AssertionError(errmsg)

    def write_temp_file(self, content, suffix=".html"):
        with tempfile.NamedTemporaryFile(suffix=suffix, prefix="twilltestcase-", delete=False) as fh:
            fh.write(smart_str(content))
        return fh.name

    def submit_form_with_name(self, form_name: str, button="runtool_btn", **kwd):
        forms_by_name: Dict[str, FormElement] = {f.get("name"): f for f in self._show_forms()}
        form = forms_by_name[form_name]
        self._submit_form(form, button, **kwd)

    def _show_forms(self) -> List[FormElement]:
        """Shows form, helpful for debugging new tests"""
        return tc.browser.forms

    def submit_form(self, form_no=-1, button="runtool_btn", form=None, **kwd):
        if form is None:
            try:
                form = self._show_forms()[form_no]
            except IndexError:
                raise ValueError("No form to submit found")
        self._submit_form(form, button, **kwd)

    def _submit_form(self, form, button, **kwd):
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

    def fill_form_value(self, form_name: str, control_name: str, value: FormValueType):
        value = str(value)
        tc.fv(form_name, control_name, value)

    def edit_repository_categories(self, categories_to_add: List[str], categories_to_remove: List[str]) -> None:
        """Select some new categories and then restore the component."""
        strings_displayed = []
        strings_not_displayed = []
        for category in categories_to_add:
            self.fill_form_value("categories", "category_id", f"+{category}")
            strings_displayed.append(f"selected>{category}")
        for category in categories_to_remove:
            self.fill_form_value("categories", "category_id", f"-{category}")
            strings_not_displayed.append(f"selected>{category}")
        self.submit_form_with_name("categories", "manage_categories_button")
        self._check_for_strings(strings_displayed, strings_not_displayed)

        strings_displayed = []
        strings_not_displayed = []
        for category in categories_to_remove:
            self.fill_form_value("categories", "category_id", f"+{category}")
            strings_displayed.append(f"selected>{category}")
        for category in categories_to_add:
            self.fill_form_value("categories", "category_id", f"-{category}")
            strings_not_displayed.append(f"selected>{category}")
        self.submit_form_with_name("categories", "manage_categories_button")
        self._check_for_strings(strings_displayed, strings_not_displayed)

    def grant_users_access(self, usernames: List[str]):
        for username in usernames:
            self.fill_form_value("user_access", "allow_push", f"+{username}")
        self.submit_form_with_name("user_access", "user_access_button")

    @property
    def is_twill(self) -> bool:
        return True

    def _check_for_strings(self, strings_displayed: List[str], strings_not_displayed: List[str]):
        if strings_displayed:
            for check_str in strings_displayed:
                self.check_page_for_string(check_str)
        if strings_not_displayed:
            for check_str in strings_not_displayed:
                self.check_string_not_in_page(check_str)
