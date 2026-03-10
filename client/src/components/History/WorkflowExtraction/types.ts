import type { WorkflowExtractionJob } from "@/api/histories";

export type WorkflowExtractionInput = WorkflowExtractionJob & {
    step_type: "input_dataset" | "input_collection";
    /** The modifiable new name for the workflow input, which will be used in the generated workflow. */
    newName: string;
};

export function isWorkflowExtractionInput(
    job: WorkflowExtractionJob | WorkflowExtractionInput,
): job is WorkflowExtractionInput {
    return job.step_type.startsWith("input");
}
