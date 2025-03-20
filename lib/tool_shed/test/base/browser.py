import abc
from typing import (
    List,
    Union,
)

FormValueType = Union[str, bool]


class ShedBrowser(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def visit_url(self, url: str, allowed_codes: List[int]) -> str:
        """Navigate to the supplied URL."""

    @abc.abstractmethod
    def page_content(self) -> str:
        """Return the page content for"""

    @abc.abstractmethod
    def check_page_for_string(self, patt: str) -> None:
        """Looks for 'patt' in the current browser page"""

    @abc.abstractmethod
    def check_string_not_in_page(self, patt: str) -> None:
        """Looks for 'patt' not being in the current browser page"""

    @abc.abstractmethod
    def fill_form_value(self, form_name: str, control_name: str, value: FormValueType):
        """Fill in a form value."""

    @abc.abstractmethod
    def submit_form(self, form_no=-1, button="runtool_btn", form=None, **kwd):
        """Submit the target button."""

    @abc.abstractmethod
    def submit_form_with_name(self, form_name: str, button="runtool_btn", **kwd):
        """Submit the target button."""

    @property
    @abc.abstractmethod
    def is_twill(self) -> bool:
        """Return whether this is a twill browser."""

    @abc.abstractmethod
    def edit_repository_categories(self, categories_to_add: List[str], categories_to_remove: List[str]) -> None:
        """Select some new categories and then restore the component."""

    @abc.abstractmethod
    def grant_users_access(self, usernames: List[str]) -> None:
        """Select users to grant access to."""
