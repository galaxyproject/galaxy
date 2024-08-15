""" Test Tool execution and state handling logic.
"""

from collections import OrderedDict
from typing import cast

import webob.exc
from sqlalchemy import select

import galaxy.model
from galaxy.app_unittest_utils import tools_support
from galaxy.managers.collections import DatasetCollectionManager
from galaxy.model.base import transaction
from galaxy.model.orm.util import add_object_to_object_session
from galaxy.util.bunch import Bunch
from galaxy.util.unittest import TestCase

BASE_REPEAT_TOOL_CONTENTS = """<tool id="test_tool" name="Test Tool">
    <command>echo "$param1" #for $r in $repeat# "$r.param2" #end for# &lt; $out1</command>
    <inputs>
        <param type="text" name="param1" value="" />
        <repeat name="repeat1" label="Repeat 1">
          %s
        </repeat>
    </inputs>
    <outputs>
        <data name="out1" format="data" />
    </outputs>
</tool>
"""

# Tool with a repeat parameter, to test state update.
REPEAT_TOOL_CONTENTS = BASE_REPEAT_TOOL_CONTENTS % ("""<param type="text" name="param2" value="" />""",)
REPEAT_COLLECTION_PARAM_CONTENTS = BASE_REPEAT_TOOL_CONTENTS % (
    """<param type="data_collection" name="param2" collection_type="paired" />""",
)


class TestToolExecution(TestCase, tools_support.UsesTools):
    tool_action: "MockAction"

    def setUp(self):
        self.setup_app()
        self.history = galaxy.model.History()
        self.trans = MockTrans(self.app, self.history)
        self.app.dataset_collection_manager = cast(DatasetCollectionManager, MockCollectionService())
        self.tool_action = MockAction(self.trans)

    def tearDown(self):
        self.tear_down_app()

    def test_state_new(self):
        self._init_tool(tools_support.SIMPLE_TOOL_CONTENTS)
        vars = self.__handle_with_incoming(param1="moo")
        state = self.__assert_rerenders_tool_without_errors(vars)
        assert state["param1"] == "moo"

    def test_execute(self):
        self._init_tool(tools_support.SIMPLE_TOOL_CONTENTS)
        vars = self.__handle_with_incoming(param1="moo")
        self.__assert_executed(vars)
        # Didn't specify a rerun_remap_id so this should be None
        assert self.tool_action.execution_call_args[0]["rerun_remap_job_id"] is None

    def test_execute_exception(self):
        self._init_tool(tools_support.SIMPLE_TOOL_CONTENTS)
        self.tool_action.raise_exception()
        try:
            self.__handle_with_incoming(param1="moo")
        except Exception as e:
            assert "Error executing tool" in str(e)

    def test_execute_errors(self):
        self._init_tool(tools_support.SIMPLE_TOOL_CONTENTS)
        self.tool_action.return_error()
        try:
            self.__handle_with_incoming(param1="moo")
        except Exception as e:
            assert "Test Error Message" in str(e)

    def test_redirect(self):
        self._init_tool(tools_support.SIMPLE_TOOL_CONTENTS)
        self.tool_action.expect_redirect = True
        redirect_raised = False
        try:
            self.__handle_with_incoming(param1="moo")
        except webob.exc.HTTPFound:
            redirect_raised = True
        assert redirect_raised

    def test_remap_job(self):
        self._init_tool(tools_support.SIMPLE_TOOL_CONTENTS)
        vars = self.__handle_with_incoming(param1="moo", rerun_remap_job_id=self.app.security.encode_id(123))
        self.__assert_executed(vars)
        assert self.tool_action.execution_call_args[0]["rerun_remap_job_id"] == 123

    def test_invalid_remap_job(self):
        self._init_tool(tools_support.SIMPLE_TOOL_CONTENTS)
        try:
            self.__handle_with_incoming(param1="moo", rerun_remap_job_id="123")
        except Exception as e:
            assert "invalid job" in str(e)

    def test_data_param_execute(self):
        self._init_tool(tools_support.SIMPLE_CAT_TOOL_CONTENTS)
        hda = self.__add_dataset(1)
        # Execute tool action
        vars = self.__handle_with_incoming(param1=1)
        self.__assert_executed(vars)
        # Tool 'executed' once, with hda as param1
        assert len(self.tool_action.execution_call_args) == 1
        assert self.tool_action.execution_call_args[0]["incoming"]["param1"] == hda

    def test_data_param_state_update(self):
        self._init_tool(tools_support.SIMPLE_CAT_TOOL_CONTENTS)
        hda = self.__add_dataset(1)
        # Update state
        vars = self.__handle_with_incoming(param1=1)
        state = self.__assert_rerenders_tool_without_errors(vars)
        assert hda == state["param1"]

    def __handle_with_incoming(self, **kwds):
        """Execute tool.handle_input with incoming specified by kwds
        (optionally extending a previous state).
        """
        return self.tool.handle_input(trans=self.trans, incoming=kwds)

    def __add_dataset(self, id, state="ok"):
        hda = galaxy.model.HistoryDatasetAssociation()
        hda.id = id
        hda.dataset = galaxy.model.Dataset()
        hda.dataset.state = "ok"

        self.trans.sa_session.add(hda)
        add_object_to_object_session(self.history, hda)
        self.history.datasets.append(hda)
        session = self.trans.sa_session
        with transaction(session):
            session.commit()
        return hda

    def __add_collection_dataset(self, id, collection_type="paired", *hdas):
        hdca = galaxy.model.HistoryDatasetCollectionAssociation()
        hdca.id = id
        collection = galaxy.model.DatasetCollection()
        hdca.collection = collection
        galaxy.model.DatasetCollectionElement(collection=collection, element=self.__add_dataset(1))
        collection.collection_type = collection_type
        self.trans.sa_session.model_objects[galaxy.model.HistoryDatasetCollectionAssociation][id] = hdca
        self.history.dataset_collections.append(hdca)
        return hdca

    def __assert_rerenders_tool_without_errors(self, vars):
        self.__assert_no_errors(vars)
        return self.tool_action.execution_call_args[0]["incoming"]

    def __assert_executed(self, vars):
        self.__assert_no_errors(vars)
        assert len(vars["jobs"]) > 0

    def __assert_no_errors(self, vars):
        assert "job_errors" in vars
        assert not vars["job_errors"]


