from unittest.mock import Mock
from uuid import uuid4

import pytest

from galaxy import exceptions
from galaxy.jobs import JobWrapper
from galaxy.model import DynamicTool
from . import test_job_wrapper


class TestUserToolJobWrapper(test_job_wrapper.AbstractTestCases.BaseWrapperTestCase):
    def setUp(self):
        super().setUp()
        self.job.dynamic_tool = DynamicTool(tool_format="GalaxyUserTool", uuid=uuid4(), public=False, active=True)
        self.dynamic_tool_manager = Mock()
        self.app.dynamic_tool_manager = self.dynamic_tool_manager

    def _wrapper(self):
        return JobWrapper(self.job, self.queue)

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
