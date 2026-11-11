import os
from unittest.mock import Mock
from uuid import uuid4

import pytest

from galaxy import exceptions
from galaxy.jobs import JobWrapper
from galaxy.model import DynamicTool
from galaxy.tool_util.deps.image_references import ContainerAllowlist
from galaxy.tool_util.deps.requirements import ContainerDescription
from . import test_job_wrapper


class TestUserToolJobWrapper(test_job_wrapper.AbstractTestCases.BaseWrapperTestCase):
    def setUp(self):
        super().setUp()
        self.job.dynamic_tool = DynamicTool(tool_format="GalaxyUserTool", uuid=uuid4(), public=False, active=True)
        self.dynamic_tool_manager = Mock()
        self.app.dynamic_tool_manager = self.dynamic_tool_manager

    def _wrapper(self):
        return JobWrapper(self.job, self.queue)

    def _prepare(self, container, tool_type="user_defined"):
        wrapper = self._wrapper()
        wrapper._get_tool_evaluator = lambda *args, **kwargs: test_job_wrapper.MockEvaluator(
            wrapper.app, wrapper.tool, wrapper.get_job(), wrapper.working_directory
        )
        wrapper.tool.tool_type = tool_type
        wrapper.tool.containers = [ContainerDescription(container)]
        self.dynamic_tool_manager.container_allowlist = ContainerAllowlist(["quay.io/biocontainers/*"])
        wrapper.prepare()

    def test_prepare_fails_when_owner_lost_execute_role_after_wrapper_was_created(self):
        wrapper = self._wrapper()
        wrapper._get_tool_evaluator = lambda *args, **kwargs: test_job_wrapper.MockEvaluator(
            wrapper.app, wrapper.tool, wrapper.get_job(), wrapper.working_directory
        )
        self.dynamic_tool_manager.ensure_can_use_unprivileged_tool.side_effect = (
            exceptions.InsufficientPermissionsException("User is not allowed to run unprivileged tools")
        )
        with pytest.raises(exceptions.InsufficientPermissionsException):
            wrapper.prepare()
        self.dynamic_tool_manager.ensure_can_use_unprivileged_tool.assert_called_once_with(self.job.user)

    def test_prepare_fails_for_container_outside_allowlist(self):
        with pytest.raises(exceptions.InsufficientPermissionsException, match="Container 'busybox' is not allowed"):
            self._prepare("busybox")

    def test_prepare_allows_container_in_allowlist(self):
        self._prepare("quay.io/biocontainers/samtools:1.17")

    def test_prepare_does_not_check_containers_of_other_tools(self):
        self._prepare("busybox", tool_type="default")

    def test_prepare_skips_upload_paramfile_copy_for_user_tool_with_upload_id(self):
        # A user tool picks its own id and inputs, so sharing the upload tool's id and
        # paramfile parameter name must not get the upload tool's paramfile handling.
        param_file_path = self._add_upload_paramfile()
        with self._prepared_wrapper() as wrapper:
            assert not os.path.exists(os.path.join(wrapper.working_directory, "configs", "upload_params.json"))
        assert self._paramfile_values() == [param_file_path]
