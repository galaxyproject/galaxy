import { useWorkflowStepStore, type Steps, type ConnectionOutputLink } from "@/stores/workflowStepStore";

interface Workflow {
    name: string;
    annotation: string;
    license: string;
    creator: any;
    version: number;
    report: any;
    steps: Steps;
}

export async function fromSimple(data: Workflow, appendData = false, defaultPosition = { top: 0, left: 0 }) {
    const stepStore = useWorkflowStepStore();
    const stepIdOffset = stepStore.getStepIndex + 1;
    Object.values(data.steps).forEach((step) => {
        // If workflow being copied into another, wipe UUID and let
        // Galaxy assign new ones.
        if (appendData) {
            delete step.uuid;
            if (!step.position) {
                // Should only happen for manually authored editor content,
                // good enough for a first pass IMO.
                step.position = { top: step.id * 100, left: step.id * 100 };
            }
            step.id += stepIdOffset;
            step.position.left += defaultPosition.left;
            step.position.top += defaultPosition.top;
            Object.values(step.input_connections).forEach((link) => {
                if (link === undefined) {
                    console.error("input connections invalid", step.input_connections);
                } else {
                    let linkArray: ConnectionOutputLink[];
                    if (!Array.isArray(link)) {
                        linkArray = [link];
                    } else {
                        linkArray = link;
                    }
                    linkArray.forEach((link) => {
                        link.id += stepIdOffset;
                    });
                }
            });
        }
    });
    Object.values(data.steps).map((step) => {
        stepStore.addStep(step);
    });
}

export function toSimple(workflow: Workflow) {
    const steps = workflow.steps;
    const report = workflow.report;
    const license = workflow.license;
    const creator = workflow.creator;
    const annotation = workflow.annotation;
    const name = workflow.name;
    return { steps, report, license, creator, annotation, name };
}
