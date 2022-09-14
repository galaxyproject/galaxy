from functools import partial

import yaml

from galaxy import model
from galaxy.app_unittest_utils import galaxy_mock
from galaxy.managers.workflows import WorkflowsManager
from galaxy.workflow.modules import module_factory


class MockTrans:
    def __init__(self):
        self.app = MockApp()
        self.sa_session = self.app.model.context
        self._user = None

    def save_workflow(self, workflow):
        stored_workflow = model.StoredWorkflow()
        stored_workflow.latest_workflow = workflow
        workflow.stored_workflow = stored_workflow
        stored_workflow.user = self.user
        self.sa_session.add(stored_workflow)
        self.sa_session.flush()
        return stored_workflow

    @property
    def user(self):
        if self._user is None:
            self._user = model.User(email="testworkflows@bx.psu.edu", password="password")
        return self._user


class MockApp(galaxy_mock.MockApp):
    def __init__(self):
        super().__init__()
        self.toolbox = MockToolbox()
        self.workflow_manager = WorkflowsManager(self)


class MockDatatypesRegistry:
    def __init__(self):
        pass

    def get_datatype_by_extension(self, ext):
        return ext

    @property
    def datatypes_by_extension(self):
        return {"fasta": object(), "fastqsanger": object(), "txt": object()}


class MockToolbox:
    def __init__(self):
        self.tools = {}

    def get_tool(self, tool_id, tool_version=None, exact=False, tool_uuid=None):
        # Real tool box returns None of missing tool also
        return self.tools.get(tool_id, None)


def yaml_to_model(has_dict, id_offset=100):
    if isinstance(has_dict, str):
        has_dict = yaml.safe_load(has_dict)

    trans = MockTrans()

    workflow = model.Workflow()
    workflow.steps = []
    for i, step in enumerate(has_dict.get("steps", [])):
        workflow_step = model.WorkflowStep()
        if "order_index" not in step:
            step["order_index"] = i
        if "id" not in step:
            # Fixed Offset ids just to test against assuption order_index != id
            step["id"] = id_offset
            id_offset += 1
        step_type = step.get("type", None)
        assert step_type is not None

        if step_type == "subworkflow":
            subworkflow_dict = step["subworkflow"]
            del step["subworkflow"]
            subworkflow = yaml_to_model(subworkflow_dict, id_offset=id_offset)
            step["subworkflow"] = subworkflow
            id_offset += len(subworkflow.steps)

        for key, value in step.items():
            if key == "input_connections":
                raise NotImplementedError()
            if key == "inputs":
                inputs = []
                for input_name, input_def in value.items():
                    step_input = model.WorkflowStepInput(workflow_step)
                    step_input.name = input_name
                    connections = []
                    for conn_dict in input_def.get("connections", []):
                        conn = model.WorkflowStepConnection()
                        for conn_key, conn_value in conn_dict.items():
                            if conn_key == "@output_step":
                                target_step = workflow.steps[conn_value]
                                conn_value = target_step
                                conn_key = "output_step"
                            if conn_key == "@input_subworkflow_step":
                                conn_value = step["subworkflow"].step_by_index(conn_value)
                                conn_key = "input_subworkflow_step"
                            setattr(conn, conn_key, conn_value)
                        connections.append(conn)
                    step_input.connections = connections
                    inputs.append(step_input)
                value = inputs
            if key == "workflow_outputs":
                value = [partial(_dict_to_workflow_output, workflow_step)(_) for _ in value]
            if key == "collection_type":
                key = "tool_inputs"
                value = {"collection_type": value}
            setattr(workflow_step, key, value)
        if workflow_step.type != "tool":
            module = module_factory.from_workflow_step(trans, workflow_step)
            module.save_to_step(workflow_step)
        workflow.steps.append(workflow_step)

    return workflow


def _dict_to_workflow_output(workflow_step, as_dict):
    output = model.WorkflowOutput(workflow_step)
    for key, value in as_dict.items():
        setattr(output, key, value)
    return output
