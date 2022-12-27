import { useWorkflowStepStore } from "stores/workflowStepStore";

export async function fromSimple(workflow, data, appendData = false) {
    workflow.name = data.name;
    workflow.annotation = data.annotation;
    workflow.license = data.license;
    workflow.creator = data.creator;
    workflow.version = data.version;
    workflow.report = data.report || {};
    Object.values(data.steps).forEach((step) => {
        // If workflow being copied into another, wipe UUID and let
        // Galaxy assign new ones.
        if (appendData) {
            step.uuid = null;
        }
    });
    const stepStore = useWorkflowStepStore();
    Object.entries(data.steps).map(([_, step]) => {
        stepStore.addStep(step);
    });
}

export function toSimple(workflow) {
    const steps = {};
    _rectifyOutputs(workflow);
    Object.values(workflow.nodes).forEach((node) => {
        steps[node.id] = node.step;
    });
    const report = workflow.report;
    const license = workflow.license;
    const creator = workflow.creator;
    const annotation = workflow.annotation;
    const name = workflow.name;
    return { steps, report, license, creator, annotation, name };
}

function _rectifyOutputs(workflow) {
    // Find out if we're using workflow_outputs or not.
    let using_workflow_outputs = false;
    let has_existing_pjas = false;
    Object.values(workflow.nodes).forEach((node) => {
        if (node.activeOutputs.count() > 0) {
            using_workflow_outputs = true;
        }
        Object.values(node.postJobActions).forEach((pja) => {
            if (pja.action_type === "HideDatasetAction") {
                has_existing_pjas = true;
            }
        });
    });
    if (using_workflow_outputs !== false || has_existing_pjas !== false) {
        // Using workflow outputs, or has existing pjas.  Remove all PJAs and recreate based on outputs.
        Object.values(workflow.nodes).forEach((node) => {
            if (node.postJobActions === null) {
                node.postJobActions = {};
            }
            const pjas_to_rem = [];
            Object.entries(node.postJobActions).forEach(([pja_id, pja]) => {
                if (pja.action_type == "HideDatasetAction") {
                    pjas_to_rem.push(pja_id);
                }
            });
            if (pjas_to_rem.length > 0) {
                pjas_to_rem.forEach((pja_name) => {
                    delete node.postJobActions[pja_name];
                });
            }
            if (using_workflow_outputs) {
                Object.values(node.outputs).forEach((ot) => {
                    const create_pja = !node.activeOutputs.exists(ot.name);
                    if (create_pja === true) {
                        const pja = {
                            action_type: "HideDatasetAction",
                            output_name: ot.name,
                            action_arguments: {},
                        };
                        node.postJobActions[`HideDatasetAction${ot.name}`] = null;
                        node.postJobActions[`HideDatasetAction${ot.name}`] = pja;
                    }
                });
            }
        });
    }
}
