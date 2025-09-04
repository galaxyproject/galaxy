from unittest import TestCase

from galaxy.datatypes.text import Ipynb
from .util import get_input_files

class TestIpynbSniffer(TestCase):
    """Test the Jupyter notebook (Ipynb) datatype sniffer"""

    def setUp(self):
        self.ipynb_sniffer = Ipynb()

    def test_empty_metadata_bug_fix(self):
        """Test the specific bug fix: empty metadata dict should not cause rejection"""
        with get_input_files("1.ipynb") as input_files:
            notebook = input_files[0]
            assert self.ipynb_sniffer.sniff(notebook) is True

    def test_missing_metadata_key(self):
        """Test notebook without metadata key (should fail)"""
        with get_input_files("2.ipynb") as input_files:
            notebook = input_files[0]
            assert self.ipynb_sniffer.sniff(notebook) is False

