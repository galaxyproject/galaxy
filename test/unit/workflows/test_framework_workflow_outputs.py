from types import SimpleNamespace
from unittest.mock import Mock

from galaxy_test.workflow.test_framework_workflows import TestWorkflow as _TestWorkflow


def test_element_tests_identifies_workflow_output_as_collection():
    workflow_test = object.__new__(_TestWorkflow)
    workflow_test.test_data_resolver = Mock()
    workflow_test.workflow_populator = Mock()
    workflow_test.dataset_populator = Mock()
    workflow_test.workflow_populator.get_invocation.return_value = {
        "output_collections": {"out": {"id": "collection-id"}}
    }
    workflow_test.dataset_populator.get_history_collection_details.return_value = {
        "collection_type": "list",
        "elements": [],
    }
    run_summary = SimpleNamespace(history_id="history-id", invocation_id="invocation-id")

    workflow_test._verify_output(run_summary, "out", {"element_tests": {}})

    workflow_test.dataset_populator.get_history_collection_details.assert_called_once_with(
        "history-id", content_id="collection-id"
    )
