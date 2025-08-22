import json
import tempfile
from unittest import TestCase

from galaxy.datatypes.sniff import FilePrefix
from galaxy.datatypes.text import (
    Ipynb,
    Json,
)


class TestIpynbSniffer(TestCase):
    """Test the Jupyter notebook (Ipynb) datatype sniffer"""

    def setUp(self):
        self.ipynb_sniffer = Ipynb()
        self.json_sniffer = Json()

    def _create_test_file(self, content):
        """Helper to create a temporary file with given content"""
        temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json")
        if isinstance(content, str):
            temp_file.write(content)
        else:
            json.dump(content, temp_file)
        temp_file.flush()
        return temp_file.name

    def _test_sniffer(self, content, expected_ipynb_result, expected_json_result=None):
        """Helper to test both sniffers on given content"""
        filename = self._create_test_file(content)
        file_prefix = FilePrefix(filename)

        ipynb_result = self.ipynb_sniffer.sniff_prefix(file_prefix)
        self.assertEqual(
            ipynb_result,
            expected_ipynb_result,
            f"Ipynb sniffer should return {expected_ipynb_result} for content: {content}",
        )

        if expected_json_result is not None:
            json_result = self.json_sniffer.sniff_prefix(file_prefix)
            self.assertEqual(
                json_result,
                expected_json_result,
                f"Json sniffer should return {expected_json_result} for content: {content}",
            )

    def test_valid_jupyter_notebook_minimal(self):
        """Test a minimal valid Jupyter notebook"""
        notebook = {"nbformat": 4, "nbformat_minor": 2, "metadata": {}, "cells": []}
        self._test_sniffer(notebook, True, True)

    def test_valid_jupyter_notebook_with_metadata(self):
        """Test a Jupyter notebook with non-empty metadata"""
        notebook = {
            "nbformat": 4,
            "nbformat_minor": 2,
            "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
            "cells": [],
        }
        self._test_sniffer(notebook, True, True)

    def test_valid_jupyter_notebook_with_cells(self):
        """Test a Jupyter notebook with actual cells"""
        notebook = {
            "nbformat": 4,
            "nbformat_minor": 2,
            "metadata": {},
            "cells": [
                {
                    "cell_type": "code",
                    "execution_count": 1,
                    "metadata": {},
                    "outputs": [],
                    "source": ["print('hello world')"],
                },
                {"cell_type": "markdown", "metadata": {}, "source": ["# Test Notebook"]},
            ],
        }
        self._test_sniffer(notebook, True, True)

    def test_empty_metadata_bug_fix(self):
        """Test the specific bug fix: empty metadata dict should not cause rejection"""
        notebook = {
            "nbformat": 4,
            "nbformat_minor": 2,
            "metadata": {},  # This empty dict was causing the bug
            "cells": [
                {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["# Test cell"]}
            ],
        }
        # This should return True after the fix
        self._test_sniffer(notebook, True, True)

    def test_missing_metadata_key(self):
        """Test notebook without metadata key (should fail)"""
        notebook = {
            "nbformat": 4,
            "nbformat_minor": 2,
            "cells": [],
            # No metadata key
        }
        self._test_sniffer(notebook, False, True)

    def test_missing_nbformat(self):
        """Test notebook without nbformat (should fail)"""
        notebook = {
            "nbformat_minor": 2,
            "metadata": {},
            "cells": [],
            # No nbformat key
        }
        self._test_sniffer(notebook, False, True)

    def test_nbformat_false_value(self):
        """Test notebook with nbformat set to False (should fail)"""
        notebook = {"nbformat": False, "nbformat_minor": 2, "metadata": {}, "cells": []}
        self._test_sniffer(notebook, False, True)

    def test_old_notebook_format_v3(self):
        """Test old v3 notebook format (should still work)"""
        notebook = {"nbformat": 3, "nbformat_minor": 0, "metadata": {}, "worksheets": [{"cells": []}]}
        self._test_sniffer(notebook, True, True)

    def test_invalid_json(self):
        """Test invalid JSON content (should fail for both)"""
        invalid_json = '{"nbformat": 4, "metadata": {, "cells": []}'
        self._test_sniffer(invalid_json, False, False)

    def test_non_json_content(self):
        """Test non-JSON content (should fail for both)"""
        non_json = "This is not JSON content at all"
        self._test_sniffer(non_json, False, False)

    def test_json_array_not_object(self):
        """Test JSON array instead of object (should fail for ipynb, succeed for json)"""
        json_array = [1, 2, 3, 4]
        self._test_sniffer(json_array, False, True)

    def test_regular_json_object(self):
        """Test regular JSON object that's not a notebook (should fail for ipynb, succeed for json)"""
        regular_json = {"name": "test", "value": 123, "items": ["a", "b", "c"]}
        self._test_sniffer(regular_json, False, True)

    def test_json_with_nbformat_but_no_metadata(self):
        """Test JSON with nbformat but missing metadata (should fail for ipynb)"""
        fake_notebook = {"nbformat": 4, "data": "some data"}
        self._test_sniffer(fake_notebook, False, True)

    def test_json_with_metadata_but_no_nbformat(self):
        """Test JSON with metadata but missing nbformat (should fail for ipynb)"""
        fake_notebook = {"metadata": {}, "data": "some data"}
        self._test_sniffer(fake_notebook, False, True)

    def test_complex_real_world_notebook(self):
        """Test a more complex notebook structure similar to real-world examples"""
        notebook = {
            "nbformat": 4,
            "nbformat_minor": 4,
            "metadata": {
                "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                "language_info": {"name": "python", "version": "3.8.5"},
            },
            "cells": [
                {
                    "cell_type": "markdown",
                    "id": "cell-id-1",
                    "metadata": {},
                    "source": ["# Machine Learning Example\n", "This notebook demonstrates basic ML concepts."],
                },
                {
                    "cell_type": "code",
                    "execution_count": 1,
                    "id": "cell-id-2",
                    "metadata": {"tags": ["parameters"]},
                    "outputs": [{"name": "stdout", "output_type": "stream", "text": ["Hello, Jupyter!\n"]}],
                    "source": ["import numpy as np\n", "import pandas as pd\n", "print('Hello, Jupyter!')"],
                },
            ],
        }
        self._test_sniffer(notebook, True, True)


class TestJsonSniffer(TestCase):
    """Test the Json datatype sniffer for comparison"""

    def setUp(self):
        self.json_sniffer = Json()

    def _test_json_sniffer(self, content, expected_result):
        """Helper to test Json sniffer on given content"""
        temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json")
        if isinstance(content, str):
            temp_file.write(content)
        else:
            json.dump(content, temp_file)
        temp_file.flush()

        file_prefix = FilePrefix(temp_file.name)
        result = self.json_sniffer.sniff_prefix(file_prefix)
        self.assertEqual(
            result, expected_result, f"Json sniffer should return {expected_result} for content: {content}"
        )

    def test_valid_json_object(self):
        """Test valid JSON object"""
        json_obj = {"key": "value", "number": 42}
        self._test_json_sniffer(json_obj, True)

    def test_valid_json_array(self):
        """Test valid JSON array"""
        json_array = [1, 2, 3, "test"]
        self._test_json_sniffer(json_array, True)

    def test_invalid_json(self):
        """Test invalid JSON"""
        invalid_json = '{"key": "value", invalid}'
        self._test_json_sniffer(invalid_json, False)

    def test_empty_file(self):
        """Test empty file"""
        self._test_json_sniffer("", False)
