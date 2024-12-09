# Test tools API.
import contextlib
import json
import os
import zipfile
from io import BytesIO
from typing import (
    Any,
    Dict,
    List,
    Optional,
)
from uuid import uuid4

import pytest
from requests import (
    get,
    put,
)

from galaxy.tool_util.verify.interactor import ValidToolTestDict
from galaxy.util import galaxy_root_path
from galaxy.util.unittest_utils import skip_if_github_down
from galaxy.schema.tools import UserToolSource
from galaxy_test.base import rules_test_data
from galaxy_test.base.api_asserts import (
    assert_has_keys,
    assert_status_code_is,
)
from galaxy_test.base.decorators import requires_new_history
from galaxy_test.base.populators import (
    BaseDatasetCollectionPopulator,
    DatasetCollectionPopulator,
    DatasetPopulator,
    skip_without_tool,
    stage_rules_example,
)
from ._framework import ApiTestCase

from .test_tools import TOOL_WITH_SHELL_COMMAND


class TestUnprivilegedToolsApi(ApiTestCase):

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    def test_create_unprivileged(self):
        response = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
        assert response.status_code == 200, response.text
        dynamic_tool = response.json()
        assert dynamic_tool["uuid"]

    def test_list_unprivileged(self):
        response = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
        assert response.status_code == 200, response.text
        response = self.dataset_populator.get_unprivileged_tools()
        assert response.status_code == 200, response.text
        assert response.json()

    def test_show(self):
        response = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
        assert response.status_code == 200, response.text
        response = self.dataset_populator.show_unprivileged_tool(TOOL_WITH_SHELL_COMMAND["id"])
        assert response.status_code == 200, response.text
        assert response.json()

    def test_deactivate(self):
        pass

    def test_run(self):
        pass
