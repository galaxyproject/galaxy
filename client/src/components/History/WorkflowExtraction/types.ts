import type { WorkflowExtractionJob } from "@/api/histories";

export type WorkflowExtractionToolJob = WorkflowExtractionJob & { step_type: "tool" };

export type WorkflowExtractionInputJob = WorkflowExtractionJob & {
    step_type: "input_dataset" | "input_collection";
};

export type WorkflowExtractionInput = WorkflowExtractionInputJob & {
    /** The modifiable new name for the workflow input, which will be used in the generated workflow. */
    newName: string;
};

export type WorkflowExtractionRow = WorkflowExtractionToolJob | WorkflowExtractionInput;

export function isWorkflowExtractionInput(job: WorkflowExtractionRow): job is WorkflowExtractionInput;
export function isWorkflowExtractionInput(job: WorkflowExtractionJob): job is WorkflowExtractionInputJob;
export function isWorkflowExtractionInput(
    job: WorkflowExtractionJob | WorkflowExtractionRow,
): job is WorkflowExtractionInputJob | WorkflowExtractionInput {
    return job.step_type === "input_dataset" || job.step_type === "input_collection";
}

export function isMappedTool(
    job: WorkflowExtractionJob | WorkflowExtractionRow,
): job is WorkflowExtractionToolJob & { implicit_collection_jobs_id: string } {
    return job.step_type === "tool" && Boolean(job.implicit_collection_jobs_id);
}
