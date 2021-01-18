import os

from .framework import (
    NotebookSeleniumTestCase,
)
from ..framework import (
    selenium_test,
)
NOTEBOOK_PATH = os.path.join(os.path.dirname(__file__), 'notebook.ipynb')


class NotebookTestCase(NotebookSeleniumTestCase):

    @selenium_test
    def test_notebook(self):
        self._validate_notebook(NOTEBOOK_PATH)
