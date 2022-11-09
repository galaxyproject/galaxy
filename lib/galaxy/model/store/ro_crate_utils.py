from galaxy.model import WorkflowInvocation
from rocrate.rocrate import ROCrate
from rocrate.model.contextentity import ContextEntity
from rocrate.model.softwareapplication import SoftwareApplication


class InvocationCrateBuilder:
    def __init__(self, crate: ROCrate, invocation: WorkflowInvocation):
        self.crate = crate
        self.invocation = invocation
        self.workflow_entity = self.crate.mainEntity
        self.roc_engine_run = None
        self.main_action = None

    def add_engine_run(self):
        roc_engine = self.crate.add(SoftwareApplication(self.crate, properties={"name": "Galaxy workflow engine"}))
        roc_engine_run = self.crate.add(
            ContextEntity(
                self.crate,
                properties={
                    "@type": "OrganizeAction",
                    "name": f"Run of {roc_engine['name']}",
                    "startTime": self.invocation.create_time.isoformat(),
                },
            )
        )
        roc_engine_run["instrument"] = roc_engine
        # TODO: add engine Agent?
        self.roc_engine_run = roc_engine_run

    def add_actions(self, activity=None, parent_instrument=None):
        workflow = self.invocation.workflow

        workflow_input_actions = []
        for input_step in workflow.input_steps:
            action = self.crate.add(
                ContextEntity(
                    self.crate,
                    properties={
                        "@type": "CreateAction",
                        "name": input_step.label,
                    },
                )
            )
            workflow_input_actions.append(action)

        workflow_output_actions = []
        # for output_step in workflow.workflow_outputs:
        #     output_step.name

        # for step in self.invocation.steps:
        #     step = cast(WorkflowInvocationStep, step)

        wf_input_ids = [{"@id": input.id} for input in workflow_input_actions]
        wf_output_ids = [{"@id": output.id} for output in workflow_output_actions]
        main_action = self.crate.add(
            ContextEntity(
                self.crate,
                properties={
                    "@type": "CreateAction",
                    "name": workflow.name,
                    "object": wf_input_ids,
                    "result": wf_output_ids,
                },
            )
        )
        self.main_action = main_action
