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
    const steps = workflow.steps;
    const report = workflow.report;
    const license = workflow.license;
    const creator = workflow.creator;
    const annotation = workflow.annotation;
    const name = workflow.name;
    return { steps, report, license, creator, annotation, name };
}
