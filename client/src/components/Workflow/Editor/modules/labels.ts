// abstractions for dealing with workflows labels and
// connecting them to the Markdown editor

type WorkflowLabelKind = "input" | "output" | "step";

export interface WorkflowLabel {
    label: string;
    type: WorkflowLabelKind;
}

interface StepOutput {
    label?: string;
}

interface Step {
    label?: string;
    type: string;
    workflow_outputs: StepOutput[];
}

export type WorkflowLabels = WorkflowLabel[];

export function fromSteps(steps?: Step[]): WorkflowLabels {
    const labels: WorkflowLabels = [];
    if (steps) {
        Object.values(steps).forEach((step) => {
            const stepType = step.type;
            if (step.label) {
                const isInput = ["data_input", "data_collection_input", "parameter_input"].indexOf(stepType) >= 0;
                if (isInput) {
                    labels.push({ type: "input", label: step.label });
                } else {
                    labels.push({ type: "step", label: step.label });
                }
            }
            step.workflow_outputs.forEach((workflowOutput) => {
                if (workflowOutput.label) {
                    labels.push({ type: "output", label: workflowOutput.label });
                }
            });
        });
    }
    return labels;
}