class MockAction(tools_support.MockActionI):
    def __init__(self, expected_trans):
        self.expected_trans = expected_trans
        self.execution_call_args = []
        self.expect_redirect = False
        self.exception_after_exection = None
        self.error_message_after_excution = None

    def execute(self, tool, trans, **kwds):
        assert self.expected_trans == trans
        self.execution_call_args.append(kwds)
        num_calls = len(self.execution_call_args)
        if self.expect_redirect:
            raise webob.exc.HTTPFound(location="http://google.com")
        if self.exception_after_exection is not None:
            if num_calls > self.exception_after_exection:
                raise Exception("Test Exception")
        if self.error_message_after_excution is not None:
            if num_calls > self.error_message_after_excution:
                return None, "Test Error Message"

        return galaxy.model.Job(), OrderedDict(out1="1")

    def raise_exception(self, after_execution=0):
        self.exception_after_exection = after_execution

    def return_error(self, after_execution=0):
        self.error_message_after_excution = after_execution


class MockTrans:
    def __init__(self, app, history):
        self.app = app
        self.history = history
        self.user = None
        self.history._active_datasets_and_roles = [
            hda
            for hda in self.app.model.session.scalars(select(galaxy.model.HistoryDatasetAssociation)).all()
            if hda.active and hda.history == history
        ]
        self.workflow_building_mode = False
        self.webapp = Bunch(name="galaxy")
        self.sa_session = self.app.model.context
        self.url_builder = None
        self.galaxy_session = None

    def get_history(self, **kwargs):
        return self.history

    def get_current_user_roles(self):
        return []

    def log_event(self, *args, **kwds):
        pass


class MockCollectionService:
    def __init__(self):
        self.collection_info = object()

    def match_collections(self, collections_to_match):
        return self.collection_info
