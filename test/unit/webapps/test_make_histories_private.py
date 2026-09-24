"""Regression tests for https://github.com/galaxyproject/galaxy/issues/22173.

When make_private is called with all_histories=True, no history_id is provided.
The bug was calling disable_link_access(trans, history_id) where history_id is None,
instead of disable_link_access(trans, history.id).
"""

import json
from unittest.mock import MagicMock

from galaxy import model
from galaxy.app_unittest_utils import galaxy_mock
from galaxy.managers.histories import HistoryManager
from galaxy.managers.users import UserManager
from galaxy.util.unittest import TestCase
from galaxy.webapps.galaxy.controllers.history import HistoryController


class TestMakeHistoriesPrivateController(TestCase):
    def setUp(self):
        self.trans = galaxy_mock.MockTrans()
        self.app = self.trans.app
        self.user_manager = self.app[UserManager]
        self.user = self.user_manager.create(email="test@example.org", username="test", password="testpass")
        self.trans.set_user(self.user)

    def test_make_all_histories_private_uses_history_id_not_history_id_param(self):
        """Regression: disable_link_access must be called with history.id, not history_id (which is None when all_histories=True)."""
        history1 = model.History(name="History 1", user=self.user)
        history2 = model.History(name="History 2", user=self.user)
        history1.importable = True
        history2.importable = True
        self.app.model.session.add_all([history1, history2])
        self.app.model.session.commit()

        controller = HistoryController(self.app)
        controller.history_manager = self.app[HistoryManager]
        mock_link_access = MagicMock()
        mock_link_access.importable = False
        controller.service = MagicMock()
        controller.service.shareable_service.disable_link_access.return_value = mock_link_access

        result = json.loads(controller.make_private(self.trans, all_histories=True))

        assert "all histories" in result["message"]
        private_role = self.app.security_agent.get_private_user_role(self.user)
        for history in (history1, history2):
            assert {permission.role for permission in history.default_permissions} == {private_role}
            assert {permission.action for permission in history.default_permissions} == {
                model.Dataset.permitted_actions.DATASET_ACCESS.action,
                model.Dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS.action,
            }

        calls = controller.service.shareable_service.disable_link_access.call_args_list
        called_ids = [call.args[1] for call in calls]
        assert history1.id in called_ids
        assert history2.id in called_ids
        assert None not in called_ids, "disable_link_access was called with None (the bug)"
